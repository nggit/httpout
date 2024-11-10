# Copyright (c) 2024 nggit

import os

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize


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
        finally:
            for source in ext.sources:
                path = os.path.join(self.build_lib, source)

                if os.path.exists(path):
                    os.unlink(path)
                    print(f'Deleted: {path}')


extensions = [
    Extension(
        'httpout.utils.modules',
        sources=[os.path.join('httpout', 'utils', 'modules.pyx')],
        optional=True
    )
]

setup(
    ext_modules=cythonize(extensions),
    cmdclass={'build_ext': OptionalBuildExt},
    setup_requires=['Cython']
)
