# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Planetary Computer Scene
Description          : Search scene from Planetary Computer API
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


import pystac_client
import planetary_computer

import requests
import mercantile

from .itemscene import Item


class SearchScenes():
    def __init__(self, collections_assets):
        self._catalog = catalog = pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=planetary_computer.sign_inplace,
        )
        self._collections_assets = collections_assets
        self._collections = list( self._collections_assets.keys() )
        self._scenes_valid = []
        self._scenes_error = []
        self._zoom_statuscode = 8
        self._total_search = 0

    def _valueScene(self, item):
        def urlTile():
            """
            Args:
                - item: Item collection
            Return: url (Tile XYZ)
            """
            r = requests.get( item.assets["tilejson"].href )
            r_json = r.json()
            url = r_json["tiles"][0]
            r.close()

            return url

        def urlAssets():
            def assertValues(asset):
                url = item.assets[ asset ].href
                name_tif = url.split('?')[0].split('/')[-1]
                resp = requests.get( url, stream=True )
                total_mb = int( resp.headers.get('content-length', 0) ) / 1048576 # 1024*1024
                return { 'name_tif': name_tif, 'total_mb': total_mb, 'url': url }
                
            if not item.collection_id in self._collections:
                str_collections = ','.join( self._collections )
                msg = f"Error: '{item.collection_id}' collection not implemented. Collections: {str_collections}"
                raise Exception( msg )

            v_return = {}
            for asset in self._collections_assets[ item.collection_id ]:
                v_return[ asset ] = assertValues( asset )
                
            return v_return


        def statuscode(url_tile, bbox):
            west, south, east, north = bbox
            part_lat = ( north - south ) / 3
            part_lng = ( east - west ) / 3

            west  += part_lng
            south += part_lat
            east  -= part_lng
            north -= part_lat

            tile = mercantile.tiles( west, south, east, north, zooms=[ self._zoom_statuscode ] ).__next__()
            url_zoom = url_tile.replace('{z}/{x}/{y}', f"{tile.z}/{tile.x}/{tile.y}")

            return requests.get( url_zoom ).status_code, url_zoom

        url_tile = urlTile()
        status_code, url_error = statuscode( url_tile, item.bbox )
        value = Item( item.id, url_tile, urlAssets(), item.geometry, item.datetime )
        if status_code == 200: 
            return value

        setattr( value, 'status_code', status_code )
        setattr( value, 'url_error', url_error )
        
        return value

    def process(self, date_ini, date_end, geometry, progressThread=None, nextStep=None):
        """
        functions_status = { 'scene_count', 'cancel'}
        """
        def searchScenes():
            formatDate = '%Y-%m-%d'
            strdate_ini, strdate_end = date_ini.strftime( formatDate ), date_end.strftime( formatDate )
            time_of_interest = f"{strdate_ini}/{strdate_end}"
            
            search = self._catalog.search(
                collections=self._collections,
                intersects=geometry,
                datetime=time_of_interest,
                # query={"eo:cloud_cover": {"lt": 10}},
            )

            return search.item_collection()

        def setScenes( item ):
            value = self._valueScene( item )
            l = self._scenes_valid if not hasattr( value, 'status_code' ) else self._scenes_error
            l.append( value )
        
        def process(scenes):
            for item in scenes:
                setScenes( item )
            if not nextStep is None:
                nextStep()

        def processProgress(scenes):
            def run():
                count = 0
                for item in scenes:
                    count += 1
                    progressThread.status( item.id, count )
                    if progressThread.cancel:
                        self._scenes_valid.clear()
                        self._scenes_error.clear()
                        break
                    setScenes( item )
                if not nextStep is None:
                    nextStep()
            
            progressThread.init( len( scenes ) )
            progressThread.start( run )

        self._scenes_valid.clear()
        self._scenes_error.clear()
        scenes_search = searchScenes()
        self._total_search = len( scenes_search )
        if not self._total_search:
            if not nextStep is None:
                nextStep()
            return
        
        p = process if progressThread is None else processProgress
        p( scenes_search )

    def itemScene(self, id_scene):
        search = self._catalog.search( collections=self._collections, ids=id_scene )
        item = next( iter( search.item_collection() ) )
        return self._valueScene( item ) 

    @property
    def collections(self):
        return self._collections

    @collections.setter
    def collections(self, collections):
        for c in collections:
            if not c in self._collections_assets:
                str_collections = ','.join( self._collections_assets.keys() )
                msg = f"Error: '{c}' collection not implemented. Collections: {str_collections}"
                raise Exception( msg )
        
        self._collections = collections

    @property
    def total(self):
        return self._total_search

    @property
    def valids(self):
        return self._scenes_valid

    @property
    def errors(self):
        return self._scenes_error
