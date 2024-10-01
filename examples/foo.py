
from httpout import response
from bar import world

response.append_header('Foo', 'bar')
response.set_header('Foo', 'baz')


class Foo:
    def __del__(self):
        print(hello)

    async def hello(self):
        response.set_cookie('foo', 'bar')
        response.set_status(201, 'Created')
        response.set_content_type('text/plain')
        await response.write(b'Hello\n')
        world()


hello = Foo().hello
