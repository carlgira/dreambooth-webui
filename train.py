from asyncio import subprocess
from re import sub
from subprocess import getoutput
import subprocess as subp
import os

HOME_DIR = os.environ['install_dir']
WORK_DIR = HOME_DIR + '/dreambooth'
MODEL_NAME = HOME_DIR + "/stable-diffusion-webui/models/Stable-diffusion/{0}.ckpt"
CONFIG_NAME = HOME_DIR + "/stable-diffusion-webui/models/Stable-diffusion/{0}.yaml"
DEFAULT_CONFIG_NAME = HOME_DIR + "/stable-diffusion-webui/models/Stable-diffusion/model.yaml"
SD_MODEL_PATH = WORK_DIR + '/stable-diffusion'


def train_model(training_subject, subject_type, instance_name, class_dir, training_steps, seed):
    Training_Subject = training_subject
    SUBJECT_TYPE = subject_type
    INSTANCE_NAME = instance_name
    CLASS_DIR= WORK_DIR + "/data/{class_dir}/{class_dir}".format(class_dir=class_dir)
    Training_Steps = training_steps
    Seed=seed
        
    With_Prior_Preservation = "Yes"
    Captionned_instance_images = False
    INSTANCE_DIR = WORK_DIR + "/data/" + INSTANCE_NAME
    NEW_MODEL_NAME = WORK_DIR + "/output/{INSTANCE_NAME}.ckpt".format(INSTANCE_NAME=INSTANCE_NAME)
    Number_of_subject_images = 500
    SUBJECT_IMAGES = Number_of_subject_images
    OUTPUT_DIR = WORK_DIR + "/models/"+ INSTANCE_NAME

    Style=""
    if Training_Subject=="Character" or Training_Subject=="Object":
        PT="photo of "+INSTANCE_NAME+" "+SUBJECT_TYPE
        CPT="a photo of a "+SUBJECT_TYPE+", ultra detailed"
        if Captionned_instance_images:
            PT="photo of"
    elif Training_Subject=="Style":
        With_Prior_Preservation = "No"
        PT="in the "+SUBJECT_TYPE+" style of "+INSTANCE_NAME
        if Captionned_instance_images:
            PT="in the style of"  
        Style="--Style"
    elif Training_Subject=="Artist":
        With_Prior_Preservation = "No"
        PT=SUBJECT_TYPE+" By "+INSTANCE_NAME
        if Captionned_instance_images:
            PT="by the artist"  
    elif Training_Subject=="Movie":
        PT="from the "+SUBJECT_TYPE+" movie "+ INSTANCE_NAME
        CPT="still frame from "+SUBJECT_TYPE+" movie, ultra detailed, 4k uhd"
        if Captionned_instance_images:
            PT="from the movie"  
    elif Training_Subject=="TV Show":
        CPT="still frame from "+SUBJECT_TYPE+" tv show, ultra detailed, 4k uhd"
        PT="from the "+SUBJECT_TYPE+" tv show "+ INSTANCE_NAME
        if Captionned_instance_images:
            PT="from the tv show"       

    fp16 = True

    if fp16:
        prec="fp16"
    else:
        prec="no"

    s = getoutput('nvidia-smi')
    if 'A100' in s:
        precision="no"
    else:
        precision=prec
    
    prc="--fp16" if precision=="fp16" else ""

    Save_Checkpoint_Every_n_Steps = False
    Save_Checkpoint_Every=500
    if Save_Checkpoint_Every==None:
        Save_Checkpoint_Every=1

    stp=0
    Start_saving_from_the_step=500
    if Start_saving_from_the_step==None:
        Start_saving_from_the_step=0
    if (Start_saving_from_the_step < 200):
        Start_saving_from_the_step=Save_Checkpoint_Every
    stpsv=Start_saving_from_the_step
    if Save_Checkpoint_Every_n_Steps:
        stp=Save_Checkpoint_Every

    SESSION_DIR='/home/ubuntu/dreambooth/sessions/carlgira'
    getoutput("sudo systemctl stop stable-diffusion")
    
    dump_only_textenc(SD_MODEL_PATH, INSTANCE_DIR, OUTPUT_DIR, "", seed, precision, 350, 1e-06)
    train_only_unet(stpsv, stp, SESSION_DIR, SD_MODEL_PATH, INSTANCE_DIR, OUTPUT_DIR, "", seed, 512, precision, Training_Steps, Style ,2e-06)
    
    getoutput(os.getenv("venv_bin_dir") + "/python {WORK_DIR}/diffusers/scripts/convertosdv2.py {PRC} {OUTPUT_DIR} {CHECKPOINT_PATH}".format(PRC=prc, OUTPUT_DIR=OUTPUT_DIR, CHECKPOINT_PATH=NEW_MODEL_NAME, WORK_DIR=WORK_DIR ))
    
    getoutput("cp {CHECKPOINT_PATH} {MODEL_NAME}".format(CHECKPOINT_PATH=NEW_MODEL_NAME, MODEL_NAME=MODEL_NAME.format("carlgira")))
    getoutput("cp {DEFAULT_CONFIG_NAME} {CONFIG_NAME}".format(DEFAULT_CONFIG_NAME=DEFAULT_CONFIG_NAME, CONFIG_NAME=CONFIG_NAME.format("carlgira")))
    
    getoutput("sudo systemctl start stable-diffusion")
    
    getoutput("rm {LOG_FILE}".format(LOG_FILE=HOME_DIR + "/dreambooth-webui/outpu.log"))
    
def dump_only_textenc(MODELT_NAME, INSTANCE_DIR, OUTPUT_DIR, PT, Seed, precision, Training_Steps, lr):
    
    command = os.getenv("venv_bin_dir") + "/accelerate launch " + WORK_DIR + '/diffusers/examples/dreambooth/train_dreambooth.py ' + \
        '--image_captions_filename ' + \
        '--train_text_encoder ' + \
        '--dump_only_text_encoder ' + \
        '--pretrained_model_name_or_path="{0}" '.format(MODELT_NAME) +  \
        '--instance_data_dir="{0}" '.format(INSTANCE_DIR)  + \
        '--output_dir="{0}" '.format(OUTPUT_DIR) + \
        '--instance_prompt="{0}" '.format(PT) + \
        '--seed={0} '.format(Seed) + \
        '--resolution=512 ' + \
        '--mixed_precision={0} '.format(precision) + \
        '--train_batch_size=1 ' + \
        '--gradient_accumulation_steps=1 --gradient_checkpointing ' + \
        '--use_8bit_adam ' + \
        '--learning_rate={0} '.format(lr) + \
        '--lr_scheduler="polynomial" ' + \
        '--lr_warmup_steps=0 ' + \
        '--max_train_steps={0} '.format(Training_Steps) + ' 2>output.log >output.log'
    
    return getoutput(command)

def train_only_unet(stpsv, stp, SESSION_DIR, MODELT_NAME, INSTANCE_DIR, OUTPUT_DIR, PT, Seed, Res, precision, Training_Steps, Style, lr):

    command = os.getenv("venv_bin_dir") + "/accelerate launch " + WORK_DIR + '/diffusers/examples/dreambooth/train_dreambooth.py ' + \
    Style + ' ' \
    '--image_captions_filename ' + \
    '--train_only_unet ' + \
    '--save_starting_step={0} '.format(stpsv) + \
    '--save_n_steps={0} '.format(stp) + \
    '--Session_dir={0} '.format(SESSION_DIR) + \
    '--pretrained_model_name_or_path="{0}" '.format(MODELT_NAME) + \
    '--instance_data_dir="{0}" '.format(INSTANCE_DIR) + \
    '--output_dir="{0}" '.format(OUTPUT_DIR) + \
    '--instance_prompt="{0}" '.format(PT) + \
    '--seed={0} '.format(Seed) + \
    '--resolution={0} '.format(Res) + \
    '--mixed_precision={0} '.format(precision) + \
    '--train_batch_size=1 ' + \
    '--gradient_accumulation_steps=1 --gradient_checkpointing ' + \
    '--use_8bit_adam ' + \
    '--learning_rate={0} '.format(lr) +  \
    '--lr_scheduler="polynomial" ' + \
    '--lr_warmup_steps=0 ' + \
    '--max_train_steps={0} '.format(Training_Steps) + ' 2>output.log >output.log'
    
    return getoutput(command)

