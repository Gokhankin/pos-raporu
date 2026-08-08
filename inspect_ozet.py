import pandas as pd
excel_path = "Pos Satis.xlsx"

# Print Özet_Rapor_Haziran
df_ozet_haziran = pd.read_excel(excel_path, sheet_name="Özet_Rapor_Haziran")
df_ozet_haziran.to_csv("ozet_haziran.csv", index=False)
print("Özet_Rapor_Haziran saved to ozet_haziran.csv")
print(df_ozet_haziran.head(40))
