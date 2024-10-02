
import asyncio


async def main():
    await asyncio.sleep(0.5)
    print('Done!')


run(main())  # noqa: F821
print('OK')
# leaves the thread while main() is still running
# should print the 'OK' first
