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
    columnas_base = ['Tipo', 'Fecha', 'Hora', 'Vehiculo', 'Patente', 'Asesor', 'Precio', 'Paños', 'Observaciones', 'Tiempo_Entrega', 'Cliente', 'Seguro', 'Recibido', 'Fotos', 'Cancelado', 'OR']
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
                'OR': ""
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
        col_fecha = next((c for c in df_raw.columns if 'FECH' in c or 'PROMESA' in c), None)
        f_fin = parsear_fecha_español(row.get(col_fecha, ''))
        if f_fin is None:
            f_fin = datetime.now()
        
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

# --- BLINDAJE DE MEMORIA ---
# Versión 5: Forzamos la actualización para cargar las nuevas columnas
if 'memoria_turnos_v5' not in st.session_state:
    st.session_state.memoria_turnos_v5 = obtener_turnos()
    # Limpiar versiones viejas si existían
    for old_key in ['df_turnos_memoria', 'memoria_turnos_v4']:
        if old_key in st.session_state:
            del st.session_state[old_key]

# --- EJECUCIÓN ---
df = obtener_datos_maestros()

tab_turnos, tab_prog, tab_fac, tab_kpi = st.tabs(["📋 Turnero Diario", "📅 Programación", "💰 Facturación", "📊 KPIs"])

# ==========================================
# PESTAÑA 1: TURNERO DIARIO
# ==========================================
with tab_turnos:
    st.subheader("Recepción de Vehículos")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        hoy = datetime.today().date()
        fechas_seleccionadas = st.date_input(
            "📅 Rango de Fechas (DD/MM/YYYY)", 
            value=(hoy, hoy),
            format="DD/MM/YYYY"
        )
        
        if isinstance(fechas_seleccionadas, tuple):
            if len(fechas_seleccionadas) == 2:
                f_inicio, f_fin = fechas_seleccionadas
            else:
                f_inicio = f_fin = fechas_seleccionadas[0]
        else:
            f_inicio = f_fin = fechas_seleccionadas
    
    with col2:
