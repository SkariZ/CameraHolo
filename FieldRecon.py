import sys
from PyQt6.QtWidgets import (
    QMainWindow, QCheckBox, QComboBox, QListWidget, QLineEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider, QToolBar,
    QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QInputDialog
)

from PyQt6.QtCore import QTimer


from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from random import randint

import numpy as np
from functools import partial

from PyQt6.QtWidgets import (
 QCheckBox, QVBoxLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem
)

# from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer

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
        self.image = None
        self.precalculated = False

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)

        self.cax= make_axes_locatable(self.ax).append_axes('right', size='5%', pad=0.05)
        self.cax2= make_axes_locatable(self.ax2).append_axes('right', size='5%', pad=0.05)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.precalculate()
        self.update_image()
        
    def precalculate(self):

        if self.image is not None and self.precalculated == False:
            X, Y, X_c, Y_c, position_matrix, G, polynomial, KX, KY, KX2_add_KY2, kx_add_ky, dist_peak, masks, phase_background, rad  = P.pre_calculations(
            self.image, 
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
            #self.phase_background = phase_background
            #self.rad = rad

            #Set precalculated to true
            self.precalculated = True

    def update_data(self, new_data):
        self.image = new_data
        self.update_image()

    def update_image(self):
        self.ax.clear()
        self.ax2.clear()

        #Pre-calculate the data if it is not done already
        self.precalculate()

        if self.image is not None:
            
            #Reconstruct the field
            self.image, self.bg = imgtofield(
                self.image, 
                self.G, 
                self.polynomial, 
                self.kx_add_ky,
                if_lowpass_b = False,
                cropping = 0,  
                mask_f = [],
                z_prop = 0,
                masks = self.masks,
                add_phase_corrections= 0,
                first_phase_background = []
                )
            
            imt = self.ax.imshow(np.angle(self.image))
            self.ax.set_xlabel('Phase')
            self.fig.colorbar(imt, cax=self.cax)

            #-----#

            imt2 = self.ax2.imshow(self.bg)
            self.ax2.set_xlabel('Background')
            self.fig.colorbar(imt2, cax=self.cax2)

            self.fig.tight_layout()
            self.canvas.draw()



class FieldAnalytics(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Data Analytics")
        self.setGeometry(100, 100, 800, 500)

        self.Recon_Widget = ReconstructField()
        
        #Define Side-by-side layout
        layout = QHBoxLayout()
        layout.addWidget(self.Recon_Widget)

        #Add the layout to the container
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        #Update the data every second
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.update_data(c_p['image']))
        self.timer.start(1000)

        #Add a toolbar
        self.toolbar = QToolBar("Options")
        self.addToolBar(self.toolbar)


        #Add a button to toggle the image FFT
        self.toggle_image_action = QAction("Toggle Image", self)
        self.toggle_image_action.setCheckable(True)
        self.toggle_image_action.setChecked(True)
        self.toggle_image_action.triggered.connect(self.toggle_image_fft)
        self.toolbar.addAction(self.toggle_image_action)

        #Add a button for closing the window
        self.close_action = QAction("Close window", self)
        self.close_action.triggered.connect(self.close)
        self.toolbar.addAction(self.close_action)

        #Add a button for setting z value
        #self.set_z_action = QAction("Set z value", self)
        #self.set_z_action.triggered.connect(self.set_z)
        #self.toolbar.addAction(self.set_z_action)

    def toggle_image_fft(self):
        if self.toggle_image_action.isChecked():
            self.Recon_Widget.show()
        else:
            self.Recon_Widget.hide()

    def close(self):
        self.timer.stop()
        self.hide()

    def update_data(self, new_data):
        self.Recon_Widget.update_data(new_data)


    #def set_z(self):
    #    z, okPressed = QInputDialog.getDouble(self, "Set z value","z value:", 0, -1000, 1000, 3)
    #    if okPressed:
    #        self.z_prop = z
        #TODO update the image with the new z value   
            


    



