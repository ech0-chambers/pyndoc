import json
import logging
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Dict

HOST = "127.0.0.1"
MESSAGE_SIZE = 16384
METADATA_FILE = Path(".pyndoc.json")

def send_request(connection: socket.socket, message: str | Dict, message_type: str) -> None:
    """Sends a JSON-encoded request to the server."""
    request: str = json.dumps({'message': message, 'type': message_type})
    connection.sendall(request.encode('utf-8'))


def ping_server(port: int, timeout: int = 5) -> bool:
    """Pings the server to check if it is running."""
    try:
        response = create_socket_and_send_request(port, 'ping', 'ping', timeout=timeout)
        response = json.loads(response)
        return response["message"] == 'pong'
    except ConnectionRefusedError:
        return False
    except Exception as e:
        logging.error(e)
        return False
    

def create_socket_and_send_request(port: int, message: str | Dict, message_type: str, timeout: int = 5) -> str:
    """Creates a socket, sends a request to the server, and returns the response."""
    # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #     s.connect((HOST, port))
    #     send_request(s, message, message_type)
    #     response = s.recv(MESSAGE_SIZE).decode('utf-8')
    #     return response
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((HOST, port))
        send_request(s, message, message_type)
        response = s.recv(MESSAGE_SIZE).decode('utf-8')
        return response


def get_active_server() -> int | None:
    """Returns the port of the active server, or None if no server is running."""
    if METADATA_FILE.exists():
        logging.debug("Metadata file exists. Reading...")
        with METADATA_FILE.open('r') as f:
            metadata = json.load(f)
        logging.debug(f"Metadata: {metadata}")
        port = metadata.get('port', None)
        if port is not None:
            logging.debug(f"Attempting to ping server on port {port}...")
            if ping_server(port):
                logging.debug(f"Server is running on port {port}.")
                return port
            else:
                logging.warning(f"Metadata file exists, but server is not responding on port {port}.")
    return None

def get_or_start_server() -> int:
    """Returns the port of the active server, starting it if necessary."""
    port = get_active_server()
    if port is None:
        port = start_server()
        with METADATA_FILE.open('w') as f:
            json.dump({'port': port}, f, indent=4)
    return port

def start_server() -> int:
    """Starts the server and returns the assigned port."""
    retries = 50
    delay = 0.01
    server_file = Path(__file__).parent / "server.py"
    # start server, without blocking the main process
    subprocess.Popen([sys.executable, str(server_file)])
    for i in range(retries):
        port = get_active_server()
        if port is not None:
            return port
        logging.debug(f"Attempt {i+1}: Waiting for server to start...")
        time.sleep(delay)
    raise RuntimeError(f"Failed to start server, or failed to read metadata file after {retries * delay:.2f}s")

def stop_server(port: int) -> None:
    """Stops the server."""
    if port is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, port))
            send_request(s, 'shutdown', 'shutdown')
            s.recv(MESSAGE_SIZE).decode('utf-8')