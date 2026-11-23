import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess

from cryptography.fernet import Fernet
from django.test import SimpleTestCase

from scripts.docker_entrypoint import main


class DockerEntrypointTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'VISOR_STATE_DIR': self.directory.name}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.exec_mock = patch('scripts.docker_entrypoint.os.execvp').start()
        self.migrate_mock = patch('scripts.docker_entrypoint.subprocess.run').start()
        self.addCleanup(patch.stopall)

    def test_generated_keys_remain_stable_across_restarts(self):
        with patch('sys.argv', ['entrypoint', 'python', 'manage.py', 'check']):
            main()
        first_secret = os.environ.pop('DJANGO_SECRET_KEY')
        first_encryption_key = os.environ.pop('GITHUB_TOKEN_ENCRYPTION_KEY')
        Fernet(first_encryption_key.encode())

        with patch('sys.argv', ['entrypoint', 'python', 'manage.py', 'check']):
            main()
        self.assertEqual(os.environ['DJANGO_SECRET_KEY'], first_secret)
        self.assertEqual(os.environ['GITHUB_TOKEN_ENCRYPTION_KEY'], first_encryption_key)
        for key_file in Path(self.directory.name).iterdir():
            self.assertEqual(key_file.stat().st_mode & 0o777, 0o600)

    def test_supplied_keys_are_preserved(self):
        existing_key = Fernet.generate_key().decode()
        os.environ.update(DJANGO_SECRET_KEY='existing-secret', GITHUB_TOKEN_ENCRYPTION_KEY=existing_key)
        with patch('sys.argv', ['entrypoint', 'python', 'manage.py', 'check']):
            main()
        self.assertEqual(os.environ['DJANGO_SECRET_KEY'], 'existing-secret')
        self.assertEqual(os.environ['GITHUB_TOKEN_ENCRYPTION_KEY'], existing_key)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_empty_persisted_key_is_not_silently_replaced(self):
        Path(self.directory.name, 'django_secret_key').touch()
        with patch('sys.argv', ['entrypoint', 'python', 'manage.py', 'check']):
            with self.assertRaisesRegex(RuntimeError, 'Persisted DJANGO_SECRET_KEY is empty'):
                main()
        self.exec_mock.assert_not_called()

    def test_default_server_runs_migrations_before_launch(self):
        command = ['python', '-m', 'daphne', '-b', '0.0.0.0', '-p', '8000', 'config.asgi:application']
        with patch('sys.argv', ['entrypoint', *command]):
            main()
        self.migrate_mock.assert_called_once()
        self.assertEqual(self.migrate_mock.call_args.args[0][1:], ['manage.py', 'migrate', '--noinput'])
        self.assertTrue(self.migrate_mock.call_args.kwargs['check'])
        self.exec_mock.assert_called_once_with('python', command)

    def test_failed_migration_prevents_server_start(self):
        self.migrate_mock.side_effect = subprocess.CalledProcessError(1, ['migrate'])
        with patch('sys.argv', ['entrypoint', 'python', '-m', 'daphne']):
            with self.assertRaises(subprocess.CalledProcessError):
                main()
        self.exec_mock.assert_not_called()

    def test_management_commands_do_not_migrate_the_application_database(self):
        command = ['python', 'manage.py', 'test', '--noinput']
        with patch('sys.argv', ['entrypoint', *command]):
            main()
        self.migrate_mock.assert_not_called()
        self.exec_mock.assert_called_once_with('python', command)
