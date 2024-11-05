
import sys

from httpout import __server__

print('Hello, ', end='')

if __server__['QUERY_STRING']:
    sys.exit(__server__['QUERY_STRING'] + '!\n')

sys.exit(0)
