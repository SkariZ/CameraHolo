import sys
from PyQt6.QtWidgets import (
    QMainWindow, QCheckBox, QComboBox, QListWidget, QLineEdit,
    QLineEdit, QSpinBox, QDoubleSpinBox, QSlider, QToolBar,
    QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
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

class HistogramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
        self.update_histogram()

    def update_data(self, new_data):
        self.data = new_data
        self.update_histogram()

    def update_histogram(self):
        self.ax.clear()
        if self.data is not None:
            histdata = self.data.flatten()#np.random.choice(self.data.flatten(), 50000) # For faster plotting
            self.ax.hist(histdata, bins=80, color='darkblue', alpha=0.7)
        self.ax.set_xlabel('Value')
        self.ax.set_ylabel('Frequency')
        self.fig.tight_layout()
        self.canvas.draw()

class ImageWidgetFFT(QWidget):
    def __init__(self):
        super().__init__()
        self.image = None
        
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.update_image()

    def update_data(self, new_data):
        self.image = new_data
        self.update_image()

    def update_image(self):
        self.ax.clear()
        if self.image is not None:
            fft_img = np.abs(np.fft.fft2(self.image))
            self.ax.imshow(np.log10(fft_img, out=np.zeros_like(fft_img), where=(fft_img!=0)), cmap='gray')
        #self.ax.axis('off')
        self.ax.set_xlabel('FFT Image')
        self.fig.tight_layout()
        self.canvas.draw()

class ImageWidgetPhase(QWidget):
    def __init__(self):
        super().__init__()
        self.image = None
        
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.update_image()

    def update_data(self, new_data):
        self.image = new_data
        self.update_image()

    def update_image(self):
        self.ax.clear()
        if self.image is not None:
            angle_img = np.angle(self.image)
            self.ax.imshow(angle_img, cmap='gray')
        #self.ax.axis('off')
        self.ax.set_xlabel('Phase Image')
        self.fig.tight_layout()
        self.canvas.draw()    

class DataAnalytics(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Data Analytics")
        self.setGeometry(100, 100, 800, 500)

        self.histogram_widget = HistogramWidget()
        self.image_widget_fft = ImageWidgetFFT()
        self.image_widget_phase = ImageWidgetPhase()

        #Define Side-by-side layout
        layout = QHBoxLayout()
        layout.addWidget(self.histogram_widget)
        layout.addWidget(self.image_widget_fft)
        layout.addWidget(self.image_widget_phase)

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

        #Add a button to toggle the histogram
        self.toggle_hist_action = QAction("Toggle Histogram", self)
        self.toggle_hist_action.setCheckable(True)
        self.toggle_hist_action.setChecked(True)
        self.toggle_hist_action.triggered.connect(self.toggle_histogram)
        self.toolbar.addAction(self.toggle_hist_action)

        #Add a button to toggle the image FFT
        self.toggle_image_action = QAction("Toggle Image FFT", self)
        self.toggle_image_action.setCheckable(True)
        self.toggle_image_action.setChecked(True)
        self.toggle_image_action.triggered.connect(self.toggle_image_fft)
        self.toolbar.addAction(self.toggle_image_action)

        #Add a button to toggle the image Phase
        self.toggle_image_action = QAction("Toggle Image Phase", self)
        self.toggle_image_action.setCheckable(True)
        self.toggle_image_action.setChecked(True)
        self.toggle_image_action.triggered.connect(self.toggle_image_phase)
        self.toolbar.addAction(self.toggle_image_action)
        
        #Add a button for closing the window
        self.close_action = QAction("Close window", self)
        self.close_action.triggered.connect(self.close)
        self.toolbar.addAction(self.close_action)

    def toggle_histogram(self):
        if self.toggle_hist_action.isChecked():
            self.histogram_widget.show()
        else:
            self.histogram_widget.hide()

    def toggle_image_fft(self):
        if self.toggle_image_action.isChecked():
            self.image_widget_fft.show()
        else:
            self.image_widget_fft.hide()

    def toggle_image_phase(self):
        if self.toggle_image_action.isChecked():
            self.image_widget_phase.show()
        else:
            self.image_widget_phase.hide()

    def close(self):
        self.timer.stop()
        self.hide()

    def update_data(self, new_data):
        self.histogram_widget.update_data(new_data)
        self.image_widget_fft.update_data(new_data)
        self.image_widget_phase.update_data(new_data)



    





"""

class HistogramW(QWidget):
    def __init__(self, c_p):
        super().__init__()
        
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.data = c_p['image'].flatten()  # Example data
        
        self.update_histogram()

    def update_histogram(self):
        self.ax.clear()
        self.ax.hist(self.data, bins=50, color='darkblue', alpha=0.7)
        #self.ax.vlines(self.data.mean(), 0, 1000, color='k', linestyle='--', alpha=0.5, label='Mean', linewidth=3)
        self.ax.set_title('Histogram')
        self.canvas.draw()


class DataAnalytics(QMainWindow):
    
    def __init__(self, c_p):
        super().__init__()
        
        self.c_p = c_p
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.addLegend()
        self.sub_widgets = []
        # Set up plot data

        self.plot_running = True
        self.graphWidget.setBackground('k')
        self.setWindowTitle("Data plotter")

        # Set up plot and a button for toggle the histogram from widget HistogramW
        self.hist_widget = HistogramW(c_p)
        self.hist_widget.update_histogram()
        self.hist_widget.show()
        self.hist_widget.setWindowTitle("Histogram")
        self.hist_widget.setGeometry(100, 100, 800, 500)
        self.hist_widget.show()

        self.toolbar = QToolBar("Options")


    #Function for updating the plot data
    def update_plot_data(self):
        pass

"""