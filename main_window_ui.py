# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QSplitter, QStackedWidget, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1220, 780)
        self.actionLoadFloating = QAction(MainWindow)
        self.actionLoadFloating.setObjectName(u"actionLoadFloating")
        self.actionLoadReference = QAction(MainWindow)
        self.actionLoadReference.setObjectName(u"actionLoadReference")
        self.actionLoadBasemap = QAction(MainWindow)
        self.actionLoadBasemap.setObjectName(u"actionLoadBasemap")
        self.actionExportOrtho = QAction(MainWindow)
        self.actionExportOrtho.setObjectName(u"actionExportOrtho")
        self.actionSalir = QAction(MainWindow)
        self.actionSalir.setObjectName(u"actionSalir")
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_main = QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setObjectName(u"verticalLayout_main")
        self.splitterMain = QSplitter(self.centralwidget)
        self.splitterMain.setObjectName(u"splitterMain")
        self.splitterMain.setOrientation(Qt.Horizontal)
        self.stackSteps = QStackedWidget(self.splitterMain)
        self.stackSteps.setObjectName(u"stackSteps")
        self.stackSteps.setMinimumSize(QSize(300, 400))
        self.pageSources = QWidget()
        self.pageSources.setObjectName(u"pageSources")
        self.verticalLayout_sources = QVBoxLayout(self.pageSources)
        self.verticalLayout_sources.setObjectName(u"verticalLayout_sources")
        self.groupFloating = QGroupBox(self.pageSources)
        self.groupFloating.setObjectName(u"groupFloating")
        self.grid_floating = QGridLayout(self.groupFloating)
        self.grid_floating.setObjectName(u"grid_floating")
        self.editFloatingPath = QLineEdit(self.groupFloating)
        self.editFloatingPath.setObjectName(u"editFloatingPath")

        self.grid_floating.addWidget(self.editFloatingPath, 0, 0, 1, 1)

        self.btnBrowseFloating = QPushButton(self.groupFloating)
        self.btnBrowseFloating.setObjectName(u"btnBrowseFloating")

        self.grid_floating.addWidget(self.btnBrowseFloating, 0, 1, 1, 1)

        self.labelFloatingInfo = QLabel(self.groupFloating)
        self.labelFloatingInfo.setObjectName(u"labelFloatingInfo")

        self.grid_floating.addWidget(self.labelFloatingInfo, 1, 0, 1, 2)


        self.verticalLayout_sources.addWidget(self.groupFloating)

        self.groupReference = QGroupBox(self.pageSources)
        self.groupReference.setObjectName(u"groupReference")
        self.grid_reference = QGridLayout(self.groupReference)
        self.grid_reference.setObjectName(u"grid_reference")
        self.editReferencePath = QLineEdit(self.groupReference)
        self.editReferencePath.setObjectName(u"editReferencePath")

        self.grid_reference.addWidget(self.editReferencePath, 0, 0, 1, 1)

        self.btnBrowseReference = QPushButton(self.groupReference)
        self.btnBrowseReference.setObjectName(u"btnBrowseReference")

        self.grid_reference.addWidget(self.btnBrowseReference, 0, 1, 1, 1)

        self.btnLoadReferenceFromCanvas = QPushButton(self.groupReference)
        self.btnLoadReferenceFromCanvas.setObjectName(u"btnLoadReferenceFromCanvas")

        self.grid_reference.addWidget(self.btnLoadReferenceFromCanvas, 1, 0, 1, 2)

        self.labelReferenceInfo = QLabel(self.groupReference)
        self.labelReferenceInfo.setObjectName(u"labelReferenceInfo")

        self.grid_reference.addWidget(self.labelReferenceInfo, 2, 0, 1, 2)


        self.verticalLayout_sources.addWidget(self.groupReference)

        self.groupDEM = QGroupBox(self.pageSources)
        self.groupDEM.setObjectName(u"groupDEM")
        self.grid_dem = QGridLayout(self.groupDEM)
        self.grid_dem.setObjectName(u"grid_dem")
        self.editDEMPath = QLineEdit(self.groupDEM)
        self.editDEMPath.setObjectName(u"editDEMPath")

        self.grid_dem.addWidget(self.editDEMPath, 0, 0, 1, 1)

        self.btnBrowseDEM = QPushButton(self.groupDEM)
        self.btnBrowseDEM.setObjectName(u"btnBrowseDEM")

        self.grid_dem.addWidget(self.btnBrowseDEM, 0, 1, 1, 1)

        self.labelDEMInfo = QLabel(self.groupDEM)
        self.labelDEMInfo.setObjectName(u"labelDEMInfo")

        self.grid_dem.addWidget(self.labelDEMInfo, 1, 0, 1, 2)


        self.verticalLayout_sources.addWidget(self.groupDEM)

        self.verticalSpacer_sources = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_sources.addItem(self.verticalSpacer_sources)

        self.stackSteps.addWidget(self.pageSources)
        self.pageAOI = QWidget()
        self.pageAOI.setObjectName(u"pageAOI")
        self.verticalLayout_aoi = QVBoxLayout(self.pageAOI)
        self.verticalLayout_aoi.setObjectName(u"verticalLayout_aoi")
        self.groupAOI = QGroupBox(self.pageAOI)
        self.groupAOI.setObjectName(u"groupAOI")
        self.vbox_aoi = QVBoxLayout(self.groupAOI)
        self.vbox_aoi.setSpacing(6)
        self.vbox_aoi.setObjectName(u"vbox_aoi")
        self.labelAOIInfo = QLabel(self.groupAOI)
        self.labelAOIInfo.setObjectName(u"labelAOIInfo")

        self.vbox_aoi.addWidget(self.labelAOIInfo)

        self.hbox_aoi_buttons = QHBoxLayout()
        self.hbox_aoi_buttons.setObjectName(u"hbox_aoi_buttons")
        self.btnDrawAOI = QPushButton(self.groupAOI)
        self.btnDrawAOI.setObjectName(u"btnDrawAOI")

        self.hbox_aoi_buttons.addWidget(self.btnDrawAOI)

        self.btnClearAOI = QPushButton(self.groupAOI)
        self.btnClearAOI.setObjectName(u"btnClearAOI")

        self.hbox_aoi_buttons.addWidget(self.btnClearAOI)

        self.horizontalSpacer_aoi = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.hbox_aoi_buttons.addItem(self.horizontalSpacer_aoi)


        self.vbox_aoi.addLayout(self.hbox_aoi_buttons)

        self.labelAOIStatus = QLabel(self.groupAOI)
        self.labelAOIStatus.setObjectName(u"labelAOIStatus")

        self.vbox_aoi.addWidget(self.labelAOIStatus)


        self.verticalLayout_aoi.addWidget(self.groupAOI)

        self.verticalSpacer_aoi = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_aoi.addItem(self.verticalSpacer_aoi)

        self.stackSteps.addWidget(self.pageAOI)
        self.pageMatching = QWidget()
        self.pageMatching.setObjectName(u"pageMatching")
        self.verticalLayout_matching = QVBoxLayout(self.pageMatching)
        self.verticalLayout_matching.setObjectName(u"verticalLayout_matching")
        self.groupMatchingParams = QGroupBox(self.pageMatching)
        self.groupMatchingParams.setObjectName(u"groupMatchingParams")
        self.grid_matching = QGridLayout(self.groupMatchingParams)
        self.grid_matching.setObjectName(u"grid_matching")
        self.label_detector = QLabel(self.groupMatchingParams)
        self.label_detector.setObjectName(u"label_detector")

        self.grid_matching.addWidget(self.label_detector, 0, 0, 1, 1)

        self.comboDetector = QComboBox(self.groupMatchingParams)
        self.comboDetector.addItem("")
        self.comboDetector.addItem("")
        self.comboDetector.setObjectName(u"comboDetector")

        self.grid_matching.addWidget(self.comboDetector, 0, 1, 1, 1)

        self.label_maxFeatures = QLabel(self.groupMatchingParams)
        self.label_maxFeatures.setObjectName(u"label_maxFeatures")

        self.grid_matching.addWidget(self.label_maxFeatures, 1, 0, 1, 1)

        self.spinMaxFeatures = QSpinBox(self.groupMatchingParams)
        self.spinMaxFeatures.setObjectName(u"spinMaxFeatures")
        self.spinMaxFeatures.setMaximum(100000)
        self.spinMaxFeatures.setValue(5000)

        self.grid_matching.addWidget(self.spinMaxFeatures, 1, 1, 1, 1)

        self.label_matcher = QLabel(self.groupMatchingParams)
        self.label_matcher.setObjectName(u"label_matcher")

        self.grid_matching.addWidget(self.label_matcher, 2, 0, 1, 1)

        self.comboMatcher = QComboBox(self.groupMatchingParams)
        self.comboMatcher.addItem("")
        self.comboMatcher.addItem("")
        self.comboMatcher.setObjectName(u"comboMatcher")

        self.grid_matching.addWidget(self.comboMatcher, 2, 1, 1, 1)

        self.label_ratio = QLabel(self.groupMatchingParams)
        self.label_ratio.setObjectName(u"label_ratio")

        self.grid_matching.addWidget(self.label_ratio, 3, 0, 1, 1)

        self.spinRatio = QDoubleSpinBox(self.groupMatchingParams)
        self.spinRatio.setObjectName(u"spinRatio")
        self.spinRatio.setDecimals(2)
        self.spinRatio.setSingleStep(0.050000000000000)
        self.spinRatio.setValue(0.750000000000000)

        self.grid_matching.addWidget(self.spinRatio, 3, 1, 1, 1)

        self.label_minMatches = QLabel(self.groupMatchingParams)
        self.label_minMatches.setObjectName(u"label_minMatches")

        self.grid_matching.addWidget(self.label_minMatches, 4, 0, 1, 1)

        self.spinMinMatches = QSpinBox(self.groupMatchingParams)
        self.spinMinMatches.setObjectName(u"spinMinMatches")
        self.spinMinMatches.setMaximum(10000)
        self.spinMinMatches.setValue(20)

        self.grid_matching.addWidget(self.spinMinMatches, 4, 1, 1, 1)


        self.verticalLayout_matching.addWidget(self.groupMatchingParams)

        self.verticalSpacer_matching = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_matching.addItem(self.verticalSpacer_matching)

        self.stackSteps.addWidget(self.pageMatching)
        self.pageOutput = QWidget()
        self.pageOutput.setObjectName(u"pageOutput")
        self.verticalLayout_output = QVBoxLayout(self.pageOutput)
        self.verticalLayout_output.setObjectName(u"verticalLayout_output")
        self.groupOutput = QGroupBox(self.pageOutput)
        self.groupOutput.setObjectName(u"groupOutput")
        self.grid_output = QGridLayout(self.groupOutput)
        self.grid_output.setObjectName(u"grid_output")
        self.label_outputPath = QLabel(self.groupOutput)
        self.label_outputPath.setObjectName(u"label_outputPath")

        self.grid_output.addWidget(self.label_outputPath, 0, 0, 1, 1)

        self.editOutputFolder = QLineEdit(self.groupOutput)
        self.editOutputFolder.setObjectName(u"editOutputFolder")

        self.grid_output.addWidget(self.editOutputFolder, 0, 1, 1, 1)

        self.btnBrowseOutputFolder = QPushButton(self.groupOutput)
        self.btnBrowseOutputFolder.setObjectName(u"btnBrowseOutputFolder")

        self.grid_output.addWidget(self.btnBrowseOutputFolder, 0, 2, 1, 1)

        self.label_outputCrs = QLabel(self.groupOutput)
        self.label_outputCrs.setObjectName(u"label_outputCrs")

        self.grid_output.addWidget(self.label_outputCrs, 1, 0, 1, 1)

        self.comboOutputCrs = QComboBox(self.groupOutput)
        self.comboOutputCrs.setObjectName(u"comboOutputCrs")

        self.grid_output.addWidget(self.comboOutputCrs, 1, 1, 1, 2)

        self.label_outputFormat = QLabel(self.groupOutput)
        self.label_outputFormat.setObjectName(u"label_outputFormat")

        self.grid_output.addWidget(self.label_outputFormat, 2, 0, 1, 1)

        self.comboOutputFormat = QComboBox(self.groupOutput)
        self.comboOutputFormat.addItem("")
        self.comboOutputFormat.addItem("")
        self.comboOutputFormat.setObjectName(u"comboOutputFormat")

        self.grid_output.addWidget(self.comboOutputFormat, 2, 1, 1, 1)


        self.verticalLayout_output.addWidget(self.groupOutput)

        self.verticalSpacer_output = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_output.addItem(self.verticalSpacer_output)

        self.stackSteps.addWidget(self.pageOutput)
        self.splitterMain.addWidget(self.stackSteps)
        self.tabViews = QTabWidget(self.splitterMain)
        self.tabViews.setObjectName(u"tabViews")
        self.tabSideBySide = QWidget()
        self.tabSideBySide.setObjectName(u"tabSideBySide")
        self.hbox_side_by_side = QHBoxLayout(self.tabSideBySide)
        self.hbox_side_by_side.setObjectName(u"hbox_side_by_side")
        self.groupFloatPreview = QGroupBox(self.tabSideBySide)
        self.groupFloatPreview.setObjectName(u"groupFloatPreview")
        self.vbox_float_preview = QVBoxLayout(self.groupFloatPreview)
        self.vbox_float_preview.setSpacing(0)
        self.vbox_float_preview.setObjectName(u"vbox_float_preview")
        self.vbox_float_preview.setContentsMargins(0, 0, 0, 0)
        self.labelFloatPreview = QLabel(self.groupFloatPreview)
        self.labelFloatPreview.setObjectName(u"labelFloatPreview")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.labelFloatPreview.sizePolicy().hasHeightForWidth())
        self.labelFloatPreview.setSizePolicy(sizePolicy)
        self.labelFloatPreview.setMinimumSize(QSize(256, 256))
        self.labelFloatPreview.setMaximumSize(QSize(256, 256))
        self.labelFloatPreview.setFrameShape(QFrame.StyledPanel)
        self.labelFloatPreview.setFrameShadow(QFrame.Sunken)
        self.labelFloatPreview.setAlignment(Qt.AlignCenter)

        self.vbox_float_preview.addWidget(self.labelFloatPreview)


        self.hbox_side_by_side.addWidget(self.groupFloatPreview)

        self.groupRefPreview = QGroupBox(self.tabSideBySide)
        self.groupRefPreview.setObjectName(u"groupRefPreview")
        self.vbox_ref_preview = QVBoxLayout(self.groupRefPreview)
        self.vbox_ref_preview.setSpacing(0)
        self.vbox_ref_preview.setObjectName(u"vbox_ref_preview")
        self.vbox_ref_preview.setContentsMargins(0, 0, 0, 0)
        self.labelRefPreview = QLabel(self.groupRefPreview)
        self.labelRefPreview.setObjectName(u"labelRefPreview")
        sizePolicy.setHeightForWidth(self.labelRefPreview.sizePolicy().hasHeightForWidth())
        self.labelRefPreview.setSizePolicy(sizePolicy)
        self.labelRefPreview.setMinimumSize(QSize(256, 256))
        self.labelRefPreview.setMaximumSize(QSize(256, 256))
        self.labelRefPreview.setFrameShape(QFrame.StyledPanel)
        self.labelRefPreview.setFrameShadow(QFrame.Sunken)
        self.labelRefPreview.setAlignment(Qt.AlignCenter)

        self.vbox_ref_preview.addWidget(self.labelRefPreview)


        self.hbox_side_by_side.addWidget(self.groupRefPreview)

        self.tabViews.addTab(self.tabSideBySide, "")
        self.tabMatches = QWidget()
        self.tabMatches.setObjectName(u"tabMatches")
        self.vbox_matches = QVBoxLayout(self.tabMatches)
        self.vbox_matches.setObjectName(u"vbox_matches")
        self.labelMatchesInfo = QLabel(self.tabMatches)
        self.labelMatchesInfo.setObjectName(u"labelMatchesInfo")

        self.vbox_matches.addWidget(self.labelMatchesInfo)

        self.labelMatchesPreview = QLabel(self.tabMatches)
        self.labelMatchesPreview.setObjectName(u"labelMatchesPreview")
        self.labelMatchesPreview.setFrameShape(QFrame.StyledPanel)
        self.labelMatchesPreview.setFrameShadow(QFrame.Sunken)
        self.labelMatchesPreview.setAlignment(Qt.AlignCenter)

        self.vbox_matches.addWidget(self.labelMatchesPreview)

        self.tabViews.addTab(self.tabMatches, "")
        self.tabResiduals = QWidget()
        self.tabResiduals.setObjectName(u"tabResiduals")
        self.vbox_residuals = QVBoxLayout(self.tabResiduals)
        self.vbox_residuals.setObjectName(u"vbox_residuals")
        self.labelResidualsInfo = QLabel(self.tabResiduals)
        self.labelResidualsInfo.setObjectName(u"labelResidualsInfo")

        self.vbox_residuals.addWidget(self.labelResidualsInfo)

        self.labelResidualsPreview = QLabel(self.tabResiduals)
        self.labelResidualsPreview.setObjectName(u"labelResidualsPreview")
        self.labelResidualsPreview.setFrameShape(QFrame.StyledPanel)
        self.labelResidualsPreview.setFrameShadow(QFrame.Sunken)
        self.labelResidualsPreview.setAlignment(Qt.AlignCenter)

        self.vbox_residuals.addWidget(self.labelResidualsPreview)

        self.tabViews.addTab(self.tabResiduals, "")
        self.splitterMain.addWidget(self.tabViews)

        self.verticalLayout_main.addWidget(self.splitterMain)

        self.frameBottom = QFrame(self.centralwidget)
        self.frameBottom.setObjectName(u"frameBottom")
        self.frameBottom.setFrameShape(QFrame.StyledPanel)
        self.frameBottom.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_bottom = QHBoxLayout(self.frameBottom)
        self.horizontalLayout_bottom.setObjectName(u"horizontalLayout_bottom")
        self.hbox_step_controls = QHBoxLayout()
        self.hbox_step_controls.setObjectName(u"hbox_step_controls")
        self.btnNextStep = QPushButton(self.frameBottom)
        self.btnNextStep.setObjectName(u"btnNextStep")

        self.hbox_step_controls.addWidget(self.btnNextStep)


        self.horizontalLayout_bottom.addLayout(self.hbox_step_controls)

        self.horizontalSpacer_bottom = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_bottom.addItem(self.horizontalSpacer_bottom)

        self.grid_status = QGridLayout()
        self.grid_status.setObjectName(u"grid_status")
        self.label_status_title = QLabel(self.frameBottom)
        self.label_status_title.setObjectName(u"label_status_title")

        self.grid_status.addWidget(self.label_status_title, 0, 0, 1, 1)

        self.label_status_value = QLabel(self.frameBottom)
        self.label_status_value.setObjectName(u"label_status_value")

        self.grid_status.addWidget(self.label_status_value, 0, 1, 1, 1)

        self.label_rmse_title = QLabel(self.frameBottom)
        self.label_rmse_title.setObjectName(u"label_rmse_title")

        self.grid_status.addWidget(self.label_rmse_title, 1, 0, 1, 1)

        self.label_rmse_value = QLabel(self.frameBottom)
        self.label_rmse_value.setObjectName(u"label_rmse_value")

        self.grid_status.addWidget(self.label_rmse_value, 1, 1, 1, 1)

        self.label_progress_title = QLabel(self.frameBottom)
        self.label_progress_title.setObjectName(u"label_progress_title")

        self.grid_status.addWidget(self.label_progress_title, 2, 0, 1, 1)

        self.progressBar = QProgressBar(self.frameBottom)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)

        self.grid_status.addWidget(self.progressBar, 2, 1, 1, 1)


        self.horizontalLayout_bottom.addLayout(self.grid_status)


        self.verticalLayout_main.addWidget(self.frameBottom)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1220, 24))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuAyuda = QMenu(self.menubar)
        self.menuAyuda.setObjectName(u"menuAyuda")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuAyuda.menuAction())
        self.menuArchivo.addAction(self.actionLoadFloating)
        self.menuArchivo.addAction(self.actionLoadReference)
        self.menuArchivo.addAction(self.actionLoadBasemap)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionExportOrtho)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuAyuda.addAction(self.actionAbout)

        self.retranslateUi(MainWindow)

        self.tabViews.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Autogeoreferencer", None))
        self.actionLoadFloating.setText(QCoreApplication.translate("MainWindow", u"Cargar imagen flotante...", None))
        self.actionLoadReference.setText(QCoreApplication.translate("MainWindow", u"Cargar referencia...", None))
        self.actionLoadBasemap.setText(QCoreApplication.translate("MainWindow", u"Cargar referencia desde mapa...", None))
        self.actionExportOrtho.setText(QCoreApplication.translate("MainWindow", u"Exportar ortomosaico...", None))
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"Acerca de Autogeoreferencer...", None))
        self.groupFloating.setTitle(QCoreApplication.translate("MainWindow", u"Imagen a georreferenciar (flotante)", None))
        self.editFloatingPath.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Ruta de la imagen (tif, jpg, png...)", None))
        self.btnBrowseFloating.setText(QCoreApplication.translate("MainWindow", u"Examinar...", None))
        self.labelFloatingInfo.setText(QCoreApplication.translate("MainWindow", u"No hay imagen cargada", None))
        self.groupReference.setTitle(QCoreApplication.translate("MainWindow", u"Capa de referencia (georreferenciada)", None))
        self.editReferencePath.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Ruta de la capa (raster/vector)", None))
        self.btnBrowseReference.setText(QCoreApplication.translate("MainWindow", u"Examinar...", None))
        self.btnLoadReferenceFromCanvas.setText(QCoreApplication.translate("MainWindow", u"Cargar referencia desde el mapa de QGIS", None))
        self.labelReferenceInfo.setText(QCoreApplication.translate("MainWindow", u"No hay referencia cargada", None))
        self.groupDEM.setTitle(QCoreApplication.translate("MainWindow", u"Modelo Digital de Elevaciones (MDE)", None))
        self.editDEMPath.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Ruta del MDE (tif, asc, etc.)", None))
        self.btnBrowseDEM.setText(QCoreApplication.translate("MainWindow", u"Examinar...", None))
        self.labelDEMInfo.setText(QCoreApplication.translate("MainWindow", u"No hay MDE cargado", None))
        self.groupAOI.setTitle(QCoreApplication.translate("MainWindow", u"\u00c1rea de Inter\u00e9s (AOI)", None))
        self.labelAOIInfo.setText(QCoreApplication.translate("MainWindow", u"Defina un rect\u00e1ngulo de inter\u00e9s sobre la referencia.", None))
        self.btnDrawAOI.setText(QCoreApplication.translate("MainWindow", u"Dibujar AOI", None))
        self.btnClearAOI.setText(QCoreApplication.translate("MainWindow", u"Limpiar AOI", None))
        self.labelAOIStatus.setText(QCoreApplication.translate("MainWindow", u"AOI no definida", None))
        self.groupMatchingParams.setTitle(QCoreApplication.translate("MainWindow", u"Par\u00e1metros de emparejamiento", None))
        self.label_detector.setText(QCoreApplication.translate("MainWindow", u"Detector de caracter\u00edsticas:", None))
        self.comboDetector.setItemText(0, QCoreApplication.translate("MainWindow", u"ORB", None))
        self.comboDetector.setItemText(1, QCoreApplication.translate("MainWindow", u"SIFT", None))

        self.label_maxFeatures.setText(QCoreApplication.translate("MainWindow", u"N\u00famero m\u00e1ximo de puntos:", None))
        self.label_matcher.setText(QCoreApplication.translate("MainWindow", u"Algoritmo de emparejamiento:", None))
        self.comboMatcher.setItemText(0, QCoreApplication.translate("MainWindow", u"FLANN", None))
        self.comboMatcher.setItemText(1, QCoreApplication.translate("MainWindow", u"BFMatcher", None))

        self.label_ratio.setText(QCoreApplication.translate("MainWindow", u"Ratio test (Lowe):", None))
        self.label_minMatches.setText(QCoreApplication.translate("MainWindow", u"M\u00ednimo de matches v\u00e1lidos:", None))
        self.groupOutput.setTitle(QCoreApplication.translate("MainWindow", u"Salida y opciones de exportaci\u00f3n", None))
        self.label_outputPath.setText(QCoreApplication.translate("MainWindow", u"Carpeta de salida:", None))
        self.editOutputFolder.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Directorio para el ortomosaico georreferenciado", None))
        self.btnBrowseOutputFolder.setText(QCoreApplication.translate("MainWindow", u"Examinar...", None))
        self.label_outputCrs.setText(QCoreApplication.translate("MainWindow", u"CRS de salida:", None))
        self.label_outputFormat.setText(QCoreApplication.translate("MainWindow", u"Formato:", None))
        self.comboOutputFormat.setItemText(0, QCoreApplication.translate("MainWindow", u"GeoTIFF", None))
        self.comboOutputFormat.setItemText(1, QCoreApplication.translate("MainWindow", u"PNG", None))

        self.groupFloatPreview.setTitle(QCoreApplication.translate("MainWindow", u"Imagen flotante", None))
        self.labelFloatPreview.setText(QCoreApplication.translate("MainWindow", u"(Sin imagen)", None))
        self.groupRefPreview.setTitle(QCoreApplication.translate("MainWindow", u"Referencia", None))
        self.labelRefPreview.setText(QCoreApplication.translate("MainWindow", u"(Sin imagen)", None))
        self.tabViews.setTabText(self.tabViews.indexOf(self.tabSideBySide), QCoreApplication.translate("MainWindow", u"Vista lado a lado", None))
        self.labelMatchesInfo.setText(QCoreApplication.translate("MainWindow", u"Visualizaci\u00f3n de puntos emparejados entre la imagen flotante y la referencia.", None))
        self.labelMatchesPreview.setText(QCoreApplication.translate("MainWindow", u"(Sin visualizaci\u00f3n)", None))
        self.tabViews.setTabText(self.tabViews.indexOf(self.tabMatches), QCoreApplication.translate("MainWindow", u"Matches", None))
        self.labelResidualsInfo.setText(QCoreApplication.translate("MainWindow", u"Mapa o gr\u00e1fica de residuales de la transformaci\u00f3n.", None))
        self.labelResidualsPreview.setText(QCoreApplication.translate("MainWindow", u"(Sin visualizaci\u00f3n)", None))
        self.tabViews.setTabText(self.tabViews.indexOf(self.tabResiduals), QCoreApplication.translate("MainWindow", u"Residuales", None))
        self.btnNextStep.setText(QCoreApplication.translate("MainWindow", u"GET MATCHES >", None))
        self.label_status_title.setText(QCoreApplication.translate("MainWindow", u"Estado:", None))
        self.label_status_value.setText(QCoreApplication.translate("MainWindow", u"Listo", None))
        self.label_rmse_title.setText(QCoreApplication.translate("MainWindow", u"RMSE:", None))
        self.label_rmse_value.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.label_progress_title.setText(QCoreApplication.translate("MainWindow", u"Progreso:", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"Archivo", None))
        self.menuAyuda.setTitle(QCoreApplication.translate("MainWindow", u"Ayuda", None))
    # retranslateUi

