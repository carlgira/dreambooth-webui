HF_TOKEN=$1
INSTALL_DIR="/home/$(whoami)"
WORK_DIR=$INSTALL_DIR/dreambooth
set -e
cd $WORK_DIR/stable-diffusion-v1-5
git init
git lfs install --system --skip-repo
git remote add -f origin "https://USER:$HF_TOKEN@huggingface.co/runwayml/stable-diffusion-v1-5"
git config core.sparsecheckout true
printf "feature_extractor\nsafety_checker\nscheduler\ntext_encoder\ntokenizer\nunet\nmodel_index.json" > .git/info/sparse-checkout
git pull origin main

git clone "https://USER:$HF_TOKEN@huggingface.co/stabilityai/sd-vae-ft-mse"
mv sd-vae-ft-mse vae
rm -rf .git


