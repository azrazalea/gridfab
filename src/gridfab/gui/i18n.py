"""Internationalization support for GridFab GUI using Python gettext."""

import gettext
from pathlib import Path

_localedir = Path(__file__).parent.parent / "locale"
_translation = gettext.translation("gridfab", _localedir, fallback=True)
_ = _translation.gettext
