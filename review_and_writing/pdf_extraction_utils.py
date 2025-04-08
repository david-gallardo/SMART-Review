#!/usr/bin/env python
"""
PDF Extraction Utilities

Additional utilities for extracting text from PDFs, particularly for handling
scientific articles, which often have complex layouts.

This module supplements the main article_summarizer.py script with more
advanced text extraction capabilities.
"""

import os
import re
import PyPDF2
from io import StringIO
import nltk

# Download required NLTK data (if not already downloaded)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def extract_sections(text):
    """
    Attempt to identify and extract common sections from scientific papers.
    
    Args:
        text (str): The full text of the article
        
    Returns:
        dict: A dictionary with section names and their content
    """
    # Common section headers in scientific papers
    section_patterns = [
        # Background/Introduction
        r'(?i)(introduction|background)[\s]*\n',
        # Methods
        r'(?i)(methods|methodology|materials\s+and\s+methods|study\s+design)[\s]*\n',
        # Results
        r'(?i)(results|findings)[\s]*\n',
        # Discussion
        r'(?i)(discussion)[\s]*\n',
        # Conclusion
        r'(?i)(conclusion|conclusions|concluding\s+remarks)[\s]*\n',
        # References
        r'(?i)(references|bibliography|works\s+cited)[\s]*\n'
    ]
    
    sections = {}
    current_section = "preamble"
    sections[current_section] = []
    
    # Split the text into lines for processing
    lines = text.split('\n')
    
    for line in lines:
        # Check if the line matches any section header
        section_match = False
        for pattern in section_patterns:
            if re.match(pattern, line):
                section_name = re.match(pattern, line).group(1).lower()
                current_section = section_name
                sections[current_section] = []
                section_match = True
                break
        
        if not section_match:
            sections[current_section].append(line)
    
    # Join the lines within each section
    for section in sections:
        sections[section] = '\n'.join(sections[section])
    
    return sections

def improve_pdf_extraction(pdf_path):
    """
    Attempt to extract text from PDF with improved handling of scientific articles.
    Try multiple extraction methods and return the best result.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text
    """
    try:
        # Method 1: Standard PyPDF2 extraction
        text1 = extract_text_standard(pdf_path)
        
        # Method 2: Page-by-page extraction with character normalization
        text2 = extract_text_normalized(pdf_path)
        
        # Choose the extraction with better quality (simple heuristic: longer text)
        # This could be improved with more sophisticated quality metrics
        if len(text2) > len(text1) * 1.1:  # text2 is at least 10% longer
            return text2
        else:
            return text1
            
    except Exception as e:
        print(f"Error during improved PDF extraction: {e}")
        # Fall back to standard extraction
        return extract_text_standard(pdf_path)

def extract_text_standard(pdf_path):
    """Standard PyPDF2 text extraction."""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
            
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
                
    return text

def extract_text_normalized(pdf_path):
    """Normalized text extraction with character handling."""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            
            # Normalize whitespace
            page_text = re.sub(r'\s+', ' ', page_text)
            
            # Fix common PDF extraction issues
            page_text = re.sub(r'([a-z])-\s*([a-z])', r'\1\2', page_text)  # Fix hyphenation
            
            text += page_text + "\n\n"
    
    return text

def extract_with_section_detection(pdf_path):
    """
    Extract text from PDF and attempt to identify document sections.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: A dictionary with both the full text and identified sections
    """
    # Extract text using the improved method
    full_text = improve_pdf_extraction(pdf_path)
    
    # Return early if extraction failed
    if not full_text:
        return {
            "full_text": "",
            "sections": {}
        }
    
    # Identify sections
    sections = extract_sections(full_text)
    
    return {
        "full_text": full_text,
        "sections": sections
    }

def clean_scientific_text(text):
    """
    Clean and preprocess text extracted from scientific papers.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove header/footer artifacts (page numbers, journal names)
    # This uses some heuristics that work well for scientific papers
    cleaned = []
    for line in text.split("\n"):
        # Skip likely header/footer lines (short lines with page numbers, dates, etc.)
        if len(line.strip()) < 50 and re.search(r'\d+\s*', line):
            continue
        # Skip copyright lines
        if re.search(r'copyright|©|all rights reserved', line.lower()):
            continue
        # Skip journal header lines
        if re.search(r'journal of|proceedings of', line.lower()) and len(line.strip()) < 60:
            continue
            
        cleaned.append(line)
    
    text = "\n".join(cleaned)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Fix hyphenation at line breaks
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Remove reference numbers [1], [2], etc.
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)
    
    # Fix spacing after periods
    text = re.sub(r'\.(?=[A-Z])', '. ', text)
    
    return text.strip()


def detect_article_structure(text):
    """
    Detect the structure of an academic article to better target extraction.
    
    Args:
        text (str): The article text
        
    Returns:
        dict: Information about the article structure
    """
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
    has_abstract = bool(re.search(r'\b(?:Abstract|ABSTRACT)\b', text[:1000], re.IGNORECASE))
    
    # Check for methods section (more robust pattern)
    has_methods = bool(re.search(r'\b(?:Methods|Methodology|Materials and Methods|METHODS)\b', text, re.IGNORECASE))
    
    # Check for typical sections (more robust patterns)
    has_introduction = bool(re.search(r'\b(?:Introduction|Background|INTRODUCTION)\b', text, re.IGNORECASE))
    has_results = bool(re.search(r'\b(?:Results|Findings|RESULTS)\b', text, re.IGNORECASE))
    has_discussion = bool(re.search(r'\b(?:Discussion|DISCUSSION)\b', text, re.IGNORECASE))
    has_conclusion = bool(re.search(r'\b(?:Conclusion|Conclusions|CONCLUSION|CONCLUSIONS)\b', text, re.IGNORECASE))
    
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
def extract_toc_or_headings(text):
    """
    Attempt to extract a table of contents or article headings.
    
    Args:
        text (str): The article text
        
    Returns:
        list: Extracted headings or sections
    """
    headings = []
    
    # Look for numbered sections (common in academic papers)
    section_patterns = [
        r'^\s*(\d+\.(?:\d+\.?)*)?\s*([A-Z][A-Za-z\s]+)',  # Numbered sections like "1. Introduction"
        r'^\s*([A-Z][A-Za-z\s]+)'  # Capitalized headings like "METHODS"
    ]
    
    for line in text.split('\n'):
        for pattern in section_patterns:
            match = re.match(pattern, line.strip())
            if match:
                # If we matched a numbered section, get the section name from group 2, otherwise group 1
                heading = match.group(2) if len(match.groups()) > 1 and match.group(2) else match.group(1)
                headings.append(heading.strip())
                break
    
    return headings

def extract_abstract(text):
    """
    Attempt to extract the abstract from an article.
    
    Args:
        text (str): The article text
        
    Returns:
        str: The extracted abstract or empty string if not found
    """
    # Common abstract patterns
    abstract_patterns = [
        r'(?i)abstract\s*\n(.*?)(?=\n\s*(?:introduction|keywords|background)|\n\s*\d+\.|\Z)',
        r'(?i)abstract[:\s]+(.*?)(?=\n\s*(?:introduction|keywords|background)|\n\s*\d+\.|\Z)'
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract
    
    return ""

def get_pdf_metadata(pdf_path):
    """
    Extract metadata from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Extracted metadata
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata
            
            # Convert PyPDF2 metadata to dictionary
            meta_dict = {}
            if metadata:
                for key in metadata:
                    clean_key = key.strip('/').lower()
                    meta_dict[clean_key] = metadata[key]
            
            # Add additional metadata
            meta_dict['pages'] = len(pdf_reader.pages)
            
            return meta_dict
    except Exception as e:
        print(f"Error extracting PDF metadata: {e}")
        return {}