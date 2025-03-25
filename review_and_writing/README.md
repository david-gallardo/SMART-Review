# PDF Article Processing Module for SMART-Review

This module provides a comprehensive system for extracting, analyzing, and summarizing scientific articles in PDF format using Large Language Models (LLMs). It's specifically designed to support systematic reviews of research on employment interventions for people with mental health disorders, but can be adapted for other research domains.

## Key Features

- Advanced PDF text extraction with specialized handling for scientific documents
- Flexible section-by-section analysis using domain-specific LLM prompts
- Support for different article types and study designs (RCTs, quasi-experimental, systematic reviews)
- Multiple processing modes (parallel, sequential, monitored) for optimal resource utilization
- Automatic generation of individual article summaries and combined review documents
- Customizable prompt management system for different research contexts
- Robust error handling and recovery mechanisms

## Components

### 1. Article Summarizer (`article_summarizer.py`)

The core component that processes individual articles with section-by-section analysis.

**Usage:**
```bash
python article_summarizer.py [--test] [--article_id ARTICLE_ID] [--model MODEL_NAME] [--api_url URL]
```

**Options:**
- `--test` - Process only one PDF file for testing
- `--article_id ID` - Process only the article with the specified ID
- `--model MODEL_NAME` - Specify the LLM model to use (default: mistral-small-24b-instruct-2501)
- `--api_url URL` - Custom LLM API URL
- `--articles_dir DIR` - Directory containing PDF articles
- `--output_dir DIR` - Directory for output files
- `--prompts_dir DIR` - Directory containing custom prompt templates

### 2. Batch Processor (`batch_processor.py`)

Unified solution for batch processing with multiple modes of operation.

**Usage:**
```bash
python batch_processor.py [--mode {parallel,sequential,monitored}] [OPTIONS]
```

**Processing Modes:**
- `parallel` - Process multiple articles simultaneously (default)
- `sequential` - Process articles one at a time
- `monitored` - Process articles with continuous server monitoring and auto-recovery

**Common Options:**
- `--batch_size N` - Number of articles per batch (default: 10)
- `--model MODEL_NAME` - LLM model to use (default: mistral-small-24b-instruct-2501)
- `--api_url URL` - Custom LLM API URL
- `--output_dir DIR` - Directory for output files
- `--articles_dir DIR` - Directory containing PDF articles
- `--resume` - Resume from last processed batch and article
- `--output FILENAME` - Name of the combined output file (default: combined_summary.docx)
- `--prompts_dir DIR` - Directory containing custom prompt templates

**Mode-Specific Options:**
- Parallel mode: `--parallel N` - Number of articles to process in parallel (default: 2)
- Sequential mode: `--timeout N` - Timeout for processing a single article (seconds, default: 1800)
- Monitored mode: 
  - `--check_interval N` - How often to check server status (seconds, default: 60)
  - `--retry_limit N` - Maximum number of retries before giving up (default: 5)

### 3. Advanced Prompt Manager (`advanced_prompt_manager.py`)

Manages specialized prompts for different article sections, study designs, and research contexts.

- Includes default prompts for common article sections (background, methods, results, etc.)
- Specialized prompts for different study designs (RCTs, quasi-experimental, systematic reviews)
- Context-aware prompts for specific mental health conditions and intervention types
- Support for custom prompt loading from YAML or JSON files

### 4. PDF Extraction Utilities (`pdf_extraction_utils.py`)

Specialized tools for extracting and cleaning text from scientific PDFs.

- Multiple extraction strategies for optimal text quality
- Scientific text cleaning and normalization
- Article structure detection
- Section identification and extraction
- Abstract extraction and metadata handling

### 5. Summary Template Generator (`create_summary_template.py`)

Creates document templates for the final systematic review.

**Usage:**
```bash
python create_summary_template.py [--output OUTPUT_FILE]
```

### 6. Setup Script (`setup.py`)

Handles installation of dependencies and preparation of the environment.

**Usage:**
```bash
python setup.py
```

## Getting Started

### Installation

1. Clone the repository and navigate to the project directory
2. Run the setup script to install dependencies:
   ```bash
   python setup.py
   ```

### Basic Usage

1. Place PDF articles in the `documents/articles/` directory
2. For a single article test:
   ```bash
   python article_summarizer.py --test
   ```
3. For batch processing with default settings:
   ```bash
   python batch_processor.py
   ```
4. Check output summaries in the `output/summaries/` directory

### Advanced Usage

#### Processing Large Collections

For large collections of PDFs (50+ files), use batch processing with appropriate settings:

```bash
# Process in monitored mode with custom batch size
python batch_processor.py --mode monitored --batch_size 20 --parallel 4

# Resume a previously interrupted processing run
python batch_processor.py --resume --mode sequential

# Process with a specific LLM model
python batch_processor.py --model "llama-3-70b-chat" --api_url "http://your-api-server:1234/v1/chat/completions"
```

#### Using Custom Prompts

Create custom prompts in the `prompts/` directory using YAML or JSON format:

```yaml
# custom_prompts.yaml
background: |
  You're an expert research assistant analyzing scientific articles on [DOMAIN].
  
  Extract and summarize the key background information from this article, including:
  1. The research problem being addressed
  2. Previous research on this topic and existing knowledge gaps
  3. The theoretical framework or model used, if any
  4. The significance and rationale for the study
  
  Focus only on the background information. Provide a well-structured summary (300-400 words).
```

Then use the custom prompts directory:

```bash
python batch_processor.py --prompts_dir "path/to/custom/prompts"
```

## System Requirements

- Python 3.8+
- Dependencies (installed by setup.py):
  - pandas
  - PyPDF2
  - python-docx
  - requests
  - nltk
  - pyyaml
  - tqdm
- Access to an LLM API server (local or remote)

## LLM API Configuration

The system is designed to work with a local or remote LLM API server that follows the OpenAI-compatible API format. By default, it connects to `http://127.0.0.1:1234/v1/chat/completions`.

You can specify a different API URL using the `--api_url` parameter with any of the scripts.

## Troubleshooting

### Common Issues

1. **PDF Extraction Problems**
   - Check that PDFs are properly formatted and readable
   - For problematic PDFs, try preprocessing with OCR software

2. **LLM API Connection Issues**
   - Verify the API server is running and accessible
   - Check network connectivity and firewall settings
   - Use the monitored mode for better resilience to API issues

3. **Memory Errors**
   - Reduce the number of parallel processes
   - Decrease batch size
   - Process articles sequentially

4. **Missing Dependencies**
   - Run `python setup.py` to install required packages
   - Check the error messages for specific missing packages

### Log Files

Check the log files for detailed error information:
- `batch_processor.log` - Contains detailed processing logs
- `batch_processing_state.json` - Contains current processing state information

## Extending the System

### Adding New Prompt Types

Modify `advanced_prompt_manager.py` to add new specialized prompts for different article types, study designs, or research domains.

### Customizing Output Formats

The system generates DOCX files by default. Modify the `create_word_document` function in `article_summarizer.py` to customize the output format or add support for additional formats.

### Integrating with Other Analysis Tools

The batch processor is designed to be modular. You can extend it to integrate with other analysis tools or databases by modifying the appropriate processing functions.