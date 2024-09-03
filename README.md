# httpout
httpout allows you to execute your Python script from a web URL, the `print()` output goes to your browser.

This is the classic way to deploy your scripts to the web.
You just need to put your regular `.py` files as well as other static files in the document root and each will be routable from the web. No server reload is required!

It's similar to [CGI](https://en.wikipedia.org/wiki/Common_Gateway_Interface), except that httpout doesn't spawn a new process for each request,
making it more lightweight in terms of resource usage.
The disadvantage is that it's not isolated; your script is executed dynamically by the server using [exec()](https://docs.python.org/3/library/functions.html#exec) within the same process.

It provides a native experience for running your script from the web,
and the remaining drawbacks can be mitigated in this era using containerization. The tip is: **don't run Python as root**.

## How does it work?
httpout will assign every route either like `/hello.py` or `/index.py` with the name `__main__` and executes it as a module in a thread pool.
Monkey patching is done at the module-level by hijacking the [`__import__`](https://docs.python.org/3/library/functions.html#import__).

In the submodules perspective, the `__main__` object points to the main module such as `/hello.py`, rather than pointing to `sys.modules['__main__']` or the web server itself.

httpout does not perform a cache mechanism like standard imports or with [sys.modules](https://docs.python.org/3/library/sys.html#sys.modules) to avoid conflicts with other modules / requests. Because each request must have its own namespace.

To keep it simple, only the main module is cached (as code object).
The cache will be valid during HTTP Keep-Alive.
So if you just change the script there is no need to reload the server process, just wait until the connection is lost.

Keep in mind this may not work for running complex python scripts,
e.g. running other server processes or multithreaded applications as each route is not a real main thread.

![httpout](https://raw.githubusercontent.com/nggit/httpout/main/example/static/hello.gif)

## Install
```
python3 -m pip install --upgrade httpout
```

## Example
```python
# hello.py
import time


print('<pre>Hello...')

time.sleep(1)
print('and')

time.sleep(2)
print('Bye!</pre>')
```

Put `hello.py` in the `example/` folder, then run the httpout server with:
```
python3 -m httpout --port 8000 example/
```

and your `hello.py` can be accessed at [http://localhost:8000/hello.py](http://localhost:8000/hello.py).
If you don't want the `.py` suffix in the URL, you can instead create a `hello/` folder with `index.py` inside.

## Handling forms
This is an overview of how to view request methods and read form data.

```python
# form.py
import sys

from httpout import request, response


method_str = __server__.REQUEST_METHOD
method_bytes = request.method


if method_str != 'POST':
    response.set_status(405, 'Method Not Allowed')
    print('Method Not Allowed')
    sys.exit()


form_data = wait(request.form())

print(method_str, method_bytes, form_data)
```

It can also be written this way:
```python
# form.py
import sys

from httpout import request, response


method_str = __server__.REQUEST_METHOD
method_bytes = request.method


if method_str != 'POST':
    response.set_status(405, 'Method Not Allowed')
    print('Method Not Allowed')
    sys.exit()


async def main():
    form_data = await request.form()

    print(method_str, method_bytes, form_data)


wait(main())
```

Then you can do:
```
curl -d foo=bar http://localhost:8000/form.py
```

## Features
httpout is designed to be fun. It's not built for perfectionists. httpout has:
- A [hybrid async and sync](#hybrid-async-and-sync), the two worlds can coexist in your script seamlessly; It's not yet time to drop your favorite synchronous library
- More lightweight than running CGI scripts
- Your `print()`s are sent immediately line by line without waiting for the script to finish like a typical CGI
- No need for a templating engine, just do `if-else` and `print()` making your script portable for both CLI and web
- And more

## Hybrid async and sync
httpout server runs each module in a separate thread asynchronously. You can run blocking codes like `time.sleep()` without bothering server's loop.
You can also run coroutine functions at once with `wait()`. Although regular `asyncio.run()` will do. The difference is that the former uses an existing event loop rather than creating a new one every time.

```python
# ...
time.sleep(1)

async def main():
   await asyncio.sleep(1)

wait(main())
print('Done!')
```

For your information, `wait()` is a shorthand of:
```python
fut = run(main())
fut.result()
```

where `fut` is a [concurrent.futures.Future](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future) object.

## Builtin objects
No need to import anything to access these, except [`__main__`](https://docs.python.org/3/library/__main__.html) which can be imported to honor the semantics.
- `print()`
- `run()`, runs a coroutine without waiting, it returns a [concurrent.futures.Future](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future) object
- `wait()` , runs a coroutine and wait until done, it returns the result
- `__main__`, a reference to your main route, available across your submodule imports
- `__server__`, a dict object containing basic HTTP request information and etc.
- `__globals__`, a worker/app-level context. to initialize objects at worker start, you can place them in \_\_globals\_\_.py

## Security
It's important to note that httpout only focuses on request security;
to ensure that [path traversal](https://en.wikipedia.org/wiki/Directory_traversal_attack) through the URL never happens.

httpout will never validate the script you write,
you can still access objects like `os`, `eval()`, `open()`, even traversal out of the document root.
So this stage is your responsibility.

FYI, PHP used to have something called [Safe Mode](https://web.archive.org/web/20201014032613/https://www.php.net/manual/en/features.safe-mode.php), but it was deemed *architecturally incorrect*, so they removed it.

> The PHP safe mode is an attempt to solve the shared-server security problem.
> It is architecturally incorrect to try to solve this problem at the PHP level,
> but since the alternatives at the web server and OS levels aren't very realistic,
> many people, especially ISP's, use safe mode for now.

## License
MIT License
