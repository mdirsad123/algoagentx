import os
import pandas as pd

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build full paths to the CSV files
bse_path = os.path.join(BASE_DIR, "Equity_bse_list.csv")
nse_path = os.path.join(BASE_DIR, "Equity_nse_list.csv")

# Load CSVs
df_bse = pd.read_csv(bse_path)
df_nse = pd.read_csv(nse_path)

# Rename columns to common names
df_bse.rename(columns={
    "ISIN No": "ISIN",
    "Security Code": "BSE_CODE"
}, inplace=True)

df_nse.rename(columns={
    "ISIN NUMBER": "ISIN",
    "SYMBOL": "NSE_SYMBOL"
}, inplace=True)

# Drop rows where ISIN is missing
df_bse.dropna(subset=["ISIN"], inplace=True)
df_nse.dropna(subset=["ISIN"], inplace=True)

# Merge both datasets using ISIN
df_map = pd.merge(df_bse, df_nse, on="ISIN", how="inner")

# Add .NS to NSE symbol for yfinance compatibility
df_map["NSE_SYMBOL"] = df_map["NSE_SYMBOL"].astype(str) + ".NS"

# Select required columns
df_final_map = df_map[["BSE_CODE", "NSE_SYMBOL"]].drop_duplicates()

# Rename for clarity
df_final_map.rename(columns={"BSE_CODE": "bse_code", "NSE_SYMBOL": "nse_symbol"}, inplace=True)

# Save mapping to file in same directory
output_path = os.path.join(BASE_DIR, "bse_nse_mapping.csv")
df_final_map.to_csv(output_path, index=False)

print("✅ Mapping completed. Sample:")
print(df_final_map.head())
