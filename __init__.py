def classFactory(iface):
    from .plugin import MiPluginQGIS
    return MiPluginQGIS(iface)