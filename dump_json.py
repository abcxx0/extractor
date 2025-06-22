# dump_json.py
import pandas as pd
import os

# 1) Lee el CSV que genera tu analysis.py
df = pd.read_csv('datos_clasificados.csv', parse_dates=['Fecha'])

# 2) Asegúrate de tener la carpeta de salida
os.makedirs('salida', exist_ok=True)

# 3) Vuelca a JSON
df.to_json(
    'salida/datos_actualizados.json',
    orient='records',
    force_ascii=False,
    date_format='iso'
)

print("✅ JSON generado en salida/datos_actualizados.json")
