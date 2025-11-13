# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsProject, QgsMapLayer, QgsRasterLayer
def _is_valid_raster_layer(layer: QgsMapLayer) -> bool:
    if not isinstance(layer, QgsRasterLayer):
        return False
    crs_ok = layer.crs().isValid()
    prov = (layer.providerType() or "").lower()
    return crs_ok and prov in {"gdal", "wms", "wcs", "xyz", "arcgismapserver"}
def wire_basemap_aoi(window, iface=None):
    required = ["radioReferenceBasemap","radioReferenceRaster","editBasemapActive",
                "btnRefreshBasemap","btnAOI","comboReferenceRaster"]
    for name in required:
        if not hasattr(window, name):
            return
    window.btnAOI.setEnabled(False)
    window.editBasemapActive.setReadOnly(True)
    def _populate_reference_rasters():
        window.comboReferenceRaster.clear()
        prj = QgsProject.instance()
        valid_rasters = [lyr for lyr in prj.mapLayers().values() if isinstance(lyr, QgsRasterLayer) and lyr.crs().isValid()]
        for lyr in valid_rasters:
            window.comboReferenceRaster.addItem(lyr.name(), lyr.id())
        if not valid_rasters:
            window.comboReferenceRaster.addItem("— (no hay rasters válidos) —", "")
    def _use_active_basemap():
        layer = iface.activeLayer() if iface is not None else None
        if layer is None:
            window.editBasemapActive.setText("")
            QMessageBox.warning(window, "Autogeoreferencer",
                                "No hay capa activa en QGIS. Selecciona una capa base en el panel de capas.")
            _update_controls_state()
            return
        window.editBasemapActive.setText(layer.name())
        if not _is_valid_raster_layer(layer):
            QMessageBox.warning(window, "Autogeoreferencer",
                                "La capa activa no es raster/XYZ/WMS con CRS válido.")
        _update_controls_state()
    def _update_controls_state():
        use_basemap = window.radioReferenceBasemap.isChecked()
        window.editBasemapActive.setEnabled(use_basemap)
        window.btnRefreshBasemap.setEnabled(use_basemap)
        can_draw_aoi = False
        if use_basemap and window.editBasemapActive.text().strip():
            lyr_ok = False
            if iface is not None:
                lyr = iface.activeLayer()
                if lyr is not None and _is_valid_raster_layer(lyr):
                    lyr_ok = True
            can_draw_aoi = lyr_ok or iface is None
        window.btnAOI.setEnabled(can_draw_aoi)
        window.comboReferenceRaster.setEnabled(window.radioReferenceRaster.isChecked())
    window.btnRefreshBasemap.clicked.connect(_use_active_basemap)
    window.radioReferenceBasemap.toggled.connect(_update_controls_state)
    window.radioReferenceRaster.toggled.connect(_update_controls_state)
    _populate_reference_rasters()
    _update_controls_state()
