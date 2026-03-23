"""
Transparent Fernet encryption for data at rest.
If ENCRYPTION_KEY is set in the environment, all data written through
StructuredMemory, AuditLog, SessionStore, and CalendarTool will be
encrypted on disk. If unset, data remains plaintext (backward-compatible).
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("agentzero.encryption")

_cipher = None
_initialized = False


def _init_cipher():
    """Lazy-initialize the Fernet cipher from ENCRYPTION_KEY env var."""
    global _cipher, _initialized
    if _initialized:
        return
    _initialized = True

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        logger.info("ENCRYPTION_KEY not set — data at rest will NOT be encrypted.")
        return

    try:
        from cryptography.fernet import Fernet
        _cipher = Fernet(key.encode() if isinstance(key, str) else key)
        logger.info("Encryption at rest enabled (Fernet AES-128-CBC).")
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY: {e}. Data will NOT be encrypted.")
        _cipher = None


def get_cipher():
    """Returns the Fernet cipher instance, or None if encryption is disabled."""
    _init_cipher()
    return _cipher


def encrypt_data(plaintext: str) -> str:
    """
    Encrypt a string. Returns the Fernet token (base64) if encryption is
    enabled, otherwise returns the original string unchanged.
    """
    cipher = get_cipher()
    if cipher is None:
        return plaintext
    try:
        return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext


def decrypt_data(data: str) -> str:
    """
    Decrypt a string. Auto-detects whether the data is encrypted:
    - If encryption is disabled, returns as-is.
    - If data looks like a Fernet token, decrypts it.
    - If data is plaintext (e.g. legacy unencrypted file), returns as-is.
    """
    cipher = get_cipher()
    if cipher is None:
        return data

    # Fernet tokens are base64-encoded and start with 'gAAAAA'
    if not data or not _is_fernet_token(data):
        return data  # plaintext passthrough

    try:
        return cipher.decrypt(data.encode("utf-8")).decode("utf-8")
    except Exception:
        # If decryption fails, it's likely plaintext from before encryption was enabled
        return data


def _is_fernet_token(data: str) -> bool:
    """
    Heuristic check: Fernet tokens are base64-encoded, typically start with
    'gAAAAA' and are at least 100 chars long. This avoids false positives
    on short JSON strings like '{}' or '[]'.
    """
    return len(data) > 80 and data.startswith("gAAAAA")
