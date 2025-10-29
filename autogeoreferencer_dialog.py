# -*- coding: utf-8 -*-
from __future__ import annotations


import os
import shutil
import tempfile

from typing import Optional

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QImageReader, QColor
from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QMessageBox, QWidget, QFrame, QPushButton
)

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsRectangle, QgsCoordinateTransform,
    QgsCoordinateReferenceSystem, QgsWkbTypes, QgsGeometry, QgsMapSettings,
    QgsMapRendererCustomPainterJob
)
from qgis.gui import QgsMapTool, QgsMapCanvas, QgsRubberBand

# QAction cambia de módulo entre PyQt5/PySide6
try:
    from qgis.PyQt.QtWidgets import QAction  # PyQt5
except Exception:
    from qgis.PyQt.QtGui import QAction      # PySide6 fallback

# UI generada desde Qt Designer (asegúrate de compilar ui -> py)
from .ui_main_window import Ui_MainWindow

# =========================== Herramienta Rectángulo ============================
class RectangleMapTool(QgsMapTool):
    """Herramienta para dibujar un rectángulo y devolver QgsRectangle vía callback."""
    def __init__(self, canvas: QgsMapCanvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self._start_mappt = None
        self._rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self._rb.setColor(QColor(255, 0, 0, 160))
        self._rb.setWidth(2)

    def canvasPressEvent(self, e):
        self._start_mappt = self.toMapCoordinates(e.pos())
        self._rb.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, e):
        if not self._start_mappt:
            return
        p2 = self.toMapCoordinates(e.pos())
        rect = QgsRectangle(self._start_mappt, p2)
        self._rb.setToGeometry(QgsGeometry.fromRect(rect), None)

    def canvasReleaseEvent(self, e):
        if not self._start_mappt:
            return
        end = self.toMapCoordinates(e.pos())
        rect = QgsRectangle(self._start_mappt, end)
        self._rb.reset(QgsWkbTypes.PolygonGeometry)
        self.callback(rect)

    def deactivate(self):
        try:
            self._rb.reset(QgsWkbTypes.PolygonGeometry)
        finally:
            super().deactivate()

# =============================== Ventana principal ===============================
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.setWindowTitle("Autogeoreferencer")

        # Canvas y herramienta de selección
        self.canvas: Optional[QgsMapCanvas] = self.iface.mapCanvas() if self.iface else None
        self.tool_rectangle: Optional[RectangleMapTool] = RectangleMapTool(self.canvas, self._on_rectangle_selected) if self.canvas else None

        # Estado
        self._basemap_layer: Optional[QgsRasterLayer] = None
        self._current_reference_image: Optional[str] = None   # imagen temporal seleccionada por el usuario
        self._base_pixmap: Optional[QtGui.QPixmap] = None     # pixmap para la preview
        self._preview_label: Optional[QLabel] = None

        # Contenedor de previsualización (tu requerimiento)
        self._preview_frame = self._find_preview_frame()
        self._init_preview_label()

        # Enlazar señales UI
        self._wire_signals()

        # Redibujar preview al redimensionar
        self.installEventFilter(self)

    # ------------------- UI wiring -------------------
    def _wire_signals(self):
        # Fijar base -> salir de selección
        btn_fijar = getattr(self, "btnFijarBase", None)
        if isinstance(btn_fijar, QPushButton):
            btn_fijar.clicked.connect(self._on_fijar_base_clicked)

        # Cargar imagen local a georreferenciar
        btn_cargar = getattr(self, "btnCargarReferencia", None)
        if isinstance(btn_cargar, QPushButton):
            btn_cargar.clicked.connect(self._on_btn_cargar_referencia)

        connected = 0

        # 2.1) Conectar posibles QPushButton por objectName
        btn_names = (
            "btnCargarReferenciaDesdeMapa",
            "btnCargarDesdeMapa",
            "btnBaseMap",
            "btnSeleccionarBase",
            "img_from_basemap",
            "pushButton_cargar_desde_basemap",
            "pushButton_cargar_referencia_desde_basemap",
        )
        for nm in btn_names:
            w = getattr(self, nm, None)
            if isinstance(w, QPushButton):
                try:
                    # Evita conexiones duplicadas
                    try:
                        w.clicked.disconnect()  
                    except Exception:
                        pass
                    w.clicked.connect(self.select_from_basemap)
                    connected += 1
                except Exception:
                    pass

        # 2.2) Conectar QAction por objectName y por texto visible
        action_names = (
            "actionCargarDesdeBaseMap",
            "actionCargarDesdeBasemap",
            "actionCargarReferenciaDesdeBaseMap",
            "actionAbrirDesdeBaseMap",
        )
        action_texts = {
            "cargar desde base map",
            "cargar referencia desde base map",
            "load from basemap",
            "load reference from basemap",
            "desde basemap",
            "desde base map",
        }

        # a) Por objectName directo
        for nm in action_names:
            act = getattr(self, nm, None)
            if isinstance(act, QAction):
                try:
                    try:
                        act.triggered.disconnect()
                    except Exception:
                        pass
                    act.triggered.connect(self.select_from_basemap)
                    connected += 1
                except Exception:
                    pass

        # b) Barrer todas las QAction por texto visible
        try:
            for act in self.findChildren(QAction):
                t = (act.text() or "").replace("&", "").strip().lower()
                if t in action_texts:
                    try:
                        try:
                            act.triggered.disconnect()
                        except Exception:
                            pass
                        act.triggered.connect(self.select_from_basemap)
                        connected += 1
                    except Exception:
                        pass
        except Exception:
            pass

        self._message(f"‘Desde basemap’ conectado a {connected} control(es).")

    # ------------------- Preview helpers -------------------
    def _find_preview_frame(self) -> QFrame:
        candidates = (
            "frame_imagen_toortorect",  # nombre indicado por ti
            "frame_image_ortorect",
            "frame_image",
            "previewFrame",
            "frameImage",
            "framePreview",
            "preview_container",
        )

        for nm in candidates:
            fr = self.findChild(QFrame, nm)
            if fr is not None:
                return fr
        # Fallback: crea un frame si no existe
        fr = QFrame(self)
        fr.setFrameShape(QFrame.StyledPanel)
        fr.setMinimumSize(240, 240)
        self.setCentralWidget(fr)
        return fr

    def _init_preview_label(self):
        self._preview_label = QLabel("Sin imagen")
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumSize(200, 200)
        lay = self._preview_frame.layout() or QVBoxLayout(self._preview_frame)
        if self._preview_frame.layout() is None:
            self._preview_frame.setLayout(lay)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._preview_label)

    # ------------------- Acciones principales -------------------
    def _on_fijar_base_clicked(self):
        """Salir de la herramienta de selección y limpiar marcas."""
        try:
            if self.canvas and self.tool_rectangle:
                if self.canvas.mapTool() is self.tool_rectangle:
                    self.canvas.unsetMapTool(self.tool_rectangle)
            self._message("Selección cerrada.")
        except Exception as e:
            self._message("No se pudo salir de la selección: {}".format(e), level="warning")

    def _on_btn_cargar_referencia(self):
        """Abrir diálogo de imagen, copiar a temporal sin cargar como capa y previsualizar."""
        file_filter = self._build_image_filter_string()
        start_dir = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen a georreferenciar",
            start_dir,
            file_filter
        )
        if not path:
            return

        # Copiar a temporal
        try:
            tmp_path = self._copy_to_temp(path)
            self._current_reference_image = tmp_path
        except Exception as e:
            QMessageBox.critical(self, "Cargar referencia", "Error creando temporal:\n{}".format(e))
            return

        # Mostrar previsualización
        try:
            self._show_image_in_frame(tmp_path, self._preview_frame)
            self._message("Imagen cargada en temporal: {}".format(tmp_path))
        except Exception as e:
            QMessageBox.critical(self, "Previsualización", "No se pudo mostrar la imagen:\n{}".format(e))

    # ------------------- Flujo 'desde mapa' -------------------
    def select_from_basemap(self):
        if not self.canvas or not self.tool_rectangle:
            self._message("Canvas no disponible.", level="warning")
            return
        self._basemap_layer = self._pick_visible_raster_layer()
        if not isinstance(self._basemap_layer, QgsRasterLayer) or not self._basemap_layer.isValid():
            self._message("No hay ráster visible/activo válido para usar como base.", level="warning")
            return
        prov = (self._basemap_layer.providerType() or "").lower()
        self._message(f"Basemap: '{self._basemap_layer.name()}' (provider={prov}). Dibuja un rectángulo…")
        self.canvas.setMapTool(self.tool_rectangle)


    def _pick_visible_raster_layer(self) -> Optional[QgsRasterLayer]:
        root = QgsProject.instance().layerTreeRoot()
        # 1) Activa si es ráster y visible
        al = self.iface.activeLayer() if self.iface else None
        if isinstance(al, QgsRasterLayer) and al.isValid():
            node = root.findLayer(al.id())
            if node and node.isVisible():
                return al

        # 2) La primera visible según orden
        for lyr in root.layerOrder():
            if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                node = root.findLayer(lyr.id())
                if node and node.isVisible():
                    return lyr

        # 3) Cualquier ráster válido
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                return lyr

        return None

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        if not self._basemap_layer:
            self._message("No hay capa base seleccionada.", level="warning")
            self._message("Rectángulo capturado en CRS del canvas.")
            self._message(f"Basemap provider: {(self._basemap_layer.providerType() or '').lower()}")
            return

        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = self._basemap_layer.crs()
        if canvas_crs != layer_crs:
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            rect_layer_crs = xform.transformBoundingBox(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

        try:
            if self._is_gdal_backed(self._basemap_layer):
                out_tif = self._clip_with_gdal(self._basemap_layer, rect_layer_crs)
            else:
                out_tif = self._render_and_wrap_to_geotiff(self._basemap_layer, rect_layer_crs)

            if out_tif:
                name = "Recorte" if self._is_gdal_backed(self._basemap_layer) else "Recorte (render)"
                self._add_result_raster(out_tif, name)
                self._show_image_in_frame(out_tif, self._preview_frame)
        except Exception as e:
            self._message("Error procesando selección: {}".format(e), level="error")
        finally:
            if self.canvas and self.tool_rectangle and self.canvas.mapTool() is self.tool_rectangle:
                self.canvas.unsetMapTool(self.tool_rectangle)

    # ------------------- Render y envoltura a GeoTIFF -------------------
    def _render_and_wrap_to_geotiff(self, layer: QgsRasterLayer, extent_rect: QgsRectangle) -> Optional[str]:
        """Renderiza la capa (WMS/XYZ/etc.) a imagen y la envuelve a GeoTIFF con compatibilidad amplia."""
        if not layer or not layer.isValid():
            self._message("Capa base no válida.", level="warning")
            return None
        if extent_rect.isEmpty() or extent_rect.width() == 0 or extent_rect.height() == 0:
            self._message("El rectángulo seleccionado es vacío.", level="warning")
            return None

        width_map_units = extent_rect.width() or 1.0
        height_map_units = extent_rect.height() or 1.0
        target_long_side = 1536
        ratio = width_map_units / height_map_units
        if ratio >= 1:
            w = target_long_side
            h = max(1, int(target_long_side / ratio))
        else:
            h = target_long_side
            w = max(1, int(target_long_side * ratio))

        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent_rect)
        ms.setOutputSize(QtCore.QSize(w, h))
        ms.setDestinationCrs(layer.crs())
        ms.setBackgroundColor(QColor(0, 0, 0, 0))
        ms.setTransformContext(QgsProject.instance().transformContext())
        ms.setOutputDpi(96)

        img = None
        try:
            from qgis.gui import QgsMapRendererParallelJob  # type: ignore
            job = QgsMapRendererParallelJob(ms)
            job.start(); job.waitForFinished()
            img = job.renderedImage()
        except Exception:
            img = None

        if img is None or (hasattr(img, 'isNull') and img.isNull()):
            img = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            p = QtGui.QPainter(img)
            try:
                job = QgsMapRendererCustomPainterJob(ms, p)
                job.start(); job.waitForFinished()
            finally:
                p.end()

        if img is None or (hasattr(img, 'isNull') and img.isNull()):
            QMessageBox.warning(self, "Render", "No se pudo renderizar el basemap.")
            return None

        png_path = self._temp_path(".png")
        img.save(png_path)

        tif_path = self._wrap_png_to_geotiff(png_path, extent_rect, layer.crs())
        if not tif_path:
            return None
        self._message("Render envuelto a GeoTIFF: {}".format(tif_path))
        return tif_path

    def _wrap_png_to_geotiff(self, png_path: str, extent: QgsRectangle, crs: QgsCoordinateReferenceSystem) -> Optional[str]:
        try:
            from osgeo import gdal, osr
        except Exception:
            raise RuntimeError("GDAL no disponible para envolver PNG a GeoTIFF")

        ds_png = gdal.Open(png_path, gdal.GA_ReadOnly)
        if ds_png is None:
            raise RuntimeError("No se pudo abrir PNG para envolver")
        xsize, ysize = ds_png.RasterXSize, ds_png.RasterYSize

        xmin, ymin, xmax, ymax = extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()
        px_w = (xmax - xmin) / float(xsize)
        px_h = (ymax - ymin) / float(ysize)
        geotransform = (xmin, px_w, 0.0, ymax, 0.0, -px_h)

        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())

        bands = ds_png.RasterCount
        dtype = gdal.GDT_Byte
        tif_path = self._temp_path(".tif")
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(tif_path, xsize, ysize, bands, dtype, options=["COMPRESS=LZW", "TILED=YES"])
        out_ds.SetGeoTransform(geotransform)
        out_ds.SetProjection(srs.ExportToWkt())

        for b in range(1, bands + 1):
            data = ds_png.GetRasterBand(b).ReadRaster(0, 0, xsize, ysize)
            out_ds.GetRasterBand(b).WriteRaster(0, 0, xsize, ysize, data)
            if b == 4:
                out_ds.GetRasterBand(b).SetColorInterpretation(gdal.GCI_AlphaBand)
        out_ds.FlushCache()
        out_ds = None
        ds_png = None
        return tif_path

    # ------------------- Clip con GDAL (raster local) -------------------
    def _clip_with_gdal(self, layer: QgsRasterLayer, rect: QgsRectangle) -> Optional[str]:
        try:
            from osgeo import gdal
        except Exception:
            raise RuntimeError("GDAL no disponible para recorte de raster")

        src_path = layer.source()
        if (src_path.lower().startswith("/vsi") or (not os.path.exists(src_path))):
            return self._render_and_wrap_to_geotiff(layer, rect)

        xmin, ymin, xmax, ymax = rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()
        out_tif = self._temp_path(".tif")
        translate_opts = gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        ds = gdal.Translate(out_tif, src_path, options=translate_opts)
        if ds is None:
            raise RuntimeError("gdal.Translate devolvió None")
        ds.FlushCache()
        ds = None
        self._message("Recorte GDAL generado: {}".format(out_tif))
        return out_tif

    # ------------------- Utilidades varias -------------------
    def _is_gdal_backed(self, layer: QgsRasterLayer) -> bool:
        prov = layer.providerType().lower() if layer.providerType() else ""
        src = layer.source() or ""
        return (prov == "gdal") and (not src.lower().startswith("/vsi")) and os.path.exists(src)

    def _build_image_filter_string(self) -> str:
        fmts = [bytes(ext).decode("utf-8").lower() for ext in QImageReader.supportedImageFormats()]
        for extra in ("png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"):
            if extra not in fmts:
                fmts.append(extra)
        patterns = " ".join("*.{}".format(e) for e in sorted(set(fmts)))
        return "Imágenes ({})".format(patterns)

    def _copy_to_temp(self, src_path: str) -> str:
        suffix = os.path.splitext(src_path)[1] or ".png"
        tmp_dir = tempfile.mkdtemp(prefix="autogeo_ref_")
        tmp_file = os.path.join(tmp_dir, "image{}".format(suffix))
        shutil.copyfile(src_path, tmp_file)
        return tmp_file

    def _temp_path(self, suffix: str) -> str:
        d = tempfile.mkdtemp(prefix="autogeo_ref_")
        return os.path.join(d, "tmp{}".format(suffix))

    def _show_image_in_frame(self, img_path: str, frame: QFrame):
        reader = QImageReader(img_path)
        reader.setAutoTransform(True)
        qimg = reader.read()
        if qimg.isNull():
            raise RuntimeError("No se pudo leer la imagen: {}".format(reader.errorString()))
        self._base_pixmap = QtGui.QPixmap.fromImage(qimg)
        self._rescale_preview(frame)

    def _rescale_preview(self, frame: QFrame):
        if not self._base_pixmap or self._base_pixmap.isNull():
            return
        size = frame.size()
        if size.width() < 4 or size.height() < 4:
            return
        pix = self._base_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(pix)

    # ------------------- Añadir/retirar capas resultado -------------------
    def _add_result_raster(self, path: str, name: str):
        try:
            prev = getattr(self, "_last_clip_layer_id", None)
            if prev:
                QgsProject.instance().removeMapLayer(prev)
        except Exception:
            pass

        lyr = QgsRasterLayer(path, name)
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            self._last_clip_layer_id = lyr.id()
        else:
            self._message("No se pudo cargar el resultado: {}".format(path), level="warning")

    # ------------------- Mensajería y eventos -------------------
    def _message(self, text: str, level: str = "info"):
        if self.iface:
            bar = self.iface.messageBar()
            if level == "warning":
                bar.pushWarning("Autogeoreferencer", text)
            elif level == "error":
                bar.pushCritical("Autogeoreferencer", text)
            else:
                bar.pushInfo("Autogeoreferencer", text)

    def eventFilter(self, obj, ev):
        if ev.type() == QtCore.QEvent.Resize and obj is self:
            self._rescale_preview(self._preview_frame)
        return super().eventFilter(obj, ev)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._rescale_preview(self._preview_frame)


# ============================ Fin de autogeoreferencer_dialog.py ============================