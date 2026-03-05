import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Sistema de Gestión Autociel")

# --- CONFIGURACIÓN ---
ID_NUEVO_SHEET = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_NUEVO_SHEET}/export?format=csv&gid="

# 🚨 GID de la pestaña "TURNOS" corregido
GID_TURNOS = "109364752" 

GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# Lista de asesores
ASESORES_LISTA = ["SIN ASIGNAR", "CESAR OLIVA", "JAVIER GUTIERREZ", "ANDREA MARTINS"]

# --- FUNCIONES DE PROCESAMIENTO ---
def parsear_fecha_español(texto):
    if pd.isna(texto) or str(texto).strip() == "": 
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    texto = str(texto).lower().strip()
    try:
        return pd.to_datetime(texto, dayfirst=True)
    except:
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match:
            dia, mes_txt, anio = match.groups()
            mes_num = MESES_ES.get(mes_txt, 1)
            return datetime(int(anio), int(mes_num), int(dia))
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

@st.cache_data(ttl=60)
def obtener_turnos():
    """Lee la pestaña de turnos del sheet"""
    if GID_TURNOS == "PONER_AQUI_GID_TURNOS":
        return pd.DataFrame(columns=['Fecha', 'Patente', 'Vehiculo', 'Asesor', 'Recibido', 'Fotos', 'OR'])
        
    url = f"{URL_BASE}{GID_TURNOS}"
    try:
        d = pd.read_csv(url, dtype=str)
        d.columns = d.columns.str.strip().str.upper()
        
        filas = []
        for _, row in d.iterrows():
            col_fecha = next((c for c in d.columns if 'FECH' in c), None)
            fecha_turno = parsear_fecha_español(row.get(col_fecha, ''))
            
            asesor_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if asesor_raw not in ASESORES_LISTA:
                asesor_raw = "SIN ASIGNAR"
                
            filas.append({
                'Fecha': fecha_turno.date(), 
                'Patente': str(row.get('PATENTE', '')).upper(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(),
                'Asesor': asesor_raw,
                'Recibido': False,
                'Fotos': False,
                'OR': ""
            })
        return pd.DataFrame(filas)
    except Exception as e:
        return pd.DataFrame(columns=['Fecha', 'Patente', 'Vehiculo', 'Asesor', 'Recibido', 'Fotos', 'OR'])

@st.cache_data(ttl=60)
def obtener_datos_maestros():
    """Lee el resto de las pestañas para programación y KPIs"""
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip().str.upper()
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
    
    if not dfs: return pd.DataFrame()
    
    df_raw = pd.concat(dfs, ignore_index=True)
    filas = []
    
    for _, row in df_raw.iterrows():
        col_fecha = next((c for c in df_raw.columns if 'FECH' in c or 'PROMESA' in c), None)
        f_fin = parsear_fecha_español(row.get(col_fecha, ''))
        
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.')
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            panos = float(numeros[0]) if numeros else 1.0
        except: panos = 1.0
            
        f_inicio = f_fin - timedelta(days=max(1, int(panos)))
        
        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: precio_val = float(precio_raw) if precio_raw != "" else 0.0
        except: precio_val = 0.0

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Asesor': str(row.get('ASESOR', 'SIN ASESOR')).strip().upper(),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio,
            'Fin': f_fin,
            'Paños': panos,
            'Estado': str(row.get('FAC', '')).strip().upper(),
            'Precio': precio_val
        })
    return pd.DataFrame(filas)

# --- MANEJO DE ESTADO TEMPORAL (TURNOS) ---
if 'df_turnos_memoria' not in st.session_state:
    st.session_state.df_turnos_memoria = obtener_turnos()

# --- EJECUCIÓN ---
df = obtener_datos_maestros()

# Creamos las 4 pestañas
tab_turnos, tab_prog, tab_fac, tab_kpi = st.tabs(["📋 Turnero Diario", "📅 Programación", "💰 Facturación", "📊 KPIs"])

# ==========================================
# PESTAÑA 1: TURNERO DIARIO
# ==========================================
with tab_turnos:
    st.subheader("Recepción de Vehículos")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        fecha_filtro = st.date_input("📅 Seleccionar Fecha", value=datetime.today())
    
    with col2:
        with st.expander("➕ Ingresar vehículo SIN TURNO (Walk-in)"):
            with st.form("form_sin_turno"):
                c_pat, c_veh, c_ase = st.columns(3)
                nueva_patente = c_pat.text_input("Patente")
                nuevo_vehiculo = c_veh.text_input("Vehículo")
                nuevo_asesor = c_ase.selectbox("Asesor", ASESORES_LISTA)
                
                if st.form_submit_button("Agregar al día"):
                    if nueva_patente:
                        nuevo_ingreso = pd.DataFrame([{
                            'Fecha': fecha_filtro,
                            'Patente': nueva_patente.upper(),
                            'Vehiculo': nuevo_vehiculo.upper(),
                            'Asesor': nuevo_asesor,
                            'Recibido': False,
                            'Fotos': False,
                            'OR': ""
                        }])
                        st.session_state.df_turnos_memoria = pd.concat([st.session_state.df_turnos_memoria, nuevo_ingreso], ignore_index=True)
                        st.success(f"Ingreso de {nueva_patente} agregado.")
                        st.rerun()

    st.divider()

    df_hoy = st.session_state.df_turnos_memoria[st.session_state.df_turnos_memoria['Fecha'] == fecha_filtro].copy()

    if df_hoy.empty:
        st.info(f"No hay turnos programados para la fecha: {fecha_filtro.strftime('%d/%m/%Y')}")
    else:
        df_hoy['OR'] = df_hoy['OR'].fillna("")
        df_pendientes = df_hoy[df_hoy['OR'].str.strip() == ""].sort_values('Asesor')
        df_recibidos = df_hoy[df_hoy['OR'].str.strip() != ""]

        st.write("### ⏱️ Turnos Pendientes")
        if not df_pendientes.empty:
            edited_df = st.data_editor(
                df_pendientes,
                column_config={
                    "Fecha": None, 
                    "Patente": st.column_config.TextColumn("Patente", disabled=True),
                    "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True),
                    "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA),
                    "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False),
                    "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False),
                    "OR": st.column_config.TextColumn("📝 N° de OR (Abre para mover)", max_chars=10)
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_pendientes_{fecha_filtro}"
            )
            
            # Al guardar, solo se actualizan los registros que se editaron
            if st.button("💾 Guardar Checklist y OR"):
                for idx, row in edited_df.iterrows():
                    st.session_state.df_turnos_memoria.loc[idx, 'Asesor'] = row['Asesor']
                    st.session_state.df_turnos_memoria.loc[idx, 'Recibido'] = row['Recibido']
                    st.session_state.df_turnos_memoria.loc[idx, 'Fotos'] = row['Fotos']
                    st.session_state.df_turnos_memoria.loc[idx, 'OR'] = row['OR']
                st.success("Cambios actualizados.")
                st.rerun() 
                
        else:
            st.success("¡Todos los vehículos del día ya tienen OR abierta!")

        st.write("### 🏁 Turnos Recibidos (Con OR Abierta)")
        if not df_recibidos.empty:
            st.dataframe(
                df_recibidos[['Patente', 'Vehiculo', 'Asesor', 'OR']],
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.write("Aún no se ha abierto ninguna OR en este día.")

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN
# ==========================================
with tab_prog:
    if not df.empty:
        st.subheader("Cronograma de Trabajo (Basado en Paños)")
        df_gantt = df[df['Estado'].isin(['SI', 'NO'])].copy()
        if not df_gantt.empty:
            df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo'].str[:15]
            fig = px.timeline(
                df_gantt, x_start="Inicio", x_end="Fin", y="ID", color="Grupo", text="Paños",
                hover_data=["Asesor", "Estado"], title="Carga de Taller por Grupo"
            )
            fig.update_yaxes(autorange="reversed")
            
            milisegundos_hoy = datetime.now().timestamp() * 1000
            fig.add_vline(x=milisegundos_hoy, line_dash="dash", line_color="red")
            fig.add_annotation(x=milisegundos_hoy, y=1.05, yref="paper", text="HOY", showarrow=False, font=dict(color="red", size=12))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay vehículos pendientes con estado SI o NO.")

# ==========================================
# PESTAÑA 3: FACTURACIÓN
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación")
        m1, m2, m3 = st.columns(3)
        m1.metric("Facturado (FAC)", f"$ {df[df['Estado'] == 'FAC']['Precio'].sum():,.0f}")
        m2.metric("Confirmado (SI)", f"$ {df[df['Estado'] == 'SI']['Precio'].sum():,.0f}")
        m3.metric("Pendiente (NO)", f"$ {df[df['Estado'] == 'NO']['Precio'].sum():,.0f}")
        
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### 👥 Por Grupo")
            res_grupo = df.groupby(['Grupo', 'Estado'])['Precio'].sum().unstack(fill_value=0)
            st.table(res_grupo.style.format("$ {:,.0f}"))
        with col_b:
            st.write("### 👔 Por Asesor")
            res_asesor = df.groupby(['Asesor', 'Estado'])['Precio'].sum().unstack(fill_value=0)
            st.table(res_asesor.style.format("$ {:,.0f}"))

# ==========================================
# PESTAÑA 4: KPIs
# ==========================================
with tab_kpi:
    if not df.empty:
        st.subheader("Indicadores Clave de Desempeño (KPI)")
        k1, k2, k3 = st.columns(3)
        
        df_fac = df[df['Estado'] == 'FAC']
        ticket = df_fac['Precio'].mean() if not df_fac.empty else 0
        k1.metric("Ticket Promedio (FAC)", f"$ {ticket:,.0f}")
        
        intensidad = df['Paños'].mean()
        k2.metric("Paños Promedio / Auto", f"{intensidad:.2f}")
        
        total_casos = len(df[df['Estado'].isin(['FAC', 'SI', 'NO'])])
        casos_fac = len(df_fac)
        ratio = (casos_fac / total_casos * 100) if total_casos > 0 else 0
        k3.metric("% Conversión a Facturado", f"{ratio:.1f}%")

        st.divider()
        st.write("### Cantidad de Vehículos por Asesor")
        fig_asesor = px.bar(df, x="Asesor", color="Estado", barmode="group")
        st.plotly_chart(fig_asesor, use_container_width=True)

with st.sidebar:
    if st.button("🔄 Refrescar Datos desde Sheet"):
        st.cache_data.clear()
        if 'df_turnos_memoria' in st.session_state:
            del st.session_state['df_turnos_memoria']
        st.rerun()
