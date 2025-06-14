import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

# --- Cargar y preparar datos ---
df = pd.read_csv('datos_clasificados.csv', sep=';', encoding='utf-8')
df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
df['Dia_Semana'] = df['Fecha'].dt.day_name()

# --- Filtrar periodo de análisis ---
fecha_inicio = datetime(2025, 5, 20)
fecha_fin = datetime(2025, 6, 17)
df = df[(df['Fecha'] >= fecha_inicio) & (df['Fecha'] <= fecha_fin)].copy()

# --- Agrupar por tópico ---
agregado = df.groupby('Topico_Final').agg(
    Cantidad_Notas=('ID', 'count'),
    Total_Vistas=('Vistas', 'sum')
)
agregado['Vistas_por_Nota'] = agregado['Total_Vistas'] / agregado['Cantidad_Notas']
agregado = agregado.sort_values('Total_Vistas', ascending=False)

# --- Crear carpeta de salida ---
os.makedirs('salida', exist_ok=True)

# --- Gráfico 1: Publicaciones y vistas ---
plt.figure(figsize=(12, 6))
agregado[['Cantidad_Notas', 'Total_Vistas']].plot(kind='bar')
plt.title('Notas publicadas y vistas por tópico (20/05 al 17/06)')
plt.ylabel('Cantidad')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('salida/publicaciones_y_vistas.png')

# --- Gráfico 2: Eficiencia (vistas por nota) ---
plt.figure(figsize=(12, 6))
agregado['Vistas_por_Nota'].plot(kind='bar', color='green')
plt.title('Eficiencia: Vistas promedio por nota')
plt.ylabel('Vistas por Nota')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('salida/vistas_por_nota.png')

# --- Gráfico 3: Heatmap por día y tópico ---
pivot = df.pivot_table(index='Dia_Semana', columns='Topico_Final', values='Vistas', aggfunc='sum', fill_value=0)
orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
pivot = pivot.reindex(orden_dias)

plt.figure(figsize=(14, 6))
sns.heatmap(pivot, cmap="coolwarm", annot=True, fmt=".0f", linewidths=.5)
plt.title('Heatmap: Vistas por día de la semana y tópico')
plt.tight_layout()
plt.savefig('salida/heatmap_dia_topico.png')

# --- Gráfico 4: Dispersión eficiencia vs cantidad ---
plt.figure(figsize=(10, 6))
plt.scatter(agregado['Cantidad_Notas'], agregado['Vistas_por_Nota'], s=100, alpha=0.7)
for i, txt in enumerate(agregado.index):
    plt.annotate(txt, (agregado['Cantidad_Notas'][i], agregado['Vistas_por_Nota'][i]))
plt.xlabel('Cantidad de notas')
plt.ylabel('Vistas por nota')
plt.title('Dispersión: eficiencia vs volumen de publicaciones')
plt.grid(True)
plt.tight_layout()
plt.savefig('salida/dispersión_eficiencia_volumen.png')

# --- Generar HTML básico con resultados ---
with open('salida/informe.html', 'w', encoding='utf-8') as f:
    f.write("""
    <html><head><title>Informe Semanal de Noticias</title></head><body>
    <h1>Informe de Noticias (20/05 al 17/06)</h1>
    <h2>1. Publicaciones y Vistas por Tópico</h2>
    <img src='publicaciones_y_vistas.png' width='800'>
    <h2>2. Eficiencia: Vistas Promedio por Nota</h2>
    <img src='vistas_por_nota.png' width='800'>
    <h2>3. Comportamiento por Día y Tópico</h2>
    <img src='heatmap_dia_topico.png' width='1000'>
    <h2>4. Dispersión: Eficiencia vs Volumen</h2>
    <img src='dispersión_eficiencia_volumen.png' width='800'>
    </body></html>
    """)

print("✅ Informe generado en la carpeta 'salida'.")
