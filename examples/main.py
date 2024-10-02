
import asyncio
import time

# `__globals__` and `wait` are built-in.
# but can be optionally imported to satisfy linters
from httpout import __globals__, wait
from foo import hello

MESSAGES = ['Done!']

time.sleep(0.1)


async def main():
    __globals__.counter += 1

    await hello()
    await asyncio.sleep(0.1)


if __name__ == '__main__':
    wait(main())

    for message in MESSAGES:
        print(message)
