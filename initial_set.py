# From Python
# It requires OpenCV installed for Python
import sys
import cv2
import os
import queue
import json        
import cmath
from sys import platform
import argparse
from inspect import getsourcefile
from os.path import abspath

def distance(p0, p1):
    return cmath.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2).real

def slope(p0, p1):
    try:
        return abs(p1[0]-p0[0])/(p1[1]-p0[1])
    except ZeroDivisionError:
        return 0

def initialize(image, identity):
    try:
        # Import Openpose (Windows/Ubuntu/OSX)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        try:
            # Windows Import
            if platform == "win32":
                # Change these variables to point to the correct folder (Release/x64 etc.)
                sys.path.append('/home/ubuntu/openpose/build/python')
                os.environ['PATH']  = os.environ['PATH'] + ';' + dir_path + '/../../x64/Release;' +  dir_path + '/../../bin;'
                import pyopenpose as op
            else:
                # Change these variables to point to the correct folder (Release/x64 etc.)
                sys.path.append('/home/ubuntu/openpose/build/python')
                # If you run `make install` (default path is `/usr/local/python` for Ubuntu), you can also access the OpenPose/python module from there. This will install OpenPose and the python library at your desired installation path. Ensure that this is in your python path in order to use it.
                # sys.path.append('/usr/local/python')
                from openpose import pyopenpose as op
        except ImportError as e:
            print('Error: OpenPose library could not be found. Did you enable `BUILD_PYTHON` in CMake and have this Python script in the right folder?')
            raise e

        # Custom Params (refer to include/openpose/flags.hpp for more parameters)
        params = dict()
        params["model_folder"] = "/home/ubuntu/openpose/models/"
        params["face"] = True
        params["hand"] = False 
        params["number_people_max"] = 1 
        #params["write_json"] = "/home/ubuntu/server/tmp/" 

        # Starting OpenPose
        opWrapper = op.WrapperPython()
        opWrapper.configure(params)
        opWrapper.start()
        
        # Process Image
        datum = op.Datum()
        imageToProcess = cv2.imread(image)
        datum.cvInputData = imageToProcess
        opWrapper.emplaceAndPop([datum])

        nose = datum.poseKeypoints[0][0]
        chest = datum.poseKeypoints[0][1]
        left_shoulder = datum.poseKeypoints[0][2]
        right_shoulder = datum.poseKeypoints[0][5]
        
        data = {}
        data['quantitative'] = []
        data['quantitative'].append({
            'shoulder_width': str(distance(left_shoulder, right_shoulder)),
            'shoulder_slope': str(slope(right_shoulder, left_shoulder)),
            'head_slope': str(slope(nose, chest)),
            'left_shoulder_neck': str(slope(chest, left_shoulder)),
            'right_shoulder_neck': str(slope(chest, right_shoulder)),
            'eye_distance': str(distance(datum.faceKeypoints[0][36], datum.faceKeypoints[0][45]))
            })
        
        print("Done " + image) 
        return data

    except (Exception, Warning) as e:
        print("Initial IMAGE: "+e)
