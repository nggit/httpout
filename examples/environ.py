
from httpout import request

print(request.method, request.environ['REQUEST_URI'])
