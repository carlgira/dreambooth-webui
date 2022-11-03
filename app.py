# create a webserver using flask framework

# import all the required libraries

from flask import Flask, render_template, request, redirect, url_for
import requests
import os
import subprocess
from train import train_model
from werkzeug.utils import secure_filename
import threading


CHECK_POINT_PATH_SD = '/home/ubuntu/stable-diffusion-webui/model.ckpt'
SD_RAW_MODEL = '/home/ubuntu/dreambooth/models/stable-diffusion-v1-5/unet/diffusion_pytorch_model.bin'
SD_URL = 'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
UPLOAD_FOLDER = '/home/ubuntu/dreambooth/data'
t = None

# create a flask object
flask = Flask(__name__)
flask.config['TEMPLATES_AUTO_RELOAD'] = True # Debugging

# create a route for the home page
@flask.route('/', methods=['GET', 'POST'])
def home():
    global t
    # check if directory exists
    
    if not os.path.exists(CHECK_POINT_PATH_SD):
        
        if request.method == 'GET':
            return render_template('setup.html')
        
        username = request.form['username']
        password = request.form['password']
        token = request.form['token']
        
        try:
            # download the model from the server and use basic authentication with the username and password
            req = requests.get(SD_URL, auth=(username, password))
            
            
            # check if the request is successful
            if req.status_code == 401:
                return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='Your credentials are incorrect. Please try again.')
            
            # check if the request is successful
            if req.status_code == 403:
                return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='Please accept the conditions of use for the model. Go to https://huggingface.co/runwayml/stable-diffusion-v1-5')

            if req.status_code >= 500:
                return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='Unexpect error occured. Please try again later.')
                
            # save the model in the current directory
            with open(CHECK_POINT_PATH_SD, 'wb') as f:
                f.write(req.content)
        except:
            return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='Your credentials are incorrect. Please try again.')
        
        subprocess.run(["sudo", "systemctl", "start", "stabble-diffusion.service"])
        
        
        try:
            sd_model = subprocess.run(["sh", "/home/ubuntu/dreambooth-webui/setup-stable-diffusion.sh", token], check=True)            
        except:
            return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='The token is incorrect. Please try again.')
        
        
        return render_template('messages.html', MESSAGE_TITLE='Information', MESSAGE_CONTENT='The model has been downloaded successfully. Now you have to wait 5 minutes for the web app to be ready.', COUNTDOWN=300, REDIRECT='"http://localhost:7860"')
    
    if not os.path.exists(SD_RAW_MODEL):
        if request.method == 'GET':
            return render_template('setup.html')
        
        token = request.form['token']
        
        try:
            sd_model = subprocess.run(["sh", "/home/ubuntu/dreambooth-webui/setup-stable-diffusion.sh", token], check=True)            
        except:
            return render_template('setup.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='The token is incorrect. Please try again.')
        
        return render_template('messages.html', MESSAGE_TITLE='Information', MESSAGE_CONTENT='The model has been downloaded successfully. Now you have to wait 5 minutes for the web app to be ready.', COUNTDOWN=300, REDIRECT='"http://localhost:7860"')
    
    if request.method == 'POST':
        
        if t is None or not t.is_alive():
            # call the train_model function from train.py
            training_subject = request.form['training_subject']
            subject_type = request.form['subject_type']
            instance_name = request.form['instance_name']
            class_dir = request.form['class_dir']
            training_steps = request.form['training_steps']
            seed = request.form['seed']
            
            if 'images' not in request.files:
                return render_template('index.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='No zip file uploaded')
            file = request.files['images']
            if file.filename == '':
                return render_template('index.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='No zip file uploaded')
            
            filename = secure_filename(file.filename)
            try:
                file.save(os.path.join(UPLOAD_FOLDER, filename))
            except:
                return render_template('index.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='The zip file could not be saved')
            
            # unzip the file
            subprocess.run(["rm", "-rf", UPLOAD_FOLDER + '/' + instance_name])
            try:
                unzip = subprocess.run(["unzip", UPLOAD_FOLDER + '/' + filename, '-d' , UPLOAD_FOLDER + '/' + instance_name], check=True)
                # check that the unzipped file contains only images
                for file in os.listdir(UPLOAD_FOLDER + '/' + instance_name):
                    file_path = UPLOAD_FOLDER + '/' + instance_name + '/' + file
                    if os.path.isdir(file_path):
                        os.rmdir(file_path)
                        continue
                    
                    # check if hidden file
                    if file[0] == '.': 
                        os.remove(file_path)
                        continue
                    
                    if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        return render_template('index.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='The zip file contains files that are not images. Images must be in .png, .jpg or .jpeg format')
            except Exception as e:
                print(e)
                return render_template('index.html', MESSAGE_TITLE='Error', MESSAGE_CONTENT='There was an error while unzipping the file, please check the file and try again.')
            
            subprocess.run(["rm", "-rf", UPLOAD_FOLDER + '/' + filename])

            # call train_model function in a new thread
            t = threading.Thread(target=train_model, args=(training_subject, subject_type, instance_name, class_dir, training_steps, seed))
            t.start()

            return render_template('messages.html', MESSAGE_TITLE='Information', MESSAGE_CONTENT='Training already in progress, it should take an hour.', COUNTDOWN=4500, REDIRECT='"http://localhost:7860"')
        else:
            return render_template('messages.html', MESSAGE_TITLE='Information', MESSAGE_CONTENT='Training already in progress, it should take an hour.', COUNTDOWN=4500, REDIRECT='"http://localhost:7860"')
    
    if request.method == 'GET':
        if t is not None and t.is_alive():
            return render_template('messages.html', MESSAGE_TITLE='Information', MESSAGE_CONTENT='Training already in progress, it should take an hour.', COUNTDOWN=4500, REDIRECT='"http://localhost:7860"')
    
    return render_template('index.html')


# run the flask app
if __name__ == '__main__':
    flask.run(debug=True, port=3000)
