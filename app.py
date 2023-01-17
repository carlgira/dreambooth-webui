# create a webserver using flask framework

# import all the required libraries

from flask import Flask, render_template, request, redirect, url_for, send_file
import requests
import os
import subprocess
from subprocess import getoutput
from train import train_model
from werkzeug.utils import secure_filename
import threading
import glob
import json
import base64
from PIL import Image, PngImagePlugin
import random
import io
from subprocess import getoutput
from time import sleep
import logging

WORK_DIR = os.environ['install_dir']
CHECK_POINT_PATH_SD = WORK_DIR + '/stable-diffusion-webui/models/Stable-diffusion/model.ckpt'
CONFIG_PATH_SD = WORK_DIR + '/stable-diffusion-webui/models/Stable-diffusion/model.yaml'
SD_RAW_MODEL = WORK_DIR + '/dreambooth/stable-diffusion/unet/diffusion_pytorch_model.bin'
SD_URL = 'https://huggingface.co/stabilityai/stable-diffusion-2-1-base/resolve/main/v2-1_512-ema-pruned.ckpt'
SD_CONFIG = 'https://raw.githubusercontent.com/Stability-AI/stablediffusion/main/configs/stable-diffusion/v2-inference.yaml'
UPLOAD_FOLDER = WORK_DIR + '/dreambooth/data'
OUTPUT_DIR = WORK_DIR + "/dreambooth/output/txt2img"
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
            req_config = requests.get(SD_CONFIG, auth=(username, password))
            
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
            
            with open(CONFIG_PATH_SD, 'wb') as f:
                f.write(req_config.content)
            
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
        
        if not is_training_running():
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
                for i, file in enumerate(os.listdir(UPLOAD_FOLDER + '/' + instance_name)):
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

                    extension = file.split('.')[-1]
                    os.rename(file_path, UPLOAD_FOLDER + '/' + instance_name + '/' + instance_name + ' ({0})'.format(i+1) + '.' + extension)
                    
            except Exception as e:
                logging.exception("Error with unzip")
                return render_template(INDEX_PAGE, MESSAGE_TITLE=texts["type_of_message_error"], MESSAGE_CONTENT=texts["error_unzip"])
            
            subprocess.run(["rm", "-rf", UPLOAD_FOLDER + '/' + filename])

            # call train_model function in a new thread
            t = threading.Thread(target=train_model, args=(training_subject, subject_type, instance_name, class_dir, training_steps, seed))
            t.start()
            
            

            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], REDIRECT='"http://localhost:7860"')
        else:
            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], REDIRECT='"http://localhost:7860"')
    
    if request.method == 'GET':
        if is_training_running():
            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['training_in_progress'], REDIRECT='"http://localhost:7860"')
    
    return render_template(INDEX_PAGE)


# create a route for the home page
@flask.route('/txt2img', methods=['GET', 'POST'])
def txt2img():
    
    if request.method == 'GET':
        return render_template(TXT2IMG_PAGE)    
    
    if request.method == 'POST':
        session = random.randrange(1000, 10000)
        SESSION_DIR = OUTPUT_DIR + '/' + str(session)
        os.mkdir(SESSION_DIR)
        file = request.files['prompts']
        PROMPTS_FILE = SESSION_DIR + '/' + 'prompts.json'
        file.save(PROMPTS_FILE)
        
        data = None
        with open(PROMPTS_FILE) as json_file:
            data = json.load(json_file)
                
        url = "http://127.0.0.1:7860"
        for e, payload in enumerate(data):
            response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)

            r = response.json()

            for i, img in enumerate(r['images']):
                image = Image.open(io.BytesIO(base64.b64decode(img.split(",",1)[0])))

                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", payload['prompt'])
                image.save(SESSION_DIR + '/' + str(e) + '-' + str(i) + '.png' , pnginfo=pnginfo)
            
        ZIP_FILE = SESSION_DIR + '/images.zip'
        getoutput("zip -j {ZIP_FILE} {ZIP_FILES}".format(ZIP_FILE=ZIP_FILE, ZIP_FILES=SESSION_DIR + '/*'))
        
        return send_file(ZIP_FILE)
        
    return render_template(TXT2IMG_PAGE)
@flask.route('/stream')
def stream():
    try:
        with open(WORK_DIR + "/dreambooth-webui/output.log") as f:
                content = f.readlines()
        last_line = content[-1]
        if '100%' in last_line:
            return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['reload_model_message'], COUNTDOWN=texts["reload_model_time"], REDIRECT='"http://localhost:7860"')
        def generate():
                if len(content) > 0:
                    yield last_line
                    sleep(1)
    except:
        return render_template(MESSAGES_PAGE, MESSAGE_TITLE=texts["type_of_message_info"], MESSAGE_CONTENT=texts['reload_model_message'], COUNTDOWN=texts["reload_model_time"], REDIRECT='"http://localhost:7860"')
                
    return flask.response_class(generate(), mimetype='text/plain')


def is_training_running():
    output = getoutput("ps -ef | grep accelerate | grep -v grep")
    return len(output) > 0
    
# run the flask app
if __name__ == '__main__':
    flask.run(debug=True, port=3000)
