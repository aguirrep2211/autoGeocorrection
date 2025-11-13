# Instalación de dependencias para Autogeoreferencer en QGIS

El plugin `Autogeoreferencer` utiliza librerías de Python adicionales:

- OpenCV (`opencv-python-headless`)
- scikit-learn (`scikit-learn`)
- numpy, scipy

Estas librerías **no vienen** con QGIS por defecto y deben instalarse
en el **mismo Python** que usa QGIS.

---

## 1. Comprobar el Python de QGIS

En QGIS:

1. Abrir `Plugins -> Consola Python`.
2. Ejecutar:

```python
import sys
print(sys.executable)
print(sys.version)
