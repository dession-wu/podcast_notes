"""Local protected credentials. No plaintext credential is returned to clients."""
import ctypes
import os
from pathlib import Path
from cryptography.fernet import Fernet


def windows_protect(value, decrypt=False):
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    output = Blob()
    api = ctypes.windll.crypt32
    if decrypt:
        ok = api.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output))
    else:
        ok = api.CryptProtectData(ctypes.byref(source), None, None, None, None, 4, ctypes.byref(output))
    if not ok:
        raise RuntimeError('无法读取本机加密凭据')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)


class KeyBox:
    def __init__(self, folder):
        self.folder = Path(folder)

    def _fernet(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        key = self.folder / 'ai-encryption.key'
        if not key.exists():
            try:
                with key.open('xb') as stream:
                    stream.write(Fernet.generate_key())
                key.chmod(0o600)
            except FileExistsError:
                pass
        return Fernet(key.read_bytes())

    def encrypt(self, value):
        import base64
        if os.name == 'nt':
            return 'dpapi:' + base64.b64encode(windows_protect(value.encode())).decode()
        return 'fernet:' + self._fernet().encrypt(value.encode()).decode()

    def decrypt(self, value):
        import base64
        if value.startswith('dpapi:'):
            return windows_protect(base64.b64decode(value[6:]), True).decode()
        return self._fernet().decrypt(value.removeprefix('fernet:').encode()).decode()


def platform_key(default_file):
    key = os.getenv('BAILIAN_API_KEY', '').strip()
    if key:
        return key
    path = Path(os.getenv('BAILIAN_API_KEY_FILE') or default_file)
    if not path.is_file():
        return ''
    if os.name != 'nt':
        return path.read_text(encoding='utf-8').strip()
    return windows_protect(path.read_bytes(), True).decode().strip()
