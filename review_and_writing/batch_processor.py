#!/usr/bin/env python
"""
Unified Batch PDF Article Processor

This script provides a comprehensive solution for batch processing PDF articles
with different processing modes, resilient error handling, and monitoring capabilities.

Usage:
    python batch_processor.py [options]

Processing Modes:
    --mode {parallel,sequential,monitored}   Processing mode (default: parallel)

Common Options:
    --batch_size N          Number of articles per batch (default: 10)
    --model MODEL_NAME      LLM model to use for analysis (default: mistral-small-24b-instruct-2501)
    --api_url URL           Custom LLM API URL (default: http://127.0.0.1:1234/v1/chat/completions)
    --output_dir DIR        Directory for storing output files (default: output/summaries)
    --articles_dir DIR      Directory containing PDF articles (default: documents/articles)
    --resume                Resume from last processed batch and article
    --start_batch N         Start processing from a specific batch number
    --start_article N       Start processing from a specific article number

Parallel Mode Options:
    --parallel N            Number of articles to process in parallel (default: 2)

Sequential Mode Options:
    --timeout N             Timeout for processing a single article (seconds, default: 1800)

Monitored Mode Options:
    --check_interval N      How often to check server status (seconds, default: 60)
    --retry_limit N         Maximum number of retries before giving up (default: 5)
"""

import os
import sys
import argparse
import json
import re
import pandas as pd
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import requests
import concurrent.futures
import subprocess
import time
import logging
import glob
import shutil
import signal
import traceback
from datetime import datetime
from pathlib import Path

# Import from other modules
from advanced_prompt_manager import PromptManager
from pdf_extraction_utils import (
    improve_pdf_extraction,
    clean_scientific_text,
    detect_article_structure
)

from article_summarizer import (
    process_all_sections,
    create_word_document
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# State file to keep track of processing progress
STATE_FILE = "batch_processing_state.json"

# Global variables for monitored mode
monitor_running = True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Unified batch processor for PDF articles')
    
    # Processing mode
    parser.add_argument('--mode', type=str, choices=['parallel', 'sequential', 'monitored'],
                        default='parallel', help='Processing mode')
    
    # Common options
    parser.add_argument('--batch_size', type=int, default=10,
                        help='Number of articles per batch')
    parser.add_argument('--model', type=str, default='mistral-small-24b-instruct-2501',
                        help='LLM model to use for analysis')
    parser.add_argument('--api_url', type=str, 
                        default='http://127.0.0.1:1234/v1/chat/completions',
                        help='Custom LLM API URL')
    parser.add_argument('--output_dir', type=str,
                        help='Directory for storing output files')
    parser.add_argument('--articles_dir', type=str,
                        help='Directory containing PDF articles')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last processed batch and article')
    parser.add_argument('--start_batch', type=int, 
                        help='Start processing from this batch number')
    parser.add_argument('--start_article', type=int,
                        help='Start processing from this article number')
    parser.add_argument('--prompts_dir', type=str, 
                        help='Directory containing custom prompt templates')
    
    # Parallel mode options
    parser.add_argument('--parallel', type=int, default=2,
                        help='Number of articles to process in parallel')
    
    # Sequential mode options
    parser.add_argument('--timeout', type=int, default=1800,
                        help='Timeout for processing a single article (seconds)')
    
    # Monitored mode options
    parser.add_argument('--check_interval', type=int, default=60,
                        help='How often to check server status (seconds)')
    parser.add_argument('--retry_limit', type=int, default=5,
                        help='Maximum number of retries before giving up')
    
    # Output file for combined summary
    parser.add_argument('--output', type=str, default='combined_summary.docx',
                        help='Name of the combined output file')
    
    return parser.parse_args()

def setup_directories(args):
    """Set up the necessary directories for the script."""
    # Get the current directory as the base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Use command-line arguments if provided, otherwise use default paths
    data_dir = os.path.join(base_dir, 'data')
    articles_dir = args.articles_dir or os.path.join(base_dir, 'documents', 'articles')
    output_dir = args.output_dir or os.path.join(base_dir, 'output', 'summaries')
    prompts_dir = args.prompts_dir or os.path.join(base_dir, 'prompts')
    
    # Create directories if they don't exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(articles_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(prompts_dir, exist_ok=True)
    
    return base_dir, data_dir, articles_dir, output_dir, prompts_dir

def load_article_metadata(data_dir):
    """Load metadata for the included articles."""
    try:
        # Try to load from the classified file first
        classified_file = os.path.join(data_dir, 'df_articles_results_classified.xlsx')
        if os.path.exists(classified_file):
            df = pd.read_excel(classified_file)
            included_df = df[df['GlobalInclusion'] == 'Yes'].copy()
            logger.info(f"Loaded {len(included_df)} included articles from classification data.")
            return included_df
        
        # If not found, try the basic results file
        results_file = os.path.join(data_dir, 'df_articles_results.xlsx')
        if os.path.exists(results_file):
            df = pd.read_excel(results_file)
            included_df = df[df['GlobalInclusion'] == 'Yes'].copy()
            logger.info(f"Loaded {len(included_df)} included articles from results data.")
            return included_df
        
        logger.info("No article metadata found. Will process PDF files without metadata.")
        return None
    
    except Exception as e:
        logger.error(f"Error loading article metadata: {e}")
        return None

def get_pdf_files(articles_dir, article_id=None):
    """Get list of PDF files to process, optionally filtered by article ID."""
    pdf_files = []
    
    if not os.path.exists(articles_dir):
        logger.error(f"Articles directory not found: {articles_dir}")
        return pdf_files
    
    # If article_id is provided, look for a specific pattern
    if article_id is not None:
        for filename in os.listdir(articles_dir):
            if filename.lower().endswith('.pdf'):
                # Look for article ID in the filename (various formats)
                patterns = [
                    fr'^{article_id}_',  # starts with ID_
                    fr'_{article_id}_',  # contains _ID_
                    fr'_{article_id}\.pdf$',  # ends with _ID.pdf
                    fr'^article_{article_id}',  # starts with article_ID
                ]
                
                if any(re.search(pattern, filename) for pattern in patterns):
                    pdf_files.append(os.path.join(articles_dir, filename))
                    break
    else:
        # Get all PDF files
        pdf_files = [os.path.join(articles_dir, f) for f in os.listdir(articles_dir) 
                   if f.lower().endswith('.pdf')]
    
    return pdf_files

def chunk_files(files, batch_size):
    """Divide the files into batches of the specified size."""
    return [files[i:i + batch_size] for i in range(0, len(files), batch_size)]

def chunk_text(text, max_chunk_length=4000, overlap=500):
    """
    Split the text into overlapping chunks for processing.
    
    Args:
        text (str): The text to chunk
        max_chunk_length (int): Maximum length for each chunk
        overlap (int): How much text should overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    if not text:
        return []
    
    # If text is shorter than max chunk length, return as a single chunk
    if len(text) <= max_chunk_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Calculate end position
        end = min(start + max_chunk_length, len(text))
        
        # If we're not at the end of the text, try to find a good break point
        if end < len(text):
            # Look for paragraph break
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break != -1 and paragraph_break > start + max_chunk_length // 2:
                end = paragraph_break
            else:
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break != -1 and sentence_break > start + max_chunk_length // 2:
                    end = sentence_break + 1  # Include the period
                else:
                    # Last resort: word break
                    word_break = text.rfind(' ', start, end)
                    if word_break != -1 and word_break > start + max_chunk_length // 2:
                        end = word_break
        
        chunks.append(text[start:end].strip())
        
        # Move start position for next chunk, with overlap
        start = max(start + max_chunk_length - overlap, end - overlap)
    
    return chunks

def save_state(state):
    """Save the current processing state to a file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    logger.info(f"Saved state: Batch {state['current_batch']}, Article {state['current_article']}")

def load_state():
    """Load the processing state from a file if it exists."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            
            # Ensure consistent structure of state dictionary
            if 'current_batch' not in state:
                state['current_batch'] = 1
            if 'current_article' not in state:
                state['current_article'] = 1
            if 'completed_batches' not in state:
                state['completed_batches'] = []
            # Ensure completed_articles is always a dictionary
            if 'completed_articles' not in state or not isinstance(state['completed_articles'], dict):
                state['completed_articles'] = {}
            
            logger.info(f"Loaded state: Batch {state['current_batch']}, Article {state['current_article']}")
            return state
        except Exception as e:
            logger.error(f"Error loading state file: {str(e)}")
            logger.info("Creating new state file.")
            return {
                'current_batch': 1, 
                'current_article': 1,
                'completed_batches': [],
                'completed_articles': {}
            }
    
    return {
        'current_batch': 1, 
        'current_article': 1,
        'completed_batches': [],
        'completed_articles': {}
    }

def is_article_processed(article_path, output_dir):
    """Check if an article has already been processed by looking for output files."""
    basename = os.path.splitext(os.path.basename(article_path))[0]
    
    # Look for potential output files with variations of the name
    potential_patterns = [
        f"{basename}_summary.docx",
        f"{basename}_summary.json",
        f"article_*_{basename}_summary.docx",
        f"article_*_{basename}_summary.json"
    ]
    
    for pattern in potential_patterns:
        matching_files = glob.glob(os.path.join(output_dir, pattern))
        if matching_files:
            return True
            
    return False

def save_individual_results(results, output_dir):
    """
    Save individual article processing results to files.
    
    Args:
        results (list): List of article processing results
        output_dir (str): Directory to save the results
    """
    for result in results:
        if not result:
            continue
            
        # Create a unique output filename
        article_id = result.get("article_id")
        if article_id and article_id != "unknown":
            output_filename = f"article_{article_id}_summary.docx"
        else:
            filename = os.path.basename(result.get("filename", "unknown"))
            output_filename = os.path.splitext(filename)[0] + "_summary.docx"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Create Word document
        article_meta = None
        if "metadata" in result:
            # Convert metadata dict to a pandas Series-like object
            from types import SimpleNamespace
            article_meta = SimpleNamespace(**result["metadata"])
            
        create_word_document(result, article_meta, output_path)
        
        # Also save raw JSON results for reference
        json_path = os.path.join(output_dir, os.path.splitext(output_filename)[0] + ".json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

def check_server_status(api_url):
    """Check if the LLM API server is running and responsive."""
    try:
        # Prepare a simple request to test the server
        url = api_url
        request_body = {
            "model": "mistral-small-24b-instruct-2501",
            "messages": [
                {"role": "system", "content": "You are an expert research assistant."},
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 10
        }
        
        response = requests.post(url, json=request_body, headers={"Content-Type": "application/json"}, timeout=5)
        return response.status_code == 200 and "choices" in response.json()
    except requests.exceptions.RequestException:
        return False

# Fix for handling None values and type checking in create_combined_document

def create_combined_document(results, article_metadata, output_path, args, prompt_manager):
    """
    Create a combined document with summaries of all processed articles.
    
    Args:
        results (list): List of article processing results
        article_metadata: Metadata for all articles
        output_path (str): Path to save the combined document
        args: Command line arguments
        prompt_manager: PromptManager instance
    """
    doc = docx.Document()
    
    # Set up document styles
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    
    # Add title
    title = doc.add_heading("Combined Summary of Processed Articles", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add processing info
    doc.add_heading("Processing Information", level=2)
    proc_info = doc.add_paragraph()
    proc_info.add_run(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    proc_info.add_run(f"Model Used: {args.model}\n")
    proc_info.add_run(f"Total Articles Processed: {len(results)}\n")
    
    # Add executive summary using the prompt manager if available
    doc.add_heading("Executive Summary", level=2)
    
    try:
        # Create a combined text from all articles for the summary
        combined_text = ""
        for idx, res in enumerate(results):
            if not res:
                continue
                
            # Safely get metadata and sections
            res_metadata = res.get('metadata', {}) or {}
            res_sections = res.get('sections', {}) or {}
            
            # Get title safely
            title = "Unknown Title"
            if isinstance(res_metadata, dict):
                title = res_metadata.get('title', 'Unknown Title')
            elif hasattr(res_metadata, 'title'):
                title = getattr(res_metadata, 'title', 'Unknown Title')
                
            # Get relevant sections safely
            conclusions = res_sections.get('conclusions', '')
            synthesis = res_sections.get('synthesis', '')
            
            # Add to combined text
            combined_text += f"Article {idx+1} - {title}:\n{conclusions}\n{synthesis}\n\n"
        
        # Get the executive summary prompt
        exec_summary_prompt = prompt_manager.get_prompt("executive_summary")
        
        # Query the LLM for an executive summary
        success, exec_summary = robust_llm_call(args.model, exec_summary_prompt, combined_text, args.api_url)
        
        if success:
            doc.add_paragraph(exec_summary)
        else:
            doc.add_paragraph(f"Error generating executive summary: {exec_summary}")
    except Exception as e:
        logger.error(f"Error generating executive summary: {str(e)}")
        doc.add_paragraph("Executive summary generation failed. Please review individual summaries.")
    
    # Add individual article summaries
    doc.add_heading("Individual Article Summaries", level=2)
    
    for idx, result in enumerate(results):
        if not result:
            continue
            
        # Get article metadata safely
        title = "Unknown Title"
        authors = "Unknown Authors"
        
        # Safely get metadata
        if result.get("metadata"):
            metadata = result.get("metadata")
            
            # Handle different metadata formats
            if isinstance(metadata, dict):
                title = metadata.get('title', f"Article {idx+1}")
                authors = metadata.get('authors', 'Unknown Authors')
            else:
                # Try to access as object attributes
                try:
                    title = getattr(metadata, 'title', f"Article {idx+1}")
                    authors = getattr(metadata, 'authors', 'Unknown Authors')
                except:
                    title = f"Article {idx+1}"
                    authors = 'Unknown Authors'
        
        doc.add_heading(f"{idx+1}. {title}", level=3)
        
        # Add metadata
        meta_para = doc.add_paragraph()
        meta_para.add_run(f"Authors: {authors}\n")
        
        # Safely handle metadata in different formats
        if "metadata" in result:
            metadata = result["metadata"]
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    if key not in ["title", "authors"]:
                        meta_para.add_run(f"{key.replace('_', ' ').title()}: {value}\n")
            else:
                # Try to iterate over object attributes
                try:
                    for key in dir(metadata):
                        if not key.startswith('_') and key not in ["title", "authors"]:
                            value = getattr(metadata, key)
                            meta_para.add_run(f"{key.replace('_', ' ').title()}: {value}\n")
                except:
                    meta_para.add_run("Additional metadata not available\n")
        
        # Add summary sections safely
        if "sections" in result and result["sections"]:
            sections = result["sections"]
            for section_name, section_title in [
                ("background", "Background"),
                ("methods", "Methods"),
                ("results", "Results"),
                ("discussion", "Discussion"),
                ("conclusions", "Conclusions")
            ]:
                if section_name in sections and sections[section_name]:
                    doc.add_heading(section_title, level=4)
                    section_text = sections[section_name]
                    # Limit section text to keep document manageable
                    if len(section_text) > 500:
                        section_text = section_text[:500] + "... (see individual summary for full text)"
                    doc.add_paragraph(section_text)
        
        # Add a page break between articles
        doc.add_page_break()
    
    # Save the document
    try:
        doc.save(output_path)
        logger.info(f"Combined document saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving combined document: {str(e)}")
        # Try to save to a different location
        backup_path = os.path.join(os.path.dirname(output_path), f"backup_{os.path.basename(output_path)}")
        try:
            doc.save(backup_path)
            logger.info(f"Combined document saved to backup location: {backup_path}")
        except:
            logger.error("Failed to save combined document even to backup location")

# =====================================
# Parallel Processing Mode Functions
# =====================================

def run_parallel_mode(args, pdf_files, article_metadata, prompt_manager, output_dir):
    """Run processing in parallel mode."""
    logger.info(f"Running in parallel mode with {args.parallel} workers")
    
    # Load state for resuming if needed
    state = load_state()
    
    # Use ThreadPoolExecutor instead of ProcessPoolExecutor
    # This avoids module re-importing issues while still providing parallelism
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        all_results = []
        futures = []
        
        # Submit all tasks to the executor
        for i, pdf_file in enumerate(pdf_files):
            # Skip files that should be skipped based on resume state
            article_id = f"article_{i+1}"
            if args.resume and article_id in state.get('completed_articles', {}):
                logger.info(f"Skipping already processed article {i+1}: {os.path.basename(pdf_file)}")
                continue
            
            # Extract article metadata if available
            article_meta = None
            if article_metadata is not None and i < len(article_metadata):
                article_meta = article_metadata.iloc[i]
            
            # Submit the task to the executor
            future = executor.submit(
                process_single_article,
                pdf_file, args.model, prompt_manager, output_dir, 
                args.api_url, 1800, article_meta, i
            )
            futures.append((future, i, pdf_file))
        
        # Process the results as they complete
        for future, idx, pdf_file in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    all_results.append(result)
                    
                    # Update state
                    state['completed_articles'][f"article_{idx+1}"] = True
                    save_state(state)
                    logger.info(f"Successfully processed article {idx+1}: {os.path.basename(pdf_file)}")
            except Exception as e:
                logger.error(f"Error processing article {idx+1} ({os.path.basename(pdf_file)}): {str(e)}")
                logger.error(traceback.format_exc())
    
    # Save individual results
    logger.info(f"Successfully processed {len(all_results)} articles")
    save_individual_results(all_results, output_dir)
    
    # Create combined document
    if all_results:
        combined_output_path = os.path.join(output_dir, args.output)
        create_combined_document(all_results, article_metadata, combined_output_path, args, prompt_manager)
        logger.info(f"Combined document saved to: {combined_output_path}")
    
    logger.info("Parallel processing complete!")
    return all_results

# =====================================
# Sequential Processing Mode Functions
# =====================================

# Add a robust wrapper for LLM API calls

def robust_llm_call(model_name, prompt, text, api_url, max_retries=3, retry_delay=5):
    """
    Make an LLM API call with robust error handling and retries.
    
    Args:
        model_name (str): The LLM model to use
        prompt (str): The prompt to send
        text (str): The text to analyze
        api_url (str): The API URL
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        tuple: (success, result_or_error_message)
    """
    for attempt in range(max_retries):
        try:
            # Check server status first
            if not check_server_status(api_url):
                logger.warning(f"LLM API server at {api_url} is not responsive (attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
                continue
                
            # Proceed with the query
            from article_summarizer import query_llm
            result = query_llm(model_name, prompt, text, api_url)
            return True, result
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"API request error (attempt {attempt+1}/{max_retries}): {str(e)}")
            time.sleep(retry_delay)
            
        except Exception as e:
            logger.error(f"Unexpected error during LLM query: {str(e)}")
            return False, f"Error: {str(e)}"
    
    return False, "Failed to get response from LLM API after multiple attempts"

def process_single_article(article_path, model_name, prompt_manager, output_dir, api_url=None, timeout=1800, article_meta=None, index=0):
    """
    Process a single PDF article directly
    
    Args:
        article_path (str): Path to the PDF file
        model_name (str): LLM model to use
        prompt_manager (PromptManager): Instance of the prompt manager
        output_dir (str): Directory for output files
        api_url (str, optional): Custom LLM API URL
        timeout (int): Processing timeout in seconds
        article_meta: Article metadata if available
        index (int): Article index
        
    Returns:
        dict: Results of processing or None if failed
    """
    try:
        article_name = os.path.basename(article_path)
        logger.info(f"Processing article: {article_name}")
        
        start_time = time.time()
        
        # Extract text from PDF using improved extraction
        pdf_text = improve_pdf_extraction(article_path)
        if pdf_text is None:
            logger.warning(f"Text extraction failed for {article_name}")
            return None
        
        # Detect article structure
        article_structure = detect_article_structure(pdf_text)
        logger.info(f"Detected article type for {article_name}: {article_structure['article_type']}")
        
        # Clean the text
        clean_pdf_text = clean_scientific_text(pdf_text)
        if not clean_pdf_text:
            logger.warning(f"No usable text after cleaning for {article_name}")
            return None
        
        # Prepare article info for specialized prompts
        article_info = {}
        article_id = index + 1
        
        # Determine study design based on detected structure
        if article_structure['article_type'] == 'research':
            if article_structure.get('has_methods', False) and article_structure.get('has_results', False):
                article_info['study_design'] = 'quasi_experimental'
        elif article_structure['article_type'] == 'review':
            article_info['study_design'] = 'systematic_review'
        
        # Handle metadata in different formats
        metadata_dict = {}
        if article_meta is not None:
            try:
                # Handle pandas Series
                if hasattr(article_meta, 'to_dict'):
                    metadata_dict = article_meta.to_dict()
                # Handle SimpleNamespace
                elif hasattr(article_meta, '__dict__'):
                    metadata_dict = article_meta.__dict__
                # Handle dict
                elif isinstance(article_meta, dict):
                    metadata_dict = article_meta
                
                # Add mental health condition if available in metadata
                if 'Mental Health Condition' in metadata_dict:
                    article_info['mental_health_condition'] = metadata_dict['Mental Health Condition']
                
                # Add intervention type if available in metadata
                if 'Intervention Type' in metadata_dict:
                    article_info['intervention_type'] = metadata_dict['Intervention Type']
                
                # If study design is specified in metadata, use that
                if 'Study Design' in metadata_dict:
                    article_info['study_design'] = metadata_dict['Study Design']
            except Exception as e:
                logger.warning(f"Error processing article metadata: {str(e)}")
        
        # Split text into manageable chunks
        logger.info(f"Splitting text into chunks for efficient processing.")
        text_chunks = chunk_text(clean_pdf_text, max_chunk_length=8000, overlap=1000)
        logger.info(f"Text split into {len(text_chunks)} chunks")
        
        # Initialize results structure
        results = {
            "article_id": article_id,
            "filename": article_path,
            "processing_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": {}
        }
        
        # Get all available sections from the prompt manager
        section_names = prompt_manager.base_prompts.keys()
        
        # Process each section with different chunking strategies
        for section_name in section_names:
            logger.info(f"  Processing section: {section_name}")
            
            # Get the appropriate prompt from the prompt manager
            section_prompt = prompt_manager.get_prompt(section_name, article_info)
            
            # For synthesis, use multiple chunks to get a comprehensive view
            if section_name == "synthesis":
                # If there are many chunks, use a sample of them
                if len(text_chunks) > 3:
                    # Use first, middle and last chunk
                    selected_chunks = [
                        text_chunks[0],
                        text_chunks[len(text_chunks)//2],
                        text_chunks[-1]
                    ]
                    combined_text = "\n\n[...]\n\n".join(selected_chunks)
                else:
                    combined_text = "\n\n".join(text_chunks[:3])  # Use up to first 3 chunks
                    
                success, section_result = robust_llm_call(model_name, section_prompt, combined_text, api_url)
                time.sleep(2)  # Give the API a short break
                
            # For background and introduction sections, prioritize the beginning
            elif section_name in ["background", "introduction"]:
                # Use the first chunk, which typically contains the introduction
                if len(text_chunks) > 0:
                    success, section_result = robust_llm_call(model_name, section_prompt, text_chunks[0], api_url)
                else:
                    success, section_result = False, "No text available for processing"
                time.sleep(1)
                
            # For methods section, use early chunks
            elif section_name == "methods":
                # Methods often appear after introduction
                if len(text_chunks) > 1:
                    # Try to use the second chunk which often contains methods
                    text_to_use = text_chunks[1]
                    if len(text_chunks) > 2:
                        text_to_use += "\n\n[...]\n\n" + text_chunks[2]  # Add third chunk if available
                    success, section_result = robust_llm_call(model_name, section_prompt, text_to_use, api_url)
                elif len(text_chunks) > 0:
                    success, section_result = robust_llm_call(model_name, section_prompt, text_chunks[0], api_url)
                else:
                    success, section_result = False, "No text available for processing"
                time.sleep(1)
                
            # For results and discussion, focus on middle to later chunks
            elif section_name in ["results", "discussion"]:
                # Results and discussion typically appear in the middle to later sections
                if len(text_chunks) > 2:
                    mid_index = len(text_chunks) // 2
                    text_to_use = text_chunks[mid_index]
                    if mid_index + 1 < len(text_chunks):
                        text_to_use += "\n\n[...]\n\n" + text_chunks[mid_index + 1]
                    success, section_result = robust_llm_call(model_name, section_prompt, text_to_use, api_url)
                elif len(text_chunks) > 0:
                    # If only a few chunks, use the last available
                    success, section_result = robust_llm_call(model_name, section_prompt, text_chunks[-1], api_url)
                else:
                    success, section_result = False, "No text available for processing"
                time.sleep(1)
                
            # For conclusions, prioritize the end
            elif section_name == "conclusions":
                # Conclusions are typically at the end
                if len(text_chunks) > 0:
                    success, section_result = robust_llm_call(model_name, section_prompt, text_chunks[-1], api_url)
                else:
                    success, section_result = False, "No text available for processing"
                time.sleep(1)
                
            # For other sections, use a mix of chunks
            else:
                # For other sections, use a representative sampling
                if len(text_chunks) > 3:
                    # Use first, a middle, and last chunk
                    selected_chunks = [
                        text_chunks[0],
                        text_chunks[len(text_chunks)//2],
                        text_chunks[-1]
                    ]
                    combined_text = "\n\n[...]\n\n".join(selected_chunks)
                    success, section_result = robust_llm_call(model_name, section_prompt, combined_text, api_url)
                elif len(text_chunks) > 0:
                    # If only a few chunks, just use them all
                    combined_text = "\n\n".join(text_chunks)
                    success, section_result = robust_llm_call(model_name, section_prompt, combined_text, api_url)
                else:
                    success, section_result = False, "No text available for processing"
                time.sleep(1)
            
            # Store the result
            if success:
                results["sections"][section_name] = section_result
            else:
                results["sections"][section_name] = f"Error processing this section: {section_result}"
                logger.warning(f"Error processing section {section_name}: {section_result}")
        
        # Add metadata to results
        if metadata_dict:
            results["metadata"] = {
                "title": metadata_dict.get("Article Title", "Unknown Title"),
                "authors": metadata_dict.get("Authors", "Unknown Authors"),
                "doi": metadata_dict.get("DOI", "Unknown DOI"),
                "publication_year": metadata_dict.get("Publication Year", "Unknown Year"),
                "journal": metadata_dict.get("Journal", "Unknown Journal"),
                "mental_health_condition": metadata_dict.get("Mental Health Condition", "Unknown"),
                "intervention_type": metadata_dict.get("Intervention Type", "Unknown"),
                "study_design": metadata_dict.get("Study Design", article_info.get("study_design", "Unknown"))
            }
        
        # Add article structure information
        results["article_structure"] = article_structure
        
        # Create a unique output filename
        output_filename = f"article_{article_id}_summary.docx"
        output_path = os.path.join(output_dir, output_filename)
        
        # Convert metadata to format expected by create_word_document
        from types import SimpleNamespace
        article_meta_obj = None
        if "metadata" in results:
            article_meta_obj = SimpleNamespace(**results["metadata"])
        
        # Create Word document
        create_word_document(results, article_meta, output_path)
        
        # Also save raw JSON results for reference
        json_path = os.path.join(output_dir, os.path.splitext(output_filename)[0] + ".json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Successfully processed {article_name} in {time.time() - start_time:.2f} seconds")
        logger.info(f"Output saved to: {output_path}")
        return results
        
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(article_path)}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def run_sequential_mode(args, pdf_files, article_metadata, prompt_manager, output_dir):
    """Run processing in sequential mode."""
    logger.info("Running in sequential mode")
    
    # Load state for resuming if needed
    state = load_state()
    
    # Divide files into batches
    batches = chunk_files(pdf_files, args.batch_size)
    
    # Determine starting point
    start_batch = args.start_batch or (state['current_batch'] if args.resume else 1)
    start_article = args.start_article or (state['current_article'] if args.resume else 1)
    
    # Adjust for zero-indexing
    start_batch_index = start_batch - 1
    
    all_results = []
    
    # Process each batch
    for batch_index, batch_files in enumerate(batches):
        # Skip batches that are before our starting point
        if batch_index < start_batch_index:
            logger.info(f"Skipping Batch {batch_index + 1}/{len(batches)} (before start batch)")
            continue
        
        # Skip batches that are marked as completed
        if batch_index + 1 in state['completed_batches']:
            logger.info(f"Skipping Batch {batch_index + 1}/{len(batches)} (marked as completed)")
            continue
            
        logger.info(f"Starting Batch {batch_index + 1}/{len(batches)} - Processing {len(batch_files)} files")
        
        # Process each article in the batch sequentially
        for article_index, article_path in enumerate(batch_files):
            # Skip articles that are before our starting article in the first batch
            if batch_index == start_batch_index and article_index + 1 < start_article:
                logger.info(f"Skipping article {article_index + 1} (before start article)")
                continue
            
            # Skip already processed articles
            article_id = f"batch{batch_index + 1}_article{article_index + 1}"
            if article_id in state['completed_articles']:
                logger.info(f"Skipping article {article_index + 1} (already completed)")
                continue
            
            # Check if output files already exist
            if is_article_processed(article_path, output_dir):
                logger.info(f"Skipping article {os.path.basename(article_path)} (output files exist)")
                state['completed_articles'][article_id] = True  # Use as dictionary
                save_state(state)
                continue
                
            # Update the state
            state['current_batch'] = batch_index + 1
            state['current_article'] = article_index + 1
            save_state(state)
            
            # Extract article metadata if available
            article_meta = None
            global_index = batch_index * args.batch_size + article_index
            if article_metadata is not None and global_index < len(article_metadata):
                article_meta = article_metadata.iloc[global_index]
            
            # Process the article
            result = process_single_article(
                article_path, 
                args.model,
                prompt_manager,
                output_dir, 
                args.api_url,
                args.timeout,
                article_meta,
                global_index
            )
            
            if result:
                logger.info(f"Article {article_index + 1} in batch {batch_index + 1} processed successfully")
                state['completed_articles'][article_id] = True  # Use as dictionary
                save_state(state)
                all_results.append(result)
            else:
                logger.error(f"Failed to process article {article_index + 1} in batch {batch_index + 1}")
                logger.error("You can resume processing with --resume flag")
                # Don't exit - continue to next article
        
        # Mark the batch as completed
        state['completed_batches'].append(batch_index + 1)
        save_state(state)
    
    # Create combined document if we have results
    if all_results:
        combined_output_path = os.path.join(output_dir, args.output)
        create_combined_document(all_results, article_metadata, combined_output_path, args, prompt_manager)
        logger.info(f"Combined document saved to: {combined_output_path}")
    
    logger.info("Monitored processing complete!")
    return all_results

# =====================================
# Monitored Mode Functions
# =====================================

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully."""
    global monitor_running
    logger.info("Received interrupt signal. Exiting monitor...")
    monitor_running = False

def run_monitored_mode(args, pdf_files, article_metadata, prompt_manager, output_dir):
    """Run processing in monitored mode with automatic restarts."""
    logger.info("Running in monitored mode")
    
    # Register signal handler for graceful exit
    global monitor_running
    monitor_running = True
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initial check of server status
    if not check_server_status(args.api_url):
        logger.error(f"LLM API server at {args.api_url} is not responsive. Please check the server and try again.")
        return []
    
    # Start with sequential processing for better control
    retry_count = 0
    all_results = []
    
    # Use the state file to track progress
    state = load_state()
    
    # Divide files into batches
    batches = chunk_files(pdf_files, args.batch_size)
    
    # Determine starting point
    start_batch = args.start_batch or (state['current_batch'] if args.resume else 1)
    start_article = args.start_article or (state['current_article'] if args.resume else 1)
    
    # Adjust for zero-indexing
    start_batch_index = start_batch - 1
    
    # Process each batch with monitoring
    for batch_index, batch_files in enumerate(batches):
        # Skip batches that are before our starting point
        if batch_index < start_batch_index:
            logger.info(f"Skipping Batch {batch_index + 1}/{len(batches)} (before start batch)")
            continue
        
        # Skip batches that are marked as completed
        if batch_index + 1 in state.get('completed_batches', []):
            logger.info(f"Skipping Batch {batch_index + 1}/{len(batches)} (marked as completed)")
            continue
        
        logger.info(f"Starting Batch {batch_index + 1}/{len(batches)} - Processing {len(batch_files)} files")
        
        # Process each article in the batch with monitoring
        for article_index, article_path in enumerate(batch_files):
            # Exit if monitor is no longer running
            if not monitor_running:
                logger.info("Monitoring stopped. Exiting gracefully.")
                return all_results
            
            # Skip articles that are before our starting article in the first batch
            if batch_index == start_batch_index and article_index + 1 < start_article:
                logger.info(f"Skipping article {article_index + 1} (before start article)")
                continue
            
            # Skip already processed articles
            article_id = f"batch{batch_index + 1}_article{article_index + 1}"
            if article_id in state['completed_articles']:
                logger.info(f"Skipping article {article_index + 1} (already completed)")
                continue
            
            # Check if output files already exist
            if is_article_processed(article_path, output_dir):
                logger.info(f"Skipping article {os.path.basename(article_path)} (output files exist)")
                state['completed_articles'][article_id] = True  # Use as dictionary
                save_state(state)
                continue
            
            # Update the state
            state['current_batch'] = batch_index + 1
            state['current_article'] = article_index + 1
            save_state(state)
            
            # Check server before processing
            if not check_server_status(args.api_url):
                logger.warning("LLM API server is not responsive!")
                retry_count += 1
                
                if retry_count > args.retry_limit:
                    logger.error(f"Exceeded retry limit ({args.retry_limit}). Please check LLM server and restart manually.")
                    return all_results
                
                logger.info(f"Waiting for server to become available (retry {retry_count}/{args.retry_limit})...")
                
                # Wait and check again
                for _ in range(args.check_interval):
                    if not monitor_running:
                        return all_results
                    time.sleep(1)
                
                # Skip to next iteration to check server again
                continue
            
            # Reset retry count if server is responsive
            retry_count = 0
            
            # Extract article metadata if available
            article_meta = None
            global_index = batch_index * args.batch_size + article_index
            if article_metadata is not None and global_index < len(article_metadata):
                article_meta = article_metadata.iloc[global_index]
            
            # Process the article
            result = process_single_article(
                article_path, 
                args.model,
                prompt_manager,
                output_dir, 
                args.api_url,
                args.timeout,
                article_meta,
                global_index
            )
            
            if result:
                logger.info(f"Article {article_index + 1} in batch {batch_index + 1} processed successfully")
                state['completed_articles'][article_id] = True  # Use as dictionary
                save_state(state)
                all_results.append(result)
            else:
                # Check if server is still responsive
                if not check_server_status(args.api_url):
                    logger.warning("LLM API server is not responsive after article processing failed!")
                    logger.info("Will retry this article when server is available again")
                    # Don't increment article counter to retry this one
                    article_index -= 1
                    
                    # Wait before retrying
                    time.sleep(args.check_interval)
                else:
                    logger.error(f"Failed to process article {article_index + 1} in batch {batch_index + 1}, but server is responsive")
                    logger.error("Continuing to next article. You can resume processing with --resume flag.")
            
            # Check server status periodically
            if article_index % 3 == 0:
                logger.info("Performing routine server check...")
                if not check_server_status(args.api_url):
                    logger.warning("Server check failed! Will wait and retry.")
                    # Wait before rechecking
                    time.sleep(args.check_interval)
        
        # Mark the batch as completed
        state['completed_batches'].append(batch_index + 1)
        save_state(state)
    
    # Create combined document if we have results
    if all_results:
        combined_output_path = os.path.join(output_dir, args.output)
        create_combined_document(all_results, article_metadata, combined_output_path, args, prompt_manager)
        logger.info(f"Combined document saved to: {combined_output_path}")
    
    logger.info("Monitored processing complete!")
    return all_results

def main():
    """Main function to batch process multiple articles."""
    args = parse_arguments()
    base_dir, data_dir, articles_dir, output_dir, prompts_dir = setup_directories(args)
    
    # Initialize the prompt manager
    prompt_manager = PromptManager(args.prompts_dir)
    
    # Load article metadata
    article_metadata = load_article_metadata(data_dir)
    
    # Get PDF files to process
    pdf_files = get_pdf_files(articles_dir)
    
    if not pdf_files:
        logger.error("No PDF files found to process.")
        return
    
    # Choose processing mode
    if args.mode == 'parallel':
        all_results = run_parallel_mode(args, pdf_files, article_metadata, prompt_manager, output_dir)
    elif args.mode == 'sequential':
        all_results = run_sequential_mode(args, pdf_files, article_metadata, prompt_manager, output_dir)
    elif args.mode == 'monitored':
        all_results = run_monitored_mode(args, pdf_files, article_metadata, prompt_manager, output_dir)
    else:
        logger.error(f"Unknown processing mode: {args.mode}")
        return
    
    logger.info(f"Processed {len(all_results)} articles successfully")

if __name__ == "__main__":
    main()