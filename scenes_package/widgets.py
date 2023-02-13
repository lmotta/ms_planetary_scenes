# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Widgets
Description          : Widgets for workin with scenes
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


from threading import Thread
import json
from datetime import datetime, timedelta

from shapely.geometry import shape
from shapely.affinity import scale


from ipywidgets import (
    Button, Checkbox,
    Label, HTML, Image,
    Layout,
    HBox, VBox,
    IntProgress, IntSlider,
    Dropdown, SelectionSlider, SelectMultiple,
    Play,
    DatePicker,
    FileUpload
)
from ipyleaflet import (
    basemap_to_tiles, basemaps,
    MagnifyingGlass, TileLayer, LayerGroup, GeoJSON,
    DrawControl, WidgetControl, FullScreenControl, SearchControl, ScaleControl, LayersControl
)

from .utils import UtilScenes, GeojsonPopup
from .planetarycomputerscenes import SearchScenes


def widgetPrevfogo():
    def htmlDescription():
        id_prevfogo = 'prevfogo_element'
        html_style = f"<style>{UtilScenes.styleLinkHtml( id_prevfogo )}</style>"
        html = """
        Division of Monitorament and Combat - DMC<br>
        National Center for Wildfire Prevention and Suppression - Prevfogo<br>
        <a id="{ELEMENT}_a" href="https://www.gov.br/ibama/pt-br">Brazilian Institute for the Environment and Renewable Natural Resources - Ibama</a>
        """.replace('{ELEMENT}', id_prevfogo)
        return HTML( f"{html_style} {html}" )

    logo_prevfogo = Image(
        value=open('./resources/prev-fogo-logo.png', 'rb').read(),
        format='png',
        width=75, height=100,
    )
    return HBox( [ logo_prevfogo, htmlDescription() ] )


class ScenesValid():
    def __init__(self, map_, control_date ):
        self.control_date = control_date
        self._total = None
        
        # Widgets
        self.w_scenes_total = HTML()
        self.w_show_date = Checkbox( value=False, description='Show valid scenes table of current date' ) 
        self.observe_show_date = lambda change: UtilScenes.toggleLayoutDisplay( self.control_date.widgets['table'] , change.new )
        self.w_show_date.observe( self.observe_show_date, names='value' )

    def add(self, scenes):
        self._total = len( scenes )
        c_msg = UtilScenes.colorMessage( f"Valid: {self._total} scenes", UtilScenes.color_ok )
        self.w_scenes_total.value = c_msg
        self.control_date.add( scenes )
        UtilScenes.toggleLayoutDisplay( self.control_date.widgets['table'] , False )

    def clear(self):
        self.control_date.remove()
        self.w_scenes_total.value = ''
        self.w_show_date.value = False

    @property
    def total(self):
        return self._total
        
    @property
    def widgets(self):
        return {
            'show_date': self.w_show_date,
            'table_date': self.control_date.widgets['table'],
            'total_scenes':  self.w_scenes_total
        }


class ScenesError():
    def __init__(self, map_, control_coordinate, style_table, id_element_table):
        self.layer = GeojsonPopup( map_, control_coordinate )
        self._total = None
        self._html_table = None
        
        #.) Styles Tables Scenes
        self.id_element_table = id_element_table
        self.style_table = style_table
        
        # Widget
        self.w_show = Checkbox( value=False, description='Show error scenes' ) 
        self.w_show.observe( self.on_observe_show, names='value')
        self.w_table = HTML()

    def add(self, scenes):
        def tableHtml():
            links = lambda item: '<br>'.join( UtilScenes.linksUrlBand( item, self.id_element_table ) )
            html = f"{self.style_table}<table>"
            html += UtilScenes.htmlRows( [ f"{len( scenes )} erros" ],'th', self.id_element_table )
            html += UtilScenes.htmlRows( ['Id', 'Code', 'Urls' ],'th', self.id_element_table )
            for item in scenes:
                html_links = UtilScenes.linksUrlBand( item, self.id_element_table )
                url_error =  f"""<a id="#ELEMENT#_a" href="{item.url_error}" target="_blank">tiles</a>""".replace('#ELEMENT#', self.id_element_table )
                html_links.insert( 0, url_error )
                html += UtilScenes.htmlRows( [ item.scene, item.status_code, '<br>'.join( html_links ) ],'td', self.id_element_table )
            html += '</table>'

            return html

        self.layer.load( UtilScenes.footprint( 'Error scenes', scenes ) )
        self._total = len( scenes )
        self._html_table = tableHtml()
        
        self.w_table.value = ''

    def clear(self):
        self.layer.clear()
        self.w_table.value = ''
        self.w_show.value = False
        
    def on_observe_show(self, change):
        def add():
            self.w_table.value = self._html_table
            self.layer.addMap()
            
        func = add if change.new else self.clear
        func()
        UtilScenes.toggleLayoutDisplay( self.w_table, change.new )

    @property
    def total(self):
        return self._total

    @property
    def widgets(self):
        return { 'show': self.w_show, 'table': self.w_table }

    
class ProgressThread():
    def __init__(self):
        self._thread = None # Start
        self._cancel = False

        self.w_progress = IntProgress( min=0)
        self.w_item = Label()
        self.w_cancel = Button(
            description='Cancel',
            disabled=False,
            button_style='',
            icon='ban'
        )
        self.w_cancel.on_click( self.on_click_cancel )
        
        self.w_widget = HBox( [ self.w_progress, self.w_item , self.w_cancel ] )
    
    def on_click_cancel(self, btn):
        self._cancel = True
    
    def init(self, total):
        self._thread = None
        self._cancel = False
        self.w_progress.max = total

    def status(self, item, count):
        self.w_progress.value = count
        self.w_progress.description = f"{count} / {self.w_progress.max} :"
        self.w_item.value = item
            
    def start(self, callback):
        """
        callback: Function to run by thread
        . Ex.: 
        ..p = ProgressThread()
        ..p.init(10)
        ..start( runThread)
        .. def runThread():
        ..     for label in data:
        ..         count += 1
        ..         if p.cancel:
        ..             break
        ..         p.status( label, count )
        """
        self._thread = Thread(target=callback )  
        self._thread.start()
    
    def close(self):
        self.w_widget.close()
    
    @property
    def cancel(self):
        return self._cancel

    @property
    def widget(self):
        return self.w_widget


class UploadGeojson():
    def __init__(self, map_, control_coordinate, w_output):
        def upload():
            widget = FileUpload()
            args = {
                'description': 'Upload Geojson (WGS 84 - EPSG 4326)',
                'accept': '.geojson',
                'multiple': False
            }
            widget = FileUpload( **args )
            widget.layout = Layout(width='300px')
            return widget

        def dropdownFields():
            widget = Dropdown(
                options=[''],
                value=None,
                description='Select Field:',
                disabled=True,
            )
            widget.layout = Layout(width='300px')
            return widget

        def dropdownValues():
            widget = Dropdown(
                options=[''],
                value=None,
                description='Select Value:',
                description_tooltip='Show selected value in map',
                disabled=True,
            )
            widget.layout = Layout(width='300px')
            return widget
        
        def buttonRemove():
            widget = Button(
                description='Remove Geojson',
                disabled=True,
                icon='minus-square'
            )
            return widget
        
        def control():
            return SearchControl(
                position=position,
                layer=LayerGroup( layers=() ),
                zoom=4,
                auto_collapse=True,
                property_name=''
            )
        
        self.map = map_
        self.w_output = w_output
        
        self.w_message = HTML()
        
        self.geojson_search = GeojsonPopup( map_, control_coordinate )
        
        self.w_upload = upload()
        self.w_upload.observe( self.on_observe_upload, names='value' )
        self.load_json = False
        
        self.layer = None
        
        self.w_fields = dropdownFields()
        self.w_fields.observe( self.on_observe_fields, names='value' )

        self.w_values = dropdownValues()
        self.w_values.observe( self.on_observe_values, names='value' )
        self._values_index = {}
        
        self.escape_dropdown = True

        self.w_remove = buttonRemove()
        self.w_remove.on_click( self.on_click_remove )
        
    def _clear(self):
            self.w_upload.data.clear()
            self.w_upload.metadata.clear()
            self.w_upload._counter = 0
            self.geojson_search.clear()
            if not self.layer is None:
                self.layer.data.clear()
                self.layer = None
            self.w_remove.disabled = True
            self.w_fields.options = ()
            self.w_values.options = ()
            self._values_index.clear()
        
    @property
    def widget(self):
        return HBox( [ self.w_upload, self.w_fields, self.w_values, self.w_remove ] )

    def on_observe_upload(self, change):
        if self.load_json:
            self.load_json = False #  'on_observe_upload' is call twice
            return

        self.w_message.value = UtilScenes.colorMessage( 'Reading Geojson...', UtilScenes.color_ok )
        with self.w_output:
            display( self.w_message )

        # Layer
        self.load_json = True
        # First key = Name of file
        name = next( iter( change.new.keys() ) )
        # Key 'content' = Binary string with data
        data = json.loads( change.new[ name ]['content'] )
        self._clear()
        args = {
            'name': name,
            'data': { k: data[ k ] for k in ( 'type', 'features') },
            'style': { 'opacity': 0, 'fillOpacity': 0 },
        }
        self.layer = GeoJSON( **args )
        
        # Fields
        self.escape_dropdown = True
        items = self.layer.data['features'][0]['properties'].items()
        self.w_fields.options = [ k for k, v in items if isinstance( v, str) == True ] # Only string
        self.w_fields.value = None
        self.w_fields.disabled = False
        self.escape_dropdown = False
        
        self.w_output.clear_output()

    def on_observe_fields(self, change):
        if change.new is None:
            return
        
        if self.escape_dropdown:
            return

        self.escape_dropdown = True
        values = [ feature['properties'][ self.w_fields.value ] for feature in self.layer.data['features'] ]
        self._values_index = { values[ idx ]: idx for idx in range( len( values ) ) }
        values.sort()
        self.w_values.options = values
        self.w_values.value = None
        self.w_values.disabled = False
        self.escape_dropdown = False

    def on_observe_values(self, change):
        if change.new is None:
            return
        
        if self.escape_dropdown:
            return
        
        idx = self._values_index[ change.new ]
        feat = self.layer.data['features'][ idx ]
        # Zoom
        geom = shape( feat['geometry'] )
        ( minx, miny, maxx, maxy ) = scale( geom, 2, 2 ).bounds
        self.map.fit_bounds( [ (miny, minx), (maxy, maxx) ] )
        # Geojson Popup
        self.geojson_search.clear()
        geojson = { 'name': feat['properties'][ self.w_fields.value ], 'type': 'FeatureCollection', 'features': [ feat ] }
        self.geojson_search.load( geojson )
        self.geojson_search.addMap()
        self.w_remove.disabled = False
        self.w_values.value = None

    def on_click_remove(self, btn):
        self.geojson_search.clear()
        btn.disabled = True


class DrawControlRectangle():
    def __init__(self, map_, position):
        def createControl():
            control = DrawControl(position=position)
            control.edit, control.remove = False, False
            control.circlemarker = {}
            control.polyline = {}
            control.polygon = {}
            control.rectangle = {
                "shapeOptions": {
                    "fillColor": "#fca45d",
                    "color": "#fca45d",
                    "fillOpacity": 0.5
                }
            }
            control.on_draw( self.on_draw )
            return control
        
        self._geometry = None
        map_.add( createControl() )
        
    def on_draw(self, target, action, geo_json):
        def changeStyle():
            style =  geo_json['properties']['style']
            style['color'] = 'blue'
            style['fill'] = False
            # Update target
            target.data = [ geo_json ]

        if not action == 'created':
            return

        self._geometry = geo_json['geometry']
        changeStyle()
        
    @property
    def geometry(self):
        return self._geometry


class LabelCoordinateControl():
    def __init__(self, map_, position):
        self.label = Label()
        self.f_coord = lambda c: f"{round( self._coord[ c ] , 4 )} º"
        self._coord = { 'x': None, 'y': None }
        
        control = WidgetControl( widget=self.label, position=position)
        map_.add( control )
        map_.on_interaction( self.on_interaction )
        
    def on_interaction(self, **kwargs):
        if kwargs['type'] == 'mousemove':
            ( self._coord['y'], self._coord['x'] ) = kwargs['coordinates']
            self.label.value = f"{self.f_coord('x')}, {self.f_coord('y')}"
            
    @property
    def x(self):
        return self._coord['x']

    @property
    def y(self):
        return self._coord['y']
    

class ScenesDateControl():
    def __init__(self, map_, position, style_table, id_element_table):
        self.map = map_
        
        #.) Styles Tables Scenes
        self.id_element_table = id_element_table
        self.style_table = style_table
        
        # Populated by addControl
        self.date_items = {} # { date: items }
        
        # Populated by on_observe_selection_date
        self.layers = []
        self.w_table = HTML()
        
        # Control, Create in add
        self.w_dates = Label('')
        self.w_play = Play(
            value=0,
            min=0,
            max=0,
            step=1,
            interval=1500, # Miliseconds
            description="Press play",
            disabled=True
        )
        self.w_play.observe( self.on_observe_play, names='value')
        self.skip_play = False # Twice call
        self.w_selection = SelectionSlider(
            options=[''],
            value='',
            description='Scenes:',
            readout=False            
        )
        self.w_selection.observe( self.on_observe_selection, names='value')
        self.w_order = Label('')
        self.w_ = HBox( [ self.w_dates, self.w_play, self.w_selection, self.w_order ] )
        self.control = WidgetControl( widget=self.w_, position=position )
        self.w_selection.disabled = True
        self.map.controls = ( self.control, *self.map.controls ) # Add top control_date

    def _removeLayersSceneDate(self):
        for layer in self.layers:
            if layer in self.map.layers:
                self.map.remove( layer )
        self.layers.clear()

    def add(self, scenes):
        def toDatesItem():
            """
            Args:
                - scenes: [ Item ]
            """
            f_date = '%Y-%m-%d'
            dates = [ item.datetime.strftime( f_date ) for item in scenes ]
            dates = list( set( dates ) )

            self.date_items.clear()
            date_scenes = {}
            for item in scenes:
                date = item.datetime.strftime( f_date )
                if not date in date_scenes:
                    date_scenes[ date ] = [ item ]
                    continue
                date_scenes[ date ].append( item )

            # Sort
            keys = list( date_scenes.keys() )
            keys.sort()
            for k in keys:
                self.date_items[ k ] = date_scenes[ k ]
        
        self.w_selection.disabled = False
        self.w_play.disabled = False
        toDatesItem()
        dates = list( self.date_items.keys() )
        self.w_dates.value = f"{dates[0]}/{dates[-1]} ({len( dates )} dates)"
        self.w_selection.options = dates
        self.w_selection.value = dates[0]
        #self.on_observe( { 'new': dates[0] } )
        self.w_play.max = len( dates ) - 1
        self.w_play.value = 0

    def remove(self):
        self._removeLayersSceneDate()

        self.w_selection.value = self.w_selection.options[0] # reset bar.
        # Not clear 'self.w_selection' (option and value), if change value/options fire trigger.
        for w in ( self.w_dates, self.w_order):
            w.value = ''
        self.w_selection.disabled = True
        self.w_play.disabled = True

    def on_observe_play(self, change):
        if self.skip_play:
            self.skip_play = False
            return
            
        self.w_selection.value = self.w_selection.options[ change.new ]
        self.skip_play = True

    def on_observe_selection(self, change):
        def tableHtml():
            html = f"{self.style_table}<table>"
            html += UtilScenes.htmlRows( [ f"{len( self.date_items[ change.new ] )} scenes ({change.new})" ],'th', self.id_element_table )
            html += UtilScenes.htmlRows( ['Id', 'Urls' ],'th', self.id_element_table )
            for item in self.date_items[ change.new ]:
                links = '<br>'.join( UtilScenes.linksUrlBand( item, self.id_element_table ) )
                html +=  UtilScenes.htmlRows( [ item.scene, links ],'td', self.id_element_table )
            html += '</table>'

            return html

        if self.date_items is None:
            return

        # Clean last layers
        self._removeLayersSceneDate()

        # Control Scenes date 
        # .) Position
        idx = list( self.date_items.keys() ).index( change.new )
        self.w_order.value = f"{change.new} ({idx+1}º)"

        #.) Add layers (map) and names (tooltip)
        names = []
        for item in self.date_items[ change.new ]:
            layer = TileLayer(name=item.scene, url=item.url_tile, attribution='Microsoft Planetary Computer')
            self.layers.append( layer )
            self.map.add( layer )
            names.append( item.scene )

        msg = '\n'.join( names )
        self.w_selection.description_tooltip = f"{msg}"

        # Table valid scenes
        self.w_table.value = tableHtml()

    @property
    def widgets(self):
        return { 'table': self.w_table }


class MagnifyingGlassLayer():
    def __init__(self, map_, position='bottomleft'):
        self.map = map_

        self.layer = None
        
        self.no_source = '-- None --'
        self.sources = {
            self.no_source: None,
            'Esri': basemap_to_tiles( basemaps.Esri.WorldImagery ),
            'Google': TileLayer( url='http://mt0.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attribution='Google')
        }
        self.w_sources = Dropdown(
            options=list( self.sources.keys() ),
            value=self.no_source,
            description='Magnifying:',
            description_tooltip='Select source for Magnifying Layer',
            icon='check'
        )
        self.w_sources.observe( self.on_observe_source, names='value')
        
        self.w_zoom = IntSlider(
            value=0,
            min=0, max=6,
            step=1,
            description="Offset Zoom:",
            description_tooltip='Increase the current zoom for Magnifying',
            disabled=True
        )
        self.w_zoom.observe( self.on_observe_zoom, names='value')

        self.w_ = VBox( [ self.w_sources, self.w_zoom ] )
        self.map.add( WidgetControl( widget=self.w_, position='bottomleft' ) )
        
        self.map.on_interaction(self.on_interaction_map)
        
    def _addLayer(self, source, zoom):
        self.layer = MagnifyingGlass( layers=[ self.sources[ source ] ], zoom_offset=zoom )
        self.layer.name = source
        self.map.add( self.layer )

    def reset(self):
        self.w_sources.value = self.no_source
        self.w_zoom.value=0

    def on_interaction_map(self, **kwargs):
        def refresh(): # ISSUE
            y, x = self.map.center
            content = {
                'type': 'mouseover',
                'coordinates': [ y+0.001, x+0.001 ]
            }
            test = {
                'comm_id': 'u-u-i-d',
                'data': {
                    'method': 'custom',
                    'content': content,
                    'buffers': None
                }
            }
            self.layer.send( **test )
            print(1)
            
        if not kwargs.get('type') == 'click' or self.w_sources.value == self.no_source:
            return

        # Return Magnifying
        if self.w_sources.disabled:
            self.w_sources.disabled = False
            self.layer.zoom_offset = self.w_zoom.value
            self.map.add( self.layer )
            #refresh() # ISSUE
            return
        
        self.w_sources.disabled = True
        self.map.remove( self.layer )
        
    def on_observe_source(self, change):
        if self.layer in self.map.layers:
            self.map.remove( self.layer )
        
        if self.no_source == change.new:
            self.layer = None
            self.w_zoom.disabled = True
            return

        self._addLayer( change.new, self.w_zoom.value )
        self.w_zoom.disabled = False
                       
    def on_observe_zoom(self, change):
        if self.no_source == self.w_sources.value or self.w_sources.disabled:
            return
        
        if self.layer in self.map.layers:
            self.map.remove( self.layer )
        self._addLayer( self.w_sources.value, change.new )


class ProcessScenes():
    def __init__(self, map_, w_output ):
        self.map = map_
        self.w_output_progress = w_output
        self.w_message = HTML()
        
        collections_assets = { 'landsat-c2-l2': ['red', 'green', 'blue'], 'sentinel-2-l2a': ['visual'] }
        self.search = SearchScenes( collections_assets )

        #.) Styles Tables Scenes
        id_element_table = 'scenes'
        html = '#{ELEMENT}_row { color: #6F9BF3; border-style:solid; border-color: #B6B5B8; }'.replace('{ELEMENT}', id_element_table)
        style_table = f"<style>{html} {UtilScenes.styleLinkHtml( id_element_table )}</style>"

        # .) Controls
        self.control_date = ScenesDateControl( map_, 'topleft', style_table, id_element_table )
        self.draw_control = DrawControlRectangle( map_, 'topleft' )
        map_.add( FullScreenControl() ) # 'topleft'
        map_.add( SearchControl(
            position="topleft", zoom=10, auto_collapse=True,
            url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
        ))
        self.control_coordinate = LabelCoordinateControl( map_, 'bottomleft' )
        map_.add_control( ScaleControl(position='bottomleft') )
        self.magnifying_control = MagnifyingGlassLayer( map_, 'bottomleft')
        map_.add( LayersControl(position='topright') )
        self.upload_geojson_control = UploadGeojson( map_, self.control_coordinate, self.w_output_progress )
        
        #.) Scenes
        self.scenes_valid = ScenesValid( map_, self.control_date )
        w = self.scenes_valid.widgets
        self.w_html_valid_total = w['total_scenes']
        self.w_show_date_table = w['show_date']
        self.w_html_date_table = w['table_date']

        self.scenes_error = ScenesError( map_, self.control_coordinate, style_table, id_element_table )
        w = self.scenes_error.widgets
        self.w_show_error_table = w['show']
        self.w_html_error_table = w['table']
        
        # Hide
        widgets = (
            self.w_html_valid_total,
            self.w_show_error_table, self.w_show_date_table,
            self.w_html_date_table, self.w_html_error_table
        )
        UtilScenes.toggleLayoutDisplay( widgets, False )
        
        # Search
        self.w_date_end = DatePicker(description='End date')
        self.w_date_end.value = datetime.today().date()

        self.w_date_ini = DatePicker(description='Initial date')
        self.w_date_ini.value = self.w_date_end.value - timedelta(days=30)

        self.w_collections = SelectMultiple(
            options=self.search.collections,
            description='Collections',
            disabled=False
        )
        self.w_collections.value = [ self.search.collections[0] ]
        
        self.w_button = Button(
            description='Search scenes',
            disabled=False,
            button_style='',
            icon='satellite-dish'
        )
        self.w_button.on_click( self._on_click )
        
        self.w_html_result_search = HTML()

    def _on_click(self, btn):
        def process():
            def finished():
                def resultSearch():
                    formatDate = '%Y-%m-%d'
                    strdate_ini = self.w_date_ini.value.strftime( formatDate )
                    strdate_end = self.w_date_end.value.strftime( formatDate )
                    msg = messageOk( f"Found {self.search.total} scenes({strdate_ini}/{strdate_end})" )
                    self.w_html_result_search.value = msg
                    UtilScenes.toggleLayoutDisplay( self.w_html_result_search, True )
                
                self.w_message.value = ''
                progress.close()
                btn.disabled = False
                
                if progress.cancel:
                    self.w_message.value = messageError('Canceled by user')
                    return
                
                if  self.search.total == 0:
                    self.w_message.value = messageError('Not found scenes')
                    return
                
                resultSearch()
                
                total_valids = len( self.search.valids )
                total_errors = len( self.search.errors )
                
                if total_valids > 0:
                    self.w_html_valid_total.value = messageOk(f"{total_valids} valid scenes")
                    self.scenes_valid.add( self.search.valids )
                    widgets = (
                        self.w_html_valid_total, self.w_show_date_table
                    )
                    UtilScenes.toggleLayoutDisplay( widgets, True )
                    
                if total_errors > 0:
                    self.w_message.value = messageError(f"{total_errors} errors")
                    self.scenes_error.add( self.search.errors )
                    UtilScenes.toggleLayoutDisplay(  self.w_show_error_table, True )
                    
            self.w_message.value = messageOk('Processing...')
            progress = ProgressThread()
            with self.w_output_progress:
                display( progress.widget )
            
            self.search.process(self.w_date_ini.value, self.w_date_end.value, self.draw_control.geometry, progress, finished )
            
        btn.disabled = True
        
        messageOk = lambda msg: UtilScenes.colorMessage( msg, UtilScenes.color_ok )
        messageError = lambda msg: UtilScenes.colorMessage( msg, UtilScenes.color_error )

        self.magnifying_control.reset()

        # Hide
        widgets = (
            self.w_html_result_search, self.w_html_valid_total,
            self.w_show_date_table, self.w_show_error_table,
            self.w_html_date_table, self.w_html_error_table
        )
        UtilScenes.toggleLayoutDisplay( widgets, False )
        self.w_message.value = ''
        self.scenes_valid.clear()
        self.scenes_error.clear()
        
        if self.draw_control.geometry is None:
            self.w_message.value = messageError('Error: Missing Rectangle on Map')
            btn.disabled = False
            return
        
        if self.w_date_ini.value > self.w_date_end.value:
            formatDate = '%Y-%m-%d'
            strdate_ini = self.w_date_ini.value.strftime( formatDate )
            strdate_end = self.w_date_end.value.strftime( formatDate )
            msg = f"Initial Date ({messageError( strdate_ini )}) > End date ({messageError( strdate_end )}</b>)"
            self.w_message.value = messageError( msg )
            btn.disabled = False
            return
            
        self.search.collections = self.w_collections.value
        process()

    @property
    def widgets(self):
        return {
            'search': HBox( [ VBox( [ self.w_date_ini, self.w_date_end ] ), self.w_collections, self.w_button ] ),
            'result_search': self.w_html_result_search,
            'valid_total': self.w_html_valid_total,
            'show_date_table': self.w_show_date_table, 'show_error_table': self.w_show_error_table,
            'date_table': self.w_html_date_table, 'error_table': self.w_html_error_table,
            'message': self.w_message,
            'upload': self.upload_geojson_control.widget
        }
