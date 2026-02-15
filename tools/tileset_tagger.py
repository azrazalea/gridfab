#!/usr/bin/env python3
"""Deprecated — use `gridfab tag` or `gridfab-tagger` instead.

This script now delegates to the gridfab.tagger package.
"""

import sys
import warnings

warnings.warn(
    "tools/tileset_tagger.py is deprecated. Use 'gridfab tag' or 'gridfab-tagger' instead.",
    DeprecationWarning,
    stacklevel=1,
)

from gridfab.tagger.app import main

if __name__ == "__main__":
    main()
