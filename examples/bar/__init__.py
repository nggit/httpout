# package: bar

# test import itself
import bar
import httpout.run

# test relative imports
from . import baz  # noqa: F401
from .baz import world  # noqa: F401

assert httpout is bar
assert httpout.run is run  # noqa: F821
