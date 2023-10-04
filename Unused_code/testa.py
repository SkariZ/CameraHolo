from pypylon import pylon
import numpy as np

import os
import cv2

def configure_camera(camera, exposure_time_us):
    # Set the exposure time in microseconds
    camera.ExposureTime.SetValue(exposure_time_us)

    # Set the camera to continuous acquisition mode
    camera.AcquisitionMode.SetValue('Continuous')

def acquire_images(camera, num_images):
    # Start grabbing images
    camera.StartGrabbingMax(num_images)

    # Create an array to store the images
    images = []

    # Retrieve and store the grabbed images
    while camera.IsGrabbing():
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        if grab_result.GrabSucceeded():
            # Access the image data and copy it into the array
            image_data = grab_result.Array
            images.append(np.copy(image_data))  # Make a copy to ensure data integrity

        grab_result.Release()

    # Stop grabbing
    camera.StopGrabbing()

    return images

#Savefolder
savefolder = ''    
name = 'test'
#os.environ["PYLON_CAMEMU"] = "1"

# Create an instant camera object with the first available camera device
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

# Open the camera
camera.Open()

# Set exposure time in microseconds
exposure_time_us = 10  # Example: Set exposure time
configure_camera(camera, exposure_time_us)

# Acquire 20 images as fast as possible with the specified exposure time
num_images_to_acquire = 20
captured_images = acquire_images(camera, num_images_to_acquire)

#Get actual framerate from image acquisition
try:
    actual_framerate = camera.ResultingFrameRate.GetValue()
except:
    actual_framerate = 60

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