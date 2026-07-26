"""protocol — ramkowanie wiadomości klient<->serwer groundera (czyste stdlib).

Działa w OBU środowiskach (.venv i .venv_s3b0). Ramka: 8 bajtów (len_header,
len_blob) big-endian + header JSON + surowy blob (klatka 256^2 uint8). Bez
picklowania numpy (niezależne od wersji numpy między venvami).
"""
from __future__ import annotations

import json
import struct


def _readn(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            raise ConnectionError("połączenie zamknięte")
        buf += c
    return buf


def send_msg(sock, header: dict, blob: bytes = b"") -> None:
    hj = json.dumps(header).encode()
    sock.sendall(struct.pack(">II", len(hj), len(blob)) + hj + blob)


def recv_msg(sock):
    hh = _readn(sock, 8)
    hl, bl = struct.unpack(">II", hh)
    header = json.loads(_readn(sock, hl).decode())
    blob = _readn(sock, bl)
    return header, blob
