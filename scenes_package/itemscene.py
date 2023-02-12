# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Item Scene
Description          : Define the item os scene
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


class Item():
    def __init__(self, scene, url_tile, url_assets, geometry, datetime):
        self._scene = scene
        self._url_tile = url_tile
        self._url_assets = url_assets # asset: { name_tif, total_mb, url }
        self._geometry = geometry
        self._datetime = datetime

    @property
    def scene(self):
        return self._scene

    @property
    def url_tile(self):
        return self._url_tile

    @property
    def url_assets(self):
        return self._url_assets

    @property
    def geometry(self):
        return self._geometry

    @property
    def datetime(self):
        return self._datetime

