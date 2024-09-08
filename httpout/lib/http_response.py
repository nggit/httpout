# Copyright (c) 2024 nggit

import asyncio
import concurrent.futures


class HTTPResponse:
    def __init__(self, response):
        self.response = response
        self.loop = response.request.protocol.loop

    def __getattr__(self, name):
        return getattr(self.response, name)

    def call_soon(self, func, *args):
        try:
            loop = asyncio.get_running_loop()

            if loop is self.loop:
                return func(*args)
        except RuntimeError:
            pass

        fut = concurrent.futures.Future()

        async def callback(fut, func, *args):
            try:
                result = func(*args)

                if not fut.done():
                    fut.set_result(result)
            except BaseException as exc:
                if not fut.done():
                    fut.set_exception(exc)

        self.loop.call_soon_threadsafe(
            self.loop.create_task, callback(fut, func, *args)
        )
        return fut.result()

    def headers_sent(self, sent=False):
        return self.call_soon(self.response.headers_sent, sent)

    def append_header(self, name, value):
        self.call_soon(self.response.append_header, name, value)

    def set_header(self, name, value=''):
        self.call_soon(self.response.set_header, name, value)

    def set_cookie(self, name, value='', expires=0, path='/', domain=None,
                   secure=False, httponly=False, samesite=None):
        self.call_soon(
            self.response.set_cookie, name, value, expires, path, domain,
            secure, httponly, samesite
        )

    def set_status(self, status=200, message='OK'):
        self.call_soon(self.response.set_status, status, message)

    def set_content_type(self, content_type='text/html; charset=utf-8'):
        self.call_soon(self.response.set_content_type, content_type)

    def print(self, *args, sep=' ', end='\n', **kwargs):
        coro = self.response.write((sep.join(map(str, args)) + end).encode())

        try:
            loop = asyncio.get_running_loop()

            if loop is self.loop:
                self.loop.create_task(coro)
                return
        except RuntimeError:
            pass

        self.loop.call_soon_threadsafe(self.loop.create_task, coro)
