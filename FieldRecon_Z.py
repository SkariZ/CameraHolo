import sys
from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit, QToolBar,
    QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout, QSlider, QInputDialog
)

from PyQt6.QtCore import QTimer, Qt

import pyqtgraph as pg
from random import randint

import numpy as np, gc

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QAction


from Utils import phase_utils as P
from Utils import Utils_z as UZ

class FieldAnalyticsZ(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Field Analytics")
        self.setGeometry(100, 100, 800, 800)
        print('Calculating field...')
        self.c_p = c_p
        self.image_size = c_p['image'].shape
        self.get_field(self.c_p['image'][:self.image_size[0], :self.image_size[1]])
        self.field = np.fft.fft2(self.field)
        print('Field calculated')

        self.z = 0
        self.wavelength = 0.532
        self.min_z = -10
        self.max_z = 10
        self.interval_z = 1
        self.zvals = np.arange(self.min_z, self.max_z + self.interval_z, self.interval_z) #OBS do not change this.
        self.TZ = None
        self.padding = 128
        self.image_case = 'real'

        if self.padding > 0 and self.TZ is None:    
            self.field = np.pad(self.field, ((self.padding, self.padding), (self.padding, self.padding)), mode = 'reflect')
        if self.TZ is None:
            self.TZ = UZ.get_Tz(self.wavelength, self.zvals, np.shape(self.field), padding = 0)

        self.cmap = pg.colormap.get('CET-L9')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create an ImageView for the image 1
        self.image_widget = pg.ImageView(
            view=pg.PlotItem()
            )
        layout.addWidget(self.image_widget)

        #Add a toolbar
        self.toolbar = QToolBar("Options")
        self.addToolBar(self.toolbar)
        
        #Add a scroll bar for z
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setMinimum(self.min_z)
        self.z_slider.setMaximum(self.max_z)
        self.z_slider.setValue(0.0)
        self.z_slider.setTickInterval(self.interval_z)
        self.z_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.z_slider.setSingleStep(self.interval_z)
        self.z_slider.valueChanged.connect(self.set_z)
        layout.addWidget(self.z_slider)

        #Add a button for setting the wavelength
        self.set_wavelength_action = QAction("Set wavelength", self)
        self.set_wavelength_action.triggered.connect(self.set_wavelength)
        self.toolbar.addAction(self.set_wavelength_action)

        #Add a box to set image-size (row col) to toolbar
        self.image_size_label = QLabel(self)
        self.image_size_label.setText("Image size (row, col) ")
        self.toolbar.addWidget(self.image_size_label)
        self.image_size_box = QLineEdit(self)
        self.image_size_box.move(20, 20)
        self.image_size_box.resize(280,40)
        self.image_size_box.setText(str(self.image_size))
        self.image_size_box.textChanged.connect(self.on_image_size_changed)
        self.toolbar.addWidget(self.image_size_box)
                
        #Button to recalulate the field
        self.update_field_action = QAction("Update field", self)
        self.update_field_action.triggered.connect(self.update_field)
        self.toolbar.addAction(self.update_field_action)

        #Add a button to toggle grayscale colormap
        self.button2 = QPushButton("Grayscale")
        self.button2.clicked.connect(self.on_click_cmap)
        layout.addWidget(self.button2)

        #Add 4 buttons to toggle image case
        self.button3 = QPushButton("Real")
        self.button3.clicked.connect(self.on_click_image_case)
        layout.addWidget(self.button3)
        self.button4 = QPushButton("Imaginary")
        self.button4.clicked.connect(self.on_click_image_case)
        layout.addWidget(self.button4)
        self.button5 = QPushButton("Amplitude")
        self.button5.clicked.connect(self.on_click_image_case)
        layout.addWidget(self.button5)
        self.button6 = QPushButton("Phase")
        self.button6.clicked.connect(self.on_click_image_case)
        layout.addWidget(self.button6)

        #Add a box to the toolbar that shows the current z
        self.z_label = QLabel(self)
        self.z_label.setText("z = " + str(self.z))
        self.toolbar.addWidget(self.z_label)
        #make sure the label is updated when z is changed
        self.z_slider.valueChanged.connect(self.update_z_label)


        #Make the button smaller horizontally
        self.button2.setMaximumWidth(100)
        self.button3.setMaximumWidth(100)
        self.button4.setMaximumWidth(100)
        self.button5.setMaximumWidth(100)
        self.button6.setMaximumWidth(100)
        self.image_size_box.setMaximumWidth(200)
        self.z_label.setMaximumWidth(100)
        
    def update_field(self):
        self.get_field(self.c_p['image'][:self.image_size[0], :self.image_size[1]])
        self.field = np.fft.fft2(self.field)
        self.TZ = UZ.get_Tz(self.wavelength, self.zvals, np.shape(self.field), padding = 0)

    def set_wavelength(self):
        wavelength, ok = QInputDialog.getDouble(self, 'Set wavelength', 'Enter wavelength um:', decimals = 3)

        if ok:
            self.wavelength = wavelength
            self.TZ = UZ.get_Tz(wavelength, self.zvals, np.shape(self.field), self.padding)   

    def set_z(self):
        self.z = self.z_slider.value()
        self.update_data()

    def update_data(self):

        if self.field is not None:
            curr_field = np.fft.ifft2(
                self.field * self.TZ[np.argwhere(self.zvals==self.z)[0][0]]
                ).T
            if self.padding > 0:
                curr_field = curr_field[self.padding:-self.padding, self.padding:-self.padding]

            if self.image_case == 'Real':
                self.image_widget.setImage(
                    np.real(curr_field),
                    )
            elif self.image_case == 'Imaginary':
                self.image_widget.setImage(
                    np.imag(curr_field),
                    )
            elif self.image_case == 'Amplitude':
                self.image_widget.setImage(
                    np.abs(curr_field),
                    )
            elif self.image_case == 'Phase':
                self.image_widget.setImage(
                    np.angle(curr_field),
                    )
            #Set the colormap
            self.image_widget.setColorMap(self.cmap)

    def imgtofield_simple(
                self,
                img, 
                G, 
                polynomial, 
                kx_add_ky,
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
            
        return E_field_corr, phase_background
    
    def get_field(self, image):
         
        _, _, _, _, _, G, polynomial, _, _, _, kx_add_ky, _, masks, _, _  = P.pre_calculations(
        image, 
        filter_radius = [], 
        cropping = 0, 
        mask_radie = [], 
        case = 'ellipse', 
        first_phase_background = 0,
        mask_out = True)

        self.field, _ = self.imgtofield_simple(
                image, 
                G, 
                polynomial, 
                kx_add_ky,
                masks = masks,
                )
        
    def on_click_cmap(self):
        if self.cmap == pg.colormap.get('CET-L9'):
            self.cmap = pg.colormap.get('CET-L1')
            self.button2.setStyleSheet("background-color: green")
        else:
            self.cmap = pg.colormap.get('CET-L9')
            self.button2.setStyleSheet("background-color: gray") 

    def on_click_image_case(self):
        self.image_case = self.sender().text()
        self.button3.setStyleSheet("background-color: gray")
        self.button4.setStyleSheet("background-color: gray")
        self.button5.setStyleSheet("background-color: gray")
        self.button6.setStyleSheet("background-color: gray")
        self.sender().setStyleSheet("background-color: green")


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
        except:
            pass
    
    def update_z_label(self):
        self.z_label.setText("z = " + str(self.z))

    #Stop the timer when the window is closed
    def closeEvent(self, event):
        gc.collect()
        event.accept()
