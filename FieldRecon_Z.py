import sys
from PyQt6.QtWidgets import (
    QMainWindow, QCheckBox, QComboBox, QListWidget, QLineEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider, QToolBar,
    QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QInputDialog,
)

from PyQt6.QtCore import QTimer, Qt


from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from random import randint

import numpy as np
from functools import partial

from PyQt6.QtWidgets import (
 QCheckBox, QVBoxLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem,
)

# from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from Utils import phase_utils as P
from Utils import Utils_z as UZ

from mpl_toolkits.axes_grid1 import make_axes_locatable

def imgtofield(img, 
               G, 
               polynomial, 
               kx_add_ky,
               if_lowpass_b = False, 
               cropping=50,
               mask_f = [], # sinc, jinc etc.
               z_prop = 0,
               masks = [],
               add_phase_corrections = 0,
               first_phase_background = []
               ):
    
    """ 
    Function for constructing optical field.
   
    """
    #Scale image by its mean
    img = np.array(img, dtype = np.float32) 
    img = img - np.mean(img) #img = img - np.mean(img)
    
    #Compute the 2-dimensional discrete Fourier Transform with offset image.
    fftImage = np.fft.fft2(img * np.exp(1j*(kx_add_ky)))

    #shifted fourier image centered on peak values in x and y. 
    fftImage = np.fft.fftshift(fftImage)
    
    #Sets values outside the defined circle to zero. Ie. take out the information for this peak.
    fftImage2 = fftImage * masks[0] 

    #If we have a weighted function. E.g sinc or jinc.
    if len(mask_f)>0: fftImage2 = fftImage2 * mask_f
    
    #Shift the zero-frequency component to the center of the spectrum.
    E_field = np.fft.fftshift(fftImage2)

    #Inverse 2-dimensional discrete Fourier Transform
    E_field = np.fft.ifft2(E_field) 

    #Removes edges in x and y. Some edge effects
    if cropping>0:
        E_field_cropped = E_field[cropping:-cropping, cropping:-cropping]
    else:
        E_field_cropped = E_field
    
    #If we use the same first phase background correction on all the data.
    if len(first_phase_background)>0:
        E_field_cropped = E_field_cropped * np.exp( -1j * first_phase_background)
    
    #Lowpass filtered phase
    if if_lowpass_b:
        phase_img = P.phase_frequencefilter(fftImage2, mask = masks[1] , is_field = False, crop = cropping) 
    else:
        phase_img  = np.angle(E_field_cropped) #Returns the angle of the complex argument (phase)
    
    # Get the phase background from phase image.
    phase_background = P.correct_phase_4order(phase_img, G, polynomial)
    E_field_corr = E_field_cropped * np.exp( -1j * phase_background)

    #Do additional background fit. Always lowpass
    if add_phase_corrections>0 and if_lowpass_b:
        for _ in range(add_phase_corrections):
            phase_img = P.phase_frequencefilter(E_field_corr, mask = masks[2], is_field = True) 
            phase_background = P.correct_phase_4order(phase_img, G, polynomial)
            E_field_corr =  E_field_corr * np.exp( -1j * phase_background)
    
    #Lowpass filtered phase
    if if_lowpass_b:
        phase_img2 = P.phase_frequencefilter(E_field_corr, mask = masks[3], is_field = True)  
    else:
        phase_img2 = np.angle(E_field_corr)
    
    #Correct E_field again
    E_field_corr2 = E_field_corr * np.exp(- 1j * np.median(phase_img2 + np.pi - 1))
    
    #Focus the field
    if np.abs(z_prop) > 0:  
        E_field_corr2 = UZ.refocus_field_z(E_field_corr2, z_prop, padding = 256)
        
    return E_field_corr2, phase_background# E_field_corr2

class ReconstructField(QWidget):
    def __init__(self):
        super().__init__()
        
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)

        self.cax= make_axes_locatable(self.ax).append_axes('right', size='5%', pad=0.05)
        self.cax2= make_axes_locatable(self.ax2).append_axes('right', size='5%', pad=0.05)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
    def update_image(self, data, z, tz, padding = 128):
        self.ax.clear()
        self.ax2.clear()    

        if data is not None:
            #Propagate the field
            data = np.fft.ifft2(tz*data)

            if padding > 0:
                data = data[padding:-padding, padding:-padding]

            #-----#Phase#-----#
            imt = self.ax.imshow(data.real)
            self.ax.set_xlabel(f'Real part ({z:.2f}) um')
            self.fig.colorbar(imt, cax=self.cax)

            #-----#Background#-----#
            imt2 = self.ax2.imshow(data.imag)
            self.ax2.set_xlabel(f'Imag part ({z:.2f}) um')
            self.fig.colorbar(imt2, cax=self.cax2)

            #-----#Update the canvas#-----#
            self.fig.tight_layout()
            self.canvas.draw()

def get_field(image):
        _, _, _, _, _, G, polynomial, _, _, __, kx_add_ky, _, masks, _, _  = P.pre_calculations(
        image, 
        filter_radius = [], 
        cropping = 0, 
        mask_radie = [], 
        case = 'ellipse', 
        first_phase_background = 0,
        mask_out = True)

        #Get the field
        E_field, _ = imgtofield(
                image, 
                G, 
                polynomial, 
                kx_add_ky,
                if_lowpass_b = False,
                cropping = 0,  
                mask_f = [],
                z_prop = 0,
                masks = masks,
                add_phase_corrections= 0,
                first_phase_background = []
                )
        return E_field

class FieldAnalyticsZ(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Field Analytics")
        self.setGeometry(100, 100, 800, 500)

        self.Recon_Widget = ReconstructField()
        
        print('Calculating field...')
        self.field = np.fft.fft2(get_field(c_p['image']))
        print('Field calculated')

        self.z = 0
        self.wavelength = 0.532
        self.min_z = -10
        self.max_z = 10
        self.interval_z = 1
        self.zvals = np.arange(self.min_z, self.max_z + self.interval_z, self.interval_z) #OBS do not change this.
        self.TZ = None
        self.padding = 128

        if self.padding > 0 and self.TZ is None:    
            self.field = np.pad(self.field, ((self.padding, self.padding), (self.padding, self.padding)), mode = 'reflect')
        if self.TZ is None:
            self.TZ = UZ.get_Tz(self.wavelength, self.zvals, np.shape(self.field), padding = 0)

        #Define Side-by-side layout
        layout = QHBoxLayout()
        layout.addWidget(self.Recon_Widget)

        #Add the layout to the container
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        #Add a toolbar
        self.toolbar = QToolBar("Options")
        self.addToolBar(self.toolbar)
        
        #Add toolbar for z, place below toolbar
        self.toolbar_z = QToolBar("Z options")
        self.addToolBar(self.toolbar_z)

        #Add a scroll bar for z
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setMinimum(self.min_z)
        self.z_slider.setMaximum(self.max_z)
        self.z_slider.setValue(0.0)
        self.z_slider.setTickInterval(self.interval_z)
        self.z_slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.z_slider.valueChanged.connect(self.set_z)
        self.toolbar_z.addWidget(self.z_slider)

        #Add a button for setting the wavelength
        self.set_wavelength_action = QAction("Set wavelength", self)
        self.set_wavelength_action.triggered.connect(self.set_wavelength)
        self.toolbar.addAction(self.set_wavelength_action)

        #Add a button for updating the field
        self.update_field_action = QAction("Update field", self)
        self.update_field_action.triggered.connect(self.update_field)
        self.toolbar.addAction(self.update_field_action)

        #Add a button to toggle the image
        self.toggle_image_action = QAction("Toggle Image", self)
        self.toggle_image_action.setCheckable(True)
        self.toggle_image_action.setChecked(True)
        self.toggle_image_action.triggered.connect(self.toggle_image)
        self.toolbar.addAction(self.toggle_image_action)

    def update_field(self):
        self.Recon_Widget.update_image(self.field, self.z, self.TZ[np.argwhere(self.zvals==self.z)[0][0]], padding = self.padding)
    
    def toggle_image(self):
        if self.toggle_image_action.isChecked():
            self.Recon_Widget.show()
        else:
            self.Recon_Widget.hide()

    def set_z(self):
        self.z = self.z_slider.value()
        self.update_field()

    def set_wavelength(self):
        wavelength, ok = QInputDialog.getDouble(self, 'Set wavelength', 'Enter wavelength um:', decimals = 3)

        if ok:
            self.wavelength = wavelength
            self.TZ = UZ.get_Tz(wavelength, self.zvals, np.shape(self.field), self.padding)        
    
            


    



