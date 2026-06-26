#!/usr/bin/env python3
"""
Script to generate a Fernet encryption key for token encryption.

Usage:
    python scripts/generate_encryption_key.py

This will output a key that you can add to your .env file:
    ENCRYPTION_KEY=<generated_key>
"""

from cryptography.fernet import Fernet


def main():
    key = Fernet.generate_key().decode()

    print("=" * 70)
    print("Generated Encryption Key for CodeBot")
    print("=" * 70)
    print()
    print("Add this to your .env file:")
    print()
    print(f"ENCRYPTION_KEY={key}")
    print()
    print("=" * 70)
    print("IMPORTANT: Keep this key secret!")
    print("- Never commit it to version control")
    print("- Store it securely (password manager, secrets vault)")
    print("- If leaked, rotate immediately and re-encrypt all tokens")
    print("=" * 70)


if __name__ == "__main__":
    main()
