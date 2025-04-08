# PDF Article Processing Module for SMART-Review

This directory contains the article processing and summarization module for the SMART-Review system. This module specializes in extracting, analyzing, and summarizing scientific articles in PDF format using Large Language Models (LLMs), specifically focused on employment interventions for people with mental health disorders.

## Module Purpose

The `review_and_writing` module handles:

1. Extracting text from PDF research articles
2. Analyzing article content section by section
3. Generating structured summaries using LLMs
4. Compiling individual summaries into comprehensive review documents
5. Supporting both individual and batch article processing

## Components

### 1. Article Summarizer (`article_summarizer.py`)

Processes individual articles with section-by-section analysis.

**Usage:**
```bash
python article_summarizer.py [--test] [--article_id ARTICLE_ID] [--model MODEL_NAME]
```

**Options:**
- `--test` - Process only one PDF file for testing
- `--article_id ID` - Process only the article with the specified ID
- `--model MODEL_NAME` - Specify the LLM model to use

### 2. Batch Processor (`batch_processor.py`)

Process multiple articles in parallel and compile results.

**Usage:**
```bash
python batch_processor.py [--parallel N] [--output OUTPUT_FILE] [--model MODEL_NAME]
```

**Options:**
- `--parallel N` - Number of articles to process in parallel (default: 2)
- `--output OUTPUT_FILE` - Name of the output file (default: combined_summary.docx)
- `--model MODEL_NAME` - Specify the LLM model to use

### 3. Advanced Prompt Manager (`advanced_prompt_manager.py`)

Manages specialized prompts for different section types and research contexts.

### 4. PDF Extraction Utilities (`pdf_extraction_utils.py`)

Specialized tools for extracting and cleaning text from scientific PDFs.

### 5. Combined Summary Template Generator (`create_summary_template.py`)

Creates document templates for the final systematic review.

## Usage Within SMART-Review

This module is designed to be used as part of the SMART-Review workflow. Typically, this module is used after articles have been collected and filtered through the systematic review process:

1. Place PDF articles in the `documents/articles/` directory relative to the parent SMART-Review project
2. Run either individual article processing or batch processing
3. Review generated summaries in the `output/summaries/` directory

### Example Workflow

```bash
# Process a batch of 4 articles in parallel
python batch_processor.py --parallel 4 --model "mistral-small-24b-instruct-2501"

# Generate a template for the final review
python create_summary_template.py
```

## Configuring the Module

### LLM API Configuration

By default, the scripts use a local LLM API server running on port 1234. You can specify a different API URL using the `--api_url` parameter with any of the scripts.

### Custom Prompts

Create custom prompts in the `prompts/` directory using YAML or JSON format. These can specialize the analysis for specific article types, mental health conditions, or intervention types.

## Dependencies

This module requires:
- Python 3.8+
- pandas
- PyPDF2
- python-docx
- requests
- nltk
- pyyaml
- tqdm

These are typically installed as part of the main SMART-Review setup process.

## Troubleshooting

If you encounter issues:

1. Check that PDFs are properly placed in the expected directory
2. Verify the LLM API server is running and accessible
3. For memory errors, reduce the number of parallel processes
4. Consult the `batch_processor.log` file for detailed error information

## Integration with Other SMART-Review Modules

This module works with other SMART-Review components:
- Takes input from the article collection and screening modules
- Provides output for the synthesis and report generation phases
- Uses the same data structures for maintaining article metadata