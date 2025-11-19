# -*- coding: utf-8 -*-
"""
Diálogo principal del plugin Autogeoreferencer.

Carga la interfaz desde main_window.ui usando qgis.PyQt.uic
y conecta los botones a la lógica del plugin.
"""

import os
import csv

from qgis.PyQt import QtWidgets, QtGui, QtCore, uic
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsApplication,
    QgsMapRendererCustomPainterJob,
    QgsRectangle,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand

from .calculus import feature_matcher_cv


# ----------------------------------------------------------
# Herramienta de rectángulo sobre el canvas de QGIS
# ----------------------------------------------------------
class RectangleMapTool(QgsMapTool):
    """
    Herramienta para dibujar un rectángulo en el canvas de QGIS y devolver
    un QgsRectangle vía un callback.
    """

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback

        self.rubberBand = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setStrokeColor(QtGui.QColor(255, 0, 0))
        self.rubberBand.setFillColor(QtGui.QColor(255, 0, 0, 40))
        self.rubberBand.setWidth(1)

        self.start_point = None
        self.isEmitting = False

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.isEmitting = True
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if not self.isEmitting or self.start_point is None:
            return

        end_point = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end_point)

        points = [
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
            QgsPointXY(rect.xMinimum(), rect.yMaximum()),
            QgsPointXY(rect.xMaximum(), rect.yMaximum()),
            QgsPointXY(rect.xMaximum(), rect.yMinimum()),
        ]
        geom = QgsGeometry.fromPolygonXY([points])
        self.rubberBand.setToGeometry(geom, None)

    def canvasReleaseEvent(self, event):
        if not self.isEmitting or self.start_point is None:
            return

        end_point = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end_point)

        self.isEmitting = False
        self.rubberBand.hide()

        if self.callback is not None:
            self.callback(rect)

    def deactivate(self):
        super().deactivate()
        self.rubberBand.hide()


# ----------------------------------------------------------
# Diálogo para elegir capa raster de referencia
# ----------------------------------------------------------
class RasterReferenceDialog(QtWidgets.QDialog):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Seleccionar capa raster de referencia")

        self.resize(450, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # Lista de capas
        self.listLayers = QtWidgets.QListWidget(self)
        layout.addWidget(self.listLayers)

        # Fila inferior: botón administrador + botones OK/Cancel
        bottom_layout = QtWidgets.QHBoxLayout()

        self.btnOpenRasterMgr = QtWidgets.QPushButton("Administrador raster...", self)
        try:
            icon = QgsApplication.getThemeIcon("mIconDataSourceManager.svg")
            if not icon.isNull():
                self.btnOpenRasterMgr.setIcon(icon)
        except Exception:
            pass

        bottom_layout.addWidget(self.btnOpenRasterMgr)

        bottom_layout.addStretch(1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        bottom_layout.addWidget(buttons)

        layout.addLayout(bottom_layout)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.btnOpenRasterMgr.clicked.connect(self._on_open_raster_manager)

        self._populate_layers()

    def _populate_layers(self):
        """Rellena la lista con las capas raster del proyecto que tengan CRS válido."""
        self.listLayers.clear()

        project = QgsProject.instance()
        for layer in project.mapLayers().values():
            if not isinstance(layer, QgsRasterLayer):
                continue
            if not layer.isValid():
                continue
            crs = layer.crs()
            if not crs.isValid():
                continue

            authid = crs.authid() or "CRS desconocido"
            item_text = f"{layer.name()} [{authid}]"
            item = QtWidgets.QListWidgetItem(item_text, self.listLayers)
            item.setData(QtCore.Qt.UserRole, layer.id())

        if self.listLayers.count() > 0:
            self.listLayers.setCurrentRow(0)

    def _on_open_raster_manager(self):
        """Abre el Administrador de fuentes de datos en la pestaña Raster."""
        if self.iface is None:
            QtWidgets.QMessageBox.warning(
                self,
                "QGIS no disponible",
                "No se puede abrir el Administrador de fuentes de datos porque "
                "no se ha pasado la interfaz de QGIS (iface).",
            )
            return

        try:
            self.iface.openDataSourceManagerPage("raster")
        except AttributeError:
            try:
                self.iface.showDataSourceManager()
            except AttributeError:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Función no disponible",
                    "La interfaz de QGIS no ofrece acceso al Administrador de "
                    "fuentes de datos desde este plugin.",
                )

        # refrescar por si hay capas nuevas
        self._populate_layers()

    def get_selected_layer(self):
        """Devuelve la QgsRasterLayer seleccionada o None."""
        item = self.listLayers.currentItem()
        if item is None:
            return None
        layer_id = item.data(QtCore.Qt.UserRole)
        if not layer_id:
            return None
        layer = QgsProject.instance().mapLayer(layer_id)
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            return layer
        return None


# ----------------------------------------------------------
# Ventana principal del plugin
# ----------------------------------------------------------
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "main_window.ui")
)


class MainWindow(QtWidgets.QMainWindow, FORM_CLASS):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface

        # Construir la UI definida en main_window.ui
        self.setupUi(self)

        # Para guardar los pixmaps originales
        self._float_pixmap = None
        self._ref_pixmap = None
        self._ref_layer = None

        # Para el motor CV
        self._ref_img_path = None      # ruta de la imagen usada como referencia
        self._ref_crs = None           # CRS de referencia

        # Para herramienta de rectángulo en el canvas
        self._rect_tool = None
        self._prev_map_tool = None

        # Para resultados del matching
        self.current_homography = None   # matriz de transformación (3x3)
        self.current_gcps = []           # lista de puntos de control / matches

        # Ajustar proporciones del splitter si existe
        try:
            self.splitterMain.setSizes([300, 700])
        except AttributeError:
            pass

        # =========================
        # CONEXIÓN DE SEÑALES
        # =========================

        # Botón "Examinar..." de la imagen flotante
        try:
            self.btnBrowseFloating.clicked.connect(self._on_browse_floating_clicked)
        except AttributeError:
            pass

        # Botón "Examinar..." de la capa de referencia (selector de ráster)
        try:
            self.btnBrowseReference.clicked.connect(self._on_browse_reference_clicked)
        except AttributeError:
            pass

        # Botón "Cargar referencia desde el mapa de QGIS"
        try:
            self.btnLoadReferenceFromCanvas.clicked.connect(
                self._on_load_reference_from_canvas_clicked
            )
        except AttributeError:
            pass

        # Botón GET MATCHES >
        try:
            self.btnNextStep.clicked.connect(self.run_matching_from_ui)
        except AttributeError:
            pass

        # Botones de exportación (matriz y GCPs)
        try:
            self.btnExportTransform.clicked.connect(self._export_transform_matrix)
        except AttributeError:
            pass

        try:
            self.btnExportGCPs.clicked.connect(self._export_gcps)
        except AttributeError:
            pass

    # ------------------------------------------------------------------
    # LÓGICA DE LOS BOTONES - IMAGEN FLOTANTE
    # ------------------------------------------------------------------
    def _on_browse_floating_clicked(self):
        """
        Se ejecuta al pulsar el botón "Examinar..." de la imagen flotante.
        """

        filtros = (
            "Imágenes (*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.gif);;"
            "Todos los archivos (*)"
        )

        start_dir = ""
        try:
            if self.editFloatingPath.text():
                existing = self.editFloatingPath.text()
                if os.path.isdir(existing):
                    start_dir = existing
                else:
                    start_dir = os.path.dirname(existing)
        except AttributeError:
            pass

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen flotante",
            start_dir,
            filtros,
        )

        if not file_path:
            return

        try:
            self.editFloatingPath.setText(file_path)
            self.labelFloatingInfo.setText(os.path.basename(file_path))
        except AttributeError:
            pass

        pixmap = QtGui.QPixmap(file_path)
        if pixmap.isNull():
            QtWidgets.QMessageBox.warning(
                self,
                "Error al cargar imagen",
                "No se ha podido cargar la imagen seleccionada:\n{}".format(
                    file_path
                ),
            )
            return

        self._float_pixmap = pixmap
        self._update_float_preview()

    # ------------------------------------------------------------------
    # LÓGICA DE LOS BOTONES - CAPA DE REFERENCIA
    # ------------------------------------------------------------------
    def _on_browse_reference_clicked(self):
        """
        Permite seleccionar una capa raster de referencia del proyecto QGIS.
        """
        dlg = RasterReferenceDialog(self.iface, self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        layer = dlg.get_selected_layer()
        if layer is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Sin capa seleccionada",
                "No se ha seleccionado ninguna capa raster de referencia.",
            )
            return

        self._ref_layer = layer
        self._ref_crs = layer.crs()  # CRS de referencia

        crs_text = layer.crs().authid() if layer.crs().isValid() else "CRS desconocido"
        desc = f"{layer.name()} [{crs_text}]"

        try:
            self.editReferencePath.setText(desc)
        except AttributeError:
            pass

        try:
            self.labelReferenceInfo.setText(f"Capa: {desc}")
        except AttributeError:
            pass

        # Guardar ruta de imagen y pixmap
        self._load_reference_pixmap_from_layer(layer)
        self._update_reference_preview()

    def _load_reference_pixmap_from_layer(self, layer: QgsRasterLayer):
        """
        Intenta cargar un QPixmap a partir de la fuente de la capa raster
        y guarda la ruta en _ref_img_path para el motor de matching.
        """
        self._ref_pixmap = None
        self._ref_img_path = None

        if not isinstance(layer, QgsRasterLayer) or not layer.isValid():
            return

        source = layer.source()
        if not source:
            return

        if "|" in source:
            source_path = source.split("|", 1)[0]
        else:
            source_path = source

        source_path = source_path.strip('"')

        pixmap = QtGui.QPixmap(source_path)
        if pixmap.isNull():
            try:
                self.labelRefPreview.setText(
                    "(Sin previsualización: formato no soportado como imagen)"
                )
            except AttributeError:
                pass
            return

        self._ref_pixmap = pixmap
        self._ref_img_path = source_path

    # ------------------------------------------------------------------
    # LÓGICA DE LOS BOTONES - CARGAR REFERENCIA DESDE MAPA QGIS
    # ------------------------------------------------------------------
    def _on_load_reference_from_canvas_clicked(self):
        """
        Activa herramienta de rectángulo sobre el canvas de QGIS.
        """
        if self.iface is None:
            QtWidgets.QMessageBox.warning(
                self,
                "QGIS no disponible",
                "No se puede acceder al mapa de QGIS porque no se ha pasado "
                "la interfaz (iface) al plugin.",
            )
            return

        canvas = self.iface.mapCanvas()
        if canvas is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Canvas no disponible",
                "No se ha podido obtener el canvas de QGIS.",
            )
            return

        self._prev_map_tool = canvas.mapTool()
        self._rect_tool = RectangleMapTool(canvas, self._on_canvas_rectangle_selected)
        canvas.setMapTool(self._rect_tool)

        try:
            self.labelAOIStatus.setText(
                "Dibuja un rectángulo en el mapa de QGIS para definir la referencia."
            )
        except AttributeError:
            pass

    def _on_canvas_rectangle_selected(self, rect: QgsRectangle):
        """
        Callback cuando el usuario termina de dibujar el rectángulo.
        Renderiza el mapa en esa extensión y actualiza la previsualización.
        """
        if self.iface is None:
            return

        canvas = self.iface.mapCanvas()
        if canvas is None:
            return

        # Restaurar herramienta anterior
        try:
            if self._prev_map_tool is not None:
                canvas.setMapTool(self._prev_map_tool)
        except Exception:
            pass
        self._prev_map_tool = None
        self._rect_tool = None

        # Renderizar la región seleccionada
        self._render_reference_from_canvas(rect)

        try:
            self.labelAOIStatus.setText("AOI definida desde el mapa de QGIS.")
        except AttributeError:
            pass

        try:
            self.editReferencePath.setText("Referencia desde mapa QGIS (AOI)")
        except AttributeError:
            pass

        try:
            self.labelReferenceInfo.setText("Referencia: mapa QGIS recortado (AOI)")
        except AttributeError:
            pass

    def _render_reference_from_canvas(self, rect: QgsRectangle):
        """
        Renderiza el mapa de QGIS en la extensión del rectángulo dado y
        guarda el resultado como pixmap de referencia y PNG temporal.
        """
        if self.iface is None:
            return

        canvas = self.iface.mapCanvas()
        if canvas is None:
            return

        ms = canvas.mapSettings()
        ms.setExtent(rect)

        size = QtCore.QSize(512, 512)
        ms.setOutputSize(size)

        img = QtGui.QImage(size, QtGui.QImage.Format_ARGB32_Premultiplied)
        img.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(img)
        job = QgsMapRendererCustomPainterJob(ms, painter)
        job.start()
        job.waitForFinished()
        painter.end()

        pixmap = QtGui.QPixmap.fromImage(img)
        if pixmap.isNull():
            QtWidgets.QMessageBox.warning(
                self,
                "Error al renderizar mapa",
                "No se ha podido renderizar la zona seleccionada del mapa.",
            )
            return

        self._ref_pixmap = pixmap
        self._update_reference_preview()

        # Guardar en fichero temporal para el motor de matching
        tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, "ref_from_canvas_aoi.png")
        pixmap.save(tmp_path, "PNG")
        self._ref_img_path = tmp_path

        # CRS del canvas como referencia
        try:
            self._ref_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ACTUALIZACIÓN DE PREVISUALIZACIONES
    # ------------------------------------------------------------------
    def _update_float_preview(self):
        """
        Escala la imagen flotante al tamaño del QLabel labelFloatPreview.
        """
        if self._float_pixmap is None or self._float_pixmap.isNull():
            return

        try:
            label = self.labelFloatPreview
        except AttributeError:
            return

        if label.width() <= 0 or label.height() <= 0:
            return

        scaled = self._float_pixmap.scaled(
            label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setText("")

    def _update_reference_preview(self):
        """
        Escala la imagen de referencia al tamaño del QLabel labelRefPreview.
        """
        if self._ref_pixmap is None or self._ref_pixmap.isNull():
            return

        try:
            label = self.labelRefPreview
        except AttributeError:
            return

        if label.width() <= 0 or label.height() <= 0:
            return

        scaled = self._ref_pixmap.scaled(
            label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setText("")

    # ------------------------------------------------------------------
    # EVENTOS
    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        """
        Reescala las previsualizaciones al cambiar el tamaño de la ventana.
        """
        super().resizeEvent(event)
        self._update_float_preview()
        self._update_reference_preview()

    # ------------------------------------------------------------------
    # MATCHING: MOTOR CV + ACTUALIZACIÓN UI
    # ------------------------------------------------------------------
    def run_matching_from_ui(self):
        """
        Ejecuta el motor de matching (feature_matcher_cv) usando:
          - Imagen flotante: editFloatingPath
          - Referencia: self._ref_img_path (capa o AOI desde mapa)
        Muestra:
          - Imagen de matches en tab 'Matches'
          - RMSE en label_rmse_value
          - Matriz de transformación en label_status_value
        """
        # Comprobar imagen flotante
        float_path = ""
        try:
            float_path = self.editFloatingPath.text().strip()
        except AttributeError:
            pass

        if not float_path or not os.path.exists(float_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Imagen flotante no disponible",
                "Debes seleccionar una imagen a georreferenciar (flotante) primero.",
            )
            return

        # Comprobar referencia
        if not self._ref_img_path or not os.path.exists(self._ref_img_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Referencia no disponible",
                "Debes seleccionar una capa de referencia o definir una AOI desde el mapa de QGIS.",
            )
            return

        # Parámetros desde la UI
        try:
            detector = self.comboDetector.currentText().strip()
        except AttributeError:
            detector = "ORB"

        try:
            matcher_ui = self.comboMatcher.currentText().strip().lower()
        except AttributeError:
            matcher_ui = "auto"

        if "flann" in matcher_ui:
            matcher_type = "flann"
        elif "bf" in matcher_ui or "brute" in matcher_ui:
            matcher_type = "bf"
        else:
            matcher_type = "auto"

        # Corregido: spinRatioTest (como en el .ui)
        try:
            ratio_thresh = float(self.spinRatioTest.value())
        except AttributeError:
            ratio_thresh = 0.75

        ransac_thresh = 3.0
        alpha_rmse = 0.15

        # Barra de progreso y estado
        try:
            self.progressBar.setValue(5)
            self.label_status_value.setText("Calculando matches...")
        except Exception:
            pass

        # Llamar al motor para obtener detalles (incluye RMSE y, si está implementado, homografía y GCPs)
        try:
            details = feature_matcher_cv.match_details(
                float_path,
                self._ref_img_path,
                detector=detector,
                matcher_type=matcher_type,
                ratio_thresh=ratio_thresh,
                ransac_thresh=ransac_thresh,
                alpha_rmse=alpha_rmse,
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error en matching",
                f"Ocurrió un error al ejecutar el motor de matching:\n{e}",
            )
            try:
                self.label_status_value.setText("Error en matching")
                self.progressBar.setValue(0)
            except Exception:
                pass
            return

        # Extraer RMSE
        rmse = details.get("rmse", None)

        # Extraer matriz de transformación si el motor la devuelve
        H = (
            details.get("homography")
            or details.get("H")
            or details.get("transform")
            or details.get("transform_matrix")
        )

        # Extraer puntos de control / GCPs si existen en el dict
        gcps = (
            details.get("gcps")
            or details.get("control_points")
            or details.get("points")
            or []
        )

        # Guardar en atributos
        self.current_homography = H
        # Forzamos lista para evitar problemas si viene como None
        self.current_gcps = list(gcps) if gcps else []

        # Actualizar matriz + RMSE en la UI
        try:
            self.update_transform_matrix(H, rmse)
        except Exception:
            # Fallback mínimo si algo falla en el formateo
            try:
                if rmse is None:
                    self.label_rmse_value.setText("-")
                    self.label_status_value.setText("Matching completado (sin RMSE / sin matriz)")
                else:
                    self.label_rmse_value.setText(f"{rmse:.3f}")
                    self.label_status_value.setText(f"Matching completado (RMSE={rmse:.3f})")
            except Exception:
                pass

        # Dibujar imagen de matches con el motor
        params_for_draw = {
            "detector": detector,
            "matcher_type": matcher_type,
            "ratio_thresh": ratio_thresh,
            "ransac_thresh": ransac_thresh,
            "alpha_rmse": alpha_rmse,
        }

        try:
            vis = feature_matcher_cv.draw_matches(
                float_path,
                self._ref_img_path,
                params_for_draw,
                max_draw=80,
                annotate=True,
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error al dibujar matches",
                f"Se han calculado los matches, pero no se pudo generar la imagen de visualización:\n{e}",
            )
            # Aun así actualizamos la barra de progreso
            try:
                self.progressBar.setValue(100)
            except Exception:
                pass
            return

        # Convertir imagen OpenCV (BGR) a QPixmap y mostrar en labelMatchesPreview
        try:
            h, w = vis.shape[:2]
            bytes_per_line = 3 * w
            qimg = QtGui.QImage(
                vis.data, w, h, bytes_per_line, QtGui.QImage.Format_BGR888
            )
            pix = QtGui.QPixmap.fromImage(qimg)

            label = self.labelMatchesPreview
            scaled = pix.scaled(
                label.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            label.setPixmap(scaled)
            label.setText("")
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error al mostrar matches",
                f"No se pudo mostrar la imagen de matches en la pestaña 'Matches':\n{e}",
            )

        # Poner la pestaña de matches al frente
        try:
            idx = self.tabViews.indexOf(self.tabMatches)
            if idx != -1:
                self.tabViews.setCurrentIndex(idx)
        except Exception:
            pass

        # Actualizar barra de progreso
        try:
            self.progressBar.setValue(100)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # MATRIZ DE TRANSFORMACIÓN: ACTUALIZAR UI
    # ------------------------------------------------------------------
    def update_transform_matrix(self, H, rmse=None):
        """
        Actualiza la etiqueta de matriz de transformación y el RMSE.

        H: matriz 3x3 (numpy array o lista de listas) o None
        rmse: error medio (float) opcional
        """
        # Matriz
        text = self._format_matrix_for_label(H)
        try:
            self.label_status_value.setText(text)
        except Exception:
            pass

        # RMSE
        try:
            if rmse is not None:
                self.label_rmse_value.setText(f"{rmse:.3f}")
            else:
                # Si no hay RMSE, mantenemos '-'
                self.label_rmse_value.setText("-")
        except Exception:
            pass

    def _format_matrix_for_label(self, H):
        """
        Devuelve la matriz formateada en varias líneas, tipo:

        [   1.000    0.002  -30.123]
        [   0.001    0.999   12.456]
        [   0.000    0.000    1.000]

        Si H es None, devuelve '(sin calcular)'.
        """
        if H is None:
            return "(sin calcular)"

        # Intentar convertir numpy array a lista de listas si es necesario
        try:
            import numpy as np
            if isinstance(H, np.ndarray):
                H = H.tolist()
        except Exception:
            pass

        # Si por lo que sea no es iterable, devolvemos str
        try:
            rows_iter = list(H)
        except TypeError:
            return str(H)

        rows = []
        for row in rows_iter:
            # Convertir cada elemento a float, si es posible
            formatted = []
            for v in row:
                try:
                    formatted.append(f"{float(v):8.3f}")
                except Exception:
                    formatted.append(str(v))
            row_str = "  ".join(formatted)
            rows.append(f"[{row_str}]")
        return "\n".join(rows)

    # ------------------------------------------------------------------
    # EXPORTAR MATRIZ DE TRANSFORMACIÓN
    # ------------------------------------------------------------------
    def _export_transform_matrix(self):
        """
        Exporta la matriz de transformación actual (self.current_homography)
        a un fichero CSV o TXT.
        """
        if self.current_homography is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Exportar matriz",
                "No hay ninguna matriz de transformación calculada.",
            )
            return

        path, flt = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Guardar matriz de transformación",
            "",
            "CSV (*.csv);;Texto (*.txt)",
        )
        if not path:
            return

        # Normalizar extensión si el usuario no la pone
        if os.path.splitext(path)[1] == "" and "CSV" in flt.upper():
            path = path + ".csv"

        # Convertir a lista de listas si viene como numpy array
        H = self.current_homography
        try:
            import numpy as np
            if isinstance(H, np.ndarray):
                H = H.tolist()
        except Exception:
            pass

        try:
            lines = []
            for row in H:
                # Si row no es iterable, escribir tal cual
                try:
                    iter(row)
                except TypeError:
                    lines.append(str(row))
                    continue

                vals = []
                for v in row:
                    try:
                        vals.append(str(float(v)))
                    except Exception:
                        vals.append(str(v))
                lines.append(",".join(vals))

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            QtWidgets.QMessageBox.information(
                self,
                "Exportar matriz",
                f"Matriz de transformación guardada en:\n{path}",
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error al exportar matriz",
                f"No se pudo guardar la matriz de transformación:\n{e}",
            )

    # ------------------------------------------------------------------
    # EXPORTAR PUNTOS DE CONTROL / GCPs
    # ------------------------------------------------------------------
    def _export_gcps(self):
        """
        Exporta los puntos de control actuales (self.current_gcps) a CSV.

        Se asume que self.current_gcps es:
          - una lista de dicts, o
          - una lista de tuplas/listas (se crean columnas genéricas).
        """
        if not self.current_gcps:
            QtWidgets.QMessageBox.warning(
                self,
                "Exportar puntos de control",
                "No hay puntos de control para exportar.",
            )
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Guardar puntos de control",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return

        if os.path.splitext(path)[1] == "":
            path = path + ".csv"

        gcps = self.current_gcps

        try:
            # Caso 1: lista de dicts
            if isinstance(gcps[0], dict):
                fieldnames = list(gcps[0].keys())
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for g in gcps:
                        writer.writerow(g)

            # Caso 2: lista de tuplas/listas
            else:
                first = gcps[0]
                try:
                    n_cols = len(first)
                except TypeError:
                    # Si no es iterable, lo volcamos como una sola columna
                    n_cols = 1

                fieldnames = [f"col{i+1}" for i in range(n_cols)]
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(fieldnames)
                    for g in gcps:
                        if n_cols == 1:
                            writer.writerow([g])
                        else:
                            try:
                                writer.writerow(list(g))
                            except Exception:
                                writer.writerow([str(g)])

            QtWidgets.QMessageBox.information(
                self,
                "Exportar puntos de control",
                f"Puntos de control guardados en:\n{path}",
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error al exportar puntos de control",
                f"No se pudo guardar el archivo CSV de puntos de control:\n{e}",
            )
