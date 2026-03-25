import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import re
import time
import json
import gspread

# --- CONEXIÓN A GOOGLE SHEETS (GSPREAD) ---
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(creds_dict)
    ID_PLANILLA = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
    planilla = gc.open_by_key(ID_PLANILLA)
    hoja = planilla.worksheet("TURNOS")
except Exception as e:
    st.error(f"Error de conexión a Google Sheets: {e}")
    hoja = None
    
# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Taller CENOA - Jujuy", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS CSS INYECTADOS ---
st.markdown("""<style>
    /* Achicar la barra lateral */
    [data-testid="stSidebar"] { min-width: 240px !important; max-width: 240px !important; }
    
    .metric-card { background-color: white; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; display: flex; flex-direction: column; justify-content: center; min-height: 110px; margin-bottom: 15px;}
    .metric-title { color: #666; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; }
    .metric-value-money { color: #00235d; font-size: 1.8rem; font-weight: bold; margin: 0; }
    .metric-value-number { color: #00235d; font-size: 1.5rem; font-weight: bold; margin: 0; }
    .metric-subtitle-red { color: #dc3545; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-green { color: #28a745; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-blue { color: #17a2b8; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-gray { color: #888; font-size: 0.8rem; margin-top: 5px; }
    .metric-subtitle-purple { color: #6f42c1; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .kanban-col { background-color: #f8f9fa; border-radius: 8px; padding: 10px; border: 1px solid #e9ecef; }
</style>""", unsafe_allow_html=True)

# --- ENCABEZADO ---
st.title("🚀 Sistema de Gestión Taller CENOA - Jujuy")

# --- CONFIGURACIÓN DE GIDS Y VARIABLES ---
ID_NUEVO_SHEET = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_NUEVO_SHEET}/export?format=csv&gid="
GID_TURNOS = "109364752" 

GIDS = {"GRUPO UNO": "609774337", "GRUPO DOS": "1212138688", "GRUPO TRES": "527300176", "TERCEROS": "431495457", "PARABRISAS": "37356499"}
MESES_ES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
ASESORES_LISTA = ["SIN ASIGNAR", "CESAR OLIVA", "JAVIER GUTIERREZ", "ANDREA MARTINS"]
CLIENTES_LISTA = ["CENOA", "CENOA SEGURO", "CIEL", "CIEL SEGURO", "CIEL OKM", "CIEL USADO", "AUTOSOL", "AUTOSOL SEGURO", "AUTOSOL OKM", "AUTOSOL USADO", "AUTOLUX", "AUTOLUX SEGURO", "AUTOLUX OKM", "AUTOLUX USADO", "PARTICULAR"]

OBJETIVO_MENSUAL_PANOS = 505.0

# --- HELPERS DE FORMATO ---
formato_pesos = lambda x: f"$ {x:,.0f}".replace(',', '.')
formato_panos = lambda x: f"{x:.1f}"

# --- LÓGICA DE DÍAS HÁBILES ---
anio_actual = datetime.now().year
FERIADOS_ARG = [
    date(anio_actual, 3, 24), # Día de la Memoria
    date(anio_actual, 4, 2),  # Día de Malvinas / Jueves Santo
    date(anio_actual, 4, 3)   # Viernes Santo
]

def dias_habiles_del_mes(anio, mes):
    _, ult_dia = calendar.monthrange(anio, mes)
    dias = 0
    for d in range(1, ult_dia + 1):
        fecha = date(anio, mes, d)
        if fecha.weekday() < 5 and fecha not in FERIADOS_ARG:
            dias += 1
    return max(1, dias)

def dias_habiles_restantes_mes(anio, mes):
    hoy_f = datetime.today().date()
    if anio == hoy_f.year and mes == hoy_f.month:
        dia_inicio = hoy_f.day
    elif date(anio, mes, 1) < hoy_f:
        return 0
    else:
        dia_inicio = 1
        
    _, ult_dia = calendar.monthrange(anio, mes)
    dias_restantes = 0
    for d in range(dia_inicio, ult_dia + 1):
        fecha = date(anio, mes, d)
        if fecha.weekday() < 5 and fecha not in FERIADOS_ARG:
            dias_restantes += 1
    return dias_restantes

# --- FUNCIONES ---
def parsear_fecha_español(texto):
    if pd.isna(texto) or str(texto).strip() == "": return None 
    texto = str(texto).lower().strip()
    match_dm = re.match(r'^(\d{1,2})[-/](\d{1,2})$', texto)
    if match_dm: return datetime(datetime.now().year, int(match_dm.groups()[1]), int(match_dm.groups()[0]))
    try:
        res = pd.to_datetime(texto, dayfirst=True)
        if pd.notna(res): return res.to_pydatetime()
    except: pass
    try:
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match: return datetime(int(match.groups()[2]), MESES_ES.get(match.groups()[1], 1), int(match.groups()[0]))
    except: pass
    return None

def clasificar_abc(panos):
    if panos <= 3: return 'A (1-3 paños)'
    elif panos <= 7: return 'B (4-7 paños)'
    else: return 'C (8+ paños)'

def obtener_proxima_fecha_libre(dias_carga):
    fecha = datetime.today()
    dias_agregados = 0
    while dias_agregados < int(dias_carga):
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha.date() not in FERIADOS_ARG:
            dias_agregados += 1
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.strftime('%d/%m')}"

@st.cache_data(ttl=300)
def obtener_turnos():
    columnas_base = ['Tipo', 'Fecha', 'Hora', 'Vehiculo', 'Patente', 'Chasis', 'Asesor', 'Precio', 'Paños', 'Observaciones', 'Tiempo_Entrega', 'Cliente', 'Seguro', 'Recibido', 'Fotos', 'Cancelado', 'OR', 'Eliminar']
    if GID_TURNOS == "PONER_AQUI_GID_TURNOS": return pd.DataFrame(columns=columnas_base)
    try:
        d = pd.read_csv(f"{URL_BASE}{GID_TURNOS}", dtype=str)
        d.columns = d.columns.str.strip().str.upper()
        if 'PATENTE' in d.columns: d = d.dropna(subset=['PATENTE']); d = d[d['PATENTE'].str.strip() != ""]
        filas = []
        col_chasis = next((c for c in d.columns if 'CHASIS' in c or 'VIN' in c), None)
        
        col_recibido = next((c for c in d.columns if 'RECIBID' in c), None)
        col_fotos = next((c for c in d.columns if 'FOTO' in c), None)
        col_or = next((c for c in d.columns if 'OR' == c or 'REFERENCIA' in c), None)
        
        for _, row in d.iterrows():
            col_fecha = next((c for c in d.columns if 'FECH' in c), None)
            fecha_turno = parsear_fecha_español(row.get(col_fecha, '')) or datetime.now()
            asesor_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if asesor_raw not in ASESORES_LISTA: asesor_raw = "SIN ASIGNAR"
            col_tiempo = next((c for c in d.columns if 'TIEMPO' in c), None)
            
            val_recibido = str(row.get(col_recibido, '')).strip().upper() if col_recibido else ""
            bool_recibido = val_recibido in ['SI', 'SÍ', 'TRUE', '1']
            
            val_fotos = str(row.get(col_fotos, '')).strip().upper() if col_fotos else ""
            bool_fotos = val_fotos in ['SI', 'SÍ', 'TRUE', '1']
            
            val_or = str(row.get(col_or, '')).strip() if col_or else ""
            
            filas.append({
                'Tipo': '📅 PROGRAMADO', 'Fecha': fecha_turno.date(), 'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(), 'Patente': str(row.get('PATENTE', '')).upper(),
                'Chasis': str(row.get(col_chasis, '')).strip().upper() if col_chasis else "",
                'Asesor': asesor_raw, 'Precio': str(row.get('PRECIO', '')).strip(), 'Paños': str(row.get('PAÑOS', '')).strip(),
                'Observaciones': str(row.get('OBSERVACIONES', '')).strip(), 'Tiempo_Entrega': str(row.get(col_tiempo, '')) if col_tiempo else "",
                'Cliente': str(row.get('CLIENTE', '')).upper(), 'Seguro': str(row.get('SEGURO', '')).upper(),
                'Recibido': bool_recibido, 'Fotos': bool_fotos, 'Cancelado': False, 'OR': val_or, 'Eliminar': False
            })
        return pd.DataFrame(filas)
    except: return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=300)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            d_raw = pd.read_csv(f"{URL_BASE}{gid}", dtype=str, header=None)
            
            idx_header = 0
            for i in range(min(15, len(d_raw))):
                fila_str = " ".join(d_raw.iloc[i].fillna("").astype(str).str.upper())
                if 'ESTADO' in fila_str or 'DOMINIO' in fila_str or 'PATENTE' in fila_str or 'CLIENTE' in fila_str or 'COMPAÑIA' in fila_str or 'PRECIO' in fila_str or 'MANO DE OBRA' in fila_str:
                    idx_header = i
                    break
                    
            cols = []
            for j, val in enumerate(d_raw.iloc[idx_header]):
                val_str = str(val).strip().upper()
                if val_str == 'NAN' or val_str == 'NONE' or not val_str:
                    cols.append(f"VACIA_{j}")
                else:
                    cols.append(val_str)
                    
            d_raw.columns = cols
            d = d_raw.iloc[idx_header + 1:].reset_index(drop=True)

            if n in ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES"]:
                cols = list(d.columns)
                while len(cols) < 22: cols.append(f"VACIA_EXTRA_{len(cols)}")
                if len(cols) > 21: cols[21] = 'ESTADO_FAC'            
                if len(cols) > 20: cols[20] = 'FASE_TALLER'            
                if len(cols) > 19: cols[19] = 'ESTADO_TALLER'         
                if len(cols) > 15: cols[15] = 'EMPRESA_TALLER'        
                if len(cols) > 11: cols[11] = 'OBSERVACIONES_TALLER'  
                if len(cols) > 9: cols[9] = 'HORA_ENTREGA'            
                if len(cols) > 8: cols[8] = 'FECHA_PROMESA_I'         
                if len(cols) > 7: cols[7] = 'FECHA_TICKET'            
                if len(cols) > 6: cols[6] = 'DIAS_TRABAJO'            
                if len(cols) > 0: cols[0] = 'FECHA_INGRESO_TALLER'    
                d.columns = cols
            else: 
                renames = {}
                for c in d.columns:
                    c_str = str(c).upper().strip()
                    if 'ESTADO FAC' in c_str or 'ESTADOFAC' in c_str or c_str == 'FAC': 
                        renames[c] = 'ESTADO_FAC'
                    elif 'ESTADO TALLER' in c_str or 'ESTADOTALLER' in c_str or c_str == 'ESTADO': 
                        renames[c] = 'ESTADO_TALLER'
                    elif 'FASE' in c_str: 
                        renames[c] = 'FASE_TALLER'
                    elif 'COMPAÑIA' in c_str or 'SEGURO' in c_str or 'EMPRESA' in c_str or 'CLIENTE' in c_str: 
                        if 'EMPRESA_TALLER' not in renames.values(): renames[c] = 'EMPRESA_TALLER'
                    elif 'OBSERVACION' in c_str: 
                        renames[c] = 'OBSERVACIONES_TALLER'
                    elif 'PROMESA' in c_str or 'FECH/PROM' in c_str: 
                        renames[c] = 'FECHA_PROMESA_I'
                    elif 'TICKET' in c_str: 
                        renames[c] = 'FECHA_TICKET'
                    elif 'INGRESO' in c_str or c_str == 'FECHA': 
                        renames[c] = 'FECHA_INGRESO_TALLER'
                    elif 'HORA' in c_str: 
                        renames[c] = 'HORA_ENTREGA'
                    elif 'DOMINIO' in c_str or 'PATENTE' in c_str: 
                        renames[c] = 'PATENTE'
                    elif 'PRECIO' in c_str or 'MONTO' in c_str or 'TOTAL' in c_str or 'FRANQUICIA' in c_str or 'MANO DE OBRA' in c_str: 
                        if 'PRECIO' not in renames.values(): renames[c] = 'PRECIO' 
                    elif 'COSTO' in c_str or 'REPUESTO' in c_str: 
                        if 'COSTO' not in renames.values(): renames[c] = 'COSTO'
                    elif 'TERCERO' in c_str or 'ASESOR' in c_str: 
                        if 'ASESOR' not in renames.values(): renames[c] = 'ASESOR'
                    elif c_str == 'MES': 
                        renames[c] = 'MES'
                    elif 'MARCA' in c_str or 'VEHIC' in c_str: 
                        renames[c] = 'VEHICULO'
                    elif 'PAÑO' in c_str:
                        if 'PAÑOS' not in renames.values(): renames[c] = 'PAÑOS'

                d = d.rename(columns=renames)
                
                if 'MES' in d.columns:
                    d['MES'] = d['MES'].replace(r'^\s*$', pd.NA, regex=True).ffill()

            d = d.loc[:, ~d.columns.duplicated()]

            if 'PATENTE' in d.columns: 
                d = d.dropna(subset=['PATENTE'])
                d = d[d['PATENTE'].str.strip() != ""]
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except Exception as e: 
            print(f"Error en pestaña {n}: {e}")
            pass
        
    if not dfs: return pd.DataFrame()
    df_raw = pd.concat(dfs, ignore_index=True)
    filas = []
    
    col_chasis_global = next((c for c in df_raw.columns if 'CHASIS' in c or 'VIN' in c), None)
    
    for _, row in df_raw.iterrows():
        f_fin = parsear_fecha_español(row.get('FECHA_PROMESA_I', ''))
        f_fin_disp = f_fin.date() if f_fin else None
        if not f_fin: f_fin = datetime.now() + timedelta(days=3650) 
        
        mes_hist = f_fin.strftime('%Y-%m') if f_fin.year < 2030 else "SIN FECHA"
        if row.get('GRUPO_ORIGEN') in ['PARABRISAS', 'TERCEROS']:
            mes_str = str(row.get('MES', '')).strip().lower()
            for m_name, m_num in MESES_ES.items():
                if m_name in mes_str:
                    mes_hist = f"{datetime.now().year}-{m_num:02d}"
                    break

        f_ingreso = parsear_fecha_español(row.get('FECHA_INGRESO_TALLER', ''))
        f_ticket = parsear_fecha_español(row.get('FECHA_TICKET', ''))
        
        try:
            t_panos = str(row.get('PAÑOS', '0')).replace(',', '.')
            if t_panos.lower() == 'nan' or not t_panos.strip(): t_panos = '0'
            panos = float(re.findall(r"[-+]?\d*\.\d+|\d+", t_panos)[0]) if re.findall(r"[-+]?\d*\.\d+|\d+", t_panos) else 0.0
        except: panos = 0.0
        
        try:
            t_dias = str(row.get('DIAS_TRABAJO', '0')).replace(',', '.')
            if t_dias.lower() == 'nan' or not t_dias.strip() or 'VACIA' in t_dias: t_dias = '0'
            dias_rep = float(re.findall(r"[-+]?\d*\.\d+|\d+", t_dias)[0]) if re.findall(r"[-+]?\d*\.\d+|\d+", t_dias) else 0.0
        except: dias_rep = 0.0

        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: precio_val = float(precio_raw) if precio_raw else 0.0
        except: precio_val = 0.0

        costo_raw = str(row.get('COSTO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: costo_val = float(costo_raw) if costo_raw else 0.0
        except: costo_val = 0.0
        
        estado_fac_raw = str(row.get('ESTADO_FAC', '')).replace('.', '').strip().upper()
        
        estado = str(row.get('ESTADO_TALLER', '')).replace('nan', '').strip().upper() or "SIN ESTADO"
        cliente = str(row.get('EMPRESA_TALLER', 'PARTICULAR')).replace('nan', '').strip().upper() or "PARTICULAR"
        asesor = str(row.get('ASESOR', '')).strip().upper()
        if asesor == 'NAN' or not asesor: asesor = "SIN ASIGNAR"
        fase = str(row.get('FASE_TALLER', '')).replace('nan', '').strip().upper()
        if not fase or fase == 'VACIA_20': fase = "SIN FASE ASIGNADA"
        hora_entrega = str(row.get('HORA_ENTREGA', '')).replace('nan', '').strip()
        chasis_val = str(row.get(col_chasis_global, '')).strip().upper() if col_chasis_global else ""

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'), 'Asesor': asesor, 'Cliente': cliente,
            'Patente': str(row.get('PATENTE', '')), 'Vehiculo': str(row.get('VEHICULO', '')), 'Chasis': chasis_val,
            'Inicio': f_fin - timedelta(days=max(1, int(panos))), 'Fin': f_fin, 'Fecha_Promesa_Disp': f_fin_disp, 
            'Fecha_Ingreso': f_ingreso.date() if f_ingreso else None, 'Fecha_Ticket': f_ticket.date() if f_ticket else None,
            'Hora_Entrega': hora_entrega,
            'Mes_Hist': mes_hist, 'Paños': panos, 'Dias_Reparacion': dias_rep, 'Tipo_ABC': clasificar_abc(panos),
            'Estado_Fac': estado_fac_raw, 
            'Estado_Taller': estado, 'Fase_Taller': fase, 
            'Precio': precio_val, 'Costo': costo_val,
            'Observaciones': str(row.get('OBSERVACIONES_TALLER', '')).replace('nan', '').strip()
        })
    return pd.DataFrame(filas)

# --- MEMORIA Y CARGA DE DATOS ---
if 'memoria_turnos_v11' not in st.session_state: 
    st.session_state.memoria_turnos_v11 = obtener_turnos()

if 'entregas_confirmadas' not in st.session_state:
    st.session_state.entregas_confirmadas = []

df = obtener_datos_maestros()
df_turnos_display = st.session_state.memoria_turnos_v11.copy()
df_completo = df.copy() 

hoy = datetime.today()
hoy_ym = hoy.strftime('%Y-%m')

# --- BARRA LATERAL (SIDEBAR) Y BUSCADOR ---
with st.sidebar:
    st.markdown("### 🔍 Buscador Rápido")
    busqueda_global = st.text_input("Dominio o Chasis", placeholder="Ej: AB123CD")
    st.caption("Filtra tablas y muestra un resumen.")
    
    contenedor_resultados_busqueda = st.container()
    
    st.divider()

    st.markdown("### 📅 Filtro Mensual")
    
    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    m1 = df[df['Mes_Hist'] != 'SIN FECHA']['Mes_Hist'].dropna().unique().tolist()
    m2 = df_turnos_display['Fecha'].dropna().apply(lambda x: x.strftime('%Y-%m') if pd.notna(x) else None).dropna().unique().tolist()
    todos_meses_disp = sorted(list(set(m1 + m2)), reverse=True)
    
    opciones_meses = ["🗓️ MES ACTUAL", "♾️ TODOS"]
    mapa_meses = {}
    for m in todos_meses_disp:
        try:
            y, mo = m.split('-')
            nombre = f"{meses_nombres[int(mo)-1]} {y}"
            opciones_meses.append(nombre)
            mapa_meses[nombre] = m
        except: pass
        
    mes_seleccionado_label = st.selectbox("Período de Análisis", opciones_meses)
    
    if mes_seleccionado_label == "🗓️ MES ACTUAL":
        mes_filtro = hoy_ym
    elif mes_seleccionado_label == "♾️ TODOS":
        mes_filtro = "TODOS"
    else:
        mes_filtro = mapa_meses.get(mes_seleccionado_label, "TODOS")
        
    st.caption("Aplica a Turnos, Taller y Facturación. El Histórico se mantiene global.")
    
    st.divider()
    st.markdown("### ⚙️ Sistema")
    if st.button("🔄 Forzar Actualización", use_container_width=True):
        st.cache_data.clear()
        # Le decimos que también mate la memoria temporal de los turnos
        if 'memoria_turnos_v11' in st.session_state:
            del st.session_state['memoria_turnos_v11']
        st.success("¡Datos actualizados y memoria limpia!"); time.sleep(0.5); st.rerun()
    st.caption("Datos extraídos de Google Sheets.")

# --- APLICAR FILTRO MENSUSAL GLOBAL A MAESTRO ---
if mes_filtro != "TODOS":
    df = df[(df['Mes_Hist'] == mes_filtro) | (df['Mes_Hist'] == 'SIN FECHA')]
    año_filtro, mes_num_filtro = map(int, mes_filtro.split('-'))
    DIAS_HABILES_MES = dias_habiles_del_mes(año_filtro, mes_num_filtro)
else:
    año_filtro, mes_num_filtro = hoy.year, hoy.month
    DIAS_HABILES_MES = dias_habiles_del_mes(año_filtro, mes_num_filtro)

CAPACIDAD_DIARIA_TALLER = OBJETIVO_MENSUAL_PANOS / DIAS_HABILES_MES
CAPACIDAD_DIARIA_GRUPO = CAPACIDAD_DIARIA_TALLER / 2
dias_restantes_calc = dias_habiles_restantes_mes(año_filtro, mes_num_filtro)

# --- APLICAR BUSCADOR GLOBAL ---
if busqueda_global:
    termino = busqueda_global.upper().strip()
    
    if not df.empty:
        if 'Chasis' not in df.columns: df['Chasis'] = ""
        df = df[(df['Patente'].str.contains(termino, na=False)) | 
                (df['Chasis'].str.contains(termino, na=False))]
                
    if not df_turnos_display.empty:
        if 'Chasis' not in df_turnos_display.columns: df_turnos_display['Chasis'] = ""
        df_turnos_display = df_turnos_display[(df_turnos_display['Patente'].str.contains(termino, na=False)) | 
                                              (df_turnos_display['Chasis'].str.contains(termino, na=False))]
    
    with contenedor_resultados_busqueda:
        st.markdown("### 📋 Resumen del Vehículo")
        if not df.empty:
            for _, row in df.head(5).iterrows():
                f_prom = row.get('Fecha_Promesa_Disp')
                fecha_str = f_prom.strftime('%d/%m/%Y') if pd.notna(f_prom) else "Sin Fecha"
                estado_taller = str(row.get('Estado_Taller', ''))
                
                if "ENTREGADO" in estado_taller: color_borde = "#28a745"
                elif "PROCESO" in estado_taller: color_borde = "#ffc107"
                elif "DETENIDO" in estado_taller: color_borde = "#dc3545"
                elif "TERM" in estado_taller: color_borde = "#17a2b8"
                else: color_borde = "#6c757d"
                
                st.markdown(f"""
                <div style='background-color: white; border: 1px solid #dee2e6; padding: 10px; border-radius: 8px; border-left: 6px solid {color_borde}; margin-bottom: 10px; font-size: 0.85em; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                    <div style='font-size: 1.1em; font-weight: bold; color: #00235d; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 3px;'>🚗 {row['Patente']} - {str(row['Vehiculo'])[:12]}</div>
                    <strong>🏷️ Estado:</strong> {estado_taller}<br>
                    <strong>🏭 Grupo:</strong> {row['Grupo']}<br>
                    <strong>👔 Asesor:</strong> {row['Asesor']}<br>
                    <strong>📅 Entrega:</strong> <span style='color: #d32f2f; font-weight: bold;'>{fecha_str}</span>
                </div>
                """, unsafe_allow_html=True)
                
        elif not df_turnos_display.empty:
            for _, row in df_turnos_display.head(3).iterrows():
                fecha_turno = row['Fecha'].strftime('%d/%m/%Y') if pd.notna(row['Fecha']) else "Sin Fecha"
                st.markdown(f"""
                <div style='background-color: white; border: 1px solid #dee2e6; padding: 10px; border-radius: 8px; border-left: 6px solid #6f42c1; margin-bottom: 10px; font-size: 0.85em; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                    <div style='font-size: 1.1em; font-weight: bold; color: #00235d; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 3px;'>📝 TURNO: {row['Patente']}</div>
                    <strong>🏷️ Tipo:</strong> {row['Tipo']}<br>
                    <strong>📅 Día Asignado:</strong> {fecha_turno}<br>
                    <strong>👔 Asesor:</strong> {row['Asesor']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No se encontró el vehículo.")

# --- CÁLCULO GLOBAL DE CAPACIDAD ---
recomendaciones_grupos = {}
if not df.empty:
    df_en_proceso_global = df[df['Estado_Taller'].str.contains("PROCESO", na=False)]
    if not df_en_proceso_global.empty:
        resumen = df_en_proceso_global.groupby('Grupo')['Paños'].sum().reset_index()
        for _, row in resumen.iterrows():
            dias_reales = row['Paños'] / CAPACIDAD_DIARIA_GRUPO
            fecha_recomendada = obtener_proxima_fecha_libre(dias_reales)
            recomendaciones_grupos[row['Grupo']] = fecha_recomendada

tab_turnos, tab_prog, tab_portal, tab_fac, tab_kpi, tab_hist = st.tabs([
    "📋 Turnero y Entregas", "🛠️ Kanban de Taller", "🏢 Seguimiento Empresas", "💰 Facturación", "📊 KPIs", "📅 Históricos"
])

# ==========================================
# PESTAÑA 1: TURNERO Y ENTREGAS
# ==========================================
with tab_turnos:
    if recomendaciones_grupos and not busqueda_global:
        st.info("**📅 Asistente de Turnos (Disponibilidad Estimada por Grupo):**\n" + 
                " | ".join([f"**{g}**: libre desde el {f}" for g, f in recomendaciones_grupos.items()]))
    
    st.markdown("<h4 style='color: #00235d; margin-top: 10px;'>🔍 Filtros de Visualización (Aplican a Ingresos y Salidas)</h4>", unsafe_allow_html=True)
    col_fecha, col_asesor, col_add = st.columns([1, 1, 2])
    
    with col_fecha:
        if mes_filtro != "TODOS":
            primer_dia = date(año_filtro, mes_num_filtro, 1)
            _, ult_dia_int = calendar.monthrange(año_filtro, mes_num_filtro)
            ultimo_dia = date(año_filtro, mes_num_filtro, ult_dia_int)
            
            if mes_seleccionado_label == "🗓️ MES ACTUAL":
                rango_default = (hoy.date(), hoy.date()) 
            else:
                rango_default = (primer_dia, ultimo_dia) 
        else:
            rango_default = (hoy.date(), hoy.date())
            
        fechas_seleccionadas = st.date_input("📅 Rango de Fechas", value=rango_default, format="DD/MM/YYYY")
        if isinstance(fechas_seleccionadas, tuple):
            f_inicio = f_fin = fechas_seleccionadas[0] if len(fechas_seleccionadas) < 2 else fechas_seleccionadas[0]
            if len(fechas_seleccionadas) == 2: f_fin = fechas_seleccionadas[1]
        else: f_inicio = f_fin = fechas_seleccionadas
        
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
                nuevo_asesor = c_ase.selectbox("Asesor", ASESORES_LISTA, index=ASESORES_LISTA.index(asesor_filtro) if asesor_filtro in ASESORES_LISTA else 0)
                
                st.write("---")
                st.write("📋 Checklist de Recepción:")
                c_chk1, c_chk2, c_ref = st.columns(3)
                val_recibido_bool = c_chk1.checkbox("✅ ¿Vehículo Recibido?")
                val_foto_bool = c_chk2.checkbox("📸 ¿Fotos tomadas?")
                nueva_referencia = c_ref.text_input("Número de Referencia (OR)")

                st.caption("* Campos obligatorios para identificar el auto.")
                
                if st.form_submit_button("Agregar al Turnero y Guardar en Sheets"):
                    if nueva_patente and nuevo_vehiculo:
                        if hoja is not None:
                            try:
                                val_recibido = "Si" if val_recibido_bool else ""
                                val_foto = "SI" if val_foto_bool else ""
                                fecha_str = f_inicio.strftime('%d/%m/%Y')
                                
                               # --- INICIO DEL CÓDIGO CORREGIDO ---
                                nueva_fila = [
                                    "NO",                                                 # A: TIPO
                                    str(fecha_str),                                       # B: FECHA
                                    "-",                                                  # C: HORAS
                                    str(nuevo_vehiculo).upper(),                          # D: VEHICULO
                                    str(nueva_patente).upper(),                           # E: PATENTE
                                    str(nuevo_asesor) if nuevo_asesor else "SIN ASIGNAR", # F: ASESOR
                                    str(nuevo_precio) if nuevo_precio else "",            # G: PRECIO
                                    str(nuevo_panos) if nuevo_panos else "",              # H: PAÑOS
                                    str(nueva_obs) if nueva_obs else "",                  # I: OBSERVACIONES
                                    str(nuevo_tiempo) if nuevo_tiempo else "",            # J: TIEMPO DE ENTR.
                                    str(nuevo_cliente) if nuevo_cliente else "PARTICULAR",# K: CLIENTE
                                    str(nuevo_seguro).upper() if nuevo_seguro else "",    # L: SEGURO
                                    val_recibido,                                         # M: RECIBIDO
                                    val_foto,                                             # N: FOTOS
                                    str(nueva_referencia) if nueva_referencia else ""     # O: REFERENCIA (OR)
                                ]
                                # --- FIN DEL CÓDIGO CORREGIDO ---
                                
                                hoja.append_row(nueva_fila)
                                
                                nuevo_ingreso = pd.DataFrame([{
                                    'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_inicio, 'Hora': '-', 'Vehiculo': nuevo_vehiculo.upper(), 
                                    'Patente': nueva_patente.upper(), 'Chasis': '', 'Asesor': nuevo_asesor, 'Precio': nuevo_precio, 
                                    'Paños': nuevo_panos, 'Observaciones': nueva_obs, 'Tiempo_Entrega': nuevo_tiempo, 
                                    'Cliente': nuevo_cliente, 'Seguro': nuevo_seguro.upper(), 'Recibido': val_recibido_bool, 
                                    'Fotos': val_foto_bool, 'Cancelado': False, 'OR': nueva_referencia, 'Eliminar': False
                                }])
                                st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, nuevo_ingreso], ignore_index=True)
                                
                                st.success(f"¡Vehículo {nueva_patente.upper()} agregado correctamente a la planilla de Google!")
                                time.sleep(1.5)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error al guardar en Google Sheets: {e}")
                        else:
                            st.error("Error: No hay conexión con Google Sheets. Revisá las credenciales.")
                    else: 
                        st.error("Por favor completa la Patente y el Vehículo.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("<h2 style='color: #00235d; margin-top: 0;'>📥 1. INGRESOS: Recepción de Vehículos</h2>", unsafe_allow_html=True)
        st.write("Administración de turnos y vehículos programados para **entrar** al taller en las fechas seleccionadas.")
        
        mask = (df_turnos_display['Fecha'] >= f_inicio) & (df_turnos_display['Fecha'] <= f_fin)
        df_rango = df_turnos_display[mask].copy()
        if asesor_filtro != "TODOS": df_rango = df_rango[df_rango['Asesor'] == asesor_filtro]

        if df_rango.empty: 
            st.info("No hay turnos para los filtros seleccionados o la búsqueda actual.")
        else:
            df_rango['OR'] = df_rango['OR'].fillna("")
            df_cancelados = df_rango[df_rango['Cancelado'] == True]
            df_activos = df_rango[df_rango['Cancelado'] == False]
            mascara_recibidos = (df_activos['OR'].str.strip() != "") & (df_activos['Recibido'] == True) & (df_activos['Fotos'] == True)
            
            df_pendientes = df_activos[~mascara_recibidos].sort_values(['Fecha', 'Hora', 'Asesor'])
            df_recibidos = df_activos[mascara_recibidos].sort_values(['Fecha', 'Hora', 'Asesor'])

            st.write("#### ⏱️ Turnos Pendientes de Recepción")
            if not df_pendientes.empty:
                df_prog = df_pendientes[df_pendientes['Tipo'] == '📅 PROGRAMADO']
                df_sin = df_pendientes[df_pendientes['Tipo'] == '🚶‍♂️ SIN TURNO']
                edited_prog, edited_sin = pd.DataFrame(), pd.DataFrame()
                
                if not df_prog.empty:
                    st.caption("📅 Programados")
                    edited_prog = st.data_editor(df_prog[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']], column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"), "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA), "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False), "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10), "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False)}, hide_index=True, use_container_width=True, key="editor_prog")
                if not df_sin.empty:
                    st.caption("🚶‍♂️ Ingresos Adicionales (Sin Turno)")
                    edited_sin = st.data_editor(df_sin[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado', 'Eliminar']], column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"), "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA), "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False), "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10), "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False), "Eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False)}, hide_index=True, use_container_width=True, key="editor_sin")

            if st.button("💾 Guardar Ingresos"):
                    with st.spinner("Conectando con Google Sheets y sincronizando..."):
                        patentes_sheet = hoja.col_values(5) if hoja else []
                        indices_a_borrar = []
                        filas_a_borrar_sheet = [] # Guardamos los números de fila a borrar físicamente
                        
                        if not edited_prog.empty:
                            for idx, row in edited_prog.iterrows():
                                row_orig = df_prog.loc[idx]
                                if (row['Recibido'] != row_orig['Recibido'] or row['Fotos'] != row_orig['Fotos'] or str(row['OR']) != str(row_orig['OR']) or row['Asesor'] != row_orig['Asesor'] or row['Cancelado'] != row_orig['Cancelado']):
                                    st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                                    
                                    if hoja and row['Patente'].upper() in patentes_sheet:
                                        fila_sheet = patentes_sheet.index(row['Patente'].upper()) + 1
                                        try:
                                            # Columnas corregidas a M, N, O y F
                                            hoja.update_acell(f'M{fila_sheet}', "Si" if row['Recibido'] else "")
                                            hoja.update_acell(f'N{fila_sheet}', "SI" if row['Fotos'] else "")
                                            hoja.update_acell(f'O{fila_sheet}', row['OR'] if pd.notna(row['OR']) else "")
                                            hoja.update_acell(f'F{fila_sheet}', row['Asesor'])
                                        except Exception as e: st.error(f"Error guardando {row['Patente']}: {e}")
                                        
                        if not edited_sin.empty:
                            for idx, row in edited_sin.iterrows():
                                if row.get('Eliminar', False): 
                                    indices_a_borrar.append(idx)
                                    # Si lo marcamos con la papelera, buscamos en qué fila del Sheet está
                                    if hoja and row['Patente'].upper() in patentes_sheet:
                                        fila_sheet = patentes_sheet.index(row['Patente'].upper()) + 1
                                        filas_a_borrar_sheet.append(fila_sheet)
                                else:
                                    row_orig = df_sin.loc[idx]
                                    if (row['Recibido'] != row_orig['Recibido'] or row['Fotos'] != row_orig['Fotos'] or str(row['OR']) != str(row_orig['OR']) or row['Asesor'] != row_orig['Asesor'] or row['Cancelado'] != row_orig['Cancelado']):
                                        st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                                        if hoja and row['Patente'].upper() in patentes_sheet:
                                            fila_sheet = patentes_sheet.index(row['Patente'].upper()) + 1
                                            try:
                                                hoja.update_acell(f'M{fila_sheet}', "Si" if row['Recibido'] else "")
                                                hoja.update_acell(f'N{fila_sheet}', "SI" if row['Fotos'] else "")
                                                hoja.update_acell(f'O{fila_sheet}', row['OR'] if pd.notna(row['OR']) else "")
                                                hoja.update_acell(f'F{fila_sheet}', row['Asesor'])
                                            except: pass
                        
                        # --- MAGIA NUEVA: Borrar físicamente del Google Sheets ---
                        if hoja and filas_a_borrar_sheet:
                            # Ordenamos de mayor a menor para borrar de abajo hacia arriba
                            filas_a_borrar_sheet.sort(reverse=True)
                            for f in filas_a_borrar_sheet:
                                try:
                                    hoja.delete_rows(f)
                                except Exception as e:
                                    pass
                                            
                        if indices_a_borrar: 
                            st.session_state.memoria_turnos_v11.drop(indices_a_borrar, inplace=True)
                            
                        st.success("¡Cambios y eliminaciones guardados correctamente en Google Sheets!"); time.sleep(1.5); st.rerun() 

            st.write("#### 🏁 Turnos Completados (Ya tienen OR)")
            if not df_recibidos.empty:
                edited_recibidos = st.data_editor(df_recibidos[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Asesor', 'Recibido', 'Fotos', 'OR']], column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", disabled=True), "Recibido": st.column_config.CheckboxColumn("✅ Recibido"), "Fotos": st.column_config.CheckboxColumn("📸 Fotos"), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10)}, hide_index=True, use_container_width=True, key="editor_recibidos")
                
                if st.button("💾 Guardar Correcciones (Completados)"):
                    with st.spinner("Actualizando planilla en la nube..."):
                        patentes_sheet = hoja.col_values(5) if hoja else []
                        for idx, row in edited_recibidos.iterrows():
                            row_orig = df_recibidos.loc[idx]
                            if (row['Recibido'] != row_orig['Recibido'] or row['Fotos'] != row_orig['Fotos'] or str(row['OR']) != str(row_orig['OR'])):
                                st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR']] = row[['Recibido', 'Fotos', 'OR']]
                                if hoja and row['Patente'].upper() in patentes_sheet:
                                    fila_sheet = patentes_sheet.index(row['Patente'].upper()) + 1
                                    try:
                                        hoja.update_acell(f'N{fila_sheet}', "Si" if row['Recibido'] else "")
                                        hoja.update_acell(f'O{fila_sheet}', "SI" if row['Fotos'] else "")
                                        hoja.update_acell(f'P{fila_sheet}', row['OR'] if pd.notna(row['OR']) else "")
                                    except: pass
                        st.success("Correcciones aplicadas y guardadas."); time.sleep(1.5); st.rerun()

    with st.container(border=True):
        st.markdown("<h2 style='color: #1e7e34; margin-top: 0;'>📤 2. SALIDAS: Agenda de Entregas</h2>", unsafe_allow_html=True)
        st.write("Vehículos listos para entregar al cliente en las fechas seleccionadas.")
        
        if not df.empty:
            df_no_entregados = df[~df['Estado_Taller'].str.contains("ENTREGADO", na=False)].copy()
            df_no_entregados = df_no_entregados[~df_no_entregados['Patente'].isin(st.session_state.entregas_confirmadas)]
            df_no_entregados['Entregado_OK'] = False
            
            entregas_rango = df_no_entregados[(df_no_entregados['Fecha_Promesa_Disp'] >= f_inicio) & (df_no_entregados['Fecha_Promesa_Disp'] <= f_fin)].copy()
            entregas_atrasadas = df_no_entregados[(df_no_entregados['Fecha_Promesa_Disp'].notna()) & (df_no_entregados['Fecha_Promesa_Disp'] < hoy.date())].copy()
            
            if asesor_filtro != "TODOS":
                entregas_rango = entregas_rango[entregas_rango['Asesor'] == asesor_filtro]
                entregas_atrasadas = entregas_atrasadas[entregas_atrasadas['Asesor'] == asesor_filtro]
            
            edit_rango_df = pd.DataFrame() 
            edit_atra = pd.DataFrame()
            
            st.markdown("#### 🔴 Entregas Atrasadas (Vencidas)")
            if not entregas_atrasadas.empty:
                entregas_atrasadas = entregas_atrasadas.sort_values(by='Fecha_Promesa_Disp', ascending=True)
                entregas_atrasadas['Fecha Prom.'] = entregas_atrasadas['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y'))
                # Calculamos los días de demora exactos
                entregas_atrasadas['Demora (Días)'] = entregas_atrasadas['Fecha_Promesa_Disp'].apply(lambda x: (hoy.date() - x).days if pd.notna(x) else 0)
                
                edit_atra = st.data_editor(
                    entregas_atrasadas[['Entregado_OK', 'Demora (Días)', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor', 'Estado_Taller', 'Grupo', 'Precio', 'Observaciones']], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Entregado_OK": st.column_config.CheckboxColumn("✅ Listo", default=False),
                        "Demora (Días)": st.column_config.NumberColumn("⚠️ Demora", format="%d días"),
                        "Fecha Prom.": st.column_config.TextColumn("📅 Venció", disabled=True),
                        "Patente": st.column_config.TextColumn("Patente", disabled=True), 
                        "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True), 
                        "Asesor": st.column_config.TextColumn("Asesor", disabled=True), 
                        "Estado_Taller": st.column_config.TextColumn("Estado", disabled=True),
                        "Grupo": st.column_config.TextColumn("Grupo", disabled=True),
                        "Precio": st.column_config.NumberColumn("Monto ($)", format="$ %d", disabled=True),
                        "Observaciones": st.column_config.TextColumn("Observaciones", disabled=True)
                    },
                    key="editor_entregas_atra"
                )
            else:
                st.success("¡Excelente! No hay vehículos con la fecha de entrega atrasada.")
                
            st.divider()
            
            if f_inicio == f_fin:
                titulo_rango = f"HOY ({f_inicio.strftime('%d/%m')})" if f_inicio == hoy.date() else f"para el {f_inicio.strftime('%d/%m')}"
            else:
                titulo_rango = f"del {f_inicio.strftime('%d/%m')} al {f_fin.strftime('%d/%m')}"
                
            st.markdown(f"#### 🟢 Entregas Programadas {titulo_rango}")
            if not entregas_rango.empty:
                entregas_rango['Fecha Prom.'] = entregas_rango['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m') if pd.notna(x) else "")
                
                orden_grupos_maestro = ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES", "PARABRISAS", "TERCEROS"]
                grupos_rango_unicos = [g for g in orden_grupos_maestro if g in entregas_rango['Grupo'].unique()]
                otros_grupos = [g for g in entregas_rango['Grupo'].unique() if pd.notna(g) and g not in orden_grupos_maestro]
                grupos_rango_unicos.extend(otros_grupos)
                
                cols_grupos = st.columns(2)
                for idx, grupo_val in enumerate(grupos_rango_unicos):
                    with cols_grupos[idx % 2]:
                        st.caption(f"📍 **{grupo_val}**")
                        df_g_rango = entregas_rango[entregas_rango['Grupo'] == grupo_val].sort_values(by=['Fecha_Promesa_Disp', 'Hora_Entrega'])
                        
                        edit_g = st.data_editor(
                            df_g_rango[['Entregado_OK', 'Fecha Prom.', 'Hora_Entrega', 'Patente', 'Vehiculo', 'Asesor', 'Precio', 'Observaciones']], 
                            hide_index=True, 
                            use_container_width=True,
                            column_config={
                                "Entregado_OK": st.column_config.CheckboxColumn("✅ Listo", default=False),
                                "Fecha Prom.": st.column_config.TextColumn("📅 Día", disabled=True),
                                "Hora_Entrega": st.column_config.TextColumn("⌚ Hora", disabled=True),
                                "Patente": st.column_config.TextColumn("Patente", disabled=True), 
                                "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True), 
                                "Asesor": st.column_config.TextColumn("Asesor", disabled=True),
                                "Precio": st.column_config.NumberColumn("Monto ($)", format="$ %d", disabled=True),
                                "Observaciones": st.column_config.TextColumn("Observaciones", disabled=True)
                            },
                            key=f"editor_entregas_rango_{grupo_val.replace(' ', '_')}"
                        )
                        edit_rango_df = pd.concat([edit_rango_df, edit_g])
            else:
                st.info("No hay entregas pendientes para el rango y/o asesor seleccionado.")
                    
            if not edit_rango_df.empty or not edit_atra.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Confirmar Salida de Vehículos Seleccionados", use_container_width=True):
                    nuevas_confirmadas = []
                    if not edit_rango_df.empty: nuevas_confirmadas.extend(edit_rango_df[edit_rango_df['Entregado_OK'] == True]['Patente'].tolist())
                    if not edit_atra.empty: nuevas_confirmadas.extend(edit_atra[edit_atra['Entregado_OK'] == True]['Patente'].tolist())
                    
                    if nuevas_confirmadas:
                        st.session_state.entregas_confirmadas.extend(nuevas_confirmadas)
                        st.success(f"Se registraron {len(nuevas_confirmadas)} entregas. ¡A seguir facturando!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("No marcaste ningún vehículo como entregado.")

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN Y KANBAN
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación y Flujo de Trabajo")
    if not df.empty:
        col_filtro, _ = st.columns([1, 2])
        with col_filtro: asesor_filtro_prog = st.selectbox("👔 Filtrar por Asesor", ["TODOS"] + ASESORES_LISTA, key="filtro_asesor_prog")
            
        df_prog_filtrado = df.copy()
        if asesor_filtro_prog != "TODOS":
            nombre_corto = asesor_filtro_prog.split()[0].upper()
            df_prog_filtrado = df_prog_filtrado[df_prog_filtrado['Asesor'].str.contains(nombre_corto, case=False, na=False)]

        df_en_proceso = df_prog_filtrado[df_prog_filtrado['Estado_Taller'].str.contains("PROCESO", na=False)]
        
        st.markdown(f"### 🚥 Termómetro de Capacidad (Mes de {DIAS_HABILES_MES} días hábiles)")
        st.write(f"Calculado en base a los **Paños Activos** divididos por la capacidad teórica de producción ({CAPACIDAD_DIARIA_GRUPO:.1f} paños/día por grupo). No incluye vehículos detenidos.")
        
        if not df_en_proceso.empty:
            resumen_capacidad = df_en_proceso.groupby('Grupo').agg(Autos=('Patente', 'count'), Panos_Activos=('Paños', 'sum')).reset_index()
            resumen_capacidad['Dias_Carga_Real'] = resumen_capacidad['Panos_Activos'] / CAPACIDAD_DIARIA_GRUPO
            
            orden_grupos_maestro = ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES", "PARABRISAS", "TERCEROS"]
            resumen_capacidad['Orden'] = resumen_capacidad['Grupo'].apply(lambda x: orden_grupos_maestro.index(x) if x in orden_grupos_maestro else 99)
            resumen_capacidad = resumen_capacidad.sort_values('Orden').drop(columns=['Orden'])
            
            cols_cap = st.columns(len(resumen_capacidad))
            for i, row in resumen_capacidad.reset_index(drop=True).iterrows():
                with cols_cap[i]:
                    dias_reales = row['Dias_Carga_Real']
                    fecha_libre = obtener_proxima_fecha_libre(dias_reales)
                    color_dias = "#28a745" if dias_reales < 4 else "#ffc107" if dias_reales < 7 else "#dc3545"
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        <h4 style='color: #00235d; margin-top: 0;'>{row['Grupo']}</h4>
                        <h1 style='color: {color_dias}; margin: 10px 0;'>{dias_reales:.1f} Días</h1>
                        <p style='color: #17a2b8; font-weight: bold; font-size: 1.1em; margin-bottom: 0;'>📅 Libre aprox: {fecha_libre}</p>
                        <hr style='margin: 10px 0;'>
                        <div style='display: flex; justify-content: space-around;'>
                            <span style='font-size: 0.9em;'>🚗 {row['Autos']} autos</span>
                            <span style='font-size: 0.9em;'>📦 {row['Panos_Activos']:.1f} paños</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else: st.info("No hay vehículos en proceso para calcular capacidad.")

        st.divider()

        st.markdown("## 📑 Listado de Vehículos en Taller (Prioridad por Fecha Promesa)")
        st.write("Columnas actuales: Fechas clave, Vehículo, Asesor, Paños, Monto Pendiente (sólo en terminados) y Observaciones.")
        estados_map = [("⏳ EN PROCESO", "PROCESO"), ("⛔ DETENIDOS", "DETENIDO"), ("✅ TERMINADOS (Pte. Fact/Entr)", "TERM PEND"), ("🚚 ENTREGADOS", "ENTREGADO")]
        
        for titulo, match in estados_map:
            if "DETENIDO" in match: st.error(f"#### {titulo}")
            else: st.markdown(f"#### {titulo}")
            col1, col2 = st.columns(2)
            
            def dibujar_tabla(col, grupo_nombre, m_key):
                d_g = df_prog_filtrado[df_prog_filtrado['Grupo'] == grupo_nombre].copy()
                d_e = d_g[d_g['Estado_Taller'].str.contains(m_key, na=False)].copy()
                with col:
                    st.caption(f"**{grupo_nombre}**")
                    if not d_e.empty:
                        d_e = d_e.sort_values(by='Fin', ascending=True, na_position='last')
                        
                        d_e['F. Ingreso'] = d_e['Fecha_Ingreso'].apply(lambda x: x.strftime('%d/%m') if pd.notna(x) else "")
                        d_e['1ra Promesa'] = d_e['Fecha_Ticket'].apply(lambda x: x.strftime('%d/%m') if pd.notna(x) else "")
                        d_e['F. Entrega'] = d_e['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m') if pd.notna(x) else "")
                        
                        if m_key == "TERM PEND":
                            cols_to_show = ['F. Ingreso', '1ra Promesa', 'F. Entrega', 'Hora_Entrega', 'Patente', 'Vehiculo', 'Asesor', 'Paños', 'Precio', 'Observaciones']
                        else:
                            cols_to_show = ['F. Ingreso', '1ra Promesa', 'F. Entrega', 'Hora_Entrega', 'Patente', 'Vehiculo', 'Asesor', 'Paños', 'Observaciones']
                            
                        df_vista = d_e[cols_to_show]
                        
                        st.dataframe(
                            df_vista, 
                            hide_index=True, 
                            use_container_width=True, 
                            column_config={
                                "Hora_Entrega": st.column_config.TextColumn("Hs"),
                                "Precio": st.column_config.NumberColumn("Monto ($)", format="$ %d"),
                                "Observaciones": st.column_config.TextColumn("Observaciones", width="medium")
                            },
                            key=f"{grupo_nombre}_{m_key}_{asesor_filtro_prog}_detalle"
                        )
                    else: st.caption(f"Sin vehículos en este estado.")
                    
            dibujar_tabla(col1, "GRUPO UNO", match)
            dibujar_tabla(col2, "GRUPO DOS", match)
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.divider()

        st.markdown("### 📋 Tablero Kanban de Producción (Separado por Sector)")
        st.write("Los vehículos fluyen de izquierda a derecha. **Prioridad por colores:** 🟢 Con tiempo | 🟡 Entrega HOY | 🔴 Atrasado | ⚪ Detenido.")
        
        df_kanban = df_prog_filtrado[df_prog_filtrado['Estado_Taller'].str.contains("PROCESO|DETENIDO", na=False)].copy()
        df_kanban.loc[df_kanban['Estado_Taller'].str.contains("DETENIDO", na=False), 'Fase_Taller'] = "⛔ DETENIDOS"
        
        df_kanban['Fase_Taller'] = df_kanban['Fase_Taller'].str.strip().str.upper()
        df_kanban['Fase_Taller'] = df_kanban['Fase_Taller'].replace({"PREPARACION": "PREPARACIÓN"})
        
        orden_ideal = ["SIN FASE ASIGNADA", "CHAPA", "PREPARACIÓN", "PINTURA", "ARMADO", "PULIDO", "⛔ DETENIDOS"]
        
        grupos_presentes_raw = list(df_kanban['Grupo'].dropna().unique())
        orden_grupos_maestro = ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES", "PARABRISAS", "TERCEROS"]
        grupos_presentes = sorted(grupos_presentes_raw, key=lambda x: orden_grupos_maestro.index(x) if x in orden_grupos_maestro else 99)

        hoy_kanban = datetime.today().date()

        for grupo in grupos_presentes:
            st.markdown(f"<h4 style='color: #00235d; margin-top: 25px; border-bottom: 2px solid #00235d; padding-bottom: 5px;'>🏭 Sector: {grupo}</h4>", unsafe_allow_html=True)
            df_grupo_kanban = df_kanban[df_kanban['Grupo'] == grupo]

            cols_kanban = st.columns(len(orden_ideal))
            for idx, fase in enumerate(orden_ideal):
                with cols_kanban[idx]:
                    st.markdown(f"<div class='kanban-col' style='padding: 5px;'><h5 style='text-align:center; color:#00235d; margin: 0; font-size: 0.85rem;'>{fase}</h5></div>", unsafe_allow_html=True)
                    df_fase = df_grupo_kanban[df_grupo_kanban['Fase_Taller'] == fase]
                    
                    if not df_fase.empty:
                        for _, row in df_fase.iterrows():
                            f_prom = row.get('Fecha_Promesa_Disp')
                            
                            if fase == "⛔ DETENIDOS":
                                color_borde = "#6c757d" 
                                circulo = "⚪"
                                texto_fecha = "Detenido"
                            else:
                                if pd.isna(f_prom) or not f_prom:
                                    color_borde = "#17a2b8" 
                                    circulo = "🔵"
                                    texto_fecha = "Sin fecha"
                                elif f_prom < hoy_kanban:
                                    color_borde = "#dc3545" 
                                    circulo = "🔴"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                elif f_prom == hoy_kanban:
                                    color_borde = "#ffc107" 
                                    circulo = "🟡"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                else:
                                    color_borde = "#28a745" 
                                    circulo = "🟢"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                    
                            asesor_corto = row['Asesor'].split()[0] if row['Asesor'] else "N/A"
                            
                            novedad_html = ""
                            if fase == "⛔ DETENIDOS" and str(row.get('Observaciones', '')).strip() != "" and str(row.get('Observaciones', '')).lower() != "nan":
                                novedad_html = f"<div style='margin-top: 5px; font-size: 0.85em; color: #721c24; background-color: #f8d7da; padding: 4px; border-radius: 4px; border: 1px solid #f5c6cb;'><strong>Novedad:</strong> {str(row['Observaciones'])}</div>"
                            
                            st.markdown(f"""
                            <div style='background: white; padding: 8px; margin-top: 8px; border-radius: 5px; border-left: 5px solid {color_borde}; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); font-size: 0.9em;'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <strong>{row['Patente']}</strong>
                                    <span title='Fecha Promesa' style='font-size: 0.9em; font-weight: bold;'>{circulo} {texto_fecha}</span>
                                </div>
                                <span style='font-size: 0.85em;'>{row['Vehiculo'][:15]}</span><br>
                                <span style='font-size: 0.8em; color: gray;'>📦 {row['Paños']} p. | Asesor: {asesor_corto}</span>
                                {novedad_html}
                            </div>
                            """, unsafe_allow_html=True)
                    else: 
                        st.caption("")

        st.divider()
        
        st.markdown("### 📊 Análisis de Carga por Método Toyota (ABC)")
        if not df_en_proceso.empty:
            c_abc1, c_abc2 = st.columns([1, 2])
            with c_abc1:
                resumen_abc = df_en_proceso.groupby('Tipo_ABC')['Patente'].count().reset_index().rename(columns={'Patente': 'Cant. Vehículos'})
                st.dataframe(resumen_abc, hide_index=True, use_container_width=True)
            with c_abc2:
                fig_abc = px.pie(resumen_abc, values='Cant. Vehículos', names='Tipo_ABC', hole=0.4, title="Vehículos EN PROCESO por Clasificación ABC", color_discrete_sequence=['#28a745', '#ffc107', '#dc3545'])
                st.plotly_chart(fig_abc, use_container_width=True)

# ==========================================
# PESTAÑA 3: PORTAL EMPRESAS 
# ==========================================
with tab_portal:
    if not df.empty:
        st.subheader("🏢 Seguimiento de Unidades: Empresas del Grupo")
        df_grupo = df[df['Cliente'].str.contains('SOL|LUX|CIEL', case=False, na=False)].copy()
        if not df_grupo.empty:
            c_filtro, _ = st.columns([1, 2])
            with c_filtro: empresa_filtro = st.selectbox("Seleccionar Empresa", ["TODAS", "AUTOSOL", "AUTOLUX", "CIEL / AUTOCIEL"])
            df_vista_emp = df_grupo.copy()
            if empresa_filtro == "AUTOSOL": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('SOL', case=False, na=False)]
            elif empresa_filtro == "AUTOLUX": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('LUX', case=False, na=False)]
            elif empresa_filtro == "CIEL / AUTOCIEL": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('CIEL', case=False, na=False)]
            
            df_vista_emp = df_vista_emp.sort_values(by='Fecha_Promesa_Disp', ascending=True, na_position='last')
            
            en_proceso = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("PROCESO", na=False)])
            detenidos = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("DETENIDO", na=False)])
            terminados = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("TERM", na=False)])
            
            ce1, ce2, ce3 = st.columns(3)
            ce1.markdown(f'<div class="metric-card"><div class="metric-title">En Proceso</div><div class="metric-value-number">{en_proceso}</div><div class="metric-subtitle-blue">Vehículos en Taller</div></div>', unsafe_allow_html=True)
            ce2.markdown(f'<div class="metric-card"><div class="metric-title">Detenidos (Con Novedad)</div><div class="metric-value-number" style="color:#dc3545;">{detenidos}</div><div class="metric-subtitle-red">Revisar Observaciones</div></div>', unsafe_allow_html=True)
            ce3.markdown(f'<div class="metric-card"><div class="metric-title">Terminados (Pte. Entregar)</div><div class="metric-value-number" style="color:#28a745;">{terminados}</div><div class="metric-subtitle-green">Listos / Facturando</div></div>', unsafe_allow_html=True)
            st.divider()
            
            def calcular_fecha_entrega(row):
                f_prom = row['Fecha_Promesa_Disp']
                f_tick = row['Fecha_Ticket']
                if pd.isna(f_prom): return "Sin Fecha"
                texto_fecha = f_prom.strftime('%d/%m/%Y')
                if pd.notna(f_tick) and f_prom > f_tick: return f"{texto_fecha} 🟡 (Demorado)"
                return texto_fecha
            df_vista_emp['Fecha Entrega'] = df_vista_emp.apply(calcular_fecha_entrega, axis=1)
            
            def calcular_estado(estado):
                estado_str = str(estado).upper()
                if "DETENIDO" in estado_str: return f"🔴 {estado_str}"
                return estado_str
            df_vista_emp['Estado_Taller'] = df_vista_emp['Estado_Taller'].apply(calcular_estado)
            df_vista_emp['Fecha Ingreso'] = df_vista_emp['Fecha_Ingreso'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
            df_vista_emp['Fecha Ticket'] = df_vista_emp['Fecha_Ticket'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
            df_vista_emp['Fecha Ingreso Concesionario'] = None
            df_vista_emp['Asesor Concesionario'] = ""

            vista_columnas = ['Cliente', 'Vehiculo', 'Patente', 'Fecha Ingreso', 'Fecha Ticket', 'Estado_Taller', 'Fecha Entrega', 'Asesor', 'Fecha Ingreso Concesionario', 'Asesor Concesionario', 'Observaciones']
            mask_entregados = df_vista_emp['Estado_Taller'].str.contains('ENTREGADO', na=False)
            df_pendientes = df_vista_emp[~mask_entregados][vista_columnas].rename(columns={'Estado_Taller': 'Estado Actual'})
            df_entregados = df_vista_emp[mask_entregados][vista_columnas].rename(columns={'Estado_Taller': 'Estado Actual'})
            
            st.write("#### ⏳ Vehículos en Taller (Prioridad por Fecha Promesa)")
            st.data_editor(df_pendientes, hide_index=True, use_container_width=True, column_config={"Cliente": st.column_config.TextColumn("Cliente", disabled=True), "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True), "Patente": st.column_config.TextColumn("Patente", disabled=True), "Fecha Ingreso": st.column_config.TextColumn("Ingreso Taller", disabled=True), "Fecha Ticket": st.column_config.TextColumn("1ra Fecha Prom.", disabled=True), "Estado Actual": st.column_config.TextColumn("Estado Actual", disabled=True), "Fecha Entrega": st.column_config.TextColumn("Fecha Entrega", disabled=True), "Asesor": st.column_config.TextColumn("Asesor Taller", disabled=True), "Fecha Ingreso Concesionario": st.column_config.DateColumn("🗓️ Ingreso Conces.", format="DD/MM/YYYY"), "Asesor Concesionario": st.column_config.TextColumn("👤 Asesor Conces."), "Observaciones": st.column_config.TextColumn("📝 Observaciones (Doble Clic)", width="large", max_chars=1000)}, key="editor_observaciones_pendientes")
            st.write("#### 🚚 Vehículos Entregados (Historial Reciente)")
            st.dataframe(df_entregados, hide_index=True, use_container_width=True, column_config={"Observaciones": st.column_config.TextColumn("Observaciones", width="large")})
        else: st.info("No hay vehículos registrados para las empresas del grupo en este momento.")

# ==========================================
# PESTAÑA 4: FACTURACIÓN Y OBJETIVOS
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación, Paños y Objetivos")
        
        df_analisis = df.copy()
        
        def clasificar_estado(row):
            est_taller = str(row['Estado_Taller']).upper()
            est_fac = str(row['Estado_Fac']).upper()
            
            if 'DETENIDO' in est_taller: return 'En Taller (Otros)' 
            if est_fac == 'FAC': return 'Facturado (FAC)'
            if est_fac == 'SI': return 'Aprobado (SI)'
            return 'En Taller (Otros)'
            
        df_analisis['Estado_Resumen'] = df_analisis.apply(clasificar_estado, axis=1)

        df_fac = df_analisis[df_analisis['Estado_Resumen'] == 'Facturado (FAC)']
        df_si = df_analisis[df_analisis['Estado_Resumen'] == 'Aprobado (SI)']
        
        pesos_fac, panos_fac = df_fac['Precio'].sum(), df_fac['Paños'].sum()
        pesos_si, panos_si = df_si['Precio'].sum(), df_si['Paños'].sum()
        pesos_est, panos_est = pesos_fac + pesos_si, panos_fac + panos_si
        
        porcentaje_logro = min((panos_est / OBJETIVO_MENSUAL_PANOS) * 100 if OBJETIVO_MENSUAL_PANOS > 0 else 0, 100)
        
        dias_restantes = dias_restantes_calc
        panos_faltantes = max(0, OBJETIVO_MENSUAL_PANOS - panos_est)
        ritmo_diario_necesario = panos_faltantes / dias_restantes if dias_restantes > 0 else 0
        
        st.markdown("### 🎯 Control de Objetivo Mensual y Ritmo")
        c_obj1, c_obj2 = st.columns([3, 1])
        with c_obj1:
            st.progress(int(porcentaje_logro))
            st.caption(f"**Progreso del Mes:** {panos_est:.1f} paños asegurados de un objetivo de {OBJETIVO_MENSUAL_PANOS} paños.")
        with c_obj2:
            st.markdown(f"<h3 style='text-align: right; color: {'#28a745' if porcentaje_logro >= 95 else '#ffc107' if porcentaje_logro >= 75 else '#dc3545'}; margin-top: 0;'>{porcentaje_logro:.1f}%</h3>", unsafe_allow_html=True)
            
        st.info(f"⏱️ **Termómetro de Ritmo:** Faltan **{panos_faltantes:.1f} paños** y quedan **{dias_restantes} días hábiles**. Para llegar a la meta, el taller debe sacar a la calle **{ritmo_diario_necesario:.1f} paños por día** de acá a fin de mes.")
            
        st.write("### 💰 Rendimiento y Proyección al Cierre")
        c_r1, c_r2, c_r3 = st.columns(3)
        c_r1.markdown(f'<div class="metric-card"><div class="metric-title">Facturado Actual (FAC)</div><div class="metric-value-money">{formato_pesos(pesos_fac)}</div><div class="metric-subtitle-gray" style="font-size: 1.1rem; margin-top: 8px;">📦 {panos_fac:.1f} paños</div></div>', unsafe_allow_html=True)
        c_r2.markdown(f'<div class="metric-card"><div class="metric-title">Aprobado (SI)</div><div class="metric-value-money" style="color:#28a745;">{formato_pesos(pesos_si)}</div><div class="metric-subtitle-green" style="font-size: 1.1rem; margin-top: 8px;">📦 {panos_si:.1f} paños</div></div>', unsafe_allow_html=True)
        c_r3.markdown(f'<div class="metric-card" style="border: 2px solid #00235d; background-color: #f8f9fa;"><div class="metric-title" style="color:#00235d;">Estimado a Cierre de Mes</div><div class="metric-value-money" style="color:#00235d;">{formato_pesos(pesos_est)}</div><div class="metric-subtitle-gray" style="font-size: 1.1rem; color:#00235d; font-weight: bold; margin-top: 8px;">📦 {panos_est:.1f} paños totales</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECCIÓN MOVIDA: ALERTAS VISUALES DE PLATA INMOVILIZADA ---
        df_tpf = df[df['Estado_Taller'].str.contains("TERM PEND FACT", na=False)]
        df_tpe = df[df['Estado_Taller'].str.contains("TERM PEND ENTREG", na=False)]
        df_epf = df[df['Estado_Taller'].str.contains("ENTREGADO PEND FACT", na=False)]

        # --- ALERTAS VISUALES DE PLATA INMOVILIZADA (Sincronizadas con el "SI") ---
        df_alertas_si = df_analisis[df_analisis['Estado_Resumen'] == 'Aprobado (SI)']

        df_tpf = df_alertas_si[df_alertas_si['Estado_Taller'].str.contains("TERM PEND FACT", na=False)]
        df_tpe = df_alertas_si[df_alertas_si['Estado_Taller'].str.contains("TERM PEND ENTREG", na=False)]
        df_epf = df_alertas_si[df_alertas_si['Estado_Taller'].str.contains("ENTREGADO", na=False)]

        st.write("### 🚨 Detalle de Estados Pendientes (Plata Inmovilizada)")
        c_e1, c_e2, c_e3 = st.columns(3)
        c_e1.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Facturar</div><div class="metric-value-money">{formato_pesos(df_tpf["Precio"].sum())}</div><div class="metric-subtitle-red">⚠️ {df_tpf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e2.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Entregar</div><div class="metric-value-money">{formato_pesos(df_tpe["Precio"].sum())}</div><div class="metric-subtitle-blue">⏳ {df_tpe["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e3.markdown(f'<div class="metric-card"><div class="metric-title">Entregados (Pendiente Facturar)</div><div class="metric-value-money">{formato_pesos(df_epf["Precio"].sum())}</div><div class="metric-subtitle-green">🚚 {df_epf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # --- RADIOGRAFÍA DEL SI ---
        with st.expander("🔍 Radiografía del Aprobado (¿Dónde está la plata del 'SI'?)", expanded=True):
            st.write("Desglose exacto de los autos que tienen 'SI' cargado y cómo componen las tarjetas de arriba.")
            
            df_si_detail = df_si.copy()
            def status_si(row):
                est = str(row['Estado_Taller']).upper()
                f_prom = row['Fecha_Promesa_Disp']
                
                # Sincronizamos las categorías con las tarjetas
                if 'ENTREGADO' in est: return '1. 🚚 Entregados (Pendiente Facturar)'
                if 'TERM PEND ENTREG' in est: return '2. ⏳ Terminados (Pendiente Entregar)'
                if 'TERM' in est: return '3. ⚠️ Terminados (Pendiente Facturar)'
                if pd.notna(f_prom) and f_prom < hoy.date(): return '5. 🔴 Atrasados en Producción'
                return '4. 🟢 En Taller (A tiempo)'

            df_si_detail['Categoría_Real'] = df_si_detail.apply(status_si, axis=1)
            
            resumen_si_cat = df_si_detail.groupby('Categoría_Real').agg(
                Vehículos=('Patente', 'count'),
                Paños=('Paños', 'sum'),
                Pesos=('Precio', 'sum')
            ).reset_index().sort_values('Categoría_Real')
            
            resumen_si_cat['Pesos ($)'] = resumen_si_cat['Pesos'].apply(formato_pesos)
            
            st.dataframe(resumen_si_cat[['Categoría_Real', 'Vehículos', 'Paños', 'Pesos ($)']], hide_index=True, use_container_width=True, column_config={
                "Categoría_Real": st.column_config.TextColumn("Estado en el Taller"),
                "Vehículos": st.column_config.NumberColumn("Cant. Autos"),
                "Paños": st.column_config.NumberColumn("Paños"),
                "Pesos ($)": st.column_config.TextColumn("Monto Esperado")
            })

        # --- RADAR MES SIGUIENTE (NO) ---
        st.write("### 🔭 Radar del Mes Siguiente (Estado 'NO')")
        st.write("Vehículos marcados con estado **'NO'** en la facturación. Esto representa el colchón de trabajo/plata que se patea y asegura para arrancar el próximo mes.")
        
        # Filtramos los 'NO' de la base global
        df_no = df_completo[df_completo['Estado_Fac'] == 'NO'].copy()
        
        if not df_no.empty:
            p_no = df_no['Precio'].sum()
            pa_no = df_no['Paños'].sum()
            a_no = df_no['Patente'].count()
            
            c_n1, c_n2, c_n3 = st.columns(3)
            c_n1.markdown(f'<div class="metric-card"><div class="metric-title">Autos para Próx. Mes</div><div class="metric-value-number" style="color:#6f42c1;">{a_no}</div></div>', unsafe_allow_html=True)
            c_n2.markdown(f'<div class="metric-card"><div class="metric-title">Paños Asegurados</div><div class="metric-value-number" style="color:#6f42c1;">{pa_no:.1f}</div></div>', unsafe_allow_html=True)
            c_n3.markdown(f'<div class="metric-card"><div class="metric-title">Plata Proyectada</div><div class="metric-value-money" style="color:#6f42c1;">{formato_pesos(p_no)}</div></div>', unsafe_allow_html=True)
            
            with st.expander("Ver detalle de los autos marcados con 'NO'"):
                st.dataframe(df_no[['Patente', 'Vehiculo', 'Cliente', 'Asesor', 'Grupo', 'Paños', 'Precio']], hide_index=True, use_container_width=True, column_config={"Precio": st.column_config.NumberColumn("Precio ($)", format="$ %d")})
        else:
            st.info("No hay vehículos marcados con 'NO' en la planilla todavía.")
            
        st.divider()

        # --- CURVA DE PROYECCIÓN DE INGRESOS ---
        if mes_filtro != "TODOS":
            st.markdown("### 📈 Curva de Producción y Facturación del Mes")
            st.write("Muestra cómo se acumula la plata. **Línea Gris:** Lo que la gerencia pide por día de forma lineal. **Línea Celeste:** Lo que *deberíamos* facturar si cumplimos con las Fechas Prometidas. **Línea Verde:** Lo que *realmente* ya terminamos o entregamos hasta hoy. **Si la Verde va por debajo de la Celeste, venimos atrasados.**")
            
            primer_dia = date(año_filtro, mes_num_filtro, 1)
            _, ult_dia = calendar.monthrange(año_filtro, mes_num_filtro)
            fechas_mes = [date(año_filtro, mes_num_filtro, d) for d in range(1, ult_dia + 1)]

            df_dias = pd.DataFrame({'Fecha': fechas_mes})
            df_dias['Es_Habil'] = df_dias['Fecha'].apply(lambda x: x.weekday() < 5 and x not in FERIADOS_ARG)
            df_habiles = df_dias[df_dias['Es_Habil']].copy()
            df_habiles['Dia_Habil_Num'] = range(1, len(df_habiles) + 1)
            
            df_habiles['Meta Lineal (Paños)'] = df_habiles['Dia_Habil_Num'] * CAPACIDAD_DIARIA_TALLER

            df_proyeccion = df_analisis[df_analisis['Estado_Resumen'].isin(['Facturado (FAC)', 'Aprobado (SI)'])].copy()
            
            def asignar_fecha_curva(row):
                f = row['Fecha_Promesa_Disp']
                if pd.isna(f) or f.month != mes_num_filtro or f.year != año_filtro:
                    return hoy.date() if hoy.month == mes_num_filtro else primer_dia
                return f

            df_proyeccion['Fecha_Curva'] = df_proyeccion.apply(asignar_fecha_curva, axis=1)
            df_proyeccion['Es_Hecho'] = df_proyeccion['Estado_Taller'].str.contains('ENTREGADO|TERM', na=False) | (df_proyeccion['Estado_Resumen'] == 'Facturado (FAC)')

            agrupado = df_proyeccion.groupby('Fecha_Curva').agg(Paños_Esperados=('Paños', 'sum'), Pesos_Esperados=('Precio', 'sum')).reset_index()
            agrupado_hecho = df_proyeccion[df_proyeccion['Es_Hecho']].groupby('Fecha_Curva').agg(Paños_Hechos=('Paños', 'sum')).reset_index()

            df_habiles = df_habiles.merge(agrupado, left_on='Fecha', right_on='Fecha_Curva', how='left').fillna(0)
            df_habiles = df_habiles.merge(agrupado_hecho, left_on='Fecha', right_on='Fecha_Curva', how='left').fillna(0)

            df_habiles['1. Proyección Esperada (SI+FAC)'] = df_habiles['Paños_Esperados'].cumsum()
            df_habiles['Acumulado Pesos ($)'] = df_habiles['Pesos_Esperados'].cumsum()
            df_habiles['2. Avance Real Hecho'] = df_habiles['Paños_Hechos'].cumsum()
            
            df_habiles.loc[df_habiles['Fecha'] > hoy.date(), '2. Avance Real Hecho'] = None

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_habiles['Fecha'], y=df_habiles['Meta Lineal (Paños)'], name='Meta Exigida (Lineal)', mode='lines', line=dict(color='gray', dash='dash', width=2)))
            fig.add_trace(go.Scatter(x=df_habiles['Fecha'], y=df_habiles['1. Proyección Esperada (SI+FAC)'], name='Proyección según Fechas (Ideal)', mode='lines+markers', line=dict(color='#00A8E8', width=2), marker=dict(size=6, color='#00A8E8')))
            fig.add_trace(go.Scatter(x=df_habiles['Fecha'], y=df_habiles['2. Avance Real Hecho'], name='Avance Real al Día de Hoy (Term/Entr)', mode='lines+markers', line=dict(color='#28a745', width=4), marker=dict(size=8, color='#1e7e34')))
            
            fig.update_layout(title="Curva de Acumulación de Trabajo (Mes)", xaxis_title="Días Hábiles", yaxis_title="Cantidad de Paños Acumulados", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Ver tabla de flujo de caja esperado por día de entrega"):
                df_cashflow = df_habiles[['Fecha', 'Paños_Esperados', 'Pesos_Esperados', '1. Proyección Esperada (SI+FAC)', 'Acumulado Pesos ($)']].rename(columns={'Paños_Esperados': 'Paños (Ese Día)', 'Pesos_Esperados': 'Plata (Ese Día)'})
                df_cashflow['Plata (Ese Día)'] = df_cashflow['Plata (Ese Día)'].apply(formato_pesos)
                df_cashflow['Acumulado Pesos ($)'] = df_cashflow['Acumulado Pesos ($)'].apply(formato_pesos)
                st.dataframe(df_cashflow[df_cashflow['Paños (Ese Día)'] > 0], hide_index=True, use_container_width=True)
                
        else:
            st.info("Para ver la Curva de Proyección de Ingresos, por favor seleccioná un mes específico en la barra lateral.")

        st.divider()

        st.write("### 📊 Análisis de Producción Detallado")
        def crear_tabla_resumen(df_origen, columna_indice):
            pivot = df_origen.pivot_table(index=columna_indice, columns='Estado_Resumen', values=['Paños', 'Precio'], aggfunc='sum', fill_value=0)
            for est in ['Facturado (FAC)', 'Aprobado (SI)', 'En Taller (Otros)']:
                if ('Paños', est) not in pivot.columns: pivot[('Paños', est)] = 0
                if ('Precio', est) not in pivot.columns: pivot[('Precio', est)] = 0
            df_res = pd.DataFrame(index=pivot.index)
            df_res['📦 FAC'] = pivot[('Paños', 'Facturado (FAC)')]
            df_res['📦 SI'] = pivot[('Paños', 'Aprobado (SI)')]
            df_res['📦 EST. CIERRE (FAC+SI)'] = df_res['📦 FAC'] + df_res['📦 SI']
            df_res['📦 OTROS (En Taller)'] = pivot[('Paños', 'En Taller (Otros)')]
            df_res['💰 FAC'] = pivot[('Precio', 'Facturado (FAC)')]
            df_res['💰 SI'] = pivot[('Precio', 'Aprobado (SI)')]
            df_res['💰 EST. CIERRE (FAC+SI)'] = df_res['💰 FAC'] + df_res['💰 SI']
            df_res['💰 OTROS (En Taller)'] = pivot[('Precio', 'En Taller (Otros)')]
            
            orden_grupos_maestro = ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES", "PARABRISAS", "TERCEROS"]
            df_res['Orden'] = df_res.index.map(lambda x: orden_grupos_maestro.index(x) if x in orden_grupos_maestro else 99)
            df_res = df_res.sort_values(by=['Orden', '📦 EST. CIERRE (FAC+SI)'], ascending=[True, False]).drop(columns=['Orden'])
            return df_res

        colores_grafico = {'Facturado': '#28a745', 'Aprobado (SI)': '#adb5bd', 'Proyección al Cierre': '#00A8E8'}
        tab_grupos, tab_asesores, tab_empresas = st.tabs(["👥 Producción por Grupo", "👔 Producción por Asesor", "🏢 Estimado Cierre por Empresa"])

        dict_formato_tablas = {}
        
        with tab_grupos:
            tabla_grupo = crear_tabla_resumen(df_analisis, 'Grupo')
            df_g_panos_chart = tabla_grupo.reset_index()[['Grupo', '📦 FAC', '📦 SI', '📦 EST. CIERRE (FAC+SI)']].melt(id_vars='Grupo', var_name='Métrica', value_name='Paños')
            df_g_panos_chart['Métrica'] = df_g_panos_chart['Métrica'].replace({'📦 FAC': 'Facturado', '📦 SI': 'Aprobado (SI)', '📦 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})
            df_g_pesos_chart = tabla_grupo.reset_index()[['Grupo', '💰 FAC', '💰 SI', '💰 EST. CIERRE (FAC+SI)']].melt(id_vars='Grupo', var_name='Métrica', value_name='Precio')
            df_g_pesos_chart['Métrica'] = df_g_pesos_chart['Métrica'].replace({'💰 FAC': 'Facturado', '💰 SI': 'Aprobado (SI)', '💰 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})

            col_g_g1, col_g_g2 = st.columns(2)
            with col_g_g1:
                fig_g_panos = px.bar(df_g_panos_chart, x='Grupo', y='Paños', color='Métrica', barmode='group', text_auto='.1f', title='📦 Paños Totales', color_discrete_map=colores_grafico)
                fig_g_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_g_panos, use_container_width=True)
            with col_g_g2:
                fig_g_pesos = px.bar(df_g_pesos_chart, x='Grupo', y='Precio', color='Métrica', barmode='group', text_auto='$.2s', title='💰 Montos en Pesos', color_discrete_map=colores_grafico)
                fig_g_pesos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_g_pesos, use_container_width=True)

            col_g_p1, col_g_p2 = st.columns(2)
            df_pie_g = tabla_grupo.reset_index()
            with col_g_p1:
                df_panos_pie = df_pie_g[df_pie_g['📦 EST. CIERRE (FAC+SI)'] > 0]
                if not df_panos_pie.empty: st.plotly_chart(px.pie(df_panos_pie, values='📦 EST. CIERRE (FAC+SI)', names='Grupo', hole=0.4, title='Distribución de Paños Totales'), use_container_width=True)
            with col_g_p2:
                df_pesos_pie = df_pie_g[df_pie_g['💰 EST. CIERRE (FAC+SI)'] > 0]
                if not df_pesos_pie.empty: st.plotly_chart(px.pie(df_pesos_pie, values='💰 EST. CIERRE (FAC+SI)', names='Grupo', hole=0.4, title='Distribución de Ingresos Totales ($)'), use_container_width=True)

            dict_formato_tablas = {c: formato_pesos for c in tabla_grupo.columns if '💰' in c}
            dict_formato_tablas.update({c: formato_panos for c in tabla_grupo.columns if '📦' in c})
            
            st.dataframe(tabla_grupo.style.format(dict_formato_tablas), use_container_width=True)

        with tab_asesores:
            df_asesores_limpio = df_analisis[df_analisis['Asesor'] != 'SIN ASIGNAR'].copy()
            
            def crear_tabla_resumen_asesor(df_origen, columna_indice):
                pivot = df_origen.pivot_table(index=columna_indice, columns='Estado_Resumen', values=['Paños', 'Precio'], aggfunc='sum', fill_value=0)
                for est in ['Facturado (FAC)', 'Aprobado (SI)', 'En Taller (Otros)']:
                    if ('Paños', est) not in pivot.columns: pivot[('Paños', est)] = 0
                    if ('Precio', est) not in pivot.columns: pivot[('Precio', est)] = 0
                df_res = pd.DataFrame(index=pivot.index)
                df_res['📦 FAC'] = pivot[('Paños', 'Facturado (FAC)')]
                df_res['📦 SI'] = pivot[('Paños', 'Aprobado (SI)')]
                df_res['📦 EST. CIERRE (FAC+SI)'] = df_res['📦 FAC'] + df_res['📦 SI']
                df_res['📦 OTROS (En Taller)'] = pivot[('Paños', 'En Taller (Otros)')]
                df_res['💰 FAC'] = pivot[('Precio', 'Facturado (FAC)')]
                df_res['💰 SI'] = pivot[('Precio', 'Aprobado (SI)')]
                df_res['💰 EST. CIERRE (FAC+SI)'] = df_res['💰 FAC'] + df_res['💰 SI']
                df_res['💰 OTROS (En Taller)'] = pivot[('Precio', 'En Taller (Otros)')]
                return df_res.sort_values(by='📦 EST. CIERRE (FAC+SI)', ascending=False)
                
            tabla_asesor = crear_tabla_resumen_asesor(df_asesores_limpio, 'Asesor')
            df_a_panos_chart = tabla_asesor.reset_index()[['Asesor', '📦 FAC', '📦 SI', '📦 EST. CIERRE (FAC+SI)']].melt(id_vars='Asesor', var_name='Métrica', value_name='Paños')
            df_a_panos_chart['Métrica'] = df_a_panos_chart['Métrica'].replace({'📦 FAC': 'Facturado', '📦 SI': 'Aprobado (SI)', '📦 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})
            df_a_pesos_chart = tabla_asesor.reset_index()[['Asesor', '💰 FAC', '💰 SI', '💰 EST. CIERRE (FAC+SI)']].melt(id_vars='Asesor', var_name='Métrica', value_name='Precio')
            df_a_pesos_chart['Métrica'] = df_a_pesos_chart['Métrica'].replace({'💰 FAC': 'Facturado', '💰 SI': 'Aprobado (SI)', '💰 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})

            col_a_g1, col_a_g2 = st.columns(2)
            with col_a_g1:
                fig_a_panos = px.bar(df_a_panos_chart, x='Asesor', y='Paños', color='Métrica', barmode='group', text_auto='.1f', title='📦 Paños por Asesor', color_discrete_map=colores_grafico)
                fig_a_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_a_panos, use_container_width=True)
            with col_a_g2:
                fig_a_pesos = px.bar(df_a_pesos_chart, x='Asesor', y='Precio', color='Métrica', barmode='group', text_auto='$.2s', title='💰 Montos por Asesor', color_discrete_map=colores_grafico)
                fig_a_pesos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_a_pesos, use_container_width=True)

            col_a_p1, col_a_p2 = st.columns(2)
            df_pie_a = tabla_asesor.reset_index()
            with col_a_p1:
                df_panos_pie_a = df_pie_a[df_pie_a['📦 EST. CIERRE (FAC+SI)'] > 0]
                if not df_panos_pie_a.empty: st.plotly_chart(px.pie(df_panos_pie_a, values='📦 EST. CIERRE (FAC+SI)', names='Asesor', hole=0.4, title='Distribución de Paños Totales'), use_container_width=True)
            with col_a_p2:
                df_pesos_pie_a = df_pie_a[df_pie_a['💰 EST. CIERRE (FAC+SI)'] > 0]
                if not df_pesos_pie_a.empty: st.plotly_chart(px.pie(df_pesos_pie_a, values='💰 EST. CIERRE (FAC+SI)', names='Asesor', hole=0.4, title='Distribución de Ingresos Totales ($)'), use_container_width=True)

            st.dataframe(tabla_asesor.style.format(dict_formato_tablas), use_container_width=True)

        with tab_empresas:
            col_e1, col_e2 = st.columns([1.5, 1])
            with col_e1:
                
                def crear_tabla_resumen_emp(df_origen, columna_indice):
                    pivot = df_origen.pivot_table(index=columna_indice, columns='Estado_Resumen', values=['Paños', 'Precio'], aggfunc='sum', fill_value=0)
                    for est in ['Facturado (FAC)', 'Aprobado (SI)', 'En Taller (Otros)']:
                        if ('Paños', est) not in pivot.columns: pivot[('Paños', est)] = 0
                        if ('Precio', est) not in pivot.columns: pivot[('Precio', est)] = 0
                    df_res = pd.DataFrame(index=pivot.index)
                    df_res['📦 FAC'] = pivot[('Paños', 'Facturado (FAC)')]
                    df_res['📦 SI'] = pivot[('Paños', 'Aprobado (SI)')]
                    df_res['📦 EST. CIERRE (FAC+SI)'] = df_res['📦 FAC'] + df_res['📦 SI']
                    df_res['📦 OTROS (En Taller)'] = pivot[('Paños', 'En Taller (Otros)')]
                    df_res['💰 FAC'] = pivot[('Precio', 'Facturado (FAC)')]
                    df_res['💰 SI'] = pivot[('Precio', 'Aprobado (SI)')]
                    df_res['💰 EST. CIERRE (FAC+SI)'] = df_res['💰 FAC'] + df_res['💰 SI']
                    df_res['💰 OTROS (En Taller)'] = pivot[('Precio', 'En Taller (Otros)')]
                    return df_res.sort_values(by='📦 EST. CIERRE (FAC+SI)', ascending=False)
                    
                tabla_empresa = crear_tabla_resumen_emp(df_analisis, 'Cliente')
                st.dataframe(tabla_empresa.style.format(dict_formato_tablas), use_container_width=True)
            with col_e2:
                df_cierre = df_analisis[df_analisis['Estado_Resumen'].isin(['Facturado (FAC)', 'Aprobado (SI)'])]
                if not df_cierre.empty:
                    res_empresa_pie = df_cierre.groupby('Cliente')[['Precio']].sum().reset_index()
                    st.plotly_chart(px.pie(res_empresa_pie, values='Precio', names='Cliente', hole=0.4, title="Participación en el Cierre Estimado ($)"), use_container_width=True)

        # --- GESTIÓN DE TERCEROS ---
        st.divider()
        st.markdown("### 🤝 Gestión Financiera de Terceros")
        df_terceros = df_analisis[(df_analisis['Grupo'] == 'TERCEROS') & (df_analisis['Estado_Resumen'].isin(['Facturado (FAC)', 'Aprobado (SI)']))]
        
        if not df_terceros.empty:
            tot_ter_fac = df_terceros['Precio'].sum()
            tot_ter_costo = df_terceros['Costo'].sum()
            tot_ter_margen = tot_ter_fac - tot_ter_costo
            tot_ter_panos = df_terceros['Paños'].sum()
            
            c_t1, c_t2, c_t3, c_t4 = st.columns(4)
            c_t1.markdown(f'<div class="metric-card"><div class="metric-title">Total Venta (Terceros)</div><div class="metric-value-money" style="font-size: 1.5rem;">{formato_pesos(tot_ter_fac)}</div></div>', unsafe_allow_html=True)
            c_t2.markdown(f'<div class="metric-card"><div class="metric-title">Costo Total</div><div class="metric-value-money" style="color:#dc3545; font-size: 1.5rem;">{formato_pesos(tot_ter_costo)}</div></div>', unsafe_allow_html=True)
            c_t3.markdown(f'<div class="metric-card"><div class="metric-title">Margen de Ganancia</div><div class="metric-value-money" style="color:#28a745; font-size: 1.5rem;">{formato_pesos(tot_ter_margen)}</div></div>', unsafe_allow_html=True)
            c_t4.markdown(f'<div class="metric-card"><div class="metric-title">Paños Asignados</div><div class="metric-value-number" style="font-size: 1.5rem;">{tot_ter_panos:.1f}</div></div>', unsafe_allow_html=True)
        else:
            st.info("No hay datos de Terceros en estado Facturado o Aprobado para el período seleccionado.")

# ==========================================
# PESTAÑA 5: KPIs
# ==========================================
with tab_kpi:
    if not df.empty:
        st.subheader("Indicadores Clave de Desempeño (KPI)")
        k1, k2, k3 = st.columns(3)
        df_fac_kpi = df[df['Estado_Fac'] == 'FAC']
        ticket = df_fac_kpi['Precio'].mean() if not df_fac_kpi.empty else 0
        k1.metric("Ticket Promedio (FAC)", formato_pesos(ticket))
        intensidad = df['Paños'].mean()
        k2.metric("Paños Promedio / Auto", f"{intensidad:.2f}")
        total_casos = len(df[df['Estado_Fac'].isin(['FAC', 'SI', 'NO'])])
        casos_fac = len(df_fac_kpi)
        ratio = (casos_fac / total_casos * 100) if total_casos > 0 else 0
        k3.metric("% Conversión a Facturado", f"{ratio:.1f}%")
        st.divider()
        st.write("### Cantidad de Vehículos por Asesor")
        df_kpi_asesores = df[df['Asesor'] != 'SIN ASIGNAR']
        st.plotly_chart(px.bar(df_kpi_asesores, x="Asesor", color="Estado_Fac", barmode="group"), use_container_width=True)

# ==========================================
# PESTAÑA 6: HISTÓRICOS
# ==========================================
with tab_hist:
    if not df_completo.empty: 
        st.subheader("📅 Histórico Mensual")
        df_hist = df_completo[df_completo['Mes_Hist'] != 'SIN FECHA'].sort_values('Mes_Hist')
        if not df_hist.empty:
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                pivot_panos = pd.pivot_table(df_hist, values='Paños', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_panos.style.format("{:.1f}"), use_container_width=True)
            with c_h2:
                pivot_pesos = pd.pivot_table(df_hist, values='Precio', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_pesos.style.format(lambda x: f"$ {x:,.0f}".replace(',', '.')), use_container_width=True)
            st.divider()
            st.plotly_chart(px.bar(df_hist, x="Mes_Hist", y="Paños", color="Cliente", barmode="group", title="Paños Facturados/Proyectados por Mes"), use_container_width=True)
        else: st.info("No hay datos con fechas válidas para mostrar el historial.")
