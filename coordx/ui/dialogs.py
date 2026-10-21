from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QRadioButton, QVBoxLayout)

from ..export_dxf import DxfOptions
from ..i18n import tr
from ..textnorm import parse_float
from .theme import S2, S3, S4, S6


class DxfDialog(QDialog):
    CURRENT, ALL_ONE, ALL_SEP = range(3)

    def __init__(self, parent, n_parcels: int, settings):
        super().__init__(parent)
        self.setWindowTitle(tr("dxf_title"))
        self.settings = settings
        lay = QVBoxLayout(self)
        lay.setContentsMargins(S6, S6, S6, S4)
        lay.setSpacing(S3)

        lay.addWidget(QLabel(tr("dxf_contents"), objectName="heading"))
        self.checks = {}
        for key in ("points", "numbers", "boundary", "lengths", "table", "area"):
            cb = QCheckBox(tr(f"dxf_{key}"))
            cb.setChecked(settings.value(f"dxf/{key}", True, type=bool))
            lay.addWidget(cb)
            self.checks[key] = cb
        row = QHBoxLayout()
        row.setSpacing(S3)
        self.auto_h = QCheckBox(tr("dxf_auto"))
        self.auto_h.setChecked(settings.value("dxf/auto_h", True, type=bool))
        self.height = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=100, singleStep=0.25)
        self.height.setValue(settings.value("dxf/height", 1.5, type=float))
        self.height.setMinimumWidth(90)
        self.height.setEnabled(not self.auto_h.isChecked())
        self.auto_h.toggled.connect(lambda on: self.height.setEnabled(not on))
        row.addWidget(QLabel(tr("dxf_height")))
        row.addStretch()
        row.addWidget(self.auto_h)
        row.addWidget(self.height)
        lay.addSpacing(S2)
        lay.addLayout(row)

        self.which_head = QLabel(tr("dxf_which"), objectName="heading")
        lay.addSpacing(S3)
        lay.addWidget(self.which_head)
        self.group = QButtonGroup(self)
        self.radios = []
        for i, key in enumerate(("dxf_current", "dxf_all_one", "dxf_all_sep")):
            rb = QRadioButton(tr(key))
            self.group.addButton(rb, i)
            lay.addWidget(rb)
            self.radios.append(rb)
        self.group.button(self.ALL_ONE if n_parcels > 1 else self.CURRENT).setChecked(True)
        for w in [self.which_head, *self.radios]:
            w.setVisible(n_parcels > 1)

        lay.addSpacing(S3)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok = bb.button(QDialogButtonBox.Ok)
        ok.setText(tr("export_dxf"))
        ok.setObjectName("primary")
        bb.button(QDialogButtonBox.Cancel).setText(tr("cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.setMinimumWidth(380)

    def options(self) -> DxfOptions:
        for key, cb in self.checks.items():
            self.settings.setValue(f"dxf/{key}", cb.isChecked())
        self.settings.setValue("dxf/auto_h", self.auto_h.isChecked())
        self.settings.setValue("dxf/height", self.height.value())
        return DxfOptions(**{k: cb.isChecked() for k, cb in self.checks.items()},
                          text_height=None if self.auto_h.isChecked() else self.height.value())

    def which(self) -> int:
        return self.group.checkedId()


class PointDialog(QDialog):
    """Edit one point's number and coordinates."""

    def __init__(self, parent, point):
        super().__init__(parent)
        self.setWindowTitle(tr("edit_point"))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(S6, S6, S6, S4)
        lay.setSpacing(S4)
        form = QFormLayout()
        form.setHorizontalSpacing(S4)
        form.setVerticalSpacing(S3)
        self.fields = {}
        for key, label in (("no", "col_no"), ("x", "col_x"), ("y", "col_y"), ("z", "col_z")):
            v = getattr(point, key)
            ed = QLineEdit("" if v is None else (v if key == "no" else f"{v:.3f}"))
            ed.setLayoutDirection(Qt.LeftToRight)
            ed.setMinimumWidth(180)
            form.addRow(tr(label), ed)
            self.fields[key] = ed
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("ok"))
        bb.button(QDialogButtonBox.Ok).setObjectName("primary")
        bb.button(QDialogButtonBox.Cancel).setText(tr("cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.fields["x"].setFocus()
        self.fields["x"].selectAll()

    def values(self):
        return {"no": self.fields["no"].text().strip(), **{k: parse_float(self.fields[k].text()) for k in "xyz"}}
