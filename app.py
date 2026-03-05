import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import re
import time

st.set_page_config(page_title="Gestión Taller CENOA", layout="wide")
st.title("🚀 Sistema de Gestión CENOA")

# --- CONFIGURACIÓN ---
ID_NUEVO_SHEET = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_NUEVO_SHEET}/export?format=csv&gid="

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

ASESORES_LISTA = ["SIN ASIGNAR", "CESAR OLIVA", "JAVIER GUTIERREZ", "ANDREA MARTINS"]

CLIENTES_LISTA = [
    "CENOA", "CENOA SEGURO", "CIEL", "CIEL SEGURO", "CIEL OKM", "CIEL USADO",
    "AUTOSOL", "AUTOSOL SEGURO", "AUTOSOL OKM", "AUTOSOL USADO", 
    "AUTOLUX", "AUTOLUX SEGURO", "AUTOLUX OKM", "AUTOLUX USADO",
    "PARTICULAR"
]

# --- FUNCIONES DE PROCESAMIENTO ---
def parsear_fecha_español(texto):
    if pd.isna(texto) or str(texto).strip() == "": 
        return None 
    
    texto = str(texto).lower().strip()
    
    match_dm = re.match(r'^(\d{1,2})[-/](\d{1,2})$', texto)
    if match_dm:
        dia, mes = match_dm.groups()
        return datetime(datetime.now().year, int(mes), int(dia))
        
    try:
        res = pd.to_datetime(texto, dayfirst=True)
        if pd.notna(res): return res.to_pydatetime()
    except:
        pass
        
    try:
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match:
            dia, mes_txt, anio = match.groups()
            mes_num = MESES_ES.get(mes_txt, 1)
            return datetime(int(anio), int(mes_num), int(dia))
    except:
        pass
            
    return None

@st.cache_data(ttl=60)
def obtener_turnos():
    columnas_base = ['Tipo', 'Fecha', 'Hora', 'Vehiculo', 'Patente', 'Asesor', 'Precio', 'Paños', 'Observaciones', 'Tiempo_Entrega', 'Cliente', 'Seguro', 'Recibido', 'Fotos', 'Cancelado', 'OR', 'Eliminar']
    if GID_TURNOS == "PONER_AQUI_GID_TURNOS":
        return pd.DataFrame(columns=columnas_base)
        
    url = f"{URL_BASE}{GID_TURNOS}"
    try:
        d = pd.read_csv(url, dtype=str)
        d.columns = d.columns.str.strip().str.upper()
        
        if 'PATENTE' in d.columns:
            d = d.dropna(subset=['PATENTE'])
            d = d[d['PATENTE'].str.strip() != ""]
        
        filas = []
        for _, row in d.iterrows():
            col_fecha = next((c for c in d.columns if 'FECH' in c), None)
            fecha_turno = parsear_fecha_español(row.get(col_fecha, ''))
            
            if fecha_turno is None:
                fecha_turno = datetime.now()
            
            asesor_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if asesor_raw not in ASESORES_LISTA:
                asesor_raw = "SIN ASIGNAR"
                
            col_tiempo = next((c for c in d.columns if 'TIEMPO' in c), None)
                
            filas.append({
                'Tipo': '📅 PROGRAMADO',
                'Fecha': fecha_turno.date(), 
                'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(),
                'Patente': str(row.get('PATENTE', '')).upper(),
                'Asesor': asesor_raw,
                'Precio': str(row.get('PRECIO', '')).strip(),
                'Paños': str(row.get('PAÑOS', '')).strip(),
                'Observaciones': str(row.get('OBSERVACIONES', '')).strip(),
                'Tiempo_Entrega': str(row.get(col_tiempo, '')) if col_tiempo else "",
                'Cliente': str(row.get('CLIENTE', '')).upper(),
                'Seguro': str(row.get('SEGURO', '')).upper(),
                'Recibido': False,
                'Fotos': False,
                'Cancelado': False,
                'OR': "",
                'Eliminar': False
            })
        return pd.DataFrame(filas)
    except Exception as e:
        return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=60)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            
            # Forzamos Columna T (índice 19) para Estado
            if len(d.columns) > 19:
                cols = list(d.columns)
                cols[19] = 'ESTADO_TALLER'
                d.columns = cols

            # NUEVO: Forzamos Columna I (índice 8) para Fecha Prometida
            if len(d.columns) > 8:
                cols = list(d.columns)
                cols[8] = 'FECHA_PROMESA_I'
                d.columns = cols
                
            d.columns = d.columns.str.strip().str.upper()
            
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d = d[d['PATENTE'].str.strip() != ""]
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
    
    if not dfs: return pd.DataFrame()
    
    df_raw = pd.concat(dfs, ignore_index=True)
    filas = []
    
    for _, row in df_raw.iterrows():
        # Usamos la columna I para la fecha
        f_fin = parsear_fecha_español(row.get('FECHA_PROMESA_I', ''))
        
        fecha_promesa_display = f_fin.date() if f_fin is not None else None
        if f_fin is None:
            f_fin = datetime.now() + timedelta(days=3650)
        
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.')
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            panos = float(numeros[0]) if numeros else 1.0
        except: panos = 1.0
            
        f_inicio = f_fin - timedelta(days=max(1, int(panos)))
        
        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: precio_val = float(precio_raw) if precio_raw != "" else 0.0
        except: precio_val = 0.0

        estado_taller = str(row.get('ESTADO_TALLER', '')).replace('nan', '').strip().upper()
        if not estado_taller: estado_taller = "SIN ESTADO"

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Asesor': str(row.get('ASESOR', 'SIN ASESOR')).strip().upper(),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio,
            'Fin': f_fin,
            'Fecha_Promesa_Disp': fecha_promesa_display,
            'Paños': panos,
            'Estado_Fac': str(row.get('FAC', '')).strip().upper(),
            'Estado_Taller': estado_taller,
            'Precio': precio_val
        })
    return pd.DataFrame(filas)

# --- BLINDAJE DE MEMORIA ---
if 'memoria_turnos_v11' not in st.session_state:
    st.session_state.memoria_turnos_v11 = obtener_turnos()

# --- EJECUCIÓN ---
df = obtener_datos_maestros()
tab_turnos, tab_prog, tab_fac, tab_kpi = st.tabs(["📋 Turnero Diario", "🛠️ Programación", "💰 Facturación", "📊 KPIs"])

# ==========================================
# PESTAÑA 1: TURNERO DIARIO (RECUPERADA)
# ==========================================
with tab_turnos:
    st.subheader("Recepción de Vehículos")
    col_fecha, col_asesor, col_add = st.columns([1, 1, 2])
    
    with col_fecha:
        hoy = datetime.today().date()
        fechas_seleccionadas = st.date_input("📅 Rango de Fechas", value=(hoy, hoy), format="DD/MM/YYYY")
        if isinstance(fechas_seleccionadas, tuple):
            if len(fechas_seleccionadas) == 2: f_inicio_f, f_fin_f = fechas_seleccionadas
            else: f_inicio_f = f_fin_f = fechas_seleccionadas[0]
        else: f_inicio_f = f_fin_f = fechas_seleccionadas

    with col_asesor:
        asesor_filtro = st.selectbox("👔 Filtrar por Asesor", ["TODOS"] + ASESORES_LISTA)
    
    with col_add:
        with st.expander("➕ Ingresar vehículo SIN TURNO (Walk-in)"):
            with st.form("form_sin_turno", clear_on_submit=True):
                c_pat, c_veh, c_cli = st.columns(3)
                nueva_patente = c_pat.text_input("Patente *")
                nuevo_vehiculo = c_veh.text_input("Vehículo *")
                nuevo_cliente = c_cli.selectbox("Cliente", CLIENTES_LISTA)
                c_seg, c_pre, c_pan = st.columns(3)
                nuevo_seguro = c_seg.text_input("Seguro")
                nuevo_precio = c_pre.text_input("Precio ($)")
                nuevo_panos = c_pan.text_input("Paños (Ej: 1.5)")
                c_tie, c_obs, c_ase = st.columns(3)
                nuevo_tiempo = c_tie.text_input("Tiempo Entrega (Días)")
                nueva_obs = c_obs.text_input("Observaciones")
                idx_ase = ASESORES_LISTA.index(asesor_filtro) if asesor_filtro in ASESORES_LISTA else 0
                nuevo_asesor = c_ase.selectbox("Asesor", ASESORES_LISTA, index=idx_ase)
                
                if st.form_submit_button("Agregar al Turnero"):
                    if nueva_patente and nuevo_vehiculo:
                        nuevo_ingreso = pd.DataFrame([{
                            'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_inicio_f, 'Hora': '-',
                            'Vehiculo': nuevo_vehiculo.upper(), 'Patente': nueva_patente.upper(),
                            'Asesor': nuevo_asesor, 'Precio': nuevo_precio, 'Paños': nuevo_panos,
                            'Observaciones': nueva_obs, 'Tiempo_Entrega': nuevo_tiempo,
                            'Cliente': nuevo_cliente, 'Seguro': nuevo_seguro.upper(),
                            'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
                        }])
                        st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, nuevo_ingreso], ignore_index=True)
                        st.success("Agregado."); time.sleep(0.5); st.rerun()

    st.divider()
    mask = (st.session_state.memoria_turnos_v11['Fecha'] >= f_inicio_f) & (st.session_state.memoria_turnos_v11['Fecha'] <= f_fin_f)
    df_rango = st.session_state.memoria_turnos_v11[mask].copy()
    if asesor_filtro != "TODOS": df_rango = df_rango[df_rango['Asesor'] == asesor_filtro]

    if not df_rango.empty:
        df_rango['OR'] = df_rango['OR'].fillna("")
        df_activos = df_rango[df_rango['Cancelado'] == False]
        mascara_rec = (df_activos['OR'].str.strip() != "") & (df_activos['Recibido'] == True) & (df_activos['Fotos'] == True)
        
        df_pend = df_activos[~mascara_rec].sort_values(['Fecha', 'Hora'])
        df_reci = df_activos[mascara_rec].sort_values(['Fecha', 'Hora'])

        st.write("### ⏱️ Turnos Pendientes")
        ed_p = st.data_editor(df_pend[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']], 
                               column_config={"Recibido": st.column_config.CheckboxColumn("✅"), "Fotos": st.column_config.CheckboxColumn("📸")},
                               hide_index=True, use_container_width=True, key="ed_pend")
        
        if st.button("💾 Guardar Pendientes"):
            for idx, row in ed_p.iterrows():
                st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Recibido', 'Fotos', 'OR', 'Cancelado']]
            st.success("Guardado"); time.sleep(0.5); st.rerun()

        st.write("### 🏁 Recibidos")
        st.dataframe(df_reci[['Patente', 'Vehiculo', 'Asesor', 'OR']], hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN (SEPARADO POR GRUPO Y ESTADO)
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación y Estado del Taller")
    
    if not df.empty:
        col1, col2 = st.columns(2)
        
        def mostrar_bloques_estado(df_grupo, key_prefix):
            # Diccionario de estados solicitados
            estados = {
                "⏳ EN PROCESO": "EN PROCESO",
                "⛔ DETENIDOS": "DETENIDO",
                "✅ TERMINADOS (Pte. Fact/Entr)": "TERMINADO",
                "🚚 ENTREGADOS": "ENTREGADO"
            }
            
            for label, key_match in estados.items():
                # Filtrar por el estado (que contenga la palabra clave)
                df_est = df_grupo[df_grupo['Estado_Taller'].str.contains(key_match, na=False)].copy()
                
                if "DETENIDO" in key_match:
                    st.error(f"**{label}**")
                else:
                    st.info(f"**{label}**")
                
                if not df_est.empty:
                    df_est = df_est.sort_values(by='Fin')
                    df_est['Fecha Prom.'] = df_est['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
                    st.dataframe(df_est[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor']], hide_index=True, use_container_width=True, key=f"{key_prefix}_{key_match}")
                else:
                    st.caption("Sin datos.")

        with col1:
            st.write("## 🧑‍🔧 GRUPO UNO")
            mostrar_bloques_estado(df[df['Grupo'] == 'GRUPO UNO'], "G1")
            
        with col2:
            st.write("## 🧑‍🔧 GRUPO DOS")
            mostrar_bloques_estado(df[df['Grupo'] == 'GRUPO DOS'], "G2")

# ==========================================
# PESTAÑAS 3 Y 4 (IGUAL QUE TU CÓDIGO)
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación")
        m1, m2, m3 = st.columns(3)
        m1.metric("Facturado (FAC)", f"$ {df[df['Estado_Fac'] == 'FAC']['Precio'].sum():,.0f}")
        m2.metric("Confirmado (SI)", f"$ {df[df['Estado_Fac'] == 'SI']['Precio'].sum():,.0f}")
        m3.metric("Pendiente (NO)", f"$ {df[df['Estado_Fac'] == 'NO']['Precio'].sum():,.0f}")

with tab_kpi:
    if not df.empty:
        st.subheader("Indicadores KPI")
        k1, k2, k3 = st.columns(3)
        k1.metric("Ticket Promedio", f"$ {df[df['Estado_Fac'] == 'FAC']['Precio'].mean():,.0f}")

with st.sidebar:
    if st.button("🔄 Refrescar Datos"):
        st.cache_data.clear()
        if 'memoria_turnos_v11' in st.session_state: del st.session_state['memoria_turnos_v11']
        st.rerun()
