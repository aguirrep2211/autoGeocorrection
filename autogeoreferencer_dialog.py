# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Optional, List

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QImageReader, QColor
from qgis.PyQt.QtWidgets import (
    QMainWindow, QFileDialog, QLabel, QVBoxLayout, QMessageBox, QWidget, QFrame, QPushButton
)

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsRectangle, QgsCoordinateTransform,
    QgsCoordinateReferenceSystem, QgsWkbTypes, QgsGeometry, QgsMapSettings,
    QgsMapRendererCustomPainterJob, QgsApplication
)
from qgis.gui import QgsMapTool, QgsMapCanvas, QgsRubberBand

# QAction cambia de módulo entre PyQt5/PySide6
try:
    from qgis.PyQt.QtWidgets import QAction  # PyQt5
except Exception:
    from qgis.PyQt.QtGui import QAction      # PySide6 fallback

# UI generada desde Qt Designer
from .ui_main_window import Ui_MainWindow


# =========================== Herramienta Rectángulo (AOI en canvas del QGIS) ============================
class RectangleMapTool(QgsMapTool):
    """Herramienta para dibujar un rectángulo y devolver QgsRectangle vía callback."""
    def __init__(self, canvas: QgsMapCanvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self._start_mappt = None
        self._rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self._rb.setColor(QColor(255, 0, 0, 160))
        self._rb.setWidth(2)

    def canvasPressEvent(self, e):
        self._start_mappt = self.toMapCoordinates(e.pos())
        self._rb.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, e):
        if not self._start_mappt:
            return
        p2 = self.toMapCoordinates(e.pos())
        rect = QgsRectangle(self._start_mappt, p2)
        self._rb.setToGeometry(QgsGeometry.fromRect(rect), None)

    def canvasReleaseEvent(self, e):
        if not self._start_mappt:
            return
        end = self.toMapCoordinates(e.pos())
        rect = QgsRectangle(self._start_mappt, end)
        self._rb.reset(QgsWkbTypes.PolygonGeometry)
        self.callback(rect)

    def deactivate(self):
        try:
            self._rb.reset(QgsWkbTypes.PolygonGeometry)
        finally:
            super().deactivate()


# ======================================== Ventana principal ============================================
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.setWindowTitle("Autogeoreferencer")

        # --- Canvases embebidos en la UI (placeholders del .ui) ---
        self.canvasFloat = QgsMapCanvas(self)      # muestra 'flotante'
        self.canvasRef = QgsMapCanvas(self)        # muestra 'referencia'
        self.canvasOver = QgsMapCanvas(self)       # superposición (usamos opacidad con setLayerOpacity)
        self._mount_canvas(self.canvasFloating, self.canvasFloat)
        self._mount_canvas(self.canvasReference, self.canvasRef)
        self._mount_canvas(self.canvasOverlay, self.canvasOver)

        # Herramienta rectángulo sobre el canvas principal del proyecto (no los embebidos)
        self.canvas_project: Optional[QgsMapCanvas] = self.iface.mapCanvas() if self.iface else None
        self.tool_rectangle: Optional[RectangleMapTool] = (
            RectangleMapTool(self.canvas_project, self._on_rectangle_selected) if self.canvas_project else None
        )

        # --- Estado ---
        self._basemap_layer: Optional[QgsRasterLayer] = None
        self._floating_layer: Optional[QgsRasterLayer] = None
        self._reference_layer: Optional[QgsRasterLayer] = None
        self._last_clip_layer_id: Optional[str] = None
        self._current_reference_image: Optional[str] = None

        # Conectar señales UI y acciones
        self._wire_signals()
        self._set_icons()

        # Stepper → stacked
        self.listSteps.itemSelectionChanged.connect(self._sync_step_from_list)
        # Selecciona el primer paso por defecto
        self.listSteps.setCurrentRow(0)
        self.stackSteps.setCurrentIndex(0)

        # Redibujar overlay con slider
        self.sliderOpacity.valueChanged.connect(self._on_overlay_opacity_changed)

        # Estadísticas iniciales
        self._update_quick_stats(crs="-", transform="-", gcp=0, rmse="-")

    # -------------------------------- Iconos QGIS theme --------------------------------
    def _set_icons(self):
        self.actionLoadFloating.setIcon(QgsApplication.getThemeIcon("mActionAddRasterLayer.svg"))
        self.actionLoadReference.setIcon(QgsApplication.getThemeIcon("mActionAddOgrLayer.svg"))
        self.actionPickBasemap.setIcon(QgsApplication.getThemeIcon("mActionAddWmsLayer.svg"))
        self.actionDrawAOI.setIcon(QgsApplication.getThemeIcon("mActionSelectRectangle.svg"))
        self.actionRun.setIcon(QgsApplication.getThemeIcon("mActionStart.svg"))
        self.actionStop.setIcon(QgsApplication.getThemeIcon("mActionStopEditing.svg"))
        self.actionClear.setIcon(QgsApplication.getThemeIcon("mActionTrash.svg"))
        self.actionExportOrtho.setIcon(QgsApplication.getThemeIcon("mActionFileSave.svg"))
        self.actionExportReport.setIcon(QgsApplication.getThemeIcon("mActionSaveAsPDF.svg"))

    # -------------------------------- Wiring --------------------------------
    def _wire_signals(self):
        # Toolbar / acciones
        self.actionLoadFloating.triggered.connect(self._on_load_floating)
        self.actionLoadReference.triggered.connect(self._on_load_reference)
        self.actionPickBasemap.triggered.connect(self._on_pick_basemap_preset)
        self.actionDrawAOI.toggled.connect(self._on_toggle_draw_aoi)
        self.actionRun.triggered.connect(self._on_run_clicked)
        self.actionStop.triggered.connect(lambda: self._message("Proceso detenido por el usuario.", "warning"))
        self.actionClear.triggered.connect(self._on_clear_clicked)
        self.actionExportOrtho.triggered.connect(self._on_export_ortho_clicked)
        self.actionExportReport.triggered.connect(self._on_export_report_clicked)

        # Botones de la página "Fuentes"
        self.btnBrowseFloating.clicked.connect(self._on_load_floating)
        self.btnBrowseReference.clicked.connect(self._on_load_reference)
        self.comboBasemapPresets.activated.connect(self._on_pick_basemap_from_combo)

        # Página "Parámetros y cálculo"
        self.btnRunNow.clicked.connect(self._on_run_clicked)
        self.btnLoadAOI.clicked.connect(self._on_toggle_draw_aoi_button)

        # Página "Exportar"
        self.btnBrowseOutRaster.clicked.connect(self._browse_out_raster)
        self.btnBrowseOutReportJson.clicked.connect(self._browse_out_json)
        self.btnBrowseOutReportPdf.clicked.connect(self._browse_out_pdf)
        self.btnExportAll.clicked.connect(self._on_export_all)

        # Stepper con click
        self.listSteps.itemClicked.connect(self._sync_step_from_list)

    # -------------------------------- Helpers UI --------------------------------
    def _mount_canvas(self, container_widget: QWidget, canvas: QgsMapCanvas):
        """Inserta un QgsMapCanvas en el contenedor nativo del .ui."""
        lay = container_widget.layout()
        if lay is None:
            lay = QVBoxLayout(container_widget)
            container_widget.setLayout(lay)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(canvas)
        canvas.setCanvasColor(QColor(255, 255, 255))
        canvas.enableAntiAliasing(True)

    def _sync_step_from_list(self):
        idx = max(0, self.listSteps.currentRow())
        self.stackSteps.setCurrentIndex(idx)

    # -------------------------------- Carga de datos --------------------------------
    def _on_load_floating(self):
        file_filter = self._build_image_filter_string()
        start_dir = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen a georreferenciar", start_dir, file_filter)
        if not path:
            return
        # Cargar como raster (no es obligatorio añadir al proyecto)
        lyr = QgsRasterLayer(path, "Flotante")
        if not lyr.isValid():
            QMessageBox.critical(self, "Cargar flotante", "No se pudo cargar la imagen.")
            return
        self._floating_layer = lyr
        self.editFloatingPath.setText(path)
        # Mostrar en canvas flotante
        self.canvasFloat.setLayers([lyr])
        self.canvasFloat.setExtent(lyr.extent())
        self.canvasFloat.refresh()
        self._message("Imagen flotante cargada.")

    def _on_load_reference(self):
        # Si radio de 'raster/vector georreferenciado' está activo → abrir archivo raster
        if self.radioReferenceRaster.isChecked():
            file_filter = self._build_image_filter_string()
            start_dir = os.path.expanduser("~")
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar referencia georreferenciada", start_dir, file_filter)
            if not path:
                return
            lyr = QgsRasterLayer(path, "Referencia")
            if not lyr.isValid():
                QMessageBox.critical(self, "Cargar referencia", "No se pudo cargar la capa de referencia.")
                return
            self._reference_layer = lyr
            self.editReferencePath.setText(path)
            # Mostrar en canvas referencia
            self.canvasRef.setLayers([lyr])
            self.canvasRef.setExtent(lyr.extent())
            self.canvasRef.refresh()
            self._message("Referencia cargada.")
        else:
            # Basemap (XYZ/WMS) → usa combo o activa herramienta AOI
            self._on_pick_basemap_preset()

    def _on_pick_basemap_preset(self):
        # Abre el combo si está en la página, o usa selección en combo actual
        idx = self.comboBasemapPresets.currentIndex()
        if idx <= 0:
            QMessageBox.information(self, "Basemap", "Elige un preset en la lista de 'Fuente de referencia'.")
            return
        self._on_pick_basemap_from_combo(idx)

    def _on_pick_basemap_from_combo(self, idx: int):
        label = self.comboBasemapPresets.itemText(idx).lower()
        # Presets XYZ (simples y robustos)
        presets = {
            "openstreetmap": "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "google satellite": "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "esri world imagery": "type=xyz&url=https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            # PNOA como XYZ de uso demostrativo (no oficial WMS aquí)
            "pnoa": "type=xyz&url=https://www.ign.es/wmts/pnoa-ma?service=WMTS&request=GetTile&version=1.0.0&layer=OI.OrthoimageCoverage&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}&format=image/jpeg"
        }
        key = None
        for k in presets.keys():
            if k in label:
                key = k
                break
        if not key:
            self._message("Preset no reconocido.", "warning")
            return
        uri = presets[key]
        lyr = QgsRasterLayer(uri, f"Basemap {key.title()}", "wms")  # 'wms' funciona con 'type=xyz' en QGIS
        if not lyr.isValid():
            QMessageBox.critical(self, "Basemap", "No se pudo crear la capa XYZ/WMS.")
            return
        # Añadimos al proyecto para facilitar AOI en canvas principal
        QgsProject.instance().addMapLayer(lyr)
        self._reference_layer = lyr
        self._basemap_layer = lyr
        self.editReferencePath.setText(lyr.name())
        # Mostrar en canvas referencia
        self.canvasRef.setLayers([lyr])
        self.canvasRef.setExtent(lyr.extent())
        self.canvasRef.refresh()
        self._message(f"Basemap '{lyr.name()}' añadido. Puedes dibujar AOI en el canvas del proyecto.")

    # -------------------------------- AOI y recorte --------------------------------
    def _on_toggle_draw_aoi(self, checked: bool):
        if not self.canvas_project or not self.tool_rectangle:
            self._message("Canvas del proyecto no disponible.", "warning")
            self.actionDrawAOI.setChecked(False)
            return
        if checked:
            self._basemap_layer = self._pick_visible_raster_layer()
            if not self._basemap_layer:
                self._message("Activa un ráster/XYZ visible para usar como base.", "warning")
                self.actionDrawAOI.setChecked(False)
                return
            self.canvas_project.setMapTool(self.tool_rectangle)
            self._message("Dibuja un rectángulo en el canvas del proyecto…")
        else:
            if self.canvas_project.mapTool() is self.tool_rectangle:
                self.canvas_project.unsetMapTool(self.tool_rectangle)
            self._message("Selección AOI cancelada.")

    def _on_toggle_draw_aoi_button(self):
        self.actionDrawAOI.setChecked(not self.actionDrawAOI.isChecked())
        self._on_toggle_draw_aoi(self.actionDrawAOI.isChecked())

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        if not self._basemap_layer:
            self._message("No hay capa base seleccionada.", level="warning")
            return

        canvas_crs = self.canvas_project.mapSettings().destinationCrs()
        layer_crs = self._basemap_layer.crs()
        if canvas_crs != layer_crs:
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            rect_layer_crs = xform.transformBoundingBox(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

        try:
            if self._is_gdal_backed(self._basemap_layer):
                out_tif = self._clip_with_gdal(self._basemap_layer, rect_layer_crs)
            else:
                out_tif = self._render_and_wrap_to_geotiff(self._basemap_layer, rect_layer_crs)

            if out_tif:
                name = "Recorte" if self._is_gdal_backed(self._basemap_layer) else "Recorte (render)"
                self._add_result_raster(out_tif, name)
                # Muestra recorte en canvas overlay con opacidad sobre referencia si existe
                layers: List[QgsRasterLayer] = []
                if self._reference_layer:
                    layers.append(self._reference_layer)
                if isinstance(self._basemap_layer, QgsRasterLayer):
                    layers.append(QgsRasterLayer(out_tif, "Recorte AOI"))  # temporal
                self.canvasOver.setLayers(layers)
                if layers:
                    self.canvasOver.setExtent(layers[-1].extent())
                self.canvasOver.refresh()
                self._message("AOI procesado y mostrado en la pestaña de Superposición.")
        except Exception as e:
            self._message("Error procesando selección: {}".format(e), level="error")
        finally:
            if self.canvas_project and self.tool_rectangle and self.canvas_project.mapTool() is self.tool_rectangle:
                self.canvas_project.unsetMapTool(self.tool_rectangle)
            self.actionDrawAOI.setChecked(False)

    def _on_overlay_opacity_changed(self, val: int):
        # Si hay 2 capas en overlay, aplica opacidad a la superior (recorte)
        layers = self.canvasOver.layers()
        if len(layers) >= 2:
            top = layers[-1]
            self.canvasOver.layerTreeRoot().findLayer(top.id()).setItemOpacity(val / 100.0)
            self.canvasOver.refresh()

    # -------------------------------- Cálculo (placeholder integrable con tu pipeline) --------------------------------
    def _on_run_clicked(self):
        # Aquí integrarías tu pipeline de emparejamiento, RANSAC, warp, etc.
        # Lee parámetros desde UI:
        detector = self.comboDetector.currentText()
        model = self.comboModel.currentText()
        min_inliers = self.spinMinInliers.value()
        resampling = self.comboResampling.currentText()
        clip_to_aoi = self.chkClipToAOI.isChecked()

        # TODO: llamada a tu optimizador y generación de métricas reales
        # Por ahora actualizamos métricas de ejemplo:
        self._update_quick_stats(crs=(self._reference_layer.crs().authid() if self._reference_layer else "-"),
                                 transform=model, gcp=max(12, min_inliers), rmse="1.42 px / 0.73 m")
        self._update_results_metrics(rmse_x="0.51 m", rmse_y="0.53 m", rmse_tot="0.73 m",
                                     matches=max(120, min_inliers*10), runtime="3.2 s")
        self._append_report_text({
            "detector": detector, "model": model, "min_inliers": min_inliers,
            "resampling": resampling, "clip_to_aoi": clip_to_aoi,
            "rmse_total": "0.73 m"
        })
        self._message("Cálculo completado (demostración). Integra aquí tu rutina real.")

    # -------------------------------- Exportación --------------------------------
    def _browse_out_raster(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar ortorrectificada", os.path.expanduser("~"), "GeoTIFF (*.tif *.tiff)")
        if path:
            if not path.lower().endswith((".tif", ".tiff")):
                path += ".tif"
            self.editOutRaster.setText(path)

    def _browse_out_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte JSON", os.path.expanduser("~"), "JSON (*.json)")
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self.editOutReportJson.setText(path)

    def _browse_out_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar reporte PDF", os.path.expanduser("~"), "PDF (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.editOutReportPdf.setText(path)

    def _on_export_ortho_clicked(self):
        out_path = self.editOutRaster.text().strip()
        if not out_path:
            self._browse_out_raster()
            out_path = self.editOutRaster.text().strip()
        if not out_path:
            return
        # Aquí harías gdal.Warp / gdal.Translate final según tus parámetros y AOI.
        # Demo simple: si existe último recorte temporal, lo copiamos:
        try:
            if self._last_clip_layer_id:
                lyr = QgsProject.instance().mapLayer(self._last_clip_layer_id)
                if isinstance(lyr, QgsRasterLayer) and os.path.exists(lyr.source()):
                    shutil.copyfile(lyr.source(), out_path)
                    self._message(f"Orto guardada en: {out_path}")
                    if self.chkAddToProject.isChecked():
                        QgsProject.instance().addMapLayer(QgsRasterLayer(out_path, os.path.basename(out_path)))
        except Exception as e:
            self._message(f"No se pudo exportar: {e}", "error")

    def _on_export_report_clicked(self):
        # Escribe JSON/PDF mínimos de ejemplo
        json_path = self.editOutReportJson.text().strip()
        pdf_path = self.editOutReportPdf.text().strip()
        if not json_path:
            self._browse_out_json(); json_path = self.editOutReportJson.text().strip()
        if not pdf_path:
            self._browse_out_pdf(); pdf_path = self.editOutReportPdf.text().strip()
        if not json_path or not pdf_path:
            return
        try:
            import json
            data = {
                "summary": "Reporte de georreferenciación (demo)",
                "rmse": self.label_rmse_tot.text(),
                "matches": self.label_num_matches.text(),
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # PDF “falso” como TXT con extensión .pdf para demostración (sustituye por ReportLab/WeasyPrint)
            with open(pdf_path, "w", encoding="utf-8") as f:
                f.write("Reporte de georreferenciación (demo)\n")
                f.write(f"RMSE total: {self.label_rmse_tot.text()}\n")
                f.write(f"Emparejamientos: {self.label_num_matches.text()}\n")
            self._message(f"Reportes guardados:\nJSON: {json_path}\nPDF: {pdf_path}")
        except Exception as e:
            self._message(f"No se pudo exportar reporte: {e}", "error")

    def _on_export_all(self):
        self._on_export_ortho_clicked()
        self._on_export_report_clicked()

    def _on_clear_clicked(self):
        try:
            if self._last_clip_layer_id:
                QgsProject.instance().removeMapLayer(self._last_clip_layer_id)
                self._last_clip_layer_id = None
            self.plainReport.clear()
            self._update_results_metrics("-", "-", "-", 0, "-")
            self._message("Limpieza realizada.")
        except Exception as e:
            self._message(f"No se pudo limpiar: {e}", "warning")

    # -------------------------------- Lógica de recorte/render (tuya, adaptada) --------------------------------
    def _pick_visible_raster_layer(self) -> Optional[QgsRasterLayer]:
        root = QgsProject.instance().layerTreeRoot()
        al = self.iface.activeLayer() if self.iface else None
        if isinstance(al, QgsRasterLayer) and al.isValid():
            node = root.findLayer(al.id())
            if node and node.isVisible():
                return al
        for lyr in root.layerOrder():
            if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                node = root.findLayer(lyr.id())
                if node and node.isVisible():
                    return lyr
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                return lyr
        return None

    def _on_rectangle_selected(self, rect_canvas_crs: QgsRectangle):
        if not self._basemap_layer:
            self._message("No hay capa base seleccionada.", level="warning")
            return

        canvas_crs = self.canvas_project.mapSettings().destinationCrs()
        layer_crs = self._basemap_layer.crs()
        if canvas_crs != layer_crs:
            xform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            rect_layer_crs = xform.transformBoundingBox(rect_canvas_crs)
        else:
            rect_layer_crs = rect_canvas_crs

        try:
            if self._is_gdal_backed(self._basemap_layer):
                out_tif = self._clip_with_gdal(self._basemap_layer, rect_layer_crs)
            else:
                out_tif = self._render_and_wrap_to_geotiff(self._basemap_layer, rect_layer_crs)

            if out_tif:
                name = "Recorte" if self._is_gdal_backed(self._basemap_layer) else "Recorte (render)"
                self._add_result_raster(out_tif, name)
                self._message("AOI procesado. Revisa la pestaña 'Superposición'.")
        except Exception as e:
            self._message("Error procesando selección: {}".format(e), level="error")
        finally:
            if self.canvas_project and self.tool_rectangle and self.canvas_project.mapTool() is self.tool_rectangle:
                self.canvas_project.unsetMapTool(self.tool_rectangle)
            self.actionDrawAOI.setChecked(False)

    def _render_and_wrap_to_geotiff(self, layer: QgsRasterLayer, extent_rect: QgsRectangle) -> Optional[str]:
        if not layer or not layer.isValid():
            self._message("Capa base no válida.", level="warning")
            return None
        if extent_rect.isEmpty() or extent_rect.width() == 0 or extent_rect.height() == 0:
            self._message("El rectángulo seleccionado es vacío.", level="warning")
            return None

        width_map_units = extent_rect.width() or 1.0
        height_map_units = extent_rect.height() or 1.0
        target_long_side = 1536
        ratio = width_map_units / height_map_units
        if ratio >= 1:
            w = target_long_side
            h = max(1, int(target_long_side / ratio))
        else:
            h = target_long_side
            w = max(1, int(target_long_side * ratio))

        ms = QgsMapSettings()
        ms.setLayers([layer])
        ms.setExtent(extent_rect)
        ms.setOutputSize(QtCore.QSize(w, h))
        ms.setDestinationCrs(layer.crs())
        ms.setBackgroundColor(QColor(0, 0, 0, 0))
        ms.setTransformContext(QgsProject.instance().transformContext())
        ms.setOutputDpi(96)

        img = None
        try:
            from qgis.gui import QgsMapRendererParallelJob  # type: ignore
            job = QgsMapRendererParallelJob(ms)
            job.start(); job.waitForFinished()
            img = job.renderedImage()
        except Exception:
            img = None

        if img is None or (hasattr(img, 'isNull') and img.isNull()):
            img = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            p = QtGui.QPainter(img)
            try:
                job = QgsMapRendererCustomPainterJob(ms, p)
                job.start(); job.waitForFinished()
            finally:
                p.end()

        if img is None or (hasattr(img, 'isNull') and img.isNull()):
            QMessageBox.warning(self, "Render", "No se pudo renderizar el basemap.")
            return None

        png_path = self._temp_path(".png")
        img.save(png_path)
        tif_path = self._wrap_png_to_geotiff(png_path, extent_rect, layer.crs())
        if not tif_path:
            return None
        self._message("Render envuelto a GeoTIFF: {}".format(tif_path))
        return tif_path

    def _wrap_png_to_geotiff(self, png_path: str, extent: QgsRectangle, crs: QgsCoordinateReferenceSystem) -> Optional[str]:
        try:
            from osgeo import gdal, osr
        except Exception:
            raise RuntimeError("GDAL no disponible para envolver PNG a GeoTIFF")

        ds_png = gdal.Open(png_path, gdal.GA_ReadOnly)
        if ds_png is None:
            raise RuntimeError("No se pudo abrir PNG para envolver")
        xsize, ysize = ds_png.RasterXSize, ds_png.RasterYSize

        xmin, ymin, xmax, ymax = extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()
        px_w = (xmax - xmin) / float(xsize)
        px_h = (ymax - ymin) / float(ysize)
        geotransform = (xmin, px_w, 0.0, ymax, 0.0, -px_h)

        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())

        bands = ds_png.RasterCount
        dtype = gdal.GDT_Byte
        tif_path = self._temp_path(".tif")
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(tif_path, xsize, ysize, bands, dtype, options=["COMPRESS=LZW", "TILED=YES"])
        out_ds.SetGeoTransform(geotransform)
        out_ds.SetProjection(srs.ExportToWkt())

        for b in range(1, bands + 1):
            data = ds_png.GetRasterBand(b).ReadRaster(0, 0, xsize, ysize)
            out_ds.GetRasterBand(b).WriteRaster(0, 0, xsize, ysize, data)
            if b == 4:
                out_ds.GetRasterBand(b).SetColorInterpretation(gdal.GCI_AlphaBand)
        out_ds.FlushCache()
        out_ds = None
        ds_png = None
        return tif_path

    def _clip_with_gdal(self, layer: QgsRasterLayer, rect: QgsRectangle) -> Optional[str]:
        try:
            from osgeo import gdal
        except Exception:
            raise RuntimeError("GDAL no disponible para recorte de raster")

        src_path = layer.source()
        if (src_path.lower().startswith("/vsi") or (not os.path.exists(src_path))):
            return self._render_and_wrap_to_geotiff(layer, rect)

        xmin, ymin, xmax, ymax = rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()
        out_tif = self._temp_path(".tif")
        translate_opts = gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        ds = gdal.Translate(out_tif, src_path, options=translate_opts)
        if ds is None:
            raise RuntimeError("gdal.Translate devolvió None")
        ds.FlushCache()
        ds = None
        self._message("Recorte GDAL generado: {}".format(out_tif))
        return out_tif

    # -------------------------------- Utilidades --------------------------------
    def _is_gdal_backed(self, layer: QgsRasterLayer) -> bool:
        prov = layer.providerType().lower() if layer.providerType() else ""
        src = layer.source() or ""
        return (prov == "gdal") and (not src.lower().startswith("/vsi")) and os.path.exists(src)

    def _build_image_filter_string(self) -> str:
        fmts = [bytes(ext).decode("utf-8").lower() for ext in QImageReader.supportedImageFormats()]
        for extra in ("png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"):
            if extra not in fmts:
                fmts.append(extra)
        patterns = " ".join("*.{}".format(e) for e in sorted(set(fmts)))
        return "Imágenes ({})".format(patterns)

    def _copy_to_temp(self, src_path: str) -> str:
        suffix = os.path.splitext(src_path)[1] or ".png"
        tmp_dir = tempfile.mkdtemp(prefix="autogeo_ref_")
        tmp_file = os.path.join(tmp_dir, "image{}".format(suffix))
        shutil.copyfile(src_path, tmp_file)
        return tmp_file

    def _temp_path(self, suffix: str) -> str:
        d = tempfile.mkdtemp(prefix="autogeo_ref_")
        return os.path.join(d, "tmp{}".format(suffix))

    def _add_result_raster(self, path: str, name: str):
        try:
            prev = getattr(self, "_last_clip_layer_id", None)
            if prev:
                QgsProject.instance().removeMapLayer(prev)
        except Exception:
            pass

        lyr = QgsRasterLayer(path, name)
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr)
            self._last_clip_layer_id = lyr.id()
        else:
            self._message("No se pudo cargar el resultado: {}".format(path), level="warning")

    # ---- UI: quick stats y métricas ----
    def _update_quick_stats(self, crs: str, transform: str, gcp: int, rmse: str):
        self.label_crs_value.setText(str(crs))
        self.label_transform_value.setText(str(transform))
        self.label_gcp_value.setText(str(gcp))
        self.label_rmse_value.setText(str(rmse))

    def _update_results_metrics(self, rmse_x: str, rmse_y: str, rmse_tot: str, matches: int, runtime: str):
        self.label_rmse_x.setText(rmse_x)
        self.label_rmse_y.setText(rmse_y)
        self.label_rmse_tot.setText(rmse_tot)
        self.label_num_matches.setText(str(matches))
        self.label_runtime.setText(runtime)

    def _append_report_text(self, data: dict):
        import json
        txt = json.dumps(data, ensure_ascii=False, indent=2)
        self.plainReport.appendPlainText(txt)

    # ---- Mensajería y eventos ----
    def _message(self, text: str, level: str = "info"):
        if self.iface:
            bar = self.iface.messageBar()
            if level == "warning":
                bar.pushWarning("Autogeoreferencer", text)
            elif level == "error":
                bar.pushCritical("Autogeoreferencer", text)
            else:
                bar.pushInfo("Autogeoreferencer", text)

    def eventFilter(self, obj, ev):
        return super().eventFilter(obj, ev)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)

# ============================ Fin de autogeoreferencer_dialog.py ============================