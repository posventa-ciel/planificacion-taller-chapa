import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
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
    
    if not lista_dfs: return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        
        # --- LIMPIEZA DE DATOS ---
        # Convertimos FECH/PROM a datetime de forma segura
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # Si no hay fecha, usamos HOY como referencia para que el gráfico no falle
        hoy_dt = pd.Timestamp(datetime.now().date())
        df['FECHA_FIN_GRAFICO'] = df['FECH/PROM'].fillna(hoy_dt)

        # Limpieza de Paños: asegurar que sea numérico y mínimo 1
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1)
        df.loc[df['PAÑOS'] < 1, 'PAÑOS'] = 1
        
        # Limpieza de precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # 1. MÉTRICAS SUPERIORES
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {df[df['FAC'] == 'FAC']['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {df[df['FAC'] == 'SI']['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {df[df['FAC'] == 'NO']['PRECIO'].sum():,.0f}")

        st.divider()

        # 2. GANTT
        st.subheader("📅 Cronograma de Carga de Trabajo")
        
        # Filtramos solo lo pendiente (SI / NO)
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()

        if not df_gantt.empty:
            # --- CORRECCIÓN DEL ERROR DE OPERANDOS ---
            # Calculamos Fecha_Inicio restando los días (paños) a la fecha de fin
            df_gantt['Fecha_Inicio'] = df_gantt['FECHA_FIN_GRAFICO'] - pd.to_timedelta(df_gantt['PAÑOS'], unit='D')
            
            # Etiqueta visual: Dominio y Vehículo
            df_gantt['ID_AUTO'] = df_gantt['PATENTE'].astype(str) + " - " + df_gantt['VEHICULO'].astype(str)

            # Graficamos: Eje Y es el ID del auto para ver cada uno por separado
            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECHA_FIN_GRAFICO", 
                y="ID_AUTO", 
                color="GRUPO_ORIGEN", # Los colores siguen siendo por Grupo
                hover_name="ID_AUTO",
                text="PAÑOS", # Mostramos la cantidad de paños en la barra
                title="Distribución de Unidades Pendientes (SI/NO)"
            )
            
            fig.update_yaxes(autorange="reversed", title="Vehículos en Taller")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea vertical de HOY
            fig.add_vline(x=hoy_dt, line_dash="dash", line_color="red", annotation_text="HOY")
            
            fig.update_layout(height=600) # Más alto para ver mejor la lista de autos
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("ℹ️ El ancho de la barra representa la cantidad de paños (1 día por paño).")
        else:
            st.info("No hay unidades pendientes con estado 'SI' o 'NO' para mostrar.")

        # 3. TABLA DE DATOS
        with st.expander("Ver listado completo de datos"):
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Error crítico: {e}")
