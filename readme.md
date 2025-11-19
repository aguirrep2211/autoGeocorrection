# autoGeocorrection

> Plugin y librería para **ortorrectificación automática de cualquier imagen raster** mediante **detección automática de features** y estimación robusta de transformaciones geométricas.

## Descripción  
`autoGeocorrection` es una herramienta diseñada para automatizar la geocorrección / ortorrectificación de imágenes **sin necesidad de puntos de control manuales**.  
El sistema detecta automáticamente características (features) en la imagen “flotante” y en la imagen de referencia, calcula una homografía o transformación óptima, evalúa su calidad y genera una versión ortorrectificada lista para usar en SIG.



## Características principales  
- **Detección automática de features** (AKAZE / ORB / otros) tanto en la imagen flotante como en la referencia.  
- **Matching robusto** y filtrado de correspondencias.  
- Estimación fiable de homografías (RANSAC y variantes).  
- **Ortorrectificación automática sin puntos de control manuales**.  
- Exportación a GeoTIFF y JSON con métricas.  
- Interfaz gráfica basada en Qt.  
- Integración opcional con **QGIS** como plugin.  
- Scripts avanzados para optimización por K‑Fold y análisis de RMSE (para workflows científicos o de gran precisión).

## Estructura del repositorio  
```
/
├── calculus/                     # Cálculo de homografías, matching y utilidades de procesamiento
├── gui/                          # Archivos de interfaz Qt
├── autogeoreferencer.py          # Núcleo del plugin/herramienta
├── autogeoreferencer_dialog.py   # Ventana principal Qt
├── autogeoreferencer_dockwidget.py
├── environment.yml               # Entorno Conda/Mamba
├── main_window.ui                # Interfaz Qt Designer
└── test_mainwindow.py            # Tests básicos
```

## Instalación  
```bash
git clone https://github.com/aguirrep2211/autoGeocorrection.git
cd autoGeocorrection
mamba env create -f environment.yml
mamba activate autoGeocorrection
python autogeoreferencer.py
```

## Uso básico  
1. Cargar una imagen sin georreferenciar (“flotante”).  
2. Cargar una imagen de referencia georreferenciada (GeoTIFF, WMS/XYZ, etc.).  
3. Seleccionar área de interés o trabajar sobre la imagen completa.  
4. La herramienta detectará automáticamente features en ambas imágenes.  
5. Se calculará la mejor homografía posible y se generará la imagen ortorrectificada.  
6. Puedes exportar la transformación, la imagen final y las métricas de ajuste.

## Características destacadas  
El principal valor añadido del proyecto es:  
### ⭐ *Ortorrectificación totalmente automática basada en feature detection*  
Sin necesidad de puntos de control manuales. Esto permite:  
- Procesar grandes lotes de imágenes rápidamente.  
- Uso en workflows de dron, satélite, cámaras móviles, fotografía aérea, etc.  
- Resultados reproducibles con RMSE exportable.

## Integración con QGIS  
El plugin permite:  
- Cargar y visualizar imágenes.  
- Dibujar AOIs.  
- Ejecutar la ortorrectificación desde la interfaz QGIS.  
- Exportar TIFF y transformaciones.

Para instalarlo en QGIS:  
Copia el directorio del plugin a:  
```
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/Autogeoreferencer
```
Actívalo desde *Complementos → Administrar e instalar complementos*.

## Autor  
**Pablo Iglesias Aguirre**

---

Si deseas una versión extendida con ejemplos, capturas o GIFs, puedo generarla.
