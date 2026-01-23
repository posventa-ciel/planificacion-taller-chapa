import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Taller Autociel", layout="wide")
st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

# 2. Botón para limpiar caché (Útil si los datos se quedan pegados)
if st.button("🔄 Recargar Datos y Limpiar Memoria"):
    st.cache_data.clear()

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
            # Leemos todo como texto (dtype=str) para evitar interpretaciones erróneas
            df_p = pd.read_csv(url, dtype=str)
            df_p.columns = df_p.columns.str.strip()
            
            if 'PATENTE' in df_p.columns:
                df_p = df_p.dropna(subset=['PATENTE'])
                df_p['GRUPO_ORIGEN'] = nombre
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error leyendo pestaña {nombre}: {e}")
    
    if not lista_dfs: return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        hoy = datetime.now()

        # --- LIMPIEZA DE DATOS MANUAL ---
        
        # 1. Limpieza de Precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # 2. Limpieza de Fechas (Promesa)
        # Convertimos a objeto datetime de Python puro
        df['FECH/PROM_DT'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # 3. Limpieza de Paños
        df['PAÑOS_FLOAT'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1)
        df.loc[df['PAÑOS_FLOAT'] < 1, 'PAÑOS_FLOAT'] = 1

        # --- CÁLCULO DE FECHAS "A PRUEBA DE BALAS" ---
        # Usamos listas de Python en lugar de Pandas Series para evitar el error de "Integer Array"
        
        fechas_fin = []
        fechas_inicio = []
        
        for fecha_promesa, paños in zip(df['FECH/PROM_DT'], df['PAÑOS_FLOAT']):
            # A. Determinar Fecha Fin (Si es NaT, usamos HOY)
            if pd.isna(fecha_promesa):
                fin = hoy
            else:
                fin = fecha_promesa
            
            # B. Calcular Inicio (Restar timedelta)
            # Aquí usamos timedelta de Python puro, que nunca falla con floats
            inicio = fin - timedelta(days=float(paños))
            
            fechas_fin.append(fin)
            fechas_inicio.append(inicio)

        # Asignamos las listas calculadas de vuelta al DataFrame
        df['Fecha_Fin_Real'] = fechas_fin
        df['Fecha_Inicio_Real'] = fechas_inicio

        # --- VISUALIZACIÓN ---

        # 1. Métricas
        st.subheader("💰 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {df[df['FAC'] == 'FAC']['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {df[df['FAC'] == 'SI']['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {df[df['FAC'] == 'NO']['PRECIO'].sum():,.0f}")

        st.divider()

        # 2. Gantt
        st.subheader("📅 Tablero de Control de Producción")
        
        # Filtramos solo lo pendiente
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()
        
        # Filtro por Grupo
        grupos = df_gantt['GRUPO_ORIGEN'].unique().tolist()
        sel_grupos = st.multiselect("Filtrar Grupos:", groups, default=grupos)
        df_gantt = df_gantt[df_gantt['GRUPO_ORIGEN'].isin(sel_grupos)]

        if not df_gantt.empty:
            # ID para el gráfico
            df_gantt['ID_AUTO'] = df_gantt['PATENTE'].astype(str) + " " + df_gantt['VEHICULO'].astype(str).str[:15]

            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio_Real", 
                x_end="Fecha_Fin_Real", 
                y="ID_AUTO", 
                color="GRUPO_ORIGEN",
                hover_name="ID_AUTO",
                text="PAÑOS_FLOAT", # Muestra los días dentro de la barra
                title="Cronograma Estimado (Días calculados por Paños)"
            )
            
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea de Hoy
            fig.add_vline(x=hoy, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Ajuste de altura
            altura = max(400, len(df_gantt) * 35)
            fig.update_layout(height=altura)
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("ℹ️ El ancho de la barra representa los días estimados (1 paño = 1 día).")
        else:
            st.info("No hay unidades pendientes para mostrar.")

        with st.expander("Ver Datos de Origen"):
            st.dataframe(df)

except Exception as e:
    st.error(f"Error inesperado: {e}")
