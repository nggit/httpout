
import asyncio
import time

from foo import hello

MESSAGE = 'Done!'

time.sleep(0.1)


async def main():
    await hello()
    await asyncio.sleep(0.1)


if __name__ == '__main__':
    asyncio.run(main())
    print(MESSAGE)
