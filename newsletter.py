#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates 
from datetime import datetime, timedelta
import os, sys, csv
from scipy.interpolate import make_interp_spline
import numpy as np


def detect_delimiter(path, sample_size=2048):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        sample = f.read(sample_size)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[',',';','\t'])
        return dialect.delimiter
    except csv.Error:
        return ','

def load_and_detect(csv_path):
    sep = detect_delimiter(csv_path)
    print(f"🕵️‍♀️ Delimitador detectado: '{sep}'")
    df = pd.read_csv(csv_path, sep=sep, engine='python',
                     on_bad_lines='warn', encoding='utf-8')
    df.columns = df.columns.str.strip()
    cols = list(df.columns)

    # Columnas obligatorias
    date_col  = next((c for c in cols if 'fecha' in c.lower()), None)
    topic_col = next((c for c in cols if 'topico' in c.lower()), None)
    title_col = next((c for c in cols if 'títul' in c.lower() or 'titulo' in c.lower()), None)
    views_col = next((c for c in cols if 'vistas' in c.lower()), None)

    missing = [n for n,v in [('Fecha',date_col),('Tópico',topic_col),
                             ('Título',title_col),('Vistas',views_col)] if v is None]
    if missing:
        print(f"❌ Faltan columnas obligatorias: {missing}")
        print("Columnas encontradas:", cols)
        sys.exit(1)

    # Opcionales
    summary_col = next((c for c in cols if 'resumen' in c.lower()), None)
    url_col     = next((c for c in cols if 'url' in c.lower()), None)

    return df, date_col, topic_col, title_col, summary_col, url_col, views_col

def update_history(hist_path, total):
    today = datetime.now().date()

    if os.path.exists(hist_path):
        # 1) Leemos el CSV y parseamos la columna ‘fecha’ como datetime
        hist = pd.read_csv(hist_path, parse_dates=['fecha'])
        # 2) Convertimos a date para descartar la hora
        hist['fecha'] = hist['fecha'].dt.date
    else:
        hist = pd.DataFrame(columns=['fecha','total'])

    # 3) Buscamos la fila de hace 7 días (ahora ambos son date)
    prev = hist[hist['fecha'] == (today - timedelta(days=7))]

    # 4) Añadimos la fila de hoy
    new_row = {'fecha': today, 'total': total}
    hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)

    # 5) Guardamos sólo la parte de fecha (YYYY-MM-DD) para mantener el CSV limpio
    hist.to_csv(hist_path, index=False, date_format='%Y-%m-%d')

    return prev


def compute_trends(df_curr, df_prev, topic_col, views_col):
    curr = df_curr[topic_col].value_counts().rename('current')
    prev = df_prev[topic_col].value_counts().rename('previous')
    trend = pd.concat([prev, curr], axis=1).fillna(0)
    trend['delta']      = trend['current'] - trend['previous']
    trend['pct_change'] = trend['delta'] / trend['previous'].replace(0,1) * 100
    trend['engagement'] = df_curr.groupby(topic_col)[views_col].sum() / trend['current']
    return trend

def main(csv_path, out_dir):
    # 1) Carga y detección de columnas
    df, date_col, topic_col, title_col, summary_col, url_col, views_col = load_and_detect(csv_path)

    # 2) Filtrado últimos 7 días
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    df7 = df[df[date_col] >= cutoff].copy()
    total = len(df7)
    md = []

     # ——— DEBUG: verificar df7 y columnas ———
    print(f"DEBUG: Filas en df7 = {total}")
    print(f"DEBUG: Columnas disponibles = {df.columns.tolist()}")
    if total > 0:
        sample = df7[[date_col, views_col]].head()
        print("DEBUG: Primeras filas de df7 con Fecha y Vistas:\n", sample.to_string(index=False))
    else:
        print("DEBUG: df7 está vacío; no hay datos en los últimos 7 días.")
    # ————————————————————————————————————————

    # ——— Nuevas líneas para tendencias automáticas ———
    # Defino fecha de hoy y de hace 7 días
    today = datetime.now().date()
    prev_date = today - timedelta(days=7)

    # Intento leer el CSV de la semana anterior
    prev_file = os.path.join(out_dir, f"{prev_date}-articulos.csv")
    if os.path.exists(prev_file):
        df_prev_week = pd.read_csv(prev_file, parse_dates=[date_col])
    else:
        df_prev_week = pd.DataFrame(columns=df.columns)
    # ————————————————————————————————————————————


    # 3) Historial y tendencias
    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    
    # Historial de totales (sigue igual)
    prev_totals = update_history(hist_path, total)

    # Tendencias por tópico usando df_prev_week
    trend = compute_trends(df7, df_prev_week, topic_col, views_col) \
            if not df_prev_week.empty else None

    # 4) Gráfico de distribución
    chart_path = os.path.join(out_dir, 'bar_topics.png')
    df7[topic_col].value_counts().plot.bar()
    plt.title('Artículos por tópico (últimos 7 días)')
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    # 4.b) Gráfico de vistas fluctuantes suavizado
    df7['solo_fecha'] = pd.to_datetime(df7[date_col].dt.date)   # ≠ antes: aseguramos datetime
    daily = (
        df7.groupby('solo_fecha')[views_col]
           .sum()
           .reset_index(name='vistas')
    )

    if not daily.empty:
        # Suavizado: promedio móvil de 3 días
        daily['suavizado'] = (
            daily['vistas']
            .rolling(window=3, center=True, min_periods=1)
            .mean()
        )

        views_chart = os.path.join(out_dir, 'line_views.png')
        plt.figure()

        # ───────── NUEVO: formateo limpio de fechas ─────────
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))  # 23 Jun
        # ----------------------------------------------------

        plt.plot(daily['solo_fecha'], daily['suavizado'], linestyle='-')
        plt.scatter(daily['solo_fecha'], daily['vistas'],
                    color='black', zorder=5)

        plt.title('Vistas fluctuantes por día (últimos 7 días)')
        plt.xlabel('Fecha')
        plt.ylabel('Vistas')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(views_chart)
        plt.close()

    # 4.c) Heat-map día de la semana × tópico
    heatmap_path = os.path.join(out_dir, 'heatmap_topics.png')

    # Mapa inglés → español
    dia_map = {
        "Monday":    "Lunes",
        "Tuesday":   "Martes",
        "Wednesday": "Miércoles",
        "Thursday":  "Jueves",
        "Friday":    "Viernes",
        "Saturday":  "Sábado",
        "Sunday":    "Domingo"
    }

    # Nueva columna con el nombre del día en castellano
    df7["dia_semana_es"] = df7[date_col].dt.day_name().map(dia_map)

    # Tabla dinámica: vistas por día × tópico
    pivot = (
        df7.pivot_table(
            index="dia_semana_es",
            columns=topic_col,
            values=views_col,
            aggfunc='sum',
            fill_value=0
        )
        .reindex(["Lunes","Martes","Miércoles","Jueves",
                  "Viernes","Sábado","Domingo"])
    )

    import seaborn as sns                      # asegúrate de seaborn instalado
    plt.figure(figsize=(14, 5))
    sns.heatmap(pivot, fmt='d', annot=True, cmap="coolwarm",
                cbar_kws=dict(label="Vistas"))
    plt.title("Heatmap: vistas por día de la semana y tópico")
    plt.xlabel("Tópico")
    plt.ylabel("Día de la semana")
    plt.tight_layout()
    plt.savefig(heatmap_path)
    plt.close()
    
    # 4.d) Barras agrupadas Notas / Vistas   ← NUEVO BLOQUE
    group_path = os.path.join(out_dir, 'bars_notes_views.png')
    totales = (
        df7.groupby(topic_col)
           .agg(Notas=('ID', 'count'),
                Vistas=(views_col, 'sum'))
           .sort_values('Vistas', ascending=False)
           .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    idx = range(len(totales))
    ax.bar(idx, totales["Notas"], width=0.4, label="Notas", color="#1f77b4")
    ax.bar([i + 0.4 for i in idx], totales["Vistas"], width=0.4,
           label="Vistas", color="#ff7f0e")
    ax.set_xticks([i + 0.2 for i in idx])
    ax.set_xticklabels(totales[topic_col], rotation=45, ha="right")
    ax.set_title("Notas publicadas y vistas por tópico (últimos 7 días)")
    ax.set_ylabel("Cantidad")
    ax.legend()
    fig.tight_layout()
    plt.savefig(group_path)
    plt.close()



    # 5) Construcción de narrativa automática
    
    md.append(f"# Newsletter semanal ({datetime.now().date()})\n")
    # Datos básicos
    start = (datetime.now() - timedelta(days=7)).strftime('%d %b')
    end   = datetime.now().strftime('%d %b')
    md.append(f"**Total de artículos ({start} – {end}):** {total}  \n")
    md.append(f"**Tópicos cubiertos:** {df7[topic_col].nunique()}\n")
    md.append("---\n")

    # Hallazgos clave
    if trend is not None:
        prev_total = int(df_prev['total'].iloc[0])
        pct = (total - prev_total) / prev_total * 100
        sign = "+" if pct >= 0 else ""
        md.append("## 🏅 Hallazgos clave\n")
        md.append(f"- **Variación semanal:** {sign}{pct:.1f}% (de {prev_total} a {total} artículos).")
        
        # Top incremento y disminución
        gain = trend.sort_values('pct_change', ascending=False).iloc[0]
        loss = trend.sort_values('pct_change').iloc[0]
        md.append(f"- **Mayor incremento:** {gain.name} (+{gain['pct_change']:.0f}% notas).")
        md.append(f"- **Mayor disminución:** {loss.name} ({loss['pct_change']:.0f}% notas).")
        md.append("\n")
        
        # 📈 Variación por tópico
        md.append("### 📈 Variación por tópico\n")
        md.append("| Tópico | Anterior | Actual | Δ notas | % cambio |")
        md.append("|---|---:|---:|---:|---:|")
        for tema, row in trend.iterrows():
            ant   = int(row['previous'])
            act   = int(row['current'])
            delta = int(row['delta'])
            pct_t = row['pct_change']
            md.append(f"| {tema} | {ant} | {act} | {delta:+d} | {pct_t:+.1f}% |")
        md.append("")   # separador final


            # 📈 Vistas fluctuantes por día
    md.append("## 📈 Vistas fluctuantes por día\n")
    md.append(f"![Vistas fluctuantes por día]({os.path.basename(views_chart)})\n")
    md.append("\n---\n")

    # Distribución y KPI
    #md.append("## 📊 Distribución por tópico\n")
    #md.append(f"![Artículos por tópico]({os.path.basename(chart_path)})\n")
    #md.append("\n---\n")

    # ─── NUEVO barras Notas vs Vistas
    md.append("## 📑 Notas publicadas vs vistas por tópico\n")
    md.append(f"![Notas vs vistas]({os.path.basename(group_path)})\n")
    md.append("\n---\n")

    # ─── NUEVO bloque heat-map 
    md.append("## 🗓️ Vistas por día y tópico\n")
    md.append(f"![Heatmap vistas día y tópico]({os.path.basename(heatmap_path)})\n")
    md.append("\n---\n")

    

    # Tabla de tópicos
    md.append("## 🔝 Tópicos más frecuentes\n")
    md.append("| Tópico | Notas | % Total | Vistas | Vistas/Nota |")
    md.append("|---|---:|---:|---:|---:|")
    total_views = df7[views_col].sum()
    for tema, cnt in df7[topic_col].value_counts().head(8).items():
        views = df7[df7[topic_col] == tema][views_col].sum()
        md.append(f"| {tema} | {cnt} | {cnt/total*100:.0f}% | {views} | {views/cnt:.1f} |")
    md.append("\n---\n")

        # Artículos destacados por vistas
    md.append("## ✨ Artículos destacados\n")
    for _, r in df7.sort_values(views_col, ascending=False).head(4).iterrows():
        fecha = r[date_col].strftime('%d %b %Y')
        vistas = int(r[views_col])
        md.append(f"### {r[title_col]}\n*{fecha} — {vistas} vistas*\n")
        if summary_col: md.append(r[summary_col] + "\n")
        if url_col:     md.append(f"[Leer más]({r[url_col]})\n")
    md.append("\n---\n")

           # Recomendaciones dinámicas basadas solo en esta semana
    md.append("## 🔮 Recomendaciones\n")
    recomendaciones = []

    resumen = (
        df7.groupby(topic_col)
           .agg(notas=('ID', 'count'), vistas_totales=(views_col, 'sum'))
           .assign(engagement=lambda x: x['vistas_totales'] / x['notas'])
    )

    # REFUERZO
    refuerzo = resumen[resumen['notas'] <= 3].sort_values('engagement', ascending=False).head(1)
    for tema, row in refuerzo.iterrows():
        recomendaciones.append(f"- Refuerzo en **{tema}**: alto interés con pocas notas (engagement: {row['engagement']:.1f}).")

    # OPTIMIZAR
    optimizar = resumen[resumen['notas'] >= 3].sort_values('engagement').head(1)
    for tema, row in optimizar.iterrows():
        recomendaciones.append(f"- Optimizar **{tema}**: bajo interés relativo pese a varias notas (engagement: {row['engagement']:.1f}).")

    # BUEN RENDIMIENTO
    buen_rend = resumen[(resumen['notas'] >= 3) & (resumen['engagement'] >= 2.5)]
    if not buen_rend.empty:
        top = buen_rend.sort_values('engagement', ascending=False).head(1)
        for tema, row in top.iterrows():
            recomendaciones.append(f"- Buen rendimiento en **{tema}**: mantener estrategia (engagement: {row['engagement']:.1f}).")

    if recomendaciones:
        md.extend(recomendaciones)
    else:
        md.append("- Esta semana no se detectaron patrones claros.\n")


    # Autores de la semana (solo nombres, orden informativo no numérico)
    md.append("\n## ✍️ Autores de la semana\n")
    autor_col = next((c for c in df7.columns if 'autor' in c.lower()), None)
    if autor_col:
        autores = (
            df7.groupby(autor_col)
               .agg(articulos=('ID', 'count'), vistas_totales=(views_col, 'sum'))
               .assign(orden=lambda x: x['articulos'] * 1.5 + x['vistas_totales'] / 10)
               .sort_values('orden', ascending=False)
               .head(5)
        )
        for autor in autores.index:
            md.append(f"- {autor}")
    else:
        md.append("- No se detectó una columna de autor.\n")



    # 6) Escritura final del Markdown
    out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))

    # ——— Guardar el detalle de esta semana para la próxima corrida ———
    semana_path = os.path.join(out_dir, f"{today}-articulos.csv")
    df7.to_csv(semana_path, index=False, date_format='%Y-%m-%d')

    # Purga archivos de más de 7 días atrás
    for fname in os.listdir(out_dir):
        if fname.endswith('-articulos.csv'):
            fecha_str = fname.split('-articulos.csv')[0]
            try:
                fecha = datetime.fromisoformat(fecha_str).date()
                if fecha < prev_date:
                    os.remove(os.path.join(out_dir, fname))
            except ValueError:
                pass

    print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python newsletter.py <csv_path> <out_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
