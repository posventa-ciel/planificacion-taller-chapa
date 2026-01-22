import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Taller - Autociel", layout="wide")

# 2. Función para convertir el link de la hoja en un link de descarga directa
def get_google_sheet_url(base_url, sheet_name):
    # Extraer el ID del spreadsheet
    ss_id = base_url.split("/d/")[1].split("/")[0]
    # Codificar el nombre de la pestaña para la URL (maneja espacios)
    sheet_name_parsed = sheet_name.replace(" ", "%20")
    return f"https://docs.google.com/spreadsheets/d/{ss_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_parsed}"

@st.cache_data(ttl=300)
def cargar_datos_robusto():
    base_url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit"
    pestanas = ["GRUPO UNO", "GRUPO DOS", "GRUPO 3", "TERCEROS"]
    lista_dfs = []
    
    for p in pestanas:
        try:
            csv_url = get_google_sheet_url(base_url, p)
            # Leemos directamente con pandas usando la URL transformada
            df_p = pd.read_csv(csv_url)
            
            if not df_p.empty:
                # Limpiar nombres de columnas
                df_p.columns = df_p.columns.str.strip()
                # Filtrar columnas vacías (Unnamed)
                df_p = df_p.loc[:, ~df_p.columns.str.contains('^Unnamed')]
                df_p['GRUPO_ORIGEN'] = p
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error cargando {p}: {e}")
            
    if not lista_dfs:
        return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

# 3. Lógica de la App
st.title("📊 Tablero de Control - Taller de Chapa y Pintura")

try:
    df_raw = cargar_datos_robusto()
    
    if df_raw.empty:
        st.warning("No se pudieron cargar datos. Verifica que el Sheet sea público.")
    else:
        # Limpieza: eliminamos filas donde la PATENTE sea nula
        df = df_raw.dropna(subset=['PATENTE']).copy()
        
        # Convertir PRECIO a número (limpiando posibles símbolos de $ o puntos)
        if 'PRECIO' in df.columns:
            df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
            df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # --- Lógica de Facturación (Columna FAC) ---
        # FAC = Facturado, SI = Este mes, NO = Mes próximo
        facturado = df[df['FAC'] == 'FAC']
        proyectado_mes = df[df['FAC'] == 'SI']
        proyectado_prox_mes = df[df['FAC'] == 'NO']

        # --- Métricas ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {facturado['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {proyectado_mes['PRECIO'].sum():,.0f}")
        c3.metric("Proyectado Próximo (NO)", f"$ {proyectado_prox_mes['PRECIO'].sum():,.0f}")

        st.divider()

        # --- Tabla de Gestión ---
        st.subheader("📋 Unidades en Proceso (SI / NO)")
        df_pendientes = df[df['FAC'].isin(['SI', 'NO'])].sort_values(by='GRUPO_ORIGEN')
        
        st.dataframe(
            df_pendientes[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']],
            use_container_width=True
        )

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
