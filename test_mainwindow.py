from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QObject
from .autogeoreferencer_dialog import MainWindow


class AutogeoreferencerPlugin(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):
        self.action = QAction(QIcon(), "Autogeoreferencer", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("Autogeoreferencer", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("Autogeoreferencer", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dlg is None:
            # Pasamos iface por si quieres interactuar con el canvas
            self.dlg = MainWindow(iface=self.iface)
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()


# 🚀 Esta función es obligatoria en todo plugin QGIS
def classFactory(iface):
    return AutogeoreferencerPlugin(iface)

if __name__ == "__main__":
    from qgis.PyQt.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
