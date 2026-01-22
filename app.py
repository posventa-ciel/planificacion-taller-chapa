import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Planificación Taller Chapa y Pintura", layout="wide")

st.title("📊 Seguimiento de Turnos - Taller de Chapa y Pintura")

# URL de tu Google Sheet
url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit#gid=609774337"

# Crear la conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer los datos
try:
    # Leemos la hoja, especificando que los datos están en la pestaña principal
    df = conn.read(spreadsheet=url, usecols=[0,1,2,3,4,5,6,7]) # Ajusta las columnas según necesites
    
    # Limpiar filas vacías si las hay
    df = df.dropna(subset=['Dominio'])

    # Filtros rápidos en el lateral
    st.sidebar.header("Filtros")
    asesor_filtro = st.sidebar.multiselect("Filtrar por Asesor:", options=df["Asesor"].unique())
    estado_filtro = st.sidebar.multiselect("Filtrar por Estado:", options=df["Estado"].unique())

    # Aplicar filtros
    if asesor_filtro:
        df = df[df["Asesor"].isin(asesor_filtro)]
    if estado_filtro:
        df = df[df["Estado"].isin(estado_filtro)]

    # Mostrar métricas rápidas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vehículos", len(df))
    col2.metric("En Proceso", len(df[df["Estado"] == "EN PROCESO"])) # Ajusta según tus etiquetas
    col3.metric("Pendientes", len(df[df["Estado"] == "PENDIENTE"]))

    # Mostrar la tabla de datos
    st.subheader("📋 Información Actual del Sheet")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"No se pudo conectar con el Sheet. Revisá los permisos de compartir. Error: {e}")

# Pie de página
st.info("Próximo paso: Agregar la lógica de programación por Grupo A/B y el diagrama de Gantt.")
