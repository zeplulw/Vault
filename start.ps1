# Thank you Claude

# Define paths
$venvDir = ".\venv"
$requirementsFile = ".\requirements.txt"
$pythonScript = "main.py"
$port = "5000"

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

# Start waitress server
Log-Message "Starting waitress server on port $port..." "SUCCESS"
waitress-serve --listen 0.0.0.0:$port $pythonScript.Replace(".py", ":app")