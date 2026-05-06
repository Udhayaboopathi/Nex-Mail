import base64
import hashlib
from cryptography.fernet import Fernet
from backend.config import settings

def _fernet() -> Fernet:
    seed = hashlib.sha256(settings.encryption_secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(seed)
    return Fernet(key)

def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()

def decrypt_text(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
