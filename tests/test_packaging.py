"""Zero-network smoke tests for distributable package and URL safety."""
import unittest
from pathlib import Path
from liveclip import __version__
from liveclip.cli import build_parser
from liveclip.capture import validate_url

class PackagingTests(unittest.TestCase):
    def test_version_and_commands(self):
        self.assertEqual(__version__, '2.4.0')
        for command in ('doctor', 'record', 'analyze'):
            self.assertIsNotNone(build_parser()._subparsers._actions)
        self.assertEqual(build_parser().parse_args(['doctor']).action, 'doctor')

    def test_reject_unsafe_url_inputs(self):
        for value in (
            'file:///etc/passwd', 'https://alice:pw@host.invalid/live',
            'http://127.0.0.2/video', 'http://10.0.0.1/video',
            'http://192.168.1.3/video', 'http://[::1]:1234/',
            'http://localhost./', 'http://x.localhost/',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_url(value)
        self.assertEqual(validate_url('https://example.com/live'), 'https://example.com/live')
