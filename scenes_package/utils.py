# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Utils
Description          : Utils class/functions for general proposite
Date                 : February, 2023
copyright            : (C) 2023 by Luiz Motta
email                : luiz.motta@ibama.gov.br
***************************************************************************/
 
/***************************************************************************
Division of Monitorament and Combat - DMC
National Center for Wildfire Prevention and Suppression - Prevfogo
Brazilian Institute for the Environment and Renewable Natural Resources - Ibama
https://www.gov.br/ibama/

***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
***************************************************************************/
"""


from osgeo import gdal
import os
import geojson
import requests
from tqdm import tqdm
from shapely.geometry import shape
from shapely.affinity import scale

from ipywidgets import  HTML
from ipyleaflet import GeoJSON, Popup


class UtilScenes(object):
    colorMessage = lambda msg, color: f"<b style='color:{color};'> {msg} </b>"
    color_ok = '#2E9AFE'
    color_error = 'red'

    @staticmethod
    def downloadScene(item, path_download):
        def download(fname, url):
            resp = requests.get(url, stream=True)
            total = int(resp.headers.get('content-length', 0))
            chunk_size = 1024
            # Can also replace 'file' with a io.BytesIO object
            with open(fname, 'wb') as file, tqdm(
                desc=fname,
                total=total,
                unit='iB',
                unit_scale=True,
                unit_divisor=chunk_size,
                #leave=False
            ) as bar:
                for data in resp.iter_content(chunk_size=chunk_size):
                    size = file.write(data)
                    bar.update(size)
                bar.close()

        # value = { 'name_tif', 'total_mb', 'url'}
        for asset, value in item.url_assets.items():
            fname = os.path.join( path_download, value['name_tif'] )
            download( fname, value['url'] )

        if len( item.url_assets ):
            bands = [ os.path.join( path_download, value['name_tif'] ) for value in item.url_assets.values() ]
            fname = os.path.join( path_download, f"{item.scene}_rgb.vrt" )
            vrt = gdal.BuildVRT( fname, bands, separate=True )
            vrt = None

    @staticmethod
    def styleLinkHtml(id_link):
        return """
            #{ELEMENT}_a:link    { color: #B9B49A; }
            #{ELEMENT}_a:visited { color: #BCB073; }
            #{ELEMENT}_a:hover   { color: #BEA62A; }
            #{ELEMENT}_a:active  { color: #D5DE54; }
        """.replace('{ELEMENT}', id_link )

    @staticmethod
    def linksUrlBand(item, id_element):
        s_format = """{asset}: <a id="#ELEMENT#_a" href="{url}" target="_blank">{name_tif} </a>  ({total_mb:.2f} MB)""".replace('#ELEMENT#', id_element )
        return [ s_format.format( **value, asset=asset ) for asset, value in item.url_assets.items() ]

    @staticmethod
    def htmlRows(values, type_row, id_element_table):
        html = ' '.join( [ f'<{type_row} id="#ELEMENT#_row">{item}</{type_row}>' for item in values ] )
        return f'<tr>{html}</tr>'.replace('#ELEMENT#', id_element_table )
    
    @staticmethod
    def footprint(name, scenes, ids=[]):
        """
        Args:
            - scenes: { scene: Item }
            - name: name of layer
            - ids: List of scene (key)
        Return: geojson
        """
        feat = lambda item: geojson.Feature( geometry=item.geometry, properties={ 'scene': item.scene } )
        features =  [ feat( item ) for item in scenes ] if not len( ids ) else \
                    [ feat( item ) for item in scenes if item.scene in ids ]
        
        return {
            'name': name,
            'type': 'FeatureCollection',
            'features': features
        }

    @staticmethod
    def toggleLayoutDisplay(widget, is_visible):
        # Values for display: block = Visible, none = Hide
        lyt_display = 'block' if is_visible else 'none'
        
        if type( widget ) in ( tuple, list ):
            for w in widget:
                w.layout.display = lyt_display
            return

        widget.layout.display = lyt_display
    

class GeojsonPopup():
    def __init__(self, map_, control_coordinate):
        self.map = map_
        self.control_coordinate = control_coordinate
        self.layer = None
        self.popup = None
        
        self.style = { 'color': 'gray','opacity': 1, 'dashArray': '0', 'fillOpacity': 0.1, 'weight': 1 }
        self.hover_style = { 'color': 'white', 'dashArray': '0', 'fillOpacity': 0.5 }
        
    def load(self, geojson):
        self.clear()
        args = {
            'name': geojson['name'],
            'data': { k: geojson[ k ] for k in ( 'type', 'features') },
            'style': self.style,
            'hover_style': self.hover_style
        }
        self.layer = GeoJSON( **args )
        self.layer.on_click( self.on_click_layer )

    def zoom(self, feature_id):
        features = self.layer.data['features']
        if feature_id > len( features ) - 1:
            raise Exception(f"Error: Invalid Index ({feature_id})")
        
        feat = shape( features[ feature_id ]['geometry'] )
        ( minx, miny, maxx, maxy ) = scale( feat, 2, 2 ).bounds
        
        self.map.fit_bounds( [ (miny, minx), (maxy, maxx) ] )
        
    def addMap(self):
        self.map.add( self.layer )
        
    def on_click_layer(self, **kargs):
        """
        The 'kargs' can be differents arguments (ex. ID), depend of Geojson (layer)
        """
        def widgetTable():
            id_element = 'geojson_popup'
            html = """
                <style>
                #{ELEMENT}_row {
                  color: #BB9BF6;
                  border-style:solid;
                  border-color: #B6B5B8;
                }
                </style>
            """.replace('{ELEMENT}', id_element)
            html += '<table>'
            html += UtilScenes.htmlRows( ['Field', 'Value' ],'th', id_element )
            for key, value in properties.items():
                if key == 'style':
                    continue
                html += UtilScenes.htmlRows( [ key, value ],'td', id_element )
            html += '</table>'
            
            return HTML( html )
        
        properties = kargs['properties'] # widgetTable
        if not self.popup in self.map.layers:
            self.popup = Popup(
                name=f"{self.layer.name} - Popup",
                location=( self.control_coordinate.y, self.control_coordinate.x ),
                child=widgetTable(),
            )
            self.map.add( self.popup )
        else:
            self.popup.location=( self.control_coordinate.y, self.control_coordinate.x )
            self.popup.child=widgetTable()

        self.popup.open_popup()

    def clear(self):
        for layer in ( self.layer, self.popup ):
            if layer in self.map.layers:
                self.map.remove( layer )
