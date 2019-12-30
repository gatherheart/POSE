from flask import Flask, request, jsonify, redirect, url_for, flash
from flask_session import Session
from werkzeug.utils import secure_filename
import os
import io
import Image

app = Flask(__name__)
sess = Session()
sess.init_app(app)

app.config.update(
    SECRET_KEY=os.urandom(24),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_NAME='POSTURE-WebSession',
    WTF_CSRF_TIME_LIMIT=None
)

UPLOAD_FOLDER = './uploaded/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
    	filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload/<frame>', methods = ['POST'])
def upload_file(frame):
    if request.method == 'POST':
        # check if the post request has the file part
        if 'image' not in request.files:
            print("File not in request.file")
            return redirect(request.url)
        file = request.files['image']
        print(file)
        # if user does not select file, browser also
        # submit a empty part without filename
        if file and allowed_file(frame):
	    try:
		img = Image.open(file)
		img.save(os.path.join(app.config['UPLOAD_FOLDER'], frame))
    		return jsonify({"success": "true"})

	    except Exception as e:
        	print('EXCEPTION:', str(e))
        	return 'Error processing image', 500

@app.route('/userLogin', methods = ['POST'])
def userLogin():
    user = request.get_json() 
    return jsonify({"success": "true"})

@app.route('/environments/<language>')
def environments(language):
    return jsonify({"language": language})

@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
