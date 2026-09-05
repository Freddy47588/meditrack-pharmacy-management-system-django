import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class EnvironmentSettingsTests(SimpleTestCase):
    def load_settings(self, environment):
        # Never load a developer's .env or change the active Django settings.
        path = Path(__file__).resolve().parents[2] / 'meditrack_project' / 'settings.py'
        with patch.dict(os.environ, environment, clear=True), patch('dotenv.load_dotenv'):
            return runpy.run_path(str(path))

    def test_development_defaults_generate_a_nonempty_secret(self):
        first = self.load_settings({})
        second = self.load_settings({})
        self.assertTrue(first['DEBUG'])
        self.assertTrue(first['SECRET_KEY'])
        self.assertNotEqual(first['SECRET_KEY'], second['SECRET_KEY'])
        self.assertEqual(first['ALLOWED_HOSTS'], [])

    def test_environment_configures_secret_debug_and_hosts(self):
        config = self.load_settings({
            'DJANGO_SECRET_KEY': 'test-only-value', 'DJANGO_DEBUG': 'false',
            'DJANGO_ALLOWED_HOSTS': 'localhost, example.test, ,',
        })
        self.assertFalse(config['DEBUG'])
        self.assertEqual(config['SECRET_KEY'], 'test-only-value')
        self.assertEqual(config['ALLOWED_HOSTS'], ['localhost', 'example.test'])

    def test_production_requires_secret(self):
        with self.assertRaisesMessage(ImproperlyConfigured, 'Set DJANGO_SECRET_KEY'):
            self.load_settings({'DJANGO_DEBUG': 'false'})
