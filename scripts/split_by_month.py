#!/usr/bin/env python3
"""
Split bank and splitwise CSVs into month-wise files
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# Configuration
BANK_INPUT = "data/raw_uploads/bank_statement_full.csv"
SPLITWISE_INPUT = "data/raw_uploads/splitwise_full.csv"
OUTPUT_DIR = Path("data/monthly_splits")

# Date formats
BANK_DATE_FORMAT = "%d/%m/%y"
SPLITWISE_DATE_FORMAT = "%Y-%m-%d"

def split_bank_csv(input_file, output_dir):
    """Split bank statement by month"""
    print(f"📄 Processing bank file: {input_file}")
    
    # Find header row
    header_row = 0
    with open(input_file, 'r') as f:
        for i, line in enumerate(f):
            if "Date" in line and "Narration" in line:
                header_row = i
                break
    
    # Read CSV
    df = pd.read_csv(input_file, skiprows=header_row)
    
    df = df[~df["Date"].str.contains(r"\*+", na=False)]
    # Remove footer/summary rows
    df = df[df['Date'].notna()]
    df = df[~df['Date'].str.contains('End Of Statement|STATEMENT SUMMARY', na=False)]
    
    # Parse dates
    df['Date'] = pd.to_datetime(df['Date'], format=BANK_DATE_FORMAT)
    df['YearMonth'] = df['Date'].dt.strftime('%Y-%m')
    
    # Split by month
    for month, group in df.groupby('YearMonth'):
        output_file = output_dir / f"bank_{month}.csv"
        
        # Save without YearMonth column
        group_clean = group.drop('YearMonth', axis=1)
        group_clean.to_csv(output_file, index=False)
        
        print(f"  ✓ {month}: {len(group)} transactions → {output_file.name}")
    
    print(f"✅ Bank file split into {df['YearMonth'].nunique()} months\n")


def split_splitwise_csv(input_file, output_dir):
    """Split splitwise export by month"""
    print(f"📄 Processing splitwise file: {input_file}")
    
    # Find header row
    header_row = 0
    with open(input_file, 'r') as f:
        first_line = f.readline()
        if "Date" not in first_line:
            header_row = 1
    
    # Read CSV
    df = pd.read_csv(input_file, skiprows=header_row)
    
    # Remove footer rows
    df = df[df['Date'].notna()]
    df = df[~df['Description'].str.contains('Total balance', na=False)]
    
    # Parse dates
    df['Date'] = pd.to_datetime(df['Date'], format=SPLITWISE_DATE_FORMAT)
    df['YearMonth'] = df['Date'].dt.strftime('%Y-%m')
    
    # Split by month
    for month, group in df.groupby('YearMonth'):
        output_file = output_dir / f"splitwise_{month}.csv"
        
        # Save without YearMonth column
        group_clean = group.drop('YearMonth', axis=1)
        group_clean.to_csv(output_file, index=False)
        
        print(f"  ✓ {month}: {len(group)} transactions → {output_file.name}")
    
    print(f"✅ Splitwise file split into {df['YearMonth'].nunique()} months\n")


if __name__ == "__main__":
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("📊 SPLITTING CSVs BY MONTH")
    print("="*60)
    print()
    
    # Split bank file
    if Path(BANK_INPUT).exists():
        split_bank_csv(BANK_INPUT, OUTPUT_DIR)
    else:
        print(f"⚠️  Bank file not found: {BANK_INPUT}\n")
    
    # Split splitwise file
    # if Path(SPLITWISE_INPUT).exists():
    #     split_splitwise_csv(SPLITWISE_INPUT, OUTPUT_DIR)
    # else:
    #     print(f"⚠️  Splitwise file not found: {SPLITWISE_INPUT}\n")
    
    print("="*60)
    print("✅ DONE!")
    print("="*60)
    print(f"\nOutput files in: {OUTPUT_DIR}/")
    print("\nFiles created:")
    for file in sorted(OUTPUT_DIR.glob("*.csv")):
        print(f"  • {file.name}")