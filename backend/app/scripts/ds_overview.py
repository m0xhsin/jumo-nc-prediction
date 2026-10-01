import pandas as pd
import numpy as np
import sys

# Laser dataset overview
laser = pd.read_csv("initdb.d/raw_data/Laser.csv", sep=";")
print(laser['OPERATOR'].value_counts())

selektion = pd.read_csv("initdb.d/raw_data/Selektion.csv", sep=";")
print(selektion['FA'].value_counts())

siebdruck = pd.read_csv("initdb.d/raw_data/Siebdruck-Screen Printing_trimmed.csv", sep=";")
print(siebdruck.iloc[:20, :20])

print(siebdruck.info())

sputtern = pd.read_csv("initdb.d/raw_data/Sputtern-Sputtering_trimmed.csv", sep=";")
print(sputtern.iloc[:20, :20])

print(sputtern.info())

substrate = pd.read_csv("initdb.d/raw_data/Substrate_trimmed.csv", sep=";")
print(substrate.iloc[:20, :20])

print(substrate.info())

# not working with latin1 enc.
partnumbers = pd.read_csv("initdb.d/raw_data/partnumbers-utf8.csv", sep=";")

print(partnumbers['MADP'].value_counts())

sys.exit()


list_of_dfs = [fertigungsauftrag, laser, selektion, siebdruck, sputtern, substrate, partnumbers]
list_of_names = ["fertigungsauftrag", "laser", "selektion", "siebdruck", "sputtern", "substrate", "partnumbers"]

# check for common columns between the dataframes, maybe needed to join later
# Common columns are 'FA', 'FA_ID', 'SUBSTRAT_ID', 'CREATED'. 'UPDATED', TYPTCA'
for i, x in enumerate(list_of_dfs):
    for j, y in enumerate(list_of_dfs):
        if x is not y:
            print(f"Comparing {list_of_names[i]} and {list_of_names[j]}")
            print(np.intersect1d(x.columns, y.columns))
