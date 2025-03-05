#!/usr/bin/env python
"""
Check Missing Articles Script

This script checks which DOIs from the included articles haven't been downloaded
and provides options to download them manually.

Usage:
    python check_missing_articles.py

Requirements:
    - pandas
    - openpyxl
"""

import os
import pandas as pd
import sys
import subprocess
import tempfile

def main():
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)  # Go up one level to get base directory
    
    # Input Excel file path
    data_path = os.path.join(base_dir, "data", "df_articles_results_classified.xlsx")
    
    # Download directory for articles
    download_dir = os.path.join(base_dir, "documents", "articles")
    
    # Check if the input file exists
    if not os.path.exists(data_path):
        print(f"Error: Input file not found: {data_path}")
        sys.exit(1)
    
    # Check if the download directory exists
    if not os.path.exists(download_dir):
        print(f"Creating download directory: {download_dir}")
        os.makedirs(download_dir, exist_ok=True)
    
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
    total_dois = len(valid_dois)
    print(f"Found {total_dois} valid DOIs to check")
    
    if total_dois == 0:
        print("No valid DOIs found for included articles")
        sys.exit(0)
    
    # Create a mapping from DOI to title for all articles
    doi_to_title = {}
    for _, row in included_df.iterrows():
        if pd.notna(row['DOI']) and pd.notna(row['Article Title']):
            doi_to_title[row['DOI']] = row['Article Title']
    
    # Initialize lists for successful and failed DOIs
    successful = []
    failed = []
    
    # Read from result.csv file to determine which articles have been downloaded
    result_csv_path = os.path.join(download_dir, "result.csv")
    print(f"Reading PyPaperBot result.csv file at: {result_csv_path}")
    
    # Load the results CSV
    results_df = pd.read_csv(result_csv_path)
    
    # Filter for failed downloads
    failed_downloads = results_df[results_df['Downloaded'] == False]
    
    # Extract DOIs of failed downloads
    failed_dois = failed_downloads['DOI'].tolist()
    
    # Filter for DOIs that we care about (from our included articles)
    failed = [doi for doi in failed_dois if doi in valid_dois]
    
    # Calculate successful downloads
    successful = [doi for doi in valid_dois if doi not in failed]
    
    print(f"Based on result.csv: {len(successful)} downloaded, {len(failed)} failed")
    
    # Note: We're using only the result.csv file as requested, no filename detection
    
    # Print results
    print(f"\nFound {len(successful)} downloaded articles and {len(failed)} missing articles")
    
    if not failed:
        print("\nAll articles have been successfully downloaded!")
        sys.exit(0)
    
    # Print missing DOIs
    print("\n" + "="*80)
    print(f"The following {len(failed)} DOIs could not be found in the download directory:")
    print("="*80)
    
    for i, doi in enumerate(failed, 1):
        print(f"{i}. {doi}")
    
    # Generate commands for individual downloads
    print("\nTo download these DOIs individually, use the following commands:")
    print("="*80)
    
    for doi in failed:
        command = f'python -m PyPaperBot --doi="{doi}" --dwn-dir="{download_dir}" --use-doi-as-filename'
        print(command)
    
    print("="*80)
    
    # Create a batch file for Windows users in the current directory
    batch_file_path = os.path.join(script_dir, "download_remaining_articles.bat")
    with open(batch_file_path, "w") as batch_file:
        batch_file.write("@echo off\n")
        batch_file.write("echo Starting download of remaining articles...\n")
        
        for doi in failed:
            command = f'python -m PyPaperBot --doi="{doi}" --dwn-dir="{download_dir}" --use-doi-as-filename'
            batch_file.write(f"{command}\n")
            batch_file.write("echo.\n")  # Empty line
            
        batch_file.write("echo All downloads completed.\n")
        batch_file.write("pause\n")
        
    print(f"\nA batch file has been created at: {batch_file_path}")
    print("You can run this file to attempt to download all remaining articles.")
    
    # Also create a text file with just the DOIs in the current directory
    doi_file_path = os.path.join(script_dir, "remaining_dois.txt")
    with open(doi_file_path, "w") as doi_file:
        for doi in failed:
            doi_file.write(f"{doi}\n")
            
    print(f"\nA file with the remaining DOIs has been saved to: {doi_file_path}")
    
    # Create a CSV with missing articles info for reference in the current directory
    csv_path = os.path.join(script_dir, "missing_articles.csv")
    
    # Collect information about missing articles
    missing_articles = []
    for doi in failed:
        article_info = {'DOI': doi}
        
        # Find the article row in the dataframe
        article_row = included_df[included_df['DOI'] == doi]
        if not article_row.empty:
            article_info['Title'] = article_row['Article Title'].iloc[0] if 'Article Title' in article_row else ''
            article_info['Authors'] = article_row['Authors'].iloc[0] if 'Authors' in article_row else ''
            
            # Add any additional fields that might be present
            for field in ['Journal', 'Year']:
                if field in article_row:
                    article_info[field] = article_row[field].iloc[0]
            
            # Check if we have additional info from PyPaperBot's result.csv
            if os.path.exists(result_csv_path):
                results_df = pd.read_csv(result_csv_path)
                paper_row = results_df[results_df['DOI'] == doi]
                if not paper_row.empty:
                    for field in ['Scholar Link', 'Scholar page', 'Downloaded from']:
                        if field in paper_row:
                            article_info[field] = paper_row[field].iloc[0]
        
        missing_articles.append(article_info)
    
    # Save to CSV
    missing_df = pd.DataFrame(missing_articles)
    missing_df.to_csv(csv_path, index=False)
    print(f"\nA CSV file with details of missing articles has been saved to: {csv_path}")
            
    # Ask if user wants to attempt downloading these DOIs now
    while True:
        choice = input("\nWould you like to attempt downloading the missing articles now? (y/n): ").lower()
        if choice in ['y', 'yes']:
            try_download(failed, download_dir)
            break
        elif choice in ['n', 'no']:
            print("Exiting without downloading. You can run the batch file later to download the articles.")
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

def try_download(dois, download_dir):
    """
    Try to download articles for the given DOIs
    
    Args:
        dois (list): List of DOIs to download
        download_dir (str): Directory to save the downloaded articles
    """
    print(f"\nAttempting to download {len(dois)} articles...")
    
    # Create a temporary file with DOIs
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
        temp_file_path = temp_file.name
        for doi in dois:
            temp_file.write(f"{doi.strip()}\n")
    
    try:
        # Construct the PyPaperBot command
        command = [
            sys.executable, "-m", "PyPaperBot",
            f"--doi-file={temp_file_path}",
            f"--dwn-dir={download_dir}",
            "--use-doi-as-filename"
        ]
        
        # Run the command
        print("Starting download with PyPaperBot...")
        print(f"Command: {' '.join(command)}")
        
        subprocess.run(command, check=True)
        print(f"Download completed. Articles saved to: {download_dir}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error running PyPaperBot: {e}")
        print("\nYou can try downloading the articles individually using the commands printed above.")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()