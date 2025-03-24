#!/usr/bin/env python
"""
Setup Script for SMART-Review PDF Article Processing System

This script installs all necessary dependencies and downloads required data
for the SMART-Review system to function properly.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def check_and_install_package(package_name, import_name=None):
    """Check if a package is installed and install it if not."""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✓ {package_name} already installed")
        return True
    except ImportError:
        print(f"Installing {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✓ {package_name} installed successfully")
            return True
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package_name}")
            return False

def setup_nltk_data():
    """Download all necessary NLTK data packages."""
    try:
        import nltk
        
        # List of all NLTK data packages needed
        nltk_packages = [
            'punkt',
            'averaged_perceptron_tagger',
            'stopwords'
        ]
        
        for package in nltk_packages:
            print(f"Checking NLTK data package: {package}")
            try:
                nltk.data.find(f'tokenizers/{package}')
                print(f"✓ NLTK {package} already downloaded")
            except LookupError:
                print(f"Downloading NLTK {package}...")
                nltk.download(package)
                print(f"✓ NLTK {package} downloaded successfully")
        
        # Verify punkt_tab issue (specific to your script)
        try:
            nltk.sent_tokenize("This is a test sentence.")
            print("✓ NLTK sentence tokenization is working correctly")
        except Exception as e:
            print(f"! Warning: NLTK sentence tokenization issue: {e}")
            print("  Applying workaround in pdf_extraction_utils.py...")
            # Apply workaround to pdf_extraction_utils.py
            fix_nltk_tokenization_issue()
        
        return True
    except Exception as e:
        print(f"✗ Error setting up NLTK data: {e}")
        return False

def fix_nltk_tokenization_issue():
    """Update pdf_extraction_utils.py to use a more robust approach to tokenization."""
    script_dir = Path(__file__).parent
    pdf_utils_path = script_dir / "pdf_extraction_utils.py"
    
    if not pdf_utils_path.exists():
        print(f"Cannot find pdf_extraction_utils.py at {pdf_utils_path}")
        return
    
    with open(pdf_utils_path, 'r') as file:
        content = file.read()
    
    # Update the detect_article_structure function to be more robust
    detect_function = """
def detect_article_structure(text):
    \"\"\"
    Detect the structure of an academic article to better target extraction.
    
    Args:
        text (str): The article text
        
    Returns:
        dict: Information about the article structure
    \"\"\"
    # Use simple sentence splitting instead of nltk if needed
    try:
        import nltk
        sentences = nltk.sent_tokenize(text)
        print(f"Using NLTK for sentence tokenization, found {len(sentences)} sentences")
    except Exception as e:
        print(f"Falling back to basic sentence splitting: {e}")
        sentences = text.split('.')
        print(f"Using basic splitting, found {len(sentences)} sentences")
    
    # Detect if abstract is present (more robust pattern)
    has_abstract = bool(re.search(r'\\b(?:Abstract|ABSTRACT)\\b', text[:1000], re.IGNORECASE))
    
    # Check for methods section (more robust pattern)
    has_methods = bool(re.search(r'\\b(?:Methods|Methodology|Materials and Methods|METHODS)\\b', text, re.IGNORECASE))
    
    # Check for typical sections (more robust patterns)
    has_introduction = bool(re.search(r'\\b(?:Introduction|Background|INTRODUCTION)\\b', text, re.IGNORECASE))
    has_results = bool(re.search(r'\\b(?:Results|Findings|RESULTS)\\b', text, re.IGNORECASE))
    has_discussion = bool(re.search(r'\\b(?:Discussion|DISCUSSION)\\b', text, re.IGNORECASE))
    has_conclusion = bool(re.search(r'\\b(?:Conclusion|Conclusions|CONCLUSION|CONCLUSIONS)\\b', text, re.IGNORECASE))
    
    # Estimate article length by number of sentences
    article_length = len(sentences)
    
    # Determine article type based on structure
    article_type = "unknown"
    if has_methods and has_results:
        article_type = "research"
    elif not has_methods and has_introduction and has_conclusion:
        article_type = "review"
    
    return {
        "has_abstract": has_abstract,
        "has_introduction": has_introduction,
        "has_methods": has_methods,
        "has_results": has_results,
        "has_discussion": has_discussion,
        "has_conclusion": has_conclusion,
        "article_length": article_length,
        "article_type": article_type
    }
"""
    
    # Replace the old function with the new one
    # This is a simple replacement strategy - could be more sophisticated
    if "def detect_article_structure" in content:
        start_pos = content.find("def detect_article_structure")
        # Find the end of the function by looking for the next def or the end of the file
        next_def_pos = content.find("def ", start_pos + 10)
        if next_def_pos == -1:
            # No next function, replace to the end of the file
            updated_content = content[:start_pos] + detect_function
        else:
            # Replace just this function
            updated_content = content[:start_pos] + detect_function + content[next_def_pos:]
        
        with open(pdf_utils_path, 'w') as file:
            file.write(updated_content)
        print("✓ Updated pdf_extraction_utils.py with more robust tokenization")
    else:
        print("! Could not locate detect_article_structure function in pdf_extraction_utils.py")

def setup_directories():
    """Create necessary directories if they don't exist."""
    base_dir = Path(__file__).parent.parent
    
    dirs_to_create = [
        base_dir / "data",
        base_dir / "documents" / "articles",
        base_dir / "output" / "summaries",
        base_dir / "prompts"
    ]
    
    for directory in dirs_to_create:
        if not directory.exists():
            print(f"Creating directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
    
    print("✓ Directory structure set up successfully")

def main():
    """Main setup function."""
    print("\n====== SMART-Review PDF Article Processing System Setup ======\n")
    
    # Required packages with their import names
    required_packages = [
        ("pandas", "pandas"),
        ("PyPDF2", "PyPDF2"),
        ("python-docx", "docx"),
        ("requests", "requests"),
        ("nltk", "nltk"),
        ("pyyaml", "yaml"),
        ("tqdm", "tqdm")
    ]
    
    all_packages_installed = True
    for package, import_name in required_packages:
        if not check_and_install_package(package, import_name):
            all_packages_installed = False
    
    if not all_packages_installed:
        print("\n! Some packages could not be installed. Please install them manually.")
    
    nltk_setup_successful = setup_nltk_data()
    
    # Set up directory structure
    setup_directories()
    
    print("\n====== Setup Complete ======\n")
    
    if all_packages_installed and nltk_setup_successful:
        print("All dependencies are installed and the system is ready to use!")
        print("\nTo start processing articles, run:")
        print("  python article_summarizer.py --test")
        print("\nFor batch processing, run:")
        print("  python batch_processor.py")
    else:
        print("Setup completed with some issues. Please resolve them before running the system.")

if __name__ == "__main__":
    main()