import os
import sys

PRIMARY = "#1F4E78"
ACCENT = "#2E86C1"
ERROR_BG = "#F8D7DA"
WARN_BG = "#FFF3CD"
OK_FG = "#1E7B34"


def resource(*parts) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, *parts)


STYLESHEET = f"""
QMainWindow, QDialog {{ background: #F4F6F9; }}
QToolBar {{ background: white; border-bottom: 1px solid #DDE3EA; spacing: 4px; padding: 4px; }}
QToolBar QToolButton {{ padding: 6px 10px; border-radius: 6px; }}
QToolBar QToolButton:hover {{ background: #E8F1FA; }}
QListWidget, QTableWidget, QGraphicsView {{ background: white; border: 1px solid #DDE3EA; border-radius: 6px; }}
QListWidget::item {{ padding: 6px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; border-radius: 4px; }}
QHeaderView::section {{ background: {PRIMARY}; color: white; padding: 4px; border: none; font-weight: bold; }}
QPushButton {{ background: white; border: 1px solid #C8D1DC; border-radius: 6px; padding: 5px 10px; }}
QPushButton:hover {{ background: #E8F1FA; }}
QPushButton#primary {{ background: {PRIMARY}; color: white; border: none; padding: 8px 22px; font-weight: bold; }}
QPushButton#primary:hover {{ background: {ACCENT}; }}
QLineEdit, QDoubleSpinBox, QComboBox {{ background: white; border: 1px solid #C8D1DC; border-radius: 5px; padding: 4px; }}
QGroupBox {{ font-weight: bold; border: 1px solid #DDE3EA; border-radius: 6px; margin-top: 10px; padding-top: 8px; background: white; }}
QGroupBox::title {{ subcontrol-origin: margin; padding: 0 6px; }}
QLabel#summary_ok {{ color: {OK_FG}; font-weight: bold; }}
QLabel#summary_bad {{ color: #B02A37; font-weight: bold; }}
"""
