import os
import sys

import pytest

# Headless Linux needs the offscreen platform. On Windows keep the real one:
# offscreen there often finds no system fonts, so text would be missing.
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
