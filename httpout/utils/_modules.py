# Copyright (c) 2024 nggit

from types import ModuleType


def cleanup_modules(modules, excludes=()):
    for module_name, module in modules.items():
        if hasattr(module, '__dict__'):
            for name, value in module.__dict__.items():
                if value in excludes or name.startswith('__'):
                    continue

                if (value is not module and
                        hasattr(value, '__dict__') and
                        not isinstance(value, (type, ModuleType))):
                    cleanup_modules(value.__dict__, excludes)

                module.__dict__[name] = None

        if not module_name.startswith('__'):
            modules[module_name] = None
