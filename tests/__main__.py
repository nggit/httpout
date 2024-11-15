#!/usr/bin/env python3

import multiprocessing as mp
import os
import sys
import signal
import unittest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# makes imports relative from the repo directory
sys.path.insert(0, PROJECT_DIR)

from tremolo import Application  # noqa: E402
from httpout import HTTPOut  # noqa: E402

app = Application()

HTTPOut(app)

HTTP_HOST = '127.0.0.1'
HTTP_PORT = 28008
DOCUMENT_ROOT = os.path.join(PROJECT_DIR, 'examples')


def main():
    mp.set_start_method('spawn')

    p = mp.Process(
        target=app.run,
        kwargs=dict(
            host=HTTP_HOST, port=HTTP_PORT,
            document_root=DOCUMENT_ROOT, app=None, debug=False
        )
    )
    p.start()

    try:
        suite = unittest.TestLoader().discover('tests')
        unittest.TextTestRunner().run(suite)
    finally:
        if p.is_alive():
            os.kill(p.pid, signal.SIGTERM)
            p.join()


if __name__ == '__main__':
    main()
