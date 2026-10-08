"""Tests de la decisión de clase de clipboard.py (sin tocar el portapapeles real).

«class ut16» aparece en cualquier texto plano copiado: solo es un menú de FileMaker
si el texto contiene XML de menú (o al menos un fmxmlsnippet).

Run: python3 agent/scripts/test_clipboard.py
"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

import clipboard as cb

MENU_XML = '<fmxmlsnippet type="FMObjectList"><CustomMenu id="1" name="M"/></fmxmlsnippet>'
MENU_SET_XML = '<CustomMenuSet id="2" name="S"><CustomMenuList/></CustomMenuSet>'


class ClassifyTests(unittest.TestCase):
    def test_binary_fm_class_wins(self):
        self.assertEqual(cb.classify_clipboard('XMSS', 'texto cualquiera'), 'XMSS')

    def test_empty_plain_text_is_not_menu(self):
        # Caso real 2026-10-08: utf8 0, ut16 2 bytes (solo BOM), string 0.
        self.assertIsNone(cb.classify_clipboard(None, ''))
        self.assertIsNone(cb.classify_clipboard(None, '﻿'))

    def test_plain_text_is_not_menu(self):
        self.assertIsNone(cb.classify_clipboard(None, 'Set Variable [ $x ; 1 ]'))

    def test_no_clipboard_content(self):
        self.assertIsNone(cb.classify_clipboard(None, None))
        self.assertIsNone(cb.classify_clipboard('', None))

    def test_menu_xml_is_menu(self):
        self.assertEqual(cb.classify_clipboard(None, MENU_XML), 'ut16')
        self.assertEqual(cb.classify_clipboard(None, MENU_SET_XML), 'ut16')

    def test_bare_fmxmlsnippet_text_is_accepted(self):
        self.assertEqual(cb.classify_clipboard(None, '<fmxmlsnippet type="FMObjectList"/>'), 'ut16')

    def test_unknown_binary_class_is_ignored(self):
        self.assertIsNone(cb.classify_clipboard('utf8', 'hola'))


class ReadTests(unittest.TestCase):
    def _read(self, ut16_text):
        out = os.path.join(tempfile.mkdtemp(), 'out.xml')
        err = io.StringIO()
        with mock.patch.object(cb, '_HAS_APPKIT', True), \
                mock.patch.object(cb, '_nspasteboard_detect',
                                  lambda: cb.classify_clipboard(None, ut16_text)), \
                mock.patch.object(cb, '_nspasteboard_read_ut16_text', lambda: ut16_text), \
                redirect_stderr(err):
            try:
                cb.read_from_clipboard(out)
                code = 0
            except SystemExit as e:
                code = e.code
        return code, os.path.exists(out), err.getvalue()

    def test_plain_text_read_fails_without_writing(self):
        code, written, err = self._read('﻿')
        self.assertNotEqual(code, 0)
        self.assertFalse(written)
        self.assertIn('no contiene objetos de FileMaker', err)

    def test_menu_read_writes_file(self):
        code, written, err = self._read(MENU_XML)
        self.assertEqual(code, 0)
        self.assertTrue(written)
        self.assertIn('ut16 (Menu)', err)


if __name__ == '__main__':
    unittest.main()
