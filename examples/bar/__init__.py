# package: bar

# test import itself
import  bar
import httpout.run

assert httpout is bar
assert httpout.run is run

# test relative imports
from . import baz
from .baz import world
