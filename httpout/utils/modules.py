# Copyright (c) 2024 nggit

import os
import sys

from types import ModuleType


def exec_module(module, code=None, max_size=8 * 1048576):
    if code is None:
        if os.stat(module.__file__).st_size > max_size:
            raise ValueError(f'File {module.__file__} exceeds the max_size')

        with open(module.__file__, 'r') as f:
            code = compile(f.read(), module.__file__, 'exec')
            exec(code, module.__dict__)  # nosec B102

        return code

    exec(code, module.__dict__)  # nosec B102


def cleanup_modules(modules, debug=0):
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
