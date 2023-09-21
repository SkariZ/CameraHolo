import sys
from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit, QToolBar,
    QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout
)

from PyQt6.QtCore import QTimer

import pyqtgraph as pg
from random import randint

import numpy as np, gc

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel

# from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QTimer

from Utils import phase_utils as P
from Utils import Utils_z as UZ

class FieldAnalytics(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Field Analytics")
        self.setGeometry(100, 100, 800, 800)
        self.update_rate = 3
        self.z_prop = 0
        self.precalculated = False
        self.image_size = c_p['image'].shape
        self.cmap = pg.colormap.get('CET-L9')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create an ImageView for the image 1
        self.image_widget = pg.ImageView(
            view=pg.PlotItem()
            )
        # Create an ImageView for the image 2
        self.image_widget2 = pg.ImageView(
            view=pg.PlotItem()
            )
        layout.addWidget(self.image_widget)
        layout.addWidget(self.image_widget2)

        # Update the data every second
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.update_data(c_p['image'][:self.image_size[0], :self.image_size[1]].T))
        self.timer.start(self.update_rate*1000)

        #Add a toolbar
        self.toolbar = QToolBar("Options")
        self.addToolBar(self.toolbar)

        #Add a pre-calculate button to toolbar
        self.button = QPushButton('Precalculate', self)
        self.button.setStyleSheet("background-color: gray")
        self.button.clicked.connect(self.on_click)
        self.toolbar.addWidget(self.button)

        #Add a boc to set image-size (row col) to toolbar
        self.image_size_label = QLabel(self)
        self.image_size_label.setText("Image size (row, col) ")
        self.toolbar.addWidget(self.image_size_label)
        self.image_size_box = QLineEdit(self)
        self.image_size_box.move(20, 20)
        self.image_size_box.resize(280,40)
        self.image_size_box.setText(str(self.image_size))
        self.image_size_box.textChanged.connect(self.on_image_size_changed)
        self.toolbar.addWidget(self.image_size_box)
        #Add name next to the text box

        #Add a text box to set the update rate
        self.textbox = QLineEdit(self)
        self.textbox.move(20, 20)
        self.textbox.resize(280,40)
        self.textbox.setText(str(self.update_rate))
        self.textbox.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.textbox)
        #Add a label next to the text box
        self.label = QLabel(self)
        self.label.setText("Update rate (s)")
        layout.addWidget(self.label)

        #Add a text box to set the propagation distance
        self.textbox2 = QLineEdit(self)
        self.textbox2.move(20, 20)
        self.textbox2.resize(280,40)
        self.textbox2.setText(str(0))
        self.textbox2.textChanged.connect(self.on_text_changed2)
        layout.addWidget(self.textbox2)
        #Add a label next to the text box
        self.label2 = QLabel(self)
        self.label2.setText("Propagation distance (um)")
        layout.addWidget(self.label2)

        #Add a button to toggle grayscale colormap
        self.button2 = QPushButton("Grayscale")
        self.button2.clicked.connect(self.on_click2)
        layout.addWidget(self.button2)

        #Make the button smaller horizontally
        self.textbox.setMaximumWidth(100)
        self.textbox2.setMaximumWidth(100)
        self.image_size_box.setMaximumWidth(100)
        self.button.setMaximumWidth(100)
        self.button2.setMaximumWidth(100)
        

    def update_data(self, new_data):
        if new_data is not None:
    
            #Pre-calculate the data if it is not done already
            if self.precalculated == False:
                self.predalculations(new_data)
                self.button.setStyleSheet("background-color: gray")

            new_data, background = self.imgtofield_simple(
                new_data,
                self.G,
                self.polynomial,
                self.kx_add_ky,
                z_prop = self.z_prop,
                masks = self.masks,
            )

            #Draw the images
            self.image_widget.setImage(
                np.angle(new_data),
                )
            self.image_widget2.setImage(
                background,
                )
            #Set the colormap
            self.image_widget.setColorMap(self.cmap)
            self.image_widget2.setColorMap(self.cmap)

    def predalculations(self, image):
        'Pre-calculations for the field reconstruction.'

        X, Y, X_c, Y_c, position_matrix, G, polynomial, KX, KY, KX2_add_KY2, kx_add_ky, dist_peak, masks, phase_background, rad  = P.pre_calculations(
        image, 
        filter_radius = [], 
        cropping = 0, 
        mask_radie = [], 
        case = 'ellipse', 
        first_phase_background = 0,
        mask_out = True)

        self.X = X
        self.Y = Y
        self.X_c = X_c
        self.Y_c = Y_c
        self.position_matrix = position_matrix
        self.G = G
        self.polynomial = polynomial
        self.KX = KX
        self.KY = KY
        self.KX2_add_KY2 = KX2_add_KY2
        self.kx_add_ky = kx_add_ky
        self.dist_peak = dist_peak
        self.masks = masks

        #Set precalculated to true
        self.precalculated = True

    def imgtofield_simple(
                self,
                img, 
                G, 
                polynomial, 
                kx_add_ky,
                z_prop = 0,
                masks = [],
                ):
        
        #Scale image by its mean
        img = np.array(img, dtype = np.float32) 
        
        #Compute the 2-dimensional discrete Fourier Transform with offset image.
        fftImage = np.fft.fft2(img * np.exp(1j*(kx_add_ky)))

        #shifted fourier image centered on peak values in x and y. 
        fftImage = np.fft.fftshift(fftImage)
        
        #Shift the zero-frequency component to the center of the spectrum.
        E_field = np.fft.ifft2(
            np.fft.fftshift(fftImage * masks[0])
        )
        phase_img  = np.angle(E_field)
        
        # Get the phase background from phase image.
        phase_background = P.correct_phase_4order(phase_img, G, polynomial)
        E_field_corr = E_field * np.exp( -1j * phase_background)
        
        #Focus the field
        if np.abs(z_prop) > 0:  
            E_field_corr = UZ.refocus_field_z(E_field_corr, z_prop, padding = 256)
            
        return E_field_corr, phase_background

    def on_click(self):
        self.precalculated = False
        self.button.setStyleSheet("background-color: green")

    def on_click2(self):
        if self.cmap == pg.colormap.get('CET-L9'):
            self.cmap = pg.colormap.get('CET-L1')
            self.button2.setStyleSheet("background-color: green")
        else:
            self.cmap = pg.colormap.get('CET-L9')
            self.button2.setStyleSheet("background-color: gray")

    def on_text_changed(self):
        update_rate = float(self.textbox.text()) if self.textbox.text() != '' else 0
        if update_rate > 0 and update_rate < 100:
            self.update_rate = update_rate
            self.timer.stop()
            self.timer.start(self.update_rate*1000)
    
    def on_text_changed2(self):
        #Read value from text box. Allow positive and negative
        z_prop = self.textbox2.text()

        #Check if z_prop contains a number
        try:
            z_prop = float(z_prop.strip())
        except:
            z_prop = 0

        if z_prop > -100 and z_prop < 100:
            self.z_prop = z_prop
            

    def on_image_size_changed(self):
        #Read value from text box. Allow positive and negative
        try:
            image_size = self.image_size_box.text()
            image_size = image_size.replace('(', '')
            image_size = image_size.replace(')', '')
            image_size = image_size.split(',') 
            image_size = [int(i) for i in image_size]

            if len(image_size) == 2 and image_size[0] > 10 and image_size[1] > 10:
                self.image_size = image_size
                self.precalculated = False
                self.button.setStyleSheet("background-color: green")
        except:
            pass

    #Stop the timer when the window is closed
    def closeEvent(self, event):
        self.timer.stop()
        gc.collect()
        event.accept()




