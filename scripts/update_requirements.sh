#!/bin/bash

# Create temporary requirements files
pip freeze > temp_requirements.txt

# Function to filter requirements
filter_requirements() {
    local input_file=$1
    local output_file=$2
    local exclude_file=$3
    
    if [ -f "$exclude_file" ]; then
        grep -v -f "$exclude_file" "$input_file" > "$output_file"
    else
        cp "$input_file" "$output_file"
    fi
}

# Create exclude patterns for dev and prod specific packages
echo "black==" > dev_packages.txt
echo "pytest==" >> dev_packages.txt
echo "pytest-asyncio==" >> dev_packages.txt
echo "pytest-cov==" >> dev_packages.txt
echo "mypy==" >> dev_packages.txt
echo "ruff==" >> dev_packages.txt

echo "gunicorn==" > prod_packages.txt
echo "uvloop==" >> prod_packages.txt
echo "httptools==" >> prod_packages.txt
echo "watchfiles==" >> prod_packages.txt

# Update common requirements (excluding both dev and prod specific packages)
cat dev_packages.txt prod_packages.txt > exclude_common.txt
filter_requirements temp_requirements.txt requirements.common.txt exclude_common.txt

# Clean up temporary files
rm temp_requirements.txt dev_packages.txt prod_packages.txt exclude_common.txt

echo "Requirements files have been updated!"
echo "Please review the changes in requirements.common.txt"
echo "Note: Dev and Prod specific packages are maintained manually in their respective files." 