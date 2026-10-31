from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

import yaml

from .preprocess import preprocess
from .timer import Timer

logger = logging.getLogger("pyndoc")


def get_default_log_dir() -> Path:
    """Return the user-level log directory for Pyndoc, falling back to CWD on error."""
    override = os.environ.get("PYNDOC_LOG_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        path = (
            Path(local_app_data) / "pyndoc"
            if local_app_data
            else Path.home() / ".pyndoc"
        )
    else:
        state_home = os.environ.get("XDG_STATE_HOME")
        cache_home = os.environ.get("XDG_CACHE_HOME")
        base = Path(state_home or cache_home or (Path.home() / ".cache"))
        path = base / "pyndoc"

    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return Path(".")


def start_logging(
    logging_level: str | None = None,
    log_file: Path | str | None = None,
) -> Path | None:
    level = (logging_level or "DEBUG").upper()

    valid_levels = logging.getLevelNamesMapping()
    if level not in valid_levels:
        valid_keys = ", ".join(k for k in valid_levels if not k.startswith("NOTSET"))
        raise ValueError(f"Invalid log level: {logging_level!r}. Expected one of: {valid_keys}")

    if log_file is not None:
        target_path = Path(log_file)
    else:
        env_log = os.environ.get("PYNDOC_LOG_FILE")
        if env_log:
            target_path = Path(env_log)
        else:
            target_path = get_default_log_dir() / "pyndoc.log"

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(target_path),
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filemode="w",
            encoding="utf-8",
            force=True,
        )
        logger.debug("Created log file at %s", target_path)
        return target_path
    except OSError as e:
        # Fall back to stderr if writing to log file fails
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,
        )
        logger.warning(
            "Could not open log file %s (%s); logging to stderr", target_path, e
        )
        return None


def check_filter_executable(filter_file: Path) -> None:
    """Ensure the filter script has executable permissions on POSIX systems."""
    if sys.platform != "win32":
        if not filter_file.is_file():
            raise FileNotFoundError(f"Filter file not found: {filter_file}")
        if not (filter_file.stat().st_mode & 0o111):
            try:
                filter_file.chmod(filter_file.stat().st_mode | 0o755)
            except OSError as e:
                logger.warning(
                    "Could not set executable permissions on filter script %s: %s",
                    filter_file,
                    e,
                )


def parse_cli_args(argv: Sequence[str]) -> tuple[argparse.Namespace, list[str]]:
    # Parse the pyndoc arguments without touching the normal Pandoc arguments
    parser = argparse.ArgumentParser(
        prog="pyndoc",
        description="Pandoc preprocessor and filter for Python execution at build time.",
        add_help=False,
    )
    parser.add_argument("--preprocess", action="store_true", help="Preprocess the input file before Pandoc.")
    parser.add_argument("--preprocess-only", action="store_true", help="Run preprocessing only and print output.")
    parser.add_argument("--log-level", default=None, help="Set logging verbosity level.")
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to log file (default: user cache directory or PYNDOC_LOG_FILE).",
    )
    parser.add_argument(
        "--strict",
        "--fail-on-error",
        dest="strict",
        action="store_true",
        help="Abort Pandoc build on filter execution errors instead of inserting inline error text.",
    )

    return parser.parse_known_args(argv)


file_ext_map = {
    "adoc": "asciidoc",
    "bib": "bibtex",
    "dbk": "docbook",
    "docx": "docx",
    "epub": "epub",
    "html": "html",
    "ipynb": "ipynb",
    "json": "json",
    "md": "markdown",
    "odt": "odt",
    "pdf": "pdf",
    "pptx": "pptx",
    "rst": "rst",
    "tex": "latex",
    "txt": "plain",
    "typ": "typst",
}


def get_format(pandoc_args: list[str]) -> str:
    # Check cli arguments to find or deduce the target format.
    # Checks for explicit output formats or writers, then the output file's 
    # extension, then a `defaults` file and finally the pdf engine
    format_parser = argparse.ArgumentParser(add_help=False)
    format_parser.add_argument("--to", "-t", "--write", "-w", dest="to_format", default=None)
    format_parser.add_argument("--output", "-o", dest="output_file", default=None)
    format_parser.add_argument("--defaults", dest="defaults_file", default=None)
    format_parser.add_argument("--pdf-engine", dest="pdf_engine", default=None)

    opts, _ = format_parser.parse_known_args(pandoc_args)
    to_format = opts.to_format

    if to_format is None:
        if opts.output_file is None:
            # Check for defaults file
            if opts.defaults_file is not None:
                defaults_path = Path(opts.defaults_file)
                if defaults_path.is_file():
                    with defaults_path.open("r", encoding="utf-8") as f:
                        defaults = yaml.safe_load(f) or {}
                    for key in ("to", "writer", "output-file"):
                        if key in defaults:
                            val = defaults[key]
                            if key == "output-file":
                                ext = Path(val).suffix.lstrip(".")
                                to_format = file_ext_map.get(ext)
                            else:
                                to_format = val
                            break
            if to_format is None:
                raise ValueError("No output format or output file specified.")
        else:
            ext = Path(opts.output_file).suffix.lstrip(".")
            to_format = file_ext_map.get(ext)
            if to_format is None:
                raise ValueError(
                    f"Unknown output format for extension '{ext}'. Please specify format with `--to`."
                )

    if to_format == "pdf":
        to_format = opts.pdf_engine if opts.pdf_engine else "latex"

    return to_format


def find_input_file_index(args: list[str]) -> int:
    # Input file is positional but can occur anywhere. Searches backwards to
    # find the last argument which doesn't have a named flag.
    val_taking_flags = {
        "-o", "--output", "-t", "--to", "-w", "--write",
        "-f", "--from", "-r", "--read",
        "--defaults", "--pdf-engine", "-F", "--filter",
        "-V", "--variable", "-M", "--metadata",
        "-C", "--citeproc", "--csl", "--bibliography",
        "--template", "--css", "--highlight-style",
    }
    i = len(args) - 1
    while i >= 0:
        arg = args[i]
        if not arg.startswith("-"):
            # Check if this was a value for the preceding flag
            if i > 0 and args[i - 1] in val_taking_flags:
                i -= 2
                continue
            return i
        i -= 1
    return len(args) - 1


return_codes = {
    1: "PandocIOError",
    3: "PandocFailOnWarningError",
    4: "PandocAppError",
    5: "PandocTemplateError",
    6: "PandocOptionError",
    21: "PandocUnknownReaderError",
    22: "PandocUnknownWriterError",
    23: "PandocUnsupportedExtensionError",
    24: "PandocCiteprocError",
    25: "PandocBibliographyError",
    31: "PandocEpubSubdirectoryError",
    43: "PandocPDFError",
    44: "PandocXMLError",
    47: "PandocPDFProgramNotFoundError",
    61: "PandocHttpError",
    62: "PandocShouldNeverHappenError",
    63: "PandocSomeError",
    64: "PandocParseError",
    66: "PandocMakePDFError",
    67: "PandocSyntaxMapError",
    83: "PandocFilterError",
    84: "PandocLuaError",
    89: "PandocNoScriptingEngine",
    91: "PandocMacroLoop",
    92: "PandocUTF8DecodingError",
    93: "PandocIpynbDecodingError",
    94: "PandocUnsupportedCharsetError",
    97: "PandocCouldNotFindDataFileError",
    98: "PandocCouldNotFindMetadataFileError",
    99: "PandocResourceNotFound",
}


def main() -> None:
    pyndoc_opts, pandoc_args = parse_cli_args(sys.argv[1:])

    if pyndoc_opts.strict:
        os.environ["PYNDOC_STRICT"] = "1"

    start_logging(pyndoc_opts.log_level, log_file=pyndoc_opts.log_file)

    target_format = get_format(pandoc_args)

    temp_file: Path | None = None
    if pyndoc_opts.preprocess or pyndoc_opts.preprocess_only:
        with Timer("Preprocessing", logger=logger, log_level=logging.INFO):
            input_idx = find_input_file_index(pandoc_args)
            target_file = Path(pandoc_args[input_idx])

            with target_file.open("r", encoding="utf-8") as f:
                contents = f.read()

            contents = preprocess(contents, target_format=target_format)

            if pyndoc_opts.preprocess_only:
                print(contents)
                return

            # Create a collision-safe temporary file. Try target_file.parent first
            # to preserve Pandoc relative path resolution, falling back to system tempdir.
            try:
                tf = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=target_file.parent,
                    prefix=f".{target_file.stem}_",
                    suffix=f"_tmp{target_file.suffix}",
                    delete=False,
                )
            except OSError:
                tf = tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    prefix=f"{target_file.stem}_",
                    suffix=f"_tmp{target_file.suffix}",
                    delete=False,
                )

            with tf:
                tf.write(contents)
            temp_file = Path(tf.name)

            pandoc_args[input_idx] = str(temp_file)

    filter_file = Path(__file__).parent / "filter.py"
    check_filter_executable(filter_file)

    # Insert Pyndoc's filter at the beginning of the arguments list
    # This guarantees it runs before any other user-specified Pandoc filters
    pandoc_args.insert(0, f"--filter={filter_file}")

    try:
        with Timer("Pandoc execution", logger=logger, log_level=logging.INFO):
            result = subprocess.run(["pandoc", *pandoc_args], capture_output=True)

        if result.returncode != 0:
            err_msg = result.stderr.decode("utf-8", errors="replace")
            print(err_msg, file=sys.stderr)
            raise RuntimeError(
                f"Pandoc failed with return code {result.returncode}: {return_codes.get(result.returncode, 'Unknown error')}"
            )
        elif result.stdout:
            sys.stdout.buffer.write(result.stdout)
            sys.stdout.buffer.flush()
    finally:
        # Guarantee cleanup even on failure or keyboard interrupt
        if temp_file is not None and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
