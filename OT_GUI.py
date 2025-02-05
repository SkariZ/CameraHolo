# -*- coding: utf-8 -*-
"""
Graphical User Interface for camera. This is the main file that should be run.

//Fredrik
"""
import sys, os
import cv2 # Certain versions of this won't work

from PyQt6.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QLineEdit,
    QToolBar, QFileDialog, QInputDialog
)

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QAction, QDoubleValidator, QPen, QIntValidator

from random import randint
import numpy as np
from time import sleep
from functools import partial
import gc


import BaslerCameras
from CameraControlsNew import CameraThread, VideoWriterThread, CameraClicks
from ControlParameters import default_c_p, get_data_dicitonary_new
from SaveDataWidget import SaveDataWindow
from DataAnalytics import DataAnalytics
from FieldRecon import FieldAnalytics
from FieldRecon_Z import FieldAnalyticsZ

class Worker(QThread):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    Used to update the screen continoulsy with the images of the camera
    '''
    changePixmap = pyqtSignal(QImage)

    def __init__(self, c_p, data, test_mode=True, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.c_p = c_p
        self.data_channels = data
        self.args = args
        self.kwargs = kwargs
        self.test_mode = test_mode
        self.buffer = self.c_p['buffer']

    def preprocess_image(self):
        # Check if offset and gain should be applied.
        if self.c_p['image_offset'] != 0:
            self.image += int(self.c_p['image_offset'])
            
        if self.c_p['image_gain'] != 1:
            # TODO unacceptably slow
            self.image = (self.image*self.c_p['image_gain'])
        
        #Convert to uint8
        self.image = np.uint8(self.image)

    def subtraction_mode_image(self):
        "Subtracts the current image from the previous image in the buffer"
        if self.c_p['SubtractionMode']:
            try:
                self.image = self.buffer[-1].astype(np.float32) - np.mean(np.array(self.buffer).astype(np.float32)[:-1], axis=0)
            except:
                pass

    def high_speed_mode_image(self):
        "Downsamples the image to increase the frame rate"
        if self.c_p['HighSpeedMode_method']=='bin':
            self.image = self.image.reshape((self.image.shape[0]//2, 2, self.image.shape[1]//2, 2)).mean(3).mean(1)
            #self.image = self.image[::int(self.c_p['HighSpeedMode_ds']), ::int(self.c_p['HighSpeedMode_ds'])].astype(np.float32)
        else:
            self.image = cv2.resize(self.image, (0,0), fx=int(self.c_p['HighSpeedMode_ds']), fy=int(self.c_p['HighSpeedMode_ds']), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    
    def overlay_image_mode(self):
        'Overlays images on top of each other'
        
        #check if num_cameras is 2
        if self.c_p['num_cameras'] != 2:
            return
        else:
            #Split images into two
            image1 = self.image[:, :self.image.shape[1]//2]
            image2 = self.image[:, self.image.shape[1]//2:]
            #Ensure the same size for both images, else pad
            if image1.shape[1] != image2.shape[1]:
                pad = np.zeros((image1.shape[0], image2.shape[1]-image1.shape[1]))
                image1 = np.hstack((image1, pad))
            #Overlay images
            self.image = cv2.addWeighted(image1, 0.35, image2, 0.65, 0)

    def run(self):
        # Initialize pens to draw on the images
        self.blue_pen = QPen()
        self.blue_pen.setColor(QColor('blue'))
        self.blue_pen.setWidth(2)
        self.red_pen = QPen()
        self.red_pen.setColor(QColor('red'))
        self.red_pen.setWidth(2)

        while True:
            if self.c_p['image'] is not None:
                self.image = np.array(self.c_p['image'])
            else:
                print("Frame does not exist, missing!")
    
            W, H = self.c_p['frame_size']
            self.c_p['image_scale'] = max(self.image.shape[1]/W, self.image.shape[0]/H)

            #Sanity check
            self.preprocess_image()
            
            #High speed mode
            if self.c_p['HighSpeedMode']:
                self.high_speed_mode_image()

            #Subtraction mode
            if self.c_p['SubtractionMode']:
                self.subtraction_mode_image()

            #Convert self.image into 0-255 range by normalizing
            if self.c_p['HighSpeedMode'] or self.c_p['SubtractionMode']:
                self.image = np.uint8((self.image - np.min(self.image))/(np.max(self.image) - np.min(self.image))*255)

            #Overlay image mode
            if self.c_p['Overlay_image_mode']:
                self.overlay_image_mode()

            # It is quite sensitive to the format here, won't accept any mismatch
            if len(np.shape(self.image)) < 3:
                QT_Image = QImage(self.image, self.image.shape[1],
                                       self.image.shape[0],
                                       QImage.Format.Format_Grayscale8)
                
                QT_Image = QT_Image.convertToFormat(QImage.Format.Format_RGB888)
            else:                
                QT_Image = QImage(self.image, self.image.shape[1],
                                       self.image.shape[0],
                                       QImage.Format.Format_RGB888)
                   
            picture = QT_Image.scaled(
                W, H,
                Qt.AspectRatioMode.KeepAspectRatio,
            )

            # Give other things time to work, roughly 40-50 fps default.
            sleep(0.2)

            # Paint extra items on the screen
            self.qp = QPainter(picture)

            # Draw zoom in rectangle
            self.c_p['click_tools'][self.c_p['mouse_params'][5]].draw(self.qp)
            self.qp.setPen(self.blue_pen)

            self.qp.end()
            self.changePixmap.emit(picture)


class MainWindow(QMainWindow):
    """
    Main window of the program. It contains the menu bar and the main widget.
    """

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Main window")
        self.c_p = default_c_p()
        self.data_channels = get_data_dicitonary_new()
        self.video_idx = 0
        self.widgets = []

        # Start camera threads
        self.CameraThread = None
        try:
            camera = None
            camera = BaslerCameras.BaslerCamera()
            
            if camera is not None:
                self.CameraThread = CameraThread(self.c_p, camera)
                self.CameraThread.start()

            #Count the number of cameras connected so we know if we can use dual camera mode
            c = 0
            if camera.cam is not None: c += 1
            if camera.cam2 is not None: c += 1
            self.c_p['num_cameras'] = c

            if c == 1: self.c_p['camera_mode'] = 'cam1'
            elif c == 2: self.c_p['camera_mode'] = 'both'

            print(f"Number of cameras connected: {c}")

        except Exception as E:
            print(f"Camera error!\n{E}")
       
        self.VideoWriterThread = VideoWriterThread(2, 'video thread', self.c_p)
        self.VideoWriterThread.start()
        
        # Set up camera window. This is just how it looks once starting.
        H = int(1024/4)
        W = int(1024)

        self.c_p['frame_size'] = int(self.c_p['camera_width']/2), int(self.c_p['camera_height']/2)
        self.label = QLabel("Hello")
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setCentralWidget(self.label)
        self.label.setMinimumSize(W, H)
        self.painter = QPainter(self.label.pixmap())

        # Start camera thread
        th = Worker(c_p=self.c_p, data=self.data_channels)
        th.changePixmap.connect(self.setImage)
        th.start()

        # Create toolbar
        create_camera_toolbar_external(self)
        self.addToolBarBreak() 
        self.create_mouse_toolbar()

        # Create menus and drop down options
        self.menu = self.menuBar()
        self.create_filemenu()
        self.drop_down_window_menu()
        self.create_cameramenu()
        self.show()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    def start_threads(self):
        pass
    
    def create_mouse_toolbar(self):
        # Here is where all the tools in the mouse toolbar are added
        self.c_p['click_tools'].append(CameraClicks(self.c_p))
        self.c_p['mouse_params'][5] = 0

        self.mouse_toolbar = QToolBar("Mouse tools")
        self.addToolBar(self.mouse_toolbar)
        self.mouse_actions = []
        
        for idx, tool in enumerate(self.c_p['click_tools']):
            self.mouse_actions.append(QAction(tool.getToolName(), self))
            self.mouse_actions[-1].setToolTip(tool.getToolTip())
            command = partial(self.set_mouse_tool, idx)
            self.mouse_actions[-1].triggered.connect(command)
            self.mouse_actions[-1].setCheckable(True)
            self.mouse_toolbar.addAction(self.mouse_actions[-1])
        self.mouse_actions[self.c_p['mouse_params'][5]].setChecked(True)
        
    def set_mouse_tool(self, tool_no=0):
        if tool_no > len(self.c_p['click_tools']):
            return
        self.c_p['mouse_params'][5] = tool_no
        for tool in self.mouse_actions:
            tool.setChecked(False)
        self.mouse_actions[tool_no].setChecked(True)
        print("Tool set to ", tool_no)

    def set_gain(self, gain):
        try:
            g = min(float(gain), 255)
            self.c_p['image_gain'] = g
            print(f"Gain is now {gain}")
        except ValueError:
            # Harmless, someone deleted all the numbers in the line-edit
            pass
        
    def create_cameramenu(self):
        cemera_menu = self.menu.addMenu("Camera")
        cemera_menu.addSeparator()

        #Create a submenu for setting camera mode.
        mode_submenu = cemera_menu.addMenu("Camera mode")
        modes = ['cam1', 'cam2', 'both']
        for mode in modes:
            mode_command = partial(self.set_camera_mode, mode)
            mode_action = QAction(mode, self)
            mode_action.setStatusTip(f"Set camera mode to {mode}")
            mode_action.triggered.connect(mode_command)
            mode_submenu.addAction(mode_action)

        #Add a submenu for setting burst mode
        burst_submenu = cemera_menu.addMenu("Burst mode")
        burst_modes = ['Off', 'On']
        for mode in burst_modes:
            mode_command = partial(self.set_burst_mode, mode)
            mode_action = QAction(mode, self)
            mode_action.setStatusTip(f"Set burst mode to {mode}")
            mode_action.triggered.connect(mode_command)
            burst_submenu.addAction(mode_action)

        # Create a submenu for setting exact region of interest
        AOI_submenu = cemera_menu.addMenu("Set AOI")
        AOI_command = partial(self.set_AOI)
        AOI_action = QAction("Set AOI", self)
        AOI_action.setStatusTip("Set exact region of interest")
        AOI_action.triggered.connect(AOI_command)
        AOI_submenu.addAction(AOI_action)

        # Create a submenu for showing actual frame size
        frame_size_submenu = cemera_menu.addMenu("Print actual frame size")
        frame_size_command = partial(self.print_actual_frame_size)
        frame_size_action = QAction("Print actual frame size", self)
        frame_size_action.setStatusTip("Print actual frame size")
        frame_size_action.triggered.connect(frame_size_command)
        frame_size_submenu.addAction(frame_size_action)

    def create_filemenu(self):

        file_menu = self.menu.addMenu("File")
        file_menu.addSeparator()

        # Create submenu for setting recording(video) format
        format_submenu = file_menu.addMenu("Recording format")
        video_formats = ['avi','mp4','npy']

        for f in video_formats :
            format_command = partial(self.set_video_format, f)
            format_action = QAction(f, self)
            format_action.setStatusTip(f"Set recording format to {f}")
            format_action.triggered.connect(format_command)
            format_submenu.addAction(format_action)

        # Submenu for setting the image format
        image_format_submenu = file_menu.addMenu("Image format")
        image_formats = ['png','jpg','npy']
        for f in image_formats:
            format_command = partial(self.set_image_format, f)
            format_action = QAction(f, self)
            format_action.setStatusTip(f"Set recording format to {f}")
            format_action.triggered.connect(format_command)
            image_format_submenu.addAction(format_action)

        # Add command to set the savepath of the experiments.
        set_save_action = QAction("Set save path", self)
        set_save_action.setStatusTip("Set save path")
        set_save_action.triggered.connect(self.set_save_path)
        file_menu.addAction(set_save_action)

        set_filename_action = QAction("Set filename", self)
        set_filename_action.setStatusTip("Set filename for saved, data, video and image files")
        set_filename_action.triggered.connect(self.set_default_filename)
        file_menu.addAction(set_filename_action)

        # Add command to save the data
        save_data_action = QAction("Save data", self)
        save_data_action.setStatusTip("Save data to an npy file")
        save_data_action.triggered.connect(self.dump_data)
        file_menu.addAction(save_data_action)

        #Add command to split written video into two videos(only works for avi and if recording is off and camera mode is both))
        split_video_action = QAction("Split video", self)
        split_video_action.setStatusTip("Split video into two videos")
        split_video_action.triggered.connect(self.split_video)
        file_menu.addAction(split_video_action) 

    def dump_data(self):
        text, ok = QInputDialog.getText(self, 'Filename dialog', 'Set name for data to be saved:')
        if not ok:
            print("No valid name entered")
            return
        path = self.c_p['recording_path'] + '/' + text
        """
        save_data = {}
        for channel_name in self.data_channels:
            channel = self.data_channels[channel_name]
            save_data[channel.name] = channel.get_data(channel.max_retrivable)
        """
        print(f"Saving data to {path}")
        np.save(path,  self.data_channels, allow_pickle=True)

    def set_default_filename(self):
        text, ok = QInputDialog.getText(self, 'Filename dialog', 'Enter name of your files:')
        if ok:
            self.video_idx = 0
            self.c_p['image_idx'] = 0
            self.c_p['filename'] = text
            self.c_p['video_name'] = text + '_video' + str(self.video_idx)
            print(f"Filename is now {text}")

    def split_video(self):
        'Function that splits the video into two parts'
        #Check so that recording is off
        if self.c_p['recording']:
            print("Can't split video while recording!")
            return
        
        #Check so that camera mode is both
        if self.c_p['camera_mode'] != 'both':
            print("Can't split video unless camera mode is both!")
            return
        
        #Check so that video format is avi or mp4
        if self.c_p['video_format'] not in ['avi']:
            print("Can't split video unless video format is avi!")
            return
        
        #Check so that there is a video to split in the first place
        if os.path.isfile(self.c_p['recording_path'] + '/' + self.c_p['video_name'] + '.' + self.c_p['video_format']):
            print("Can't split video if there is no video to split!")
            return
        
        #Check so that we have two cameras connected
        if self.c_p['num_cameras'] != 2:
            print("Can't split video if there is not two cameras connected!")
            return

        #Read video
        #Find the name of the video in recording path and video name
        all_videos = os.listdir(self.c_p['recording_path'])
        video_name = [video for video in all_videos if self.c_p['video_name'] in video and self.c_p['video_format'] in video]
        if len(video_name) != 1:
            print("Couldn't find video!")
            return
        
        #Original video
        video_name = self.c_p['recording_path'] + '/' + video_name[0]

        #New videos
        video_name1 = self.c_p['recording_path'] + '/' + self.c_p['video_name'] + '_1' + '.' + self.c_p['video_format']
        video_name2 = self.c_p['recording_path'] + '/' + self.c_p['video_name'] + '_2' + '.' + self.c_p['video_format']

        #Video info
        cap = cv2.VideoCapture(video_name)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count/fps
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Video has {frame_count} frames and a duration of {duration} seconds and a fps of {fps} and a width of {width} and a height of {height}")

        #New sizes
        width_new = int(width/2)
        width1 = width_new
        width2 = width - width_new

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')

        #Create new videos
        writer1 = cv2.VideoWriter(video_name1, fourcc, min(500, self.c_p['fps']),
                                (width1, height), isColor=False)
        writer2 = cv2.VideoWriter(video_name2, fourcc, min(500, self.c_p['fps']),
                                (width2, height), isColor=False)
        
        for i in range(frame_count):
            ret, frame = cap.read()
            frame = frame[..., 0]
            frame1 = frame[:, :width_new]
            frame2 = frame[:, width_new:]
            writer1.write(frame1)
            writer2.write(frame2)

        #Release everything    
        cap.release()
        writer1.release()
        writer2.release()
        print("Video has been split!")

        #Delete old video
        os.remove(video_name)

        #Garbage collector
        gc.collect()

        #Delete all variables 
        del (cap, writer1, writer2, frame, frame1, 
             frame2, fourcc, fps, frame_count, 
             duration, height, width, 
             width_new, width1, width2, video_name, 
             video_name1, video_name2)
        
    def drop_down_window_menu(self):
        # Create windows drop down menu
        window_menu = self.menu.addMenu("Windows")
        window_menu.addSeparator()

        # Data analytics window
        self.open_data_window = QAction("Data analytics", self)
        self.open_data_window.setToolTip("Open window for data analytics.")
        self.open_data_window.triggered.connect(self.show_data_analytics_window)
        self.open_data_window.setCheckable(False)
        window_menu.addAction(self.open_data_window)

        #Field reconstruction window 
        self.open_field_recon_window = QAction("Field reconstruction", self)
        self.open_field_recon_window.setToolTip("Open window for field reconstruction.")
        self.open_field_recon_window.triggered.connect(self.show_field_analytics_window)
        self.open_field_recon_window.setCheckable(False)
        window_menu.addAction(self.open_field_recon_window)

        #Z propagation window
        self.open_field_recon_window_z = QAction("Field propagation", self)
        self.open_field_recon_window_z.setToolTip("Open window for propagating field")
        self.open_field_recon_window_z.triggered.connect(self.show_field_analytics_window_z)
        self.open_field_recon_window_z.setCheckable(False)
        window_menu.addAction(self.open_field_recon_window_z)

    def set_video_format(self, video_format):
        self.c_p['video_format'] = video_format

    def set_image_format(self, image_format):
        self.c_p['image_format'] = image_format
        
    def set_video_name(self, string):
        self.c_p['video_name'] = string

    def set_exposure_time(self):
        # Updates the exposure time of the camera to what is inside the textbox
        self.c_p['exposure_time'] = float(self.exposure_time_LineEdit.text())
        self.c_p['new_settings_camera'] = [True, 'exposure_time']

    def set_buffer_size_text(self):
        # Updates the buffer size of the camera to what is inside the textbox
        self.c_p['buffer_size'] = int(self.buffer_size_LineEdit.text())
        self.c_p['new_settings_camera'] = [True, 'buffer_size']

    def set_camera_mode(self, mode):
        # Updates the camera mode to what is inside the textbox
        self.c_p['camera_mode'] = mode
        self.c_p['new_settings_camera'] = [True, 'camera_mode']

    def set_AOI(self):
        #Prompt a box to enter the AOI
        AOI, ok = QInputDialog.getText(self, 'AOI dialog', 'Enter AOI as x, x2, y, y2:')
        if ok:
            AOI = AOI.split(',')
            AOI = [int(x) for x in AOI]
            self.c_p['AOI'] = AOI
            self.c_p['new_settings_camera'] = [True, 'AOI']

    def set_burst_mode(self, mode):
        # Updates the burst mode to what is inside the textbox
        self.c_p['burst_mode'] = mode
        self.c_p['new_settings_camera'] = [True, 'burst_mode']

    def set_fps_text(self):
        # Updates the fps of the camera to what is inside the textbox
        self.c_p['fps'] = int(self.fps_LineEdit.text())
        self.c_p['new_settings_camera'] = [True, 'fps']

    def set_save_path(self):
        fname = QFileDialog.getExistingDirectory(self, "Save path")
        if len(fname) > 3:
            # If len is less than 3 then the action was cancelled and we should not update
            self.c_p['recording_path'] = fname

    def print_actual_frame_size(self):
        print(f"Actual frame size is {self.c_p['image'].shape[0]}, {self.c_p['image'].shape[1]}")

    def ZoomOut(self):
        self.c_p['AOI'] = [0, self.c_p['camera_width'], 0, self.c_p['camera_height']]
        self.c_p['new_settings_camera'] = [True, 'AOI']

    def SubtractionMode(self):
        self.c_p['SubtractionMode'] = not self.c_p['SubtractionMode']

    def HighSpeedMode(self):
        self.c_p['HighSpeedMode'] = not self.c_p['HighSpeedMode']

    def OverlayImageMode(self):
        self.c_p['Overlay_image_mode'] = not self.c_p['Overlay_image_mode']

    def get_fps(self):
        self.frame_rate_label.setText("Frame rate: %d\n" % self.c_p['fps'])

    def ToggleRecording(self):
        # Turns on/off recording
        # Need to add somehting to indicate the number of frames left to save when recording.
        self.c_p['recording'] = not self.c_p['recording']
        if self.c_p['recording']:
            self.c_p['video_name'] = self.c_p['filename'] + '_video' + str(self.video_idx)
            self.video_idx += 1
            self.record_action.setToolTip("Turn OFF recording.")
        else:
            self.record_action.setToolTip("Turn ON recording.")

    def snapshot(self):
        # Captures a snapshot of what the camera is viewing and saves that
        idx = str(self.c_p['image_idx'])
        filename = self.c_p['recording_path'] + '/'+self.c_p['filename']+'image_' + idx +'.'+ self.c_p['image_format']
        if self.c_p['image_format'] == 'npy':
            np.save(filename[:-4], self.c_p['image'])
        else:
            cv2.imwrite(filename, cv2.cvtColor(self.c_p['image'],
                                           cv2.COLOR_RGB2BGR))
        self.c_p['image_idx'] += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        H = event.size().height()
        W = event.size().width()
        self.c_p['frame_size'] = W, H

    def mouseMoveEvent(self, e):
        self.c_p['mouse_params'][3] = e.pos().x()-self.label.pos().x()
        self.c_p['mouse_params'][4] = e.pos().y()-self.label.pos().y()
        self.c_p['click_tools'][self.c_p['mouse_params'][5]].mouseMove()

    def mousePressEvent(self, e):
        self.c_p['mouse_params'][1] = e.pos().x()-self.label.pos().x()
        self.c_p['mouse_params'][2] = e.pos().y()-self.label.pos().y()

        if e.button() == Qt.MouseButton.LeftButton:
            self.c_p['mouse_params'][0] = 1
        if e.button() == Qt.MouseButton.RightButton:
            self.c_p['mouse_params'][0] = 2
        if e.button() == Qt.MouseButton.MiddleButton:
            self.c_p['mouse_params'][0] = 3
        self.c_p['click_tools'][self.c_p['mouse_params'][5]].mousePress()

    def mouseReleaseEvent(self, e):
        self.c_p['mouse_params'][3] = e.pos().x()-self.label.pos().x()
        self.c_p['mouse_params'][4] = e.pos().y()-self.label.pos().y()
        self.c_p['click_tools'][self.c_p['mouse_params'][5]].mouseRelease()
        self.c_p['mouse_params'][0] = 0

    def mouseDoubleClickEvent(self, e):
        # Double click to move center?
        x = e.pos().x()-self.label.pos().x()
        y = e.pos().y()-self.label.pos().y()
        print(x*self.c_p['image_scale'] ,y*self.c_p['image_scale'] )
        self.c_p['click_tools'][self.c_p['mouse_params'][5]].mouseDoubleClick()

    def show_data_analytics_window(self):
        self.data_analytics_window = DataAnalytics(self.c_p)
        self.data_analytics_window.show()
        self.widgets.append(self.data_analytics_window)

    def show_field_analytics_window(self):
        self.field_analytics_window = FieldAnalytics(self.c_p)
        self.field_analytics_window.show()
        self.widgets.append(self.field_analytics_window)

    def show_field_analytics_window_z(self):
        self.field_analytics_window_z = FieldAnalyticsZ(self.c_p)
        self.field_analytics_window_z.show()
        self.widgets.append(self.field_analytics_window_z)

    def DataWindow(self):
        self.data_window = SaveDataWindow(self.c_p, self.data_channels)
        self.data_window.show()
        self.widgets.append(self.data_window)

    def close_all_widgets(self):
        #Close all widgets
        for widget in self.widgets:
            widget.close()
        self.widgets = []

    def flush_memory(self):
        "Flushes the memory(closes open widgets and clears data)."

        #Close all widgets
        for widget in self.widgets:
            widget.close()

            #Stop timers if they exist
            try: widget.timer.stop() 
            except: pass

            #Hide widgets if they exist
            try: widget.hide()
            except: pass

            #Clear widgets if they exist
            try: widget.clear()
            except: pass

        #Clear widgets
        self.widgets = []

        #Garbage Collector
        gc.collect()
 
    def __del__(self):
        self.c_p['program_running'] = False
        # TODO organize this better
        if self.CameraThread is not None:
            self.CameraThread.join()
        self.VideoWriterThread.join()

def create_camera_toolbar_external(main_window):
    # TODO do not have this as an external function, urk
    main_window.camera_toolbar = QToolBar("Camera tools")
    main_window.addToolBar(main_window.camera_toolbar)

    main_window.camera_toolbar_sec = QToolBar("Secondary tools")
    main_window.addToolBar(main_window.camera_toolbar_sec)

    # main_window.add_camera_actions(main_window.camera_toolbar)
    main_window.zoom_action = QAction("Zoom out", main_window)
    main_window.zoom_action.setToolTip("Resets the field of view of the camera.")
    main_window.zoom_action.triggered.connect(main_window.ZoomOut)
    main_window.zoom_action.setCheckable(False)

    main_window.subtraction_action = QAction("Subtraction mode", main_window)
    main_window.subtraction_action.setToolTip("Switches to subtraction mode.Only visually, does not affect the data.")
    main_window.subtraction_action.triggered.connect(main_window.SubtractionMode)
    main_window.subtraction_action.setCheckable(True)

    main_window.highspeed_action = QAction("Downsampling mode", main_window)
    main_window.highspeed_action.setToolTip("Switches to high speed mode. Only visually, does not affect the data.")
    main_window.highspeed_action.triggered.connect(main_window.HighSpeedMode)
    main_window.highspeed_action.setCheckable(True)

    main_window.overlay_image_action = QAction("Overlay mode", main_window)
    main_window.overlay_image_action.setToolTip("Switches to overlaying mode. Only visually, does not affect the data.")
    main_window.overlay_image_action.triggered.connect(main_window.OverlayImageMode)
    main_window.overlay_image_action.setCheckable(True)

    main_window.flush_action = QAction("Flush memory", main_window)
    main_window.flush_action.setToolTip("Flushes the memory(closes open widgets and clears data).")
    main_window.flush_action.triggered.connect(main_window.flush_memory)
    main_window.flush_action.setCheckable(True)

    main_window.record_action = QAction("Record video", main_window)
    main_window.record_action.setToolTip("Turn ON recording.")
    main_window.record_action.setShortcut('Ctrl+R')
    main_window.record_action.triggered.connect(main_window.ToggleRecording)
    main_window.record_action.setCheckable(True)

    #Window for taking snapshot
    main_window.snapshot_action = QAction("Snapshot", main_window)
    main_window.snapshot_action.setToolTip("Take snapshot of camera view.")
    main_window.snapshot_action.setShortcut('Shift+S')
    main_window.snapshot_action.triggered.connect(main_window.snapshot)
    main_window.snapshot_action.setCheckable(False)

    #Window for setting exposure time
    main_window.set_exp_tim = QAction("Set exposure time", main_window)
    main_window.set_exp_tim.setToolTip("Sets exposure time to the value in the textboox")
    main_window.set_exp_tim.triggered.connect(main_window.set_exposure_time)

    #Window for setting buffer size
    main_window.set_buffer_size = QAction("Set buffer size", main_window)
    main_window.set_buffer_size.setToolTip("Sets buffer size to use when in subtraction mode")
    main_window.set_buffer_size.triggered.connect(main_window.set_buffer_size_text)

    #Window for setting fps
    main_window.set_fps = QAction("Set fps", main_window)
    main_window.set_fps.setToolTip("Sets fps to the value in the textboox")
    main_window.set_fps.triggered.connect(main_window.set_fps_text)

    #Window for getting fps
    main_window.get_frame_rate = QAction("FPS", main_window)
    main_window.get_frame_rate.setToolTip("Show actual FPS.")
    main_window.get_frame_rate.triggered.connect(main_window.get_fps)
    main_window.get_frame_rate.setCheckable(False)

    #Add actions to first toolbar
    main_window.camera_toolbar.addAction(main_window.zoom_action)
    main_window.camera_toolbar.addAction(main_window.record_action)
    main_window.camera_toolbar.addAction(main_window.snapshot_action)
    main_window.camera_toolbar.addAction(main_window.subtraction_action)
    main_window.camera_toolbar.addAction(main_window.highspeed_action)
    main_window.camera_toolbar.addAction(main_window.overlay_image_action)
    main_window.camera_toolbar.addAction(main_window.flush_action)

    #Add actions to second toolbar
    main_window.camera_toolbar_sec.addAction(main_window.get_frame_rate)

    #Add textboxes to toolbar - These are not actions but settable.

    #First toolbar
    main_window.exposure_time_LineEdit = QLineEdit()
    main_window.exposure_time_LineEdit.setFixedWidth(60)
    main_window.exposure_time_LineEdit.setText(str(main_window.c_p['exposure_time']))
    main_window.exposure_time_LineEdit.setValidator(QDoubleValidator(0.99,99.99, 2))
    main_window.camera_toolbar.addAction(main_window.set_exp_tim)
    main_window.camera_toolbar.addWidget(main_window.exposure_time_LineEdit)
    
    main_window.buffer_size_LineEdit = QLineEdit()
    main_window.buffer_size_LineEdit.setFixedWidth(60)
    main_window.buffer_size_LineEdit.setValidator(QIntValidator(1,100))
    main_window.buffer_size_LineEdit.setText(str(main_window.c_p['buffer_size']))
    main_window.camera_toolbar.addAction(main_window.set_buffer_size)
    main_window.camera_toolbar.addWidget(main_window.buffer_size_LineEdit)

    main_window.fps_LineEdit = QLineEdit()
    main_window.fps_LineEdit.setFixedWidth(60)
    main_window.fps_LineEdit.setValidator(QIntValidator(1,10000))
    main_window.fps_LineEdit.setText(str(main_window.c_p['fps']))
    main_window.camera_toolbar.addAction(main_window.set_fps)
    main_window.camera_toolbar.addWidget(main_window.fps_LineEdit)

    #Secondary toolbar
    main_window.frame_rate_label = QLabel()
    main_window.frame_rate_label.setText("Frame rate: %d\n" % main_window.c_p['fps'])
    main_window.camera_toolbar_sec.addWidget(main_window.frame_rate_label)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
    w.c_p['program_running'] = False
