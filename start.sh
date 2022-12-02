#!/bin/bash

# Set defaults
# Install directory without trailing slash
if [[ -z "${install_dir}" ]]
then
    export install_dir="$(eval echo ~$USER)"
fi

WORK_DIR=$install_dir/dreambooth

if [[ -z "${LAUNCH_SCRIPT}" ]]
then
    LAUNCH_SCRIPT="app.py"
fi

# Name of the subdirectory (defaults to dreambooth-webui)
if [[ -z "${clone_dir}" ]]
then
    clone_dir="dreambooth-webui"
fi

# python3 executable
if [[ -z "${python_cmd}" ]]
then
    python_cmd="python3"
fi

if [[ -z "${pip_cmd}" ]]
then
    pip_cmd="pip3"
fi

# git executable
if [[ -z "${GIT}" ]]
then
    export GIT="git"
fi

# python3 venv without trailing slash (defaults to ${install_dir}/${clone_dir}/venv)
if [[ -z "${venv_dir}" ]]
then
    venv_dir="venv"
fi


# Disable sentry logging
export ERROR_REPORTING=FALSE

# Do not reinstall existing pip packages on Debian/Ubuntu
export PIP_IGNORE_INSTALLED=0

# Pretty print
delimiter="################################################################"

printf "\n%s\n" "${delimiter}"
printf "\e[1m\e[32mInstall script for dreambooth + Web UI\n"
printf "\n%s\n" "${delimiter}"

# Do not run as root
if [[ $(id -u) -eq 0 ]]
then
    printf "\n%s\n" "${delimiter}"
    printf "\e[1m\e[31mERROR: This script must not be launched as root, aborting...\e[0m"
    printf "\n%s\n" "${delimiter}"
    exit 1
else
    printf "\n%s\n" "${delimiter}"
    printf "Running on \e[1m\e[32m%s\e[0m user" "$(whoami)"
    printf "\n%s\n" "${delimiter}"
fi

# Check prerequisites
for preq in "${GIT}" "${python_cmd}"
do
    if ! hash "${preq}" &>/dev/null
    then
        printf "\n%s\n" "${delimiter}"
        printf "\e[1m\e[31mERROR: %s is not installed, aborting...\e[0m" "${preq}"
        printf "\n%s\n" "${delimiter}"
        exit 1
    fi
done

if ! "${python_cmd}" -c "import venv" &>/dev/null
then
    printf "\n%s\n" "${delimiter}"
    printf "\e[1m\e[31mERROR: python3-venv is not installed, aborting...\e[0m"
    printf "\n%s\n" "${delimiter}"
    exit 1
fi

cd "${install_dir}"/ || { printf "\e[1m\e[31mERROR: Can't cd to %s/, aborting...\e[0m" "${install_dir}"; exit 1; }
if [[ -d "${clone_dir}" ]]
then
    cd "${clone_dir}"/ || { printf "\e[1m\e[31mERROR: Can't cd to %s/%s/, aborting...\e[0m" "${install_dir}" "${clone_dir}"; exit 1; }
fi

printf "\n%s\n" "${delimiter}"
printf "Create and activate python venv"
printf "\n%s\n" "${delimiter}"
cd "${install_dir}"/"${clone_dir}"/ || { printf "\e[1m\e[31mERROR: Can't cd to %s/%s/, aborting...\e[0m" "${install_dir}" "${clone_dir}"; exit 1; }
if [[ ! -d "${venv_dir}" ]]
then
    "${python_cmd}" -m venv "${venv_dir}"
    first_launch=1
fi

# shellcheck source=/dev/null
if [[ -f "${venv_dir}"/bin/activate ]]
then
    source "${venv_dir}"/bin/activate
else
    printf "\n%s\n" "${delimiter}"
    printf "\e[1m\e[31mERROR: Cannot activate python venv, aborting...\e[0m"
    printf "\n%s\n" "${delimiter}"
    exit 1
fi

if [[ "$first_launch" -eq 1 ]]; then
    "${pip_cmd}" install -r requirements.txt
    mkdir -p $WORK_DIR/stable-diffusion-v1-5
    mkdir -p $WORK_DIR/models/stable-diffusion
    mkdir -p $WORK_DIR/data
    mkdir -p $WORK_DIR/output

    wget -O $WORK_DIR/convertosd.py https://github.com/TheLastBen/fast-stable-diffusion/raw/main/Dreambooth/convertosd.py
    git clone https://github.com/TheLastBen/diffusers $WORK_DIR/diffusers
    cd $WORK_DIR/diffusers
    git checkout 08a6dc8a5840e0cc09e65e71e9647321ab9bb254
    cd -
    
    git clone https://github.com/djbielejeski/Stable-Diffusion-Regularization-Images-person_ddim.git $WORK_DIR/data/person_ddim
    git clone https://github.com/djbielejeski/Stable-Diffusion-Regularization-Images-man_euler.git $WORK_DIR/data/man_euler
    git clone https://github.com/djbielejeski/Stable-Diffusion-Regularization-Images-man_unsplash.git $WORK_DIR/data/man_unsplash
    git clone https://github.com/djbielejeski/Stable-Diffusion-Regularization-Images-woman_ddim.git $WORK_DIR/data/woman_ddim
    git clone https://github.com/djbielejeski/Stable-Diffusion-Regularization-Images-blonde_woman.git $WORK_DIR/data/blonde_woman

    # Horrible FIX to avoid problem with CUDA_VISIBLE_DEVICES
    SITE_PACKAGES=$($python_cmd -c "import site; print(site.getsitepackages()[0])")
    sed -i '375s/args.gpu_ids/\"0\"/g' $SITE_PACKAGES/accelerate/commands/launch.py
fi

# locate the bin folder of the venv
export venv_bin_dir=$(dirname "$(command -v python)")

printf "\n%s\n" "${delimiter}"
printf "Launching app.py..."
printf "\n%s\n" "${delimiter}"
"${python_cmd}" "${LAUNCH_SCRIPT}"
