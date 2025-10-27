def classFactory(iface):
    from .autogeoreferencer import AutogeoreferencerPlugin
    return AutogeoreferencerPlugin(iface)
