import sys
import os

HAS_ENGINE = False
my_engine = None

# Ensure the search path includes the native binary directory
_search_dirs = [
    os.path.dirname(__file__),
    os.path.dirname(os.path.dirname(__file__)),
    os.path.join(os.path.dirname(__file__), "binaries"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "binaries"),
]

for _d in _search_dirs:
    if os.path.isdir(_d) and _d not in sys.path:
        sys.path.insert(0, _d)

try:
    import my_engine as _eng
    my_engine = _eng
    HAS_ENGINE = True
except ImportError:
    try:
        from .. import my_engine as _eng
        my_engine = _eng
        HAS_ENGINE = True
    except ImportError:
        HAS_ENGINE = False
        print("WARNING: 'my_engine' native module not found. GPU overlay will not work.")
