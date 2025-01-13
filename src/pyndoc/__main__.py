import sys
from pathlib import Path
import time
from .preprocess import preprocess
import subprocess
import json
import yaml
from .server_utils import get_or_start_server, stop_server

import logging

def start_logging(logging_level: str | None = None):
    """Start logging to a file."""
    if logging_level is not None:
        logging_level = logging.getLevelName(logging_level.upper())
    logging.basicConfig(
        filename="pyndoc.log",
        level=logging.DEBUG if logging_level is None else logging_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="w+",
    )

    logging.debug("Created log file from __main__.py")


def check_filter_executable(filter_file: Path):
    # if we're on linux, check if the filter has execute permissions
    if sys.platform == "linux":
        if not filter_file.is_file():
            raise FileNotFoundError("Filter file not found.")
        if not filter_file.stat().st_mode & 0o111:
            filter_file.chmod(0o755)


def get_arg(
    args: list[str], arg: str | list[str], remove: bool = False, is_flag=False
) -> str | bool | None:
    """Get an argument from a list of command line arguments.

    Parameters
    ----------
    args : list[str]
        The list of command line arguments, split on spaces.
    arg : str | list[str]
        The argument to search for. If a list, this should be a list of 
        aliases for the argument. The first one found will be returned.
    remove : bool, optional
        Whether to remove the argument from the list, by default False
    is_flag : bool, optional
        Whether the argument is a flag (no value), by default False

    Returns
    -------
    str | bool | None
        The value of the argument, or True if it is a flag, or None if not found.
    """    
    if isinstance(arg, str):
        arg = [arg]
    if is_flag:
        for a in arg:
            if a in args:
                if remove:
                    idx = args.index(a)
                    args.pop(idx)
                return True
        return False
    for a in arg:
        if a in args:
            idx = args.index(a)
            value = args[idx + 1]
            if remove:
                args.pop(idx)
                args.pop(idx)
            return value
    for a in arg:
        for i, sys_a in enumerate(args):
            if "=" not in sys_a:
                continue
            sys_a = sys_a.split("=")
            if sys_a[0] == a:
                if remove:
                    args.pop(i)
                return sys_a[1]
    return None


def replace_arg(args: list[str], arg: str | list[str], value: str):
    """Replace an argument in a list of command line arguments.

    Parameters
    ----------
    args : list[str]
        The list of command line arguments, split on spaces.
    arg : str | list[str]
        The argument to search for. If a list, this should be a list of 
        aliases for the argument. The first one found will be replaced.
    value : str
        The value to replace the argument with.

    Raises
    ------
    ValueError
        If the argument is not found in the list of arguments.
    """    
    if isinstance(arg, str):
        arg = [arg]
    for a in arg:
        if a in args:
            idx = args.index(a)
            args[idx + 1] = value
            return
    for a in arg:
        for i, sys_a in enumerate(args):
            if "=" not in sys_a:
                continue
            sys_a = sys_a.split("=")
            if sys_a[0] == a:
                args[i] = f"{a}={value}"
                return
    raise ValueError(f"Argument {arg} not found in args.")


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


def get_format(args) -> str:
    """Get the output format from the command line arguments. Checks for
        - `--to` or `-t`
        - `--write` or `-w`
        - `--output` or `-o` specifying a file extension
        - `--defaults` specifying a file with default options

    Parameters
    ----------
    args : _type_
        The list of command line arguments.

    Returns
    -------
    str
        The output format to convert to.

    Raises
    ------
    ValueError
        If no output format is specified.
    ValueError
        If an unknown output format or file extension is specified.
    """    
    to_format = get_arg(args, ("--to", "-t", "--write", "-w"))
    if to_format is None:
        out_file = get_arg(args, ("--output", "-o"))
        if out_file is None:
            # No format given, try checking for a defaults file
            defaults_file = get_arg(args, ("--defaults",))
            if defaults_file is not None:
                with Path(defaults_file).open("r") as f:
                    defaults = yaml.safe_load(f)
                # Could be `to`, `writer`, or `output-file`
                options = ["to", "writer", "output-file"]
                for option in options:
                    if option in defaults:
                        to_format = defaults[option]
                        break
            if to_format is None:
                raise ValueError("No output format or output file specified.")
        else:
            file_ext = Path(out_file).suffix
            to_format = file_ext_map.get(file_ext[1:], None)
            if to_format is None:
                raise ValueError(
                    f"Unknown output format: {file_ext}. Please specify the format with `--to`."
                )
    if to_format == "pdf":
        pdf_engine = get_arg(args, "--pdf-engine")
        to_format = "latex" if pdf_engine is None else pdf_engine
    return to_format


logging_files = ["pyndoc.log", "pyndoc.filters.log", "pyndoc.server.log"]

return_codes = {
    1:  "PandocIOError",
    3:  "PandocFailOnWarningError",
    4:  "PandocAppError",
    5:  "PandocTemplateError",
    6:  "PandocOptionError",
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


def main():
    """Main function for the command line interface. Parses the command line
    arguments, preprocesses the input file if necessary, starts the server,
    runs pandoc, stops the server, and deletes the metadata file.
    """    
    args = sys.argv[1:]
    to_preprocess = get_arg(args, ("--preprocess"), is_flag=True, remove=True)
    only_preprocess = get_arg(args, ("--preprocess-only"), is_flag=True, remove=True)

    # remove the log files if they exist
    for log_file in logging_files:
        try:
            Path(log_file).unlink()
        except FileNotFoundError:
            pass

    logging_level = get_arg(args, ("--log-level"), remove=True)
    start_logging(logging_level)

    target_format = get_format(args)

    if to_preprocess:
        logging.info("Preprocessing file.")
        start_time = time.perf_counter_ns()
        target_file = Path(args[-1])
        with target_file.open("r") as f:
            contents = f.read()
        contents = preprocess(contents, target_format=target_format)
        temp_file = target_file.parent / (
            target_file.stem + "_tmp" + target_file.suffix
        )
        with temp_file.open("w") as f:
            f.write(contents)
        end_time = time.perf_counter_ns()
        logging.info(f"Preprocessing took {(end_time - start_time) / 1e6:.0f} ms.")
        args[-1] = str(temp_file)
        if only_preprocess:
            # print(contents)
            return

    check_filter_executable(Path(__file__).parent / "filter.py")

    # add the filter to the filters list
    filter_file = Path(__file__).parent / "filter.py"
    # current_filters = get_arg(args, ("--filter", "-F"))
    # if current_filters is not None:
    #     current_filters = current_filters.split(",")
    #     current_filters.append(str(filter_file))
    #     replace_arg(args, ("--filter", "-F"), ",".join(current_filters))
    # else:
    #     args.append(f"--filter={filter_file}")
    # This is not how pandoc filters work. It does not take a list of filters, instead the filter can be passed multiple times. This filter should be first, however.
    args.insert(0, f"--filter={filter_file}")

    start_time = time.perf_counter_ns()
    logging.debug("Getting or starting server.")
    port = get_or_start_server()
    logging.debug(f"Server started on port {port}.")
    end_time = time.perf_counter_ns()
    logging.info(f"Server startup took {(end_time - start_time) / 1e6:.0f} ms.")
    metadata_file = Path(".pyndoc.json")
    metadata = {"format": target_format, "port": port}
    with metadata_file.open("w") as f:
        json.dump(metadata, f, indent=4)

    # run pandoc
    start_time = time.perf_counter_ns()
    result = subprocess.run(["pandoc", *args], capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode())
        raise Exception(f"Pandoc failed with return code {result.returncode}: {return_codes.get(result.returncode, 'Unknown error')}")
    else:
        print(result.stdout.decode())
    end_time = time.perf_counter_ns()
    logging.info(f"Pandoc took {(end_time - start_time) / 1e6:.0f} ms and returned {result.returncode}.")
    if to_preprocess:
        temp_file.unlink()
    stop_server(port)
    try:
        metadata_file.unlink()
    except FileNotFoundError:
        logging.warning("Metadata file not found to delete.")
    


if __name__ == "__main__":
    main()
