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
from PySide6.QtWidgets import (QApplication, QFrame, QMainWindow, QMdiArea,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1074, 733)
        MainWindow.setProperty(u"centralWidget", u"centralwidget")
        MainWindow.setProperty(u"menuBar", u"menubar")
        MainWindow.setProperty(u"statusBar", u"statusbar")
        self.actionNuevo = QAction(MainWindow)
        self.actionNuevo.setObjectName(u"actionNuevo")
        self.actionAbrir = QAction(MainWindow)
        self.actionAbrir.setObjectName(u"actionAbrir")
        self.actionGuardar = QAction(MainWindow)
        self.actionGuardar.setObjectName(u"actionGuardar")
        self.actionSalir = QAction(MainWindow)
        self.actionSalir.setObjectName(u"actionSalir")
        self.actionCargarImagenGeorreferenciar = QAction(MainWindow)
        self.actionCargarImagenGeorreferenciar.setObjectName(u"actionCargarImagenGeorreferenciar")
        self.actionCargarImagenReferencia = QAction(MainWindow)
        self.actionCargarImagenReferencia.setObjectName(u"actionCargarImagenReferencia")
        self.actionGetFromMainScreen = QAction(MainWindow)
        self.actionGetFromMainScreen.setObjectName(u"actionGetFromMainScreen")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.frame_image = QFrame(self.centralwidget)
        self.frame_image.setObjectName(u"frame_image")
        self.frame_image.setGeometry(QRect(0, 0, 511, 401))
        self.frame_image.setFrameShape(QFrame.StyledPanel)
        self.frame_image.setFrameShadow(QFrame.Raised)
        self.btnCargarReferencia = QPushButton(self.centralwidget)
        self.btnCargarReferencia.setObjectName(u"btnCargarReferencia")
        self.btnCargarReferencia.setGeometry(QRect(860, 60, 201, 41))
        self.mdiArea = QMdiArea(self.centralwidget)
        self.mdiArea.setObjectName(u"mdiArea")
        self.mdiArea.setGeometry(QRect(250, 420, 661, 261))
        self.btnCargarFlotante = QPushButton(self.centralwidget)
        self.btnCargarFlotante.setObjectName(u"btnCargarFlotante")
        self.btnCargarFlotante.setGeometry(QRect(860, 10, 201, 41))
        self.img_from_basemap = QPushButton(self.centralwidget)
        self.img_from_basemap.setObjectName(u"img_from_basemap")
        self.img_from_basemap.setGeometry(QRect(860, 110, 201, 41))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1074, 22))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuEditar = QMenu(self.menubar)
        self.menuEditar.setObjectName(u"menuEditar")
        self.menuVer = QMenu(self.menubar)
        self.menuVer.setObjectName(u"menuVer")
        self.menuConfiguracion = QMenu(self.menubar)
        self.menuConfiguracion.setObjectName(u"menuConfiguracion")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuEditar.menuAction())
        self.menubar.addAction(self.menuVer.menuAction())
        self.menubar.addAction(self.menuConfiguracion.menuAction())
        self.menuArchivo.addAction(self.actionNuevo)
        self.menuArchivo.addAction(self.actionAbrir)
        self.menuArchivo.addAction(self.actionGuardar)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Mi Ventana QGIS", None))
        self.actionNuevo.setText(QCoreApplication.translate("MainWindow", u"&Nuevo", None))
#if QT_CONFIG(statustip)
        self.actionNuevo.setStatusTip(QCoreApplication.translate("MainWindow", u"Crear nuevo proyecto", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(shortcut)
        self.actionNuevo.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
        self.actionAbrir.setText(QCoreApplication.translate("MainWindow", u"&Abrir\u2026", None))
#if QT_CONFIG(statustip)
        self.actionAbrir.setStatusTip(QCoreApplication.translate("MainWindow", u"Abrir archivo", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(shortcut)
        self.actionAbrir.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.actionGuardar.setText(QCoreApplication.translate("MainWindow", u"&Guardar", None))
#if QT_CONFIG(statustip)
        self.actionGuardar.setStatusTip(QCoreApplication.translate("MainWindow", u"Guardar archivo", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(shortcut)
        self.actionGuardar.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"&Salir", None))
#if QT_CONFIG(statustip)
        self.actionSalir.setStatusTip(QCoreApplication.translate("MainWindow", u"Salir de la aplicaci\u00f3n", None))
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(shortcut)
        self.actionSalir.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionCargarImagenGeorreferenciar.setText(QCoreApplication.translate("MainWindow", u"Cargar imagen a georreferenciar", None))
#if QT_CONFIG(tooltip)
        self.actionCargarImagenGeorreferenciar.setToolTip(QCoreApplication.translate("MainWindow", u"Selecciona la imagen SIN CRS que vas a registrar", None))
#endif // QT_CONFIG(tooltip)
        self.actionCargarImagenReferencia.setText(QCoreApplication.translate("MainWindow", u"Cargar imagen de referencia", None))
#if QT_CONFIG(tooltip)
        self.actionCargarImagenReferencia.setToolTip(QCoreApplication.translate("MainWindow", u"Selecciona la ortofoto/raster con CRS de referencia", None))
#endif // QT_CONFIG(tooltip)
        self.actionGetFromMainScreen.setText(QCoreApplication.translate("MainWindow", u"Capturar desde pantalla", None))
#if QT_CONFIG(tooltip)
        self.actionGetFromMainScreen.setToolTip(QCoreApplication.translate("MainWindow", u"Selecciona un rect\u00e1ngulo en el mapa principal de QGIS y captura la vista", None))
#endif // QT_CONFIG(tooltip)
        self.btnCargarReferencia.setText(QCoreApplication.translate("MainWindow", u"Cargar imagen a referenciar", None))
        self.btnCargarFlotante.setText(QCoreApplication.translate("MainWindow", u"Cargar Imagen de referencia", None))
        self.img_from_basemap.setText(QCoreApplication.translate("MainWindow", u"Cargar referencia desde base map", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"&Archivo", None))
        self.menuEditar.setTitle(QCoreApplication.translate("MainWindow", u"&Editar", None))
        self.menuVer.setTitle(QCoreApplication.translate("MainWindow", u"&Ver", None))
        self.menuConfiguracion.setTitle(QCoreApplication.translate("MainWindow", u"Con&figuraci\u00f3n", None))
    # retranslateUi

