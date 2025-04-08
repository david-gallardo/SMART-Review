#!/usr/bin/env python
"""
Advanced Prompt Manager for Scientific Articles

This module provides a flexible system for managing and customizing prompts 
for different sections of scientific articles. It allows defining specialized 
prompts for different article types, research methodologies, and mental health conditions.

Usage:
    Import this module in your article processing script to access the specialized prompts.
"""

import os
import yaml
import json
import re
from typing import Dict, List, Optional

class PromptManager:
    """
    Manages prompts for different sections of scientific articles.
    
    This class allows loading, customizing, and retrieving prompts for different
    article sections based on article type, methodology, and content.
    """
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize the prompt manager.
        
        Args:
            prompts_dir (str, optional): Directory containing custom prompt templates
        """
        self.prompts_dir = prompts_dir
        self.base_prompts = {}
        self.specialized_prompts = {}
        self.custom_prompts = {}
        
        # Load default prompts
        self._load_default_prompts()
        
        # Load custom prompts if directory is specified
        if prompts_dir and os.path.exists(prompts_dir):
            self._load_custom_prompts()
    
    def _load_default_prompts(self):
        """Load the default set of prompts for article sections."""
        self.base_prompts = {
            "background": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.
        
            Extract and summarize the key background information from this article, including:
            1. The research problem being addressed
            2. Previous research on this topic and existing knowledge gaps
            3. The theoretical framework or model used, if any
            4. The significance and rationale for the study
        
            Focus only on the background information. Don't include methods, results, or discussion in this section.
            Provide a well-structured summary (300-400 words) with clear sections.
            """,

            "methods": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.

            Extract and summarize the methodology used in this study, including:
            1. Study design (e.g., RCT, quasi-experimental, etc.)
            2. Population and sampling (including mental health condition and demographic details)
            3. Intervention description in detail (type, duration, components, implementation)
            4. Control or comparison groups
            5. Outcome measures (primary and secondary)
            6. Data collection procedures
            7. Statistical analysis methods
        
            Provide a well-structured summary (300-400 words) with clear sections following the points above.
            """,

            "results": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.

            Extract and summarize the key results of this study, including:
            1. Primary outcome results (employment rates, job retention, etc.)
            2. Secondary outcome results (mental health improvements, quality of life, etc.)
            3. Any subgroup analyses
            4. Statistical significance and effect sizes
            5. Any unexpected or negative findings

            Present both the statistics and their interpretation. If exact numbers are provided, include them.
            Provide a well-structured summary (300-400 words) with clear sections.
            """,

            "discussion": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.

            Extract and summarize the discussion section of this article, including:
            1. The authors' interpretation of the main findings
            2. How the findings relate to previous research
            3. Implications for practice or policy
            4. Limitations of the study
            5. Suggestions for future research

            Provide a well-structured summary (300-400 words) with clear sections following the points above.
            """,

            "conclusions": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.

            Extract and provide a concise summary of the authors' conclusions, including:
            1. The main takeaway messages
            2. Any recommendations for implementation
            3. The significance of the findings for the field

            Keep this summary brief (150-200 words) but comprehensive, focusing on the authors' final conclusions.
            """,

            "synthesis": """
            You're an expert research assistant analyzing scientific articles on employment interventions for people with mental health disorders.

            After reading the entire article, provide a critical synthesis that includes:
            1. An assessment of the study quality (methodological strengths and weaknesses)
            2. The significance of this study to the field of employment interventions for people with mental health disorders
            3. How this intervention compares to other approaches in the literature
            4. Practical implications for employment support services
            5. The generalizability of findings to different populations or settings

            This synthesis should reflect a high-level, critical analysis of the article rather than just summarizing content.
            Provide a well-structured synthesis (300-400 words) with clear sections.
            """,

            "executive_summary": """
            You're an expert research assistant creating an executive summary of multiple scientific articles on employment interventions for people with mental health disorders.

            Based on the information provided about these articles, create a comprehensive executive summary that:
            1. Identifies the common themes and research questions addressed across the articles
            2. Summarizes the key employment interventions studied and their overall effectiveness
            3. Highlights the most significant findings that appear consistent across studies
            4. Identifies important practical implications for mental health practitioners and employment services

            The audience for this summary includes researchers, policymakers, and practitioners in mental health and employment support services.

            Provide a well-structured, cohesive executive summary (500-600 words) that presents an integrated overview of the field based on these articles.
            """,

            "overall_synthesis": """
            You're an expert research assistant synthesizing findings from multiple scientific articles on employment interventions for people with mental health disorders.

            Based on the critical syntheses and conclusions of all the reviewed articles, provide a comprehensive analysis that:
            1. Identifies patterns, trends, and common themes across the studies
            2. Compares and contrasts the methodologies and their strengths/limitations
            3. Evaluates the consistency of findings across different interventions and populations
            4. Highlights areas of consensus and disagreement in the literature
            5. Identifies gaps in current research and promising directions for future studies
            6. Discusses implications for policy, practice, and service delivery

            This overall synthesis should provide a high-level, critical analysis of the collective body of evidence rather than merely summarizing individual articles.

            Provide a well-structured synthesis (800-1000 words) with clear sections addressing each of the above points.
            """
    }
        
        # Define specialized prompts for different article types, methods, etc.
        self.specialized_prompts = {
            # Prompts for specific study designs
            "study_design": {
                "rct": {
                    "methods": """
                    You're an expert research assistant analyzing a randomized controlled trial (RCT) on employment interventions for people with mental health disorders.
                    
                    Extract and summarize the methodology of this RCT, with special attention to:
                    1. Randomization procedures and allocation concealment
                    2. Blinding procedures (if any)
                    3. Intervention and control conditions in detail
                    4. Sample size calculation and power analysis
                    5. Population characteristics and inclusion/exclusion criteria
                    6. Primary and secondary outcome measures
                    7. Statistical analysis methods, including intention-to-treat analysis
                    
                    Provide a well-structured summary (300-400 words) that clearly describes the RCT methodology.
                    """,
                    
                    "results": """
                    You're an expert research assistant analyzing a randomized controlled trial (RCT) on employment interventions for people with mental health disorders.
                    
                    Extract and summarize the results of this RCT, with special attention to:
                    1. Primary outcome results with effect sizes and confidence intervals
                    2. Secondary outcome results
                    3. Subgroup analyses and treatment effect moderators
                    4. Dropout rates and missing data handling
                    5. Adverse events or negative outcomes
                    6. Statistical significance and clinical significance of findings
                    
                    Present both the statistics and their interpretation. Include exact numbers, p-values, confidence intervals, and effect sizes when available.
                    Provide a well-structured summary (300-400 words) with clear sections.
                    """
                },
                
                "quasi_experimental": {
                    "methods": """
                    You're an expert research assistant analyzing a quasi-experimental study on employment interventions for people with mental health disorders.
                    
                    Extract and summarize the methodology of this quasi-experimental study, with special attention to:
                    1. The specific quasi-experimental design used (e.g., non-equivalent control group, interrupted time series)
                    2. How comparison groups were established
                    3. Methods to control for selection bias and confounding variables
                    4. Intervention details and implementation
                    5. Population characteristics and sampling methods
                    6. Outcome measures and their validity
                    7. Statistical analysis methods to account for non-randomization
                    
                    Provide a well-structured summary (300-400 words) that clearly describes the quasi-experimental methodology.
                    """
                },
                
                "systematic_review": {
                    "methods": """
                    You're an expert research assistant analyzing a systematic review or meta-analysis on employment interventions for people with mental health disorders.
                    
                    Extract and summarize the methodology of this systematic review, with special attention to:
                    1. Search strategy and databases used
                    2. Inclusion and exclusion criteria
                    3. Quality assessment or risk of bias evaluation methods
                    4. Data extraction procedures
                    5. Meta-analytic methods (if applicable)
                    6. Heterogeneity assessment
                    7. Publication bias assessment
                    
                    Provide a well-structured summary (300-400 words) that clearly describes the systematic review methodology.
                    """,
                    
                    "results": """
                    You're an expert research assistant analyzing a systematic review or meta-analysis on employment interventions for people with mental health disorders.
                    
                    Extract and summarize the results of this systematic review, with special attention to:
                    1. Number of studies included and their characteristics
                    2. Quality assessment or risk of bias results
                    3. Main findings from the evidence synthesis
                    4. Meta-analytic results with effect sizes (if applicable)
                    5. Heterogeneity analysis
                    6. Subgroup or sensitivity analyses
                    7. Publication bias assessment results
                    
                    Present both the statistics and their interpretation. Include exact numbers of studies, effect sizes, confidence intervals, and heterogeneity statistics when available.
                    Provide a well-structured summary (300-400 words) with clear sections.
                    """
                }
            },
            
            # Prompts for specific mental health conditions
            "mental_health_condition": {
                "depression": {
                    "synthesis": """
                    You're an expert research assistant analyzing a study on employment interventions for people with depression.
                    
                    After reading the entire article, provide a critical synthesis that includes:
                    1. An assessment of the study quality and methodology
                    2. How this study addresses the specific challenges of depression in workplace settings
                    3. How the intervention accounts for depression symptoms (e.g., low motivation, concentration problems)
                    4. Comparison to other depression-focused employment interventions
                    5. Implications for employment support services working with depressed clients
                    6. Assessment of outcome measures relevant to depression
                    7. Generalizability to different populations with depression
                    
                    This synthesis should reflect a high-level, critical analysis focusing specifically on depression-related aspects.
                    Provide a well-structured synthesis (300-400 words) with clear sections.
                    """
                },
                
                "schizophrenia": {
                    "synthesis": """
                    You're an expert research assistant analyzing a study on employment interventions for people with schizophrenia or psychotic disorders.
                    
                    After reading the entire article, provide a critical synthesis that includes:
                    1. An assessment of the study quality and methodology
                    2. How this study addresses the specific challenges of schizophrenia in employment settings
                    3. How the intervention accounts for schizophrenia symptoms (e.g., cognitive impairments, negative symptoms)
                    4. Comparison to other schizophrenia-focused employment interventions, especially IPS if mentioned
                    5. Implications for vocational rehabilitation services working with clients with schizophrenia
                    6. Assessment of outcome measures relevant to schizophrenia and recovery
                    7. Consideration of stigma and disclosure issues in the workplace
                    
                    This synthesis should reflect a high-level, critical analysis focusing specifically on schizophrenia-related aspects.
                    Provide a well-structured synthesis (300-400 words) with clear sections.
                    """
                }
            },
            
            # Prompts for specific intervention types
            "intervention_type": {
                "supported_employment": {
                    "synthesis": """
                    You're an expert research assistant analyzing a study on supported employment interventions for people with mental health disorders.
                    
                    After reading the entire article, provide a critical synthesis that includes:
                    1. An assessment of the study quality and methodology
                    2. How this intervention compares to the IPS (Individual Placement and Support) model
                    3. Fidelity to supported employment principles
                    4. Integration of employment and mental health services
                    5. Job development and employer engagement strategies
                    6. Long-term support mechanisms
                    7. Cost-effectiveness considerations
                    8. Implications for implementing supported employment programs
                    
                    This synthesis should reflect a high-level, critical analysis focusing specifically on supported employment aspects.
                    Provide a well-structured synthesis (300-400 words) with clear sections.
                    """
                },
                
                "vocational_rehabilitation": {
                    "synthesis": """
                    You're an expert research assistant analyzing a study on vocational rehabilitation for people with mental health disorders.
                    
                    After reading the entire article, provide a critical synthesis that includes:
                    1. An assessment of the study quality and methodology
                    2. The vocational rehabilitation model or approach used
                    3. How pre-employment assessment and training were conducted
                    4. Skills development and educational components
                    5. Placement processes and employer relationships
                    6. Integration with clinical mental health services
                    7. Comparison to other vocational models (e.g., supported employment)
                    8. Implications for improving vocational rehabilitation practices
                    
                    This synthesis should reflect a high-level, critical analysis focusing specifically on vocational rehabilitation aspects.
                    Provide a well-structured synthesis (300-400 words) with clear sections.
                    """
                }
            }
        }
    
    def _load_custom_prompts(self):
        """Load custom prompts from the specified directory."""
        try:
            # Look for YAML or JSON files in the prompt directory
            for filename in os.listdir(self.prompts_dir):
                filepath = os.path.join(self.prompts_dir, filename)
                
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        custom_prompts = yaml.safe_load(f)
                        
                elif filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        custom_prompts = json.load(f)
                else:
                    continue
                
                # Add the custom prompts
                if isinstance(custom_prompts, dict):
                    self.custom_prompts.update(custom_prompts)
        
        except Exception as e:
            print(f"Error loading custom prompts: {e}")
    
    def get_prompt(self, section: str, article_info: Optional[Dict] = None) -> str:
        """
        Get the appropriate prompt for a section based on article information.
        
        Args:
            section (str): The article section (background, methods, etc.)
            article_info (dict, optional): Information about the article that helps
                                          determine the best prompt to use
                                          
        Returns:
            str: The selected prompt
        """
        # Start with the base prompt for the section
        if section not in self.base_prompts:
            raise ValueError(f"Unknown section: {section}")
        
        prompt = self.base_prompts[section]
        
        # If no article info provided, return the base prompt
        if not article_info:
            return prompt
        
        # Check for specialized prompts based on article characteristics
        
        # 1. Check for study design specific prompts
        if 'study_design' in article_info:
            design = article_info['study_design'].lower()
            
            # Map variant names to standard keys
            design_mapping = {
                'rct': 'rct',
                'randomized controlled trial': 'rct',
                'randomised controlled trial': 'rct',
                'quasi-experimental': 'quasi_experimental',
                'quasi experimental': 'quasi_experimental',
                'non-randomized': 'quasi_experimental',
                'non-randomised': 'quasi_experimental',
                'systematic review': 'systematic_review',
                'meta-analysis': 'systematic_review',
                'meta analysis': 'systematic_review'
            }
            
            design_key = design_mapping.get(design)
            
            if design_key and design_key in self.specialized_prompts['study_design']:
                if section in self.specialized_prompts['study_design'][design_key]:
                    prompt = self.specialized_prompts['study_design'][design_key][section]
        
        # 2. Check for mental health condition specific prompts
        if 'mental_health_condition' in article_info:
            condition = article_info['mental_health_condition'].lower()
            
            # Map variant names to standard keys
            condition_mapping = {
                'depression': 'depression',
                'depressive disorder': 'depression',
                'major depression': 'depression',
                'schizophrenia': 'schizophrenia',
                'psychosis': 'schizophrenia',
                'psychotic disorders': 'schizophrenia',
                'schizoaffective': 'schizophrenia'
            }
            
            condition_key = condition_mapping.get(condition)
            
            if condition_key and condition_key in self.specialized_prompts['mental_health_condition']:
                if section in self.specialized_prompts['mental_health_condition'][condition_key]:
                    prompt = self.specialized_prompts['mental_health_condition'][condition_key][section]
        
        # 3. Check for intervention type specific prompts
        if 'intervention_type' in article_info:
            intervention = article_info['intervention_type'].lower()
            
            # Map variant names to standard keys
            intervention_mapping = {
                'supported employment': 'supported_employment',
                'individual placement and support': 'supported_employment',
                'ips': 'supported_employment',
                'vocational rehabilitation': 'vocational_rehabilitation',
                'voc rehab': 'vocational_rehabilitation',
                'vocational training': 'vocational_rehabilitation'
            }
            
            intervention_key = intervention_mapping.get(intervention)
            
            if intervention_key and intervention_key in self.specialized_prompts['intervention_type']:
                if section in self.specialized_prompts['intervention_type'][intervention_key]:
                    prompt = self.specialized_prompts['intervention_type'][intervention_key][section]
        
        # 4. Check for custom prompts (these take highest precedence)
        if section in self.custom_prompts:
            prompt = self.custom_prompts[section]
        
        return prompt.strip()
    
    def save_custom_prompt(self, section: str, prompt: str, filename: str = "custom_prompts.yaml"):
        """
        Save a custom prompt for future use.
        
        Args:
            section (str): The article section this prompt is for
            prompt (str): The prompt text
            filename (str): Filename to save the custom prompt to
        """
        if not self.prompts_dir:
            self.prompts_dir = os.path.join(os.getcwd(), "prompts")
            os.makedirs(self.prompts_dir, exist_ok=True)
        
        filepath = os.path.join(self.prompts_dir, filename)
        
        # Load existing custom prompts if file exists
        existing_prompts = {}
        if os.path.exists(filepath):
            if filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_prompts = yaml.safe_load(f) or {}
            elif filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_prompts = json.load(f)
        
        # Update with new prompt
        existing_prompts[section] = prompt
        
        # Save back to file
        if filepath.endswith('.yaml') or filepath.endswith('.yml'):
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(existing_prompts, f, default_flow_style=False)
        elif filepath.endswith('.json'):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_prompts, f, indent=2)
        
        # Update the current custom prompts
        self.custom_prompts[section] = prompt
    
    def list_available_prompts(self) -> Dict:
        """
        List all available prompts by category.
        
        Returns:
            dict: Dictionary containing all prompts organized by category
        """
        return {
            "base_prompts": list(self.base_prompts.keys()),
            "specialized_prompts": self.specialized_prompts,
            "custom_prompts": list(self.custom_prompts.keys())
        }


# Example usage
if __name__ == "__main__":
    # Create prompt manager
    manager = PromptManager()
    
    # Get a basic prompt
    background_prompt = manager.get_prompt("background")
    print("Basic Background Prompt:")
    print(background_prompt[:100] + "...\n")
    
    # Get a specialized prompt
    article_info = {
        "study_design": "RCT",
        "mental_health_condition": "depression",
        "intervention_type": "supported employment"
    }
    methods_prompt = manager.get_prompt("methods", article_info)
    print("Specialized Methods Prompt for RCT:")
    print(methods_prompt[:100] + "...\n")
    
    # Save a custom prompt
    custom_prompt = """
    You're an expert research assistant analyzing the outcomes of a study on employment interventions for people with mental health disorders.
    
    Extract and summarize the key outcomes focusing specifically on:
    1. Long-term employment retention (beyond 12 months)
    2. Quality of employment (wages, hours, job satisfaction)
    3. Career advancement opportunities
    4. Workplace accommodations and supports
    
    Provide a well-structured summary (300-400 words) with clear sections.
    """
    manager.save_custom_prompt("outcomes", custom_prompt, "my_custom_prompts.yaml")
    
    # List available prompts
    available_prompts = manager.list_available_prompts()
    print("Available base prompts:", available_prompts["base_prompts"])
    print("Available custom prompts:", available_prompts["custom_prompts"])