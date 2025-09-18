# mi_plugin_qgis/dev_debug.py
import os
def enable_debugpy():
    if os.getenv("QGIS_DEBUGPY", "0") == "1":
        try:
            import debugpy
            port = int(os.getenv("QGIS_DEBUGPY_PORT", "5678"))
            debugpy.listen(("127.0.0.1", port))
            print(f"[debugpy] Esperando attach en {port}...")
            # Opcional: bloquear hasta que el debugger se conecte
            # debugpy.wait_for_client()
        except Exception as e:
            print("[debugpy] no disponible:", e)
