#!/bin/bash
# Thank you Claude

# Define paths
VENV_DIR="./venv"
REQUIREMENTS_FILE="./requirements.txt"
PYTHON_SCRIPT="main.py"
PORT="5000"
ENV_FILE="./.env"
VAULT_JSON_FILE="./vault.json"
VAULT_FILES_DIR="./vault-files"

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

# Check for .env file
if [ -f "$ENV_FILE" ]; then
    log_message ".env file found." "SUCCESS"
else
    log_message ".env file not found. Application may not function correctly without environment variables." "WARNING"
    
    # Create .env file with base contents
    read -p "Would you like to create a .env file with base configuration? (y/n): " create_env
    if [ "$create_env" = "y" ]; then
        cat > "$ENV_FILE" << EOF
ARGON2_CONFIG=""
SECRET_KEY=""
EOF
        log_message ".env file created with base configuration. Please set your environment variables." "INFO"
    fi
fi

# Check for vault.json file
if [ -f "$VAULT_JSON_FILE" ]; then
    log_message "vault.json file found." "SUCCESS"
    
    # Validate JSON format and structure
    if command -v grep &> /dev/null && command -v head &> /dev/null; then
        # Quick structure check using grep - efficient but basic
        if grep -q '"accounts"' "$VAULT_JSON_FILE"; then
            log_message "vault.json appears to have the required {'accounts': {...}} structure." "SUCCESS"
        else
            log_message "vault.json may not have the required {'accounts': {...}} structure." "WARNING"
            
            # More detailed check if jq is available
            if command -v jq &> /dev/null; then
                if jq -e '.accounts' "$VAULT_JSON_FILE" > /dev/null 2>&1; then
                    log_message "Confirmed: vault.json has the 'accounts' property." "SUCCESS"
                else
                    log_message "vault.json does not have the 'accounts' property." "WARNING"
                    read -p "Would you like to update vault.json to the correct structure? (y/n): " update_structure
                    if [ "$update_structure" = "y" ]; then
                        echo '{"accounts": {}}' > "$VAULT_JSON_FILE"
                        log_message "vault.json updated with the {'accounts': {}} structure." "SUCCESS"
                    fi
                fi
            else
                read -p "Would you like to update vault.json to the correct structure? (y/n): " update_structure
                if [ "$update_structure" = "y" ]; then
                    echo '{"accounts": {}}' > "$VAULT_JSON_FILE"
                    log_message "vault.json updated with the {'accounts': {}} structure." "SUCCESS"
                fi
            fi
        fi
    else
        log_message "Required tools for checking JSON structure not available." "WARNING"
    fi
else
    log_message "vault.json file not found. This file may be required for certain functionality." "WARNING"
    
    # Create vault.json file with correct structure
    read -p "Would you like to create a vault.json file with the required structure? (y/n): " create_vault
    if [ "$create_vault" = "y" ]; then
        echo '{"accounts": {}}' > "$VAULT_JSON_FILE"
        log_message "vault.json file created with {'accounts': {}} structure." "SUCCESS"
    fi
fi

# Check for vault-files directory
if [ -d "$VAULT_FILES_DIR" ]; then
    log_message "vault-files directory found." "SUCCESS"
else
    log_message "vault-files directory not found. This directory may be required for file storage." "WARNING"
    
    # Create vault-files directory
    read -p "Would you like to create the vault-files directory? (y/n): " create_dir
    if [ "$create_dir" = "y" ]; then
        mkdir -p "$VAULT_FILES_DIR"
        log_message "vault-files directory created." "SUCCESS"
    fi
fi

# Start waitress server
log_message "Starting waitress server on port $PORT..." "SUCCESS"
module_name=$(basename "$PYTHON_SCRIPT" .py)
waitress-serve --listen=*:$PORT "$module_name:app"