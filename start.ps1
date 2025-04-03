# Thank you Claude

# Define paths
$venvDir = ".\venv"
$requirementsFile = ".\requirements.txt"
$pythonScript = "main.py"
$port = "5000"
$envFile = ".\.env"
$vaultJsonFile = ".\vault.json"
$vaultFilesDir = ".\vault-files"

# Log function with timestamp and color-coding
function Log-Message {
    param (
        [string]$Message,
        [string]$Type = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Type) {
        "INFO"    { "Cyan" }
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR"   { "Red" }
        default   { "White" }
    }
    
    Write-Host "[$timestamp] [$Type] $Message" -ForegroundColor $color
}

# Check if virtual environment exists
if (-not (Test-Path $venvDir)) {
    Log-Message "Virtual environment not found. Creating new virtual environment..." "INFO"
    python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Log-Message "Failed to create virtual environment. Please make sure Python is installed correctly." "ERROR"
        exit 1
    }
    Log-Message "Virtual environment created successfully." "SUCCESS"
}

# Activate virtual environment
Log-Message "Activating virtual environment..." "INFO"
& "$venvDir\Scripts\Activate.ps1"

# Check if requirements file exists
if (Test-Path $requirementsFile) {
    # Get currently installed packages
    $installedPackages = pip freeze
    
    # Read requirements file
    $requirements = Get-Content $requirementsFile
    
    # Check if all requirements are already installed with correct versions
    $needsUpdate = $false
    foreach ($req in $requirements) {
        if ($req -and -not ($req -match "^\s*#")) {  # Skip empty lines and comments
            $packageName = $req -split "==" | Select-Object -First 1
            if (-not ($installedPackages -match "^$packageName==")) {
                $needsUpdate = $true
                break
            }
        }
    }
    
    if ($needsUpdate) {
        Log-Message "Installing/updating packages from requirements.txt..." "INFO"
        pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            Log-Message "Failed to install required packages. Please check your requirements.txt file." "ERROR"
            exit 1
        }
        Log-Message "Packages installed successfully." "SUCCESS"
    } else {
        Log-Message "All required packages are already installed." "SUCCESS"
    }
} else {
    Log-Message "requirements.txt not found. Skipping package installation." "WARNING"
}

# Check for .env file
if (Test-Path $envFile) {
    Log-Message ".env file found." "SUCCESS"
} else {
    Log-Message ".env file not found. Application may not function correctly without environment variables." "WARNING"
    
    # Create .env file with default variables
    $createEnv = Read-Host "Would you like to create a .env file with default environment variables? (y/n)"
    if ($createEnv -eq "y") {
        @"
ARGON2_CONFIG=""
SECRET_KEY=""
"@ | Out-File -FilePath $envFile
        Log-Message ".env file created with default environment variables. Please configure the values." "INFO"
    }
}

# Check for vault.json file
if (Test-Path $vaultJsonFile) {
    Log-Message "vault.json file found." "SUCCESS"
    
    # Validate JSON format and structure
    try {
        $vaultContent = Get-Content $vaultJsonFile -Raw | ConvertFrom-Json
        
        # Check if vault.json has the required structure {"accounts": {...}}
        if (Get-Member -InputObject $vaultContent -Name "accounts" -MemberType Properties) {
            Log-Message "vault.json has the required {'accounts': {...}} structure." "SUCCESS"
        } else {
            Log-Message "vault.json is valid JSON but does not have the required {'accounts': {...}} structure." "WARNING"
            $updateStructure = Read-Host "Would you like to update vault.json to the correct structure? (y/n)"
            if ($updateStructure -eq "y") {
                $existingContent = if ($vaultContent -ne $null) { $vaultContent | ConvertTo-Json -Depth 10 } else { "{}" }
                $newContent = '{"accounts": {}}'
                $newContent | Out-File -FilePath $vaultJsonFile
                Log-Message "vault.json updated with the {'accounts': {}} structure." "SUCCESS"
            }
        }
    } catch {
        Log-Message "vault.json is not valid JSON. Please check the file format." "ERROR"
    }
} else {
    Log-Message "vault.json file not found. This file may be required for certain functionality." "WARNING"
    
    # Create empty vault.json file with correct structure
    $createVault = Read-Host "Would you like to create a vault.json file with the required structure? (y/n)"
    if ($createVault -eq "y") {
        '{"accounts": {}}' | Out-File -FilePath $vaultJsonFile
        Log-Message "vault.json file created with {'accounts': {}} structure." "SUCCESS"
    }
}

# Check for vault-files directory
if (Test-Path $vaultFilesDir) {
    Log-Message "vault-files directory found." "SUCCESS"
} else {
    Log-Message "vault-files directory not found. This directory may be required for file storage." "WARNING"
    
    # Create vault-files directory
    $createDir = Read-Host "Would you like to create the vault-files directory? (y/n)"
    if ($createDir -eq "y") {
        New-Item -Path $vaultFilesDir -ItemType Directory | Out-Null
        Log-Message "vault-files directory created." "SUCCESS"
    }
}

# Start waitress server
Log-Message "Starting waitress server on port $port..." "SUCCESS"
waitress-serve --listen *:$port $pythonScript.Replace(".py", ":app")