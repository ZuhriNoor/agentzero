"""Tests for the encryption-at-rest module."""
import os
import json
import tempfile
import pytest
from unittest.mock import patch


def test_encrypt_decrypt_roundtrip():
    """Verify encrypt → decrypt returns the original data."""
    # Generate a real Fernet key for testing
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        # Force re-initialization
        import agentzero.encryption as enc
        enc._initialized = False
        enc._cipher = None

        plaintext = '{"tasks": [{"name": "Buy groceries"}]}'
        encrypted = enc.encrypt_data(plaintext)

        # Encrypted output should be different from plaintext
        assert encrypted != plaintext
        assert enc._is_fernet_token(encrypted)

        # Decrypt should return original
        decrypted = enc.decrypt_data(encrypted)
        assert decrypted == plaintext

    # Cleanup
    enc._initialized = False
    enc._cipher = None


def test_no_key_passthrough():
    """When ENCRYPTION_KEY is not set, data passes through unchanged."""
    with patch.dict(os.environ, {}, clear=False):
        # Remove ENCRYPTION_KEY if present
        os.environ.pop("ENCRYPTION_KEY", None)

        import agentzero.encryption as enc
        enc._initialized = False
        enc._cipher = None

        plaintext = '{"hello": "world"}'
        assert enc.encrypt_data(plaintext) == plaintext
        assert enc.decrypt_data(plaintext) == plaintext

    enc._initialized = False
    enc._cipher = None


def test_plaintext_passthrough_when_encrypted_enabled():
    """Existing plaintext data should be readable even after encryption is enabled."""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        import agentzero.encryption as enc
        enc._initialized = False
        enc._cipher = None

        # Simulate reading an old plaintext file
        old_plaintext = '{"legacy": true}'
        result = enc.decrypt_data(old_plaintext)
        assert result == old_plaintext  # Should pass through, not crash

    enc._initialized = False
    enc._cipher = None


def test_structured_memory_encrypted(tmp_path):
    """Verify StructuredMemory encrypts on save and decrypts on load."""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        import agentzero.encryption as enc
        enc._initialized = False
        enc._cipher = None

        from agentzero.memory import StructuredMemory

        file_path = str(tmp_path / "test_data.json")
        mem = StructuredMemory(file_path)

        # Save data
        test_data = {"tasks": [{"name": "Test task", "done": False}]}
        mem.save(test_data)

        # Raw file should be encrypted (not valid JSON)
        with open(file_path, 'r') as f:
            raw = f.read()
        assert raw.startswith("gAAAAA"), f"File should be encrypted, got: {raw[:50]}"

        # Load should return original data
        loaded = mem.load()
        assert loaded == test_data

    enc._initialized = False
    enc._cipher = None


def test_audit_log_encrypted(tmp_path):
    """Verify AuditLog encrypts each line.."""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        import agentzero.encryption as enc
        enc._initialized = False
        enc._cipher = None

        from agentzero.memory import AuditLog

        log_path = str(tmp_path / "audit.log")
        log = AuditLog(log_path)

        entry = {"action": "add_task", "user": "admin", "success": True}
        log.append(entry)

        # Raw file should be encrypted
        with open(log_path, 'r') as f:
            raw_line = f.readline().strip()
        assert raw_line.startswith("gAAAAA")

        # Read should decrypt
        entries = log.read_all()
        assert len(entries) == 1
        assert entries[0] == entry

    enc._initialized = False
    enc._cipher = None
