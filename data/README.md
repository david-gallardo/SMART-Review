# Data Directory

This directory contains the datasets used and produced by the SMART-Review project.

## Contents

- `raw/`: Original datasets before processing
  - Contains the initial Excel files with article metadata that need to be screened
  - These are the starting point for the systematic review process
  
- **Key Files**:
  - `full_data.xlsx`: The initial complete dataset of articles to be screened
  - `df_articles_results.xlsx`: Results after initial screening with LLMs
  - `df_articles_results_classified.xlsx`: Detailed classification of included articles
  - `included_articles_classified.xlsx`: Dataset containing only the included articles
  - `included_articles_classified_MAPPED.xlsx`: Articles with standardized category mappings

## Data Flow

1. Start with the raw dataset (`full_data.xlsx`)
2. Run inclusion/exclusion screening to produce `df_articles_results.xlsx`
3. Classify included articles to produce `df_articles_results_classified.xlsx`
4. Extract and standardize included articles into `included_articles_classified_MAPPED.xlsx`

This standardized data is then used for downloading the actual PDF articles and performing detailed analysis.