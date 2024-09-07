
import asyncio


async def main():
    await asyncio.sleep(0.5)
    print('Done!')


run(main())
# leaves the thread while main() is still running
