import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de la página (DEBE IR PRIMERO)
st.set_page_config(page_title="Gestión de Taller - Autociel", layout="wide")

# 2. Conexión y URL
url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit#gid=609774337"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Función de carga de datos con decorador después de importar 'st'
@st.cache_data(ttl=300)
def cargar_datos():
    # Nombres exactos de tus pestañas
    pestanas = ["GRUPO UNO", "GRUPO DOS", "GRUPO 3", "TERCEROS"]
    lista_dfs = []
    
    for p in pestanas:
        try:
            # Intentamos leer la pestaña. 
            # La librería st-gsheets ya debería manejar los espacios, 
            # pero si falla, leeremos la hoja completa.
            df_p = conn.read(spreadsheet=url, worksheet=p)
            
            if df_p is not None and not df_p.empty:
                df_p.columns = df_p.columns.str.strip()
                df_p['GRUPO_ORIGEN'] = p
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"No se pudo leer la pestaña '{p}': {e}")
            
    if not lista_dfs:
        return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

# 4. Lógica Principal
try:
    st.title("📊 Control de Producción y Facturación")
    
    df_raw = cargar_datos()
    
    if df_raw.empty:
        st.warning("No se encontraron datos en las pestañas especificadas.")
    else:
        # Limpieza y conversión
        df = df_raw.dropna(subset=['PATENTE']).copy()
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)
        
        # --- FILTROS DE FACTURACIÓN (Columna FAC) ---
        # FAC = Facturado, SI = Mes curso, NO = Próximo mes
        facturado = df[df['FAC'] == 'FAC']
        proyectado_mes = df[df['FAC'] == 'SI']
        proyectado_prox_mes = df[df['FAC'] == 'NO']

        # --- MÉTRICAS ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {facturado['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {proyectado_mes['PRECIO'].sum():,.0f}")
        c3.metric("Proyectado Próximo (NO)", f"$ {proyectado_prox_mes['PRECIO'].sum():,.0f}")

        st.divider()

        # --- TABLA DE TRABAJO ---
        st.subheader("📋 Unidades Pendientes de Facturación (SI / NO)")
        df_pendientes = df[df['FAC'].isin(['SI', 'NO'])]
        
        st.dataframe(
            df_pendientes[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']],
            use_container_width=True
        )

except Exception as e:
    st.error(f"Error general en la aplicación: {e}")
