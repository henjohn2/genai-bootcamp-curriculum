#!/bin/bash
# This script is tailored for setup on an Amazon EC2 Ubuntu instance.
# Define default user for the script
# This script is specific to cloud_init although it should work in user directory too

DEFAULT_USER="ubuntu"

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
    sudo apt-get install -y curl unzip wget git

    # Install AWS CLI if not present
    if ! command -v aws &> /dev/null; then
        sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        sudo unzip awscliv2.zip
        sudo ./aws/install
        sudo rm -rf awscliv2.zip aws
    fi
}

# Install Python tools and environment
function install_python_tools {
    run_as_user $DEFAULT_USER mkdir -p /home/$DEFAULT_USER
    if [ ! -d "/home/$DEFAULT_USER/miniconda" ]; then
        run_as_user $DEFAULT_USER wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh
        run_as_user $DEFAULT_USER bash /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh -b -p /home/$DEFAULT_USER/miniconda
        run_as_user $DEFAULT_USER rm /home/$DEFAULT_USER/Miniconda3-latest-Linux-x86_64.sh
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
    run_as_user $DEFAULT_USER bash -c "source /home/$DEFAULT_USER/miniconda/bin/activate $env_name && $CONDA_PATH install ipykernel --yes && python -m ipykernel install --user --name $env_name --display-name 'Python 3.12 ($env_name)' && $CONDA_PATH install torch --yes && pip install packaging ninja && pip install --verbose /home/$DEFAULT_USER/genai-bootcamp-curriculum/flash_attn-2.5.8-cp312-cp312-linux_x86_64_aws.whl --no-build-isolation"
}

# Clone and setup a course repository
function setup_repository {
    REPO_DIR="/home/$DEFAULT_USER/genai-bootcamp-curriculum"
    if [ ! -d "$REPO_DIR" ]; then
        run_as_user $DEFAULT_USER git clone https://github.com/henjohn2/genai-bootcamp-curriculum.git $REPO_DIR
    fi

    run_as_user $DEFAULT_USER bash -c "cd $REPO_DIR && git checkout improvements"
}

# Download data from S3
function download_data {
    if [ -n "$COMPANY_S3" ] && [ -n "$TASK" ]; then
        local target_path="/home/$DEFAULT_USER/genai-bootcamp-curriculum/data/${TASK,,}"
        run_as_user $DEFAULT_USER mkdir -p "$target_path"
        run_as_user $DEFAULT_USER aws s3 cp "s3://$COMPANY_S3/" "$target_path" --recursive
    fi
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

    local public_hostname=$(curl -s --max-time 2 http://169.254.169.254/latest/meta-data/public-hostname)
    if [ -z "$public_hostname" ]; then
        public_hostname="localhost"
    fi
    local access_url="http://$public_hostname:8888/lab?token=$jupyter_token"
    echo "Jupyter Lab is accessible at: $access_url"

    local filename="/home/$DEFAULT_USER/${public_hostname}_access_details.txt"
    echo -e "DNS: $public_hostname\nUsername: $DEFAULT_USER\nAccess Token: $jupyter_token\nAccess URL: $access_url" | run_as_user $DEFAULT_USER tee "$filename"

    if [ -n "$COMPANY_S3" ]; then
        run_as_user $DEFAULT_USER aws s3 cp "$filename" "s3://$COMPANY_S3/${public_hostname}_access_details.txt"
    fi
}

# Main function to run all setups
function main {
    parse_args "$@"
    update_system
    setup_repository
    install_python_tools
    setup_env_variables
    download_data
    start_jupyter
}

main "$@"
