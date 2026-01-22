import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Planificación Taller Chapa y Pintura", layout="wide")

st.title("📊 Seguimiento de Turnos - Taller de Chapa y Pintura")

# URL de tu Google Sheet (la principal)
url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit#gid=609774337"

# Crear la conexión
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leemos TODO el sheet primero para ver qué nombres de columnas tiene
    df = conn.read(spreadsheet=url)
    
    # Limpiamos nombres de columnas (quita espacios raros)
    df.columns = df.columns.str.strip()

    # Verificamos si existe la columna Dominio (o DOMINIO)
    columna_clave = "Dominio" if "Dominio" in df.columns else "DOMINIO"
    
    if columna_clave in df.columns:
        # Limpiar filas donde el Dominio esté vacío
        df = df.dropna(subset=[columna_clave])

        # Filtros en el lateral
        st.sidebar.header("Filtros")
        
        # Asesor
        col_asesor = "Asesor" if "Asesor" in df.columns else df.columns[2] # Por si cambia el nombre
        asesor_filtro = st.sidebar.multiselect("Filtrar por Asesor:", options=df[col_asesor].unique())
        
        # Estado
        col_estado = "Estado" if "Estado" in df.columns else df.columns[3]
        estado_filtro = st.sidebar.multiselect("Filtrar por Estado:", options=df[col_estado].unique())

        if asesor_filtro:
            df = df[df[col_asesor].isin(asesor_filtro)]
        if estado_filtro:
            df = df[df[col_estado].isin(estado_filtro)]

        # Métricas
        col1, col2 = st.columns(2)
        col1.metric("Total Vehículos", len(df))
        if col_estado in df.columns:
            en_proceso = len(df[df[col_estado].str.contains("PROCESO", na=False, case=False)])
            col2.metric("En Proceso/Taller", en_proceso)

        # Mostrar Tabla Principal
        st.subheader("📋 Información Actual del Taller")
        st.dataframe(df, use_container_width=True)
    else:
        st.error(f"No encontré la columna 'Dominio'. Las columnas detectadas son: {list(df.columns)}")
        st.write("Asegurate de que la primera fila de tu Sheet tenga los encabezados.")

except Exception as e:
    st.error(f"Error de conexión o lectura: {e}")

st.info("💡 Si ves la tabla arriba, el siguiente paso es crear el formulario para asignar Grupos A/B.")
