#!/usr/bin/env python3

import sys
from typing import Dict, Tuple
import panflute
import logging
from pathlib import Path
import json

from pyndoc.formats import Format
import pyndoc.markdown as md
import pyndoc.latex as tex
import pyndoc.server_utils as server_utils


def handle_file(
    file_path: str, classes: list, element_type: panflute.Element
) -> panflute.Element:
    """Handle a file element. Reads the file and executes the contents,
    collecting any output to stdout and returning it as a raw block or inline
    element.

    Parameters
    ----------
    file_path : str
        Path to the python file to execute
    classes : list
        Classes associated with the element
    element_type : panflute.Element
        Type of element to return (CodeBlock if block, Code if inline)

    Returns
    -------
    panflute.Element
        The output of the code execution as a panflute element, or an error message
    """    
    file = Path(file_path)
    if not file.exists():
        return element_type(f"Error: File not found: {file}")
    if not file.is_file():
        return element_type(f"Error: Not a file: {file}")
    response = get_file_response(file)
    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        return element_type(f"Failed to decode response (invalid JSON): {response}")
    if response["type"] == "error":
        return element_type(f"Error running file: {response['message']}")

    if "quiet" in classes:
        return []

    constructor = (
        panflute.RawBlock
        if element_type == panflute.CodeBlock
        else panflute.RawInline
    )
    format = md.TARGET_FORMAT.name.lower()
    if format in ["revealjs", "chunkedhtml"]:
        format = "html"
    if format == "beamer":
        format = "latex"
    return constructor(response["message"], format=format)


def handle_element(
    code: str, classes: list, element_type: panflute.Element
) -> panflute.Element:
    """Handle a code element. Evaluates the contents of the code block and returns 
    the output as a panflute element (inline or block as appropriate).

    Parameters
    ----------
    code : str
        Code to execute
    classes : list
        Classes associated with the element
    element_type : panflute.Element
        Type of element to return (CodeBlock if block, Code if inline)

    Returns
    -------
    panflute.Element
        The value of the code execution as a panflute element, or an error message
    """    
    response = get_element_response(code)
    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        return element_type(f"Failed to decode response (invalid JSON): {response}")
    if response["type"] == "error":
        return element_type(f"Error running code: {response['message']}")
    if "quiet" in classes:
        # This shouldn't happen, but just in case we want it to behave as expected
        return []
    
    try:
        new_element = element_from_json(response["message"])
    except Exception as e:
        return element_type(f"Error converting to panflute.Element: {e}")
    logging.debug(f"Recieved {'block' if isinstance(new_element, panflute.Block) else 'inline'} element with classes {classes}")
    if "inline" in classes and isinstance(new_element, panflute.Block):
        # This has returned a block element, but was requested as an inline element. Convert to a Span
        new_element = panflute.Span(*new_element.content)
    elif "block" in classes and isinstance(new_element, panflute.Inline):
        # This has returned an inline element, but was requested as a block element. Convert to a Para
        new_element = panflute.Para(new_element)
    elif isinstance(new_element, panflute.Block) and element_type == panflute.Code:
        logging.warning(f"Expected inline but recieved a block: \n\tCode: {code}\n\tResult: {panflute.stringify(new_element)}")
    #     # This should probably have been an inline element, but was wrapped in a Para
        new_element = panflute.Span(*new_element.content)
    elif isinstance(new_element, panflute.Inline) and element_type == panflute.CodeBlock:
        logging.warning(f"Expected block but recieved an inline: \n\tCode: {code}\n\tResult: {panflute.stringify(new_element)}")
    #     # This should probably have been a block element, but was wrapped in a Span
        new_element = panflute.Para(new_element)
    return new_element


def element_from_json(object: Dict) -> panflute.Element:
    """Convert a JSON object to a panflute element, appropriately handling nested elements.

    Parameters
    ----------
    object : Dict
        The JSON object to convert to a panflute element

    Returns
    -------
    panflute.Element
        The panflute element created from the JSON object
    """    
    # Call panflute.elements.from_json() recursively to convert the entire object and all its children
    logging.debug(f"Converting json to element: \n{json.dumps(object, indent = 2)}")
    children = object.get("c", [])
    if isinstance(children, list):
        children = convert_children(children)
    object["c"] = children
    return panflute.elements.from_json(object)

def convert_children(children: list) -> list:
    """Helper function to convert a list of children to panflute elements Should not be 
    called directly.

    Parameters
    ----------
    children : list
        List of children to convert

    Returns
    -------
    list
        List of panflute elements created from the children
    """    
    return [element_from_json(child) if isinstance(child, dict) else convert_children(child) if isinstance(child, list) else child for child in children]


def handle_raw(
    code: str, classes: list, element_type: panflute.Element
) -> panflute.Element:
    """Handle a raw code element. Executes the contents of the code block and returns
    the output ready to be inserted verbatim into the document.

    Parameters
    ----------
    code : str
        Code to execute
    classes : list
        Classes associated with the element
    element_type : panflute.Element
        Type of element to return (CodeBlock if block, Code if inline)

    Returns
    -------
    panflute.Element
        The output of the code execution as a panflute element, or an error message
    """    
    response = get_string_response(code)
    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        return element_type(f"Failed to decode response (invalid JSON): {response}")
    if response["type"] == "error":
        return element_type(f"Error running code: {response['message']}")
    if "quiet" in classes:
        return []
    constructor = (
        panflute.RawBlock
        if element_type == panflute.CodeBlock
        else panflute.RawInline
    )
    format=md.TARGET_FORMAT.name.lower()
    if format in ["revealjs", "chunkedhtml"]:
        format = "html"
    if format == "beamer":
        format = "latex"
    return constructor(response["message"], format=format)


def process_code(elem: panflute.Element) -> panflute.Element:
    """Process a code element, determining the type of code block and handling it appropriately.

    Parameters
    ----------
    elem : 
        The code block to process

    Returns
    -------
    panflute.Element
        The output of the code execution as a panflute element, or an error message
    """    
    if "py-file" in elem.classes:
        return handle_file(elem.text.strip(), elem.classes, elem.__class__)
    elif "py-md" in elem.classes:
        return handle_element(elem.text.strip(), elem.classes, elem.__class__)
    elif "py" in elem.classes:
        return handle_raw(elem.text.strip(), elem.classes, elem.__class__)


def get_string_response(code: str) -> str:
    """Sends the code to the server for execution and accepts the output as the response."""
    response = server_utils.create_socket_and_send_request(port, code, "string")
    return response


def get_element_response(code: str) -> str:
    """Sends the code to the server for execution and accepts the output as the response."""
    response = server_utils.create_socket_and_send_request(port, code, "object")
    return response


def get_file_response(file_path: Path) -> str:
    """Sends the code to the server for execution and accepts the output as the response."""
    response = server_utils.create_socket_and_send_request(port, str(file_path), "file")
    return response


def filter(elem, doc):
    """Main filter function. Processes each code block in the document."""
    if isinstance(elem, (panflute.CodeBlock, panflute.Code)):
        logging.debug("\n" + "-" * 80)
        to_return = process_code(elem)
        return to_return


def get_target_format() -> Format:
    """Get the target format from the metadata file, if it exists. If not, default to markdown."""
    try:
        with open(server_utils.METADATA_FILE, "r") as f:
            metadata = json.load(f)
        return Format[metadata["format"].upper()]
    except FileNotFoundError:
        logging.warning("Metadata file not found. Defaulting to markdown.")
        return Format.MARKDOWN
    except KeyError:
        logging.warning("No format specified in metadata file. Defaulting to markdown.")
        return Format.MARKDOWN


def run_filter(doc=None):
    return panflute.run_filter(filter, doc=doc)


def get_logging() -> None:
    """Check if there is already an active logger, and if not start one."""
    log_file = Path("pyndoc.filters.log")
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            filename=log_file,
            filemode="a",
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

def get_server_port() -> Tuple[int, bool]:
    """Get the port number for the server, starting one if it doesn't exist."""
    clear_metadata_file = False  # if the metadata file doesn't exist by the time the filter is run, then it will be created and should be deleted at the end

    port = server_utils.get_active_server()
    if port is None:
        logging.debug("No server found, starting one.")
        port = server_utils.start_server()
        # Get target format from command line arguments instead of metadata file
        target_format = sys.argv[1]
        try:
            md.TARGET_FORMAT = Format[target_format.upper()]
        except KeyError:
            logging.error(
                f"Unrecognised format: {target_format}. Defaulting to markdown."
            )
            md.TARGET_FORMAT = Format.MARKDOWN
        with server_utils.METADATA_FILE.open("w") as f:
            json.dump(
                {"format": md.TARGET_FORMAT.name.upper(), "port": port}, f, indent=4
            )
        clear_metadata_file = True
    return port, clear_metadata_file


if __name__ == "__main__":
    get_logging()
    logging.debug("Called filter.py")
    logging.debug("sys.argv: " + str(sys.argv))
    logging.info("Getting server info.")
    port, clear_metadata_file = get_server_port()
    md.TARGET_FORMAT = get_target_format()
    logging.debug(f"TARGET_FORMAT: {md.TARGET_FORMAT}")
    logging.debug(f"port: {port}")

    if not server_utils.ping_server(port):
        logging.error("Failed to start or communicate with server.")
        sys.exit(1)

    logging.info("Running filter.")
    run_filter()
    logging.info("Filter run complete.")

    if clear_metadata_file:
        server_utils.METADATA_FILE.unlink()