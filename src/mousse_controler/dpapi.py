"""Current-user DPAPI helpers; plaintext secrets never need to enter config files."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB),
    wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptProtectData.restype = wintypes.BOOL
crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(DATA_BLOB),
    wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptUnprotectData.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
kernel32.LocalFree.restype = wintypes.HLOCAL


def _blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    storage = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(storage, ctypes.POINTER(ctypes.c_ubyte))), storage


def _call(function, data: bytes) -> bytes:
    incoming, storage = _blob(data)
    outgoing = DATA_BLOB()
    if not function(ctypes.byref(incoming), None, None, None, None, 0, ctypes.byref(outgoing)):
        raise OSError(ctypes.get_last_error(), "DPAPI operation failed")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(outgoing.pbData, wintypes.HLOCAL))


def protect(secret: bytes) -> str:
    return base64.b64encode(_call(crypt32.CryptProtectData, secret)).decode("ascii")


def unprotect(value: str) -> bytes:
    return _call(crypt32.CryptUnprotectData, base64.b64decode(value, validate=True))
