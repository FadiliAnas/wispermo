"""Tiny client that sends one command to the running app and prints the reply.

This is what the GNOME keyboard shortcut runs (with the "toggle" command).
"""
import socket
import sys

from .config import socket_path


def send(cmd: str) -> str:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(socket_path())
    except (FileNotFoundError, ConnectionRefusedError):
        return "error: WISPERMO is not running"
    with s:
        s.sendall(cmd.encode())
        return s.recv(256).decode(errors="replace").strip()


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "toggle"
    reply = send(cmd)
    print(reply)
    return 1 if reply.startswith("error") else 0


if __name__ == "__main__":
    sys.exit(main())
