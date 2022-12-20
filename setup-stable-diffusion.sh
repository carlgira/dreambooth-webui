HF_TOKEN=$1
INSTALL_DIR="/home/$(whoami)"
WORK_DIR=$INSTALL_DIR/dreambooth
set -e
cd $WORK_DIR/stable-diffusion
git init
git lfs install --system --skip-repo
git remote add -f origin "https://USER:$HF_TOKEN@huggingface.co/stabilityai/stable-diffusion-2-1-base"
git config core.sparsecheckout true
printf "scheduler\ntext_encoder\ntokenizer\nunet\nvae\nmodel_index.json" > .git/info/sparse-checkout
git pull origin main

rm -rf .git
