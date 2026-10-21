"""CoordX theme: one place for colour roles, type scale, spacing scale and the stylesheet.

Direction: an architectural-studio take on Windows 11 Fluent. Paper-white
surfaces in a clear ladder, graphite ink, one deep-teal accent used only on
primary actions and selection. The drawing canvas stays dark like a CAD
model space in both themes.
"""
import os
import tempfile

from PySide6.QtGui import QColor, QFont

# ---------------------------------------------------------------- spacing (4px base)
S1, S2, S3, S4, S6, S8 = 4, 8, 12, 16, 24, 32
RADIUS = 8        # cards, panels
RADIUS_CTL = 6    # buttons, inputs

# ---------------------------------------------------------------- type scale (pt)
TITLE_PT, BODY_PT, CAPTION_PT = 14, 10, 9
UI_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Noto Sans Arabic", "Noto Sans", "Arial"]
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"]

# ---------------------------------------------------------------- colour roles
LIGHT = {
    "window": "#F3F3EF", "panel": "#EAEAE5", "card": "#FFFFFF", "input": "#FFFFFF",
    "border": "#E0E0D9", "border_strong": "#C9C9C1",
    "text": "#1C1F23", "text2": "#5B6168", "text3": "#7A8087",
    "accent": "#0F6B66", "accent_hover": "#0C5A56", "accent_pressed": "#094845",
    "accent_text": "#FFFFFF", "accent_soft": "#DDEEEC", "accent_soft_text": "#0A4F4B",
    "header": "#F7F7F4", "alt_row": "#FAFAF8",
    "danger": "#B3261E", "danger_bg": "#FBE3E0", "warn": "#8A5A00", "warn_bg": "#FFF0D2",
    "ok": "#1E7A4C", "ok_bg": "#E0F2E8",
    "canvas": "#1E2328", "image_bg": "#EAEAE5",
}
DARK = {
    "window": "#16181B", "panel": "#1D2024", "card": "#23272C", "input": "#1A1D21",
    "border": "#31363C", "border_strong": "#454B52",
    "text": "#E8EAED", "text2": "#A7AEB6", "text3": "#8B929A",
    "accent": "#3DBDB3", "accent_hover": "#5ACDC4", "accent_pressed": "#2FA59C",
    "accent_text": "#06201E", "accent_soft": "#1C3A38", "accent_soft_text": "#9FE3DC",
    "header": "#1F2327", "alt_row": "#262A30",
    "danger": "#FF7A70", "danger_bg": "#4A2427", "warn": "#F2BE55", "warn_bg": "#43371B",
    "ok": "#62D9A0", "ok_bg": "#1C3A2C",
    "canvas": "#15181B", "image_bg": "#1A1D21",
}

_name = "light"
_roles = LIGHT


def name() -> str:
    return _name


def c(role: str) -> str:
    return _roles[role]


def qc(role: str) -> QColor:
    return QColor(_roles[role])


def font(size=BODY_PT, weight=QFont.Normal, mono=False) -> QFont:
    f = QFont()
    f.setFamilies(MONO_FAMILIES if mono else UI_FAMILIES)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def _asset(fname, svg) -> str:
    """QSS can only take indicator images from files: write the themed SVG once."""
    d = os.path.join(tempfile.gettempdir(), "coordx_theme")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{_name}_{fname}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path.replace("\\", "/")


def stylesheet() -> str:
    r = _roles
    check = _asset("check.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-7" '
                                f'fill="none" stroke="{r["accent_text"]}" stroke-width="2" stroke-linecap="round" '
                                f'stroke-linejoin="round"/></svg>')
    dot = _asset("dot.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="3.5" '
                            f'fill="{r["accent_text"]}"/></svg>')
    fam = ", ".join(f'"{f}"' for f in UI_FAMILIES)
    return f"""
* {{ font-family: {fam}; font-size: {BODY_PT}pt; color: {r["text"]}; }}
QMainWindow, QDialog {{ background: {r["window"]}; }}
QWidget#central {{ background: {r["window"]}; }}

/* ---------- surfaces */
QFrame#card {{ background: {r["card"]}; border: 1px solid {r["border"]}; border-radius: {RADIUS}px; }}
QFrame#card QLabel, QFrame#card QCheckBox, QFrame#card QRadioButton {{ background: transparent; }}
QFrame#soft {{ background: {r["panel"]}; border: none; border-radius: {RADIUS}px; }}
QFrame#rule {{ background: {r["border"]}; border: none; max-height: 1px; min-height: 1px; }}

/* ---------- splash */
QFrame#splashCard {{ background: {r["card"]}; border: 1px solid {r["border_strong"]}; border-radius: 12px; }}
QFrame#accentPanel {{ background: {r["accent_soft"]}; border: none; border-radius: {RADIUS}px; }}
QLabel#accentStrong {{ color: {r["accent_soft_text"]}; font-weight: 600; background: transparent; }}
QLabel#accentText {{ color: {r["accent_soft_text"]}; background: transparent; }}
QLabel#display {{ font-size: 24pt; font-weight: 600; }}
QLabel#lead {{ font-size: {BODY_PT + 2}pt; color: {r["text2"]}; }}
QFrame#splashCard QLabel {{ background: transparent; }}

/* ---------- type */
QLabel#title {{ font-size: {TITLE_PT}pt; font-weight: 600; }}
QLabel#heading {{ font-size: {BODY_PT + 1}pt; font-weight: 600; }}
QLabel#caption {{ font-size: {CAPTION_PT}pt; color: {r["text2"]}; }}
QLabel#metric {{ font-size: {TITLE_PT}pt; font-weight: 600; }}
QLabel#metricCaption {{ font-size: {CAPTION_PT}pt; color: {r["text2"]}; }}
QLabel#banner {{ border-radius: 11px; padding: 3px {S3}px; font-weight: 600; }}
QLabel#banner[state="ok"] {{ background: {r["ok_bg"]}; color: {r["ok"]}; }}
QLabel#banner[state="bad"] {{ background: {r["danger_bg"]}; color: {r["danger"]}; }}
QLabel#banner[state="none"] {{ background: {r["panel"]}; color: {r["text2"]}; }}
QLabel#note {{ color: {r["text2"]}; }}
QLabel#danger {{ color: {r["danger"]}; }}
QLabel#coords {{ font-family: "{MONO_FAMILIES[0]}", "{MONO_FAMILIES[1]}", monospace; color: {r["text2"]}; }}

/* ---------- toolbar */
QToolBar {{ background: {r["card"]}; border: none; border-bottom: 1px solid {r["border"]};
           padding: {S2}px {S4}px; spacing: {S1}px; }}
QToolBar::separator {{ background: {r["border"]}; width: 1px; margin: {S2}px {S2}px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: {RADIUS_CTL}px;
              padding: {S1 + 2}px {S3 - 2}px; color: {r["text"]}; }}
QToolButton:hover {{ background: {r["panel"]}; }}
QToolButton:pressed {{ background: {r["border"]}; }}
QToolButton:checked {{ background: {r["accent_soft"]}; color: {r["accent_soft_text"]}; }}
QToolButton:disabled {{ color: {r["text3"]}; }}
QToolButton:focus {{ border: 1px solid {r["accent"]}; }}
QToolButton#primary {{ background: {r["accent"]}; color: {r["accent_text"]}; font-weight: 600;
                      padding: {S1 + 2}px {S4}px; }}
QToolButton#primary:hover {{ background: {r["accent_hover"]}; }}
QToolButton#primary:pressed {{ background: {r["accent_pressed"]}; }}

/* ---------- buttons */
QPushButton {{ background: {r["card"]}; color: {r["text"]}; border: 1px solid {r["border_strong"]};
              border-radius: {RADIUS_CTL}px; padding: {S1 + 2}px {S3}px; }}
QPushButton:hover {{ background: {r["panel"]}; }}
QPushButton:pressed {{ background: {r["border"]}; }}
QPushButton:disabled {{ color: {r["text3"]}; border-color: {r["border"]}; background: {r["panel"]}; }}
QPushButton:focus {{ border: 1px solid {r["accent"]}; }}
QPushButton#primary, QPushButton:default {{ background: {r["accent"]}; color: {r["accent_text"]}; border: 1px solid {r["accent"]};
                                           font-weight: 600; padding: {S2}px {S6}px; }}
QPushButton#primary:hover, QPushButton:default:hover {{ background: {r["accent_hover"]}; border-color: {r["accent_hover"]}; }}
QPushButton#primary:pressed, QPushButton:default:pressed {{ background: {r["accent_pressed"]}; }}
QPushButton#ghost {{ background: transparent; border: 1px solid transparent; color: {r["text2"]}; }}
QPushButton#ghost:hover {{ background: {r["panel"]}; color: {r["text"]}; }}
QPushButton#ghost:pressed {{ background: {r["border"]}; }}

/* ---------- inputs */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{ background: {r["input"]}; border: 1px solid {r["border_strong"]};
    border-radius: {RADIUS_CTL}px; padding: {S1}px {S2 + 2}px; min-height: 22px; selection-background-color: {r["accent"]};
    selection-color: {r["accent_text"]}; }}
QLineEdit:hover, QDoubleSpinBox:hover, QComboBox:hover {{ border-color: {r["text3"]}; }}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1px solid {r["accent"]}; }}
QLineEdit:disabled, QDoubleSpinBox:disabled {{ background: {r["panel"]}; color: {r["text3"]}; border-color: {r["border"]}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}

/* ---------- tables and lists */
QTableView {{ background: {r["card"]}; alternate-background-color: {r["alt_row"]}; border: none;
             gridline-color: {r["border"]}; selection-background-color: {r["accent_soft"]};
             selection-color: {r["accent_soft_text"]}; }}
QTableView::item {{ padding: 0 {S2}px; }}
QTableView::item:selected {{ background: {r["accent_soft"]}; color: {r["accent_soft_text"]}; }}
QHeaderView {{ background: {r["header"]}; border: none; }}
QHeaderView::section {{ background: {r["header"]}; color: {r["text2"]}; font-weight: 600; border: none;
                       border-bottom: 1px solid {r["border"]}; padding: {S1 + 2}px {S2}px; }}
QTableCornerButton::section {{ background: {r["header"]}; border: none; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: {S2}px {S2}px; margin: 1px 0; border-radius: {RADIUS_CTL}px; color: {r["text"]}; }}
QListWidget::item:hover {{ background: {r["panel"]}; }}
QListWidget::item:selected {{ background: {r["accent_soft"]}; color: {r["accent_soft_text"]}; font-weight: 600; }}

/* ---------- tabs */
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; color: {r["text2"]}; padding: {S2}px {S4}px; margin: 0 {S1}px;
               border: none; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover:!selected {{ color: {r["text"]}; }}
QTabBar::tab:selected {{ color: {r["accent"]}; border-bottom: 2px solid {r["accent"]}; font-weight: 600; }}

/* ---------- check boxes, radio buttons, chips */
QCheckBox, QRadioButton {{ spacing: {S2}px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; border: 1px solid {r["border_strong"]};
                                                background: {r["input"]}; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {r["accent"]}; }}
QCheckBox::indicator:checked {{ background: {r["accent"]}; border-color: {r["accent"]}; image: url({check}); }}
QRadioButton::indicator:checked {{ background: {r["accent"]}; border-color: {r["accent"]}; image: url({dot}); }}
QCheckBox::indicator:disabled {{ background: {r["panel"]}; border-color: {r["border"]}; }}
QCheckBox#chip {{ background: {r["card"]}; border: 1px solid {r["border_strong"]}; border-radius: 12px;
                 padding: 3px {S3}px; color: {r["text2"]}; spacing: 0; }}
QCheckBox#chip::indicator {{ width: 0; height: 0; border: none; image: none; background: transparent; }}
QCheckBox#chip:hover {{ border-color: {r["text3"]}; color: {r["text"]}; }}
QCheckBox#chip:checked {{ background: {r["accent_soft"]}; border-color: {r["accent"]}; color: {r["accent_soft_text"]};
                         font-weight: 600; }}
QCheckBox#chip:focus {{ border-color: {r["accent"]}; }}

/* ---------- scroll bars */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {r["border_strong"]}; border-radius: 3px; min-height: 28px; }}
QScrollBar::handle:horizontal {{ background: {r["border_strong"]}; border-radius: 3px; min-width: 28px; }}
QScrollBar::handle:hover {{ background: {r["text3"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

/* ---------- menus, tooltips, status bar, splitter, progress */
QMenu {{ background: {r["card"]}; border: 1px solid {r["border"]}; border-radius: {RADIUS}px; padding: {S1}px; }}
QMenu::item {{ padding: {S2 - 2}px {S6}px {S2 - 2}px {S3}px; border-radius: {S1}px; }}
QMenu::item:selected {{ background: {r["accent_soft"]}; color: {r["accent_soft_text"]}; }}
QMenu::separator {{ height: 1px; background: {r["border"]}; margin: {S1}px {S2}px; }}
QToolTip {{ background: {r["card"]}; color: {r["text"]}; border: 1px solid {r["border"]}; padding: {S1 + 2}px {S2}px; }}
QStatusBar {{ background: {r["card"]}; border-top: 1px solid {r["border"]}; color: {r["text2"]}; }}
QStatusBar QLabel {{ color: {r["text2"]}; }}
QSplitter::handle {{ background: transparent; }}
QGraphicsView {{ border: 1px solid {r["border"]}; border-radius: {RADIUS_CTL}px; }}
QProgressBar {{ background: {r["panel"]}; border: none; border-radius: 4px; height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {r["accent"]}; border-radius: 4px; }}
QMessageBox QLabel {{ min-width: 260px; }}
"""


def apply(app, theme_name: str):
    global _name, _roles
    _name = "dark" if theme_name == "dark" else "light"
    _roles = DARK if _name == "dark" else LIGHT
    app.setFont(font())
    app.setStyleSheet(stylesheet())
