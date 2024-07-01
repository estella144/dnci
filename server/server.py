"""DNCI Server: Communication interface
Usage: server [--help|--version]
       server [options]

Options:
-h, --help      Show this help message.
--version       Show version information.
"""

##    dnci.server.server - server for communication interface
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

import hashlib
import json
import logging
import logging.config
import os
import time
import threading
import socket
import sys

import zmq

from __init__ import *

NOTICE = """DNCI Copyright (C) 2024 Oliver Nguyen
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c` for details."""

login_socket_address = "tcp://*:5555"
receive_socket_address = "tcp://*:5557"
message_socket_address = "tcp://*:5556"

def get_server_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

# Function to load users from a JSON file
def load_users(filename='data/users.json'):
    """Loads users from a JSON file."""
    with open(filename, 'r') as file:
        users = json.load(file)
    logger.info("Users loaded")
    return users

# Function to load messages from a JSON file
def load_messages(filename='data/messages.json'):
    """Loads messages from a JSON file."""
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        logger.info("Messages loaded")
    else:
        data = {"messages": []}
        logger.warning("Could not find messages file")
    return data

# Function to save messages to a JSON file
def save_messages(messages, filename='data/messages.json'):
    """Saves messages to a JSON file."""
    with open(filename, 'w') as file:
        json.dump(messages, file, indent=4)
    logger.info(f"Saved messages to {filename}")

# Handle client logins
def handle_login():
    """Handles client logins.
    When the server receives a login message from the client on the
    login socket, it checks if the username is in the list of users and
    if the password hash sent matches the password hash corresponding
    to the user.
    If this check is successful, the server sends a successful login
    message to the client on the login socket.
    Otherwise, the server sends a failed login message to the client on
    the login socket.
    """

    while True:
        message = login_socket.recv_json()
        if message['type'] == "LOGIN":
            username = message['username']
            password_hash = message['password']
            logger.info(f"User {username} attempted to login")
            if username in USERS and USERS[username] == password_hash:
                login_socket.send_json({"status": "success"})
                logger.info(f"User {username} logged in successfully")
            else:
                login_socket.send_json({"status": "fail"})
                logger.info(f"User {username} failed to login")

# Receive and broadcast messages
def handle_messages():
    """Receives and broadcasts messages.
    When the server receives a message from the client on the receive
    socket, it deserializes the JSON representation of the message and
    formats the message with a timestamp.
    The server then reserializes the message into a JSON representation
    and adds the message to the messages file.
    The server then broadcasts the message to all clients on the
    message socket.
    """

    while True:
        message_json = receive_socket.recv_string()
        logger.info("Received message")
        message_data = json.loads(message_json)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        message_data['time'] = timestamp
        formatted_message_json = json.dumps(message_data)

        # Append to the messages list and save to file
        messages['messages'].append(message_data)
        save_messages(messages)

        # Broadcast the message to all clients
        message_socket.send_string(formatted_message_json)
        logger.info("Broadcasted message to all clients")

# Main server loop
def run_server():
    """Main server loop.
    Creates a login thread and a message handling thread.
    """
    logger.info(f"Starting server on IP address {get_server_ip()}")
    login_thread = threading.Thread(target=handle_login)
    login_thread.start()
    logger.info("Login thread started")
    message_thread = threading.Thread(target=handle_messages)
    message_thread.start()
    logger.info("Message thread started")
    login_thread.join()
    logger.info("Login thread joined")
    message_thread.join()
    logger.info("Message thread joined")

if __name__ == "__main__":
    if ("-h" in sys.argv) or ("--help" in sys.argv):
        print(__doc__)
        exit()
    elif "--version" in sys.argv:
        print(f"DNCI Server v{__version__} [{internal_release_phase}; "
              f"{internal_release_date}]")
        exit()

    print(f"Welcome to DNCI Server v{version} "
          f"[{internal_release_phase}; {internal_release_date}]\n")

    print(NOTICE)

    logging.config.fileConfig('config/logging.verbose.conf')
    logger = logging.getLogger('server')

    logger.info("Starting server")
    logger.info(f"DNCI server version: {version}")

    command = "-"
    while command != "":
        command = input("\nPress [ENTER] to start or type a command...")
        if command == 'show w':
            license_pages = ["150", "160", "170"]
            display_license_pages(license_pages)
        elif command == 'show c':
            license_pages = ["040", "050", "051", "060", "061", "062",
                             "063", "070", "071", "072", "080", "081",
                             "090", "100"]
            display_license_pages(license_pages)

    # Initialize ZeroMQ context
    context = zmq.Context()
    logger.info('Initialized zmq context')

    # Set up REP socket for login/logout
    login_socket = context.socket(zmq.REP)
    login_socket.bind(login_socket_address)
    logger.info(f"Binded login socket to {login_socket_address}")

    # Set up PULL socket for receiving messages from clients
    receive_socket = context.socket(zmq.PULL)
    receive_socket.bind(receive_socket_address)
    logger.info(f"Binded receive socket to {receive_socket_address}")

    # Set up PUB socket for message broadcasting
    message_socket = context.socket(zmq.PUB)
    message_socket.bind(message_socket_address)
    logger.info(f"Binded message socket to {message_socket_address}")

    # Load users
    USERS = load_users()

    # Load existing messages
    messages = load_messages()

    run_server()
