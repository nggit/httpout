__all__ = ('read_header', 'getcontents')

import socket  # noqa: E402
import time  # noqa: E402


def read_header(header, key):
    name = b'\r\n%s: ' % key
    headers = []
    start = 0

    while True:
        start = header.find(name, start)

        if start == -1:
            break

        start += len(name)
        headers.append(header[start:header.find(b'\r\n', start)])

    return headers or [b'']


# a simple HTTP client for tests
def getcontents(host, port, method='GET', url='/', version='1.1', headers=None,
                data='', raw=b''):
    if raw == b'':
        if not headers:
            headers = []

        if data:
            if headers == []:
                headers.append(
                    'Content-Type: application/x-www-form-urlencoded'
                )

            headers.append('Content-Length: %d' % len(data))

        raw = (
            '{:s} {:s} HTTP/{:s}\r\n'
            'Host: {:s}:{:d}\r\n{:s}'
            '\r\n\r\n{:s}'
        ).format(
            method, url, version, host, port,
            '\r\n'.join(headers), data).encode('latin-1')

    family = socket.AF_INET

    if ':' in host:
        family = socket.AF_INET6

    if host in ('0.0.0.0', '::'):
        host = 'localhost'

    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(10)

        while sock.connect_ex((host, port)) != 0:
            time.sleep(1)

        request_header = raw[:raw.find(b'\r\n\r\n') + 4]
        request_body = raw[raw.find(b'\r\n\r\n') + 4:]
        _request_header = request_header.lower()

        sock.sendall(request_header)

        if not (b'\r\nexpect: 100-continue' in _request_header or
                b'\r\nupgrade:' in _request_header):
            sock.sendall(request_body)

        response_data = bytearray()
        response_header = b''
        cl = -1
        buf = True

        while buf:
            if ((cl != -1 and len(response_data) >= cl) or
                    response_data.endswith(b'\r\n0\r\n\r\n')):
                break

            try:
                buf = sock.recv(4096)
            except ConnectionResetError:
                print('getcontents: retry:', request_header)
                return getcontents(host, port, raw=raw)

            response_data.extend(buf)

            if response_header:
                continue

            header_size = response_data.find(b'\r\n\r\n')

            if header_size == -1:
                continue

            response_header = response_data[:header_size]
            del response_data[:header_size + 4]

            if method.upper() == 'HEAD':
                break

            _response_header = response_header.lower()
            _version = version.encode('latin-1')
            cl = int(
                read_header(_response_header, b'content-length')[0] or -1
            )

            if _response_header.startswith(b'http/%s 100 continue' % _version):
                sock.sendall(request_body)
                response_header = b''
            elif _response_header.startswith(b'http/%s 101 ' % _version):
                sock.sendall(request_body)

        return response_header, response_data
