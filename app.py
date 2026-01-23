import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Gestión de Taller Autociel", layout="wide")

# --- CONFIGURACIÓN DE GIDs REALES ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/export?format=csv&gid="

GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

@st.cache_data(ttl=60)
def cargar_datos_taller():
    lista_dfs = []
    for nombre, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            df_p = pd.read_csv(url)
            df_p.columns = df_p.columns.str.strip()
            if 'PATENTE' in df_p.columns:
                df_p = df_p.dropna(subset=['PATENTE'])
                df_p['GRUPO_ORIGEN'] = nombre
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error en {nombre}: {e}")
    return pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()

st.title("🚀 Programación de Taller - Autociel")

try:
    df = cargar_datos_taller()
    
    if not df.empty:
        # 1. Limpieza de Datos
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)
        
        # Limpieza de Fechas (Formato DD/MM/YYYY)
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1)

        # 2. MÉTRICAS FINANCIERAS
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {df[df['FAC'] == 'FAC']['PRECIO'].sum():,.0f}")
        c2.metric("Este Mes (SI)", f"$ {df[df['FAC'] == 'SI']['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {df[df['FAC'] == 'NO']['PRECIO'].sum():,.0f}")

        st.divider()

        # 3. FILTROS PARA EL GANTT
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            grupos_sel = st.multiselect("Filtrar Grupos:", options=list(GIDS.keys()), default=list(GIDS.keys()))
        with col_f2:
            ver_todo = st.checkbox("Ver también unidades facturadas", value=False)

        # Filtrado de datos para el gráfico
        df_gantt = df[df['GRUPO_ORIGEN'].isin(grupos_sel)].copy()
        if not ver_todo:
            df_gantt = df_gantt[df_gantt['FAC'].isin(['SI', 'NO'])]
        
        # Quitar filas sin fecha promesa para el Gantt
        df_gantt = df_gantt.dropna(subset=['FECH/PROM'])

        # --- LÓGICA DEL GANTT ---
        # Calculamos la fecha de inicio: Fecha Promesa - Días (Paños)
        df_gantt['Fecha_Inicio'] = df_gantt.apply(lambda x: x['FECH/PROM'] - timedelta(days=int(x['PAÑOS'])), axis=1)
        
        # Etiqueta para el gráfico
        df_gantt['Detalle'] = df_gantt['PATENTE'] + " - " + df_gantt['VEHICULO']

        if not df_gantt.empty:
            st.subheader("📅 Cronograma de Trabajos (Gantt)")
            
            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECH/PROM", 
                y="GRUPO_ORIGEN", 
                color="GRUPO_ORIGEN",
                hover_name="Detalle",
                text="PATENTE",
                labels={"GRUPO_ORIGEN": "Grupo de Trabajo"},
                title="Programación por Grupo (Estimada por Paños)"
            )
            
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=400, showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 4. TABLA DETALLADA BAJO EL GANTT
            st.subheader("📋 Detalle de Unidades Programadas")
            st.dataframe(
                df_gantt[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']],
                use_container_width=True
            )
        else:
            st.info("No hay unidades con Fecha Promesa cargada para mostrar en el Gantt.")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
