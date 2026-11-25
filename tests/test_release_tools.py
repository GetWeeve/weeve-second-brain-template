"""Manifest refresh must preserve the release allowlist and refuse secrets."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch
import audit
import manifest


class ReleaseToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'README.md').write_text('# Fictional template\n', encoding='utf-8')
        (self.root / 'release-manifest.json').write_text(json.dumps({'version': 1, 'files': {}}), encoding='utf-8')
        self.patch = patch.object(audit, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def run_manifest(self, *args):
        with redirect_stdout(io.StringIO()):
            return manifest.main(args)

    def test_manifest_previews_refreshes_and_checks_without_self_hash(self):
        self.assertEqual(self.run_manifest(), 1)
        self.assertEqual(self.run_manifest('--refresh'), 0)
        self.assertEqual(self.run_manifest(), 0)
        value = json.loads((self.root / 'release-manifest.json').read_text(encoding='utf-8'))
        self.assertNotIn('release-manifest.json', value['files'])
        self.assertIn('README.md', value['files'])
        (self.root / 'README.md').write_text('# Changed\n', encoding='utf-8')
        self.assertEqual(self.run_manifest(), 1)

    def test_unknown_root_cannot_be_blessed_by_manifest_refresh(self):
        (self.root / 'private-notes.txt').write_text('Fictional private note', encoding='utf-8')
        self.assertEqual(self.run_manifest('--refresh'), 1)
        self.assertEqual(json.loads((self.root / 'release-manifest.json').read_text(encoding='utf-8'))['files'], {})

    @unittest.skipUnless(shutil.which('git'), 'Git is optional for ZIP users')
    def test_product_image_survives_git_text_normalization(self):
        source = Path(audit.__file__).parent
        (self.root / '.gitattributes').write_bytes((source / '.gitattributes').read_bytes())
        image = (source / 'assets/weeve-notes-demo.png').read_bytes()
        (self.root / 'demo.png').write_bytes(image)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'core.autocrlf=true', 'add', '.gitattributes', 'demo.png'],
                       check=True, capture_output=True)
        stored = subprocess.check_output(['git', '-C', str(self.root), 'show', ':demo.png'])
        self.assertEqual(stored, image)
        audit.validate_png(stored)

    def test_key_pattern_cannot_be_blessed_by_manifest_refresh(self):
        # Construct a clearly synthetic scanner fixture without storing a token-shaped literal.
        (self.root / 'README.md').write_text('ghp_' + 'A' * 36, encoding='utf-8')
        self.assertEqual(self.run_manifest('--refresh'), 1)


if __name__ == '__main__':
    unittest.main()
