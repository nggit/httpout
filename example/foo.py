
from httpout import response
from bar import world


def hello():
    wait(response.write(b'Hello\n'))
    world()
