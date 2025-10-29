from __future__ import annotations

# (opcional) encoding o docstring aquí
# -*- coding: utf-8 -*-
"""Autogeoreferencer dialog"""

import os
import re
import tempfile
from uuid import uuid4
# ... resto de imports ..


# autogeoreferencer_dialog.py — versión reforzada
from qgis.core import QgsWkbTypes, QgsGeometry


from uuid import uuid4
from typing import Optional

from .ui_main_window import Ui_MainWindow

from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QPushButton, QMessageBox,
    QWidget, QFrame
)
try:
    from qgis.PyQt.QtWidgets import QAction  # PyQt5/QGIS
except Exception:  # PySide6 fallback
    from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtGui import QPixmap, QImage, QColor, QPainter
from qgis.PyQt.QtCore import Qt, QSize

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsMapSettings,
    QgsPointXY,
)

# Renderer job desde qgis.core con fallbacks
try:
    from qgis.core import QgsMapRendererParallelJob as _RendererJob
except Exception:
    try:
        from qgis.core import QgsMapRendererSequentialJob as _RendererJob
    except Exception:
        _RendererJob = None  # último recurso: CustomPainter

# Intentar importar QgsMapRendererCustomPainterJob si está disponible (entornos sin los jobs paralelos/secuenciales)
try:
    from qgis.core import QgsMapRendererCustomPainterJob
except Exception:
    QgsMapRendererCustomPainterJob = None

from qgis.gui import (
    QgsMapTool, QgsMapCanvas, QgsRubberBand
)

# GDAL
from osgeo import gdal, osr


def is_gdal_backed(layer: QgsRasterLayer) -> bool:
    """True si la capa es archivo GDAL (GeoTIFF, etc.), False si es servicio WMS/XYZ/WMTS."""
    if not isinstance(layer, QgsRasterLayer):
        return False
    src = (layer.source() or "").lower()
    if src.startswith("context:") or "url=" in src or src.startswith("type=xyz") or src.startswith("wms") or "service=" in src:
        return False
    try:
        return os.path.exists(layer.dataProvider().dataSourceUri().split("|")[0])
    except Exception:
        return False


def temp_file(suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix=f"autogeo_{uuid4().hex[:6]}_", suffix=suffix)
    os.close(fd)
    return path


class RectangleMapTool(QgsMapTool):
    """Herramienta para dibujar un rectángulo y devolver su QgsRectangle en CRS del canvas."""
    def __init__(self, canvas: QgsMapCanvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.start_point: Optional[QgsPointXY] = None
        self.rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setColor(QColor(255, 0, 0, 180))
        self.rb.setWidth(2)

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.rb.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if not self.start_point:
            return
        p2 = self.toMapCoordinates(event.pos())
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = p2.x(), p2.y()
        pts = [QgsPointXY(x1, y1), QgsPointXY(x2, y1), QgsPointXY(x2, y2), QgsPointXY(x1, y2)]
        self.rb.setToGeometry(QgsGeometry.fromPolygonXY([pts]), None)

    def canvasReleaseEvent(self, event):
        if not self.start_point:
            return
        end_point = self.toMapCoordinates(event.pos())
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = end_point.x(), end_point.y()
        rect = QgsRectangle(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        self.callback(rect)

    def deactivate(self):
        super().deactivate()
        self.rb.reset(QgsWkbTypes.PolygonGeometry)

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.setWindowTitle("Autogeoreferencer")

        self.canvas: Optional[QgsMapCanvas] = iface.mapCanvas() if iface else None
        if not self.canvas:
            self._message("No se encontró el canvas de QGIS (iface.mapCanvas()).", level="warning")

        # Herramienta rectángulo
        self.tool_rectangle = RectangleMapTool(self.canvas, self._on_rectangle_selected) if self.canvas else None

        # Previsualización
        self.preview_label = QLabel("Previsualización")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Box)
        self.preview_label.setMinimumSize(200, 200)
        
        # Intento incrustar en un contenedor definido en la UI (incluye frame_image_ortorect)
        candidates = (
            "frame_image_ortorect",  # ← tu frame
            "frame_image",
            "previewFrame",
            "frameImage",
            "framePreview",
            "preview_container",
        )
        self._preview_container = None
        for nm in candidates:
            w = getattr(self, nm, None)
            if isinstance(w, QWidget):
                self._preview_container = w
                break

        if self._preview_container:
            lay = self._preview_container.layout()
            if lay is None:
                lay = QVBoxLayout(self._preview_container)
                self._preview_container.setLayout(lay)
            lay.addWidget(self.preview_label)
        else:
            # fallback: crea un contenedor simple
            holder = QWidget(self)
            holder.setLayout(QVBoxLayout())
            holder.layout().addWidget(self.preview_label)
            holder.setMinimumHeight(220)
            self._preview_container = holder

        if isinstance(self._preview_container, QWidget):
            lay = self._preview_container.layout()
            if lay is None:
                lay = QVBoxLayout(self._preview_container)
                self._preview_container.setLayout(lay)
            lay.addWidget(self.preview_label)
        else:
            holder = QWidget(self)
            holder.setLayout(QVBoxLayout())
            holder.layout().addWidget(self.preview_label)
            holder.setMinimumHeight(220)

        # Estado
        self._basemap_layer: Optional[QgsRasterLayer] = None
        self._last_preview_path: Optional[str] = None
        self._last_clip_layer_id: Optional[str] = None

        # Conectar UI
        self._wire_ui_inputs()

    # ---------------- Utilidades de UI ----------------
    def _message(self, text: str, level: str = "info"):
        if not self.iface:
            return
        mb = self.iface.messageBar()
        if level == "warning":
            mb.pushWarning("Autogeoreferencer", text)
        elif level == "error":
            mb.pushCritical("Autogeoreferencer", text)
        else:
            mb.pushInfo("Autogeoreferencer", text)

    def _get_preview_container(self) -> QWidget:
        return self._preview_container if isinstance(self._preview_container, QWidget) else self.preview_label

    def _wire_ui_inputs(self):
        """Conecta cualquier QAction/QPushButton que parezca ser 'Cargar desde basemap'. Si no encuentra nada, crea un botón de fallback."""
        connected = 0

        # 1) Buscar acciones por objectName/texto
        patterns = [
            r"action.*(base\s*map|basemap|referencia.*base|cargar.*base)",
            r"(base\s*map|basemap|referencia.*base|cargar.*base)"
        ]
        def _match(name_or_text: str) -> bool:
            s = (name_or_text or "").lower()
            return any(re.search(p, s) for p in patterns)

        # Acciones de menú/toolbar
        for act in self.findChildren(QAction):
            if _match(act.objectName()) or _match(act.text()):
                act.triggered.connect(self.select_from_basemap)
                connected += 1

        # Botones
        for btn in self.findChildren(QPushButton):
            if _match(btn.objectName()) or _match(btn.text()):
                btn.clicked.connect(self.select_from_basemap)
                connected += 1

        # 2) Si no encontró nada, crea botón fallback dentro de la ventana
        if connected == 0:
            fb = QPushButton("Capturar desde Basemap (fallback)", self)
            fb.clicked.connect(self.select_from_basemap)
            # lo ponemos al final del contenedor de preview si existe, o en la ventana
            container = self._get_preview_container()
            lay = container.layout() if isinstance(container, QWidget) else None
            if lay is None and isinstance(container, QWidget):
                lay = QVBoxLayout(container)
                container.setLayout(lay)
            if lay:
                lay.addWidget(fb)
            else:
                # último recurso: layout propio
                holder = QWidget(self)
                holder.setLayout(QVBoxLayout())
                holder.layout().addWidget(fb)

        self._message(f"Acciones/botones conectados: {connected}")

    # ---------------- Lógica principal ----------------
    def select_from_basemap(self):
        if not self.canvas or not self.tool_rectangle:
            self._message("Canvas no disponible. ¿Abriste la ventana desde QGIS?", level="warning")
            return
        self._basemap_layer = self._pick_visible_raster_layer()
        if not self._basemap_layer:
            self._message("No hay una capa raster visible para usar como referencia.", level="warning")
            return
        self.canvas.setMapTool(self.tool_rectangle)
        self._message("Dibuja un rectángulo sobre el mapa para recortar.")

    def _pick_visible_raster_layer(self) -> Optional[QgsRasterLayer]:
        layers = [l for l in QgsProject.instance().layerTreeRoot().layerOrder()]
        raster_layers = [l for l in layers if isinstance(l, QgsRasterLayer)]

        def _is_service(l: QgsRasterLayer) -> bool:
            s = (l.source() or "").lower()
            return any(k in s for k in ("wms", "wmts", "url=", "service=", "type=xyz"))

        # priorizar servicios
        raster_layers.sort(key=lambda r: (not _is_service(r),))

        visibles = []
        root = QgsProject.instance().layerTreeRoot()
        for r in raster_layers:
            n = root.findLayer(r.id())
            if n and n.isVisible():
                visibles.append(r)
        return visibles[0] if visibles else (raster_layers[0] if raster_layers else None)

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        if not self._basemap_layer:
            self._message("No hay capa base seleccionada.", level="warning")
            return

        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = self._basemap_layer.crs()
        if canvas_crs != layer_crs:
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            rect_layer_crs = xform.transform(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

    def _render_and_wrap_to_geotiff(self, layer: QgsRasterLayer, rect_layer_crs: QgsRectangle):
        from qgis.PyQt.QtGui import QImage, QColor, QPainter
        from qgis.PyQt.QtCore import QSize

    # ---------------- Render + envoltura a GeoTIFF ----------------
    def _render_and_wrap_to_geotiff(self, layer: QgsRasterLayer, rect_layer_crs: QgsRectangle):
        from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
        from qgis.PyQt.QtGui import QImage, QColor, QPainter
        from qgis.PyQt.QtCore import QSize

        w, h = 1024, 1024
        extent_rect = rect_layer_crs


        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent_rect)
        ms.setOutputSize(QSize(w, h))
        ms.setBackgroundColor(QColor(0, 0, 0, 0))

        img = None
        if _RendererJob is not None:
            try:
                job = _RendererJob(ms)
                job.start()
                job.waitForFinished()
                img = job.renderedImage()
            except Exception:
                img = None

        if img is None or img.isNull():
            try:
                img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
                img.fill(0)
                painter = QPainter(img)
                job = QgsMapRendererCustomPainterJob(ms, painter)
                job.start()
                job.waitForFinished()
                painter.end()
            except Exception:
                img = QImage(w, h, QImage.Format_ARGB32)
                img.fill(0)

        png_path = self._temp_path(".png")
        img.save(png_path)
        # Envolver PNG → GeoTIFF con la misma extensión y CRS de la capa
        self._wrap_png_to_geotiff(png_path, extent_rect, layer.crs())
        # Envolver PNG → GeoTIFF
        self._wrap_png_to_geotiff(png_path, extent_rect, layer.crs())
        # Previsualiza directamente el PNG (mejor compatibilidad que TIFF en Qt)
        self._show_image_preview(png_path)

    def _temp_path(self, suffix: str) -> str:
        return temp_file(suffix)
    
    def _ensure_png_preview(self, src_path: str) -> str:
        """
        Si src_path no es PNG (o QPixmap no lo abre), genera un PNG temporal con GDAL y devuelve su ruta.
        """
        # Si ya es PNG, pruébalo directo
        if src_path.lower().endswith(".png"):
            if not QPixmap(src_path).isNull():
                return src_path
        # Ruta PNG temporal hermana
        png_path = os.path.splitext(src_path)[0] + "_preview.png"
        try:
            ds = gdal.Open(src_path)
            if ds is None:
                return src_path  # lo intentará QPixmap
            # Convertir a PNG (GDAL hace el remapeo de bandas)
            gdal.Translate(png_path, ds, format="PNG")
            ds = None
            if os.path.exists(png_path) and not QPixmap(png_path).isNull():
                return png_path
        except Exception:
            pass
        return src_path

    def _set_preview_pixmap(self, path: str):
        """Coloca el QPixmap escalado en el label de preview."""
        pix = QPixmap(path)
        if pix.isNull():
        # Último intento: fuerza PNG y reintenta
            png = self._ensure_png_preview(path)
            pix = QPixmap(png)
            if pix.isNull():
                self.preview_label.setText("Sin preview")
                return
            path = png
        w = max(200, self._preview_container.width())
        h = max(200, self._preview_container.height())
        self.preview_label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._last_preview_path = path


    def _wrap_png_to_geotiff(self, png_path: str, extent_rect: QgsRectangle, crs: QgsCoordinateReferenceSystem):
        tif_path = os.path.splitext(png_path)[0] + ".tif"
        src = gdal.Open(png_path)
        if src is None:
            self._message("No se pudo abrir la imagen renderizada.", level="error")
            return
        w, h = src.RasterXSize, src.RasterYSize

        drv = gdal.GetDriverByName("GTiff")
        dst = drv.Create(tif_path, w, h, 4, gdal.GDT_Byte, options=["COMPRESS=LZW", "TILED=YES"])
        if dst is None:
            self._message("No se pudo crear el GeoTIFF.", level="error")
            return

        px_w = extent_rect.width() / float(w)
        px_h = extent_rect.height() / float(h)
        geotransform = (extent_rect.xMinimum(), px_w, 0.0, extent_rect.yMaximum(), 0.0, -px_h)
        dst.SetGeoTransform(geotransform)

        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())
        dst.SetProjection(srs.ExportToWkt())

        # Copiamos la imagen PNG como 4 bandas (si tu PNG tiene 3+alpha reales, adapta este bloque)
        for b in range(1, 5):
            rb = src.GetRasterBand(1)
            db = dst.GetRasterBand(b)
            data = rb.ReadRaster(0, 0, w, h)
            db.WriteRaster(0, 0, w, h, data)
            db.FlushCache()

        dst.FlushCache()
        dst = None
        src = None

        tiff_layer = QgsRasterLayer(tif_path, f"Autogeo render {os.path.basename(tif_path)}", "gdal")
        if not tiff_layer.isValid():
            self._message("No se pudo cargar el GeoTIFF generado.", level="error")
            return

        QgsProject.instance().addMapLayer(tiff_layer, True)
        self._last_preview_path = tif_path
        self._last_clip_layer_id = tiff_layer.id()
        self._show_image_preview(tif_path)

        self._message(f"Render envuelto a GeoTIFF: {tif_path}")

    # ---------------- Recorte con GDAL (archivo) ----------------
    def _clip_with_gdal(self, layer: QgsRasterLayer, rect_layer_crs: QgsRectangle):
        src_path = layer.dataProvider().dataSourceUri().split("|")[0]
        if not os.path.exists(src_path):
            self._message("No se encontró el archivo de origen para recorte.", level="warning")
            return

        out_tif = self._temp_path(".tif")

        warp_opt = gdal.WarpOptions(
            outputBounds=(rect_layer_crs.xMinimum(), rect_layer_crs.yMinimum(),
                          rect_layer_crs.xMaximum(), rect_layer_crs.yMaximum()),
            dstSRS=layer.crs().authid() or layer.crs().toWkt(),
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "TILED=YES"]
        )
        res = gdal.Warp(out_tif, src_path, options=warp_opt)
        if res is None:
            self._message("Fallo al recortar con GDAL.", level="error")
            return
        res = None

        clip_layer = QgsRasterLayer(out_tif, f"Recorte {os.path.basename(out_tif)}", "gdal")
        if not clip_layer.isValid():
            self._message("No se pudo cargar el recorte.", level="error")
            return

        QgsProject.instance().addMapLayer(clip_layer, True)
        self._last_preview_path = out_tif
        self._last_clip_layer_id = clip_layer.id()
        # Usa el convertidor a PNG para garantizar preview
        png_prev = self._ensure_png_preview(out_tif)
        self._show_image_preview(out_tif)
        self._message(f"Recorte GDAL creado: {out_tif}")

    # ---------------- Previsualización ----------------
    def _show_image_preview(self, path: str):

        pix = QPixmap(path)
        if pix.isNull():
            self.preview_label.setText("Sin preview")
            return
        w = max(200, self._get_preview_container().width())
        h = max(200, self._get_preview_container().height())
        self.preview_label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_preview_path:
            self._show_image_preview(self._last_preview_path)
