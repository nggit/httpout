
import asyncio

# in routes it should be available as `__globals__.counter`
# you can't access this from inside the middleware, btw
counter = 0


# this middleware is usually not placed here but in a separate package
class _MyMiddleware:
    def __init__(self, app):
        app.add_middleware(self._on_request, 'request')
        app.add_middleware(self._on_response, 'response')

    async def _on_request(self, **server):
        response = server['response']

        response.set_header('X-Powered-By', 'foo')
        response.set_header('X-Hacker', 'bar')

    async def _on_response(self, **server):
        response = server['response']

        del response.headers[b'x-hacker']


# you have access to the httpout's app object when
# the worker starts (`__enter__`) or ends (`__exit__`)
# allowing you to inject middlewares and etc.
def __enter__(app):
    app.logger.info('entering %s', __file__)

    # apply middleware
    _MyMiddleware(app)

    app.ctx.sleep = asyncio.sleep(1)


# `async` is also supported
async def __exit__(app):
    app.logger.info('exiting %s', __file__)

    # incremented in `main.py`
    assert counter > 0
    await app.ctx.sleep
