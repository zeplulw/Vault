#!/bin/bash
# Thank you Claude

# Define paths
VENV_DIR="./venv"
REQUIREMENTS_FILE="./requirements.txt"
PYTHON_SCRIPT="main.py"
PORT="5000"

# Log function with timestamp and color-coding
log_message() {
    local message="$1"
    local type="${2:-INFO}"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case "$type" in
        "INFO")    color="\033[36m" ;; # Cyan
        "SUCCESS") color="\033[32m" ;; # Green
        "WARNING") color="\033[33m" ;; # Yellow
        "ERROR")   color="\033[31m" ;; # Red
        *)         color="\033[0m"  ;; # Default
    esac
    
    echo -e "${color}[$timestamp] [$type] $message\033[0m"
}

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    log_message "Virtual environment not found. Creating new virtual environment..." "INFO"
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        log_message "Failed to create virtual environment. Please make sure Python is installed correctly." "ERROR"
        exit 1
    fi
    log_message "Virtual environment created successfully." "SUCCESS"
fi

# Activate virtual environment
log_message "Activating virtual environment..." "INFO"
source "$VENV_DIR/bin/activate"

# Check if requirements file exists
if [ -f "$REQUIREMENTS_FILE" ]; then
    # Check if pip-tools is installed for better dependency management
    if ! pip list | grep -q "pip-tools"; then
        log_message "Installing pip-tools for dependency management..." "INFO"
        pip install pip-tools
    fi
    
    # Get currently installed packages as a temporary file
    pip freeze > /tmp/installed_packages.txt
    
    # Check if all requirements are already installed with correct versions
    needs_update=false
    while IFS= read -r requirement; do
        # Skip empty lines and comments
        if [[ -n "$requirement" && ! "$requirement" =~ ^\s*# ]]; then
            package_name=$(echo "$requirement" | cut -d'=' -f1)
            if ! grep -q "^$package_name==" /tmp/installed_packages.txt; then
                needs_update=true
                break
            fi
        fi
    done < "$REQUIREMENTS_FILE"
    
    # Clean up temporary file
    rm /tmp/installed_packages.txt
    
    if [ "$needs_update" = true ]; then
        log_message "Installing/updating packages from requirements.txt..." "INFO"
        pip install -r "$REQUIREMENTS_FILE"
        if [ $? -ne 0 ]; then
            log_message "Failed to install required packages. Please check your requirements.txt file." "ERROR"
            exit 1
        fi
        log_message "Packages installed successfully." "SUCCESS"
    else
        log_message "All required packages are already installed." "SUCCESS"
    fi
else
    log_message "requirements.txt not found. Skipping package installation." "WARNING"
fi

# Start waitress server
log_message "Starting waitress server on port $PORT..." "SUCCESS"
module_name=$(basename "$PYTHON_SCRIPT" .py)
waitress-serve --listen=0.0.0.0:$PORT "$module_name:app"