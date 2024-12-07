# Copyright (c) 2024 nggit


class HTTPRequest:
    def __init__(self, request, environ):
        self.request = request
        self.environ = environ

    def __getattr__(self, name):
        return getattr(self.request, name)
