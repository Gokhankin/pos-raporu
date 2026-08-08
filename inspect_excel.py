import pandas as pd
import openpyxl

excel_path = "Pos Satis.xlsx"

try:
    # Load excel file to inspect sheets
    xls = pd.ExcelFile(excel_path)
    print("Sheets in the excel file:", xls.sheet_names)
    
    # Let's inspect the first sheet
    for sheet_name in xls.sheet_names:
        print(f"\n--- Inspecting sheet: {sheet_name} ---")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print("Shape:", df.shape)
        print("Columns:", list(df.columns)[:15])
        print("Head:")
        print(df.head(10))
except Exception as e:
    print("Error:", e)
