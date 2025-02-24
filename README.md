# httpout
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=nggit_httpout&metric=coverage)](https://sonarcloud.io/summary/new_code?id=nggit_httpout)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=nggit_httpout&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nggit_httpout)

httpout is a runtime environment for Python files. It allows you to execute your Python scripts from a web URL, the `print()` output goes to your browser.

This is the classic way to deploy your scripts to the web.
You just need to put your regular `.py` files as well as other static files in the document root and each will be routable from the web. No server reload is required!

It provides a native experience for running your script from the web.

## How does it work?
httpout will assign every route either like `/hello.py` or `/index.py` with the name `__main__` and executes its corresponding file as a module in a thread pool.
Monkey patching is done at the module-level by hijacking the [`__import__`](https://docs.python.org/3/library/functions.html#import__).

In the submodules perspective, the `__main__` object points to the main module such as `/hello.py`, rather than pointing to `sys.modules['__main__']` or the web server itself.

httpout does not perform a cache mechanism like standard imports or with [sys.modules](https://docs.python.org/3/library/sys.html#sys.modules) to avoid conflicts with other modules / requests. Because each request must have its own namespace.

To keep it simple, only the main module is cached (as code object).
The cache will be valid during HTTP Keep-Alive.
So if you just change the script there is no need to reload the server process, just wait until the connection is lost.

Keep in mind this may not work for running complex python scripts,
e.g. running other server processes or multithreaded applications as each route is not a real main thread.

![httpout](https://raw.githubusercontent.com/nggit/httpout/main/examples/static/hello.gif)

## Installation
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

Put `hello.py` in the `examples/` folder, then run the httpout server with:
```
python3 -m httpout --port 8000 examples/
```

and your `hello.py` can be accessed at [http://localhost:8000/hello.py](http://localhost:8000/hello.py).
If you don't want the `.py` suffix in the URL, you can instead create a `hello/` folder with `index.py` inside.

## Handling forms
This is an overview of how to view request methods and read form data.

```python
# form.py
from httpout import wait, request, response


method_str = request.environ['REQUEST_METHOD']
method_bytes = request.method


if method_str != 'POST':
    response.set_status(405, 'Method Not Allowed')
    print('Method Not Allowed')
    exit()


# we can't use await outside the async context
# so wait() is used here because request.form() is a coroutine object
form_data = wait(request.form())

print(method_str, method_bytes, form_data)
```

It can also be written this way:
```python
# form.py
from httpout import run, request, response


method_str = request.environ['REQUEST_METHOD']
method_bytes = request.method


if method_str != 'POST':
    response.set_status(405, 'Method Not Allowed')
    print('Method Not Allowed')
    exit()


async def main():
    # using await instead of wait()
    form_data = await request.form()

    print(method_str, method_bytes, form_data)


run(main())
```

Then you can do:
```
curl -d foo=bar http://localhost:8000/form.py
```

## Features
httpout is designed to be fun. It's not built for perfectionists. httpout has:
- A [hybrid async and sync](https://httpout.github.io/hybrid.html), the two worlds can coexist in your script seamlessly; It's not yet time to drop your favorite synchronous library
- More lightweight than running CGI scripts
- Your `print()`s are sent immediately line by line without waiting for the script to finish like a typical CGI
- No need for a templating engine, just do `if-else` and `print()` making your script portable for both CLI and web
- And more

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
