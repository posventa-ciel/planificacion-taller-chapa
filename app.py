import streamlit as st
import pandas as pd

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
    
    return pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()

# --- LÓGICA DE LA APP ---
st.title("🚀 Sistema de Gestión - Taller de Chapa y Pintura")

try:
    df = cargar_datos_taller()
    
    if not df.empty:
        # Limpieza de precios (Formato Argentina)
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # 1. MÉTRICAS DE FACTURACIÓN (Columna FAC)
        st.subheader("💰 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        
        fac_si = df[df['FAC'] == 'SI']
        fac_no = df[df['FAC'] == 'NO']
        ya_fac = df[df['FAC'] == 'FAC']

        c1.metric("Ya Facturado (FAC)", f"$ {ya_fac['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar (SI)", f"$ {fac_si['PRECIO'].sum():,.0f}", help="Trabajos para facturar este mes")
        c3.metric("Próximo Mes (NO)", f"$ {fac_no['PRECIO'].sum():,.0f}")

        st.divider()

        # 2. VISTA DE PROGRAMACIÓN (FILTRO PARA EL GANTT)
        st.subheader("📅 Planificación de Unidades en Taller")
        
        # Filtro por Grupo
        grupos_disponibles = list(GIDS.keys())
        seleccion = st.multiselect("Filtrar por Grupo de Trabajo:", grupos_disponibles, default=grupos_disponibles)
        
        # Solo mostramos lo que NO está facturado (SI / NO) para programar
        df_pendientes = df[(df['FAC'].isin(['SI', 'NO'])) & (df['GRUPO_ORIGEN'].isin(seleccion))]
        
        # Ordenar por Fecha Promesa
        if 'FECH/PROM' in df_pendientes.columns:
            df_pendientes = df_pendientes.sort_values(by='FECH/PROM')

        st.dataframe(
            df_pendientes[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'ASESOR', 'OBSERVACIONES']],
            use_container_width=True
        )

        # 3. ESPACIO PARA EL GANTT
        st.info("💡 En la siguiente etapa, convertiremos esta tabla en un Diagrama de Gantt inteligente.")

except Exception as e:
    st.error(f"Error crítico en la aplicación: {e}")
