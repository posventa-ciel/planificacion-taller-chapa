import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Gestión de Taller - Autociel", layout="wide")

url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit#gid=609774337"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def cargar_datos():
    # Pestañas a consolidar
    pestanas = ["GRUPO UNO", "GRUPO DOS", "GRUPO 3", "TERCEROS"]
    lista_dfs = []
    for p in pestanas:
        try:
            df_p = conn.read(spreadsheet=url, worksheet=p)
            df_p.columns = df_p.columns.str.strip()
            df_p['GRUPO_ORIGEN'] = p
            lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error en pestaña {p}: {e}")
    return pd.concat(lista_dfs, ignore_index=True)

try:
    df_raw = cargar_datos()
    # Limpieza: quitamos filas sin patente y convertimos PRECIO a número
    df = df_raw.dropna(subset=['PATENTE']).copy()
    df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)
    
    # --- LÓGICA DE ESTADOS (Columna FAC) ---
    # FAC: Ya facturado
    # SI: Facturable este mes
    # NO: Facturable mes próximo
    
    facturado = df[df['FAC'] == 'FAC']
    proyectado_mes = df[df['FAC'] == 'SI']
    proyectado_prox_mes = df[df['FAC'] == 'NO']

    st.title("📊 Control de Producción y Facturación")

    # --- MÉTRICAS FINANCIERAS ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Ya Facturado (FAC)", f"$ {facturado['PRECIO'].sum():,.0f}")
        st.caption(f"Unidades: {len(facturado)}")
        
    with c2:
        st.subheader("Mes en Curso (SI)")
        st.metric("A Facturar", f"$ {proyectado_mes['PRECIO'].sum():,.0f}", delta="Pendiente")
        st.caption(f"Unidades: {len(proyectado_mes)}")

    with c3:
        st.subheader("Próximo Mes (NO)")
        st.metric("Proyectado", f"$ {proyectado_prox_mes['PRECIO'].sum():,.0f}")
        st.caption(f"Unidades: {len(proyectado_prox_mes)}")

    st.divider()

    # --- VISTA PARA EL GANTT (LO QUE NO ESTÁ FACTURADO AÚN) ---
    st.subheader("📅 Programación de Trabajos Pendientes (SI / NO)")
    
    # Filtramos lo que requiere programación (lo que no se facturó todavía)
    df_pendientes = df[df['FAC'].isin(['SI', 'NO'])].copy()
    
    # Ordenamos por fecha de promesa para ver qué urge más
    if 'FECH/PROM' in df_pendientes.columns:
        df_pendientes = df_pendientes.sort_values(by='FECH/PROM')

    # Filtro por Grupo para el Jefe de Taller
    grupo_sel = st.multiselect("Filtrar por Grupo/Taller:", options=df_pendientes['GRUPO_ORIGEN'].unique(), default=df_pendientes['GRUPO_ORIGEN'].unique())
    df_filtrado = df_pendientes[df_pendientes['GRUPO_ORIGEN'].isin(grupo_sel)]

    st.dataframe(
        df_filtrado[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR', 'OBSERVACIONES']],
        use_container_width=True
    )

except Exception as e:
    st.error(f"Hubo un problema al procesar los datos: {e}")
