# autogeoreferencer_dialog.py — versión corregida
# Compatible con QGIS 3.22+ (probado 3.34) y PyQt5/PySide6
# - Selección de rectángulo sobre el canvas
# - Carga desde basemap (prioriza WMS/XYZ/ArcGIS; si no, cualquier raster visible)
# - Recorte con GDAL si es archivo GDAL; si es WMS/XYZ, render a PNG y envoltura a GeoTIFF
# - Conexión automática a botón/acción "cargar desde base map" si existen en la UI

from __future__ import annotations
import os
import tempfile
from uuid import uuid4
from typing import Optional

from .ui_main_window import Ui_MainWindow

from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QPushButton, QMessageBox,
    QWidget, QFrame
)
# QAction cambia de módulo entre PyQt5/PySide6: intenta Widgets y si no, Gui
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
    QgsGeometry,
    QgsWkbTypes,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsMapSettings,
    QgsMapLayer,
)
from qgis.gui import (
    QgsMapToolEmitPoint,
    QgsRubberBand,
)

# ---------------- Herramienta de rectángulo ----------------
class MapToolRectangle(QgsMapToolEmitPoint):

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.start_point = None
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 180))
        self.rubberBand.setWidth(2)

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if not self.start_point:
            return
        end_point = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end_point)
        self.rubberBand.setToGeometry(QgsGeometry.fromRect(rect), None)

    def canvasReleaseEvent(self, event):
        if not self.start_point:
            return
        end_point = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end_point)
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.callback(rect)
        self.canvas.unsetMapTool(self)

# ---------------- Ventana principal del plugin ----------------
class MainWindow(QMainWindow):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface

        # --- Cargar UI generada por pyuic5 (asegura centralwidget, menús, etc.) ---
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # --- Asegurar centralWidget si la UI no lo trae (seguridad extra) ---
        if not self.centralWidget():
            cw = QWidget(self)
            self.setCentralWidget(cw)

        # --- Widgets de previsualización ---
        self._preview_container = self._get_preview_container()
        self.preview_label = QLabel("Sin previsualización")
        self.preview_label.setAlignment(Qt.AlignCenter)

        self.preview_label.setMinimumSize(200, 200)
        lay = self._preview_container.layout()
        if lay is None:
            lay = QVBoxLayout(self._preview_container)
            self._preview_container.setLayout(lay)
        lay.addWidget(self.preview_label)

        # Estado
        self._basemap_layer: Optional[QgsRasterLayer] = None
        self._last_preview_path: Optional[str] = None
        self._last_clip_layer_id: Optional[str] = None

        # Cableado de UI (botones/acciones si existen en el .ui)
        self._wire_ui_inputs()

    # ---------------- Utilidades de UI ----------------
    def _get_preview_container(self) -> QWidget:
        """Devuelve un contenedor para la previsualización dentro del centralWidget."""
        candidate_names = [
            "frame_image", "frameImage", "framePreview", "frame_previa",
            "frame_previsualizacion", "previewFrame", "preview_container"
        ]
        for nm in candidate_names:
            w = self.findChild((QFrame, QWidget), nm)
            if w is not None:
                return w

        # Crear dentro del centralWidget (no en el QMainWindow)
        cw = self.centralWidget()
        if cw is None:
            cw = QWidget(self)
            self.setCentralWidget(cw)

        container = QFrame(cw)
        container.setObjectName("frame_image_auto")
        l = cw.layout()
        if l is None:
            l = QVBoxLayout(cw)
            cw.setLayout(l)
        l.addWidget(container)
        return container


    def _wire_ui_inputs(self):
        """Conecta botones/acciones del .ui si existen; silencioso si no."""
        def _connect_button(names, slot):
            for nm in names:
                b = self.findChild(QPushButton, nm)
                if b:
                    b.clicked.connect(slot)
                    return True
            return False

        def _connect_action(names, texts, slot):
            # 1) Buscar por objectName directamente en atributos de la ventana
            for nm in names:
                a = getattr(self, nm, None)
                if a:
                    try:
                        a.triggered.connect(slot)
                        return True
                    except Exception:
                        pass
            # 2) Barrer todas las QAction hijas y comparar el texto visible (sin & ni espacios)
            try:
                for act in self.findChildren(QAction):
                    try:
                        t = (act.text() or "").replace('&', '').strip().lower()
                        if t in texts:
                            act.triggered.connect(slot)
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        # Botón/acción de \"cargar desde base map\"
        _connect_button(
            (
                "img_from_basemap",
                "btnCargarDesdeBaseMap", "btnCargarDesdeBasemap",
                "pushButton_base_map", "pushButton_cargar_desde_basemap",
                "pushButton_cargar_referencia_desde_basemap",
            ),
            self.select_from_basemap,
        )
        _connect_action(
            (
                "actionCargarDesdeBaseMap", "actionCargarDesdeBasemap",
                "actionCargarReferenciaDesdeBaseMap", "actionAbrirDesdeBaseMap",
            ),
            {s.lower() for s in (
                "Cargar desde base map", "Cargar referencia desde base map",
                "Load from basemap", "Load reference from basemap",
            )},
            self.select_from_basemap,
        )

        # Botones genéricos de abrir imágenes (opcionales en la UI)
        _connect_button(("btnOpenTarget", "pushButton_open_target", "btn_flotante"), self.select_target_image)
        _connect_button(("btnOpenRef", "pushButton_open_ref", "btn_referencia"), self.select_reference_image)

    # ---------------- Localización de basemap ----------------
    def _pick_basemap_layer(self) -> Optional[QgsRasterLayer]:
        """Devuelve una QgsRasterLayer visible, priorizando WMS/XYZ/ArcGIS; si no, cualquier ráster visible."""
        root = QgsProject.instance().layerTreeRoot()
        lyr = self.iface.activeLayer()
        if isinstance(lyr, QgsRasterLayer):
            node = root.findLayer(lyr.id())
            if node and node.isVisible():
                return lyr
        preferred = {"wms", "xyz", "arcgismapserver", "wcs", "ows"}
        for l in root.layerOrder():
            if isinstance(l, QgsRasterLayer) and l.isValid():
                node = root.findLayer(l.id())
                if node and node.isVisible():
                    prov = (l.providerType() or "").lower()
                    if prov in preferred or prov not in {"gdal"}:
                        return l
        for l in root.layerOrder():
            if isinstance(l, QgsRasterLayer) and l.isValid():
                node = root.findLayer(l.id())
                if node and node.isVisible():
                    return l
        return None

    # ---------------- Acciones de archivo (opcionales) ----------------
    def _open_image_dialog(self, title: str) -> Optional[str]:
        filt = "Imágenes (*.tif *.tiff *.jp2 *.png *.jpg *.jpeg *.bmp);;Todos (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, title, "", filt)
        return path or None

    def select_target_image(self):
        p = self._open_image_dialog("Selecciona imagen a georreferenciar")
        if p:
            self._show_image_preview(p)

    def select_reference_image(self):
        p = self._open_image_dialog("Selecciona imagen de referencia")
        if p:
            self._show_image_preview(p)

    # ---------------- Flujo basemap ----------------
    def select_from_basemap(self):
        """Activa herramienta de selección rectangular sobre el lienzo."""
        self._basemap_layer = self._pick_basemap_layer()
        if not isinstance(self._basemap_layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning(
                "Sin basemap",
                "No se encontró una capa ráster visible (WMS/XYZ/… o archivo). Activa o añade un basemap.")
            return
        canvas = self.iface.mapCanvas()
        self.tool = MapToolRectangle(canvas, self._on_rectangle_selected)
        self.iface.messageBar().pushMessage("Selecciona un área en el mapa…", duration=5)
        canvas.setMapTool(self.tool)

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        layer = getattr(self, "_basemap_layer", None)
        if not isinstance(layer, QgsRasterLayer):
            layer = self.iface.activeLayer()
        if hasattr(self, "_basemap_layer"):
            self._basemap_layer = None
        if not isinstance(layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("Error", "No hay una capa ráster para recortar.")
            return

        # Transformar el rectángulo al CRS de la capa
        canvas = self.iface.mapCanvas()
        src_crs: QgsCoordinateReferenceSystem = canvas.mapSettings().destinationCrs()
        dst_crs: QgsCoordinateReferenceSystem = layer.crs()
        if src_crs != dst_crs:
            xform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
            rect_layer_crs = xform.transformBoundingBox(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

        provider = (layer.providerType() or "").lower()
        if provider == "gdal":
            self._clip_with_gdal(layer, rect_layer_crs)
        else:
            self._render_and_wrap_to_geotiff(layer, rect_layer_crs)

    # ---------------- Recorte con GDAL (archivo) ----------------
    def _clip_with_gdal(self, layer: QgsRasterLayer, rect_layer_crs: QgsRectangle):
        try:
            from osgeo import gdal
        except Exception:
            QMessageBox.warning(self, "GDAL no disponible", "No se pudo importar GDAL en el entorno de QGIS.")
            return

        src_uri_full = layer.dataProvider().dataSourceUri()
        src_path = src_uri_full.split("|")[0]
        ds_src = gdal.OpenEx(src_path, gdal.OF_RASTER)
        if ds_src is None:
            self.iface.messageBar().pushWarning("No se puede abrir con GDAL", "No se pudo abrir la fuente:\n" + str(src_path))
            return

        xmin, xmax = rect_layer_crs.xMinimum(), rect_layer_crs.xMaximum()
        ymin, ymax = rect_layer_crs.yMinimum(), rect_layer_crs.yMaximum()

        out_tif = self._temp_path(".tif")
        

        translate_opts = gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            projWinSRS=layer.crs().toWkt(),
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        ds_out = gdal.Translate(out_tif, ds_src, options=translate_opts)
        if ds_out is None:
            self.iface.messageBar().pushWarning("Error al recortar", "GDAL.Translate devolvió NULL.")
            return
        ds_out = None

        self._add_result_raster(out_tif, "Recorte")
        self._show_image_preview(out_tif)

    # ---------------- Render a imagen + envoltura GeoTIFF (WMS/XYZ) ----------------
    def _render_and_wrap_to_geotiff(self, layer: QgsRasterLayer, rect_layer_crs: QgsRectangle):
        from qgis.gui import QgsMapRendererParallelJob
        # Tamaño del render (puedes ajustar dinámicamente según zoom)
        w, h = 1024, 1024
        extent_rect = rect_layer_crs

        # Configuración del render independiente del canvas
        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent_rect)
        ms.setOutputSize(QSize(w, h))
        ms.setBackgroundColor(QColor(0, 0, 0, 0))

        job = QgsMapRendererParallelJob(ms)
        job.start(); job.waitForFinished()
        img = job.renderedImage()
        if img is None or img.isNull():
            # Fallback mínimo: imagen transparente
            img = QImage(w, h, QImage.Format_ARGB32)
            img.fill(0)

        png_path = self._temp_path(".png")
        img.save(png_path)

        # Envolver PNG a GeoTIFF con geotransform
        self._wrap_png_to_geotiff(png_path, extent_rect, layer.crs())

    def _wrap_png_to_geotiff(self, png_path: str, extent_rect: QgsRectangle, crs: QgsCoordinateReferenceSystem):
        try:
            from osgeo import gdal, osr
        except Exception:
            QMessageBox.warning(self, "GDAL no disponible", "No se pudo importar GDAL en el entorno de QGIS.")
            return
        tif_path = os.path.splitext(png_path)[0] + ".tif"

        src = gdal.Open(png_path)
        if src is None:
            self.iface.messageBar().pushWarning("Error", "No se pudo abrir la imagen renderizada.")
            return
        w, h = src.RasterXSize, src.RasterYSize


        drv = gdal.GetDriverByName("GTiff")
        dst = drv.Create(tif_path, w, h, 4, gdal.GDT_Byte, options=["COMPRESS=LZW", "TILED=YES"])
        if dst is None:
            self.iface.messageBar().pushWarning("Error", "No se pudo crear el GeoTIFF.")
            return

        px_w = extent_rect.width() / float(w)
        px_h = extent_rect.height() / float(h)
        geotransform = [extent_rect.xMinimum(), px_w, 0, extent_rect.yMaximum(), 0, -px_h]
        dst.SetGeoTransform(geotransform)

        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())
        dst.SetProjection(srs.ExportToWkt())

        # Copiar bandas RGBA
        for i in range(1, 5):
            rb = src.GetRasterBand(1 if i == 1 else min(i, src.RasterCount))
            data = rb.ReadRaster(0, 0, w, h)
            dst.GetRasterBand(i).WriteRaster(0, 0, w, h, data)
            if i == 4:
                dst.GetRasterBand(i).SetColorInterpretation(gdal.GCI_AlphaBand)

        dst.FlushCache(); dst = None; src = None

        self._add_result_raster(tif_path, "Recorte (render)")
        self._show_image_preview(tif_path)

    # ---------------- Utilidades comunes ----------------
    def _add_result_raster(self, path: str, name: str):
        self._remove_previous_clip_layer()
        lyr = QgsRasterLayer(path, name)
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            self._last_clip_layer_id = lyr.id()
        else:
            self.iface.messageBar().pushWarning("No válido", f"No se pudo cargar el resultado: {path}")

    def _remove_previous_clip_layer(self):
        if getattr(self, "_last_clip_layer_id", None):
            try:
                QgsProject.instance().removeMapLayer(self._last_clip_layer_id)
            except Exception:
                pass
            self._last_clip_layer_id = None

    def _temp_path(self, suffix: str) -> str:
        return os.path.join(tempfile.gettempdir(), f"autogeo_clip_{uuid4().hex}{suffix}")

    # ---------------- Previsualización ----------------
    def _show_image_preview(self, path: str):
        self._last_preview_path = path
        pix = QPixmap(path)
        if not pix or pix.isNull():
            self.preview_label.setText(os.path.basename(path))
            return
        w = max(200, self._preview_container.width())
        h = max(200, self._preview_container.height())
        self.preview_label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if self._last_preview_path:
            self._show_image_preview(self._last_preview_path)
