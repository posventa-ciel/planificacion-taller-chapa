import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestión de Taller - Autociel", layout="wide")

# --- CONFIGURACIÓN DE GIDs (Cambiá estos números por los de tu Sheet) ---
GIDS = {
    "GRUPO UNO": "0", 
    "GRUPO DOS": "123456789", # <-- CAMBIAR ESTE
    "GRUPO TRES": "609774337", 
    "TERCEROS": "987654321"    # <-- CAMBIAR ESTE
}

def get_sheet_url_by_gid(gid):
    ss_id = "1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw"
    return f"https://docs.google.com/spreadsheets/d/{ss_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=60)
def cargar_datos_seguros():
    lista_dfs = []
    for nombre, gid in GIDS.items():
        try:
            url = get_sheet_url_by_gid(gid)
            df_p = pd.read_csv(url)
            
            # Limpieza inmediata
            df_p.columns = df_p.columns.str.strip()
            # Nos aseguramos de que la fila tenga una PATENTE válida
            df_p = df_p.dropna(subset=['PATENTE'])
            df_p['GRUPO_ORIGEN'] = nombre
            lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error en {nombre} (GID {gid}): {e}")
            
    return pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()

# --- INTERFAZ ---
st.title("📊 Control de Producción - Autociel")

try:
    df = cargar_datos_seguros()
    
    if not df.empty:
        # Limpieza de precios (formato Argentina)
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # Separación por estado FAC
        facturado = df[df['FAC'] == 'FAC']
        mes_curso = df[df['FAC'] == 'SI']
        proximo_mes = df[df['FAC'] == 'NO']

        # Métricas principales
        c1, c2, c3 = st.columns(3)
        c1.metric("Facturado (FAC)", f"$ {facturado['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar (SI)", f"$ {mes_curso['PRECIO'].sum():,.0f}")
        c3.metric("Proyectado (NO)", f"$ {proximo_mes['PRECIO'].sum():,.0f}")

        st.divider()

        # Selector para verificar cada grupo por separado
        grupo_verificar = st.selectbox("Verificar Integridad de Datos por Grupo:", options=GIDS.keys())
        df_verificar = df[df['GRUPO_ORIGEN'] == grupo_verificar]
        
        st.write(f"Mostrando {len(df_verificar)} unidades encontradas en {grupo_verificar}")
        st.dataframe(df_verificar[['PATENTE', 'VEHICULO', 'PAÑOS', 'FAC', 'ASESOR']], use_container_width=True)

except Exception as e:
    st.error(f"Error general: {e}")
