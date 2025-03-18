# Copyright (c) 2024 nggit

import sys

from types import ModuleType

from libc.stdio cimport (FILE, fopen, fclose, fread, feof, ferror,
                         SEEK_SET, SEEK_END, fseek, ftell)


def exec_module(module, code=None, size_t max_size=8 * 1048576):
    cdef FILE* fp
    cdef char[4096] buf
    cdef size_t file_size, n
    cdef bytearray data

    if code is None:
        fp = fopen(module.__file__.encode('utf-8'), 'rb')

        if fp is NULL:
            raise OSError(f'Failed to open file: {module.__file__}')

        fseek(fp, 0, SEEK_END)
        file_size = ftell(fp)

        if file_size > max_size:
            fclose(fp)
            raise ValueError(f'File {module.__file__} exceeds the max_size')

        fseek(fp, 0, SEEK_SET)
        data = bytearray()

        while True:
            n = fread(buf, 1, sizeof(buf), fp)

            if n <= 0:
                break

            data.extend(buf[:n])

        if ferror(fp):
            fclose(fp)
            raise OSError(f'Error reading file: {module.__file__}')

        fclose(fp)

        code = compile(data, module.__file__, 'exec')
        exec(code, module.__dict__)

        return code

    exec(code, module.__dict__)


def cleanup_modules(modules, int debug=0):
    cdef str module_name, name
    cdef dict module_dict, value_dict

    if debug:
        if debug == 1:
            print('  cleanup_modules:')

        debug += 4

    for module_name, module in modules.items():
        module_dict = getattr(module, '__dict__', None)

        if module_dict:
            for name, value in module_dict.items():
                if name.startswith('__'):
                    continue

                value_module = getattr(value, '__module__', '__main__')

                if value_module != '__main__' and value_module in sys.modules:
                    continue

                if not (value is module or
                        isinstance(value, (type, ModuleType))):
                    value_dict = getattr(value, '__dict__', None)

                    if value_dict:
                        cleanup_modules(value_dict, debug)

                module_dict[name] = None

                if debug:
                    print(' ' * debug, ',-- deleted:', name, value)

        if not module_name.startswith('__'):
            modules[module_name] = None

            if debug:
                print(' ' * debug, '|')
                print(' ' * debug, 'deleted:', module_name, module)
