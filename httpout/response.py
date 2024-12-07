# Copyright (c) 2024 nggit

import asyncio
import concurrent.futures

from traceback import TracebackException
from tremolo.utils import html_escape


class HTTPResponse:
    def __init__(self, response):
        self.response = response
        self.loop = response.request.protocol.loop
        self.logger = response.request.protocol.logger
        self.tasks = set()

    def __getattr__(self, name):
        return getattr(self.response, name)

    def create_task(self, coro):
        task = self.loop.create_task(coro)

        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def join(self):
        while self.tasks:
            await self.tasks.pop()

    async def handle_exception(self, exc):
        if self.response.request.upgraded:
            await self.response.request.protocol.handle_exception(exc)
        else:
            if not self.response.headers_sent():
                self.response.set_status(500, b'Internal Server Error')
                self.response.set_content_type(b'text/html; charset=utf-8')
                self.response.request.http_keepalive = False

            if isinstance(exc, Exception):
                if self.response.request.protocol.options['debug']:
                    te = TracebackException.from_exception(exc)
                    await self.response.write(
                        b'<ul><li>%s</li></ul>\n' % b'</li><li>'.join(
                            html_escape(line)
                            .encode() for line in te.format()
                        )
                    )
                else:
                    await self.response.write(
                        f'<ul><li>{exc.__class__.__name__}: '
                        f'{html_escape(str(exc))}</li></ul>\n'
                        .encode()
                    )
            elif isinstance(exc, SystemExit):
                if exc.code:
                    await self.response.write(str(exc.code).encode())
            else:
                self.response.request.protocol.print_exception(exc)

    def run_coroutine(self, coro):
        fut = concurrent.futures.Future()

        async def callback():
            try:
                result = await coro

                if not fut.done():
                    fut.set_result(result)
            except BaseException as exc:
                if not fut.done():
                    fut.set_result(None)

                await self.handle_exception(exc)

        self.loop.call_soon_threadsafe(self.create_task, callback())
        return fut

    def call_soon(self, func, *args):
        try:
            loop = asyncio.get_running_loop()

            if loop is self.loop:
                return func(*args)
        except RuntimeError:
            pass

        fut = concurrent.futures.Future()

        def callback():
            try:
                result = func(*args)

                if not fut.done():
                    fut.set_result(result)
            except BaseException as exc:
                if not fut.done():
                    fut.set_exception(exc)

        self.loop.call_soon_threadsafe(callback)
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

    async def _run_middleware(self):
        g = self.response.request.protocol.globals
        ctx = self.response.request.protocol.context
        middlewares = g.options['_middlewares']['response']
        i = len(middlewares)

        try:
            while i > 0:
                i -= 1

                if await middlewares[i][1](globals=g,
                                           context=ctx,
                                           loop=self.loop,
                                           logger=self.logger,
                                           request=self.response.request,
                                           response=self.response):
                    break
        except Exception as exc:
            await self.response.request.protocol.handle_exception(exc)

    async def write(self, data, **kwargs):
        if not self.response.headers_sent():
            await self._run_middleware()

        await self.response.write(data, **kwargs)

    def print(self, *args, sep=' ', end='\n', **kwargs):
        coro = self.write((sep.join(map(str, args)) + end).encode())

        try:
            loop = asyncio.get_running_loop()

            if loop is self.loop:
                self.create_task(coro)
                return
        except RuntimeError:
            pass

        self.loop.call_soon_threadsafe(self.create_task, coro)
