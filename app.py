import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Planificación Taller Chapa", layout="wide")

st.title("🚗 Gestión de Turnos y Programación - Taller de Chapa")

url = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/edit#gid=609774337"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leemos el sheet
    df = conn.read(spreadsheet=url)
    df.columns = df.columns.str.strip() # Limpiamos espacios

    # Mapeo de columnas según lo que detectamos
    col_patente = "PATENTE"
    col_vehiculo = "VEHICULO"
    col_asesor = "ASESOR"
    col_estado = "REFERENCIA" # Usamos REFERENCIA o alguna otra como estado provisional
    col_promesa = "FECH/PROM"

    # Limpieza básica
    df = df.dropna(subset=[col_patente])

    # --- INTERFAZ DE USUARIO ---
    
    tab1, tab2 = st.tabs(["📋 Vista General", "🛠️ Programación Jefe de Taller"])

    with tab1:
        st.subheader("Estado Actual del Taller")
        
        # Filtros
        c1, c2 = st.columns(2)
        with c1:
            filtro_asesor = st.multiselect("Filtrar por Asesor", options=df[col_asesor].unique())
        with c2:
            search = st.text_input("Buscar por Patente o Modelo")

        # Aplicar filtros
        df_display = df.copy()
        if filtro_asesor:
            df_display = df_display[df_display[col_asesor].isin(filtro_asesor)]
        if search:
            df_display = df_display[df_display[col_patente].str.contains(search, case=False, na=False) | 
                                    df_display[col_vehiculo].str.contains(search, case=False, na=False)]

        st.dataframe(df_display[[col_patente, col_vehiculo, col_asesor, col_promesa, "PAÑOS", "OBSERVACIONES"]], use_container_width=True)

    with tab2:
        st.subheader("Asignación de Tiempos y Grupos")
        st.write("Seleccioná un vehículo para programar su trabajo en el Gantt.")
        
        # Selector de vehículo para editar
        patente_sel = st.selectbox("Seleccionar Vehículo por Patente", options=df[col_patente].unique())
        
        if patente_sel:
            datos_auto = df[df[col_patente] == patente_sel].iloc[0]
            
            st.info(f"Programando: {datos_auto[col_vehiculo]} - Asesor: {datos_auto[col_asesor]}")
            
            with st.form("form_programacion"):
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    grupo = st.radio("Asignar a Grupo:", ["Grupo A", "Grupo B"], horizontal=True)
                    dias_chapa = st.number_input("Días de Chapa (Estimado)", min_value=0.0, step=0.5, value=1.0)
                
                with col_f2:
                    dias_prep = st.number_input("Días de Preparación", min_value=0.0, step=0.5, value=1.0)
                    dias_pinto = st.number_input("Días de Pintura", min_value=0.0, step=0.5, value=1.0)
                
                comentario = st.text_area("Notas para los técnicos")
                
                btn_guardar = st.form_submit_button("Actualizar Programación")
                
                if btn_guardar:
                    st.success(f"¡Datos guardados! (Simulado) - Total días: {dias_chapa + dias_prep + dias_pinto}")
                    # Aquí es donde luego programaremos que escriba en el Sheet o en una base de datos local

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
