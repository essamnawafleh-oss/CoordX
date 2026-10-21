"""Live view of the DXF drawing, with point selection, editing and dragging."""

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsView, QMenu)

from ..i18n import tr

BACKGROUND = QColor("#212830")  # AutoCAD-like model space
LAYER_COLORS = {
    "POINTS": QColor("#FF4D4D"), "POINT_NO": QColor("#F2F2F2"), "BOUNDARY": QColor("#3DDC84"),
    "LENGTHS": QColor("#33D6E8"), "TABLE": QColor("#9AA4AE"), "AREA": QColor("#F5D442"),
}
SELECTED = QColor("#FF9F1C")
LEVEL_COLORS = {"error": QColor("#FF3B30"), "warn": QColor("#FFD60A")}
MARKER = 6  # point marker radius in screen pixels


class PointItem(QGraphicsEllipseItem):
    """A point marker that keeps the same screen size at any zoom."""

    def __init__(self, view, index, level):
        super().__init__(-MARKER, -MARKER, 2 * MARKER, 2 * MARKER)
        self.view, self.index, self.level = view, index, level
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10)
        self.set_selected(False)

    def set_selected(self, on):
        color = SELECTED if on else LEVEL_COLORS.get(self.level, LAYER_COLORS["POINTS"])
        r = MARKER * (1.6 if on or self.level else 1)
        self.setRect(-r, -r, 2 * r, 2 * r)
        self.setPen(QPen(color, 2.5 if on or self.level else 1.5))
        self.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 90 if on or self.level else 0)))

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        # the PDMODE 35 cross inside the circle
        painter.setPen(self.pen())
        r = self.rect().width() / 2 * 0.7
        painter.drawLine(QPointF(-r, -r), QPointF(r, r))
        painter.drawLine(QPointF(-r, r), QPointF(r, -r))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged and self.view.dragging is self:
            self.view._on_drag(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.view.point_clicked.emit(self.index)
            if self.view.drag_enabled:
                self.view.dragging = self
                self.setFlag(QGraphicsItem.ItemIsMovable, True)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.view.dragging is self:
            self.view.dragging = None
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            x, y = self.view.to_world(self.scenePos())
            if self.pos() != self.view._start_pos:
                # applied after the event returns: rebuilding the scene deletes this item
                QTimer.singleShot(0, lambda: self.view.point_moved.emit(self.index, round(x, 3), round(y, 3)))

    def mouseDoubleClickEvent(self, e):
        self.view.edit_requested.emit(self.index)

    def contextMenuEvent(self, e):
        self.view.point_clicked.emit(self.index)
        menu = QMenu()
        a_edit = menu.addAction(tr("edit_point"))
        a_ins = menu.addAction(tr("insert_after"))
        menu.addSeparator()
        a_del = menu.addAction(tr("delete_point"))
        chosen = menu.exec(e.screenPos())
        sig = {a_edit: self.view.edit_requested, a_ins: self.view.insert_after_requested,
               a_del: self.view.delete_requested}.get(chosen)
        if sig is not None:
            QTimer.singleShot(0, lambda: sig.emit(self.index))

    def hoverEnterEvent(self, e):
        x, y = self.view.to_world(self.scenePos())
        self.setToolTip(f"{self.view.labels.get(self.index, '')}\nX = {x:.3f}\nY = {y:.3f}")
        super().hoverEnterEvent(e)


class DrawingView(QGraphicsView):
    point_clicked = Signal(int)
    point_moved = Signal(int, float, float)
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    insert_after_requested = Signal(int)
    mouse_moved = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setBackgroundBrush(BACKGROUND)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLayoutDirection(Qt.LeftToRight)
        self.origin = (0.0, 0.0)
        self.items_by_index = {}
        self.labels = {}
        self.boundary = None
        self.boundary_pts = []
        self.boundary_closed = False
        self.drag_enabled = False
        self.dragging = None
        self._start_pos = None
        self._selected = None
        self._key = None
        self._msg = ""

    # ------------------------------------------------------------ geometry
    def to_scene(self, x, y):
        return QPointF(x - self.origin[0], -(y - self.origin[1]))

    def to_world(self, p: QPointF):
        return p.x() + self.origin[0], -p.y() + self.origin[1]

    def set_message(self, text):
        self._msg = text
        self.viewport().update()

    def set_drawing(self, key, ents, levels: dict, labels: dict):
        """Redraw. The view keeps its zoom when `key` (the parcel) is the same as before."""
        new_parcel = key != self._key
        self._key = key
        sc = self.scene()
        sc.clear()
        self.items_by_index, self.labels = {}, labels
        self.boundary, self.boundary_pts = None, []
        self.dragging = None
        if not ents:
            self.viewport().update()
            return
        if new_parcel or self.origin == (0.0, 0.0):
            p0 = next((e.data for e in ents if e.kind == "point"), None)
            if p0 is None:
                p0 = {"x": ents[0].data.get("pos", (0, 0))[0], "y": ents[0].data.get("pos", (0, 0))[1]}
            self.origin = (p0["x"], p0["y"])

        for e in ents:
            d = e.data
            color = LAYER_COLORS.get(e.layer, QColor("white"))
            pen = QPen(color, 0)  # cosmetic: 1 px at any zoom
            if e.kind == "poly":
                path = QPainterPath(self.to_scene(*d["pts"][0]))
                for x, y in d["pts"][1:]:
                    path.lineTo(self.to_scene(x, y))
                if d["closed"]:
                    path.closeSubpath()
                pen.setWidthF(1.6)
                pen.setCosmetic(True)
                item = sc.addPath(path, pen)
                if e.layer == "BOUNDARY":
                    self.boundary, self.boundary_pts, self.boundary_closed = item, list(d["pts"]), d["closed"]
            elif e.kind == "line":
                sc.addLine(self.to_scene(*d["a"]).x(), self.to_scene(*d["a"]).y(),
                           self.to_scene(*d["b"]).x(), self.to_scene(*d["b"]).y(), pen)
            elif e.kind == "text":
                self._add_text(d, color)
            elif e.kind == "point":
                item = PointItem(self, d["index"], levels.get(d["index"]))
                item.setPos(self.to_scene(d["x"], d["y"]))
                sc.addItem(item)
                self.items_by_index[d["index"]] = item

        # boundary vertex order follows the order of point entities
        self._vertex_of = {idx: k for k, idx in enumerate(sorted(self.items_by_index))}
        rect = sc.itemsBoundingRect()
        m = max(rect.width(), rect.height(), 1) * 0.5
        sc.setSceneRect(rect.adjusted(-m, -m, m, m))
        if new_parcel:
            self.fit()
            QTimer.singleShot(0, self.fit)
        if self._selected in self.items_by_index:
            self.items_by_index[self._selected].set_selected(True)

    def _add_text(self, d, color):
        font = QFont("Arial")
        font.setPixelSize(100)
        item = QGraphicsSimpleTextItem(d["text"])
        item.setFont(font)
        item.setBrush(color)
        fm = QFontMetricsF(font)
        cap = fm.capHeight() or fm.ascent() * 0.7
        s = d["height"] / cap
        w = fm.horizontalAdvance(d["text"])
        dx = -w / 2 if d["align"] == "center" else 0
        pos = self.to_scene(*d["pos"])
        t = QTransform()
        t.translate(pos.x(), pos.y())
        t.rotate(-d["rotation"])
        t.scale(s, s)
        t.translate(dx, -(fm.ascent() - cap / 2))
        item.setTransform(t)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene().addItem(item)

    # ------------------------------------------------------------ selection
    def select(self, index):
        if self._selected in self.items_by_index:
            self.items_by_index[self._selected].set_selected(False)
        self._selected = index
        item = self.items_by_index.get(index)
        if item is not None:
            item.set_selected(True)
            if not self.viewport().rect().contains(self.mapFromScene(item.scenePos())):
                self.centerOn(item)

    def fit(self):
        rect = self.scene().itemsBoundingRect()
        if rect.isValid() and not rect.isEmpty():
            self.fitInView(rect.adjusted(-rect.width() * 0.05, -rect.height() * 0.05,
                                         rect.width() * 0.05, rect.height() * 0.05), Qt.KeepAspectRatio)

    # ------------------------------------------------------------ dragging
    def _on_drag(self, item):
        x, y = self.to_world(item.scenePos())
        self.mouse_moved.emit(x, y)
        k = self._vertex_of.get(item.index)
        if self.boundary is None or k is None or k >= len(self.boundary_pts):
            return
        pts = list(self.boundary_pts)
        pts[k] = (x, y)
        path = QPainterPath(self.to_scene(*pts[0]))
        for px, py in pts[1:]:
            path.lineTo(self.to_scene(px, py))
        if self.boundary_closed:
            path.closeSubpath()
        self.boundary.setPath(path)

    # ------------------------------------------------------------ events
    def mousePressEvent(self, e):
        item = self.itemAt(e.position().toPoint())
        if isinstance(item, PointItem):
            self._start_pos = item.pos()
            # don't scroll the view while a point is being dragged
            self.setDragMode(QGraphicsView.NoDrag if self.drag_enabled else QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if self.dragging is None and self.scene().items():
            x, y = self.to_world(self.mapToScene(e.position().toPoint()))
            self.mouse_moved.emit(x, y)

    def wheelEvent(self, e):
        f = 1.25 if e.angleDelta().y() > 0 else 1 / 1.25
        self.scale(f, f)

    def mouseDoubleClickEvent(self, e):
        if isinstance(self.itemAt(e.position().toPoint()), PointItem):
            return super().mouseDoubleClickEvent(e)
        self.fit()

    def drawForeground(self, painter, rect):
        if not self.items_by_index and self._msg:
            painter.save()
            painter.resetTransform()
            painter.setPen(QColor("#9AA4AE"))
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self._msg)
            painter.restore()
        # small north arrow, like on the plans
        painter.save()
        painter.resetTransform()
        vr = self.viewport().rect()
        x, y = vr.right() - 28, vr.top() + 18
        painter.setPen(QPen(QColor("#C8D1DC"), 1.5))
        painter.setBrush(QColor("#C8D1DC"))
        painter.drawPolygon([QPointF(x, y), QPointF(x - 6, y + 18), QPointF(x, y + 13), QPointF(x + 6, y + 18)])
        painter.drawText(int(x - 5), int(y + 34), "N")
        painter.restore()
