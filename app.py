# create a webserver using flask framework

# import all the required libraries

from flask import Flask, render_template, request, redirect, url_for
import requests
import os
import subprocess
from train import train_model
from werkzeug.utils import secure_filename
import threading
import glob
import json
import logging

WORK_DIR = os.environ['install_dir']
CHECK_POINT_PATH_SD = WORK_DIR + '/stable-diffusion-webui/model.ckpt'
SD_RAW_MODEL = WORK_DIR + '/dreambooth/stable-diffusion-v1-5/unet/diffusion_pytorch_model.bin'
SD_URL = 'https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt'
UPLOAD_FOLDER = WORK_DIR + '/dreambooth/data'
t = None

INDEX_PAGE='index.html'
SETUP_PAGE='setup.html'
MESSAGES_PAGE='messages.html'
TXT2IMG_PAGE='txt2img.html'

languages = {}
language = 'en_US'

language_list = glob.glob("language/*.json")
for lang in language_list:
    filename = lang.split('/')[1]
    lang_code = filename.split('.')[0]
    with open(lang, 'r', encoding='utf8') as file:
        languages[lang_code] = json.loads(file.read())

texts = languages[language]

# create a flask object
flask = Flask(__name__)
# flask.config['TEMPLATES_AUTO_RELOAD'] = True # Debugging

# create a route for the home page
@flask.route('/', methods=['GET', 'POST'])
def home():
    global t
    
    # check if directory exists
    if not os.path.exists(CHECK_POINT_PATH_SD):
        
        if request.method == 'GET':
            return render_template(SETUP_PAGE)
        
        username = request.form['username']
        password = request.form['password']
        token = request.form['token']
        
        try:
            # download the model from the server and use basic authentication with the username and password
            req = requests.get(SD_URL, auth=(username, password))
            
            # check if the request is successful
            if req.status_code == 401:
                return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_wrong_credentials"])
            
            # check if the request is successful 
            if req.status_code == 403:
                return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_accept_conditions"])

            if req.status_code >= 500:
                return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_unexpected"])
                
            # save the model in the current directory
            with open(CHECK_POINT_PATH_SD, 'wb') as f:
                f.write(req.content)
        except:
            return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_wrong_credentials"])
        
        subprocess.run(["sudo", "systemctl", "start", "stable-diffusion.service"])
        
        
        try:
            sd_model = subprocess.run(["sh", WORK_DIR + "/dreambooth-webui/setup-stable-diffusion.sh", token], check=True)            
        except:
            return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_wrong_token"])
        
        
        return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts["ok_download"], COUNTDOWN=texts["download_waiting_time"], REDIRECT='"http://localhost:7860"')
    
    if not os.path.exists(SD_RAW_MODEL):
        if request.method == 'GET':
            return render_template(SETUP_PAGE)
        
        token = request.form['token']
        
        try:
            sd_model = subprocess.run(["sh", WORK_DIR + "/dreambooth-webui/setup-stable-diffusion.sh", token], check=True)            
        except:
            return render_template(SETUP_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_wrong_token"])
        
        return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts["ok_download"], COUNTDOWN=texts["download_waiting_time"], REDIRECT='"http://localhost:7860"')
    
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
                return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_no_zip_file"])
            file = request.files['images']
            if file.filename == '':
                return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_no_zip_file"])
            
            filename = secure_filename(file.filename)
            try:
                file.save(os.path.join(UPLOAD_FOLDER, filename))
            except:
                return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT='The zip file could not be saved')
            
            # unzip the file
            subprocess.run(["rm", "-rf", UPLOAD_FOLDER + '/' + instance_name])
            try:
                unzip = subprocess.run(["unzip", UPLOAD_FOLDER + '/' + filename, '-d' , UPLOAD_FOLDER + '/' + instance_name], check=True)
                # check that the unzipped file contains only images
                for file in os.listdir(UPLOAD_FOLDER + '/' + instance_name):
                    file_path = UPLOAD_FOLDER + '/' + instance_name + '/' + file
                    if os.path.isdir(file_path):
                        subprocess.run(["rm", "-rf", file_path])
                        continue
                    
                    # check if hidden file
                    if file[0] == '.': 
                        os.remove(file_path)
                        continue
                    
                    if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts['error_zip_contains_other_files'])
            except Exception as e:
                subprocess.run(["echo", str(e)])
                return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_unzip"])
            
            subprocess.run(["rm", "-rf", UPLOAD_FOLDER + '/' + filename])

            # call train_model function in a new thread
            t = threading.Thread(target=train_model, args=(training_subject, subject_type, instance_name, class_dir, training_steps, seed))
            t.start()

            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], COUNTDOWN=texts['training_time'], REDIRECT='"http://localhost:7860"')
        else:
            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], COUNTDOWN=texts['training_time'], REDIRECT='"http://localhost:7860"')
    
    if request.method == 'GET':
        if t is not None and t.is_alive():
            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], COUNTDOWN=texts['training_time'], REDIRECT='"http://localhost:7860"')
    
    return render_template(INDEX_PAGE)


# create a route for the home page
@flask.route('/txt2img', methods=['GET', 'POST'])
def txt2img():
    
    if request.method == 'GET':
        return render_template(TXT2IMG_PAGE)    
    
    if request.method == 'POST':
        
        file = request.files['prompts']
        
        logging.info('file: ' + str(file))
        

    
    
    
    return render_template(TXT2IMG_PAGE)

# run the flask app
if __name__ == '__main__':
    flask.run(debug=True, port=3000)
