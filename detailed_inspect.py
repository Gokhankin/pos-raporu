import pandas as pd
import numpy as np

excel_path = "Pos Satis.xlsx"
xls = pd.ExcelFile(excel_path)

def inspect_sheet_layout(sheet_name):
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    print(f"\n=================== SHEET: {sheet_name} ===================")
    print("Shape:", df.shape)
    
    # Check non-null values per cell to find table boundaries
    # We can inspect non-empty cells
    row_count = len(df)
    col_count = len(df.columns)
    
    # Print the first 50 rows, but only columns that have some data
    # Let's save a readable representation
    rep = []
    for r in range(min(100, row_count)):
        row_vals = []
        for c in range(col_count):
            val = df.iloc[r, c]
            if pd.isna(val):
                row_vals.append("")
            else:
                row_vals.append(str(val))
        # if the row is not completely empty, print it
        if any(v != "" for v in row_vals):
            rep.append(f"Row {r:02d}: " + " | ".join(f"C{c}:{v}" for c, v in enumerate(row_vals) if v != ""))
            
    print("\n".join(rep[:60]))

for name in ['Özet_Rapor_Haziran', 'Özet_Rapor_Mayıs']:
    inspect_sheet_layout(name)
