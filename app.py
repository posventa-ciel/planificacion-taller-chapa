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
            st.error(f"Error cargando pestaña {nombre}: {e}")
    
    if not lista_dfs: return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        
        # --- LIMPIEZA DE DATOS (A PRUEBA DE FALLOS) ---
        
        # 1. Fechas: Forzamos conversión. Si falla, queda NaT (Not a Time)
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # 2. Referencia de Fin: Si no tiene fecha promesa, usamos HOY
        hoy_dt = pd.Timestamp(datetime.now().date())
        df['FECHA_FIN_REF'] = df['FECH/PROM'].fillna(hoy_dt)

        # 3. Paños: Limpiamos cualquier texto. Si es texto ("2 aprox"), se convierte en NaN y luego en 1.
        df['PAÑOS_LIMPIO'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
        df['PAÑOS_LIMPIO'] = df['PAÑOS_LIMPIO'].fillna(1) # Rellenamos vacíos con 1 día
        df.loc[df['PAÑOS_LIMPIO'] < 1, 'PAÑOS_LIMPIO'] = 1 # Mínimo 1 día

        # 4. Precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # --- MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {df[df['FAC'] == 'FAC']['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {df[df['FAC'] == 'SI']['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {df[df['FAC'] == 'NO']['PRECIO'].sum():,.0f}")

        st.divider()

        # --- GANTT ---
        st.subheader("📅 Cronograma de Carga de Trabajo")
        
        # Filtramos SI / NO
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()

        if not df_gantt.empty:
            
            # --- CÁLCULO DE FECHAS SEGURO ---
            # Convertimos los números de paños a "Intervalos de Tiempo" (Timedelta)
            duracion_dias = pd.to_timedelta(df_gantt['PAÑOS_LIMPIO'], unit='D')
            
            # Restamos: Fecha - Intervalo = Fecha Inicio
            df_gantt['Fecha_Inicio'] = df_gantt['FECHA_FIN_REF'] - duracion_dias
            
            # Creamos ID único para el gráfico
            df_gantt['ID_VISUAL'] = df_gantt['PATENTE'].astype(str) + " (" + df_gantt['VEHICULO'].astype(str) + ")"

            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECHA_FIN_REF", 
                y="ID_VISUAL", 
                color="GRUPO_ORIGEN",
                hover_name="ID_VISUAL",
                text="PAÑOS_LIMPIO",
                title="Distribución de Trabajo (Calculado hacia atrás desde Fecha Promesa)"
            )
            
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea de HOY
            fig.add_vline(x=hoy_dt, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura dinámica
            altura = max(400, len(df_gantt) * 35)
            fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=10))
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ Los números dentro de las barras indican la cantidad de paños/días estimados.")
        else:
            st.warning("No hay datos pendientes (SI/NO) para mostrar en el gráfico.")

        # TABLA
        with st.expander("Ver Datos Completos"):
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
