#!/usr/bin/env python
"""
Download Articles Script

This script downloads PDF articles for included studies (GlobalInclusion = "Yes")
from the df_articles_results_classified.xlsx file using PyPaperBot.

Usage:
    python download_articles.py

Requirements:
    - pandas
    - openpyxl
    - PyPaperBot (install with: pip install PyPaperBot)
"""

import os
import pandas as pd
import subprocess
import tempfile
import sys
import importlib.util

def check_package_installed(package_name):
    """Check if a Python package is installed"""
    package_spec = importlib.util.find_spec(package_name)
    return package_spec is not None

def install_package(package_name):
    """Install a Python package using pip"""
    print(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"Successfully installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package_name}: {e}")
        return False

def main():
    # Check if PyPaperBot is installed
    if not check_package_installed("PyPaperBot"):
        print("PyPaperBot is not installed. Attempting to install it automatically...")
        
        # Try to install PyPaperBot
        if not install_package("PyPaperBot"):
            print("Could not install PyPaperBot via pip.")
            print("Trying to install from GitHub...")
            
            if not install_package("git+https://github.com/ferru97/PyPaperBot.git"):
                print("Failed to install PyPaperBot.")
                print("Please install it manually using: pip install PyPaperBot")
                sys.exit(1)
        
        # Verify installation worked
        if not check_package_installed("PyPaperBot"):
            print("PyPaperBot was installed but still cannot be imported.")
            print("There might be an issue with the installation.")
            sys.exit(1)
            
    # Check for required dependencies
    required_dependencies = [
        "requests", 
        "beautifulsoup4", 
        "pandas", 
        "numpy", 
        "selenium", 
        "undetected_chromedriver"
    ]
    
    missing_deps = []
    for dep in required_dependencies:
        if not check_package_installed(dep.split('>')[0]):  # Handle version requirements
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"Installing missing dependencies: {', '.join(missing_deps)}")
        for dep in missing_deps:
            install_package(dep)
        
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)  # Go up one level to get base directory
    
    # Input Excel file path
    data_path = os.path.join(base_dir, "data", "df_articles_results_classified.xlsx")
    
    # Output directory for downloaded articles
    download_dir = os.path.join(base_dir, "documents", "articles")
    
    # Create the download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    # Check if the input file exists
    if not os.path.exists(data_path):
        print(f"Error: Input file not found: {data_path}")
        sys.exit(1)
    
    # Load the Excel file
    try:
        print(f"Loading data from {data_path}...")
        df = pd.read_excel(data_path)
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        sys.exit(1)
    
    # Check if the required columns exist
    if "GlobalInclusion" not in df.columns:
        print("Error: 'GlobalInclusion' column not found in the Excel file")
        sys.exit(1)
    
    if "DOI" not in df.columns:
        print("Error: 'DOI' column not found in the Excel file")
        sys.exit(1)
    
    # Filter for included articles (GlobalInclusion = "Yes")
    included_df = df[df["GlobalInclusion"] == "Yes"]
    
    # Check if we have any included articles
    if len(included_df) == 0:
        print("No articles with GlobalInclusion = 'Yes' found")
        sys.exit(0)
    
    # Extract DOIs and filter out empty/missing values
    dois = included_df["DOI"].dropna().tolist()
    valid_dois = [doi for doi in dois if doi and isinstance(doi, str) and doi.strip()]
    
    # Report the number of DOIs
    print(f"Found {len(valid_dois)} valid DOIs to download")
    
    if len(valid_dois) == 0:
        print("No valid DOIs found for included articles")
        sys.exit(0)
    
    # Create a temporary file to store the DOIs
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
        temp_file_path = temp_file.name
        for doi in valid_dois:
            temp_file.write(f"{doi.strip()}\n")
    
    try:
        # Construct the PyPaperBot command
        # Use sys.executable to ensure we use the same Python interpreter
        command = [
            sys.executable, "-m", "PyPaperBot",
            f"--doi-file={temp_file_path}",
            f"--dwn-dir={download_dir}"
        ]
        
        # Run the command
        print("Starting download with PyPaperBot...")
        print(f"Command: {' '.join(command)}")
        
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running PyPaperBot: {e}")
            error_output = str(e)
            
            # Look for specific errors in the output
            if "ModuleNotFoundError" in error_output and "undetected_chromedriver" in error_output:
                print("Missing dependency: undetected_chromedriver. Attempting to install...")
                if install_package("undetected-chromedriver"):
                    print("Successfully installed undetected-chromedriver. Trying again...")
                    try:
                        subprocess.run(command, check=True)
                        print(f"Download completed. Articles saved to: {download_dir}")
                        return
                    except subprocess.CalledProcessError:
                        pass
            
            print("\nTroubleshooting steps:")
            print("1. Install these dependencies manually:")
            print("   pip install requests beautifulsoup4 pandas numpy selenium undetected-chromedriver")
            print("2. If you're behind a proxy, set the appropriate environment variables")
            print("3. Check if you can access the DOIs in a web browser")
            print("4. Try running PyPaperBot manually from the command line")
            
            sys.exit(1)
        
        print(f"Download completed. Articles saved to: {download_dir}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error running PyPaperBot: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()