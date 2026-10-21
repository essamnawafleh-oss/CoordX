from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class ImageView(QGraphicsView):
    """Source image with zoom/pan and a highlight on the selected table row."""

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
        pen = QPen(QColor(46, 134, 193, 160), 1.5)
        for b in boxes:
            if b is None:
                self._rows.append(None)
                continue
            r = self.scene().addRect(QRectF(b[0] - 3, b[1] - 3, b[2] - b[0] + 6, b[3] - b[1] + 6), pen,
                                     QBrush(QColor(46, 134, 193, 25)))
            self._rows.append(r)
        self.viewport().update()

    def select_row(self, index: int):
        for k, r in enumerate(self._rows):
            if r is None:
                continue
            if k == index:
                r.setPen(QPen(QColor(220, 53, 69), 2.5))
                r.setBrush(QBrush(QColor(220, 53, 69, 45)))
                self.ensureVisible(r, 60, 60)
            else:
                r.setPen(QPen(QColor(46, 134, 193, 160), 1.5))
                r.setBrush(QBrush(QColor(46, 134, 193, 25)))

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
            painter.setPen(QColor("#8A96A3"))
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self._msg)
            painter.restore()
