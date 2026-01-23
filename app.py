import streamlit as st
import pandas as pd
import plotly.express as px

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
            # Limpieza: Solo filas con patente
            if 'PATENTE' in df_p.columns:
                df_p = df_p.dropna(subset=['PATENTE'])
                df_p['GRUPO_ORIGEN'] = nombre
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error en {nombre}: {e}")
    
    if not lista_dfs:
        return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

# --- LÓGICA DE LA APP ---
st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        
        # Limpieza de precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # Limpieza de Fechas y Paños
        df['FECH/PROM'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce').fillna(1).astype(int)

        # 1. MÉTRICAS SUPERIORES
        st.subheader("💰 Resumen de Facturación")
        c1, c2, c3 = st.columns(3)
        
        fac_si = df[df['FAC'] == 'SI']
        fac_no = df[df['FAC'] == 'NO']
        ya_fac = df[df['FAC'] == 'FAC']

        c1.metric("Ya Facturado (FAC)", f"$ {ya_fac['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {fac_si['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {fac_no['PRECIO'].sum():,.0f}")

        st.divider()

        # 2. FILTROS Y GANTT
        tab_gantt, tab_datos = st.tabs(["📅 Cronograma Gantt", "📋 Datos Detallados"])

        with tab_gantt:
            st.subheader("Programación Estimada (1 día por paño)")
            
            # Filtro de grupos para el Gantt
            grupos_sel = st.multiselect("Filtrar Grupos en Pantalla:", options=list(GIDS.keys()), default=list(GIDS.keys()))
            
            # Preparamos datos para el Gantt
            df_gantt = df[df['GRUPO_ORIGEN'].isin(grupos_sel)].copy()
            # Solo lo pendiente (SI / NO) y con fecha promesa
            df_gantt = df_gantt[df_gantt['FAC'].isin(['SI', 'NO'])]
            df_gantt = df_gantt.dropna(subset=['FECH/PROM'])

            if not df_gantt.empty:
                # Lógica del Gantt: Fecha Inicio = Promesa - Paños
                df_gantt['Fecha_Inicio'] = df_gantt.apply(lambda x: x['FECH/PROM'] - pd.Timedelta(days=x['PAÑOS']), axis=1)
                df_gantt['Detalle'] = df_gantt['PATENTE'].astype(str) + " (" + df_gantt['VEHICULO'].astype(str) + ")"

                fig = px.timeline(
                    df_gantt, 
                    x_start="Fecha_Inicio", 
                    x_end="FECH/PROM", 
                    y="GRUPO_ORIGEN", 
                    color="GRUPO_ORIGEN",
                    hover_name="Detalle",
                    text="PATENTE",
                    title="Ocupación de Grupos"
                )
                
                fig.update_yaxes(autorange="reversed")
                fig.update_traces(textposition='inside', insidetextanchor='middle')
                fig.update_layout(height=500, xaxis_title="Calendario de Trabajo", yaxis_title="Grupos")
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay unidades pendientes con 'Fecha Promesa' para mostrar en el cronograma.")

        with tab_datos:
            st.subheader("Listado de Unidades")
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Error crítico: {e}")
