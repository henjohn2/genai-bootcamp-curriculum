#!/bin/bash
# This script is tailored for general setup from the repository.

# Absolute path to the Conda executable
CONDA_PATH="$HOME/miniconda/bin/conda"
cd $HOME
#use the packages that are already resolved
use_locked_env="no"


# Function to parse command-line options
function parse_args {
    while getopts ":u:" opt; do
        case $opt in
            u) use_locked_env="$OPTARG" ;;
            \?) echo "Invalid option -$OPTARG" >&2; exit 1 ;;
        esac
    done
}

# Load company-specific configurations from company.yml if it exists
function setup_env_variables {
    COMPANY_FILE="$HOME/genai-bootcamp-curriculum/company.yml"
    if [ -f "$COMPANY_FILE" ]; then
        export $(python3 -c "import yaml; env_vars = yaml.safe_load(open('$COMPANY_FILE')); print(' '.join([f'{k.upper()}={v}' for k, v in env_vars.items()]))")
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
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf awscliv2.zip aws
    fi
}

# Install Python tools and environment
function install_python_tools {
    if [ ! -d "$HOME/miniconda" ]; then
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O Miniconda3-latest-Linux-x86_64.sh
        bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
        rm Miniconda3-latest-Linux-x86_64.sh
    fi
    
    # Initialize Conda for the shell
    $CONDA_PATH init bash
    source $HOME/.bashrc # Assuming the default shell is bash

    # Define the paths to the environment files
    local env_file="$HOME/genai-bootcamp-curriculum/environment.yml"
    if [ "$use_locked_env" = "yes" ]; then
        env_file="$HOME/genai-bootcamp-curriculum/locked-environment.yml"
    fi
    local env_name="course-env"
    
    # Create or update the Conda environment
    if $CONDA_PATH env list | grep -qw "$env_name"; then
        echo "Updating existing Conda environment: $env_name"
        $CONDA_PATH env update -n $env_name -f $env_file
    else
        echo "Creating new Conda environment: $env_name"
        if $CONDA_PATH env create -f $env_file; then
            echo "Environment $env_name created successfully."
        else
            echo "Failed to create Conda environment. Please check the environment file."
            return 1
        fi
    fi

    # Activate the Conda environment
    source $HOME/miniconda/bin/activate $env_name
    if [ $? -ne 0 ]; then
        echo "Failed to activate Conda environment: $env_name"
        exit 1
    fi

    # Additional Python packages installations
    $CONDA_PATH install ipykernel --yes
    python -m ipykernel install --user --name $env_name --display-name "Python 3.12 ($env_name)"
    $CONDA_PATH install torch --yes
    pip install packaging ninja
    pip install --verbose flash-attn --no-build-isolation
}



# Clone and setup a course repository
function setup_repository {
    REPO_DIR="$HOME/genai-bootcamp-curriculum"
    if [ ! -d "$REPO_DIR" ]; then
        echo "Cloning the repository..."
        git clone https://github.com/henjohn2/genai-bootcamp-curriculum.git $REPO_DIR
    fi

    cd $REPO_DIR
    git checkout improvements

    local env_file="$HOME/genai-bootcamp-curriculum/environment.yml"
    if [ "$use_locked_env" = "yes" ]; then
        env_file="$HOME/genai-bootcamp-curriculum/locked-environment.yml"
    fi
    local env_name="course-env"

    if ! type $CONDA_PATH >/dev/null 2>&1; then
        echo "Conda is not available. Attempting to initialize Conda..."
        $CONDA_PATH init bash
        echo "Please restart your terminal or source the appropriate shell configuration file."
        return 1
    fi

    if $CONDA_PATH env list | grep -qw "$env_name"; then
        echo "Updating existing Conda environment: $env_name"
        $CONDA_PATH env update -n $env_name -f $env_file
    else
        echo "Creating new Conda environment: $env_name"
        if $CONDA_PATH env create -f $env_file; then
            echo "Environment $env_name created successfully."
        else
            echo "Failed to create Conda environment. Please check the environment file."
            return 1
        fi
    fi
}

# Download data from S3
function download_data {
    if [ -n "$COMPANY_S3" ] && [ -n "$TASK" ]; then
        local target_path="$HOME/genai-bootcamp-curriculum/data/${TASK,,}"
        mkdir -p "$target_path"
        aws s3 cp "s3://$COMPANY_S3/" "$target_path" --recursive
    fi
}

# Update Jupyter configuration
function update_jupyter_config {
    JUPYTER_CONFIG_DIR="$HOME/.jupyter"
    mkdir -p $JUPYTER_CONFIG_DIR
    JUPYTER_CONFIG_FILE="$JUPYTER_CONFIG_DIR/jupyter_lab_config.py"

    if [ ! -f "$JUPYTER_CONFIG_FILE" ]; then
        jupyter lab --generate-config
    fi

    if ! grep -q "c.MultiKernelManager.default_kernel_name" $JUPYTER_CONFIG_FILE; then
        echo "c.MultiKernelManager.default_kernel_name = 'course-env'" >> $JUPYTER_CONFIG_FILE
    fi
}

# Start Jupyter Lab in a detached tmux session
function start_jupyter {
    update_jupyter_config
    jupyter_token=$(openssl rand -hex 32)
    tmux new-session -d -s jupyter "source $HOME/miniconda/bin/activate course-env; jupyter lab --ip=0.0.0.0 --no-browser --log-level=INFO --NotebookApp.token='$jupyter_token'"
    sleep 10

    if [ -z "$jupyter_token" ]; then
        echo "Failed to capture Jupyter Lab token."
        exit 1
    else
        public_hostname=$(curl -s --max-time 2 http://169.254.169.254/latest/meta-data/public-hostname)
        if [ -z "$public_hostname" ]; then
            public_hostname="localhost"
        fi
        access_url="http://$public_hostname:8888/lab?token=$jupyter_token"
        echo "Jupyter Lab is accessible at: $access_url"
        
        filename="$HOME/${public_hostname}_access_details.txt"
        echo "DNS: $public_hostname" > "$filename"
        echo "Username: ubuntu" >> "$filename"
        echo "Access Token: $jupyter_token" >> "$filename"
        echo "Access URL: $access_url" >> "$filename"
        
        if [ -n "$COMPANY_S3" ]; then
            aws s3 cp "$filename" "s3://$COMPANY_S3/${public_hostname}_access_details.txt"
        fi
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
