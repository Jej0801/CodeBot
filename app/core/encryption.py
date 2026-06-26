"""
Token encryption utilities for secure storage of OAuth tokens.

This module provides encryption/decryption for GitHub OAuth tokens
using Fernet symmetric encryption (AES-128 in CBC mode with PKCS7 padding).

Security considerations:
- Encryption key must be stored in environment variables
- Keys should be rotated periodically
- Never log or expose decrypted tokens
"""

from cryptography.fernet import Fernet
from functools import lru_cache
import base64
from typing import Optional


@lru_cache()
def get_encryption_key() -> bytes:
    """
    Get encryption key from environment.

    Cached to avoid repeated environment lookups.
    Key must be 32 url-safe base64-encoded bytes.

    Returns:
        bytes: Fernet encryption key

    Raises:
        ValueError: If ENCRYPTION_KEY not set in environment
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not hasattr(settings, 'encryption_key') or not settings.encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY not configured. Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    # Convert string key to bytes
    key = settings.encryption_key
    if isinstance(key, str):
        key = key.encode()

    return key


def encrypt_token(plaintext_token: Optional[str]) -> Optional[str]:
    """
    Encrypt a plaintext token for secure storage.

    Args:
        plaintext_token: The token to encrypt (e.g., GitHub OAuth token)

    Returns:
        Encrypted token as base64 string, or None if input is None

    Example:
        >>> token = "ghp_abc123xyz"
        >>> encrypted = encrypt_token(token)
        >>> print(encrypted)  # "gAAAA..."
    """
    if plaintext_token is None:
        return None

    if not isinstance(plaintext_token, str):
        raise TypeError("Token must be a string")

    if not plaintext_token.strip():
        return None

    fernet = Fernet(get_encryption_key())
    encrypted_bytes = fernet.encrypt(plaintext_token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """
    Decrypt an encrypted token for use in API calls.

    Args:
        encrypted_token: The encrypted token from database

    Returns:
        Decrypted plaintext token, or None if input is None

    Raises:
        cryptography.fernet.InvalidToken: If token is corrupted or key is wrong

    Example:
        >>> encrypted = "gAAAA..."
        >>> token = decrypt_token(encrypted)
        >>> # Use token to call GitHub API
    """
    if encrypted_token is None:
        return None

    if not isinstance(encrypted_token, str):
        raise TypeError("Encrypted token must be a string")

    if not encrypted_token.strip():
        return None

    fernet = Fernet(get_encryption_key())
    decrypted_bytes = fernet.decrypt(encrypted_token.encode())
    return decrypted_bytes.decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to generate a key for your .env file:

    Returns:
        A new encryption key as a string

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode()


# Validation helper
def is_valid_encryption_key(key: str) -> bool:
    """
    Check if a string is a valid Fernet encryption key.

    Args:
        key: The key to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        if isinstance(key, str):
            key = key.encode()
        Fernet(key)
        return True
    except Exception:
        return False
