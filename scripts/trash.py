import os
import pandas as pd

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Build the absolute path to the Excel file (go up one directory to the repo root)
data_path = os.path.join(script_dir, '..', 'data', 'full_data.xlsx')

# Now read the Excel file
df_full = pd.read_excel(data_path)
print(df_full.head())
