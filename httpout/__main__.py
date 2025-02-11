# Copyright (c) 2024 nggit

import sys

import tremolo

from httpout import __version__, HTTPOut

app = tremolo.Application()

HTTPOut(app)


def usage(**context):
    print('Usage: python3 -m httpout [OPTIONS] DOCUMENT_ROOT')
    print()
    print('Example:')
    print('  python3 -m httpout --port 8080 /home/user/public_html')
    print('  python3 -m httpout --debug --port 8080 /home/user/public_html')
    print()
    print('Options:')
    print('  --host                    Listen host. Defaults to "127.0.0.1"')
    print('  --port                    Listen port. Defaults to 8000')
    print('  --bind                    Address to bind.')
    print('                            Instead of using --host or --port')
    print('                            E.g. "127.0.0.1:8000" or "/tmp/file.sock"')  # noqa: E501
    print('                            Multiple binds can be separated by commas')  # noqa: E501
    print('                            E.g. "127.0.0.1:8000,:8001"')
    print('  --worker-num              Number of worker processes. Defaults to 1')  # noqa: E501
    print('  --thread-pool-size        Number of executor threads per process')  # noqa: E501
    print('                            Defaults to 5')
    print('  --limit-memory            Restart the worker if this limit (in KiB) is reached')  # noqa: E501
    print('                            (Linux-only). Defaults to 0 or unlimited')  # noqa: E501
    print('  --ssl-cert                SSL certificate location')
    print('                            E.g. "/path/to/fullchain.pem"')
    print('  --ssl-key                 SSL private key location')
    print('                            E.g. "/path/to/privkey.pem"')
    print('  --directory-index         Index files to be served on directory-based URLs')  # noqa: E501
    print('                            Must be separated by commas. E.g. "index.py,index.html"')  # noqa: E501
    print('  --debug                   Enable debug mode')
    print('                            Intended for development')
    print('  --log-level               Defaults to "DEBUG". See')
    print('                            https://docs.python.org/3/library/logging.html#levels')  # noqa: E501
    print('  --log-fmt                 Python\'s log format. If empty defaults to "%(message)s"')  # noqa: E501
    print('  --loop                    A fully qualified event loop name')
    print('                            E.g. "asyncio" or "asyncio.SelectorEventLoop"')  # noqa: E501
    print('                            It expects the respective module to already be present')  # noqa: E501
    print('  --shutdown-timeout        Maximum number of seconds to wait after SIGTERM is')  # noqa: E501
    print('                            sent to a worker process. Defaults to 30 (seconds)')  # noqa: E501
    print('  --version                 Print the httpout version and exit')
    print('  --help                    Show this help and exit')
    print()
    print('Please run "python3 -m tremolo --help" to see more available options')  # noqa: E501
    return 0


def bind(value='', **context):
    context['options']['host'] = None

    try:
        for bind in value.split(','):
            if ':\\' not in bind and ':' in bind:
                host, port = bind.rsplit(':', 1)
                app.listen(int(port), host=host.strip('[]') or None)
            else:
                app.listen(bind)
    except ValueError:
        print(f'Invalid --bind value "{value}"')
        return 1


def version(**context):
    print(
        'httpout %s (tremolo %s, %s %d.%d.%d, %s)' %
        (__version__,
         tremolo.__version__,
         sys.implementation.name,
         *sys.version_info[:3],
         sys.platform)
    )
    return 0


def threads(value, **context):
    try:
        context['options']['thread_pool_size'] = int(value)
    except ValueError:
        print(
            f'Invalid --thread-pool-size value "{value}". It must be a number'
        )
        return 1


def indexes(value, **context):
    context['options']['directory_index'] = value.split(',')


if __name__ == '__main__':
    options = tremolo.utils.parse_args(
        help=usage, bind=bind, version=version, thread_pool_size=threads,
        directory_index=indexes
    )

    if sys.argv[-1] != sys.argv[0] and not sys.argv[-1].startswith('-'):
        options['document_root'] = sys.argv[-1]

    if 'document_root' not in options:
        print('You must specify DOCUMENT_ROOT. Use "--help" for help')
        sys.exit(1)

    if 'server_name' not in options:
        options['server_name'] = 'HTTPOut'

    app.run(**options)
