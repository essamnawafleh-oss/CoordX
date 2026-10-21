"""CoordX - كورد اكس: coordinate tables from images/PDF/Excel to AutoCAD DXF."""
import sys

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from coordx.i18n import set_lang
from coordx.ui.main_window import MainWindow
from coordx.ui.splash import SplashDialog
from coordx.ui.style import STYLESHEET, resource


def selftest(src, out):
    """CoordX --selftest <input> <report.txt>: read a file without the UI (used by the build check)."""
    from coordx.checks import analyze
    from coordx.sources import load_file
    lines = []
    for p in load_file(src):
        lines.append(f"{p.name}: {len(p.points)} points, area {analyze(p).area:.2f}")
        lines += [f"  {q.no} {q.x} {q.y}" for q in p.points]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--selftest":
        return selftest(sys.argv[2], sys.argv[3])
    app = QApplication(sys.argv)
    app.setApplicationName("CoordX")
    app.setOrganizationName("CoordX")
    app.setWindowIcon(QIcon(resource("assets", "icon.ico")))
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLESHEET)
    set_lang(QSettings("CoordX", "CoordX").value("lang", "ar"))

    win = MainWindow()
    SplashDialog().exec()
    win.show()
    files = [a for a in sys.argv[1:] if not a.startswith("-")]
    if files:
        win.load(files)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
