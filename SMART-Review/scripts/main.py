import os
import re
import pandas as pd
import requests
import json
import concurrent.futures
import itertools
import numpy as np
from statsmodels.stats.inter_rater import fleiss_kappa

# Set TEST to True to process only the first 5 articles, or False to process all.
TEST = False

def extract_json_block(text):
    """
    Extract the JSON block from a string by counting matching curly braces.
    Returns the substring that constitutes the JSON object.
    """
    start = text.find('{')
    if start == -1:
        return text  # No JSON block found
    count = 0
    end = start
    for i, char in enumerate(text[start:], start=start):
        if char == '{':
            count += 1
        elif char == '}':
            count -= 1
            if count == 0:
                end = i + 1
                break
    return text[start:end]

def consult_model(model_name, article_text):
    """
    Send a request to LMStudio to evaluate an article based on inclusion/exclusion criteria.

    Parameters:
        model_name (str): The name of the model to use.
        article_text (str): The text of the article (title and abstract).

    Returns:
        dict: A dictionary containing the following keys:
            - inclusion_decision: "Included", "Excluded", or "Unclear"
            - reason: Short explanation for the decision
            - study_design: The type of methodology (e.g., RCT, quasi-experimental, systematic review, etc.)
            - logprobs: Placeholder for log probabilities if available
    """
    url = "http://127.0.0.1:1234/v1/chat/completions"
    
    # Construct the prompt with inclusion and exclusion criteria
    prompt = (
        "You are a research assistant specialized in systematic reviews.\n\n"
        "We want to screen an article to see if it meets the following inclusion and exclusion criteria. "
        "The overall objective is to identify what works in active employment policies for people with mental health disorders.\n\n"
        "Inclusion criteria:\n"
        "• Study design: meta-analyses, systematic reviews of controlled trials, RCTs (including cluster RCTs), or quasi-experimental studies with a control group.\n"
        "• Geographic scope: EU countries, Europe, US, Canada, Australia.\n"
        "• Timeframe: 2005-2025.\n"
        "• Intervention: job search services, adult training, wage subsidies, supported employment.\n"
        "• Population: people with mental disorders or documented mental health problems.\n"
        "• Outcomes: must include employment or labor outcomes such as employment rates, job duration, job quality, workplace integration, or job retention.\n\n"
        "Exclusion criteria:\n"
        "• Study design: lacks a rigorous evaluation or no control group.\n"
        "• Geographic scope: outside the EU, Europe, US, Canada, or Australia.\n"
        "• Timeframe: published before 2005 or after 2025.\n"
        "• Intervention: labor regulation policies, social security policies, or does not directly address employment.\n"
        "• Population: does not reference mental health or has an undefined population.\n"
        "• Outcomes: does not present measures of employment or labor results.\n\n"
        "Task:\n"
        "Please read the following article and determine if it meets the inclusion criteria or should be excluded. "
        "Then provide a structured JSON with these fields:\n"
        "1. \"inclusion_decision\": either \"Included\" or \"Excluded\"\n"
        "2. \"reason\": a short explanation of why it was included or excluded\n"
        "3. \"study_design\": the type of methodology (e.g., RCT, quasi-experimental, systematic review, etc.)\n"
        "4. \"logprobs\": (optional) placeholder for log probabilities if available.\n\n"
        "Important: Output must be valid JSON with no extra text.\n\n"
        "Article to Screen:\n" + article_text +
        "Very Important: Output only a JSON object with no additional text, explanations, or formatting.\n\n"
    )
    
    # Prepare the request body
    request_body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are an expert in academic article review."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300,
        "logprobs": 5
    }
    
    try:
        response = requests.post(url, json=request_body, headers={"Content-Type": "application/json"})
        response_text = response.text
        response_json = json.loads(response_text)
    except Exception as e:
        print(f"Error calling model {model_name}: {e}")
        return {"inclusion_decision": "Unclear", "reason": "Error in API call", "study_design": None, "logprobs": None}
    
    try:
        generated_text = response_json["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Invalid response structure from {model_name}: {e}")
        return {"inclusion_decision": "Unclear", "reason": "Invalid response structure", "study_design": None, "logprobs": None}
    
    # Clean the text (remove markdown delimiters)
    cleaned_text = generated_text.replace("```json", "").replace("```", "").strip()
    
    # If the model is phi-3-mini-4k-instruct, extract only the JSON block.
    if model_name == "phi-3-mini-4k-instruct":
        cleaned_text = extract_json_block(cleaned_text)
    
    try:
        parsed_result = json.loads(cleaned_text)
    except Exception as e:
        print(f"JSON parsing error for {model_name}: {e}")
        return {"inclusion_decision": "Unclear", "reason": "Could not parse model's JSON output", "study_design": None, "logprobs": None}
    
    # Ensure all essential fields are present
    if "inclusion_decision" not in parsed_result:
        parsed_result["inclusion_decision"] = "Unclear"
    if "reason" not in parsed_result:
        parsed_result["reason"] = "No reason provided"
    if "study_design" not in parsed_result:
        parsed_result["study_design"] = None
    if "logprobs" not in parsed_result:
        parsed_result["logprobs"] = None
    
    return parsed_result

def pairwise_agreement(ratings):
    """
    Calculate pairwise agreement from a list of ratings (considering only "Included" and "Excluded").

    Parameters:
        ratings (list): List of rating strings.

    Returns:
        float or None: The average pairwise agreement or None if not enough ratings.
    """
    filtered = [r for r in ratings if r in ["Included", "Excluded"]]
    n = len(filtered)
    if n < 2:
        return None
    agreements = []
    for r1, r2 in itertools.combinations(filtered, 2):
        agreements.append(1 if r1 == r2 else 0)
    return sum(agreements) / len(agreements) if agreements else None

def compute_global_inclusion(ratings):
    """
    Determine the overall inclusion decision for an article based on majority vote.

    Parameters:
        ratings (list): List of rating strings.

    Returns:
        str: "Yes" if majority Included, "No" if majority Excluded, otherwise "Unclear".
    """
    filtered = [r for r in ratings if r in ["Included", "Excluded"]]
    if not filtered:
        return "Unclear"
    count_included = filtered.count("Included")
    count_excluded = filtered.count("Excluded")
    if count_included > count_excluded:
        return "Yes"
    elif count_excluded > count_included:
        return "No"
    else:
        return "Unclear"

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Build the absolute path to the Excel file (go up one directory to the repo root)
    data_path = os.path.join(script_dir, '..', 'data', 'full_data.xlsx')
    
    # Read the Excel file containing all articles
    df_full = pd.read_excel(data_path)
    df_articles = df_full[["Authors", "Article Title", "Abstract", "DOI"]]
    
    # If TEST is True, only process the first 5 articles.
    if TEST:
        df_articles = df_articles.head(5)
        print("TEST mode enabled: processing only the first 5 articles.")
    else:
        print("Processing all articles.")
    
    models = [
        "mistral-small-24b-instruct-2501",
        "qwen2.5-7b-instruct-1m",
        "phi-3-mini-4k-instruct",
        "llama-3.2-3b-instruct"
    ]
    
    # Prepare output directory for processed JSON files
    out_dir = os.path.join(script_dir, '..', 'output', 'processed')
    os.makedirs(out_dir, exist_ok=True)
    
    all_results = []
    records = []
    
    # Process each article
    for idx, row in df_articles.iterrows():
        article_id = idx + 1
        print(f"\n=== Processing article {article_id} ===")
        article_text = f"Title: {row['Article Title']}\n\nAbstract: {row['Abstract']}"
        model_results = {}
        
        # Parallelize requests to each model (limiting to 8 workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_model = {
                executor.submit(consult_model, model, article_text): model for model in models
            }
            for future in concurrent.futures.as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                except Exception as exc:
                    print(f"{model} generated an exception: {exc}")
                    result = {"inclusion_decision": "Unclear", "reason": "Exception occurred", "study_design": None, "logprobs": None}
                model_results[model] = result
        
        # Create a dictionary containing article details and model results
        article_result = {
            "ArticleID": article_id,
            "Authors": row["Authors"],
            "Article Title": row["Article Title"],
            "Abstract": row["Abstract"],
            "DOI": row["DOI"],
            "Model Results": model_results
        }
        
        # Save the article result as a JSON file in output/processed
        output_file = os.path.join(out_dir, f"{article_id}.json")
        try:
            with open(output_file, "w", encoding="utf-8") as f_out:
                json.dump(article_result, f_out, indent=4)
            print(f"Saved article {article_id} results to '{output_file}'.")
        except Exception as e:
            print(f"Error saving article {article_id} JSON file: {e}")
        
        # Also collect results for later aggregate processing
        all_results.append(model_results)
        record = {"Article": article_id}
        for model in models:
            mod_clean = model.replace("-", ".")
            res = model_results.get(model, {"inclusion_decision": None, "reason": None, "study_design": None})
            record[f"{mod_clean}_inclusion"] = res.get("inclusion_decision")
            record[f"{mod_clean}_reason"] = res.get("reason")
            record[f"{mod_clean}_study_design"] = res.get("study_design")
        records.append(record)
    
    # Build a DataFrame with the aggregate results (similar format to the R code)
    results_df = pd.DataFrame(records)
    
    # Calculate global inclusion based on model decisions
    inclusion_cols = [col for col in results_df.columns if col.endswith("_inclusion")]
    global_inclusion = []
    for idx, row in results_df.iterrows():
        ratings = row[inclusion_cols].tolist()
        global_inclusion.append(compute_global_inclusion(ratings))
    results_df["GlobalInclusion"] = global_inclusion
    
    # Calculate pairwise agreement for each article
    pairwise_agreements = []
    for idx, row in results_df.iterrows():
        ratings = row[inclusion_cols].tolist()
        pairwise_agreements.append(pairwise_agreement(ratings))
    results_df["PairwiseAgreement"] = pairwise_agreements
    
    print("\nFinal aggregate results (DataFrame):")
    print(results_df)
    
    # Calculate global Fleiss' Kappa based on inclusion decisions.
    fleiss_data = []
    for idx, row in results_df.iterrows():
        ratings = row[inclusion_cols].tolist()
        counts = {"Included": 0, "Excluded": 0, "Unclear": 0}
        for r in ratings:
            if r in counts:
                counts[r] += 1
            else:
                counts["Unclear"] += 1
        fleiss_data.append([counts["Included"], counts["Excluded"], counts["Unclear"]])
    fleiss_matrix = np.array(fleiss_data)
    
    try:
        fk = fleiss_kappa(fleiss_matrix)
        print("\nGlobal Fleiss' Kappa:")
        print(fk)
    except Exception as e:
        print(f"Error calculating Fleiss' Kappa: {e}")
    
    # Combine the aggregate results with the original article data and write to a new Excel file.
    output_path = os.path.join(script_dir, '..', 'data', 'df_articles_results.xlsx')
    combined_df = pd.concat([df_articles.reset_index(drop=True), results_df.drop(columns=["Article"])], axis=1)
    combined_df.to_excel(output_path, index=False)
    print(f"\nCombined results have been saved to '{output_path}'.")

if __name__ == "__main__":
    main()
