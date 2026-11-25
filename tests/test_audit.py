"""Regression checks for the explicitly reviewed product image."""
import struct
import unittest
import zlib
import audit


class ImageAuditTests(unittest.TestCase):
    def setUp(self):
        self.image = (audit.ROOT / 'assets/weeve-notes-demo.png').read_bytes()

    def test_reviewed_image_passes(self):
        audit.validate_png(self.image)

    def test_appended_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.validate_png(self.image + b'private-note')

    def test_text_metadata_chunk_is_rejected(self):
        payload = b'Comment\x00Private draft'
        kind = b'tEXt'
        chunk = struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
        # Insert the text chunk immediately before IEND.
        with self.assertRaises(ValueError):
            audit.validate_png(self.image[:-12] + chunk + self.image[-12:])
