import io
import logging
import socket
import json
from pathlib import Path
import sys
import time
from typing import Dict
import panflute
import threading

# if no logging is set up, set up a basic config to server.pyndoc.log
if not logging.root.handlers:
    logging.basicConfig(
        filename="pyndoc.server.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="a",
    )


from pyndoc.formats import Format
import pyndoc.markdown as md
import pyndoc.latex as tex

# print_normal = print
# def print(*args, **kwargs):
#     if len(args) == 1:
#         arg1 = args[0]
#         if isinstance(arg1, tex.Token):
#             print_normal("\\(" + str(arg1) + "\\)", **kwargs)
#             return
#     print_normal(*args, **kwargs)

# Configuration
HOST: str = '127.0.0.1'
MAX_TIMEOUT: int = 60
METADATA_FILE: Path = Path(".pyndoc.json")

md.TARGET_FORMAT = None
tex.TARGET_FORMAT = None

def deindent(code: str) -> str:
    # remove the indentation from the code block based on the first line
    code = code.replace("\t", " " * 4)
    lines = code.split("\n")
    if len(lines) == 0:
        return code
    indent = len(lines[0]) - len(lines[0].lstrip())
    out_lines = []
    for i, line in enumerate(lines):
        if len(line) < indent:
            if len(line.strip()) == 0:
                out_lines.append("")
                continue
            else:
                raise Exception(
                    f"Inconsistent indentation in code block at line {i+1}:\n"
                    + "-" * 80
                    + "\n"
                    + code
                    + "\n"
                    + "-" * 80
                )
        if line[:indent] == " " * indent:
            out_lines.append(line[indent:])
        else:
            raise Exception(
                f"Inconsistent indentation in code block at line {i+1}:\n"
                + "-" * 80
                + "\n"
                + code
                + "\n"
                + "-" * 80
            )
    return "\n".join(out_lines)


def check_format():
    if md.TARGET_FORMAT is None:
        # read format from metadata file
        with METADATA_FILE.open("r") as f:
            metadata = json.load(f)
            if 'format' not in metadata:
                logging.warning("No format specified in metadata file. Defaulting to markdown.")
                md.TARGET_FORMAT = Format.MARKDOWN
                return
            md.TARGET_FORMAT = metadata['format']
            md.TARGET_FORMAT = Format[md.TARGET_FORMAT.upper()]
            tex.TARGET_FORMAT = md.TARGET_FORMAT
    if md.TARGET_FORMAT not in Format:
        raise ValueError(f"Invalid format: {md.TARGET_FORMAT}")
    logging.info(f"Using format: {md.TARGET_FORMAT}")
    # md.TARGET_FORMAT = Format[md.TARGET_FORMAT.upper()]

def capture_output(code):
    """Captures the output of the code execution.

    Args:
        code: The Python code string to be executed.

    Returns:
        The captured output as a string.
    """
    check_format()

    code = deindent(code)
    logging.debug("Running code:\n" + code)
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    try:
        exec(code, globals())
    except Exception as e:
        logging.exception(e)
        sys.stdout = old_stdout
        raise e
    finally:
        sys.stdout = old_stdout

    out = new_stdout.getvalue()
    # strip a single newline from the end of the output
    if out.endswith("\n"):
        out = out[:-1]
    # if out.startswith("\n"):
    #     out = out[1:]
    return out


def capture_value(code):
    """Captures the return value of the code evaluation.

    Args:
        code: The Python code string to be executed.

    Returns:
        The captured output as an object.
    """
    check_format()

    code = deindent(code)
    logging.debug(f"Evaluating code:\n" + code)
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    try:
        output = eval(code, globals())
    except Exception as e:
        logging.exception(e)
        sys.stdout = old_stdout
        raise e
    finally:
        sys.stdout = old_stdout
    return output




def find_open_port() -> int:
    """Finds an available port by attempting to create a socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def save_metadata(port: int) -> None:
    """Saves the assigned port to a metadata file."""
    metadata: Dict[str, int] = {"port": port}
    with METADATA_FILE.open("w") as f:
        json.dump(metadata, f, indent=4)

def send_response(connection: socket.socket, message: str | Dict, message_type: str) -> None:
    """Sends a JSON-encoded response to the client."""
    response: str = json.dumps({'message': message, 'type': message_type})
    connection.sendall(response.encode('utf-8'))

def ping_handler(connection: socket.socket, message: Dict) -> bool:
    """Handles a ping request from the client."""
    send_response(connection, 'pong', 'ping')
    return True

def shutdown_handler(connection: socket.socket, message: Dict) -> bool:
    """Handles a shutdown request from the client."""
    logging.info("Received shutdown signal. Shutting down server.")
    send_response(connection, 'Shutting down server.', 'shutdown')
    return False

def string_handler(connection: socket.socket, message: Dict) -> bool:
    """Handles a string request from the client."""
    logging.debug("Received string request:\n" + message['message'])
    try:
        # Yes, this is supremely stupid, but should only ever be connected to from the local machine anyway.
        output = capture_output(message['message'])
    except Exception as e:
        send_response(connection, f"Error: {e}", 'error')
        return True
    send_response(connection, output, 'string')
    return True

def object_handler(connection: socket.socket, message: Dict) -> bool:
    """Handles an object request from the client."""
    try:
        output = capture_value(message['message'])
    except Exception as e:
        logging.error(e)
        send_response(connection, f"Error: {e}", 'error')
        return True
    if isinstance(output, tex.Token):
        output = md.inline_math(output)
    if isinstance(output, panflute.Element):
        output = output.to_json()
        logging.debug("Received object request:\n" + message['message'])
        logging.debug(f"Output here: \n{json.dumps(output, indent = 2)}")
    elif isinstance(output, list) and len(output) == 1 and isinstance(output[0], panflute.Element):
        output = output[0].to_json()
        logging.debug("Received object request:\n" + message['message'])
        logging.debug(f"Output here: \n{json.dumps(output, indent = 2)}")
    else:
        raise ValueError(f"Unsupported object type: {type(output)}")
    send_response(connection, output, 'object')
    return True

def file_handler(connection: socket.socket, message: Dict) -> bool:
    """Handles a file request from the client. The file is read and the contents executed."""
    logging.debug("Received file request:\n" + message['message'])
    try:
        with open(message['message'], 'r') as f:
            code = f.read()
        output = capture_output(code)
    except FileNotFoundError:
        send_response(connection, f"File not found: {message['message']}", 'error')
        return True
    except Exception as e:
        send_response(connection, f"Error: {e}", 'error')
        return True
    send_response(connection, output, 'string')
    return True

handlers = {
    "ping": ping_handler,
    "shutdown": shutdown_handler,
    "string": string_handler,
    "object": object_handler,
    "file": file_handler
}


def handle_client(connection: socket.socket, listening: threading) -> None:
    """Handles communication with a connected client."""
    data: bytes = connection.recv(16384)
    if not data:
        return False
    try:
        message: Dict[str, str] = json.loads(data.decode('utf-8'))
        logging.debug(f"Received message of type: {message['type']}")
        continue_listening = handlers[message['type']](connection, message)
    except json.JSONDecodeError:
        send_response(connection, "Invalid JSON", "error")
        continue_listening = True
    except KeyError:
        send_response(connection, f"Invalid message type `{message['type']}`", "error")
        continue_listening = True
    except Exception as e:
        send_response(connection, f"Error: {e}", "error")
        continue_listening = True
    finally:
        connection.close()
        if not continue_listening:
            listening.set()
            

time_per_request = 0.1

def main() -> None:
    """Main server function."""
    port: int = find_open_port()
    save_metadata(port)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, port))
        server_socket.listen(1)

        logging.info(f'Server listening on {HOST}:{port}')

        listening = threading.Event()

        timeouts = MAX_TIMEOUT / time_per_request # there's definitely a better way to do this, but this works even when we're dispatching new threads to handle clients
        while not listening.is_set():
            while timeouts > 0:
                if listening.is_set():
                    break
                try:
                    server_socket.settimeout(time_per_request)
                    conn: socket.socket
                    addr: tuple[str, int]
                    conn, addr = server_socket.accept()

                    if addr[0] != HOST:
                        logging.warning(f"Connection from {addr[0]} refused.")
                        continue

                    # Create a new thread to handle the client
                    client_thread = threading.Thread(target=handle_client, args=(conn,listening))
                    logging.info(f"Starting new thread to handle client from {addr}")
                    client_thread.start()  
                    timeouts = MAX_TIMEOUT / time_per_request
                except socket.timeout:
                    timeouts -= 1
                    continue
                except Exception as e:
                    logging.error(f"Error: {e}")
                    timeouts = MAX_TIMEOUT / time_per_request
            if not listening.is_set():
                logging.info("Server timed out. Shutting down.")
                break
        if listening.is_set():
            logging.info("Server shutting down due to shutdown signal")
        logging.debug(f"Timeouts: {MAX_TIMEOUT - timeouts * time_per_request:.2f}s of {MAX_TIMEOUT}s")


if __name__ == "__main__":
    main()
