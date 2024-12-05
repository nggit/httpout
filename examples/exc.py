
from httpout import run
from httpout.exceptions import WebSocketException


print('Hi')


async def main():
    raise WebSocketException('')


run(main())
