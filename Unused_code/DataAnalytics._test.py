import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QLabel, QGridLayout
)
from PyQt6.QtCore import QTimer, QSize
from PyQt6.QtGui import QAction

class DataAnalytics(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Data Analytics")
        self.setGeometry(100, 100, 800, 500)

        # Add a toolbar
        self.toolbar = QToolBar("Options")
        self.addToolBar(self.toolbar)

        # Add a button for closing the window
        self.close_action = QAction("Close window", self)
        self.close_action.triggered.connect(self.close)
        self.toolbar.addAction(self.close_action)

        # Add a button for changing the data type
        self.toggle_data_action = QAction("Toggle data type", self)
        self.toggle_data_action.setCheckable(True)
        self.toggle_data_action.setChecked(True)
        self.toggle_data_action.triggered.connect(self.toggle_data_type)
        self.toolbar.addAction(self.toggle_data_action)

        # Initialize pyqtgraph PlotDataItems
        #self.plot = self.image_object.getImageItem()
        self.colormap = pg.colormap.getFromMatplotlib('viridis')

        # Initialize the data type
        self.data_type = 'image'

        # Update the data every second/2
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.update_data(c_p['image']))
        self.timer.start(500)

    def toggle_data_type(self):
        self.data_type = 'fft' if self.toggle_data_action.isChecked() else 'image'

    def close(self):
        self.timer.stop()
        self.hide()


    def update_data(self, new_data):
                
        image_object = pg.ImageView()
        widget = QWidget()
    
        # Update the FFT image plot (replace this with your FFT calculation)
        if new_data is not None:
            if self.data_type == 'image':
                label = QLabel("IMAGE")
                image_object.setImage(new_data, autoRange=False, autoLevels=False, autoHistogramRange=False, levels=(0, 255))

            elif self.data_type == 'fft':
                label = QLabel("FFT")
                fft_img = np.abs(np.fft.fftshift(np.fft.fft2(new_data)))
                image_object.setImage(fft_img)

            #Set colormap
            image_object.setColorMap(self.colormap)

            layout = QGridLayout()
            widget.setLayout(layout)
            layout.addWidget(label, 0, 0, 1, 1)
            layout.addWidget(image_object, 0, 2, 5, 1)
            self.setCentralWidget(widget)

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