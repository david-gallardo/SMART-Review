import os
import sys
import pandas as pd
import requests
import json
import concurrent.futures
import time
import matplotlib.pyplot as plt
import re
# Eliminem l'ús de seaborn i creem un heatmap manual amb matplotlib

# Variable per controlar el mode test: True només per 5 casos, False per tot el dataset
test = False  # Canvia a False per processar tot el dataset

# Afegir el directori de scripts al camí de Python
scripts_dir = os.path.abspath('../scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Importa funcions de main.py (suposant que existeixen)
# Assegura't que 'main.py' inclou aquestes definicions o comenta aquestes línies si no són necessàries:
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

# -------------------------------------------------------------------
# 1) Funcions per mapejar categories brutes a categories estàndard
# -------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Converteix a minúscules, lleva espais sobrants, etc.
    """
    if not isinstance(text, str):
        return ""
    return text.strip().lower()

def map_study_design(raw_design: str) -> str:
    """
    Retorna la categoria canonical de Study Design:
       - RCT (Randomized Controlled Trial)
       - Quasi-experimental (Non-randomized studies with a control group)
       - Systematic review (Systematic review or meta-analysis)
       - Observational (Cohort studies, case-control, cross-sectional)
       - Theoretical/Other (Conceptual, methodological, or narrative review)
    """
    text = normalize_text(raw_design)

    if "rct" in text or "randomized controlled trial" in text:
        return "RCT (Randomized Controlled Trial)"
    elif "quasi" in text or "non-randomized" in text or "nonrandomized" in text:
        return "Quasi-experimental (Non-randomized studies with a control group)"
    elif "systematic" in text or "meta" in text:
        return "Systematic review (Systematic review or meta-analysis)"
    elif "observational" in text or "cohort" in text or "case-control" in text or "cross-sectional" in text:
        return "Observational (Cohort studies, case-control, cross-sectional)"
    else:
        return "Theoretical/Other (Conceptual, methodological, or narrative review)"


MENTAL_HEALTH_KEYWORDS = {
    # paraula/clau  => categoria canònica
    "depress": "Depression",            # inclou "depressive", "depression", etc.
    "anxiety": "Anxiety",
    "bipolar": "Bipolar",
    "personality": "Personality disorders",
    "schizo": "Schizophrenia",          # inclou "schizophrenia", "schizoaffective", etc.
    "psychosis": "Schizophrenia",       # "early psychosis" -> "Schizophrenia"
    "general mental": "General mental health",
    "common mental": "General mental health",
}

def map_mental_health(raw_conditions_str: str) -> list:
    """
    Retorna una llista de categories canòniques de salut mental, cadascuna d’entre:
       - Depression
       - Anxiety
       - Schizophrenia
       - Bipolar
       - Personality disorders
       - General mental health
       - Multiple specific conditions
       - Other (please specify)
    """
    if not isinstance(raw_conditions_str, str) or not raw_conditions_str.strip():
        return ["Other (please specify)"]

    # separem el text original per comes, punts i comes, etc.
    raw_conditions = [normalize_text(x) for x in re.split(r"[;,]", raw_conditions_str) if x.strip()]

    mapped_categories = set()
    for cond in raw_conditions:
        matched = False
        for key, val in MENTAL_HEALTH_KEYWORDS.items():
            if key in cond:
                mapped_categories.add(val)
                matched = True
        if not matched:
            # Qualsevol cosa fora de les paraules clau entra a 'Other'
            mapped_categories.add("Other (please specify)")

    # Si vols forçar que si hi ha >1 categoria diferent es converteixi a "Multiple specific conditions",
    # descomenta el següent:
    #
    # if len(mapped_categories) > 1 and "Other (please specify)" not in mapped_categories:
    #     return ["Multiple specific conditions"]
    #
    # Si prefereixes llistar-ho tot, ho deixes tal qual.

    return sorted(mapped_categories)


INTERVENTION_KEYWORDS = {
    # paraula/clau  => categoria canònica
    "supported employment": "Supported employment",
    "ips": "Supported employment",  # IPS és un tipus concret de supported employment
    "vocational rehab": "Vocational rehabilitation",
    "vocational rehabilit": "Vocational rehabilitation",
    "job search": "Job search assistance",
    "skills training": "Skills training",
    "workplace accommodation": "Workplace accommodations",
    "return to work": "Return-to-work programs",
    "return-to-work": "Return-to-work programs",
}

def map_intervention_type(raw_interventions_str: str) -> list:
    """
    Retorna una llista de categories canòniques d’intervenció:
       - Supported employment
       - Vocational rehabilitation
       - Job search assistance
       - Skills training
       - Workplace accommodations
       - Return-to-work programs
       - Multiple interventions
       - Other (please specify)
    """
    if not isinstance(raw_interventions_str, str) or not raw_interventions_str.strip():
        return ["Other (please specify)"]

    raw_interventions = [normalize_text(x) for x in re.split(r"[;,]", raw_interventions_str) if x.strip()]

    mapped_categories = set()
    for interv in raw_interventions:
        matched = False
        for key, val in INTERVENTION_KEYWORDS.items():
            if key in interv:
                mapped_categories.add(val)
                matched = True
        if not matched:
            mapped_categories.add("Other (please specify)")

    return sorted(mapped_categories)


OUTCOME_KEYWORDS = {
    # paraula/clau  => categoria canònica
    "employment rate": "Employment rate",
    "job retention": "Job retention",
    "income/earnings": "Income/earnings",
    "income": "Income/earnings",   # si detectes "income" sol, el mapejem
    "earnings": "Income/earnings", # idem
    "work functioning": "Work functioning",
    "mental health improvement": "Mental health improvement",
    "quality of life": "Quality of life",
    "qol": "Quality of life"
}

def map_outcome_measures(raw_outcomes_str: str) -> list:
    """
    Retorna una llista de categories canòniques de resultats:
       - Employment rate
       - Job retention
       - Income/earnings
       - Work functioning
       - Mental health improvement
       - Quality of life
       - Multiple outcomes
       - Other (please specify)
    """
    if not isinstance(raw_outcomes_str, str) or not raw_outcomes_str.strip():
        return ["Other (please specify)"]

    raw_outcomes = [normalize_text(x) for x in re.split(r"[;,]", raw_outcomes_str) if x.strip()]

    mapped_categories = set()
    for outc in raw_outcomes:
        matched = False
        for key, val in OUTCOME_KEYWORDS.items():
            if key in outc:
                mapped_categories.add(val)
                matched = True
        if not matched:
            mapped_categories.add("Other (please specify)")

    return sorted(mapped_categories)


def apply_mappings_to_global_df(global_df):
    """
    Aplica el mapeig sobre les columnes de la classificació global i retorna
    un nou DataFrame amb columnes 'Mapped_Study_Design', 'Mapped_Mental_Health_Condition',
    'Mapped_Intervention_Type', 'Mapped_Outcome_Measures'.
    """
    df = global_df.copy()

    # Mapejar Study Design
    df["Mapped_Study_Design"] = df["Study_Design"].apply(map_study_design)

    # Mapejar Mental Health Condition
    df["Mapped_Mental_Health_Condition"] = df["Mental_Health_Condition"].apply(map_mental_health)

    # Mapejar Intervention Type
    df["Mapped_Intervention_Type"] = df["Intervention_Type"].apply(map_intervention_type)

    # Mapejar Outcome Measures
    df["Mapped_Outcome_Measures"] = df["Outcome_Measures"].apply(map_outcome_measures)

    return df

# -------------------------------------------------------------------
# 2) Funcions originals de classificació
# -------------------------------------------------------------------

def classify_abstract(model_name, title, abstract):
    """Query LLM per classificar un abstract segons disseny, condicions, etc."""
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
        
        # Neteja la resposta per extreure el JSON
        cleaned_text = generated_text.replace("```json", "").replace("```", "").strip()
        
        # Per al model phi-3-mini, fem una extracció de bloc JSON específica
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
    
    # Combina title i abstract si abstract és buit
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
    
    # Calcular la classificació global basant-se en tots els resultats
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
    
    # Guarda el resultat de l'article com a fitxer JSON a ./output/postprocessed
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
    
    return record, global_record

def print_unique_categories(global_df):
    """Imprimeix els valors únics de cada camp de classificació global."""
    # Study Design
    unique_study_design = sorted(global_df['Study_Design'].dropna().unique())
    print("Unique Study Design values:")
    print(unique_study_design)
    
    # Mental Health Condition (multiselect)
    all_conditions = []
    for conditions_str in global_df["Mental_Health_Condition"].dropna():
        conditions = [cat.strip() for cat in conditions_str.split(",")]
        all_conditions.extend(conditions)
    unique_conditions = sorted(set(all_conditions))
    print("\nUnique Mental Health Condition values:")
    print(unique_conditions)
    
    # Intervention Type
    all_interventions = []
    for interventions_str in global_df["Intervention_Type"].dropna():
        interventions = [item.strip() for item in interventions_str.split(",")]
        all_interventions.extend(interventions)
    unique_interventions = sorted(set(all_interventions))
    print("\nUnique Intervention Type values:")
    print(unique_interventions)
    
    # Outcome Measures
    all_outcomes = []
    for outcomes_str in global_df["Outcome_Measures"].dropna():
        outcomes = [item.strip() for item in outcomes_str.split(",")]
        all_outcomes.extend(outcomes)
    unique_outcomes = sorted(set(all_outcomes))
    print("\nUnique Outcome Measures values:")
    print(unique_outcomes)


# -------------------------------------------------------------------
# 3) Funcions per a gràfics amb matplotlib (sense seaborn)
# -------------------------------------------------------------------

def create_multiple_category_chart(df, column_name, chart_title, output_path):
    """
    Crea un diagrama de barres simple, comptant la freqüència de cadascuna
    de les categories aparegudes al camp `column_name` (que és llista o string).
    Desa la figura a output_path + ".png".
    """
    # Si el camp és tipus llista, l'hem de "flatten"
    all_items = []
    for val in df[column_name].dropna():
        # Pot ser string separat per comes o directament una llista
        if isinstance(val, list):
            all_items.extend(val)
        else:
            # suposem que pot ser un string separat per comes
            items = [x.strip() for x in val.split(",")]
            all_items.extend(items)

    freq = pd.Series(all_items).value_counts()

    plt.figure(figsize=(10, 6))
    freq.plot(kind="bar")
    plt.xlabel(column_name)
    plt.ylabel("Frequency")
    plt.title(chart_title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path + ".png")
    plt.close()


import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd

def create_heatmap_condition_intervention(df, condition_col, intervention_col, title, output_path):
    """
    Crea un heatmap mostrant la freqüència de coocurrència
    entre `condition_col` i `intervention_col`, amb una paleta de colors personalitzada.
    """
    # Recollim totes les condicions i intervencions de manera plana
    all_conditions = set()
    all_interventions = set()

    for idx, row in df.iterrows():
        conds = row[condition_col]
        intervs = row[intervention_col]

        # Convertim conds, intervs a llistes si són strings separats per comes
        if isinstance(conds, str):
            conds = [x.strip() for x in conds.split(",")]
        if isinstance(intervs, str):
            intervs = [x.strip() for x in intervs.split(",")]
        if not isinstance(conds, list):
            conds = []
        if not isinstance(intervs, list):
            intervs = []

        for c in conds:
            all_conditions.add(c)
        for i in intervs:
            all_interventions.add(i)

    # Convertim a llista ordenada per ser índex de files i columnes
    condition_list = sorted(all_conditions)
    intervention_list = sorted(all_interventions)

    # Creem la matriu de comptatge
    matrix = [[0]*len(intervention_list) for _ in range(len(condition_list))]

    # Omplim la matriu comptant les coocurrències
    for idx, row in df.iterrows():
        conds = row[condition_col]
        intervs = row[intervention_col]
        if isinstance(conds, str):
            conds = [x.strip() for x in conds.split(",")]
        if isinstance(intervs, str):
            intervs = [x.strip() for x in intervs.split(",")]
        if not isinstance(conds, list):
            conds = []
        if not isinstance(intervs, list):
            intervs = []

        for c in conds:
            for i in intervs:
                if c in condition_list and i in intervention_list:
                    c_idx = condition_list.index(c)
                    i_idx = intervention_list.index(i)
                    matrix[c_idx][i_idx] += 1

    # Creem un DataFrame amb la matriu
    matrix_df = pd.DataFrame(matrix, index=condition_list, columns=intervention_list)

    # ---------- DEFINICIÓ DE LA COLORMAP PERSONALITZADA ----------
    # Colors aproximats a la gamma YlGnBu de ColorBrewer
    color_list = [
        "#ffffcc",  # groc clar
        "#a1dab4",  # verd clar
        "#41b6c4",  # turquesa
        "#2c7fb8",  # blau mitjà
        "#253494"   # blau fosc
    ]
    custom_cmap = mcolors.LinearSegmentedColormap.from_list("custom_ylgnbu", color_list, N=256)
    # -------------------------------------------------------------

    # Dibuixem el heatmap
    plt.figure(figsize=(14, 10))
    # Fem servir el colormap custom
    img = plt.imshow(matrix_df, cmap=custom_cmap, aspect="auto")
    plt.colorbar(img, label="Count")

    # Posem el valor de cada cel·la
    for row_idx in range(len(condition_list)):
        for col_idx in range(len(intervention_list)):
            value = matrix_df.iloc[row_idx, col_idx]
            plt.text(col_idx, row_idx, str(value),
                     ha="center", va="center", color="black")

    plt.xticks(range(len(intervention_list)), intervention_list, rotation=45, ha="right")
    plt.yticks(range(len(condition_list)), condition_list)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path + ".png")
    plt.close()



# -------------------------------------------------------------------
# 4) Funció principal
# -------------------------------------------------------------------

def main():
    """
    Funció principal per analitzar i classificar els articles inclosos basant-se en diverses dimensions:
    - Disseny de l'estudi
    - Condicions de salut mental
    - Tipus d'intervenció
    - Mesures de resultat

    Aquesta funció:
    1. Carrega el dataset original i filtra els estudis inclosos.
    2. O carrega les dades classificades existents o consulta l'LLM per classificar els articles.
    3. Aplica un mapeig de categories per unificar noms.
    4. Genera visualitzacions per a les classificacions (basades en les categories mapejades).
    5. Proporciona estadístiques resum.
    """
    print("Loading original dataset...")
    original_df = pd.read_excel(original_file)
    
    # Mapear valors de GlobalInclusion
    global_inclusion_mapping = {"Yes": "Included", "No": "Excluded", "Unclear": "Unclear"}
    original_df["GlobalInclusion"] = original_df["GlobalInclusion"].map(global_inclusion_mapping)
    
    # Filtrar només estudis inclosos
    included_df = original_df[original_df["GlobalInclusion"] == "Included"].copy()
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
        if test:
            all_model_df = all_model_df.head(5)
            global_df = global_df.head(5)
    else:
        print("Classified file not found. Querying LLM to classify included studies...")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = {executor.submit(process_article, idx, row): idx for idx, row in included_df.iterrows()}
            for future in concurrent.futures.as_completed(futures):
                record, global_record = future.result()
                if record is not None:
                    all_results.append(record)
                    global_results.append(global_record)
        
        all_model_df = pd.DataFrame(all_results)
        global_df = pd.DataFrame(global_results)
        
        with pd.ExcelWriter(classified_file) as writer:
            all_model_df.to_excel(writer, sheet_name="All_Models", index=False)
            global_df.to_excel(writer, sheet_name="Global_Decision", index=False)
        
        print(f"Classification complete. Results saved to {classified_file}")
    
    # Imprimeix els valors únics "bruts" per ajudar amb el mapeig
    print("\nUnique categories in global classification (raw):")
    print_unique_categories(global_df)

    # ----------------------------------------------------------------
    # APARTAT NOU: apliquem el mapeig de categories
    # ----------------------------------------------------------------
    mapped_global_df = apply_mappings_to_global_df(global_df)

    # Creem unes columnes que potser volem en format "string separat per comes" en lloc de llistes
    # Això facilita la visualització o l'export final
    mapped_global_df["Mapped_Mental_Health_Condition_str"] = mapped_global_df["Mapped_Mental_Health_Condition"].apply(lambda x: ", ".join(x))
    mapped_global_df["Mapped_Intervention_Type_str"] = mapped_global_df["Mapped_Intervention_Type"].apply(lambda x: ", ".join(x))
    mapped_global_df["Mapped_Outcome_Measures_str"] = mapped_global_df["Mapped_Outcome_Measures"].apply(lambda x: ", ".join(x))

    # Guardem el fitxer d'articles ja amb el mapeig final:
    final_mapped_file = os.path.join(data_path, "included_articles_classified_MAPPED.xlsx")
    mapped_global_df.to_excel(final_mapped_file, index=False)
    print(f"\nMapped classification saved to: {final_mapped_file}")

    # Ara fem els gràfics basats en les columnes mapejades
    print("Generating visualizations with mapped columns...")
    
    figures_dir = os.path.join(os.getcwd(), "figures", "charts")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir, exist_ok=True)

    # 1) Distribució de Study Design (mapejat)
    plt.figure(figsize=(10, 6))
    mapped_global_df["Mapped_Study_Design"].value_counts().plot(kind="bar")
    plt.xlabel("Study Design (mapped)")
    plt.ylabel("Number of Articles")
    plt.title("Distribution of Study Types (Included Studies) - Mapped")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "study_design_distribution_mapped.png"))
    plt.close()

    # 2) Distribució de categories múltiples (mapejades)
    create_multiple_category_chart(
        mapped_global_df,
        "Mapped_Mental_Health_Condition",
        "Mental Health Conditions Distribution (Mapped)",
        os.path.join(figures_dir, "mental_health_distribution_mapped")
    )

    create_multiple_category_chart(
        mapped_global_df,
        "Mapped_Intervention_Type",
        "Intervention Types Distribution (Mapped)",
        os.path.join(figures_dir, "intervention_distribution_mapped")
    )

    create_multiple_category_chart(
        mapped_global_df,
        "Mapped_Outcome_Measures",
        "Outcome Measures Distribution (Mapped)",
        os.path.join(figures_dir, "outcomes_distribution_mapped")
    )

    # 3) Heatmap condicions vs. tipus d'intervenció (basat en columnes mapejades)
    create_heatmap_condition_intervention(
        mapped_global_df,
        "Mapped_Mental_Health_Condition",
        "Mapped_Intervention_Type",
        "Mental Health Conditions vs Intervention Types (Mapped)",
        os.path.join(figures_dir, "condition_intervention_heatmap_mapped")
    )

    # 4) Estadístiques resum
    print("\nSummary Statistics (Included Studies Only, MAPPED categories):")
    print(f"Total number of included articles: {len(mapped_global_df)}")

    design_counts = mapped_global_df["Mapped_Study_Design"].value_counts()
    print("\nStudy Design Distribution (mapped):")
    print(design_counts)

    # Per a mental health (multiselect) -> aplanem
    all_conditions = []
    for cond_list in mapped_global_df["Mapped_Mental_Health_Condition"]:
        all_conditions.extend(cond_list)
    condition_counts = pd.Series(all_conditions).value_counts()
    print("\nMental Health Condition Distribution (mapped):")
    print(condition_counts)

    # Interventions
    all_interventions = []
    for intv_list in mapped_global_df["Mapped_Intervention_Type"]:
        all_interventions.extend(intv_list)
    intervention_counts = pd.Series(all_interventions).value_counts()
    print("\nIntervention Type Distribution (mapped):")
    print(intervention_counts)

    # Outcomes
    all_outcomes = []
    for outc_list in mapped_global_df["Mapped_Outcome_Measures"]:
        all_outcomes.extend(outc_list)
    outcome_counts = pd.Series(all_outcomes).value_counts()
    print("\nOutcome Measures Distribution (mapped):")
    print(outcome_counts)

    print("\nVisualizations have been saved to the 'figures' directory.")
    print("Done!")


if __name__ == "__main__":
    main()
