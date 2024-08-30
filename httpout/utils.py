# Copyright (c) 2024 nggit

__all__ = ('is_safe_path', 'exec_module', 'mime_types')

import re  # noqa: E402

pattern = re.compile(r'^[\w\-\/\.]{1,255}$')


def is_safe_path(path):
    if not pattern.match(path) or '..' in path:
        return False

    return True


def exec_module(module, code=None):
    if code is None:
        with open(module.__file__, 'r') as f:
            code = compile(f.read(), '<string>', 'exec')
            exec(code, module.__dict__)  # nosec B102

        return code

    exec(code, module.__dict__)  # nosec B102


# https://developer.mozilla.org
# /en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
mime_types = {
    '.aac': 'audio/aac',
    '.abw': 'application/x-abiword',
    '.apng': 'image/apng',
    '.arc': 'application/x-freearc',
    '.avif': 'image/avif',
    '.avi': 'video/x-msvideo',
    '.azw': 'application/vnd.amazon.ebook',
    '.bin': 'application/octet-stream',
    '.bmp': 'image/bmp',
    '.bz': 'application/x-bzip',
    '.bz2': 'application/x-bzip2',
    '.cda': 'application/x-cdf',
    '.csh': 'application/x-csh',
    '.css': 'text/css',
    '.csv': 'text/csv',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # noqa: 501
    '.eot': 'application/vnd.ms-fontobject',
    '.epub': 'application/epub+zip',

    # Note: Windows and macOS might use 'application/x-gzip'
    '.gz': 'application/gzip',

    '.gif': 'image/gif',
    '.htm': 'text/html',
    '.html': 'text/html',
    '.ico': 'image/vnd.microsoft.icon',
    '.ics': 'text/calendar',
    '.jar': 'application/java-archive',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript',  # Or 'application/javascript'
    '.json': 'application/json',
    '.jsonld': 'application/ld+json',
    '.mid': 'audio/midi',
    '.midi': 'audio/midi',
    '.mjs': 'text/javascript',
    '.mp3': 'audio/mpeg',
    '.mp4': 'video/mp4',
    '.mpeg': 'video/mpeg',
    '.mpkg': 'application/vnd.apple.installer+xml',
    '.odp': 'application/vnd.oasis.opendocument.presentation',
    '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
    '.odt': 'application/vnd.oasis.opendocument.text',
    '.oga': 'audio/ogg',
    '.ogv': 'video/ogg',
    '.ogx': 'application/ogg',
    '.opus': 'audio/ogg',
    '.otf': 'font/otf',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
    '.php': 'application/x-httpd-php',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # noqa: 501
    '.rar': 'application/vnd.rar',
    '.rtf': 'application/rtf',
    '.sh': 'application/x-sh',
    '.svg': 'image/svg+xml',
    '.tar': 'application/x-tar',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.ts': 'video/mp2t',
    '.ttf': 'font/ttf',
    '.txt': 'text/plain',
    '.vsd': 'application/vnd.visio',
    '.wav': 'audio/wav',
    '.weba': 'audio/webm',
    '.webm': 'video/webm',
    '.webp': 'image/webp',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.xhtml': 'application/xhtml+xml',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # noqa: 501
    '.xml': 'application/xml',  # 'text/xml' is still used sometimes
    '.xul': 'application/vnd.mozilla.xul+xml',

    # Note: Windows might use 'application/x-zip-compressed'
    '.zip': 'application/zip',

    '.3gp': 'video/3gpp',  # 'audio/3gpp' if it doesn't contain video
    '.3g2': 'video/3gpp2',  # 'audio/3gpp2' if it doesn't contain video
    '.7z': 'application/x-7z-compressed'
}
