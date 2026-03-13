import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import calendar
import re
import time

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
    .kanban-col { background-color: #f8f9fa; border-radius: 8px; padding: 10px; border: 1px solid #e9ecef; }
</style>""", unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) Y BUSCADOR ---
with st.sidebar:
    st.markdown("### 🔍 Buscador Rápido")
    busqueda_global = st.text_input("Dominio o Chasis", placeholder="Ej: AB123CD")
    st.caption("Filtra tablas y muestra un resumen.")
    st.divider()

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

# --- LÓGICA DE DÍAS HÁBILES ---
FERIADOS_ARG = [date(datetime.now().year, 3, 24)] 

def dias_habiles_del_mes(anio, mes):
    _, ult_dia = calendar.monthrange(anio, mes)
    dias = 0
    for d in range(1, ult_dia + 1):
        fecha = date(anio, mes, d)
        if fecha.weekday() < 5 and fecha not in FERIADOS_ARG:
            dias += 1
    return max(1, dias)

DIAS_HABILES_MES = dias_habiles_del_mes(datetime.now().year, datetime.now().month)
CAPACIDAD_DIARIA_TALLER = OBJETIVO_MENSUAL_PANOS / DIAS_HABILES_MES
CAPACIDAD_DIARIA_GRUPO = CAPACIDAD_DIARIA_TALLER / 2

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

def dias_habiles_restantes_mes():
    hoy = datetime.today()
    _, ult_dia = calendar.monthrange(hoy.year, hoy.month)
    dias_restantes = 0
    for d in range(hoy.day, ult_dia + 1):
        fecha = date(hoy.year, hoy.month, d)
        if fecha.weekday() < 5 and fecha not in FERIADOS_ARG:
            dias_restantes += 1
    return max(1, dias_restantes) 

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
        
        for _, row in d.iterrows():
            col_fecha = next((c for c in d.columns if 'FECH' in c), None)
            fecha_turno = parsear_fecha_español(row.get(col_fecha, '')) or datetime.now()
            asesor_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if asesor_raw not in ASESORES_LISTA: asesor_raw = "SIN ASIGNAR"
            col_tiempo = next((c for c in d.columns if 'TIEMPO' in c), None)
            
            filas.append({
                'Tipo': '📅 PROGRAMADO', 'Fecha': fecha_turno.date(), 'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(), 'Patente': str(row.get('PATENTE', '')).upper(),
                'Chasis': str(row.get(col_chasis, '')).strip().upper() if col_chasis else "",
                'Asesor': asesor_raw, 'Precio': str(row.get('PRECIO', '')).strip(), 'Paños': str(row.get('PAÑOS', '')).strip(),
                'Observaciones': str(row.get('OBSERVACIONES', '')).strip(), 'Tiempo_Entrega': str(row.get(col_tiempo, '')) if col_tiempo else "",
                'Cliente': str(row.get('CLIENTE', '')).upper(), 'Seguro': str(row.get('SEGURO', '')).upper(),
                'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
            })
        return pd.DataFrame(filas)
    except: return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=300)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            d = pd.read_csv(f"{URL_BASE}{gid}", dtype=str)
            d.columns = d.columns.str.strip().str.upper()
            
            if n != "PARABRISAS":
                cols = list(d.columns)
                while len(cols) < 22: cols.append(f"VACIA_{len(cols)}")
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
                    if 'ESTADO FAC' in c or 'ESTADOFAC' in c: renames[c] = 'ESTADO_FAC'
                    elif 'ESTADO TALLER' in c or 'ESTADOTALLER' in c: renames[c] = 'ESTADO_TALLER'
                    elif 'FASE' in c: renames[c] = 'FASE_TALLER'
                    elif 'COMPAÑIA' in c or 'SEGURO' in c or 'EMPRESA' in c: renames[c] = 'EMPRESA_TALLER'
                    elif 'OBSERVACION' in c: renames[c] = 'OBSERVACIONES_TALLER'
                    elif 'PROMESA' in c: renames[c] = 'FECHA_PROMESA_I'
                    elif 'TICKET' in c: renames[c] = 'FECHA_TICKET'
                    elif 'INGRESO' in c: renames[c] = 'FECHA_INGRESO_TALLER'
                    elif 'HORA' in c: renames[c] = 'HORA_ENTREGA'
                d = d.rename(columns=renames)

            if 'PATENTE' in d.columns: 
                d = d.dropna(subset=['PATENTE'])
                d = d[d['PATENTE'].str.strip() != ""]
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
        
    if not dfs: return pd.DataFrame()
    df_raw = pd.concat(dfs, ignore_index=True)
    filas = []
    
    col_chasis_global = next((c for c in df_raw.columns if 'CHASIS' in c or 'VIN' in c), None)
    
    for _, row in df_raw.iterrows():
        f_fin = parsear_fecha_español(row.get('FECHA_PROMESA_I', ''))
        f_fin_disp = f_fin.date() if f_fin else None
        if not f_fin: f_fin = datetime.now() + timedelta(days=3650)
        
        mes_hist = f_fin.strftime('%Y-%m') if f_fin.year < 2030 else "SIN FECHA"
        if row.get('GRUPO_ORIGEN') == 'PARABRISAS':
            mes_str = str(row.get('MES', '')).strip().lower()
            if mes_str in MESES_ES:
                mes_hist = f"{datetime.now().year}-{MESES_ES[mes_str]:02d}"

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
            'Estado_Fac': str(row.get('ESTADO_FAC', '')).strip().upper(), 
            'Estado_Taller': estado, 'Fase_Taller': fase, 'Precio': precio_val, 'Observaciones': str(row.get('OBSERVACIONES_TALLER', '')).replace('nan', '').strip()
        })
    return pd.DataFrame(filas)

# --- MEMORIA Y CARGA DE DATOS ---
if 'memoria_turnos_v11' not in st.session_state: 
    st.session_state.memoria_turnos_v11 = obtener_turnos()

if 'entregas_confirmadas' not in st.session_state:
    st.session_state.entregas_confirmadas = []

df = obtener_datos_maestros()
df_turnos_display = st.session_state.memoria_turnos_v11.copy()

# --- APLICAR BUSCADOR GLOBAL (CON RESUMEN EN LA BARRA LATERAL) ---
if busqueda_global:
    termino = busqueda_global.upper().strip()
    
    # 1. Filtrar Taller
    if not df.empty:
        if 'Chasis' not in df.columns: df['Chasis'] = ""
        df = df[(df['Patente'].str.contains(termino, na=False)) | 
                (df['Chasis'].str.contains(termino, na=False))]
                
    # 2. Filtrar Turnos
    if not df_turnos_display.empty:
        if 'Chasis' not in df_turnos_display.columns: df_turnos_display['Chasis'] = ""
        df_turnos_display = df_turnos_display[(df_turnos_display['Patente'].str.contains(termino, na=False)) | 
                                              (df_turnos_display['Chasis'].str.contains(termino, na=False))]
    
    # 3. Dibujar el resumen en la barra lateral
    with st.sidebar:
        st.markdown("### 📋 Resumen del Vehículo")
        
        if not df.empty:
            for _, row in df.head(5).iterrows(): # Mostramos hasta 5 coincidencias
                f_prom = row.get('Fecha_Promesa_Disp')
                fecha_str = f_prom.strftime('%d/%m/%Y') if pd.notna(f_prom) else "Sin Fecha"
                estado_taller = str(row.get('Estado_Taller', ''))
                
                # Definir color del borde según el estado
                if "ENTREGADO" in estado_taller: color_borde = "#28a745" # Verde
                elif "PROCESO" in estado_taller: color_borde = "#ffc107" # Amarillo
                elif "DETENIDO" in estado_taller: color_borde = "#dc3545" # Rojo
                elif "TERM" in estado_taller: color_borde = "#17a2b8" # Celeste
                else: color_borde = "#6c757d" # Gris
                
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
            st.warning("No se encontró el vehículo en el taller ni en los turnos.")

# --- BOTÓN DE ACTUALIZACIÓN EN LA BARRA LATERAL ---
with st.sidebar:
    st.divider()
    st.markdown("### ⚙️ Sistema")
    if st.button("🔄 Forzar Actualización", use_container_width=True):
        st.cache_data.clear()
        st.success("¡Datos actualizados!"); time.sleep(0.5); st.rerun()
    st.caption("Datos extraídos de Google Sheets.")

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
# PESTAÑA 1: TURNERO Y ENTREGAS (Cajas Separadas)
# ==========================================
with tab_turnos:
    if recomendaciones_grupos and not busqueda_global:
        st.info("**📅 Asistente de Turnos (Disponibilidad Estimada por Grupo):**\n" + 
                " | ".join([f"**{g}**: libre desde el {f}" for g, f in recomendaciones_grupos.items()]))
    
    # --- FILTROS GLOBALES PARA LA PESTAÑA ---
    st.markdown("<h4 style='color: #00235d; margin-top: 10px;'>🔍 Filtros de Visualización (Aplican a Ingresos y Salidas)</h4>", unsafe_allow_html=True)
    col_fecha, col_asesor, col_add = st.columns([1, 1, 2])
    with col_fecha:
        hoy = datetime.today().date()
        fechas_seleccionadas = st.date_input("📅 Rango de Fechas", value=(hoy, hoy), format="DD/MM/YYYY")
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
                nueva_patente, nuevo_vehiculo, nuevo_cliente = c_pat.text_input("Patente *"), c_veh.text_input("Vehículo *"), c_cli.selectbox("Cliente", CLIENTES_LISTA)
                c_seg, c_pre, c_pan = st.columns(3)
                nuevo_seguro, nuevo_precio, nuevo_panos = c_seg.text_input("Seguro"), c_pre.text_input("Precio ($)"), c_pan.text_input("Paños (Ej: 1.5)")
                c_tie, c_obs, c_ase = st.columns(3)
                nuevo_tiempo, nueva_obs = c_tie.text_input("Tiempo Entrega (Días)"), c_obs.text_input("Observaciones")
                nuevo_asesor = c_ase.selectbox("Asesor", ASESORES_LISTA, index=ASESORES_LISTA.index(asesor_filtro) if asesor_filtro in ASESORES_LISTA else 0)
                st.caption("* Campos obligatorios para identificar el auto.")
                if st.form_submit_button("Agregar al Turnero"):
                    if nueva_patente and nuevo_vehiculo:
                        nuevo_ingreso = pd.DataFrame([{'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_inicio, 'Hora': '-', 'Vehiculo': nuevo_vehiculo.upper(), 'Patente': nueva_patente.upper(), 'Chasis': '', 'Asesor': nuevo_asesor, 'Precio': nuevo_precio, 'Paños': nuevo_panos, 'Observaciones': nueva_obs, 'Tiempo_Entrega': nuevo_tiempo, 'Cliente': nuevo_cliente, 'Seguro': nuevo_seguro.upper(), 'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False}])
                        st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, nuevo_ingreso], ignore_index=True)
                        st.success(f"Ingreso sin turno agregado con éxito."); time.sleep(0.5); st.rerun()
                    else: st.error("Por favor completa la Patente y el Vehículo.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- CAJA 1: INGRESOS ---
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
                    indices_a_borrar = []
                    if not edited_prog.empty:
                        for idx, row in edited_prog.iterrows(): st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                    if not edited_sin.empty:
                        for idx, row in edited_sin.iterrows():
                            if row.get('Eliminar', False): indices_a_borrar.append(idx)
                            else: st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                    if indices_a_borrar: st.session_state.memoria_turnos_v11.drop(indices_a_borrar, inplace=True)
                    st.success("Actualizado."); time.sleep(0.5); st.rerun() 

            st.write("#### 🏁 Turnos Completados (Ya tienen OR)")
            if not df_recibidos.empty:
                edited_recibidos = st.data_editor(df_recibidos[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Asesor', 'Recibido', 'Fotos', 'OR']], column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", disabled=True), "Recibido": st.column_config.CheckboxColumn("✅ Recibido"), "Fotos": st.column_config.CheckboxColumn("📸 Fotos"), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10)}, hide_index=True, use_container_width=True, key="editor_recibidos")
                if st.button("💾 Guardar Correcciones (Completados)"):
                    for idx, row in edited_recibidos.iterrows(): st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR']] = row[['Recibido', 'Fotos', 'OR']]
                    st.success("Correcciones aplicadas."); time.sleep(0.5); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- CAJA 2: SALIDAS ---
    with st.container(border=True):
        st.markdown("<h2 style='color: #1e7e34; margin-top: 0;'>📤 2. SALIDAS: Agenda de Entregas</h2>", unsafe_allow_html=True)
        st.write("Vehículos listos para entregar al cliente en las fechas seleccionadas.")
        
        if not df.empty:
            df_no_entregados = df[~df['Estado_Taller'].str.contains("ENTREGADO", na=False)].copy()
            df_no_entregados = df_no_entregados[~df_no_entregados['Patente'].isin(st.session_state.entregas_confirmadas)]
            df_no_entregados['Entregado_OK'] = False
            
            # FILTROS DE RANGO Y ASESOR
            entregas_rango = df_no_entregados[(df_no_entregados['Fecha_Promesa_Disp'] >= f_inicio) & (df_no_entregados['Fecha_Promesa_Disp'] <= f_fin)].copy()
            entregas_atrasadas = df_no_entregados[(df_no_entregados['Fecha_Promesa_Disp'].notna()) & (df_no_entregados['Fecha_Promesa_Disp'] < hoy)].copy()
            
            if asesor_filtro != "TODOS":
                entregas_rango = entregas_rango[entregas_rango['Asesor'] == asesor_filtro]
                entregas_atrasadas = entregas_atrasadas[entregas_atrasadas['Asesor'] == asesor_filtro]
            
            edit_rango_df = pd.DataFrame() 
            edit_atra = pd.DataFrame()
            
            # --- 1. ATRASADAS (ARRIBA, ANCHO COMPLETO) ---
            st.markdown("#### 🔴 Entregas Atrasadas (Vencidas)")
            if not entregas_atrasadas.empty:
                entregas_atrasadas = entregas_atrasadas.sort_values(by='Fecha_Promesa_Disp', ascending=True)
                entregas_atrasadas['Fecha Prom.'] = entregas_atrasadas['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y'))
                edit_atra = st.data_editor(
                    entregas_atrasadas[['Entregado_OK', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor', 'Grupo']], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Entregado_OK": st.column_config.CheckboxColumn("✅ Listo", default=False),
                        "Fecha Prom.": st.column_config.TextColumn("📅 Venció", disabled=True),
                        "Patente": st.column_config.TextColumn("Patente", disabled=True), 
                        "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True), 
                        "Asesor": st.column_config.TextColumn("Asesor", disabled=True), 
                        "Grupo": st.column_config.TextColumn("Grupo", disabled=True)
                    },
                    key="editor_entregas_atra"
                )
            else:
                st.success("¡Excelente! No hay vehículos con la fecha de entrega atrasada.")
                
            st.divider()
            
            # --- 2. PROGRAMADAS (ABAJO, EN COLUMNAS) ---
            if f_inicio == f_fin:
                titulo_rango = f"HOY ({f_inicio.strftime('%d/%m')})" if f_inicio == hoy else f"para el {f_inicio.strftime('%d/%m')}"
            else:
                titulo_rango = f"del {f_inicio.strftime('%d/%m')} al {f_fin.strftime('%d/%m')}"
                
            st.markdown(f"#### 🟢 Entregas Programadas {titulo_rango}")
            if not entregas_rango.empty:
                entregas_rango['Fecha Prom.'] = entregas_rango['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m') if pd.notna(x) else "")
                
                orden_grupos_maestro = ["GRUPO UNO", "GRUPO DOS", "GRUPO TRES", "PARABRISAS", "TERCEROS"]
                grupos_rango_unicos = [g for g in orden_grupos_maestro if g in entregas_rango['Grupo'].unique()]
                otros_grupos = [g for g in entregas_rango['Grupo'].unique() if pd.notna(g) and g not in orden_grupos_maestro]
                grupos_rango_unicos.extend(otros_grupos)
                
                # Crear dos columnas para mostrar los grupos uno al lado del otro
                cols_grupos = st.columns(2)
                
                for idx, grupo_val in enumerate(grupos_rango_unicos):
                    # Usamos el módulo para alternar entre columna izquierda (0) y derecha (1)
                    with cols_grupos[idx % 2]:
                        st.caption(f"📍 **{grupo_val}**")
                        df_g_rango = entregas_rango[entregas_rango['Grupo'] == grupo_val].sort_values(by=['Fecha_Promesa_Disp', 'Hora_Entrega'])
                        
                        edit_g = st.data_editor(
                            df_g_rango[['Entregado_OK', 'Fecha Prom.', 'Hora_Entrega', 'Patente', 'Vehiculo', 'Asesor']], 
                            hide_index=True, 
                            use_container_width=True,
                            column_config={
                                "Entregado_OK": st.column_config.CheckboxColumn("✅ Listo", default=False),
                                "Fecha Prom.": st.column_config.TextColumn("📅 Día", disabled=True),
                                "Hora_Entrega": st.column_config.TextColumn("⌚ Hora", disabled=True),
                                "Patente": st.column_config.TextColumn("Patente", disabled=True), 
                                "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True), 
                                "Asesor": st.column_config.TextColumn("Asesor", disabled=True)
                            },
                            key=f"editor_entregas_rango_{grupo_val.replace(' ', '_')}"
                        )
                        edit_rango_df = pd.concat([edit_rango_df, edit_g])
            else:
                st.info("No hay entregas pendientes para el rango y/o asesor seleccionado.")
                    
            if not edit_rango_df.empty or not edit_atra.empty:
                st.markdown("<br>", unsafe_allow_html=True) # Espacio antes del botón
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
        
        # --- 1. TERMÓMETRO ---
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

        # --- 2. TABLAS POR ESTADO ---
        st.markdown("## 📑 Listado de Vehículos en Taller (Prioridad por Fecha Promesa)")
        st.write("Se eliminó el tipo ABC. Columnas actuales: **Dominio, Vehículo y Asesor** para rápida identificación técnica.")
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
                        d_e['Fecha Prom.'] = d_e['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
                        
                        if m_key in ["TERM PEND", "ENTREGADO"]:
                            df_vista = d_e[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor', 'Paños']]
                        else:
                            df_vista = d_e[['Estado_Taller', 'Fase_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Asesor', 'Paños']]
                            
                        st.dataframe(df_vista, hide_index=True, use_container_width=True, key=f"{grupo_nombre}_{m_key}_{asesor_filtro_prog}_detalle")
                    else: st.caption(f"Sin vehículos en este estado.")
                    
            dibujar_tabla(col1, "GRUPO UNO", match)
            dibujar_tabla(col2, "GRUPO DOS", match)
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.divider()

        # --- 3. KANBAN ---
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
                            # Lógica de colores basada en FECHA PROMESA
                            f_prom = row.get('Fecha_Promesa_Disp')
                            
                            if fase == "⛔ DETENIDOS":
                                color_borde = "#6c757d" # Gris
                                circulo = "⚪"
                                texto_fecha = "Detenido"
                            else:
                                if pd.isna(f_prom) or not f_prom:
                                    color_borde = "#17a2b8" # Celeste
                                    circulo = "🔵"
                                    texto_fecha = "Sin fecha"
                                elif f_prom < hoy_kanban:
                                    color_borde = "#dc3545" # Rojo (Atrasado)
                                    circulo = "🔴"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                elif f_prom == hoy_kanban:
                                    color_borde = "#ffc107" # Amarillo (Hoy)
                                    circulo = "🟡"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                else:
                                    color_borde = "#28a745" # Verde (A tiempo)
                                    circulo = "🟢"
                                    texto_fecha = f_prom.strftime('%d/%m')
                                    
                            asesor_corto = row['Asesor'].split()[0] if row['Asesor'] else "N/A"
                            
                            # Mostrar novedades si está detenido
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
        
        # --- 4. ABC TOYOTA ---
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
        def clasificar_estado(x):
            if x == 'FAC': return 'Facturado (FAC)'
            elif x == 'SI': return 'Aprobado (SI)'
            else: return 'En Taller (Otros)'
        df_analisis['Estado_Resumen'] = df_analisis['Estado_Fac'].apply(clasificar_estado)

        df_fac = df_analisis[df_analisis['Estado_Resumen'] == 'Facturado (FAC)']
        df_si = df_analisis[df_analisis['Estado_Resumen'] == 'Aprobado (SI)']
        
        pesos_fac, panos_fac = df_fac['Precio'].sum(), df_fac['Paños'].sum()
        pesos_si, panos_si = df_si['Precio'].sum(), df_si['Paños'].sum()
        pesos_est, panos_est = pesos_fac + pesos_si, panos_fac + panos_si
        
        porcentaje_logro = min((panos_est / OBJETIVO_MENSUAL_PANOS) * 100 if OBJETIVO_MENSUAL_PANOS > 0 else 0, 100)
        
        dias_restantes = dias_habiles_restantes_mes()
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
        c_r1.markdown(f'<div class="metric-card"><div class="metric-title">Facturado Actual (FAC)</div><div class="metric-value-money">${pesos_fac:,.0f}</div><div class="metric-subtitle-gray" style="font-size: 1.1rem; margin-top: 8px;">📦 {panos_fac:.1f} paños</div></div>', unsafe_allow_html=True)
        c_r2.markdown(f'<div class="metric-card"><div class="metric-title">Aprobado (SI)</div><div class="metric-value-money" style="color:#28a745;">${pesos_si:,.0f}</div><div class="metric-subtitle-green" style="font-size: 1.1rem; margin-top: 8px;">📦 {panos_si:.1f} paños</div></div>', unsafe_allow_html=True)
        c_r3.markdown(f'<div class="metric-card" style="border: 2px solid #00235d; background-color: #f8f9fa;"><div class="metric-title" style="color:#00235d;">Estimado a Cierre de Mes</div><div class="metric-value-money" style="color:#00235d;">${pesos_est:,.0f}</div><div class="metric-subtitle-gray" style="font-size: 1.1rem; color:#00235d; font-weight: bold; margin-top: 8px;">📦 {panos_est:.1f} paños totales</div></div>', unsafe_allow_html=True)
        st.divider()
        
        df_tpf = df[df['Estado_Taller'].str.contains("TERM PEND FACT", na=False)]
        df_tpe = df[df['Estado_Taller'].str.contains("TERM PEND ENTREG", na=False)]
        df_epf = df[df['Estado_Taller'].str.contains("ENTREGADO PEND FACT", na=False)]

        st.write("### 🚨 Detalle de Estados Pendientes (Plata Inmovilizada)")
        c_e1, c_e2, c_e3 = st.columns(3)
        c_e1.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Facturar</div><div class="metric-value-money">${df_tpf["Precio"].sum():,.0f}</div><div class="metric-subtitle-red">⚠️ {df_tpf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e2.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Entregar</div><div class="metric-value-money">${df_tpe["Precio"].sum():,.0f}</div><div class="metric-subtitle-blue">⏳ {df_tpe["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e3.markdown(f'<div class="metric-card"><div class="metric-title">Entregado Pend. Facturar</div><div class="metric-value-money">${df_epf["Precio"].sum():,.0f}</div><div class="metric-subtitle-green">🚚 {df_epf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
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

        with tab_grupos:
            tabla_grupo = crear_tabla_resumen(df_analisis, 'Grupo')
            df_g_panos_chart = tabla_grupo.reset_index()[['Grupo', '📦 FAC', '📦 SI', '📦 EST. CIERRE (FAC+SI)']].melt(id_vars='Grupo', var_name='Métrica', value_name='Paños')
            df_g_panos_chart['Métrica'] = df_g_panos_chart['Métrica'].replace({'📦 FAC': 'Facturado', '📦 SI': 'Aprobado (SI)', '📦 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})
            df_g_pesos_chart = tabla_grupo.reset_index()[['Grupo', '💰 FAC', '💰 SI', '💰 EST. CIERRE (FAC+SI)']].melt(id_vars='Grupo', var_name='Métrica', value_name='Precio')
            df_g_pesos_chart['Métrica'] = df_g_pesos_chart['Métrica'].replace({'💰 FAC': 'Facturado', '💰 SI': 'Aprobado (SI)', '💰 EST. CIERRE (FAC+SI)': 'Proyección al Cierre'})

            col_g_g1, col_g_g2 = st.columns(2)
            with col_g_g1:
                fig_g_panos = px.bar(df_g_panos_chart, x='Grupo', y='Paños', color='Métrica', barmode='group', text_auto='.1f', title='📦 Paños Totales (Escalera al Cierre)', color_discrete_map=colores_grafico)
                fig_g_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_g_panos, use_container_width=True)
            with col_g_g2:
                fig_g_pesos = px.bar(df_g_pesos_chart, x='Grupo', y='Precio', color='Métrica', barmode='group', text_auto='$.2s', title='💰 Montos en Pesos (Escalera al Cierre)', color_discrete_map=colores_grafico)
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

            st.dataframe(tabla_grupo.style.format({
                '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
            }), use_container_width=True)

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
                fig_a_panos = px.bar(df_a_panos_chart, x='Asesor', y='Paños', color='Métrica', barmode='group', text_auto='.1f', title='📦 Paños por Asesor (Escalera al Cierre)', color_discrete_map=colores_grafico)
                fig_a_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), legend_title_text='')
                st.plotly_chart(fig_a_panos, use_container_width=True)
            with col_a_g2:
                fig_a_pesos = px.bar(df_a_pesos_chart, x='Asesor', y='Precio', color='Métrica', barmode='group', text_auto='$.2s', title='💰 Montos por Asesor (Escalera al Cierre)', color_discrete_map=colores_grafico)
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

            st.dataframe(tabla_asesor.style.format({
                '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
            }), use_container_width=True)

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
                st.dataframe(tabla_empresa.style.format({
                    '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                    '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
                }), use_container_width=True)
            with col_e2:
                df_cierre = df_analisis[df_analisis['Estado_Resumen'].isin(['Facturado (FAC)', 'Aprobado (SI)'])]
                if not df_cierre.empty:
                    res_empresa_pie = df_cierre.groupby('Cliente')[['Precio']].sum().reset_index()
                    st.plotly_chart(px.pie(res_empresa_pie, values='Precio', names='Cliente', hole=0.4, title="Participación en el Cierre Estimado ($)"), use_container_width=True)

# ==========================================
# PESTAÑA 5: KPIs
# ==========================================
with tab_kpi:
    if not df.empty:
        st.subheader("Indicadores Clave de Desempeño (KPI)")
        k1, k2, k3 = st.columns(3)
        df_fac_kpi = df[df['Estado_Fac'] == 'FAC']
        ticket = df_fac_kpi['Precio'].mean() if not df_fac_kpi.empty else 0
        k1.metric("Ticket Promedio (FAC)", f"$ {ticket:,.0f}")
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
    if not df.empty:
        st.subheader("📅 Histórico Mensual")
        df_hist = df[df['Mes_Hist'] != 'SIN FECHA'].sort_values('Mes_Hist')
        if not df_hist.empty:
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                pivot_panos = pd.pivot_table(df_hist, values='Paños', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_panos.style.format("{:.1f}"), use_container_width=True)
            with c_h2:
                pivot_pesos = pd.pivot_table(df_hist, values='Precio', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_pesos.style.format("$ {:,.0f}"), use_container_width=True)
            st.divider()
            st.plotly_chart(px.bar(df_hist, x="Mes_Hist", y="Paños", color="Cliente", barmode="group", title="Paños Facturados/Proyectados por Mes"), use_container_width=True)
        else: st.info("No hay datos con fechas válidas para mostrar el historial.")
