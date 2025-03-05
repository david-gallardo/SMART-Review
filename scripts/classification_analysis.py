import os
import pandas as pd
import requests
import json
import concurrent.futures
import time
import matplotlib.pyplot as plt
import seaborn as sns
import sys

# Variable per controlar el mode test: True només per 5 casos, False per tot el dataset
test = False  # Canvia a False per processar tot el dataset

# Afegir el directori de scripts al camí de Python
scripts_dir = os.path.abspath('../scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Importa funcions de main.py
from main import consult_model, extract_json_block, compute_global_classification, create_multiple_category_chart

# File paths
data_path = os.path.join(os.getcwd(), "data")
classified_file = os.path.join(data_path, "included_articles_classified.xlsx")
original_file = os.path.join(data_path, "df_articles_results_classified.xlsx")

# Models LLM a utilitzar
models = [
    "mistral-small-24b-instruct-2501",
    "qwen2.5-7b-instruct-1m",
    "phi-3-mini-4k-instruct",
    "llama-3.2-3b-instruct"
]

def classify_abstract(model_name, title, abstract):
    """Query LLM to classify the abstract according to study design, conditions, etc."""
    article_text = f"Title: {title}\nAbstract: {abstract}"
    
    prompt = (
        "You are a research assistant specialized in systematic reviews of mental health and employment interventions.\n\n"
        "Task:\n"
        "Classify the following study according to these categories:\n\n"
        "1. Study Design (select one):\n"
        "   - RCT (Randomized Controlled Trial)\n"
        "   - Quasi-experimental (Non-randomized studies with a control group)\n"
        "   - Systematic review (Systematic review or meta-analysis)\n"
        "   - Observational (Cohort studies, case-control, cross-sectional)\n"
        "   - Theoretical/Other (Conceptual, methodological, or narrative review)\n\n"
        "2. Mental Health Condition (select all that apply):\n"
        "   - Depression\n"
        "   - Anxiety\n"
        "   - Schizophrenia\n"
        "   - Bipolar\n"
        "   - Personality disorders\n"
        "   - General mental health\n"
        "   - Multiple specific conditions\n"
        "   - Other (please specify)\n\n"
        "3. Intervention Type (select all that apply):\n"
        "   - Supported employment\n"
        "   - Vocational rehabilitation\n"
        "   - Job search assistance\n"
        "   - Skills training\n"
        "   - Workplace accommodations\n"
        "   - Return-to-work programs\n"
        "   - Multiple interventions\n"
        "   - Other (please specify)\n\n"
        "4. Outcome Measures (select all that apply):\n"
        "   - Employment rate\n"
        "   - Job retention\n"
        "   - Income/earnings\n"
        "   - Work functioning\n"
        "   - Mental health improvement\n"
        "   - Quality of life\n"
        "   - Multiple outcomes\n"
        "   - Other (please specify)\n\n"
        "Important: Output must be a JSON with this structure:\n"
        "{\n"
        "  \"study_design\": \"CATEGORY\",\n"
        "  \"mental_health_condition\": [\"CONDITION1\", \"CONDITION2\"],\n"
        "  \"intervention_type\": [\"INTERVENTION1\", \"INTERVENTION2\"],\n"
        "  \"outcome_measures\": [\"OUTCOME1\", \"OUTCOME2\"]\n"
        "}\n\n"
        "Article:\n"
        f"{article_text}\n\n"
        "Very Important: Output only a JSON object with no additional text."
    )
    
    url = "http://127.0.0.1:1234/v1/chat/completions"
    request_body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are an expert in systematic reviews of mental health and employment interventions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, json=request_body, headers={"Content-Type": "application/json"})
        response_text = response.text
        response_json = json.loads(response_text)
        generated_text = response_json["choices"][0]["message"]["content"]
        
        # Clean up the response to extract just the JSON
        cleaned_text = generated_text.replace("```json", "").replace("```", "").strip()
        
        # For phi-3-mini model, extract the JSON block
        if model_name == "phi-3-mini-4k-instruct":
            cleaned_text = extract_json_block(cleaned_text)
            
        parsed_result = json.loads(cleaned_text)
        return parsed_result
    except Exception as e:
        print(f"Error processing article with {model_name}: {e}")
        return {
            "study_design": "Error",
            "mental_health_condition": ["Error"],
            "intervention_type": ["Error"],
            "outcome_measures": ["Error"]
        }

def process_article(idx, row):
    """Processa un article individual: consulta tots els models i retorna els resultats."""
    article_id = idx + 1
    print(f"Processing article {article_id}")
    
    title = row["Article Title"] if "Article Title" in row else ""
    abstract = row["Abstract"] if "Abstract" in row else ""
    
    # Combine title and abstract if abstract is missing
    if not abstract and title:
        abstract = title
    if not abstract and not title:
        print(f"Skipping article {article_id} - no title or abstract")
        return None, None

    model_results = {}
    # Paral·lelitza les consultes a tots els models (operació I/O)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
        future_to_model = {executor.submit(classify_abstract, model, title, abstract): model for model in models}
        for future in concurrent.futures.as_completed(future_to_model):
            model = future_to_model[future]
            try:
                result = future.result()
                model_results[model] = result
            except Exception as e:
                print(f"Error getting result from {model}: {e}")
                model_results[model] = {
                    "study_design": "Error",
                    "mental_health_condition": ["Error"],
                    "intervention_type": ["Error"],
                    "outcome_measures": ["Error"]
                }
    
    # Crear el registre per als resultats de tots els models
    record = {
        "Article_ID": article_id,
        "Article_Title": title,
        "Abstract": abstract,
        "DOI": row["DOI"] if "DOI" in row else ""
    }
    for model in models:
        model_clean = model.replace("-", "_")
        result = model_results.get(model, {})
        record[f"{model_clean}_study_design"] = result.get("study_design", "Unknown")
        record[f"{model_clean}_mental_health"] = ", ".join(result.get("mental_health_condition", ["Unknown"]))
        record[f"{model_clean}_intervention"] = ", ".join(result.get("intervention_type", ["Unknown"]))
        record[f"{model_clean}_outcomes"] = ", ".join(result.get("outcome_measures", ["Unknown"]))
    
    # Calcular la classificació global basant-se en els resultats de tots els models
    results_list = list(model_results.values())
    global_record = {
        "Article_ID": article_id,
        "Article_Title": title,
        "Abstract": abstract,
        "DOI": row["DOI"] if "DOI" in row else "",
        "Study_Design": compute_global_classification(results_list, "study_design"),
        "Mental_Health_Condition": ", ".join(compute_global_classification(results_list, "mental_health_condition")),
        "Intervention_Type": ", ".join(compute_global_classification(results_list, "intervention_type")),
        "Outcome_Measures": ", ".join(compute_global_classification(results_list, "outcome_measures"))
    }
    
    # Guarda el resultat de l'article com a fitxer JSON a la carpeta "output/postprocessed"
    out_dir = os.path.join("./output", "postprocessed")
    os.makedirs(out_dir, exist_ok=True)
    article_output = {
        "Article_ID": article_id,
        "Article_Title": title,
        "Abstract": abstract,
        "Model_Results": model_results,
        "Global_Results": {
            "Study_Design": global_record["Study_Design"],
            "Mental_Health_Condition": global_record["Mental_Health_Condition"].split(", "),
            "Intervention_Type": global_record["Intervention_Type"].split(", "),
            "Outcome_Measures": global_record["Outcome_Measures"].split(", ")
        }
    }
    output_file = os.path.join(out_dir, f"article_{article_id}_classification.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(article_output, f, indent=2)
    
    # Retorna els registres per a l'agregació
    return record, global_record

def main():
    """
    Funció principal per analitzar i classificar els articles inclosos basant-se en diverses dimensions:
    - Disseny de l'estudi
    - Condicions de salut mental
    - Tipus d'intervenció
    - Mesures d'resultat
    
    Aquesta funció:
    1. Carrega el dataset original i filtra els estudis inclosos.
    2. O carrega les dades classificades existents o consulta l'LLM per classificar els articles.
    3. Genera visualitzacions per a les classificacions.
    4. Proporciona estadístiques resum.
    """
    print("Loading original dataset...")
    original_df = pd.read_excel(original_file)
    
    # Mapear valors de GlobalInclusion
    global_inclusion_mapping = {"Yes": "Included", "No": "Excluded", "Unclear": "Unclear"}
    original_df["GlobalInclusion"] = original_df["GlobalInclusion"].map(global_inclusion_mapping)
    
    # Filtrar només estudis inclosos
    included_df = original_df[original_df["GlobalInclusion"] == "Included"].copy()
    # Si test és True, processa només els 5 primers articles
    if test:
        included_df = included_df.head(5)
    print(f"Processing only included studies: {len(included_df)} articles")
    
    all_results = []
    global_results = []
    
    # Si ja existeix el fitxer classificat, el carreguem
    if os.path.exists(classified_file):
        print("Classified file found. Loading data without querying LLM...")
        all_model_df = pd.read_excel(classified_file, sheet_name="All_Models")
        global_df = pd.read_excel(classified_file, sheet_name="Global_Decision")
        # Si test és True, només mantenim els 5 primers casos
        if test:
            all_model_df = all_model_df.head(5)
            global_df = global_df.head(5)
    else:
        print("Classified file not found. Querying LLM to classify included studies...")
        # Paral·lelitza el processament dels articles amb ProcessPoolExecutor
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = {executor.submit(process_article, idx, row): idx for idx, row in included_df.iterrows()}
            for future in concurrent.futures.as_completed(futures):
                record, global_record = future.result()
                if record is not None:
                    all_results.append(record)
                    global_results.append(global_record)
        
        # Convertir els resultats en DataFrames
        all_model_df = pd.DataFrame(all_results)
        global_df = pd.DataFrame(global_results)
        
        # Guardar els resultats a Excel amb diverses fulles
        with pd.ExcelWriter(classified_file) as writer:
            all_model_df.to_excel(writer, sheet_name="All_Models", index=False)
            global_df.to_excel(writer, sheet_name="Global_Decision", index=False)
        
        print(f"Classification complete. Results saved to {classified_file}")

    # Generar visualitzacions per a les decisions globals
    print("Generating visualizations...")
    
    figures_dir = os.path.join(os.getcwd(), "figures", "charts")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir, exist_ok=True)

    # Visualització de Study Design
    plt.figure(figsize=(10, 6))
    global_df["Study_Design"].value_counts().plot(kind="bar", color="green")
    plt.xlabel("Study Design")
    plt.ylabel("Number of Articles")
    plt.title("Distribution of Study Types (Included Studies)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "study_design_distribution.png"))
    plt.close()

    # Visualitzacions per camps multi-categoria
    create_multiple_category_chart(global_df, "Mental_Health_Condition", 
                                  "Mental Health Conditions Distribution", 
                                  os.path.join(figures_dir, "mental_health_distribution"))

    create_multiple_category_chart(global_df, "Intervention_Type", 
                                  "Intervention Types Distribution", 
                                  os.path.join(figures_dir, "intervention_distribution"))

    create_multiple_category_chart(global_df, "Outcome_Measures", 
                                  "Outcome Measures Distribution", 
                                  os.path.join(figures_dir, "outcomes_distribution"))

    # Heatmap de condicions vs tipus d'intervenció
    all_conditions = []
    for conditions_str in global_df["Mental_Health_Condition"].dropna():
        conditions = [c.strip() for c in conditions_str.split(",")]
        all_conditions.extend(conditions)

    all_interventions = []
    for interventions_str in global_df["Intervention_Type"].dropna():
        interventions = [i.strip() for i in interventions_str.split(",")]
        all_interventions.extend(interventions)

    unique_conditions = sorted(list(set(all_conditions)))
    unique_interventions = sorted(list(set(all_interventions)))

    condition_intervention_matrix = pd.DataFrame(0, 
                                              index=unique_conditions,
                                              columns=unique_interventions)

    # Omplir la matriu
    for _, row in global_df.iterrows():
        if pd.isna(row["Mental_Health_Condition"]) or pd.isna(row["Intervention_Type"]):
            continue
            
        conditions = [c.strip() for c in row["Mental_Health_Condition"].split(",")]
        interventions = [i.strip() for i in row["Intervention_Type"].split(",")]
        
        for condition in conditions:
            for intervention in interventions:
                if condition in condition_intervention_matrix.index and intervention in condition_intervention_matrix.columns:
                    condition_intervention_matrix.loc[condition, intervention] += 1

    plt.figure(figsize=(14, 10))
    sns.heatmap(condition_intervention_matrix, annot=True, cmap="YlGnBu", fmt="d")
    plt.title("Mental Health Conditions vs Intervention Types (Included Studies)")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "condition_intervention_heatmap.png"))
    plt.close()

    # Estadístiques resum
    print("\nSummary Statistics (Included Studies Only):")
    print(f"Total number of included articles: {len(global_df)}")

    if "Study_Design" in global_df.columns:
        design_counts = global_df["Study_Design"].value_counts()
        print("\nStudy Design Distribution:")
        print(design_counts)

    all_conditions = []
    for conditions_str in global_df["Mental_Health_Condition"].dropna():
        conditions = [c.strip() for c in conditions_str.split(",")]
        all_conditions.extend(conditions)
    condition_counts = pd.Series(all_conditions).value_counts()
    print("\nMental Health Condition Distribution:")
    print(condition_counts)

    all_interventions = []
    for interventions_str in global_df["Intervention_Type"].dropna():
        interventions = [i.strip() for i in interventions_str.split(",")]
        all_interventions.extend(interventions)
    intervention_counts = pd.Series(all_interventions).value_counts()
    print("\nIntervention Type Distribution:")
    print(intervention_counts)

    all_outcomes = []
    for outcomes_str in global_df["Outcome_Measures"].dropna():
        outcomes = [o.strip() for o in outcomes_str.split(",")]
        all_outcomes.extend(outcomes)
    outcome_counts = pd.Series(all_outcomes).value_counts()
    print("\nOutcome Measures Distribution:")
    print(outcome_counts)

    print(f"\nResults have been saved to: {classified_file}")
    print("Visualizations have been saved to the 'figures' directory.")

if __name__ == "__main__":
    main()
