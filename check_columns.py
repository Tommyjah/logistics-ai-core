import pandas as pd

# Tell pandas the column headers sit precisely on row index 4
df = pd.read_excel("November Fleet Summery.xlsx", header=4)
print("--- YOUR EXCEL COLUMNS ARE NOW DETECTED AS: ---")
print(list(df.columns))