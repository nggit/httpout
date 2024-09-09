
import asyncio
import time

from foo import hello

__globals__.counter += 1
MESSAGE = 'Done!'

time.sleep(0.1)


async def main():
    await hello()
    await asyncio.sleep(0.1)


if __name__ == '__main__':
    asyncio.run(main())
    print(MESSAGE)
