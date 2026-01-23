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
        
        # --- LIMPIEZA CRÍTICA DE FECHAS ---
        # Convertimos a fecha, si falla ponemos NaT (Not a Time)
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # Si la fecha está vacía, para el gráfico le asignamos "Hoy" para que aparezca algo
        df['FECHA_GRAFICO'] = df['FECH/PROM'].fillna(pd.Timestamp(datetime.now()))

        # Limpieza de Paños (si es 0 o texto, ponemos 1 para que la barra tenga ancho)
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1)
        df.loc[df['PAÑOS'] <= 0, 'PAÑOS'] = 1
        df['PAÑOS'] = df['PAÑOS'].astype(int)

        # Limpieza de precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # 1. MÉTRICAS SUPERIORES
        st.subheader("💰 Resumen de Facturación")
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
            # Lógica: Fecha Inicio = Fecha Gráfico - Cantidad de Paños
            df_gantt['Fecha_Inicio'] = df_gantt.apply(lambda x: x['FECHA_GRAFICO'] - pd.Timedelta(days=x['PAÑOS']), axis=1)
            
            # Etiqueta visual
            df_gantt['Detalle'] = df_gantt['PATENTE'].astype(str) + " (" + df_gantt['VEHICULO'].astype(str) + ")"

            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECHA_GRAFICO", 
                y="GRUPO_ORIGEN", 
                color="GRUPO_ORIGEN",
                hover_name="Detalle",
                text="PATENTE",
                title="Distribución de Trabajo por Grupo (1 día por paño)"
            )
            
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea vertical indicando HOY
            hoy = datetime.now()
            fig.add_vline(x=hoy, line_dash="dash", line_color="red", annotation_text="HOY")
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("⚠️ Nota: Las unidades sin 'Fecha Promesa' en el Sheet se muestran terminando HOY por defecto.")
        else:
            st.info("No hay unidades con estado 'SI' o 'NO' para mostrar.")

        # 3. TABLA DE DATOS
        with st.expander("Ver listado completo de datos"):
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Error crítico: {e}")
