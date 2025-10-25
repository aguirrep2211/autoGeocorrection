from qgis.PyQt.QtWidgets import QMainWindow, QFileDialog
#from .ui_main_window import Ui_MainWindow
from ui_main_window import Ui_MainWindow

from qgis.utils import iface
from qgis.core import QgsMapSettings, QgsMapRendererParallelJob
from qgis.gui import QgsMapToolRectangleRubberBand
from qgis.PyQt.QtGui import QColor


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.actionCargarImagenGeorreferenciar.triggered.connect(self.cargar_georreferenciar)
        self.actionCargarImagenReferencia.triggered.connect(self.cargar_referencia)

    def cargar_georreferenciar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona imagen a georreferenciar",
            "", "Ráster (*.tif *.tiff *.png *.jpg *.jpeg);;Todos (*.*)"
        )
        if path:
            # aquí puedes cargar como QgsRasterLayer (aunque no tenga CRS)
            # layer = QgsRasterLayer(path, "Flotante", "gdal")
            self.statusBar().showMessage(f"Flotante: {path}", 4000)

    def cargar_referencia(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona imagen de referencia",
            "", "Ráster (*.tif *.tiff);;Todos (*.*)"
        )
        if path:
            # layer_ref = QgsRasterLayer(path, "Referencia", "gdal")
            self.statusBar().showMessage(f"Referencia: {path}", 4000)

    def get_from_mian_screen(self):
        #Activa una herramienta de rectángulo sobre el canvas principal de QGIS.
        #Al finalizar el dibujo, renderiza ese extent a una imagen (pregunta ruta).
   
        # Canvas de QGIS
        self._canvas = iface.mapCanvas()

        # Guardamos la herramienta actual para restaurarla luego
        self._prev_tool = self._canvas.mapTool()

        # Herramienta de rectángulo con banda elástica
        self._rect_tool = QgsMapToolRectangleRubberBand(self._canvas, True)  # True = modo geométrico
        self._rect_tool.setColor(QColor(0, 170, 255, 100))  # azul semi-transparente
        self._rect_tool.setWidth(2)

        # Cuando el usuario termina de dibujar el rectángulo, disparamos el handler
        self._rect_tool.rectangleCreated.connect(self._on_rectangle_done)

        # Activamos la herramienta
        self._canvas.setMapTool(self._rect_tool)
        self.statusBar().showMessage("Dibuja un rectángulo en el mapa (ESC para cancelar).", 5000)


    def _on_rectangle_done(self, qrect):
        """
        Recibe un QgsRectangle (en coordenadas del proyecto), renderiza ese extent y guarda imagen.
        """
        # Elegir archivo de salida
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar captura del mapa",
            "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;TIFF (*.tif *.tiff)"
        )
        if not path:
            self._restore_map_tool()
            return

    # Configuramos los ajustes de render
    # Usamos la misma configuración de capas/CRS que el canvas actual
        ms = QgsMapSettings()
        ms.setLayers(self._canvas.layers())
        ms.setDestinationCrs(self._canvas.mapSettings().destinationCrs())
        ms.setCrsTransformEnabled(True)
        ms.setExtent(qrect)

    # Tamaño de salida: usamos el tamaño actual del canvas (puedes cambiarlo si quieres más resolución)
        ms.setOutputSize(self._canvas.size())

    # Render paralelo a QImage
        job = QgsMapRendererParallelJob(ms)
        job.start()
        job.waitForFinished()
        img = job.renderedImage()

    # Guardamos
    ok = img.save(path)
    if ok:
        self.statusBar().showMessage(f"✅ Imagen guardada: {path}", 6000)
    else:
        self.statusBar().showMessage("❌ No se pudo guardar la imagen.", 6000)

        self._restore_map_tool()


    def _restore_map_tool(self):
        """Restaura la herramienta previa del canvas y desconecta señales."""
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

