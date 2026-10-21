from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import __version__
from ..i18n import tr
from .style import resource
from .theme import S1, S2, S3, S4, S6, S8


class SplashDialog(QDialog):
    """Welcome screen shown at start-up and from “About”."""

    def __init__(self, parent=None, about=False):
        super().__init__(parent)
        self.setObjectName("splash")
        self.setWindowTitle(tr("about") if about else tr("app_name"))
        self.setModal(True)
        self.setFixedWidth(660)
        if not about:
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(objectName="splashCard")
        outer.addWidget(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(S8 + S2, S8, S8 + S2, S6)
        lay.setSpacing(S4)

        head = QHBoxLayout()
        head.setSpacing(S4)
        logo = QLabel()
        logo.setPixmap(QPixmap(resource("assets", "icon.png")).scaled(64, 64, Qt.KeepAspectRatio,
                                                                       Qt.SmoothTransformation))
        head.addWidget(logo, 0, Qt.AlignTop)
        names = QVBoxLayout()
        names.setSpacing(S1)
        names.addWidget(QLabel(tr("app_name"), objectName="display"))
        names.addWidget(QLabel(f"{tr('app_alt_name')}   ·   {tr('version')} {__version__}", objectName="caption"))
        head.addLayout(names, 1)
        lay.addLayout(head)

        tag = QLabel(tr("app_tagline").replace("\n", " "), objectName="lead", wordWrap=True)
        lay.addWidget(tag)

        lay.addWidget(QFrame(objectName="rule"))

        dev = QVBoxLayout()
        dev.setSpacing(2)
        dev.addWidget(QLabel(tr("dev_label"), objectName="caption"))
        dev.addWidget(QLabel(tr("dev_name"), objectName="heading"))
        lay.addLayout(dev)

        dua = QFrame(objectName="accentPanel")
        dl = QVBoxLayout(dua)
        dl.setContentsMargins(S6, S4, S6, S4)
        dl.setSpacing(S2)
        dl.addWidget(QLabel(tr("free_line"), objectName="accentStrong", wordWrap=True))
        dl.addWidget(QLabel(tr("dua_line"), objectName="accentText", wordWrap=True))
        dl.addWidget(QLabel(tr("dua_text"), objectName="accentStrong", wordWrap=True))
        lay.addWidget(dua)

        row = QHBoxLayout()
        row.setContentsMargins(0, S3, 0, 0)
        row.addStretch()
        btn = QPushButton(tr("close") if about else tr("start"), objectName="primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        row.addWidget(btn)
        lay.addLayout(row)
