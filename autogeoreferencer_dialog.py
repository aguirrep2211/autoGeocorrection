# main.py  (o my_plugin_dialog.py si lo integras en un plugin)
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QAction
# Si necesitas iconos: from PyQt5.QtGui import QIcon
from ui_main_window import Ui_MainWindow  # generado por pyuic5
import sys

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # crea menús, toolbar, statusbar, etc.

        # Conectar acciones (deben existir en tu .ui con esos objectName)
        self.actionNuevo.triggered.connect(self.on_nuevo)
        self.actionAbrir.triggered.connect(self.on_abrir)
        self.actionGuardar.triggered.connect(self.on_guardar)
        self.actionSalir.triggered.connect(self.close)  # cierra ventana

        # Ejemplo:
        # self.actionCopiar.triggered.connect(self.on_copiar)
        # self.actionZoom_In.triggered.connect(self.on_zoom_in)
        # self.actionPreferencias.triggered.connect(self.on_preferencias)

    def on_nuevo(self):
        QMessageBox.information(self, "Nuevo", "Acción: Nuevo documento")

    def on_abrir(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir archivo", "",
            "Imágenes (*.tif *.tiff *.png *.jpg *.jpeg);;Todos (*.*)"
        )
        if path:
            self.statusBar().showMessage(f"Abrir: {path}", 3000)

    def on_guardar(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", "",
            "Proyecto (*.qgs *.qgz);;Todos (*.*)"
        )
        if path:
            self.statusBar().showMessage(f"Guardado en: {path}", 3000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    # En PyQt5 suele usarse exec_(), pero exec() funciona desde 5.15
    sys.exit(app.exec_())
