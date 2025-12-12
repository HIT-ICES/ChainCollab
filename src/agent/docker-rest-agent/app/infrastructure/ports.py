import socket
from contextlib import closing

from ..utils import ValidationError


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def get_available_ports(port_number: int):
    if port_number <= 0:
        raise ValidationError("port_number must be positive")
    available_ports = []
    port = 1024
    while len(available_ports) < port_number and port < 65535:
        if is_port_available(port):
            available_ports.append(port)
        port += 1
    return available_ports
