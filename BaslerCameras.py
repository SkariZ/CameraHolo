# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 11:33:55 2022

@author: marti
"""
import numpy as np
from CameraControlsNew import CameraInterface
from pypylon import pylon  # For basler camera, maybe move that out of here
from time import sleep

class TimeoutException(Exception):
    print("Timeout of camera!")

class BaslerCamera(CameraInterface):

    def __init__(self):
        self.capturing = False
        self.is_grabbing = False
        self.img = pylon.PylonImage()
        self.img2 = pylon.PylonImage()
        self.cam = None
        self.cam2 = None
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
            
            if len(devices) > 1:
                self.cam2 = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[1]))
                self.cam2.Open()
                print("Camera 2 is now open")

            sleep(0.2)
            self.num_cameras = len(devices)

            return True
        
        except Exception as ex:
            self.cam = None
            print(ex)
            return False
        
    def disconnect_camera(self):
        self.stop_grabbing()
        self.cam.Close()
        self.cam = None

    def stop_grabbing(self):
        try:
            self.cam.StopGrabbing()
            self.cam2.StopGrabbing()
        except:
            pass
        self.is_grabbing = False

    def set_AOI(self, AOI):
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
            sleep(0.1)
            self.cam.Width = width
            self.cam.Height = height
            self.cam.OffsetX = offset_x
            self.cam.OffsetY = offset_y

        except Exception as ex:
            print(f"AOI not accepted, AOI: {AOI}, error {ex}")

    def set_exposure_time(self, exposure_time):
        self.stop_grabbing()
        try:
            self.cam.ExposureTime = exposure_time

        except Exception as ex:
            print(f"Exposure time not accepted by camera, {ex}")

    def get_exposure_time(self):
        return self.cam.ExposureTime()

    def get_fps(self):
        fps = round(float(self.cam.ResultingFrameRate.GetValue()), 1)
        return fps

    def get_sensor_size(self):
        width = int(self.cam.Width.GetMax())
        height = int(self.cam.Height.GetMax())
        return width, height
