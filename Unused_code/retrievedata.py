from pypylon import pylon
import numpy as np

import time

import os
import cv2

def configure_camera(camera, exposure_time_us, num_images_to_acquire, W=0, H=0, burst_mode=True):
    # Set the exposure time in microseconds
    camera.ExposureTime.SetValue(exposure_time_us)

    # Set the camera to continuous acquisition mode
    camera.AcquisitionMode.SetValue('Continuous')
    
    # Set the pixel format to Mono8
    camera.PixelFormat.SetValue('Mono8')

    #Set the size of the image
    if W != 0 and H != 0:
        camera.Width.SetValue(W)
        camera.Height.SetValue(H)
    
    camera.MaxNumBuffer.SetValue(num_images_to_acquire)

    if burst_mode:
        #Set trigger mode to FrameBurstStart
        camera.TriggerSelector.SetValue('FrameBurstStart')

        #Set triggerMode to On
        camera.TriggerMode.SetValue('On')

        #Set triggerSource to Software
        camera.TriggerSource.SetValue('Software')

        #Set BslAcquisitionBurstMode
        camera.BslAcquisitionBurstMode.SetValue('HighSpeed')

        #Set BslAcquisitionBurstFrameCount
        camera.AcquisitionBurstFrameCount.SetValue(num_images_to_acquire)

def acquire_images_burst(camera, num_images, retrievespeed=100):
    # Start grabbing images
    camera.StartGrabbingMax(num_images, pylon.GrabStrategy_OneByOne)

    # Create an array to store the images
    images = []

    camera.ExecuteSoftwareTrigger()

    # Retrieve and store the grabbed images
    while camera.IsGrabbing():
        grab_result = camera.RetrieveResult(retrievespeed, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            images.append(grab_result.Array)

        grab_result.Release()

    # Stop grabbing
    camera.StopGrabbing()

    return images

def acquire_images(camera, num_images, retrievespeed=100):
    # Start grabbing images
    camera.StartGrabbingMax(num_images, pylon.GrabStrategy_OneByOne)

    # Create an array to store the images
    images = []

    camera.ExecuteSoftwareTrigger()

    # Retrieve and store the grabbed images
    while camera.IsGrabbing():
        grab_result = camera.RetrieveResult(retrievespeed, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            images.append(grab_result.Array)

        grab_result.Release()

    # Stop grabbing
    camera.StopGrabbing()

    return images

###MAIN###
if __name__ == '__main__':
    #Savefolder
    savefolder = 'C:/Users/Fredrik/Desktop/'    
    name = 'test'

    #Images to acquire (total, or in burst)
    num_images_to_acquire = 20

    # Set exposure time in microseconds
    exposure_time_us = 50  # Example: Set exposure time

    #Set retrieve speed, in us for retrieving each image. 
    retrievespeed_us = 50

    #Set burst mode
    burst_mode = True

    #Set size of image
    W = 512
    H = 512

    # Create an instant camera object with the first available camera device
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    # Open the camera
    camera.Open()

    #Configure the camera
    configure_camera(
        camera = camera, 
        exposure_time_us = exposure_time_us, 
        num_images_to_acquire = num_images_to_acquire, 
        W = W, 
        H = H,
        burst_mode = burst_mode
        )
    
    start = time.time()
    if not burst_mode:
        # Acquire images
        captured_images = acquire_images(
            camera, 
            num_images_to_acquire, 
            retrievespeed=retrievespeed_us,
            )
    else:
        # Acquire images
        captured_images = acquire_images_burst(
            camera, 
            num_images_to_acquire, 
            retrievespeed=retrievespeed_us,
            )
        
    end = time.time()
    print(f'Acquired {len(captured_images)} images in {end-start} seconds (including overhead)')

    #Get actual framerate from image acquisition and burst mode parameters
    try:
        if burst_mode:
            ResultingFrameRate = camera.ResultingFrameRate.GetValue()
            actual_framerate = camera.ResultingFrameRate.GetValue() * camera.AcquisitionBurstFrameCount.GetValue()
            actual_framerate2 = camera.BslResultingFrameBurstRate.GetValue()
            transfer_rate = camera.BslResultingTransferFrameRate.GetValue()

            print(f'ResultingFrameRate: {ResultingFrameRate} fps')
            print(f'ResultingFrameRate * camera.BslResultingFrameBurstRate: {actual_framerate} fps')
            print(f'BslResultingFrameBurstRate: {actual_framerate2} fps')
            print(f'BslResultingTransferFrameRate: {transfer_rate} fps')

        else:
            actual_framerate = camera.ResultingFrameRate.GetValue()
            print(f'ResultingFrameRate: {actual_framerate} fps')

    except:
        actual_framerate = 60

        print(f'ResultingFrameRate: {actual_framerate} fps')

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    shape = captured_images[0].shape
    out = cv2.VideoWriter(
        f'{savefolder}{name}.avi', 
        fourcc, 
        actual_framerate, 
        (shape[1], shape[0]), 
        isColor=False,
        )

    # Write the images to the video file
    for image in captured_images:
        out.write(image)
    # Release everything if job is finished
    out.release()

    # Close the camera
    camera.Close()