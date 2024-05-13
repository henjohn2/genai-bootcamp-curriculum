#!/bin/bash
# This script is tailored for setup on a Google Cloud Platform (GCP) Ubuntu instance.
# Define default user for the script
# This script is specific to cloud_init although it should work in user directory too

DEFAULT_USER="ubuntu"
REPO_DIR="/home/$DEFAULT_USER/genai-bootcamp-curriculum"
export DRIVER_VERSION=$(curl --retry 5 -s -f -H 'Metadata-Flavor: Google' http://metadata/computeMetadata/v1/instance/attributes/nvidia-driver-version)
# Starting the main function


# Function to run command as a specific user
function run_as_user {
    local user=$1
    shift
    sudo -u $user "$@"
}

# Parse command-line options
function parse_args {
    while getopts ":u:" opt; do
        case $opt in
            u) use_locked_env="$OPTARG" ;;
            \?) echo "Invalid option -$OPTARG" >&2; exit 1 ;;
        esac
    done
}

# Function to wait until the apt-get locks are released
function wait_apt_locks_released {
    echo 'Waiting for apt locks to be released...'
    while sudo fuser /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        sleep 1
    done
}

# Function to install Linux headers necessary for the driver
function install_linux_headers {
    local kernel_version=$(uname -r)
    echo "Installing Linux headers for kernel: $kernel_version"
    sudo apt-get -o DPkg::Lock::Timeout=120 install -y linux-headers-$kernel_version
}

# Function to download and install Nvidia drivers
function install_nvidia_linux_drivers {
    echo "DRIVER_VERSION: $DRIVER_VERSION"
    local driver_installer_file_name=driver_installer.run
    local nvidia_driver_file_name=NVIDIA-Linux-x86_64-$DRIVER_VERSION.run

    if [[ -z $DRIVER_GCS_PATH ]]; then
        DRIVER_GCS_PATH="gs://nvidia-drivers-us-public/tesla/$DRIVER_VERSION"
    fi

    local driver_gcs_file_path="$DRIVER_GCS_PATH/$nvidia_driver_file_name"
    echo "Downloading driver from GCS location and install: $driver_gcs_file_path"
    gsutil -q cp "$driver_gcs_file_path" $driver_installer_file_name

    if [[ -f $driver_installer_file_name ]]; then
        chmod +x $driver_installer_file_name
        sudo ./$driver_installer_file_name --dkms -a -s --no-drm --install-libglvnd -m=kernel-open
        rm -rf $driver_installer_file_name
    else
        echo "Failed to download the Nvidia driver installer."
        exit 1
    fi
}


# Load company-specific configurations
function setup_env_variables {
    COMPANY_FILE="/home/$DEFAULT_USER/genai-bootcamp-curriculum/company.yml"
    if [ -f "$COMPANY_FILE" ]; then
        export $(run_as_user $DEFAULT_USER python3 -c "import yaml; env_vars = yaml.safe_load(open('$COMPANY_FILE')); print(' '.join([f'{k.upper()}={v}' for k, v in env_vars.items()]))")
    else
        echo "Warning: company.yml not found. Skipping company-specific configurations."
    fi
}

# Update package lists and install essential packages
function update_system {
    sudo apt-get update
    sudo apt-get install -y curl unzip wget git git-lfs docker-compose-plugin
}

# Install Python tools and environment
function install_python_tools {
    run_as_user $DEFAULT_USER mkdir -p /home/$DEFAULT_USER
    if [ ! -d "/home/$DEFAULT_USER/miniconda" ]; then
        run_as_user $DEFAULT_USER wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh
        run_as_user $DEFAULT_USER bash /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh -b -p /home/$DEFAULT_USER/miniconda
        run_as_user $DEFAULT_USER rm /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh
    else
        echo "Directory Exists"
    fi

    local CONDA_PATH="/home/$DEFAULT_USER/miniconda/bin/conda"
    run_as_user $DEFAULT_USER $CONDA_PATH init bash
    run_as_user $DEFAULT_USER bash -c "source /home/$DEFAULT_USER/.bashrc"

    local env_file="/home/$DEFAULT_USER/genai-bootcamp-curriculum/environment.yml"
    if [ "$use_locked_env" = "yes" ]; then
        env_file="/home/$DEFAULT_USER/genai-bootcamp-curriculum/locked-environment.yml"
    fi
    local env_name="course-env"

    run_as_user $DEFAULT_USER $CONDA_PATH env update -n $env_name -f $env_file || run_as_user $DEFAULT_USER $CONDA_PATH env create -f $env_file
    # run_as_user $DEFAULT_USER bash -c "source /home/$DEFAULT_USER/miniconda/bin/activate $env_name; $CONDA_PATH install ipykernel --yes; python -m ipykernel install --user --name $env_name --display-name 'Python 3.12 ($env_name)'; $CONDA_PATH install torch --yes; pip install packaging ninja; MAX_JOBS=2 pip install --verbose flash-attn --no-build-isolation"
    run_as_user $DEFAULT_USER bash -c "source /home/$DEFAULT_USER/miniconda/bin/activate $env_name && $CONDA_PATH install ipykernel --yes && python -m ipykernel install --user --name $env_name --display-name 'Python 3.12 ($env_name)' && pip install packaging ninja && pip install --verbose /home/$DEFAULT_USER/genai-bootcamp-curriculum/flash_attn-2.5.8-cp312-cp312-linux_x86_64.whl --no-build-isolation"
}


# Clone and setup a course repository
function setup_repository {
    
    if [ ! -d "$REPO_DIR" ]; then
        run_as_user $DEFAULT_USER git clone https://github.com/henjohn2/genai-bootcamp-curriculum.git $REPO_DIR
    fi

    run_as_user $DEFAULT_USER bash -c "cd $REPO_DIR && git checkout improvements && git-lfs pull"
}

# Update Jupyter configuration and start Jupyter Lab
function start_jupyter {
    local JUPYTER_CONFIG_DIR="/home/$DEFAULT_USER/.jupyter"
    run_as_user $DEFAULT_USER mkdir -p $JUPYTER_CONFIG_DIR
    local JUPYTER_CONFIG_FILE="$JUPYTER_CONFIG_DIR/jupyter_lab_config.py"

    if [ ! -f "$JUPYTER_CONFIG_FILE" ]; then
        run_as_user $DEFAULT_USER jupyter lab --generate-config
    fi

    if ! grep -q "c.MultiKernelManager.default_kernel_name" $JUPYTER_CONFIG_FILE; then
        echo "c.MultiKernelManager.default_kernel_name = 'course-env'" | run_as_user $DEFAULT_USER tee -a $JUPYTER_CONFIG_FILE
    fi

    local jupyter_token=$(run_as_user $DEFAULT_USER openssl rand -hex 32)
    run_as_user $DEFAULT_USER tmux new-session -d -s jupyter "cd /home/$DEFAULT_USER/genai-bootcamp-curriculum/ && source /home/$DEFAULT_USER/miniconda/bin/activate course-env && jupyter lab --ip=0.0.0.0 --no-browser --log-level=INFO --NotebookApp.token='$jupyter_token'"
    sleep 10
    local public_hostname=$(curl -s --max-time 2 http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")
    if [ -z "$public_hostname" ]; then
        public_hostname="localhost"
    fi
    local access_url="http://$public_hostname:8888/lab?token=$jupyter_token"
    echo "Jupyter Lab is accessible at: $access_url"

    local filename="/home/$DEFAULT_USER/${public_hostname}_access_details.txt"
    echo -e "DNS: $public_hostname\nUsername: $DEFAULT_USER\nAccess Token: $jupyter_token\nAccess URL: $access_url" | run_as_user $DEFAULT_USER tee "$filename"
}

function start_docker {
    run_as_user $DEFAULT_USER bash -c "cd $REPO_DIR && docker compose up -d"
}


# Main function to run all setups
function main {
    parse_args "$@"
    update_system

    # GCP does not have NVIDIA drivers by default.
    wait_apt_locks_released
    install_linux_headers
    source /opt/deeplearning/driver-version.sh
    install_nvidia_linux_drivers
    echo "Nvidia driver installation completed."

    # Set up course specific stuff.
    setup_repository
    install_python_tools
    # setup_env_variables
    start_jupyter
    start_docker
}

main "$@"
