"""
Genera un informe PDF con visualizaciones clave
a partir de datos_clasificados.csv (separador = coma).
"""

import os, sys, subprocess, json, datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

# ───────────────────────────────────────────────────────────────
# Instalar adjustText “on-the-fly” si hace falta
try:
    from adjustText import adjust_text
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "adjustText"])
    from adjustText import adjust_text

# ───────────────────────────────────────────────────────────────
### NUEVO: función para generar la portada del PDF
def portada(pdf, resumen_bullets, kpi_row, fecha_hoy):
    fig = plt.figure(figsize=(8.27, 11.69))            # A4 vertical

    # 1) Título y subtítulo
    fig.text(0.5, 0.93, "Informe semanal de tráfico",
             ha="center", va="top", weight="bold", size=24)
    fig.text(0.5, 0.88, "Dónde ganamos y dónde perderíamos clics",
             ha="center", va="top", size=16, color="#005FAB")

    # ── AQUÍ van las tres líneas de layout ─────────────────────
    tbl_y      = 0.55        # desplaza la tabla hacia abajo
    bullet_y0  = 0.48        # punto de partida de los bullets
    table_font = 12          # tamaño de fuente de la tabla
    # -----------------------------------------------------------

    # 2) Tabla KPI (usando tbl_y)
    col_labels = ["Notas", "Vistas", "1.º tema", "Eficiencia top"]
    table = plt.table(cellText=[kpi_row],
                  colLabels=col_labels,
                  cellLoc="center",
                  bbox=[0.15, tbl_y, 0.7, 0.12])   # x, y, ancho, alto en coords figura
    table.auto_set_font_size(False)
    table.set_fontsize(table_font)
    table.scale(1, 2.5)


    # 3) Bullets (usando bullet_y0)
    for i, line in enumerate(resumen_bullets):
        fig.text(0.07, bullet_y0 - i*0.035, f"• {line}",
                 size=12, va="top")

    # 4) Pie de página
    fig.text(0.5, 0.05,
             f"Generado automáticamente · {fecha_hoy:%d %b %Y}",
             ha="center", size=8, color="gray")

    # 5) Guardar la página
    pdf.savefig(fig)
    plt.close()


# ───────────────────────────────────────────────────────────────
CSV = "datos_clasificados.csv"
df  = pd.read_csv(CSV, parse_dates=["Fecha"])

# ───────────────────────────────────────────────────────────────
# Definir rango incremental (start_date, end_date)
# ───────────────────────────────────────────────────────────────
STATE = ".ultima_fecha_analizada.json"

if os.path.exists(STATE):
    with open(STATE) as f:
        last_date = dt.date.fromisoformat(json.load(f)["ultima_fecha"])
    start_date = last_date + dt.timedelta(days=1)       # día siguiente
else:
    # Primera vez: 4 semanas hacia atrás desde la fecha más reciente
    start_date = (df["Fecha"].max() - pd.Timedelta(weeks=4)).date()

end_date   = df["Fecha"].max().date()                   # fecha más reciente
rango_str  = f"{start_date:%d/%m} – {end_date:%d/%m}"   # para títulos dinámicos

# Filtrar dataframe SOLO al rango deseado
mask = (df["Fecha"].dt.date >= start_date) & (df["Fecha"].dt.date <= end_date)
df   = df.loc[mask]

# Añadir columna Día_Semana (inglés; cambia a español si prefieres)
df["Dia_Semana"] = df["Fecha"].dt.day_name()

# ───────────────────────────────────────────────────────────────
# KPI y datasets auxiliares
# ───────────────────────────────────────────────────────────────
kpi = (df.groupby("Topico_Final")
         .agg(Notas=("ID", "count"),
              Vistas=("Vistas", "sum"))
         .sort_values("Vistas", ascending=False))
kpi["Vistas/Nota"] = kpi["Vistas"] / kpi["Notas"]
kpi["% Notas"]     = (kpi["Notas"]  / kpi["Notas"].sum()  * 100).round(1)
kpi["% Vistas"]    = (kpi["Vistas"] / kpi["Vistas"].sum() * 100).round(1)

pareto     = kpi["Vistas"].cumsum() / kpi["Vistas"].sum() * 100
mean_views = kpi["Vistas/Nota"].sort_values(ascending=False)
disp       = (pd.DataFrame({"Notas": kpi["Notas"],
                            "Vistas_x_Nota": kpi["Vistas/Nota"],
                            "Total_Vistas": kpi["Vistas"]})
              .reset_index())
totales    = kpi[["Notas", "Vistas"]].reset_index()
pivot      = (df.pivot_table(index="Dia_Semana",
                             columns="Topico_Final",
                             values="Vistas",
                             aggfunc="sum",
                             fill_value=0)
                .reindex(["Monday","Tuesday","Wednesday","Thursday",
                           "Friday","Saturday","Sunday"]))

# ───────────────── NUEVO: datos para la portada ────────────────
today          = pd.Timestamp.today()
tot_notas      = int(kpi["Notas"].sum())
tot_vistas     = int(kpi["Vistas"].sum())
top_tema       = kpi.index[0]                         # tema con más vistas
ef_top         = kpi.loc[top_tema, "Vistas/Nota"]

resumen_ideas = [
    "Concentrar esfuerzos en Policial y Justicia",
    "Revisar Finanzas y Turismo (baja tracción)",
    "Mantener volumen en Deportes, pero subir eficiencia",
]
kpi_row = [tot_notas, tot_vistas, top_tema, f"{ef_top:.1f} v/n"]
# ───────────────────────────────────────────────────────────────

# ───────────────────────────────────────────────────────────────
# Crear carpeta de salida y PDF consolidado
# ───────────────────────────────────────────────────────────────
OUT_DIR = "salida"
os.makedirs(OUT_DIR, exist_ok=True)

with PdfPages(f"{OUT_DIR}/informe_analisis.pdf") as pdf:

    # 0) Portada
    portada(pdf, resumen_ideas, kpi_row, today)

    # 1) Tabla KPI
    fig, ax = plt.subplots(figsize=(10, 0.6 + 0.28*len(kpi)))
    ax.axis("off")
    tbl = ax.table(cellText=kpi.round(2).values,
                   colLabels=kpi.columns,
                   rowLabels=kpi.index,
                   loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.4)
    ax.set_title(f"KPI por tópico ({rango_str})", fontsize=12, pad=12)
    pdf.savefig(fig); plt.close()

    # 2) Pareto
    fig, ax1 = plt.subplots(figsize=(10,5))
    ax1.bar(kpi.index, kpi["Vistas"], color="skyblue")
    ax1.set_ylabel("Vistas acumuladas")
    ax1.tick_params(axis="x", labelrotation=45)
    plt.setp(ax1.get_xticklabels(), ha="right")
    ax2 = ax1.twinx()
    ax2.plot(pareto.index, pareto, color="orange", marker="o")
    ax2.set_ylabel("% acumulado")
    ax2.set_ylim(0, 100); ax2.axhline(80, ls="--", color="grey")
    ax1.set_title("Pareto de vistas acumuladas por tópico")
    fig.tight_layout(); pdf.savefig(fig); plt.close()

    # 3) Barras Vistas/Nota
    fig, ax = plt.subplots(figsize=(10,5))
    mean_views.plot(kind="bar", ax=ax, color="#228B22")
    ax.set_ylabel("Vistas por nota")
    ax.set_title("Eficiencia: vistas promedio por nota")
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.1f}",
                    (p.get_x()+p.get_width()/2, p.get_height()),
                    ha='center', va='bottom', fontsize=8)
    ax.tick_params(axis="x", labelrotation=45)
    plt.setp(ax.get_xticklabels(), ha="right")
    fig.tight_layout(); pdf.savefig(fig); plt.close()

    # 4) Dispersión eficiencia vs volumen
    fig, ax = plt.subplots(figsize=(10,6))
    sizes = disp["Total_Vistas"] / 10  # ajusta si las burbujas se ven pequeñas
    ax.scatter(disp["Notas"], disp["Vistas_x_Nota"], s=sizes, alpha=0.7)
    ax.axhline(disp["Vistas_x_Nota"].mean(), ls='--', lw=1, color="grey")
    ax.axvline(disp["Notas"].mean(),        ls='--', lw=1, color="grey")
    for x, y, lbl in zip(disp["Notas"], disp["Vistas_x_Nota"], disp["Topico_Final"]):
        ax.text(x, y, lbl)
    ax.set_xlabel("Cantidad de notas")
    ax.set_ylabel("Vistas por nota")
    ax.set_title("Eficiencia vs volumen (tamaño = vistas totales)")
    fig.tight_layout(); pdf.savefig(fig); plt.close()

    # 5) Barras agrupadas Notas / Vistas
    fig, ax = plt.subplots(figsize=(10,5))
    idx = range(len(totales))
    ax.bar(idx, totales["Notas"], width=0.4, label="Notas", color="#1f77b4")
    ax.bar([i+0.4 for i in idx], totales["Vistas"], width=0.4,
           label="Vistas", color="#ff7f0e")
    ax.set_xticks([i+0.2 for i in idx])
    ax.set_xticklabels(totales["Topico_Final"], rotation=45, ha="right")
    ax.set_title(f"Notas publicadas y vistas por tópico\n({rango_str})")
    ax.set_ylabel("Cantidad")
    ax.legend()
    fig.tight_layout(); pdf.savefig(fig); plt.close()

    # 6) Heatmap día de la semana × tópico
    fig, ax = plt.subplots(figsize=(14,5))
    sns.heatmap(pivot, fmt='d', annot=True, cmap="coolwarm", ax=ax,
                cbar_kws=dict(label="Vistas"))
    ax.set_title("Heatmap: vistas por día de la semana y tópico")
    ax.set_xlabel("Tópico")
    fig.tight_layout(); pdf.savefig(fig); plt.close()

print(f"✅ Informe generado: {OUT_DIR}/informe_analisis.pdf")

# ───────────────────────────────────────────────────────────────
# Guardar la fecha de corte para la próxima corrida
# ───────────────────────────────────────────────────────────────
with open(".ultima_fecha_analizada.json", "w") as f:
    json.dump({"ultima_fecha": end_date.isoformat()}, f)

print("Archivos en cwd tras generar el reporte:")
print(os.listdir("."))

# ── Guardar la última fecha analizada en la raíz del repo ──────────
from pathlib import Path
STATE_FILE = Path(__file__).resolve().parent / ".ultima_fecha_analizada.json"

with open(STATE_FILE, "w") as f:
    json.dump({"ultima_fecha": end_date.isoformat()}, f)

print("JSON de estado guardado en:", STATE_FILE)
