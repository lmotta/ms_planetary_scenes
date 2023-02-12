# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Progress Thread
Description          : Progress widget with cancel button
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

from ipywidgets import (
    Button, Label,
    IntProgress,
    HBox
)


class ProgressThread():
    def __init__(self):
        self._thread = None # Start
        self._cancel = False

        self.w_progress = IntProgress( min=0 )
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
