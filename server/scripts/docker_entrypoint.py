"""Initialize persistent application keys, migrate, and launch the container command."""

import os
from pathlib import Path
import secrets
import subprocess
import sys

from cryptography.fernet import Fernet


def main():
    state_dir = Path(os.environ.get('VISOR_STATE_DIR', '/var/lib/visor'))
    state_dir.mkdir(parents=True, exist_ok=True)

    for name, generate in (
        ('DJANGO_SECRET_KEY', lambda: secrets.token_urlsafe(64)),
        ('GITHUB_TOKEN_ENCRYPTION_KEY', lambda: Fernet.generate_key().decode()),
    ):
        if os.environ.get(name):
            continue
        key_path = Path(os.environ.get(f'{name}_FILE') or state_dir / name.lower())
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            value = key_path.read_text().strip()
            if not value:
                raise RuntimeError(f'Persisted {name} is empty; restore it before starting')
        else:
            value = generate()
            with os.fdopen(descriptor, 'w') as key_file:
                key_file.write(value)
        os.environ[name] = value

    command = sys.argv[1:]
    if not command:
        raise RuntimeError('No container command supplied')
    if command[:3] == ['python', '-m', 'daphne']:
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], check=True)
    os.execvp(command[0], command)


if __name__ == '__main__':
    main()
