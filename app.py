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
    except: pass
    try:
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match:
            dia, mes_txt, anio = match.groups()
            mes_num = MESES_ES.get(mes_txt, 1)
            return datetime(int(anio), int(mes_num), int(dia))
    except: pass
    return None

@st.cache_data(ttl=60)
def obtener_turnos():
    columnas_base = ['Tipo', 'Fecha', 'Hora', 'Vehiculo', 'Patente', 'Asesor', 'Precio', 'Paños', 'Observaciones', 'Tiempo_Entrega', 'Cliente', 'Seguro', 'Recibido', 'Fotos', 'Cancelado', 'OR', 'Eliminar']
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
            f_turno = parsear_fecha_español(row.get(col_fecha, ''))
            if f_turno is None: f_turno = datetime.now()
            ase_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if ase_raw not in ASESORES_LISTA: ase_raw = "SIN ASIGNAR"
            col_t = next((c for c in d.columns if 'TIEMPO' in c), None)
            filas.append({
                'Tipo': '📅 PROGRAMADO', 'Fecha': f_turno.date(), 'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(), 'Patente': str(row.get('PATENTE', '')).upper(),
                'Asesor': ase_raw, 'Precio': str(row.get('PRECIO', '')).strip(), 'Paños': str(row.get('PAÑOS', '')).strip(),
                'Observaciones': str(row.get('OBSERVACIONES', '')).strip(), 'Tiempo_Entrega': str(row.get(col_t, '')) if col_t else "",
                'Cliente': str(row.get('CLIENTE', '')).upper(), 'Seguro': str(row.get('SEGURO', '')).upper(),
                'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
            })
        return pd.DataFrame(filas)
    except: return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=60)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            # Columna T para Estado y Columna I para Promesa
            if len(d.columns) > 19:
                cols = list(d.columns)
                cols[19] = 'ESTADO_TALLER'
                d.columns = cols
            if len(d.columns) > 8:
                cols = list(d.columns)
                cols[8] = 'FECHA_PROMESA_I' # <-- Ajuste Columna I
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
        f_fin = parsear_fecha_español(row.get('FECHA_PROMESA_I', ''))
        fecha_disp = f_fin.date() if f_fin is not None else None
        if f_fin is None: f_fin = datetime.now() + timedelta(days=3650)
        try:
            txt_p = str(row.get('PAÑOS', '1')).replace(',', '.')
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", txt_p)
            panos = float(nums[0]) if nums else 1.0
        except: panos = 1.0
        f_ini = f_fin - timedelta(days=max(1, int(panos)))
        pre_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: pre_val = float(pre_raw) if pre_raw != "" else 0.0
        except: pre_val = 0.0
        est_t = str(row.get('ESTADO_TALLER', '')).replace('nan', '').strip().upper()
        if not est_t: est_t = "SIN ESTADO"
        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'), 'Asesor': str(row.get('ASESOR', 'SIN ASESOR')).strip().upper(),
            'Patente': str(row.get('PATENTE', '')), 'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_ini, 'Fin': f_fin, 'Fecha_Promesa_Disp': fecha_disp,
            'Paños': panos, 'Estado_Fac': str(row.get('FAC', '')).strip().upper(),
            'Estado_Taller': est_t, 'Precio': pre_val
        })
    return pd.DataFrame(filas)

if 'memoria_turnos_v11' not in st.session_state:
    st.session_state.memoria_turnos_v11 = obtener_turnos()

df = obtener_datos_maestros()
t_tur, t_pro, t_fac, t_kpi = st.tabs(["📋 Turnero Diario", "🛠️ Programación", "💰 Facturación", "📊 KPIs"])

# --- PESTAÑA 1: TURNERO ---
with t_tur:
    st.subheader("Recepción de Vehículos")
    c_f, c_a, c_add = st.columns([1, 1, 2])
    with c_f:
        hoy = datetime.today().date()
        sel_f = st.date_input("📅 Rango", value=(hoy, hoy), format="DD/MM/YYYY")
        if isinstance(sel_f, tuple) and len(sel_f) == 2: f_i, f_f = sel_f
        elif isinstance(sel_f, tuple): f_i = f_f = sel_f[0]
        else: f_i = f_f = sel_f
    with c_a:
        f_ase = st.selectbox("👔 Filtrar Asesor", ["TODOS"] + ASESORES_LISTA)
    with c_add:
        with st.expander("➕ Walk-in"):
            with st.form("f_in", clear_on_submit=True):
                cp, cv, cc = st.columns(3)
                p_n, v_n, c_n = cp.text_input("Patente*"), cv.text_input("Vehículo*"), cc.selectbox("Cliente", CLIENTES_LISTA)
                if st.form_submit_button("Cargar"):
                    if p_n and v_n:
                        new = pd.DataFrame([{'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_i, 'Hora': '-', 'Vehiculo': v_n.upper(), 'Patente': p_n.upper(), 'Asesor': f_ase if f_ase != "TODOS" else "SIN ASIGNAR", 'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False}])
                        st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, new], ignore_index=True)
                        st.rerun()

    st.divider()
    m = (st.session_state.memoria_turnos_v11['Fecha'] >= f_i) & (st.session_state.memoria_turnos_v11['Fecha'] <= f_f)
    df_r = st.session_state.memoria_turnos_v11[m].copy()
    if f_ase != "TODOS": df_r = df_r[df_r['Asesor'] == f_ase]
    if not df_r.empty:
        df_r['OR'] = df_r['OR'].fillna("")
        df_act = df_r[df_r['Cancelado'] == False]
        m_rec = (df_act['OR'].str.strip() != "") & (df_act['Recibido'] == True) & (df_act['Fotos'] == True)
        df_p = df_act[~m_rec].sort_values(['Fecha', 'Hora'])
        st.write("### ⏱️ Pendientes")
        ed = st.data_editor(df_p[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']], hide_index=True, use_container_width=True, key="e_p")
        if st.button("💾 Guardar"):
            for idx, r in ed.iterrows(): st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR', 'Cancelado']] = r[['Recibido', 'Fotos', 'OR', 'Cancelado']]
            st.success("Guardado"); time.sleep(0.5); st.rerun()

# --- PESTAÑA 2: PROGRAMACIÓN ---
with t_pro:
    st.subheader("🛠️ Estado del Taller por Grupo")
    if not df.empty:
        c1, c2 = st.columns(2)
        def bloques(df_g, kp):
            est_map = {"⏳ EN PROCESO": "PROCESO", "⛔ DETENIDOS": "DETENIDO", "✅ TERMINADOS": "TERM PEND", "🚚 ENTREGADOS": "ENTREGADO"}
            for lab, match in est_map.items():
                d_e = df_g[df_g['Estado_Taller'].str.contains(match, na=False)].copy()
                if "DETENIDO" in match: st.error(f"**{lab}**")
                else: st.info(f"**{lab}**")
                if not d_e.empty:
                    d_e = d_e.sort_values(by='Fin')
                    d_e['Fecha Prom.'] = d_e['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
                    st.dataframe(d_e[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor']], hide_index=True, use_container_width=True, key=f"{kp}_{match}")
                else: st.caption("Sin datos.")
            st.divider()
        with c1: st.write("## 🧑‍🔧 GRUPO UNO"); bloques(df[df['Grupo'] == 'GRUPO UNO'], "G1")
        with c2: st.write("## 🧑‍🔧 GRUPO DOS"); bloques(df[df['Grupo'] == 'GRUPO DOS'], "G2")

# --- FACTURACIÓN Y KPI ---
with t_fac:
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Facturado", f"$ {df[df['Estado_Fac'] == 'FAC']['Precio'].sum():,.0f}")
        m2.metric("Confirmado", f"$ {df[df['Estado_Fac'] == 'SI']['Precio'].sum():,.0f}")
        m3.metric("Pendiente", f"$ {df[df['Estado_Fac'] == 'NO']['Precio'].sum():,.0f}")

with t_kpi:
    if not df.empty:
        st.subheader("KPIs")
        st.metric("Paños Promedio", f"{df['Paños'].mean():.2f}")

with st.sidebar:
    if st.button("🔄 Refrescar"):
        st.cache_data.clear()
        if 'memoria_turnos_v11' in st.session_state: del st.session_state['memoria_turnos_v11']
        st.rerun()
