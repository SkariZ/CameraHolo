# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 11:33:55 2022
##########options to change to basler camera 2
@author: marti
"""
import numpy as np
from CameraControlsNew import CameraInterface
from pypylon import pylon  # For basler camera, maybe move that out of here
from time import sleep, time
import os
from PIL import ImageOps, Image #Basler?

class TimeoutException(Exception):
    print("Timeout of camera!")

class BaslerCamera(CameraInterface):

    def __init__(self):
        self.capturing = False
        self.img = pylon.PylonImage()
        self.img2 = pylon.PylonImage()

        self.is_grabbing = False
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
        
        if not self.is_grabbing:
            self.cam.StartGrabbing(pylon.GrabStrategy_OneByOne)
            self.cam2.StartGrabbing(pylon.GrabStrategy_OneByOne) #basler2
            self.is_grabbing = True
        try:
            self.cam.ExecuteSoftwareTrigger()
            self.cam2.ExecuteSoftwareTrigger() #basler2
            result = self.cam.RetrieveResult(3000)
            result2 = self.cam2.RetrieveResult(3000) #basler2
            self.img.AttachGrabResultBuffer(result)
            self.img2.AttachGrabResultBuffer(result2) #basler2
            
            if result.GrabSucceeded():# and result2.GrabSucceeded():
                # Consider if we need to put directly in c_p?
                image = np.uint8(self.img.GetArray()[:1024,:1024]) #basler2
                image = np.uint8(self.img.GetArray())
                image2 = np.uint8(self.img2.GetArray()) #basler2
                tmp = np.zeros(np.shape(image)) #basler2?
                tmp[0:np.shape(image2)[0],0:np.shape(image2)[1]] = image2 #basler2
                org_img = np.concatenate((image, tmp), 0) #basler
                image = np.fliplr(org_img)
                return image 
        except TimeoutException as TE:
            print(f"Warning, camera timed out {TE}")


    def connect_camera(self):
        try:
            
            #os.environ["PYLON_CAMEMU"] = "1"

            #tlf = pylon.TlFactory.GetInstance() #basler2?
            #self.cam = pylon.InstantCamera(tlf.CreateFirstDevice()) #basler2?
            #self.cam.Open() #basler2?
            
            #self.cam.ImageFileMode = "On"
            #self.cam.TestImageSelector = "Off"
            #self.cam.ImageFilename = r"D:\SiO2_776nmEvery1_3\videos\figs"
            #self.cam.PixelFormat = "Mono8"


            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()
            self.cam = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
            self.cam.Open()

            # Adding second camera
            self.cam2 = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[1]))
            self.cam2.Open()
            print("Camera 2 is now open")
            
            sleep(0.2)
            
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
