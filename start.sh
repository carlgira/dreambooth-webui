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
    python_cmd="python3.8"
fi

if [[ -z "${pip_cmd}" ]]
then
    pip_cmd="pip3.8"
fi

# git executable
if [[ -z "${GIT}" ]]
then
    export GIT="git"
fi

# python3 venv without trailing slash (defaults to ${install_dir}/${clone_dir}/venv)
if [[ -z "${venv_dir}" ]]
then
    venv_dir=".venv"
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
    "${pip_cmd}" install -q --no-deps accelerate==0.12.0
    wget -q -i "https://github.com/TheLastBen/fast-stable-diffusion/raw/main/Dependencies/dbdeps.txt"
    for i in {1..3}
    do
        mv "deps.${i}" "deps.7z.00${i}"
    done
    7z x deps.7z.001
    cp -rf usr/local/lib/python3.8/dist-packages/* .venv/lib/python3.8/site-packages
    rm -rf *.00* dbdeps.txt usr

    "${pip_cmd}" install -r requirements.txt

    mkdir -p $WORK_DIR/stable-diffusion
    mkdir -p $WORK_DIR/models/stable-diffusion
    mkdir -p $WORK_DIR/data
    mkdir -p $WORK_DIR/output/txt2img

    git clone --depth 1 --branch updt https://github.com/TheLastBen/diffusers $WORK_DIR/diffusers
fi

# locate the bin folder of the venv
export venv_bin_dir=$(dirname "$(command -v python)")

printf "\n%s\n" "${delimiter}"
printf "Launching app.py..."
printf "\n%s\n" "${delimiter}"
"${python_cmd}" "${LAUNCH_SCRIPT}"
