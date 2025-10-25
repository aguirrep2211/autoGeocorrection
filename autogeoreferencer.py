from qgis.PyQt.QtWidgets import QAction
from .autogeoreferencer_dialog import MainWindow

class MyPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):
        self.action = QAction("Abrir ventana de Mi Plugin", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("Mi Plugin", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("Mi Plugin", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dlg is None:
            self.dlg = MainWindow()  # tu clase del UI
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
