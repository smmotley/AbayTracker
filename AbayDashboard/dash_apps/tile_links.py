url_list = {
    "SWE": "https://idpgis.ncep.noaa.gov/arcgis/services/NWS_Observations/NOHRSC_Snow_Analysis/"
            "MapServer/WmsServer?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/"
            "png&TRANSPARENT=true&LAYERS=1&WIDTH=256&HEIGHT=256&CRS=EPSG:3857&STYLES=&BBOX={bbox-epsg-3857}",
    "RADAR": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-$900913/{z}/{x}/{y}.png",
    "SAT_TILES": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    "PRECIP_24": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-n24p-900913/{z}/{x}/{y}.png",
    "PRECIP_48": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-n48p-900913/{z}/{x}/{y}.png",
    "PRECIP_72": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-n72p-900913/{z}/{x}/{y}.png",
}

class MapboxLayers:
    def __init__(self, url, name, sourcetype):
        self.name = name
        self.url = url
        self.sourcetype = sourcetype

    def load_urls(self):
        for key, value in url_list.items():
            self.name = key
            self.url = value
            self.sourcetype = 'raster'
        return self
