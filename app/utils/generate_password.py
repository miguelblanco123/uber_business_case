"""
Generate a bcrypt password hash for use in assets/config.yaml.

Usage:
    python generate_password.py
"""

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


if __name__ == "__main__":
    plain = input("Password: ")
    print(hash_password(plain))
