from flask import request, jsonify, redirect, url_for, flash
from flask_session import Session
from werkzeug.utils import secure_filename
from threading import Thread
from PIL import Image
from time import time, sleep
from check_realtime import parseImg
from initial_set import initialize
from flask_jwt_extended import (create_access_token, create_refresh_token, 
jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)
from models import UserModel, PostureModel
from config import app, db, jwt
from ML import Classifier
import pandas as pd
import numpy as np
import traceback
import os
import shutil
import io
import asyncio
import glob
import json
	
sess = Session()
sess.init_app(app)

UPLOAD_FOLDER = './uploaded/'
PARSE_FOLDER = './parsed/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
MAX_COUNT = 30
THRESHOLD = 1.3

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PARSE_FOLDER'] = PARSE_FOLDER

@app.before_first_request
def create_tables():
    db.create_all()

def delete_files(folder):
    files = glob.glob(folder+'*')
    for f in files:
        os.remove(f)

def allowed_file(filename):
    return '.' in filename and \
    	filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def jsonLoad(path):
    with open(path) as f:
        return json.load(f)

def pdStrToFloat(datagram):
    datagram.eye_distance.astype('float64')
    datagram.head_slope.astype('float64')
    datagram.right_shoulder_neck.astype('float64')
    datagram.left_shoulder_neck.astype('float64')
    datagram.shoulder_slope.astype('float64')
    datagram.shoulder_width.astype('float64')

@app.route('/initialSet', methods = ['POST'])
@jwt_required
def initial_set():
    identity = get_raw_jwt()['identity']
    print(identity)
    data = None
    files = request.files
    if 'image' not in files:
        print("File not in request.file")
        return redirect(request.url)
    file = files['image']
    user = UserModel.find_by_username(identity)
    if file:
        try:
            img = Image.open(file)
            img.save(os.path.join(app.config['UPLOAD_FOLDER']+identity+'/', 'initial.jpg'))
            data = initialize(os.path.join(app.config['UPLOAD_FOLDER']+identity+'/', 'initial.jpg'), identity)
        
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            return {'message': 'Error in initialization'}, 500

        try:
            user.normalPosture = json.dumps(data)
        except Exception as e:         
            print(e)
            print(traceback.format_exc())
            return {'message': 'Failure'}, 500
        finally:
            user.save_to_db()
            return {'message': 'Success'}, 200

@app.route('/parse', methods = ['GET'])
@jwt_required
def parse_data():
    identity = get_raw_jwt()['identity']
    user = UserModel.find_by_username(identity)

    try:
        folderCount = len(glob.glob(app.config['UPLOAD_FOLDER']+identity+'/*.jpg'))

        delete_files(app.config['PARSE_FOLDER']+identity+'/json/')
        delete_files(app.config['PARSE_FOLDER']+identity+'/image/')
        parseImg(app.config['UPLOAD_FOLDER']+identity+'/', identity)
        delete_files(app.config['UPLOAD_FOLDER']+identity+'/')
        
        normalPosture = json.loads(user.normalPosture)
        normalSeries = pd.Series(normalPosture['quantitative'][0])
        normalSeries = normalSeries.astype('float64')
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return {"message": "Failure"}, 500

    jsonFiles = glob.glob(app.config['PARSE_FOLDER']+identity+'/json/*.json')
    if 'initial.json' in jsonFiles:
        jsonFiles.remove('initial.json')
    folderCount = len(jsonFiles)
    
    data = pd.DataFrame()
    for i, _file in enumerate(jsonFiles):
        try:
            jsonFile = jsonLoad(_file)
            jsonFile = jsonFile['quantitative'][0]  
        except Exception as e:
            print(e)
            folderCount -= 1
            continue
        
        data = data.append(pd.DataFrame(jsonFile, index=[i]))
    
    data = data.astype('float64')
    # Centering Data on Normal Posture
    data -= normalSeries
    # standardization
    data = (data - np.mean(data, axis = 0)) / np.std(data, axis = 0, ddof = 1)
    predicted = Classifier.Rf(data)
    
    total = len(predicted)
    normal = (predicted == 0).sum() / total
    FHP = (predicted == 1).sum() / total
    scoliosis = (predicted == 2).sum() / total
    slouch = (predicted == 3).sum() / total
    postures = np.array([normal, FHP, scoliosis, slouch])
    print("Normal: {}, FHP: {}, Scoliosis: {}, Slouch: {}".format(normal, FHP, scoliosis, slouch))
    postureVal = np.amax(postures)
    postureIdx = np.where(postures == np.amax(postures))[0][0]
    
    # Threshold for normal posture
    if postureVal < THRESHOLD * normal:
        postureVal = normal
        postureIdx = 0

    print("Posture: {} - {}".format(postureIdx, postureVal))
    result =  {"message": "Success", "MFP": str(postureIdx), "MFP_val": str(postureVal), 
            "normal": str(normal), "FHP": str(FHP), "scoliosis": str(scoliosis), "slouch": str(slouch)}
    
    try:
        new_posture = PostureModel(
            uid = user.id,
            postureData = json.dumps(result)
        )
    except Exception as e:         
        print(traceback.format_exc())
        print(e)
    finally:
        new_posture.save_to_db()

    return result, 200

@app.route('/upload/<frame>', methods = ['POST'])
@jwt_required
def upload_file(frame):
    if request.method == 'POST':

        identity = get_raw_jwt()['identity']
        # check if the post request has the file part
        files = request.files
        if 'image' not in files:
            print("File not in request.file")
            return redirect(request.url)
        file = files['image']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file and allowed_file(frame):
            try:
                img = Image.open(file)
                img.save(os.path.join(app.config['UPLOAD_FOLDER']+identity+'/', frame))

                print(frame)
                count = frame.split('_')[1]
                print(count)

                return jsonify({"success": "true", "count": str(int(count) % MAX_COUNT)})

            except Exception as e:
                print('EXCEPTION:', str(e))
                return 'Error processing image', 500

@app.route('/userSignin', methods = ['POST'])
def userSignin():
    data = request.get_json()

    if UserModel.find_by_username(data['username']):
          return {'message': 'User {} already exists'. format(data['username'])}

    new_user = UserModel(
        username = data['username'],
        password = UserModel.generate_hash(data['password'])
    )
    try:
        new_user.save_to_db()
        access_token = create_access_token(identity = data['username'])
        refresh_token = create_refresh_token(identity = data['username'])
        return {'message': 'User {} was created'.format( data['username']), 
                'access_token': access_token, 
                'refresh_token': refresh_token}
    except:
        return {'message': 'Something went wrong'}, 500


@app.route('/userLogin', methods = ['POST'])
def userLogin():
    data = request.get_json() 
    current_user = UserModel.find_by_username(data['username'])
    if not current_user:
        return {'message': 'User {} doesn\'t exist'.format(data['username'])}
      
    if UserModel.verify_hash(data['password'], current_user.password):
        access_token = create_access_token(identity = data['username'])
        refresh_token = create_refresh_token(identity = data['username'])

        if not os.path.exists(app.config['UPLOAD_FOLDER']+data['username']):
            os.makedirs(app.config['UPLOAD_FOLDER']+data['username'])
        else:
            delete_files(app.config['UPLOAD_FOLDER']+data['username']+'/')

        if not os.path.exists(app.config['PARSE_FOLDER']+data['username']+'/image'):
            os.makedirs(app.config['PARSE_FOLDER']+data['username']+'/image')
        else:
            delete_files(app.config['UPLOAD_FOLDER']+data['username']+'/image/')

        if not os.path.exists(app.config['PARSE_FOLDER']+data['username']+'/json'):
            os.makedirs(app.config['PARSE_FOLDER']+data['username']+'/json')
        else:
            delete_files(app.config['UPLOAD_FOLDER']+data['username']+'/json/')

        return {'message': 'Logged in as {}'.format(current_user.username), 
                'access_token': access_token, 
                'refresh_token': refresh_token}
    else:
        return {'message': 'Wrong credentials'}, 404

@app.route('/', methods= ['GET'])
@jwt_required
def hello_world():
    print(get_raw_jwt())
    return 'Hello World!'

if __name__ == "__main__":

    app.run(host='0.0.0.0', port=8000)
