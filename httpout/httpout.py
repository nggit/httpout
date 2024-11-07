# Copyright (c) 2024 nggit

import asyncio
import builtins
import os
import sys

from traceback import TracebackException
from types import ModuleType

from awaiter import MultiThreadExecutor
from tremolo.exceptions import BadRequest, NotFound, Forbidden
from tremolo.lib.websocket import WebSocket
from tremolo.utils import html_escape

from .lib.http_request import HTTPRequest
from .lib.http_response import HTTPResponse
from .utils import (
    is_safe_path, new_module, exec_module, cleanup_modules, mime_types
)

_INDEX_FILES = ('index.py', 'index.html')


class HTTPOut:
    def __init__(self, app):
        app.add_hook(self._on_worker_start, 'worker_start')
        app.add_hook(self._on_worker_stop, 'worker_stop')
        app.add_middleware(self._on_request, 'request', priority=9999)  # low
        app.add_middleware(self._on_close, 'close')

    async def _on_worker_start(self, **worker):
        worker_ctx = worker['context']
        app = worker['app']
        loop = worker['loop']
        logger = worker['logger']
        thread_pool_size = worker_ctx.options.get('thread_pool_size', 5)
        document_root = os.path.abspath(
            worker_ctx.options.get('document_root', os.getcwd())
        )
        worker_ctx.options['document_root'] = document_root

        def wait(coro, timeout=None):
            return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout)

        def load_module(name, globals, level=0):
            if name in globals['__main__'].__server__['modules']:
                # already imported
                return globals['__main__'].__server__['modules'][name]

            module = new_module(name, level, document_root)

            if module:
                logger.info(
                    '%d: %s: importing %s',
                    globals['__main__'].__server__['request'].socket.fileno(),
                    globals['__name__'],
                    name
                )
                module.__main__ = globals['__main__']
                module.__server__ = globals['__main__'].__server__
                module.print = globals['__main__'].print
                module.run = globals['__main__'].run
                module.wait = wait
                globals['__main__'].__server__['modules'][name] = module

                exec_module(module)
                return module

        py_import = builtins.__import__

        def ho_import(name, globals=None, locals=None, fromlist=(), level=0):
            if (name not in sys.builtin_module_names and
                    globals is not None and '__main__' in globals and
                    globals['__main__'].__file__.startswith(document_root)):
                # satisfy import __main__
                if name == '__main__':
                    logger.info(
                        '%d: %s: importing __main__',
                        globals['__main__'].__server__['request']
                                           .socket.fileno(),
                        globals['__name__']
                    )
                    return globals['__main__']

                oldname = name

                if level > 0:
                    name = globals['__name__'].rsplit('.', level)[0]

                    if oldname != '':
                        name = f'{name}.{oldname}'

                module = load_module(name, globals, level)

                if module:
                    if oldname == '':
                        # relative import
                        for child in fromlist:
                            module.__dict__[child] = load_module(
                                f'{name}.{child}', globals
                            )

                    return module

                if name == 'httpout' or name.startswith('httpout.'):
                    module = globals['__main__'].__server__['modules'][
                        globals['__name__']
                    ]

                    # handles virtual imports,
                    # e.g. from httpout import request, response
                    if fromlist:
                        for child in fromlist:
                            if child in module.__dict__:
                                continue

                            if child in module.__server__:
                                module.__dict__[child] = module.__server__[
                                    child
                                ]
                            else:
                                try:
                                    module.__dict__[child] = getattr(
                                        builtins, child
                                    )
                                except AttributeError as exc:
                                    raise ImportError(
                                        f'cannot import name \'{child}\' '
                                        f'from \'{name}\''
                                    ) from exc

                    return module

            return py_import(name, globals, locals, fromlist, level)

        builtins.__import__ = ho_import

        worker_ctx.wait = wait
        worker_ctx.caches = {}
        worker_ctx.executor = MultiThreadExecutor(thread_pool_size)

        worker_ctx.executor.start()
        logger.info('entering directory: %s', document_root)
        os.chdir(document_root)
        sys.path.insert(0, document_root)

        # provides __globals__, a worker-level context
        builtins.__globals__ = new_module('__globals__')
        app.ctx = worker_ctx

        if __globals__:  # noqa: F821
            exec_module(__globals__)  # noqa: F821

            if '__enter__' in __globals__.__dict__:  # noqa: F821
                coro = __globals__.__enter__(app)  # noqa: F821

                if hasattr(coro, '__await__'):
                    await coro
        else:
            builtins.__globals__ = ModuleType('__globals__')

    async def _on_worker_stop(self, **worker):
        app = worker['app']

        try:
            if '__exit__' in __globals__.__dict__:  # noqa: F821
                coro = __globals__.__exit__(app)  # noqa: F821

                if hasattr(coro, '__await__'):
                    await coro
        finally:
            await app.ctx.executor.shutdown()

    async def _on_request(self, **server):
        request = server['request']
        response = server['response']
        logger = server['logger']
        worker_ctx = server['worker']
        document_root = worker_ctx.options['document_root']

        if not request.is_valid:
            raise BadRequest

        # no need to unquote path
        # in fact, the '%' character in the path will be rejected.
        # httpout strictly uses A-Z a-z 0-9 - _ . for directory names
        # which does not need the use of percent-encoding
        path = request.path.decode('latin-1')
        path_info = path[(path + '.py/').find('.py/') + 3:]

        if path_info:
            path = path[:path.rfind(path_info)]
            path_info = os.path.normpath(path_info).replace(os.sep, '/')

        module_path = os.path.abspath(
            os.path.join(document_root, os.path.normpath(path.lstrip('/')))
        )

        if not module_path.startswith(document_root):
            raise Forbidden('Path traversal is not allowed')

        if '/.' in path and not path.startswith('/.well-known/'):
            raise Forbidden('Access to dotfiles is prohibited')

        if not is_safe_path(path):
            raise Forbidden('Unsafe URL detected')

        dirname, basename = os.path.split(module_path)
        ext = os.path.splitext(basename)[-1]
        request_uri = request.url.decode('latin-1')

        if ext == '':
            dirname = module_path

            # no file extension in the URL, try index.py, index.html, etc.
            for basename in _INDEX_FILES:
                module_path = os.path.join(dirname, basename)
                ext = os.path.splitext(basename)[-1]

                if os.path.exists(module_path):
                    break

        if basename.startswith('_') or not os.path.isfile(module_path):
            raise NotFound('URL not found:', html_escape(request_uri))

        if ext == '.py':
            # begin loading the module
            logger.info(
                '%d: %s -> __main__: %s',
                request.socket.fileno(), path, module_path
            )
            server['request'] = HTTPRequest(request, server)
            server['response'] = HTTPResponse(response)
            server['REQUEST_METHOD'] = request.method.decode('latin-1')
            server['SCRIPT_NAME'] = module_path[len(document_root):].replace(
                os.sep, '/'
            )
            server['PATH_INFO'] = path_info
            server['QUERY_STRING'] = request.query_string.decode('latin-1')
            server['REMOTE_ADDR'] = request.ip.decode('latin-1')
            server['HTTP_HOST'] = request.host.decode('latin-1')
            server['REQUEST_URI'] = request_uri
            server['REQUEST_SCHEME'] = request.scheme.decode('latin-1')
            server['DOCUMENT_ROOT'] = document_root

            if (request.protocol.options['ws'] and
                    b'upgrade' in request.headers and
                    b'connection' in request.headers and
                    b'sec-websocket-key' in request.headers and
                    request.headers[b'upgrade'].lower() == b'websocket'):
                server['websocket'] = WebSocket(request, response)
            else:
                server['websocket'] = None

            module = ModuleType('__main__')
            module.__file__ = module_path
            module.__main__ = module
            server['modules'] = {'__main__': module}
            module.__server__ = server
            module.print = server['response'].print
            module.run = server['response'].run_coroutine
            module.wait = worker_ctx.wait
            code = worker_ctx.caches.get(module_path, None)

            if code:
                logger.info(
                    '%d: %s: using cache', request.socket.fileno(), path
                )

            try:
                # execute module in another thread
                result = await worker_ctx.executor.submit(
                    exec_module, module, code
                )
                await server['response'].join()

                if result:
                    worker_ctx.caches[module_path] = result
                    logger.info(
                        '%d: %s: cached', request.socket.fileno(), path
                    )
                else:
                    # cache is going to be deleted on @app.on_close
                    # but it can be delayed on a Keep-Alive request
                    server['context'].module_path = module_path
            except BaseException as exc:
                await server['response'].join()

                if not response.headers_sent():
                    response.set_status(500, b'Internal Server Error')
                    response.set_content_type(b'text/html; charset=utf-8')
                    request.http_keepalive = False

                if isinstance(exc, Exception):
                    if request.protocol.options['debug']:
                        te = TracebackException.from_exception(exc)
                        await response.write(
                            b'<ul><li>%s</li></ul>\n' % b'</li><li>'.join(
                                html_escape(line)
                                .encode() for line in te.format()
                            )
                        )
                    else:
                        await response.write(
                            f'<ul><li>{exc.__class__.__name__}: '
                            f'{html_escape(str(exc))}</li></ul>\n'
                            .encode()
                        )
                elif isinstance(exc, SystemExit):
                    if exc.code:
                        await response.write(str(exc.code).encode())
                else:
                    request.protocol.print_exception(exc)
            finally:
                await worker_ctx.executor.submit(
                    cleanup_modules, server['modules'], (module.print,
                                                         module.run,
                                                         module.wait,
                                                         worker_ctx,
                                                         server['context'],
                                                         server['response'])
                )
                await server['response'].join()
                server['modules'].clear()
            # EOF
            return b''

        # not a module
        if ext not in mime_types:
            raise Forbidden(f'Disallowed file extension: {ext}')

        logger.info(
            '%d: %s -> %s: %s',
            request.socket.fileno(), path, mime_types[ext], module_path
        )
        await response.sendfile(
            module_path,
            content_type=mime_types[ext],
            executor=worker_ctx.executor
        )
        # exit middleware without closing the connection
        return True

    async def _on_close(self, **server):
        request_ctx = server['context']
        worker_ctx = server['worker']
        logger = server['logger']

        if 'module_path' in request_ctx:
            worker_ctx.caches[request_ctx.module_path] = None
            logger.info('cache deleted: %s', request_ctx.module_path)
