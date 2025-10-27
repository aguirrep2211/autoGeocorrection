from qgis.PyQt.QtWidgets import QMainWindow, QFileDialog
from qgis.PyQt.QtGui import QColor
from .ui_main_window import Ui_MainWindow
from qgis.utils import iface
from qgis.core import QgsMapSettings, QgsMapRendererParallelJob
from qgis.gui import QgsMapToolRectangleRubberBand

class DockWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        if hasattr(self, "actionCargarImagenGeorreferenciar"):
            self.actionCargarImagenGeorreferenciar.triggered.connect(self.cargar_georreferenciar)
        if hasattr(self, "actionCargarImagenReferencia"):
            self.actionCargarImagenReferencia.triggered.connect(self.cargar_referencia)

    def cargar_georreferenciar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona imagen a georreferenciar",
            "", "Ráster (*.tif *.tiff *.png *.jpg *.jpeg);;Todos (*.*)"
        )
        if path:
            self.statusBar().showMessage(f"Flotante: {path}", 4000)

    def cargar_referencia(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona imagen de referencia",
            "", "Ráster (*.tif *.tiff);;Todos (*.*)"
        )
        if path:
            self.statusBar().showMessage(f"Referencia: {path}", 4000)

    def get_from_main_screen(self):
        # Canvas de QGIS
        self._canvas = iface.mapCanvas()
        self._prev_tool = self._canvas.mapTool()

        self._rect_tool = QgsMapToolRectangleRubberBand(self._canvas, True)
        self._rect_tool.setColor(QColor(0, 170, 255, 100))
        self._rect_tool.setWidth(2)
        self._rect_tool.rectangleCreated.connect(self._on_rectangle_done)

        self._canvas.setMapTool(self._rect_tool)
        self.statusBar().showMessage("Dibuja un rectángulo en el mapa (ESC para cancelar).", 5000)

    def _on_rectangle_done(self, qrect):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar captura del mapa",
            "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tif *.tiff)"
        )
        if not path:
            self._restore_map_tool()
            return

        ms = QgsMapSettings()
        ms.setLayers(self._canvas.layers())
        ms.setDestinationCrs(self._canvas.mapSettings().destinationCrs())
        ms.setCrsTransformEnabled(True)
        ms.setExtent(qrect)
        ms.setOutputSize(self._canvas.size())

        job = QgsMapRendererParallelJob(ms)
        job.start()
        job.waitForFinished()
        img = job.renderedImage()

        ok = img.save(path)
        if ok:
            self.statusBar().showMessage(f"✅ Imagen guardada: {path}", 6000)
        else:
            self.statusBar().showMessage("❌ No se pudo guardar la imagen.", 6000)

        self._restore_map_tool()

    def _restore_map_tool(self):
        try:
            if hasattr(self, "_rect_tool") and self._rect_tool:
                self._rect_tool.rectangleCreated.disconnect(self._on_rectangle_done)
        except Exception:
            pass
        try:
            if hasattr(self, "_canvas") and hasattr(self, "_prev_tool") and self._prev_tool:
                self._canvas.setMapTool(self._prev_tool)
        except Exception:
            pass
        self._rect_tool = None
        self._prev_tool = None
