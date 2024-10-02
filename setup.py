# Copyright (c) 2024 nggit

import glob
import os

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class OptionalBuildExt(build_ext):
    """Allow C extension building to fail gracefully."""
    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception:
            base_name = os.path.join(self.build_lib, *ext.name.split('.'))

            for file_name in glob.glob(base_name + '.*'):
                if not file_name.endswith('.c'):
                    print(
                        f'Failed to build {file_name}. '
                        'Falling back to pure Python version.'
                    )

                    if os.path.isfile(file_name):
                        os.unlink(file_name)


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
