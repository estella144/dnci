import getpass
import hashlib
import json
import logging
import logging.config
import time
import threading
import socket

import zmq

MESSAGE_FORMAT = "{time} {sender}@{sender_ip}: {message}"

def get_client_ip():
    """Returns the IP address of the client."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

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
def send_message(username, msg):
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
    logging.info("Sent message to server")

def login(username, password_hash):
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

def main_loop(username):
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
        print("Login successful")
        logger.info("Login successful")
        main_loop(username)
    else:
        print("Login failed")
        logger.error("Login failed")

if __name__ == "__main__":
    print("Welcome to DNCI v0.1")
    server_ip = input("Server IP [type `localhost` to enter dev mode]: ")
    login_socket_address = f"tcp://{server_ip}:5555"
    send_socket_address = f"tcp://{server_ip}:5557"
    receive_socket_address = f"tcp://{server_ip}:5556"

    logging.config.fileConfig('config/logging.conf')
    logger = logging.getLogger('client')

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

    start_client()
