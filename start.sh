#!/bin/bash

# Check if apt-get is available
if command -v apt-get >/dev/null 2>&1; then
    echo "apt-get is available."

    # Check if Python packages are installed
    if ! dpkg -s python3 python3.11-venv python3-pip >/dev/null 2>&1; then
        echo "Python packages are not installed."
        read -p "Do you want to install python3, python3-venv, and python3-pip? [y/N] " response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            # Prompt for sudo password if not running as root
            if [[ $EUID -ne 0 ]]; then
                echo "You need to have sudo privileges to install packages."
                sudo -v
                if [[ $? -ne 0 ]]; then
                    echo "Failed to obtain sudo privileges."
                    exit 1
                fi
            fi

            echo "Installing Python packages..."
            sudo apt-get update
            sudo apt-get install -y python3 python3-venv python3-pip
        else
            echo "Installation aborted. Exiting."
            exit 1
        fi
    else
        echo "Required Python packages are already installed. Proceeding..."
    fi
else
    echo "apt-get is not available. Please install python3, python3-venv, and python3-pip manually."
    exit 1
fi

# Create a Python virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install Python packages from requirements.txt
pip install -r requirements.txt

# Run the Python script
python3 mass_ip_analysis.py
