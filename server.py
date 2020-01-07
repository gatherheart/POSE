from flask import request, jsonify, redirect, url_for, flash
from flask_session import Session
from werkzeug.utils import secure_filename
from threading import Thread
from PIL import Image
from time import time, sleep
from check_realtime import parseImg
from flask_jwt_extended import (create_access_token, create_refresh_token, 
jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)
from models import UserModel
from config import app, db, jwt
import os
import shutil
import io
import asyncio
import glob
	
sess = Session()
sess.init_app(app)

UPLOAD_FOLDER = './uploaded/'
PARSE_FOLDER = './parsed/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
MAX_COUNT = 5

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

                if int(count) % MAX_COUNT == 0:
                    folderCount = len(glob.glob(app.config['UPLOAD_FOLDER']+identity+'/*.jpg'))
                    print(folderCount)
                    if  folderCount >= MAX_COUNT:
                        print("2 Minutes")
                        parseImg(app.config['UPLOAD_FOLDER']+identity+'/', identity)
                        delete_files(app.config['UPLOAD_FOLDER']+identity+'/')

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
        
        if not os.path.exists(app.config['PARSE_FOLDER']+data['username']):
            os.makedirs(app.config['PARSE_FOLDER']+data['username'])
            os.makedirs(app.config['PARSE_FOLDER']+data['username']+'/json')
            os.makedirs(app.config['PARSE_FOLDER']+data['username']+'/image')
        
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
