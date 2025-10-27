# autogeoreferencer_dialog.py

from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QPushButton, QMessageBox
)
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsGeometry,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.utils import iface

import os
import tempfile

# UI generada con pyuic5 a partir de main_window.ui
from .ui_main_window import Ui_MainWindow


class MapToolRectangle(QgsMapToolEmitPoint):
    """Herramienta para dibujar un rectángulo en el canvas y devolver su extensión (QgsRectangle) vía callback."""
    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.start_point = None
        # RubberBand de tipo polígono (API moderna)
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
        # setToGeometry espera QgsGeometry, no WKT
        self.rubberBand.setToGeometry(QgsGeometry.fromRect(rect), None)

    def canvasReleaseEvent(self, event):
        if not self.start_point:
            return
        end_point = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end_point)
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.callback(rect)
        self.canvas.unsetMapTool(self)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, iface=None):
        super().__init__()
        # iface lo pasa QGIS en classFactory; por compat dejamos fallback
        self.iface = iface or iface
        self.setupUi(self)

        # === Cableado de botones de selección de archivos ===
        self._wire_ui_buttons()

        # === Botón para seleccionar desde el lienzo (img_from_basemap) ===
        btn = self.findChild(QPushButton, "img_from_basemap")
        if btn:
            btn.clicked.connect(self.select_from_basemap)

        # === Preparar frame de previsualización ===
        self.frame_image_layout = QVBoxLayout(self.frame_image)
        self.preview_label = QLabel("Sin imagen cargada")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.frame_image_layout.addWidget(self.preview_label)

    # ---------------- Utilidades de conexión ----------------
    def _wire_ui_buttons(self):
        """Conecta botones para abrir archivos de imagen (flotante y referencia)."""
        # Intento robusto por objectName
        target_candidates = [
            "pushButton_cargar_a_georreferenciar", "pushButton_cargar_imagen",
            "btnCargarFlotante", "btnImagenAGeorreferenciar"
        ]
        ref_candidates = [
            "pushButton_cargar_referencia", "btnCargarReferencia", "pushButton_base_map"
        ]

        btn_target = None
        for n in target_candidates:
            btn_target = self.findChild(QPushButton, n)
            if btn_target: break
        if btn_target:
            btn_target.clicked.connect(self.select_target_image)

        btn_ref = None
        for n in ref_candidates:
            btn_ref = self.findChild(QPushButton, n)
            if btn_ref: break
        if btn_ref:
            btn_ref.clicked.connect(self.select_reference_image)

        # Si existen acciones de menú equivalentes, conéctalas también
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

        # Poner ruta en LineEdit si existe
        if target:
            for candidate in ("lineEdit_target_path", "lineEdit_flotante_path", "lineEdit_imagen_georreferenciar"):
                le = getattr(self, candidate, None)
                if le:
                    le.setText(path); break
            self.statusBar().showMessage(f"Imagen a georreferenciar: {path}", 4000)
        else:
            for candidate in ("lineEdit_ref_path", "lineEdit_referencia_path"):
                le = getattr(self, candidate, None)
                if le:
                    le.setText(path); break
            self.statusBar().showMessage(f"Imagen de referencia: {path}", 4000)

        # Añadir como capa (opcional, útil para revisar)
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

    def _on_rectangle_selected(self, rect: QgsRectangle):
        """Recorta la capa raster activa con la extensión seleccionada y la muestra en frame_image."""
        layer = self.iface.activeLayer()
        if not isinstance(layer, QgsRasterLayer):
            self.iface.messageBar().pushWarning("Error", "La capa activa no es un raster.")
            return

        # --- Recorte con GDAL.Translate manteniendo georreferencia ---
        try:
            from osgeo import gdal
        except Exception as e:
            QMessageBox.warning(self, "GDAL no disponible",
                                "No se pudo importar GDAL en el entorno del plugin.\n"
                                "Instala/activa GDAL en el entorno de QGIS.")
            return

        temp_dir = tempfile.gettempdir()
        out_tif = os.path.join(temp_dir, "autogeo_clip.tif")
        out_png = os.path.join(temp_dir, "autogeo_clip_preview.png")

        # projWin = [xmin, ymax, xmax, ymin] en CRS de la capa
        xmin, xmax = rect.xMinimum(), rect.xMaximum()
        ymin, ymax = rect.yMinimum(), rect.yMaximum()
        translate_opts = gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            creationOptions=["COMPRESS=LZW"]
        )
        ds = gdal.Translate(out_tif, layer.source(), options=translate_opts)
        if ds is None:
            self.iface.messageBar().pushWarning("Error", "No se pudo crear el recorte.")
            return
        ds = None  # cierra

        # Añadir el GeoTIFF recortado como capa
        clipped = QgsRasterLayer(out_tif, "Recorte")
        if clipped.isValid():
            QgsProject.instance().addMapLayer(clipped)
        else:
            self.iface.messageBar().pushWarning("Error", "El GeoTIFF recortado no es válido.")

        # --- Generar PNG para previsualización (QPixmap no abre GeoTIFF) ---
        png_opts = gdal.TranslateOptions(format="PNG")
        ds2 = gdal.Translate(out_png, out_tif, options=png_opts)
        if ds2: ds2 = None

        self._show_image_preview(out_png)

    # ---------------- Previsualización en frame_image ----------------
    def _show_image_preview(self, img_path):
        pix = QPixmap(img_path)
        if pix.isNull():
            self.preview_label.setText("No se pudo cargar la imagen de previsualización")
            return
        scaled = pix.scaled(
            self.frame_image.width(), self.frame_image.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
