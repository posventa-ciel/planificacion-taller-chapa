import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Tablero de Control - TPS")

if st.button("🔄 Refrescar Datos"):
    st.cache_data.clear()

# --- DATOS ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/export?format=csv&gid="
GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

@st.cache_data(ttl=60)
def cargar_datos():
    dfs = []
    for n, gid in GIDS.items():
        try:
            # Leemos TODO como texto (str) para que no falle la carga
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip()
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# --- FUNCIÓN DE LIMPIEZA MANUAL (LA CLAVE PARA QUE NO FALLE) ---
def limpiar_y_calcular(df_in):
    # Creamos listas vacías para guardar los resultados limpios
    fechas_inicio = []
    fechas_fin = []
    textos_visuales = []
    
    hoy = datetime.now()

    # Recorremos fila por fila (Iteración manual)
    for index, row in df_in.iterrows():
        
        # 1. PROCESAR FECHA (PROMESA)
        try:
            # Intentamos convertir el texto a fecha
            f_fin = pd.to_datetime(row['FECH/PROM'], dayfirst=True)
            if pd.isna(f_fin):
                f_fin = hoy
        except:
            f_fin = hoy # Si falla, usamos HOY
            
        # 2. PROCESAR PAÑOS (DÍAS)
        try:
            # Buscamos números en el texto usando expresiones regulares
            texto_panos = str(row.get('PAÑOS', '1'))
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            if numeros:
                dias = float(numeros[0])
            else:
                dias = 1.0
            
            # Evitamos números negativos o cero
            if dias < 0.5: dias = 1.0
        except:
            dias = 1.0

        # 3. CÁLCULO MATEMÁTICO (Convertimos todo a formato estándar de Python)
        try:
            # Convertimos Timestamp de Pandas a datetime de Python puro para restar sin error
            f_fin_py = f_fin.to_pydatetime()
            f_inicio = f_fin_py - timedelta(days=dias)
        except:
            f_inicio = f_fin
        
        fechas_inicio.append(f_inicio)
        fechas_fin.append(f_fin)
        textos_visuales.append(f"{dias:.1f}")

    # Devolvemos las columnas listas
    return fechas_inicio, fechas_fin, textos_visuales

# --- APP PRINCIPAL ---
try:
    df_raw = cargar_datos()
    
    if not df_raw.empty:
        df = df_raw.copy()

        # 1. Limpieza de Precios (Visualización)
        try:
            df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
            df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)
        except:
            df['PRECIO'] = 0

        # 2. MÉTRICAS
        st.subheader("💰 Finanzas Taller")
        c1, c2, c3 = st.columns(3)
        # Filtramos con cuidado
        si = df[df['FAC'] == 'SI']['PRECIO'].sum()
        no = df[df['FAC'] == 'NO']['PRECIO'].sum()
        fac = df[df['FAC'] == 'FAC']['PRECIO'].sum()
        
        c1.metric("Ya Facturado", f"$ {fac:,.0f}")
        c2.metric("A Facturar (SI)", f"$ {si:,.0f}")
        c3.metric("Proyectado (NO)", f"$ {no:,.0f}")

        st.divider()

        # 3. GANTT
        st.subheader("📅 Planificación Visual (Gantt)")
        
        # Filtramos datos
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()
        
        if not df_gantt.empty:
            # APLICAMOS LA FUNCIÓN MANUAL AQUÍ
            inicios, fines, dias_txt = limpiar_y_calcular(df_gantt)
            
            df_gantt['Inicio_Calc'] = inicios
            df_gantt['Fin_Calc'] = fines
            df_gantt['Dias_Txt'] = dias_txt
            
            # ID para el gráfico
            df_gantt['ID'] = df_gantt['PATENTE'].astype(str) + " " + df_gantt['VEHICULO'].astype(str).str[:15]

            # Gráfico
            fig = px.timeline(
                df_gantt,
                x_start="Inicio_Calc",
                x_end="Fin_Calc",
                y="ID",
                color="GRUPO_ORIGEN",
                text="Dias_Txt",
                title="Programación de Trabajos"
            )
            fig.update_yaxes(autorange="reversed", title="")
            fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura dinámica
            h = max(400, len(df_gantt) * 40)
            fig.update_layout(height=h)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay autos pendientes para mostrar.")

        with st.expander("Ver Datos"):
            st.dataframe(df)

except Exception as e:
    st.error(f"Error grave: {e}")
