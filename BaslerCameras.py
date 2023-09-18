# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 11:33:55 2022

@author: marti
"""
import numpy as np
from CameraControlsNew import CameraInterface
from pypylon import pylon  # For basler camera, maybe move that out of here
from time import sleep

#class TimeoutException(Exception):
#    print("Timeout of camera!")

class BaslerCamera(CameraInterface):

    def __init__(self):
        self.capturing = False
        self.is_grabbing = False
        self.img = pylon.PylonImage()
        self.img2 = pylon.PylonImage()
        self.cam = None
        self.cam2 = None
        self.num_cameras =  len(pylon.TlFactory.GetInstance().EnumerateDevices())
        self.cam1_max_width = 0
        self.cam1_max_height = 0
        self.cam2_max_width = 0
        self.cam2_max_height = 0

    '''
    def capture_image(self):
        
        if not self.is_grabbing:
            self.cam.StartGrabbing(pylon.GrabStrategy_OneByOne)
            self.is_grabbing = True
        try:
            
            with self.cam.RetrieveResult(3000) as result: # 3000

                self.img.AttachGrabResultBuffer(result)
                if result.GrabSucceeded():
                    # Consider if we need to put directly in c_p?
                    #image = np.uint8(self.img.GetArray()[:1024,:1024])
                    image = np.uint8(self.img.GetArray())    
                    #self.img.Release()
                    
                    return image
        except TimeoutException as TE:
            print(f"Warning, camera timed out {TE}")
    '''
    def capture_image(self):
        
        #Define the cameras to use
        if not self.is_grabbing:
            self.cam.StartGrabbing(pylon.GrabStrategy_OneByOne)

            #Second camera if it exists
            if self.num_cameras > 1:
                self.cam2.StartGrabbing(pylon.GrabStrategy_OneByOne) #basler2
            self.is_grabbing = True

        #One camera
        if self.num_cameras == 1:
            self.cam.ExecuteSoftwareTrigger()
            result = self.cam.RetrieveResult(3000)
            self.img.AttachGrabResultBuffer(result)
            if result.GrabSucceeded():
                image = np.uint8(self.img.GetArray())
                return image
            else:
                print("Camera failed to grab an image")
                return None

        #Two cameras    
        elif self.num_cameras == 2:
            self.cam.ExecuteSoftwareTrigger()
            self.cam2.ExecuteSoftwareTrigger()
            result = self.cam.RetrieveResult(3000)
            result2 = self.cam2.RetrieveResult(3000)
            self.img.AttachGrabResultBuffer(result)
            self.img2.AttachGrabResultBuffer(result2)

            if result.GrabSucceeded() and result2.GrabSucceeded():
                image1 = np.uint8(self.img.GetArray())
                image2 = np.uint8(self.img2.GetArray())

                #If they are the same size, concatenate them horisontally.
                if image1.shape == image2.shape:
                    image = np.concatenate((image1, image2), axis = 1)
                #If they are not the same size, make them the same size and concatenate them horisontally.
                else:
                    image = np.zeros((max(image1.shape[0], image2.shape[0]), image1.shape[1]+image2.shape[1]))
                    image[0:image1.shape[0], 0:image1.shape[1]] = image1
                    image[0:image2.shape[0], image1.shape[1]:image1.shape[1]+image2.shape[1]] = image2

                return image
            #exception if one of the cameras fail
            else:
                print("One of the two cameras failed to grab an image")
                return None
        #except TimeoutException as TE:
        #    print(f"Warning, camera timed out {TE}")

    def connect_camera(self):
        try:
            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()
            
            #No camera found
            if len(devices) == 0:
                self.cam = None
                raise pylon.RuntimeException("No camera present.")
    
            # Adding first camera
            if len(devices) > 0:
                self.cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
                self.cam.Open()
                print("Camera 1 is now open")
            
            if len(devices) > 1:
                self.cam2 = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[1]))
                self.cam2.Open()
                print("Camera 2 is now open")

            self.num_cameras = len(devices)
            self.cam1_max_width = self.cam.Width.GetMax()
            self.cam1_max_height = self.cam.Height.GetMax()
            if self.num_cameras > 1:
                self.cam2_max_width = self.cam2.Width.GetMax()
                self.cam2_max_height = self.cam2.Height.GetMax()    
            sleep(0.1)

            return True
        
        except Exception as ex:
            self.cam = None
            print(ex)
            return False
        
    def disconnect_camera(self):
        self.stop_grabbing()
        self.cam.Close()
        self.cam = None
        self.cam2.Close()
        self.cam2 = None

    def stop_grabbing(self):
        try:
            self.cam.StopGrabbing()
            self.cam2.StopGrabbing()
        except:
            pass
        self.is_grabbing = False
    
    def set_AOI(self, AOI):
        '''
        Function that sets the region of interest of the camera.
        AOI = [x1, x2, y1, y2]

        if two cameras are used, the AOI is set to the same area of the both cameras
        '''
        self.stop_grabbing()

        #Check if the AOI is larger than the sensor size of camera1
        #This allows for zoom in also on the second camera
        if AOI[1] > self.cam1_max_width:
            AOI[1] = AOI[1] - self.cam1_max_width
            AOI[0] = AOI[0] - self.cam1_max_width
        if AOI[3] > self.cam1_max_height:
            AOI[3] = AOI[3] - self.cam1_max_height
            AOI[2] = AOI[2] - self.cam1_max_height

        #Ensure that the AOI is a multiple of 16
        AOI[0] -= AOI[0] % 16
        AOI[1] -= AOI[1] % 16
        AOI[2] -= AOI[2] % 16
        AOI[3] -= AOI[3] % 16

        try:
            #Setting the AOI for camera1
            self.cam.Width = int(AOI[1] - AOI[0])
            self.cam.Height = int(AOI[3] - AOI[2])
            self.cam.OffsetX = AOI[0]
            self.cam.OffsetY = AOI[2]

            #Setting the AOI for camera2 if available
            if self.num_cameras == 2:
                self.cam2.Width = int(AOI[1] - AOI[0])
                self.cam2.Height = int(AOI[3] - AOI[2])
                self.cam2.OffsetX = AOI[0]
                self.cam2.OffsetY = AOI[2]

        except Exception as ex:
            print(f"AOI not accepted, AOI: {AOI}, error {ex}")


    def set_AOI2(self, AOI):
        '''
        Function for setting AOI of basler camera to c_p['AOI']
        '''
        self.stop_grabbing()
        try:
            '''
            The order in which you set the size and offset parameters matter.
            If you ever get the offset + width greater than max width the
            camera won't accept your valuse. Thereof the if-else-statements
            below. Conditions might need to be changed if the usecase of this
            funciton change.
            '''
            # TODO test with a real sample
            width = int(AOI[1] - AOI[0])
            offset_x = AOI[0]
            height = int(AOI[3] - AOI[2])
            offset_y = AOI[2]


            width -= width % 16
            height -= height % 16
            offset_x -= offset_x % 16
            offset_y -= offset_y % 16
            self.video_width = width
            self.video_height = height
            self.cam.OffsetX = 0
            self.cam.OffsetY = 0

            #Setting the AOI
            self.cam.Width = width
            self.cam.Height = height
            self.cam.OffsetX = offset_x
            self.cam.OffsetY = offset_y

            sleep(0.1)

        except Exception as ex:
            print(f"AOI not accepted, AOI: {AOI}, error {ex}")

    def set_camera_mode(self, mode):
        self.camera_mode = mode

    def set_exposure_time(self, exposure_time):
        self.stop_grabbing()
        try:
            self.cam.ExposureTime = exposure_time
            self.cam2.ExposureTime = exposure_time
        except Exception as ex:
            print(f"Exposure time not accepted by camera, {ex}")

    def get_exposure_time(self):
        return self.cam.ExposureTime()

    def get_fps(self):
        fps = round(float(self.cam.ResultingFrameRate.GetValue()), 1)
        return fps

    def get_sensor_size(self):

        if self.num_cameras > 0:
            width = int(self.cam.Width.GetMax())
            height = int(self.cam.Height.GetMax())

        if self.num_cameras > 1:
            width2 =  int(self.cam2.Width.GetMax())
            height2 = int(self.cam2.Height.GetMax())
        else:
            width2 = 0
            height2 = 0

        return width, height, width2, height2

    def set_cam_size(self, width, height):
        self.stop_grabbing()
        try:
            self.cam.Width = width
            self.cam.Height = height

            if self.num_cameras == 2:
                self.cam2.Width = width
                self.cam2.Height = height

        except Exception as ex:
            print(f"Camera size not accepted by camera, {ex}")
