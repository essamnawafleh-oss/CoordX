"""CoordX line icons: one 24px grid, 1.75 stroke, round joins, tinted from the theme."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import theme

_PATHS = {
    "open": '<path d="M3 7.5V18a1.5 1.5 0 0 0 1.5 1.5h15A1.5 1.5 0 0 0 21 18v-8a1.5 1.5 0 0 0-1.5-1.5h-7L10 6H4.5A1.5 1.5 0 0 0 3 7.5z"/>',
    "new": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path d="M12 11v6M9 14h6"/>',
    "trash": '<path d="M4.5 6.5h15"/><path d="M9.5 6.5V4.5h5v2"/><path d="M6.5 6.5l1 13h9l1-13"/><path d="M10.5 10.5v6M13.5 10.5v6"/>',
    "dxf": '<path d="M12 3.5l8.5 4.5L12 12.5 3.5 8z"/><path d="M3.5 12L12 16.5 20.5 12"/><path d="M3.5 16L12 20.5 20.5 16"/>',
    "excel": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M3.5 14.5h17M9.5 4.5v15"/>',
    "csv": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path d="M8.5 12.5h7M8.5 16h7"/>',
    "undo": '<path d="M9 14.5L4.5 10 9 5.5"/><path d="M4.5 10h10a5 5 0 0 1 0 10H11"/>',
    "lang": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/><path d="M12 3.5c2.4 2.3 3.6 5.1 3.6 8.5s-1.2 6.2-3.6 8.5c-2.4-2.3-3.6-5.1-3.6-8.5S9.6 5.8 12 3.5z"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.6v.2"/>',
    "moon": '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
    "sun": '<circle cx="12" cy="12" r="3.75"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>',
    "fit": '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/>',
    "image": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><circle cx="9" cy="10" r="1.75"/><path d="M20.5 16l-5-5-8.5 8.5"/>',
    "drawing": '<path d="M5 18.5L9 6l6 3.5 4 9z"/><circle cx="5" cy="18.5" r="1.5"/><circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="9.5" r="1.5"/><circle cx="19" cy="18.5" r="1.5"/>',
    "add": '<path d="M12 5v14M5 12h14"/>',
    "insert": '<path d="M4 6.5h10M4 11.5h10M4 16.5h6"/><path d="M17.5 13.5v6M14.5 16.5h6"/>',
    "minus": '<path d="M4.5 6.5h15"/><path d="M9.5 6.5V4.5h5v2"/><path d="M6.5 6.5l1 13h9l1-13"/>',
    "up": '<path d="M6 14.5l6-6 6 6"/>',
    "down": '<path d="M6 9.5l6 6 6-6"/>',
    "swap": '<path d="M7 7.5h12M15.5 4l3.5 3.5-3.5 3.5"/><path d="M17 16.5H5M8.5 13L5 16.5 8.5 20"/>',
    "renumber": '<path d="M10 6.5h10M10 12h10M10 17.5h10"/><path d="M4.5 5.5l1.5-1v4"/><path d="M4.2 13.6c.3-.9 2.4-1 2.4.3 0 1-2.4 1.6-2.4 2.6h2.5"/>',
    "edit": '<path d="M14.5 5.5l4 4L9 19H5v-4z"/><path d="M12.5 7.5l4 4"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "rotl": '<path d="M4.5 9.5A8 8 0 1 1 6 17"/><path d="M4 4.5v5h5"/>',
    "rotr": '<path d="M19.5 9.5A8 8 0 1 0 18 17"/><path d="M20 4.5v5h-5"/>',
    "level": '<path d="M3.5 15.5l17-7"/><path d="M3.5 18.5h17"/><circle cx="12" cy="12" r="1.6"/>',
    "region": '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><path d="M8.5 10h7M8.5 14h7"/>',
    "reread": '<path d="M19.5 12a7.5 7.5 0 0 1-13 5.1"/><path d="M4.5 12a7.5 7.5 0 0 1 13-5.1"/><path d="M17.5 3.5v3.4h-3.4M6.5 20.5v-3.4h3.4"/>',
    "pdf": '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path d="M8.5 16.5h7M8.5 13h4"/>',
    "acad": '<path d="M13.5 4.5h6v6"/><path d="M19.5 4.5l-8 8"/><path d="M17.5 13.5v5A1.5 1.5 0 0 1 16 20H5.5A1.5 1.5 0 0 1 4 18.5V8A1.5 1.5 0 0 1 5.5 6.5h5"/>',
    "export": '<path d="M12 15V4.5M8 8.5l4-4 4 4"/><path d="M4.5 14v4A1.5 1.5 0 0 0 6 19.5h12a1.5 1.5 0 0 0 1.5-1.5v-4"/>',
}


def _svg(name: str, color: str) -> bytes:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>').encode()


def pixmap(name: str, size: int = 18, role: str = "text") -> QPixmap:
    ratio = 2  # crisp on high-DPI screens
    pm = QPixmap(size * ratio, size * ratio)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    QSvgRenderer(QByteArray(_svg(name, theme.c(role)))).render(p, QRectF(0, 0, size * ratio, size * ratio))
    p.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def icon(name: str, role: str = "text") -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, 18, role), QIcon.Normal)
    ic.addPixmap(pixmap(name, 18, "text3"), QIcon.Disabled)
    return ic


def dot(role: str, size: int = 10) -> QIcon:
    """Small filled status dot for list items."""
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(theme.c(role)))
    p.drawEllipse(2, 2, size * ratio - 4, size * ratio - 4)
    p.end()
    pm.setDevicePixelRatio(ratio)
    return QIcon(pm)
