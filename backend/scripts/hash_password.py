"""Imprime un hash bcrypt. No guarda la contraseña.

Dentro del contenedor:

    python scripts/hash_password.py
"""

from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> int:
    password = getpass.getpass("Contraseña: ")
    if len(password) < 6:
        print("La contraseña tiene que tener al menos 6 caracteres.", file=sys.stderr)
        return 1
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    print(hashed.decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
