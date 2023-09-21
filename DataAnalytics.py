import sys
from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit,
    QLineEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QVBoxLayout
)

from PyQt6.QtCore import QTimer

import pyqtgraph as pg
from random import randint

import numpy as np

from PyQt6.QtWidgets import (
QVBoxLayout, QWidget, QLabel, 
)

# from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QTimer


class DataAnalytics(QMainWindow):
    def __init__(self, c_p):
        super().__init__()
        self.setWindowTitle("Data Analytics")
        self.setGeometry(100, 100, 800, 800)
        self.image_case = 'image'
        self.update_rate = 1
        self.cmap = pg.colormap.get('CET-L9')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create an ImageView for the image
        self.image_widget = pg.ImageView(
            view=pg.PlotItem()
            )
        layout.addWidget(self.image_widget)

        # Update the data every second
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.update_data(c_p['image'].T))
        self.timer.start(self.update_rate*1000)

        #Add a button to set image as image
        self.button = QPushButton("Image")
        self.button.clicked.connect(self.on_click)
        layout.addWidget(self.button)

        #Add a button to set image as FFT
        self.button2 = QPushButton("FFT")
        self.button2.clicked.connect(self.on_click2)
        layout.addWidget(self.button2)

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

        #Add a button to toggle grayscale colormap
        self.button3 = QPushButton("Grayscale")
        self.button3.clicked.connect(self.on_click3)
        layout.addWidget(self.button3)

        #Make the button smaller horizontally
        self.button.setMaximumWidth(100)
        self.button2.setMaximumWidth(100)
        self.textbox.setMaximumWidth(100)
        self.button3.setMaximumWidth(100)

    def update_data(self, new_data):
        if new_data is not None:

            if self.image_case == 'image':
                self.image_widget.setImage(
                    new_data,
                    )
            elif self.image_case == 'fft':
                self.image_widget.setImage(
                    self.fft_transform(new_data),
                )
            self.image_widget.setColorMap(self.cmap)

            #TODO could add more costumization here

    def fft_transform(dself, data):
        im = np.log(np.abs(np.fft.fftshift(np.fft.fft2(data))))
        im[im == np.inf] = 0
        im[im == -np.inf] = 0
        return im

    def on_click(self):
        self.image_case = 'image'
        self.button.setStyleSheet("background-color: green")
        self.button2.setStyleSheet("background-color: gray")

    def on_click2(self):
        self.image_case = 'fft'
        self.button.setStyleSheet("background-color: gray")
        self.button2.setStyleSheet("background-color: green")

    def on_click3(self):
        if self.cmap == pg.colormap.get('CET-L9'):
            self.cmap = pg.colormap.get('CET-L1')
            self.button3.setStyleSheet("background-color: green")
        else:
            self.cmap = pg.colormap.get('CET-L9')
            self.button3.setStyleSheet("background-color: gray")
            
    def on_text_changed(self):
        update_rate = float(self.textbox.text()) if self.textbox.text() != '' else 0
        if update_rate > 0 and update_rate < 100:
            self.update_rate = update_rate
            self.timer.stop()
            self.timer.start(self.update_rate*1000)

    #Stop the timer when the window is closed
    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

