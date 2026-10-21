from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import __version__
from ..i18n import tr
from .style import PRIMARY, resource


class SplashDialog(QDialog):
    """Welcome screen shown at start-up and from “About”."""

    def __init__(self, parent=None, about=False):
        super().__init__(parent)
        self.setWindowTitle(tr("about") if about else tr("app_name"))
        self.setModal(True)
        self.setMinimumWidth(560)
        if not about:
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(f"""
            QDialog {{ background: white; border: 2px solid {PRIMARY}; border-radius: 10px; }}
            QLabel {{ color: #22313F; }}
            QLabel#title {{ color: {PRIMARY}; }}
            QLabel#dua {{ color: #6B4E16; background: #FFF8E6; border-radius: 8px; padding: 10px; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 28, 36, 24)
        lay.setSpacing(10)

        logo = QLabel(alignment=Qt.AlignCenter)
        pm = QPixmap(resource("assets", "icon.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(logo)

        title = QLabel(tr("app_title"), objectName="title", alignment=Qt.AlignCenter)
        title.setFont(QFont(title.font().family(), 22, QFont.Bold))
        lay.addWidget(title)

        tag = QLabel(tr("app_tagline"), alignment=Qt.AlignCenter)
        tag.setFont(QFont(tag.font().family(), 11))
        lay.addWidget(tag)

        line = QFrame(frameShape=QFrame.HLine)
        line.setStyleSheet("color: #DDE3EA;")
        lay.addWidget(line)

        dev = QLabel(f"{tr('dev_label')}:  <b>{tr('dev_name')}</b>", alignment=Qt.AlignCenter)
        dev.setFont(QFont(dev.font().family(), 12))
        lay.addWidget(dev)

        dua = QLabel(f"<b>{tr('free_line')}</b><br>{tr('dua_line')}<br><br><b>{tr('dua_text')}</b>",
                     objectName="dua", alignment=Qt.AlignCenter, wordWrap=True)
        dua.setFont(QFont(dua.font().family(), 11))
        lay.addWidget(dua)

        ver = QLabel(f"{tr('version')} {__version__}", alignment=Qt.AlignCenter)
        ver.setStyleSheet("color: #8A96A3;")
        lay.addWidget(ver)

        row = QHBoxLayout()
        row.addStretch()
        btn = QPushButton(tr("close") if about else tr("start"), objectName="primary")
        btn.setStyleSheet(f"background:{PRIMARY}; color:white; border:none; border-radius:6px; padding:9px 30px; font-weight:bold;")
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        row.addWidget(btn)
        row.addStretch()
        lay.addLayout(row)
