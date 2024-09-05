# Copyright (c) 2024 nggit

__version__ = '0.0.11'
__all__ = ('app',)

import asyncio  # noqa: E402
import builtins  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

from traceback import TracebackException  # noqa: E402
from types import ModuleType  # noqa: E402

from awaiter import MultiThreadExecutor  # noqa: E402
from tremolo import Tremolo  # noqa: E402
from tremolo.exceptions import NotFound, Forbidden  # noqa: E402
from tremolo.lib.contexts import Context  # noqa: E402
from tremolo.lib.websocket import WebSocket  # noqa: E402
from tremolo.utils import html_escape  # noqa: E402

from .utils import is_safe_path, exec_module, mime_types  # noqa: E402

app = Tremolo()


@app.on_worker_start
async def httpout_worker_start(**worker):
    worker_ctx = worker['context']
    app = worker['app']
    loop = worker['loop']
    logger = worker['logger']
    thread_pool_size = worker_ctx.options.get('thread_pool_size', 5)
    document_root = os.path.abspath(
        worker_ctx.options.get('document_root', os.getcwd())
    )
    worker_ctx.options['document_root'] = document_root

    def run(coro):
        return asyncio.run_coroutine_threadsafe(coro, loop)

    def wait(coro, timeout=None):
        return run(coro).result(timeout=timeout)

    def load_module(name, globals, level=0):
        if name in globals['__main__'].__server__.modules:
            # already imported
            return globals['__main__'].__server__.modules[name]

        module_path = os.path.join(
            document_root,
            name.replace('.', os.sep), '__init__.py'
        )

        if not os.path.isfile(module_path):
            module_path = os.path.join(
                document_root, name.replace('.', os.sep) + '.py'
            )

        if os.path.isfile(module_path):
            if name in sys.modules:
                if ('__file__' in sys.modules[name].__dict__ and
                        sys.modules[name].__file__
                        .startswith(document_root)):
                    del sys.modules[name]

                raise ImportError(f'module name conflict: {name}')

            logger.info(
                'httpout: %d: %s: importing %s',
                globals['__main__'].__server__.request.socket.fileno(),
                globals['__name__'],
                name
            )
            module = ModuleType(name)
            module.__file__ = module_path
            module.__package__ = (
                os.path.dirname(module_path)[len(document_root):]
                .lstrip(os.sep)
                .rsplit(os.sep, level)[0]
                .replace(os.sep, '.')
            )

            if name == module.__package__:
                module.__path__ = [os.path.dirname(module_path)]

            module.__main__ = globals['__main__']
            module.__server__ = globals['__main__'].__server__
            module.print = globals['__main__'].print
            module.run = run
            module.wait = wait
            globals['__main__'].__server__.modules[name] = module

            exec_module(module)
            return module

    python_import = builtins.__import__

    def httpout_import(name, globals=None, locals=None, fromlist=(), level=0):
        if (name not in sys.builtin_module_names and globals is not None and
                '__main__' in globals and
                globals['__main__'].__file__.startswith(document_root)):
            # satisfy import __main__
            if name == '__main__':
                logger.info(
                    'httpout: %d: %s: importing __main__',
                    globals['__main__'].__server__.request.socket.fileno(),
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

            if name == 'httpout':
                module = globals['__main__'].__server__.modules[
                    globals['__name__']
                ]

                # from httpout import request, response
                for child in fromlist:
                    module.__dict__[child] = module.__server__[child]

                return module

        return python_import(name, globals, locals, fromlist, level)

    builtins.__import__ = httpout_import

    worker_ctx.run = run
    worker_ctx.wait = wait
    worker_ctx.caches = {}
    worker_ctx.executor = MultiThreadExecutor(thread_pool_size)

    worker_ctx.executor.start()

    logger.info('entering directory: %s', document_root)
    os.chdir(document_root)
    sys.path.insert(0, document_root)

    # provides __globals__, a worker-level context
    builtins.__globals__ = ModuleType('__globals__')  # noqa: F821
    __globals__.__file__ = os.path.join(document_root, '__globals__.py')  # noqa: E501,F821
    app.ctx = Context()

    if os.path.isfile(__globals__.__file__):  # noqa: F821
        exec_module(__globals__)  # noqa: F821

        if '__enter__' in __globals__.__dict__:  # noqa: F821
            __globals__.__enter__(app)  # noqa: F821

    app.add_middleware(httpout_on_request, 'request')


@app.on_worker_stop
async def httpout_worker_stop(**worker):
    worker_ctx = worker['context']
    app = worker['app']

    try:
        if '__exit__' in __globals__.__dict__:  # noqa: F821
            __globals__.__exit__(app)  # noqa: F821
    finally:
        await worker_ctx.executor.shutdown()


@app.on_close
async def httpout_on_close(**server):
    request_ctx = server['context']
    worker_ctx = server['worker']
    logger = server['logger']

    if 'module_path' in request_ctx:
        worker_ctx.caches[request_ctx.module_path] = None
        logger.info('httpout: cache deleted: %s', request_ctx.module_path)


async def httpout_on_request(**server):
    request = server['request']
    response = server['response']
    loop = server['loop']
    logger = server['logger']
    worker_ctx = server['worker']
    document_root = worker_ctx.options['document_root']

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

    if ext == '':
        dirname = module_path
        basename = 'index.py'
        module_path = os.path.join(dirname, basename)
        ext = '.py'

    request_uri = request.url.decode('latin-1')

    if not os.path.isfile(module_path):
        raise NotFound('URL not found:', html_escape(request_uri))

    if ext == '.py':
        # begin loading the module
        logger.info(
            'httpout: %d: %s -> __main__: %s',
            request.socket.fileno(), path, module_path
        )
        __server__ = Context()
        __server__.request = request
        __server__.response = response
        __server__.REQUEST_METHOD = request.method.decode('latin-1')
        __server__.SCRIPT_NAME = module_path[len(document_root):].replace(os.sep, '/')  # noqa: E501
        __server__.PATH_INFO = path_info
        __server__.QUERY_STRING = request.query_string.decode('latin-1')
        __server__.REMOTE_ADDR = request.ip.decode('latin-1')
        __server__.HTTP_HOST = request.host.decode('latin-1')
        __server__.REQUEST_URI = request_uri
        __server__.REQUEST_SCHEME = request.scheme.decode('latin-1')
        __server__.DOCUMENT_ROOT = document_root

        if (request.protocol.options['ws'] and
                b'upgrade' in request.headers and
                b'connection' in request.headers and
                b'sec-websocket-key' in request.headers and
                request.headers[b'upgrade'].lower() == b'websocket'):
            __server__.websocket = WebSocket(request, response)
        else:
            __server__.websocket = None

        def create_task(coro):
            request.ctx.task = loop.create_task(coro)

        async def write(data, waiter):
            if waiter:
                await waiter

            await response.write(data)

        def httpout_print(*args, sep=' ', end='\n', **kwargs):
            loop.call_soon_threadsafe(
                create_task,
                write((sep.join(map(str, args)) + end).encode(),
                      request.ctx.get('task'))
            )

        module = ModuleType('__main__')
        module.__file__ = module_path
        module.__main__ = module
        __server__.modules = {'__main__': module}
        module.__server__ = __server__
        module.print = httpout_print
        module.run = worker_ctx.run
        module.wait = worker_ctx.wait
        code = worker_ctx.caches.get(module_path, None)

        if code:
            logger.info(
                'httpout: %d: %s: using cache', request.socket.fileno(), path
            )

        try:
            # execute module in another thread
            result = await worker_ctx.executor.submit(
                exec_module, module, code
            )

            if 'task' in request.ctx:
                await request.ctx.task

            if result:
                worker_ctx.caches[module_path] = result
                logger.info(
                    'httpout: %d: %s: cached', request.socket.fileno(), path
                )
            else:
                # cache is going to be deleted on @app.on_close
                # but it can be delayed on a Keep-Alive request
                request.ctx.module_path = module_path
        except BaseException as exc:
            if 'task' in request.ctx and not request.ctx.task.done():
                await request.ctx.task

            if not response.headers_sent():
                response.set_status(500, b'Internal Server Error')
                response.set_content_type(b'text/html; charset=utf-8')
                request.http_keepalive = False

            if isinstance(exc, Exception):
                if request.protocol.options['debug']:
                    te = TracebackException.from_exception(exc)
                    await response.write(
                        b'<ul><li>%s</li></ul>\n' % b'</li><li>'.join(
                            html_escape(line).encode() for line in te.format()
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
        # EOF
        return b''

    # not a module
    if ext not in mime_types:
        raise Forbidden(f'Disallowed file extension: {ext}')

    logger.info(
        'httpout: %d: %s -> %s: %s',
        request.socket.fileno(), path, mime_types[ext], module_path
    )
    await response.sendfile(module_path, content_type=mime_types[ext])

    # exit middleware without closing the connection
    return True
