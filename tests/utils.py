__all__ = ('read_header', 'getcontents')

import socket  # noqa: E402
import time  # noqa: E402


def read_header(header, key):
    name = b'\r\n%s: ' % key
    values = []
    start = 0

    while True:
        start = header.find(name, start)

        if start == -1:
            break

        start += len(name)
        values.append(header[start:header.find(b'\r\n', start)])

    return values


# a simple HTTP client for tests
def getcontents(host, port, method='GET', url='/', version='1.1', headers=(),
                data='', raw=b'', timeout=10, max_retries=10):
    if max_retries <= 0:
        raise ValueError('max_retries is exceeded, or it cannot be negative')

    method = method.upper().encode('latin-1')
    url = url.encode('latin-1')
    version = version.encode('latin-1')

    if raw == b'':
        headers = list(headers)

        if data:
            if not headers:
                headers.append(
                    'Content-Type: application/x-www-form-urlencoded'
                )

            headers.append('Content-Length: %d' % len(data))

        raw = b'%s %s HTTP/%s\r\nHost: %s:%d\r\n%s\r\n\r\n%s' % (
            method, url, version, host.encode('latin-1'), port,
            '\r\n'.join(headers).encode('latin-1'), data.encode('latin-1')
        )

    family = socket.AF_INET

    if ':' in host:
        family = socket.AF_INET6

    if host in ('0.0.0.0', '::'):
        host = 'localhost'

    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(timeout)

        while sock.connect_ex((host, port)) != 0:  # server is not ready yet?
            print('getcontents: reconnecting: %s:%d' % (host, port))
            time.sleep(1)

        request_header = raw[:raw.find(b'\r\n\r\n') + 4]
        request_body = raw[raw.find(b'\r\n\r\n') + 4:]

        try:
            sock.sendall(request_header)

            if not (b'\r\nExpect: 100-continue' in request_header or
                    b'\r\nUpgrade:' in request_header):
                sock.sendall(request_body)

            response_data = bytearray()
            response_header = b''
            content_length = -1

            while True:
                if ((content_length != -1 and
                        len(response_data) >= content_length) or
                        response_data.endswith(b'\r\n0\r\n\r\n')):
                    break

                buf = sock.recv(4096)

                if not buf:
                    break

                response_data.extend(buf)

                if response_header:
                    continue

                header_size = response_data.find(b'\r\n\r\n')

                if header_size == -1:
                    continue

                response_header = response_data[:header_size]
                del response_data[:header_size + 4]

                if method == b'HEAD':
                    break

                values = read_header(response_header, b'Content-Length')

                if values:
                    content_length = int(values[0])

                if response_header.startswith(b'HTTP/%s 100 ' % version):
                    sock.sendall(request_body)
                    response_header = b''
                elif response_header.startswith(b'HTTP/%s 101 ' % version):
                    sock.sendall(request_body)

            return response_header, bytes(response_data)
        except OSError:  # retry if either sendall() or recv() fails
            print(
                'getcontents: retry (%d): %s' % (max_retries, request_header)
            )
            time.sleep(1)
            return getcontents(
                host, port, raw=raw, max_retries=max_retries - 1
            )
