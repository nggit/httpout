
import asyncio
import time

from foo import hello

MESSAGE = 'Done!'

time.sleep(0.1)


async def main():
    __globals__.counter += 1

    await hello()
    await asyncio.sleep(0.1)


if __name__ == '__main__':
    wait(main())
    print(MESSAGE)
