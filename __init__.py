# -*- coding: utf-8 -*-
"""
Autogeoreferencer QGIS Plugin
Estructura mínima:
├─ autogeoreferencer.py
├─ autogeoreferencer_dialog.py          ← usa la versión SAFE o PATCHED y renómbrala así
├─ basemap_utils.py                     ← opcional pero recomendado
├─ main_window_with_AOI_fixed.ui        ← archivo fuente de Qt Designer
└─ ui_main_window.py                    ← se genera en el paso 

Este archivo define el punto de entrada del plugin para QGIS.
"""

def classFactory(iface):
    """
    QGIS llama a esta función al cargar el plugin.
    Devuelve una instancia del plugin principal.
    """
    from .autogeoreferencer import AutogeoreferencerPlugin
    return AutogeoreferencerPlugin(iface)
