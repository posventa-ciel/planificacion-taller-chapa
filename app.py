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
        # Convertimos FECH/PROM a fecha de forma segura
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # Si no hay fecha, usamos HOY como referencia
        hoy_dt = pd.Timestamp(datetime.now().date())
        df['FECHA_FIN_REF'] = df['FECH/PROM'].fillna(hoy_dt)

        # Limpieza de Paños: aseguramos que sea numérico y mínimo 1
        df['PAÑOS_NUM'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1)
        df.loc[df['PAÑOS_NUM'] < 1, 'PAÑOS_NUM'] = 1
        
        # Limpieza de precios para indicadores
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
            # --- SOLUCIÓN AL ERROR DE OPERANDOS ---
            # Usamos pd.to_timedelta para restar los días correctamente
            df_gantt['Fecha_Inicio'] = df_gantt['FECHA_FIN_REF'] - pd.to_timedelta(df_gantt['PAÑOS_NUM'], unit='D')
            
            # Etiqueta visual para el eje Y
            df_gantt['VEHICULO_ID'] = df_gantt['PATENTE'].astype(str) + " - " + df_gantt['VEHICULO'].astype(str)

            # Creamos el Gantt
            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECHA_FIN_REF", 
                y="VEHICULO_ID", 
                color="GRUPO_ORIGEN",
                hover_name="VEHICULO_ID",
                text="PAÑOS",
                title="Distribución por Unidad (1 día por paño)"
            )
            
            fig.update_yaxes(autorange="reversed", title="Vehículos en Taller")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea de HOY para ver retrasos
            fig.add_vline(x=hoy_dt, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Ajustar altura según cantidad de autos
            altura_dinamica = max(400, len(df_gantt) * 30)
            fig.update_layout(height=altura_dinamica, margin=dict(t=50, b=50, l=0, r=50))
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("ℹ️ El largo de la barra indica la cantidad de paños. Las unidades sin fecha promesa se muestran venciendo HOY.")
        else:
            st.info("No hay unidades pendientes (SI/NO) para mostrar en el gráfico.")

        # 3. TABLA DE DATOS
        with st.expander("Ver tabla de datos completa"):
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Se produjo un error: {e}")
