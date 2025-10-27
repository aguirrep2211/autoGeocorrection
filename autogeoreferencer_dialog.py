# autogeoreferencer_dialog.py

from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QPushButton, QMessageBox,
    QSizePolicy, QAction, QWidget, QFrame
)
from qgis.PyQt.QtGui import QPixmap, QImageReader
from qgis.PyQt.QtCore import Qt, QSize

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsGeometry,
    QgsWkbTypes,
    QgsCoordinateTransform,
    QgsMapSettings,
)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

# RenderJob: usa Parallel si existe; si no, Sequential (compat)
try:
    from qgis.core import QgsMapRendererParallelJob as _RenderJobClass
except Exception:
    from qgis.core import QgsMapRendererSequentialJob as _RenderJobClass

from qgis.utils import iface as qgis_iface

import os
import tempfile
from uuid import uuid4

# UI generada con pyuic5 a partir de main_window.ui
from .ui_main_window import Ui_MainWindow


# ------------------------------ Herramienta de rectángulo ---------------------------------
class MapToolRectangle(QgsMapToolEmitPoint):
    """Herramienta para dibujar un rectángulo en el canvas y devolver su extensión vía callback."""
    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.start_point = None
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(Qt.red)
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


# ----------------------------------- Ventana principal ------------------------------------
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, iface=None):
        super().__init__()
        # Usa iface pasado por classFactory o el global de QGIS
        self.iface = iface or qgis_iface
        self.setupUi(self)

        # === Cableado de botones + menús Archivo/Abrir ===
        self._wire_ui_inputs()

        # === Botón para seleccionar desde el lienzo (img_from_basemap) ===
        btn = self.findChild(QPushButton, "img_from_basemap")
        if btn:
            btn.clicked.connect(self.select_from_basemap)

        # === Preparar contenedor de previsualización (resolver por nombre o crear fallback) ===
        self._preview_container = self._get_preview_container()
        self.frame_image_layout = QVBoxLayout()
        self._preview_container.setLayout(self.frame_image_layout)

        self.preview_label = QLabel("Sin imagen cargada")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setMinimumSize(200, 200)
        self.frame_image_layout.addWidget(self.preview_label)

        # Últimos objetos para limpieza/reescalado
        self._last_preview_path = None
        self._last_clip_layer_id = None

    # ---------------- Localiza/crea el contenedor de preview ----------------
    def _get_preview_container(self) -> QWidget:
        """
        Localiza el frame de preview por varios objectName comunes.
        Si no existe, crea un QFrame de respaldo y lo inserta en el layout del centralwidget.
        """
        candidate_names = [
            "frame_image", "frameImage", "framePreview", "frame_previa",
            "frame_previsualizacion", "previewFrame", "preview_container"
        ]
        for nm in candidate_names:
            w = self.findChild((QFrame, QWidget), nm)
            if w is not None:
                return w

        # No hay contenedor: crear uno y añadirlo al layout del centralwidget (o crear layout si no hay)
        container = QFrame(self)
        container.setObjectName("frame_image_auto")
        parent = getattr(self, "centralwidget", self)
        lay = parent.layout()
        if lay is None:
            lay = QVBoxLayout(parent)
            parent.setLayout(lay)
        lay.addWidget(container)
        return container

    # ---------------- Utilidades de conexión ----------------
    def _wire_ui_inputs(self):
        """Conecta QPushButtons y acciones de menú (Archivo → Abrir...) a los mismos slots."""
        # 1) Botones (nombres posibles)
        target_btn_names = [
            "pushButton_cargar_a_georreferenciar", "pushButton_cargar_imagen",
            "btnCargarFlotante", "btnImagenAGeorreferenciar"
        ]
        ref_btn_names = [
            "pushButton_cargar_referencia", "btnCargarReferencia", "pushButton_base_map"
        ]
        # Conectar botones a slots
        for name in target_btn_names:
            b = self.findChild(QPushButton, name)
            if b:
                b.clicked.connect(self.select_target_image)
                break
        for name in ref_btn_names:
            b = self.findChild(QPushButton, name)
            if b:
                b.clicked.connect(self.select_reference_image)
                break

        # 2) Acciones de menú (Archivo → Abrir …)
        action_names_ref = ["actionAbrirReferencia", "actionAbrirImagenReferencia", "actionAbrir_ref"]
        action_names_target = ["actionAbrirFlotante", "actionAbrirImagenAGeorreferenciar", "actionAbrir_target"]
        action_texts_ref = {"Abrir imagen de referencia", "Abrir referencia", "Open reference image"}
        action_texts_target = {"Abrir imagen a georreferenciar", "Abrir imagen flotante", "Open target image"}
        generic_texts = {"Abrir…", "Abrir", "Open…", "Open"}

        def _connect_action_by_names(names_list, slot):
            for nm in names_list:
                act = self.findChild(QAction, nm)
                if act:
                    act.triggered.connect(slot)
                    return True
            return False

        def _connect_action_by_texts(texts_set, slot):
            for act in self.findChildren(QAction):
                if act.text().strip() in texts_set:
                    act.triggered.connect(slot)
                    return True
            return False

        ok_ref = _connect_action_by_names(action_names_ref, self.select_reference_image) \
                 or _connect_action_by_texts(action_texts_ref, self.select_reference_image)
        ok_tar = _connect_action_by_names(action_names_target, self.select_target_image) \
                 or _connect_action_by_texts(action_texts_target, self.select_target_image)

        if not (ok_ref or ok_tar):
            _connect_action_by_texts(generic_texts, self.select_reference_image)  # por defecto referencia

        # 3) Compat acciones antiguas
        if hasattr(self, "actionCargarImagenGeorreferenciar"):
            self.actionCargarImagenGeorreferenciar.triggered.connect(self.select_target_image)
        if hasattr(self, "actionCargarImagenReferencia"):
            self.actionCargarImagenReferencia.triggered.connect(self.select_reference_image)

    # ---------------- Diálogos de archivo ----------------
    def _open_image_dialog(self, title: str):
        filt = "Imágenes (*.tif *.tiff *.jp2 *.png *.jpg *.jpeg *.bmp);;Todos (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, title, "", filt)
        return path

    def _post_select_common(self, path: str, target: bool):
        if not path:
            return
        if target:
            for candidate in ("lineEdit_target_path", "lineEdit_flotante_path", "lineEdit_imagen_georreferenciar"):
                le = getattr(self, candidate, None)
                if le:
                    le.setText(path); break
            if hasattr(self, "statusBar"):
                self.statusBar().showMessage(f"Imagen a georreferenciar: {path}", 4000)
        else:
            for candidate in ("lineEdit_ref_path", "lineEdit_referencia_path"):
                le = getattr(self, candidate, None)
                if le:
                    le.setText(path); break
            if hasattr(self, "statusBar"):
                self.statusBar().showMessage(f"Imagen de referencia: {path}", 4000)

        try:
            name = os.path.basename(path)
            rlayer = QgsRasterLayer(path, name)
            if rlayer.isValid() and self.iface:
                self.iface.addRasterLayer(path, name)
        except Exception:
            pass

    # ---------------- Slots públicos ----------------
    def select_target_image(self):
        path = self._open_image_dialog("Seleccionar imagen a georreferenciar")
        self._post_select_common(path, target=True)

    def select_reference_image(self):
        path = self._open_image_dialog("Seleccionar imagen de referencia")
        self._post_select_common(path, target=False)

    # ---------------- Selección rectángulo en canvas ----------------
    def select_from_basemap(self):
        """Activa herramienta de selección rectangular sobre el lienzo de QGIS."""
        canvas = self.iface.mapCanvas()
        self.tool = MapToolRectangle(canvas, self._on_rectangle_selected)
        self.iface.messageBar().pushMessage("Selecciona un área en el mapa…", duration=5)
        canvas.setMapTool(self.tool)

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        """
        Recorta la capa raster activa con la extensión seleccionada:
         - Si es GDAL → gdal.Translate(projWin+projWinSRS)
         - Si es WMS/XYZ/otro → render a PNG y envolver a GeoTIFF georreferenciado
        """
        layer = self.iface.activeLayer()
        if not isinstance(layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("Error", "La capa activa no es un ráster.")
            return

        canvas = self.iface.mapCanvas()
        canvas_crs = canvas.mapSettings().destinationCrs()
        layer_crs = layer.crs()
        if canvas_crs != layer_crs:
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            rect_layer_crs = xform.transformBoundingBox(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

        rect_layer_crs = rect_layer_crs.intersect(layer.extent())
        if rect_layer_crs.isEmpty():
            self.iface.messageBar().pushWarning("Selección fuera", "El rectángulo no intersecta la extensión de la capa.")
            return

        provider = layer.providerType().lower()
        if provider == "gdal":
            self._clip_gdal_file(layer, rect_layer_crs, layer_crs)
        else:
            self._clip_via_canvas_render(layer, rect_layer_crs, layer_crs)

    # ---------------- Recorte GDAL (archivos en disco) ----------------
    def _clip_gdal_file(self, layer, rect_layer_crs, layer_crs):
        try:
            from osgeo import gdal
        except Exception:
            QMessageBox.warning(self, "GDAL no disponible", "No se pudo importar GDAL en el entorno de QGIS.")
            return

        src_uri_full = layer.dataProvider().dataSourceUri()
        src_path = src_uri_full.split("|")[0]
        ds_src = gdal.OpenEx(src_path, gdal.OF_RASTER)
        if ds_src is None:
            self.iface.messageBar().pushWarning("No se puede abrir con GDAL", f"No se pudo abrir la fuente:\n{src_path}")
            return

        xmin, xmax = rect_layer_crs.xMinimum(), rect_layer_crs.xMaximum()
        ymin, ymax = rect_layer_crs.yMinimum(), rect_layer_crs.yMaximum()

        out_tif = self._temp_path(".tif")
        out_png = self._temp_path(".png")

        translate_opts = gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            projWinSRS=layer_crs.toWkt(),
            creationOptions=["COMPRESS=LZW"]
        )
        ds_out = gdal.Translate(out_tif, ds_src, options=translate_opts)
        if ds_out is None:
            self.iface.messageBar().pushWarning("Error al recortar", "GDAL.Translate devolvió NULL.")
            return
        ds_out = None

        self._remove_previous_clip_layer()
        clipped = QgsRasterLayer(out_tif, "Recorte")
        if clipped.isValid():
            QgsProject.instance().addMapLayer(clipped)
            self._last_clip_layer_id = clipped.id()
        else:
            self.iface.messageBar().pushWarning("Error", "El GeoTIFF recortado no es válido.")

        png_opts = gdal.TranslateOptions(format="PNG")
        ds_png = gdal.Translate(out_png, out_tif, options=png_opts)
        if ds_png:
            ds_png = None

        self._show_image_preview(out_png)

    # ---------------- Recorte por render (WMS / XYZ / otros) ----------------
    def _clip_via_canvas_render(self, layer, rect_layer_crs, layer_crs):
        try:
            from osgeo import gdal
        except Exception:
            QMessageBox.warning(self, "GDAL no disponible", "No se pudo importar GDAL en el entorno de QGIS.")
            return

        canvas = self.iface.mapCanvas()
        canvas_extent = canvas.extent()
        canvas_size = canvas.size()
        ppmu_x = canvas_size.width()  / max(canvas_extent.width(),  1e-9)
        ppmu_y = canvas_size.height() / max(canvas_extent.height(), 1e-9)
        out_w = max(1, int(rect_layer_crs.width()  * ppmu_x))
        out_h = max(1, int(rect_layer_crs.height() * ppmu_y))

        settings = QgsMapSettings()
        settings.setLayers([layer])              # ← pasar QgsMapLayer, no id
        settings.setDestinationCrs(layer_crs)
        settings.setExtent(rect_layer_crs)
        settings.setOutputSize(QSize(out_w, out_h))
        settings.setBackgroundColor(Qt.white)

        job = _RenderJobClass(settings)
        job.start()
        job.waitForFinished()
        img = job.renderedImage()

        out_png = self._temp_path(".png")
        img.save(out_png, "PNG")
        if not os.path.exists(out_png) or os.path.getsize(out_png) == 0:
            self.iface.messageBar().pushWarning("Render vacío", "No se generó la imagen de previsualización.")
            return

        out_tif = self._temp_path(".tif")
        self._png_to_geotiff(out_png, out_tif, rect_layer_crs, layer_crs)

        self._remove_previous_clip_layer()
        clipped = QgsRasterLayer(out_tif, "Recorte (render)")
        if clipped.isValid():
            QgsProject.instance().addMapLayer(clipped)
            self._last_clip_layer_id = clipped.id()
        else:
            self.iface.messageBar().pushWarning("Error", "El GeoTIFF recortado no es válido.")

        self._show_image_preview(out_png)

    # ---------------- Utilidades raster ----------------
    def _png_to_geotiff(self, png_path, tif_path, extent_rect, crs):
        from osgeo import gdal, osr
        src = gdal.Open(png_path, gdal.GA_ReadOnly)
        if src is None:
            self.iface.messageBar().pushWarning("Error", f"No se pudo abrir el PNG: {png_path}")
            return
        w, h = src.RasterXSize, src.RasterYSize
        bands = src.RasterCount

        drv = gdal.GetDriverByName("GTiff")
        dst = drv.Create(tif_path, w, h, bands, gdal.GDT_Byte,
                         options=["COMPRESS=LZW", "TILED=YES"])
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

        for i in range(1, bands + 1):
            data = src.GetRasterBand(i).ReadRaster(0, 0, w, h)
            dst.GetRasterBand(i).WriteRaster(0, 0, w, h, data)
            if i == bands:
                src_nodata = src.GetRasterBand(i).GetNoDataValue()
                if src_nodata is not None:
                    dst.GetRasterBand(i).SetNoDataValue(src_nodata)

        dst.FlushCache()
        dst = None
        src = None

    # ---------------- Previsualización ----------------
    def _show_image_preview(self, img_path):
        try:
            if not img_path or not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
                self.preview_label.setText("No hay imagen de previsualización")
                self._last_preview_path = None
                return

            reader = QImageReader(img_path)
            reader.setAutoTransform(True)
            image = reader.read()
            if image.isNull():
                self.preview_label.setText("No se pudo leer la imagen de previsualización")
                self._last_preview_path = None
                return

            target_size = self.preview_label.size()
            if target_size.width() < 2 or target_size.height() < 2:
                target_size = QSize(400, 400)

            scaled = QPixmap.fromImage(image).scaled(
                QSize(self._preview_container.width(), self._preview_container.height()),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
            self._last_preview_path = img_path
        except Exception as e:
            self.preview_label.setText(f"Error de preview: {e}")
            self._last_preview_path = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_preview_path:
            self._show_image_preview(self._last_preview_path)

    def _remove_previous_clip_layer(self):
        if getattr(self, "_last_clip_layer_id", None):
            try:
                QgsProject.instance().removeMapLayer(self._last_clip_layer_id)
            except Exception:
                pass
            self._last_clip_layer_id = None

    def _temp_path(self, suffix: str) -> str:
        return os.path.join(tempfile.gettempdir(), f"autogeo_clip_{uuid4().hex}{suffix}")
