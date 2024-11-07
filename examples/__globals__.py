
import __main__

from httpout import app, __globals__

# just for testing. the only thing that matters here is the `app` :)
assert __main__ is __globals__

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
        response.set_header('X-Debug', 'bar')

    async def _on_response(self, **server):
        response = server['response']

        del response.headers[b'x-debug']


app.logger.info('entering %s', __file__)

# apply middleware
_MyMiddleware(app)


@app.on_worker_stop
async def _on_worker_stop(**worker):
    app.logger.info('exiting %s', __file__)

    # incremented in `main.py`
    assert counter > 0
