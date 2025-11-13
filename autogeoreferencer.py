# -*- coding: utf-8 -*-
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
            self.dlg = MainWindow(iface=self.iface, parent=self.iface.mainWindow())
            try:
                from qgis.core import QgsApplication
                icon_map = {
                    "actionLoadFloating": "mActionAddRasterLayer.svg",
                    "actionLoadReference": "mActionAddOgrLayer.svg",
                    "actionPickBasemap": "mActionAddWmsLayer.svg",
                    "actionDrawAOI": "mActionSelectRectangle.svg",
                    "actionRun": "mActionStart.svg",
                    "actionStop": "mActionStopEditing.svg",
                    "actionClear": "mActionTrash.svg",
                    "actionExportOrtho": "mActionSaveAs.svg",
                }
                for attr, theme_name in icon_map.items():
                    act = getattr(self.dlg, attr, None)
                    if act is not None:
                        icon = QgsApplication.getThemeIcon(theme_name)
                        if not icon.isNull():
                            act.setIcon(icon)
            except Exception as e:
                print("[Autogeoreferencer] No se pudieron aplicar iconos:", e)
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    def _run_matching_action(self):
        if self.dlg is None:
            self.dlg = MainWindow(iface=self.iface)
        self.dlg.run_matching_from_ui()