# Copyright (c) 2024 nggit

import os

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class OptionalBuildExt(build_ext):
    """Allow C extension building to fail gracefully."""
    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception:
            print(
                f'Failed to build {ext.name}. '
                'Falling back to pure Python version.'
            )
            dirname = os.path.join(self.build_lib, *ext.name.split('.')[:-1])

            with os.scandir(dirname) as entries:
                for entry in entries:
                    if (entry.name.startswith('modules.') and
                            not entry.name.endswith('.c') and
                            os.path.isfile(entry.path)):
                        os.unlink(entry.path)


extensions = [
    Extension(
        'httpout.utils.modules',
        sources=[os.path.join('httpout', 'utils', 'modules.c')],
        optional=True
    )
]

setup(
    ext_modules=extensions,
    cmdclass={'build_ext': OptionalBuildExt}
)
