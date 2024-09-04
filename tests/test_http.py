#!/usr/bin/env python3

import os
import sys
import unittest

# makes imports relative from the repo directory
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from tests.__main__ import main, HTTP_HOST, HTTP_PORT  # noqa: E402
from tests.utils import getcontents  # noqa: E402


class TestHTTP(unittest.TestCase):
    def setUp(self):
        print('[', self.id(), ']')

    def test_root_notfound(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 404 Not Found'
        )

    def test_index_empty(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/home',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertTrue(b'\r\nContent-Length: 0' in header)
        self.assertEqual(body, b'')

    def test_imports(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/main.py',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertEqual(
            body,
            b'6\r\nHello\n\r\n7\r\nWorld!\n\r\n3\r\nOK\n\r\n0\r\n\r\n'
        )

    def test_path_info(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='//path.py//',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertEqual(body, b'D\r\n//path.py //\n\r\n0\r\n\r\n')

    def test_syntax_error(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/syntax.py',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 500 Internal Server Error'
        )
        self.assertTrue(b'<ul><li>SyntaxError: ' in body)
        self.assertEqual(body[-18:], b'</li></ul>\n\r\n0\r\n\r\n')

    def test_exc_after_print(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/exc.py',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertEqual(
            body,
            b'3\r\nHi\n\r\n1F\r\n<ul><li>ValueError: </li></ul>\n\r\n0\r\n\r\n'
        )

    def test_exit_after_print(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/exit.py',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertEqual(body, b'7\r\nHello, \r\n0\r\n\r\n')

    def test_exit_str(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/exit.py?World',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertEqual(body, b'7\r\nHello, \r\n7\r\nWorld!\n\r\n0\r\n\r\n')

    def test_static_file(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/static/hello.gif',
                                   version='1.1')

        self.assertEqual(header[:header.find(b'\r\n')], b'HTTP/1.1 200 OK')
        self.assertTrue(b'\r\nContent-Type: image/gif' in header)
        self.assertEqual(body[:6], b'GIF89a')

    def test_sec_path_traversal(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='../.ssh/id_rsa',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Path traversal is not allowed')

    def test_sec_dotfiles(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/.env',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Access to dotfiles is prohibited')

    def test_sec_long_path(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/q' * 128,
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Unsafe URL detected')

    def test_sec_unsafe_chars_percent(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/example.php%00.png',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Unsafe URL detected')

    def test_sec_unsafe_chars_null(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/example.php\x00.png',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Unsafe URL detected')

    def test_disallowed_ext(self):
        header, body = getcontents(host=HTTP_HOST,
                                   port=HTTP_PORT,
                                   method='GET',
                                   url='/bad.ext',
                                   version='1.1')

        self.assertEqual(
            header[:header.find(b'\r\n')],
            b'HTTP/1.1 403 Forbidden'
        )
        self.assertEqual(body, b'Disallowed file extension: .ext')


if __name__ == '__main__':
    main()
