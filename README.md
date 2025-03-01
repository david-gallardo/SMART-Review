# SMART Review

**SMART Review** stands for **Systematic Manuscript Analysis and Review Tool**. It is an AI-driven project designed to automate and streamline the screening and evaluation process of research manuscripts for systematic reviews. The tool leverages local large language models (LLMs) via the LMStudio API to assess articles against predefined inclusion and exclusion criteria. **The research question and screening criteria are externalized in text files (inclusion_criteria.txt, exclusion_criteria.txt, research_question.txt) located in the scripts/utilities folder.**

## Features

- **Automated Screening:** Evaluate research articles based on rigorous inclusion and exclusion criteria.
- **Parallel Processing:** Utilize multiple local LLMs concurrently to accelerate the review process.
- **Structured Output:** Generate structured JSON responses from each model and aggregate decisions.
- **Statistical Analysis:** Compute inter-rater reliability metrics, including Fleiss' Kappa and pairwise agreement.
- **Modular Design:** Easily extendable and adaptable to various systematic review tasks.

## Repository Structure

```bash
SMART-Review/ 
├── data/ 
│ ├── raw/ # Original datasets or Excel files 
│ └── README.md # Data folder documentation 
├── documents/ 
│ ├── proposals/ # Project proposals and design documents 
│ ├── reports/ # Meeting notes and progress reports 
│ └── README.md # Documentation about project documents 
├── figures/ 
│ ├── charts/ # Visualizations and charts generated during analysis 
│ └── README.md # Explanation of figures and sources 
├── output/ 
│ ├── processed/ # Final processed output files (e.g., reports, results) 
│ └── README.md # Overview of output files and formats 
├── scripts/ 
│ ├── analysis/ # Scripts for data analysis and processing 
│ ├── utilities/ # inclusion_criteria.txt, exclusion_criteria.txt &research_question.txt 
│ └── main.py # Main script to run the project 
├── README.md # This file 
├── LICENSE # License file
└── requirements.txt # Python dependencies
```

## Installation

1. **Clone the Repository:**

```bash
   git clone https://github.com/david-gallardo/SMART-Review.git
   cd SMART-Review
   ```

2. **Install Dependencies:**

Ensure you have Python 3 installed, then run:
```bash
   pip install -r requirements.txt
   ```  

## Usage

1. **Prepare Your Data:**
Place your input data (e.g., Excel files with research articles) into the data/ folder.

2. **Run the Main Script:**
Execute the main script to perform the automated screening and review:

```bash
python scripts/main.py
```

3. **Review the output**
Processed results will be saved in the output/processed directory.

4. **Update Criteria (Optional):**
You can update the research question and screening criteria by editing the text files in the scripts/utilities folder.

## Contributing

Contributions are welcome! To contribute:

   - Fork the repository.
   - Create a new branch for your feature or bug fix.
   - Commit your changes.
   - Open a pull request with a clear description of your modifications.

## License

This project is licensed under the MIT License – see the LICENSE file for details.

## Contact

For questions, suggestions, or support, please contact david.gallardo@ub.edu.
