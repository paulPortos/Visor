import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import env


class SettingsEnvironmentTests(SimpleTestCase):
    def test_secret_files_support_commands_executed_in_running_containers(self):
        with TemporaryDirectory() as directory:
            key_file = Path(directory, 'key')
            key_file.write_text('persisted-key\n')
            for raw_value in (None, ''):
                with self.subTest(raw_value=raw_value):
                    variables = {'DOCKER_TEST_SECRET_FILE': str(key_file)}
                    if raw_value is not None:
                        variables['DOCKER_TEST_SECRET'] = raw_value
                    with patch.dict(os.environ, variables, clear=True):
                        self.assertEqual(env('DOCKER_TEST_SECRET', required=True), 'persisted-key')

    def test_explicit_values_take_precedence_over_secret_files(self):
        with patch.dict(os.environ, {
            'DOCKER_TEST_SECRET': 'explicit-key',
            'DOCKER_TEST_SECRET_FILE': '/missing-file',
        }, clear=True):
            self.assertEqual(env('DOCKER_TEST_SECRET', required=True), 'explicit-key')

    def test_missing_secret_file_fails_clearly(self):
        with patch.dict(os.environ, {'DOCKER_TEST_SECRET_FILE': '/missing-file'}, clear=True):
            with self.assertRaisesRegex(ImproperlyConfigured, 'Cannot read DOCKER_TEST_SECRET_FILE'):
                env('DOCKER_TEST_SECRET', required=True)

    def test_missing_required_values_still_fail(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ImproperlyConfigured, 'DOCKER_TEST_SECRET is required'):
                env('DOCKER_TEST_SECRET', required=True)
