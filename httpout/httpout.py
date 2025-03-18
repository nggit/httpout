# Copyright (c) 2024 nggit

import asyncio
import builtins
import os
import sys

from types import ModuleType

from awaiter import MultiThreadExecutor
from tremolo.exceptions import BadRequest, NotFound, Forbidden
from tremolo.lib.websocket import WebSocket
from tremolo.utils import html_escape

from .request import HTTPRequest
from .response import HTTPResponse
from .utils import (
    is_safe_path, new_module, exec_module, cleanup_modules, mime_types
)


class HTTPOut:
    def __init__(self, app):
        app.add_hook(self._on_worker_start, 'worker_start')
        app.add_hook(self._on_worker_stop, 'worker_stop')
        app.add_middleware(self._on_request, 'request', priority=9999)  # low
        app.add_middleware(self._on_close, 'close')

    async def _on_worker_start(self, **worker):
        loop = worker['loop']
        logger = worker['logger']
        g = worker['globals']
        thread_pool_size = g.options.get('thread_pool_size', 5)
        document_root = os.path.abspath(
            g.options.get('document_root', os.getcwd())
        )
        g.options['document_root'] = document_root
        g.options['directory_index'] = g.options.get(
            'directory_index', ['index.py', 'index.html']
        )

        logger.info('entering directory: %s', document_root)
        os.chdir(document_root)
        sys.path.insert(0, document_root)

        # provides __globals__, a worker-level context
        module = new_module('__globals__')
        worker['__globals__'] = module or ModuleType('__globals__')
        worker['modules'] = {'__globals__': worker['__globals__']}
        py_import = builtins.__import__

        def wait(coro, timeout=None):
            return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout)

        def load_module(name, globals, level=0):
            if '__server__' in globals:
                modules = globals['__main__'].__server__['modules']
            else:
                modules = worker['modules']

            if name in modules:
                # already imported
                return modules[name]

            module = new_module(name, level, document_root)

            if module:
                logger.info('%s: importing %s', globals['__name__'], name)

                if '__server__' in globals:
                    module.__main__ = globals['__main__']
                    module.__server__ = globals['__main__'].__server__
                    module.print = globals['__main__'].print
                    module.run = globals['__main__'].run
                    module.wait = wait

                modules[name] = module
                exec_module(module)

                return module

        def ho_import(name, globals=None, locals=None, fromlist=(), level=0):
            if (name not in sys.builtin_module_names and
                    globals is not None and '__file__' in globals and
                    globals['__file__'].startswith(document_root)):
                # satisfy import __main__
                if name == '__main__':
                    logger.info('%s: importing __main__', globals['__name__'])

                    if globals['__name__'] == '__globals__':
                        return worker['__globals__']

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

                parent, _, child = name.partition('.')

                if parent == 'httpout' and (child == '' or child in globals):
                    if '__server__' in globals:
                        module = globals['__main__'].__server__['modules'][
                            globals['__name__']
                        ]
                    else:
                        module = worker['modules'][globals['__name__']]

                    # handles virtual imports,
                    # e.g. from httpout import request, response
                    if fromlist:
                        for child in fromlist:
                            if child in module.__dict__:
                                continue

                            if ('__server__' in globals and
                                    child in module.__server__):
                                module.__dict__[child] = module.__server__[
                                    child
                                ]
                            elif child in worker:
                                module.__dict__[child] = worker[child]
                            else:
                                raise ImportError(
                                    f'cannot import name \'{child}\' '
                                    f'from \'{name}\''
                                )

                    return module

            return py_import(name, globals, locals, fromlist, level)

        builtins.__import__ = ho_import
        builtins.__globals__ = worker['__globals__']
        builtins.exit = sys.exit

        g.wait = wait
        g.caches = {}
        g.executor = MultiThreadExecutor(thread_pool_size)
        g.executor.start()

        if module:
            exec_module(module)

    async def _on_worker_stop(self, **worker):
        g = worker['globals']

        await g.executor.shutdown()

    async def _on_request(self, **server):
        request = server['request']
        response = server['response']
        logger = server['logger']
        ctx = server['context']
        g = server['globals']
        document_root = g.options['document_root']

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
            for basename in g.options['directory_index']:
                module_path = os.path.join(dirname, basename)
                ext = os.path.splitext(basename)[-1]

                if os.path.exists(module_path):
                    break

        if basename.startswith('_') or not os.path.isfile(module_path):
            raise NotFound('URL not found:', html_escape(request_uri))

        if ext == '.py':
            # begin loading the module
            logger.info('%s -> __main__: %s', path, module_path)

            server['request'] = HTTPRequest(request, server)
            server['response'] = HTTPResponse(response)

            if (g.options['ws'] and
                    b'sec-websocket-key' in request.headers and
                    b'upgrade' in request.headers and
                    request.headers[b'upgrade'].lower() == b'websocket'):
                server['websocket'] = WebSocket(request, response)
            else:
                server['websocket'] = None

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

            module = ModuleType('__main__')
            module.__file__ = module_path
            module.__main__ = module
            server['modules'] = {'__main__': module}
            module.__server__ = server
            module.print = server['response'].print
            module.run = server['response'].run_coroutine
            module.wait = g.wait
            code = g.caches.get(module_path, None)

            if code:
                logger.info('%s: using cache', path)

            try:
                # execute module in another thread
                result = await g.executor.submit(exec_module, module, code)
                await server['response'].join()

                if result:
                    g.caches[module_path] = result
                    logger.info('%s: cached', path)
                else:
                    # cache is going to be deleted on @app.on_close
                    # but it can be delayed on a Keep-Alive request
                    ctx.module_path = module_path
            except BaseException as exc:
                await server['response'].join()
                await server['response'].handle_exception(exc)
            finally:
                await g.executor.submit(
                    cleanup_modules, server['modules'], g.options['debug']
                )
                await server['response'].join()
                server['modules'].clear()
            # EOF
            return b''

        # not a module
        if ext not in mime_types:
            raise Forbidden(f'Disallowed file extension: {ext}')

        logger.info('%s -> %s: %s', path, mime_types[ext], module_path)
        await response.sendfile(
            module_path, content_type=mime_types[ext], executor=g.executor
        )
        # exit middleware without closing the connection
        return True

    async def _on_close(self, **server):
        logger = server['logger']
        ctx = server['context']
        g = server['globals']

        if 'module_path' in ctx:
            g.caches[ctx.module_path] = None
            logger.info('cache deleted: %s', ctx.module_path)
