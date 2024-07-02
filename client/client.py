"""DNCI Client: Communication interface
Usage: client [--help|--version]
       client [options] [-s server] [-u username]

Options:
-h, --help      Show this help message.
--version       Show version information.
-s, --server    Specify server IP address.
-u, --username  Specify username to login with.
"""

##    dnci.client.client - client for communication interface
##    Copyright (C) 2024 Oliver Nguyen
##
##    This file is part of dnci.
##
##    dnci is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import getpass
import hashlib
import json
import logging
import logging.config
import time
import threading
import socket
import sys

import zmq

from __init__ import *

MESSAGE_FORMAT = "{time} {sender}@{sender_ip}: {message}"
NOTICE = """DNCI Copyright (C) 2024 Oliver Nguyen
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c` for details."""

def get_client_ip() -> str:
    """Returns the IP address of the client."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def display_license_pages(license_pages: list) -> None:
    """Displays specified license pages."""
    for page in license_pages:
        with open(f"legal/license.{page}.txt", "r") as f:
            print(f.read())
            input(f"Press [ENTER] to continue...")

def setup_zmq_sockets(server_ip: str) -> dict:
    """Sets up ZMQ sockets to connect to the server.
    The client initializes a ZMQ context and then creates a REQ socket
    for login, a PUSH socket for sending messages, and a SUB socket
    for receiving messages.
    """
    login_socket_address = f"tcp://{server_ip}:5555"
    send_socket_address = f"tcp://{server_ip}:5557"
    receive_socket_address = f"tcp://{server_ip}:5556"

    context = zmq.Context()
    logger.info(f"Initialized zmq context")

    # REQ socket for login/logout
    login_socket = context.socket(zmq.REQ)
    login_socket.connect(login_socket_address)
    logger.info(f"Connected login socket to {login_socket_address}")

    # PUSH socket for sending messages
    send_socket = context.socket(zmq.PUSH)
    send_socket.connect(send_socket_address)
    logger.info(f"Connected send socket to {send_socket_address}")

    # SUB socket for receiving messages
    receive_socket = context.socket(zmq.SUB)
    receive_socket.connect(receive_socket_address)
    logger.info(f"Connected receive socket to {receive_socket_address}")
    receive_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    return {"login_socket": login_socket,
            "send_socket": send_socket,
            "receive_socket": receive_socket}

# Receive messages from server
def receive_messages():
    """Receive messages from the server.
    When a message is received from the server on the receive socket,
    it deserializes the JSON representation of the message, formats
    the message and prints it to stdout.
    """

    while True:
        message_json = receive_socket.recv_string()
        logging.info("Received message from server")
        message_data = json.loads(message_json)
        formatted_message = MESSAGE_FORMAT.format(
            time=message_data['time'],
            sender=message_data['sender'],
            sender_ip=message_data['sender_ip'],
            message=message_data['message']
        )
        print("\n"+formatted_message)
        logging.info("Printed message")

# Send a message
def send_message(username: str, msg: str) -> None:
    """Sends a message to the server.
    The client adds a timestamp to the message. The message data is
    stored in a dict. It then serializes the message into a JSON
    representation and sends it to the server on the send socket.
    """

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    message_data = {
        "type": "MESSAGE",
        "message": msg,
        "sender": username,
        "sender_ip": get_client_ip(),
        "time": timestamp
    }
    message_json = json.dumps(message_data)
    send_socket.send_string(message_json)
    logger.info("Sent message to server")

def display_initial_messages(messages: list) -> None:
    """Displays initial messages from the server."""
    print("Last 10 messages on server:")
    for message_data in messages:
        formatted_message = MESSAGE_FORMAT.format(
            time=message_data['time'],
            sender=message_data['sender'],
            sender_ip=message_data['sender_ip'],
            message=message_data['message']
        )
        print(formatted_message)

def login(username: str, password_hash: str) -> dict:
    """Logs in the user.
    The client requests a username and password from the user. It then
    hashes the password and sends the username and password to the
    server on the login socket.
    The client then receives a response from the server. If the
    response status is successful, the user can access the application.
    """

    login_socket.send_json({"type": "LOGIN", "username": username, "password": password_hash})
    logger.info("Login request sent to server")
    response = login_socket.recv_json()
    logger.info(f"Response from server received: {response}")
    return response

def main_loop(username: str):
    """Main loop for the client.
    The client starts a background task to receive messages from the
    server.
    It then displays a prompt to the user. If the user types `send`,
    the client requests the message from the user and then sends it.
    If the user types `logout`, the client logs out the user.
    """

    # Start a background task to receive messages
    threading.Thread(target=receive_messages, daemon=True).start()
    logger.info("Started background task to receive messages")

    while True:
        cmd = input(f"dnci:{username}@{get_client_ip()}> ")
        if cmd == "logout":
            break
        elif cmd == "help":
            print("DNCI commands:")
            print("help    Displays this help message.")
            print("logout  Logs the user out.")
            print("send    Sends a message to the server.")
        elif cmd == "send":
            msg = input("Enter message: ")
            send_message(username, msg)

# Start the client
def start_client():
    """Starts the client.
    The client attemps to log in the user. If the login is successful,
    the user can access the application.
    """

    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    password_hash = hashlib.md5(password.encode()).hexdigest()
    response = login(username, password_hash)

    if response['status'] == "success":
        print("Login successful\n")
        logger.info("Login successful")
        display_initial_messages(response.get("messages", []))
        print("Welcome to DNCI. Type `help` for help.")
        main_loop(username)
    else:
        print("Login failed")
        logger.error("Login failed")

if __name__ == "__main__":
    if ("-h" in sys.argv) or ("--help" in sys.argv):
        print(__doc__)
        exit()
    elif "--version" in sys.argv:
        print(f"DNCI Client v{version} [{internal_release_phase}; "
              f"{internal_release_date}]")
        exit()

    print(f"Welcome to DNCI Client v{version} "
          f"[{internal_release_phase}; {internal_release_date}]")

    logging.config.fileConfig('config/logging.conf')
    logger = logging.getLogger('client')

    logger.info("Starting client")
    logger.info(f"DNCI client version: {version}")

    print(NOTICE)

    command = "-"
    while command != "":
        command = input("Press [ENTER] to login or type a command...")
        if command == 'show w':
            license_pages = ["150", "160", "170"]
            display_license_pages(license_pages)
        elif command == 'show c':
            license_pages = ["040", "050", "051", "060", "061", "062",
                             "063", "070", "071", "072", "080", "081",
                             "090", "100"]
            display_license_pages(license_pages)

    if ("-s" not in sys.argv) and ("--server" not in sys.argv):
        server_ip = input("Server IP [type `localhost` to enter local dev mode]: ")
    else:
        index = sys.argv.index('-s')
        server_ip = sys.argv[index+1]

    sockets = setup_zmq_sockets(server_ip)
    login_socket = sockets["login_socket"]
    send_socket = sockets["send_socket"]
    receive_socket = sockets["receive_socket"]

    start_client()
