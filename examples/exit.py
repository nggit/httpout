
from httpout import __server__

print('Hello, ', end='')

if __server__['QUERY_STRING']:
    exit(__server__['QUERY_STRING'] + '!\n')

exit(0)
