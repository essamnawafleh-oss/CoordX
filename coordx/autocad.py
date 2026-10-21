"""Open a DXF in AutoCAD: the running AutoCAD first, else the installed one, else the default app."""
from __future__ import annotations

import glob
import os
import subprocess
import sys


def _running_autocad():
    """The AutoCAD that is already open, through COM (Windows + pywin32 only)."""
    try:
        import win32com.client  # type: ignore
        return win32com.client.GetActiveObject("AutoCAD.Application")
    except Exception:
        return None


def find_acad(saved: str | None = None) -> str | None:
    """Path of acad.exe: the one the user picked, then the registry, then the usual folders."""
    if saved and os.path.isfile(saved):
        return saved
    if sys.platform != "win32":
        return None
    found = []
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                root = winreg.OpenKey(hive, r"SOFTWARE\Autodesk\AutoCAD")
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(root)[0]):
                release = winreg.EnumKey(root, i)
                rkey = winreg.OpenKey(root, release)
                for j in range(winreg.QueryInfoKey(rkey)[0]):
                    try:
                        prod = winreg.OpenKey(rkey, winreg.EnumKey(rkey, j))
                        loc = winreg.QueryValueEx(prod, "AcadLocation")[0]
                    except OSError:
                        continue
                    exe = os.path.join(loc, "acad.exe")
                    if os.path.isfile(exe):
                        found.append((release, exe))
    except ImportError:
        pass
    if not found:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
            for exe in glob.glob(os.path.join(base, "Autodesk", "AutoCAD*", "acad.exe")):
                found.append((os.path.basename(os.path.dirname(exe)), exe))
    if not found:
        return None
    return sorted(found)[-1][1]  # newest release


def open_in_autocad(path: str, saved_exe: str | None = None) -> str:
    """Open `path`. Returns how: "running", "launched" or "default"."""
    path = os.path.abspath(path)
    app = _running_autocad()
    if app is not None:
        try:
            app.Documents.Open(path)
            app.Visible = True
            return "running"
        except Exception:
            pass
    exe = find_acad(saved_exe)
    if exe:
        subprocess.Popen([exe, path])
        return "launched"
    if sys.platform == "win32":
        os.startfile(path)  # whatever opens .dxf on this machine
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
    return "default"
