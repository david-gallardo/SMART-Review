# Documents Directory

This directory contains documentation and files related to the articles analyzed in the systematic review.

## Contents

- `articles/`: Directory containing PDF files of the included articles
  - This directory is populated by running the download scripts

- `README.md`: This file

- `collect_papers.py`: Python script for collecting research papers
  
- `download_remaining_articles.bat`: Batch file to download articles that failed during initial download
  
- `missing_articles.csv`: CSV file listing articles that couldn't be downloaded

- `remaining_dois.txt`: Text file containing DOIs of articles that still need to be downloaded

## Usage

The main workflow for article management:

1. Articles are initially downloaded using `collect_papers.py` or via the main download script in the scripts directory

2. If some articles fail to download, they are listed in `missing_articles.csv` and their DOIs are recorded in `remaining_dois.txt`

3. The `download_remaining_articles.bat` batch file can be run to attempt to download these remaining articles

The PDFs in the `articles/` directory are then processed by the text extraction and analysis tools in the `scripts/` directory.