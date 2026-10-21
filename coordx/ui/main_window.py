import copy
import os
import subprocess
import sys

from PySide6.QtCore import QSettings, QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QProgressDialog, QPushButton, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QTabWidget, QToolBar, QVBoxLayout, QWidget)

from .. import __version__
from ..checks import analyze
from ..excel_io import write_csv, write_excel
from ..export_dxf import DxfOptions, build_drawing, export_dxf
from ..i18n import lang, set_lang, tr
from ..model import Parcel, Point
from ..sources import ALL_EXT, load_file
from ..textnorm import parse_float
from .dialogs import DxfDialog, PointDialog
from .drawing_view import DrawingView
from .image_view import ImageView
from .splash import SplashDialog
from . import icons, theme
from .style import resource
from .theme import S1, S2, S3, S4, S6

FIELDS = ("no", "x", "y", "z")
LAYER_KEYS = ("points", "numbers", "boundary", "lengths", "table", "area")
UNDO_LIMIT = 100


class LoadWorker(QThread):
    file_started = Signal(str, int, int)
    loaded = Signal(str, list)
    failed = Signal(str, str)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        for i, path in enumerate(self.paths):
            self.file_started.emit(path, i, len(self.paths))
            try:
                self.loaded.emit(path, load_file(path))
            except Exception as e:  # keep going with the other files
                self.failed.emit(path, str(e))


def open_folder(path):
    folder = os.path.dirname(path) if os.path.isfile(path) else path
    if sys.platform == "win32":
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("CoordX", "CoordX")
        self.parcels: list[Parcel] = []
        self.current: Parcel | None = None
        self.report = None
        self.worker = None
        self._loading = False
        self._undo = {}  # id(parcel) -> list of point snapshots

        self.setWindowIcon(QIcon(resource("assets", "icon.ico")))
        self.resize(1400, 860)
        self.setAcceptDrops(True)
        self._build()
        self.retranslate()
        self._show_parcel(None)

    # ------------------------------------------------------------------ UI
    def _card(self, margins=S4):
        card = QFrame(objectName="card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(margins, margins, margins, margins)
        lay.setSpacing(S3)
        return card, lay

    def _action(self, icon_name, slot, shortcut=None):
        a = QAction(self, triggered=slot)
        if shortcut is not None:
            a.setShortcut(shortcut)
        self._icon_names[a] = icon_name
        return a

    def _build(self):
        self._icon_names = {}
        tb = QToolBar(movable=False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        brand = QWidget()
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(0, 0, S4, 0)
        bl.setSpacing(S2)
        logo = QLabel()
        logo.setPixmap(QPixmap(resource("assets", "icon.png")).scaled(26, 26, Qt.KeepAspectRatio,
                                                                       Qt.SmoothTransformation))
        self.lbl_brand = QLabel(objectName="title")
        bl.addWidget(logo)
        bl.addWidget(self.lbl_brand)
        tb.addWidget(brand)

        self.act_open = self._action("open", self.open_files, QKeySequence.Open)
        self.act_new = self._action("new", self.new_parcel)
        self.act_remove = self._action("trash", self.remove_parcel)
        self.act_undo = self._action("undo", self.undo, QKeySequence.Undo)
        self.act_theme = self._action("moon", self.toggle_theme)
        self.act_lang = self._action("lang", self.toggle_language)
        self.act_about = self._action("info", self.about)
        self.act_xlsx = self._action("excel", self.export_excel)
        self.act_csv = self._action("csv", self.export_csv)
        self.act_dxf = self._action("dxf", self.export_dxf, QKeySequence.Save)
        for a in (self.act_open, self.act_new, self.act_remove):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.act_undo)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        for a in (self.act_theme, self.act_lang, self.act_about):
            tb.addAction(a)
        tb.addSeparator()
        for a in (self.act_xlsx, self.act_csv, self.act_dxf):
            tb.addAction(a)
        tb.widgetForAction(self.act_dxf).setObjectName("primary")
        for a in (self.act_theme, self.act_lang, self.act_about):
            tb.widgetForAction(a).setToolButtonStyle(Qt.ToolButtonIconOnly)

        # left: parcels
        left, ll = self._card()
        head = QHBoxLayout()
        self.lbl_parcels = QLabel(objectName="heading")
        self.lbl_count = QLabel(objectName="caption")
        head.addWidget(self.lbl_parcels)
        head.addStretch()
        head.addWidget(self.lbl_count)
        ll.addLayout(head)
        self.list = QListWidget()
        self.list.setIconSize(QSize(10, 10))
        self.list.currentRowChanged.connect(self._on_parcel_selected)
        self.lbl_list_hint = QLabel(objectName="caption", wordWrap=True)
        ll.addWidget(self.lbl_list_hint)
        ll.addWidget(self.list, 1)

        # middle: source image and drawing viewer, as tabs
        mid, midl = self._card(S2)
        img_tab = QWidget()
        ml = QVBoxLayout(img_tab)
        ml.setContentsMargins(S2, S3, S2, S2)
        ml.setSpacing(S2)
        top = QHBoxLayout()
        self.lbl_source = QLabel(objectName="caption")
        top.addWidget(self.lbl_source, 1)
        self.btn_fit = QPushButton(objectName="ghost", clicked=lambda: self.view.fit())
        self._icon_names[self.btn_fit] = "fit"
        top.addWidget(self.btn_fit)
        ml.addLayout(top)
        self.view = ImageView()
        ml.addWidget(self.view, 1)

        draw_tab = QWidget()
        dl = QVBoxLayout(draw_tab)
        dl.setContentsMargins(S2, S3, S2, S2)
        dl.setSpacing(S2)
        bar = QHBoxLayout()
        bar.setSpacing(S1 + 2)
        self.layer_checks = {}
        for key in LAYER_KEYS:
            cb = QCheckBox(objectName="chip")
            cb.setCursor(Qt.PointingHandCursor)
            cb.setChecked(self.settings.value(f"dxf/{key}", True, type=bool))
            cb.toggled.connect(lambda on, k=key: self._on_layer_toggled(k, on))
            bar.addWidget(cb)
            self.layer_checks[key] = cb
        bar.addStretch()
        self.chk_drag = QCheckBox()
        self.chk_drag.toggled.connect(lambda on: setattr(self.draw, "drag_enabled", on))
        bar.addWidget(self.chk_drag)
        self.btn_fit_draw = QPushButton(objectName="ghost", clicked=lambda: self.draw.fit())
        self._icon_names[self.btn_fit_draw] = "fit"
        bar.addWidget(self.btn_fit_draw)
        dl.addLayout(bar)
        self.draw = DrawingView()
        self.draw.point_clicked.connect(self._on_point_clicked)
        self.draw.point_moved.connect(self._on_point_moved)
        self.draw.edit_requested.connect(self.edit_point)
        self.draw.delete_requested.connect(self._on_point_delete)
        self.draw.insert_after_requested.connect(self._on_insert_after)
        self.draw.mouse_moved.connect(
            lambda x, y: self.lbl_coords.setText(f"⁦X  {x:,.3f}     Y  {y:,.3f}⁩"))
        dl.addWidget(self.draw, 1)
        foot = QHBoxLayout()
        self.lbl_hint = QLabel(objectName="caption")
        self.lbl_coords = QLabel(objectName="coords")
        foot.addWidget(self.lbl_hint, 1)
        foot.addWidget(self.lbl_coords)
        dl.addLayout(foot)

        self.tabs = QTabWidget(documentMode=True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.addTab(img_tab, "")
        self.tabs.addTab(draw_tab, "")
        midl.addWidget(self.tabs)

        # right: editor card and checks card
        right = QSplitter(Qt.Vertical)
        right.setHandleWidth(S4)
        right.setChildrenCollapsible(False)

        edit_card, el = self._card()
        form = QGridLayout()
        form.setHorizontalSpacing(S3)
        form.setVerticalSpacing(S1)
        self.lbl_name, self.lbl_area = QLabel(objectName="caption"), QLabel(objectName="caption")
        self.ed_name = QLineEdit()
        self.ed_name.editingFinished.connect(self._on_name_changed)
        self.ed_area = QLineEdit()
        self.ed_area.editingFinished.connect(self._on_area_changed)
        form.addWidget(self.lbl_name, 0, 0)
        form.addWidget(self.lbl_area, 0, 1)
        form.addWidget(self.ed_name, 1, 0)
        form.addWidget(self.ed_area, 1, 1)
        form.setColumnStretch(0, 3)
        form.setColumnStretch(1, 2)
        el.addLayout(form)

        self.table = QTableWidget(0, 4)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemChanged.connect(self._on_cell_changed)
        self.table.currentCellChanged.connect(self._on_row_changed)
        el.addWidget(self.table, 1)

        btns = QHBoxLayout()
        btns.setSpacing(S1)
        self.btn_add = QPushButton(clicked=self.add_row)
        self.btn_insert = QPushButton(objectName="ghost", clicked=self.insert_row)
        self.btn_del = QPushButton(objectName="ghost", clicked=self.delete_row)
        self.btn_up = QPushButton(objectName="ghost", clicked=lambda: self.move_row(-1))
        self.btn_down = QPushButton(objectName="ghost", clicked=lambda: self.move_row(1))
        self.btn_swap = QPushButton(objectName="ghost", clicked=self.swap_xy)
        self.btn_renum = QPushButton(objectName="ghost", clicked=self.renumber)
        for b, ic in ((self.btn_add, "add"), (self.btn_insert, "insert"), (self.btn_del, "minus"),
                      (self.btn_up, "up"), (self.btn_down, "down"), (self.btn_swap, "swap"),
                      (self.btn_renum, "renumber")):
            self._icon_names[b] = ic
        btns.addWidget(self.btn_add)
        btns.addStretch()
        for b in (self.btn_insert, self.btn_del, self.btn_up, self.btn_down, self.btn_swap, self.btn_renum):
            btns.addWidget(b)
        el.addLayout(btns)
        right.addWidget(edit_card)

        checks_card, cl = self._card()
        head = QHBoxLayout()
        self.lbl_checks = QLabel(objectName="heading")
        head.addWidget(self.lbl_checks)
        head.addStretch()
        self.lbl_summary = QLabel(objectName="banner")
        head.addWidget(self.lbl_summary)
        cl.addLayout(head)
        self.metrics_box = QWidget()
        metrics = QHBoxLayout(self.metrics_box)
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(S6)
        self.metric_vals, self.metric_caps = [], []
        for _ in range(3):
            box = QVBoxLayout()
            box.setSpacing(0)
            v, cap = QLabel(objectName="metric"), QLabel(objectName="metricCaption")
            box.addWidget(v)
            box.addWidget(cap)
            metrics.addLayout(box)
            self.metric_vals.append(v)
            self.metric_caps.append(cap)
        metrics.addStretch()
        cl.addWidget(self.metrics_box)
        self.lbl_stats = QLabel(objectName="note", wordWrap=True)
        self.lbl_msgs = QLabel(objectName="danger", wordWrap=True)
        cl.addWidget(self.lbl_stats)
        cl.addWidget(self.lbl_msgs)
        self.sides = QTableWidget(0, 4)
        self.sides.setAlternatingRowColors(True)
        self.sides.setShowGrid(False)
        self.sides.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sides.setSelectionMode(QAbstractItemView.NoSelection)
        self.sides.setFocusPolicy(Qt.NoFocus)
        self.sides.verticalHeader().setVisible(False)
        self.sides.verticalHeader().setDefaultSectionSize(28)
        self.sides.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sides.horizontalHeader().setHighlightSections(False)
        cl.addWidget(self.sides, 1)
        right.addWidget(checks_card)
        right.setSizes([470, 380])
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 2)
        self.table.setMinimumHeight(220)

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(S4)
        split.addWidget(left)
        split.addWidget(mid)
        split.addWidget(right)
        split.setSizes([220, 640, 560])
        split.setStretchFactor(1, 1)
        central = QWidget(objectName="central")
        cl2 = QVBoxLayout(central)
        cl2.setContentsMargins(S4, S4, S4, S4)
        cl2.addWidget(split)
        self.setCentralWidget(central)
        self.editor = right
        self._apply_theme_bits()

    def _apply_theme_bits(self):
        """Things the stylesheet can't reach: icons and the two canvases."""
        for obj, name in self._icon_names.items():
            role = "accent_text" if obj is self.act_dxf else "text"
            if obj is self.act_theme:
                name = "sun" if theme.name() == "dark" else "moon"
            obj.setIcon(icons.icon(name, role))
        self.tabs.setTabIcon(0, icons.icon("image", "text2"))
        self.tabs.setTabIcon(1, icons.icon("drawing", "text2"))
        self.view.setBackgroundBrush(theme.qc("image_bg"))
        self.draw.setBackgroundBrush(theme.qc("canvas"))

    def retranslate(self):
        rtl = lang() == "ar"
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        self.setWindowTitle(f"{tr('app_title')}  —  {tr('version')} {__version__}")
        self.lbl_brand.setText(tr("app_name"))
        for a, k in ((self.act_open, "open"), (self.act_new, "new_parcel"), (self.act_remove, "remove_parcel"),
                     (self.act_dxf, "export_dxf"), (self.act_xlsx, "export_excel"), (self.act_csv, "export_csv"),
                     (self.act_lang, "language"), (self.act_about, "about"), (self.act_undo, "undo"),
                     (self.act_theme, "theme")):
            a.setText(tr(k))
            a.setToolTip(tr(k))
        self.act_open.setToolTip(tr("open_tip"))
        self.lbl_parcels.setText(tr("parcels"))
        self.lbl_list_hint.setText(tr("list_hint"))
        self.btn_fit.setText(tr("fit"))
        self.lbl_name.setText(tr("name"))
        self.lbl_area.setText(tr("stated_area"))
        self.ed_area.setPlaceholderText(tr("stated_area_ph"))
        self.table.setHorizontalHeaderLabels([tr("col_no"), tr("col_x"), tr("col_y"), tr("col_z")])
        for b, k in ((self.btn_add, "add_row"), (self.btn_swap, "swap_xy")):
            b.setText(tr(k))
        for b, k in ((self.btn_insert, "insert_row"), (self.btn_del, "del_row"), (self.btn_up, "move_up"),
                     (self.btn_down, "move_down"), (self.btn_renum, "renumber"), (self.btn_swap, "swap_xy")):
            b.setToolTip(tr(k))
        self.lbl_checks.setText(tr("checks"))
        for cap, k in zip(self.metric_caps, ("points_n", "area_m2", "perimeter_m")):
            cap.setText(tr(k))
        self.sides.setHorizontalHeaderLabels([tr("side"), tr("length"), tr("on_plan"), tr("status")])
        self.view.set_message(tr("drop_hint"))
        self.draw.set_message(tr("viewer_empty"))
        self.tabs.setTabText(0, tr("tab_image"))
        self.tabs.setTabText(1, tr("tab_drawing"))
        for key, cb in self.layer_checks.items():
            cb.setText(tr(f"lay_{key}"))
        self.chk_drag.setText(tr("drag_mode"))
        self.btn_fit_draw.setText(tr("fit"))
        self.lbl_hint.setText(tr("viewer_hint"))
        self._refresh_list()
        if self.current:
            self._show_parcel(self.current)

    # ------------------------------------------------------------- loading
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        paths = [p for p in paths if os.path.splitext(p)[1].lower() in ALL_EXT]
        if paths:
            self.load(paths)

    def open_files(self):
        pattern = " ".join(f"*{e}" for e in sorted(ALL_EXT))
        paths, _ = QFileDialog.getOpenFileNames(self, tr("open"), self.settings.value("last_dir", ""),
                                                f"{tr('file_filter')} ({pattern})")
        if paths:
            self.settings.setValue("last_dir", os.path.dirname(paths[0]))
            self.load(paths)

    def load(self, paths):
        if self.worker and self.worker.isRunning():
            return
        self._errors = []
        self._added = 0
        self.progress = QProgressDialog(tr("reading"), None, 0, len(paths), self)
        self.progress.setWindowTitle(tr("app_name"))
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setMinimumDuration(0)
        self.progress.setValue(0)
        self.worker = LoadWorker(paths)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.loaded.connect(self._on_loaded)
        self.worker.failed.connect(lambda p, e: self._errors.append(tr("read_error", f=os.path.basename(p), e=e)))
        self.worker.finished.connect(self._on_load_finished)
        self.worker.start()

    def _on_file_started(self, path, i, total):
        self.progress.setLabelText(tr("reading_file", f=os.path.basename(path)) + f"  ({i + 1}/{total})")
        self.progress.setValue(i)

    def _on_loaded(self, path, parcels):
        found = [p for p in parcels if p.points]
        if not found:
            self._errors.append(tr("nothing_found", f=os.path.basename(path)))
            # keep the image so the user can type the points while looking at it
            found = parcels[:1]
        for p in found:
            self.parcels.append(p)
            self._added += 1
        self._refresh_list()
        if found and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def _on_load_finished(self):
        self.progress.setValue(self.progress.maximum())
        self.progress.close()
        if self._added:
            self.list.setCurrentRow(len(self.parcels) - self._added)
        self.statusBar().showMessage(tr("loaded", n=self._added), 8000)
        if self._errors:
            QMessageBox.warning(self, tr("app_name"), "\n\n".join(self._errors))

    # ------------------------------------------------------------- parcels
    def _refresh_list(self):
        row = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        for p in self.parcels:
            item = QListWidgetItem()
            self._style_list_item(item, p, analyze(p).issue_count == 0 and bool(p.points))
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.lbl_count.setText(str(len(self.parcels)) if self.parcels else "")
        self.lbl_list_hint.setVisible(not self.parcels)
        if 0 <= row < len(self.parcels):
            self.list.setCurrentRow(row)

    def _on_parcel_selected(self, row):
        self._show_parcel(self.parcels[row] if 0 <= row < len(self.parcels) else None)

    def new_parcel(self):
        p = Parcel(name=f"{'قطعة' if lang() == 'ar' else 'Parcel'} {len(self.parcels) + 1}", method="manual",
                   points=[Point(no="1")])
        self.parcels.append(p)
        self._refresh_list()
        self.list.setCurrentRow(len(self.parcels) - 1)

    def remove_parcel(self):
        row = self.list.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, tr("app_name"), tr("confirm_remove", n=self.parcels[row].name)) != QMessageBox.Yes:
            return
        del self.parcels[row]
        self._refresh_list()
        self.list.setCurrentRow(min(row, len(self.parcels) - 1))
        if not self.parcels:
            self._show_parcel(None)

    def _on_name_changed(self):
        if self.current and self.ed_name.text().strip() and self.ed_name.text().strip() != self.current.name:
            self.current.name = self.ed_name.text().strip()
            self._refresh_list()

    def _on_area_changed(self):
        if self.current:
            self.current.stated_area = parse_float(self.ed_area.text())
            self._recheck()

    # --------------------------------------------------------------- table
    def _show_parcel(self, p):
        self.current = p
        self.editor.setEnabled(p is not None)
        self._loading = True
        if p is None:
            self.ed_name.clear()
            self.ed_area.clear()
            self.table.setRowCount(0)
            self.sides.setRowCount(0)
            for lbl in (self.lbl_stats, self.lbl_msgs, self.lbl_source, *self.metric_vals):
                lbl.clear()
            self.lbl_summary.setText(tr("no_parcel"))
            _set_state(self.lbl_summary, "none")
            self.metrics_box.setVisible(False)
            self.view.show_image(None, [])
            self.draw.set_drawing(None, [], {}, {})
            self._loading = False
            return
        if p.image is None:
            self.tabs.setCurrentIndex(1)
        self.ed_name.setText(p.name)
        self.ed_area.setText("" if p.stated_area is None else f"{p.stated_area:g}")
        # isolate the file name so "1.jpg" doesn't turn into "jpg.1" in right-to-left text
        src = f"\u2066{os.path.basename(p.source)}\u2069" if p.source else ""
        if p.page:
            src += f"  ·  p{p.page}"
        self.lbl_source.setText(f"{tr('source')}: {src}  ·  {tr('method_' + (p.method or 'manual'))}" if src
                                else tr("method_manual"))
        self.table.setRowCount(len(p.points))
        for r, pt in enumerate(p.points):
            for c, f in enumerate(FIELDS):
                v = getattr(pt, f)
                self.table.setItem(r, c, QTableWidgetItem(v if f == "no" else _fmt(v)))
        self._loading = False
        self.view.show_image(p.image, [pt.bbox for pt in p.points])
        self._recheck()

    def _recheck(self):
        p = self.current
        if p is None:
            return
        rep = analyze(p)
        self.report = rep
        self._loading = True
        for r in range(self.table.rowCount()):
            for c, f in enumerate(FIELDS):
                item = self.table.item(r, c)
                if item is None:
                    continue
                flag = rep.cell_flags.get((r, f))
                if flag:
                    level, key, kw = flag
                    item.setBackground(theme.qc("danger_bg" if level == "error" else "warn_bg"))
                    item.setForeground(theme.qc("danger" if level == "error" else "warn"))
                    item.setToolTip(tr(key, **kw))
                else:
                    item.setData(Qt.BackgroundRole, None)  # let alternating rows show
                    item.setData(Qt.ForegroundRole, None)
                    item.setToolTip("")
        self._loading = False

        self.sides.setRowCount(len(rep.sides))
        for r, s in enumerate(rep.sides):
            vals = [f"\u2066{s.name}\u2069", f"{s.length:.2f}", "" if s.label is None else f"{s.label:.2f}", tr("st_" + s.status)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if s.status == "ok":
                    it.setForeground(theme.qc("ok"))
                elif s.status == "warn":
                    it.setBackground(theme.qc("danger_bg"))
                    it.setForeground(theme.qc("danger"))
                self.sides.setItem(r, c, it)

        self.metrics_box.setVisible(True)
        for lbl, v in zip(self.metric_vals, (f"{len(p.valid_points())}", f"\u2066{rep.area:,.2f}\u2069",
                                             f"\u2066{rep.perimeter:,.2f}\u2069")):
            lbl.setText(v)
        stats = []
        matched = sum(1 for s in rep.sides if s.status == "ok")
        if p.labels and rep.sides:
            stats.append(tr("sides_matched", m=matched, n=len(rep.sides)))
        if rep.area_status == "ok":
            stats.append(tr("area_ok"))
        elif rep.area_status == "warn" and p.stated_area:
            stats.append(tr("area_warn", d=rep.area_diff, p=rep.area_diff / p.stated_area * 100))
        self.lbl_stats.setText("<br>".join(stats))
        self.lbl_stats.setVisible(bool(stats))
        self.lbl_msgs.setText("<br>".join(tr(k, **kw) for _, k, kw in rep.messages))
        self.lbl_msgs.setVisible(bool(rep.messages))
        n = rep.issue_count
        self.lbl_summary.setText(tr("summary_ok") if n == 0 else tr("summary_issues", n=n))
        _set_state(self.lbl_summary, "ok" if n == 0 else "bad")
        self._update_list_item()
        self._redraw()

    # ------------------------------------------------------------- drawing
    def _view_options(self) -> DxfOptions:
        h = None if self.settings.value("dxf/auto_h", True, type=bool) else self.settings.value("dxf/height", 1.5,
                                                                                                  type=float)
        return DxfOptions(**{k: cb.isChecked() for k, cb in self.layer_checks.items()}, text_height=h)

    def _redraw(self):
        p = self.current
        if p is None or self.report is None:
            return
        levels = {}
        for (r, f), (level, _, _) in self.report.cell_flags.items():
            if f in ("x", "y") and levels.get(r) != "error":
                levels[r] = level
        labels = {k: f"{tr('col_no')} {pt.no}" for k, pt in enumerate(p.points)}
        self.draw.set_drawing(id(p), build_drawing(p, self._view_options(), self.report), levels, labels)
        r = self.table.currentRow()
        if r >= 0:
            self.draw.select(r)

    def _on_layer_toggled(self, key, on):
        self.settings.setValue(f"dxf/{key}", on)  # the DXF export uses the same choices
        self._redraw()

    def _on_row_changed(self, row, *_):
        self.view.select_row(row)
        self.draw.select(row)

    def _on_point_clicked(self, index):
        if index != self.table.currentRow():
            self.table.setCurrentCell(index, max(self.table.currentColumn(), 1))
        self.draw.select(index)

    def _apply_point(self, index, values: dict):
        """Change one point from the viewer, keeping the table and checks in sync."""
        p = self.current
        if p is None or not (0 <= index < len(p.points)):
            return
        self._push_undo()
        pt = p.points[index]
        for f, v in values.items():
            setattr(pt, f, v)
            pt.conf.pop(f, None)
        if "no" in values and "split" in pt.notes:
            pt.notes.remove("split")
        self._show_parcel(p)
        self.table.setCurrentCell(index, 1)

    def _on_point_moved(self, index, x, y):
        self._apply_point(index, {"x": x, "y": y})

    def edit_point(self, index):
        p = self.current
        if p is None or not (0 <= index < len(p.points)):
            return
        dlg = PointDialog(self, p.points[index])
        if dlg.exec() == PointDialog.Accepted:
            self._apply_point(index, dlg.values())

    def _on_point_delete(self, index):
        self.table.setCurrentCell(index, 1)
        self.delete_row()

    def _on_insert_after(self, index):
        p = self.current
        if p is None:
            return
        self._push_undo()
        a = p.points[index]
        b = next((q for q in p.points[index + 1:] + p.points[:index] if q.valid and q is not a), None)
        new = Point(no=_next_no(p))
        if a.valid and b is not None:  # start in the middle of the side, then let the user type the values
            new.x, new.y = round((a.x + b.x) / 2, 3), round((a.y + b.y) / 2, 3)
        p.points.insert(index + 1, new)
        self._show_parcel(p)
        self.table.setCurrentCell(index + 1, 1)
        self.edit_point(index + 1)

    # ---------------------------------------------------------------- undo
    def _push_undo(self):
        if self.current is None:
            return
        stack = self._undo.setdefault(id(self.current), [])
        stack.append(copy.deepcopy(self.current.points))
        del stack[:-UNDO_LIMIT]

    def undo(self):
        p = self.current
        stack = self._undo.get(id(p)) if p else None
        if not stack:
            return
        row = self.table.currentRow()
        p.points = stack.pop()
        self._show_parcel(p)
        self._refresh_list()
        if 0 <= row < len(p.points):
            self.table.setCurrentCell(row, 1)

    def _update_list_item(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.parcels) and self.report is not None:
            p = self.parcels[row]
            ok = self.report.issue_count == 0 and p.points
            self._style_list_item(self.list.item(row), p, bool(ok))

    def _style_list_item(self, item, p, ok):
        item.setText(f"{p.name}\n{tr('n_points', n=len(p.points))}")
        item.setIcon(icons.dot("ok" if ok else "warn"))
        item.setToolTip(tr("summary_ok") if ok else tr("needs_review"))

    def _on_cell_changed(self, item):
        if self._loading or self.current is None:
            return
        r, c = item.row(), item.column()
        if r >= len(self.current.points):
            return
        pt = self.current.points[r]
        f = FIELDS[c]
        self._push_undo()
        if f == "no":
            pt.no = item.text().strip()
        else:
            setattr(pt, f, parse_float(item.text()))
        pt.conf.pop(f, None)  # the user checked this value
        if f == "no" and "split" in pt.notes:
            pt.notes.remove("split")
        self._recheck()

    def _table_row(self):
        r = self.table.currentRow()
        return r if r >= 0 else None

    def add_row(self):
        if self.current is None:
            return
        self._push_undo()
        self.current.points.append(Point(no=_next_no(self.current)))
        self._show_parcel(self.current)
        self.table.setCurrentCell(len(self.current.points) - 1, 1)
        self.table.editItem(self.table.item(len(self.current.points) - 1, 1))

    def insert_row(self):
        r = self._table_row()
        if self.current is None or r is None:
            return self.add_row()
        self._push_undo()
        self.current.points.insert(r, Point())
        self._show_parcel(self.current)
        self.table.setCurrentCell(r, 1)

    def delete_row(self):
        r = self._table_row()
        if self.current is None or r is None:
            return
        self._push_undo()
        del self.current.points[r]
        self._show_parcel(self.current)
        self.table.setCurrentCell(min(r, len(self.current.points) - 1), 1)
        self._refresh_list()

    def move_row(self, d):
        r = self._table_row()
        pts = self.current.points if self.current else []
        if r is None or not (0 <= r + d < len(pts)):
            return
        self._push_undo()
        pts[r], pts[r + d] = pts[r + d], pts[r]
        self._show_parcel(self.current)
        self.table.setCurrentCell(r + d, 1)

    def swap_xy(self):
        if self.current is None:
            return
        self._push_undo()
        for pt in self.current.points:
            pt.x, pt.y = pt.y, pt.x
            cx, cy = pt.conf.pop("x", None), pt.conf.pop("y", None)
            if cy is not None:
                pt.conf["x"] = cy
            if cx is not None:
                pt.conf["y"] = cx
        self._show_parcel(self.current)

    def renumber(self):
        if self.current is None:
            return
        self._push_undo()
        for i, pt in enumerate(self.current.points, 1):
            pt.no = str(i)
            pt.conf.pop("no", None)
            if "split" in pt.notes:
                pt.notes.remove("split")
        self._show_parcel(self.current)

    # -------------------------------------------------------------- export
    def _check_before_export(self, parcels) -> bool:
        if not parcels:
            QMessageBox.information(self, tr("app_name"), tr("no_parcels"))
            return False
        n = sum(analyze(p).issue_count for p in parcels)
        if n:
            return QMessageBox.question(self, tr("app_name"), tr("export_issues", n=n)) == QMessageBox.Yes
        return True

    def _save_path(self, default_name, ext, title):
        start = os.path.join(self.settings.value("out_dir", self.settings.value("last_dir", "")), default_name + ext)
        path, _ = QFileDialog.getSaveFileName(self, title, start, f"*{ext}")
        if path:
            if not path.lower().endswith(ext):
                path += ext
            self.settings.setValue("out_dir", os.path.dirname(path))
        return path

    def _done(self, path):
        self.statusBar().showMessage(tr("saved", f=path), 10000)
        box = QMessageBox(QMessageBox.Information, tr("app_name"), tr("saved", f=path), parent=self)
        open_btn = box.addButton(tr("open_folder"), QMessageBox.ActionRole)
        box.addButton(tr("close"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == open_btn:
            open_folder(path)

    def _ready_parcels(self):
        return [p for p in self.parcels if p.valid_points()]

    def export_dxf(self):
        parcels = self._ready_parcels()
        if not parcels:
            return QMessageBox.information(self, tr("app_name"), tr("no_parcels"))
        dlg = DxfDialog(self, len(parcels), self.settings)
        if dlg.exec() != DxfDialog.Accepted:
            return
        opts, which = dlg.options(), dlg.which()
        for key, cb in self.layer_checks.items():  # the dialog may have changed the shared layer choices
            cb.blockSignals(True)
            cb.setChecked(getattr(opts, key))
            cb.blockSignals(False)
        self._redraw()
        if which == DxfDialog.CURRENT or len(parcels) == 1:
            chosen = [self.current] if self.current in parcels else parcels[:1]
        else:
            chosen = parcels
        if not self._check_before_export(chosen):
            return
        try:
            if which == DxfDialog.ALL_SEP and len(chosen) > 1:
                folder = QFileDialog.getExistingDirectory(self, tr("choose_folder"),
                                                          self.settings.value("out_dir", ""))
                if not folder:
                    return
                self.settings.setValue("out_dir", folder)
                for p in chosen:
                    export_dxf([p], os.path.join(folder, _safe_file(p.name) + ".dxf"), opts)
                self._done(folder)
            else:
                name = chosen[0].name if len(chosen) == 1 else "CoordX"
                path = self._save_path(_safe_file(name), ".dxf", tr("export_dxf"))
                if path:
                    export_dxf(chosen, path, opts)
                    self._done(path)
        except Exception as e:
            QMessageBox.critical(self, tr("app_name"), tr("save_error", e=e))

    def export_excel(self):
        parcels = self._ready_parcels()
        if not self._check_before_export(parcels):
            return
        name = parcels[0].name if len(parcels) == 1 else "CoordX"
        path = self._save_path(_safe_file(name), ".xlsx", tr("export_excel"))
        if not path:
            return
        try:
            write_excel(parcels, [analyze(p) for p in parcels], path)
            self._done(path)
        except Exception as e:
            QMessageBox.critical(self, tr("app_name"), tr("save_error", e=e))

    def export_csv(self):
        parcels = self._ready_parcels()
        if not self._check_before_export(parcels):
            return
        name = parcels[0].name if len(parcels) == 1 else "CoordX"
        path = self._save_path(_safe_file(name), ".csv", tr("export_csv"))
        if not path:
            return
        try:
            write_csv(parcels, path)
            self._done(path)
        except Exception as e:
            QMessageBox.critical(self, tr("app_name"), tr("save_error", e=e))

    # ---------------------------------------------------------------- misc
    def toggle_theme(self):
        theme.apply(QApplication.instance(), "light" if theme.name() == "dark" else "dark")
        self.settings.setValue("theme", theme.name())
        self._apply_theme_bits()
        self._refresh_list()
        if self.current:
            self._recheck()

    def toggle_language(self):
        set_lang("en" if lang() == "ar" else "ar")
        self.settings.setValue("lang", lang())
        self.retranslate()

    def about(self):
        SplashDialog(self, about=True).exec()


def _set_state(widget, state):
    """Switch a dynamic-property QSS state and re-polish so the style updates."""
    widget.setProperty("state", state)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _fmt(v):
    if v is None:
        return ""
    s = f"{v:.3f}"
    # keep at least two decimals, as on survey plans
    if s.endswith("0"):
        s = s[:-1]
    return s


def _next_no(parcel):
    nums = [int(p.no) for p in parcel.points if p.no.isdigit()]
    return str(max(nums) + 1) if nums else str(len(parcel.points) + 1)


def _safe_file(name):
    import re
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip() or "CoordX"
