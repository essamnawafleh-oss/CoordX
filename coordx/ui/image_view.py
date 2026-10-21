from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from . import theme


class ImageView(QGraphicsView):
    """Source image with zoom/pan, a highlight on the selected table row and region selection."""

    region_selected = Signal(QRectF)  # in image pixels
    region_cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setLayoutDirection(Qt.LeftToRight)
        self._path = None
        self._pix = None
        self._rows = []
        self._sel = None
        self._msg = ""
        self._selecting = False
        self._band = None
        self._band_start = None

    def set_message(self, text: str):
        self._msg = text
        self.viewport().update()

    def show_image(self, path, boxes):
        if path != self._path:
            self._path = path
            self.scene().clear()
            self._pix = None
            self._rows = []
            self._sel = None
            if path:
                pm = QPixmap(path)
                if not pm.isNull():
                    self._pix = self.scene().addPixmap(pm)
                    self.scene().setSceneRect(QRectF(pm.rect()))
            self.fit()
            QTimer.singleShot(0, self.fit)  # again once the view has its final size
        for item in self._rows:
            if item is not None:
                self.scene().removeItem(item)
        self._rows = []
        self._sel = None
        if self._pix is None:
            self.viewport().update()
            return
        pen = QPen(_alpha(theme.qc("accent"), 170), 1.5)
        for b in boxes:
            if b is None:
                self._rows.append(None)
                continue
            r = self.scene().addRect(QRectF(b[0] - 3, b[1] - 3, b[2] - b[0] + 6, b[3] - b[1] + 6), pen,
                                     QBrush(_alpha(theme.qc("accent"), 25)))
            self._rows.append(r)
        self.viewport().update()

    def select_row(self, index: int):
        for k, r in enumerate(self._rows):
            if r is None:
                continue
            if k == index:
                r.setPen(QPen(theme.qc("danger"), 2.5))
                r.setBrush(QBrush(_alpha(theme.qc("danger"), 45)))
                self.ensureVisible(r, 60, 60)
            else:
                r.setPen(QPen(_alpha(theme.qc("accent"), 170), 1.5))
                r.setBrush(QBrush(_alpha(theme.qc("accent"), 25)))

    # ------------------------------------------------------------ region selection
    def start_region_select(self):
        if self._pix is None:
            return False
        self._selecting = True
        self.setDragMode(QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.CrossCursor)
        return True

    def stop_region_select(self):
        self._selecting = False
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewport().unsetCursor()
        if self._band is not None:
            self.scene().removeItem(self._band)
            self._band = None

    def mousePressEvent(self, e):
        if self._selecting and e.button() == Qt.LeftButton:
            self._band_start = self.mapToScene(e.position().toPoint())
            pen = QPen(theme.qc("accent"), 2, Qt.DashLine)
            pen.setCosmetic(True)
            self._band = self.scene().addRect(QRectF(self._band_start, self._band_start), pen,
                                              QBrush(_alpha(theme.qc("accent"), 40)))
            self._band.setZValue(20)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._selecting and self._band is not None:
            self._band.setRect(QRectF(self._band_start, self.mapToScene(e.position().toPoint())).normalized())
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._selecting and self._band is not None and e.button() == Qt.LeftButton:
            rect = self._band.rect().intersected(self.sceneRect())
            self.stop_region_select()
            if rect.width() > 8 and rect.height() > 8:
                self.region_selected.emit(rect)
            else:
                self.region_cancelled.emit()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if self._selecting and e.key() == Qt.Key_Escape:
            self.stop_region_select()
            self.region_cancelled.emit()
            return
        super().keyPressEvent(e)

    def fit(self):
        if self._pix is not None:
            self.fitInView(self._pix, Qt.KeepAspectRatio)

    def wheelEvent(self, e):
        if self._pix is None:
            return
        f = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        self.scale(f, f)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._pix is not None and self.transform().m11() < 0.05:
            self.fit()

    def drawForeground(self, painter, rect):
        if self._pix is None and self._msg:
            painter.save()
            painter.resetTransform()
            painter.setPen(theme.qc("text3"))
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self._msg)
            painter.restore()


def _alpha(color: QColor, a: int) -> QColor:
    c = QColor(color)
    c.setAlpha(a)
    return c
