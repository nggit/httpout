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

![httpout](example/static/hello.gif)

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

## Features
httpout is designed to be fun. It's not built for perfectionists. httpout has:
- A [hybrid async and sync](#hybrid-async-and-sync), the two worlds can coexist in your script seamlessly
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
- `wait()` , runs a coroutine and wait until done
- `__main__`, a reference to your main route, available across your submodule imports
- `__server__`, a dict object containing basic HTTP request information and etc.

## License
MIT License
