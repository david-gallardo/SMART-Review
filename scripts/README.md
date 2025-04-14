# Scripts Directory

This directory contains the Python scripts that power the SMART-Review system.

## Key Scripts

- `main.py`: The main entry point for running the article screening and classification
- `download_articles.py`: Downloads PDF articles based on DOIs from included studies
- `check_download.py`: Checks for missing articles and provides download options
- `classification_analysis.py`: Analyzes and classifies included articles
- `article_summarizer.py`: Generates structured summaries from PDFs
- `batch_processor.py`: Handles batch processing of multiple articles
- `pdf_extraction_utils.py`: Tools for extracting and processing PDF text

## Subdirectories

- `analysis/`: Scripts focused on data analysis and visualization
- `utilities/`: Contains crucial configuration files:
  - `inclusion_criteria.txt`: Criteria for including articles
  - `exclusion_criteria.txt`: Criteria for excluding articles
  - `research_question.txt`: The main research question being addressed

## Usage

1. Run initial screening:
python scripts/main.py

2. Download included articles:
python scripts/download_articles.py

3. Analyze and classify:
python scripts/classification_analysis.py

4. Generate summaries:
python scripts/article_summarizer.py

5. Batch process multiple articles:
python scripts/batch_processor.py