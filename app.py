import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import re
import time

st.set_page_config(page_title="Gestión Taller CENOA - Jujuy", layout="wide")

# --- ESTILOS CSS INYECTADOS (FORMATO TARJETAS) ---
st.markdown("""<style>
    .metric-card { 
        background-color: white; 
        border: 1px solid #dee2e6; 
        padding: 15px; 
        border-radius: 8px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        text-align: center; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
        min-height: 110px; 
        margin-bottom: 15px;
    }
    .metric-title { color: #666; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; }
    .metric-value-money { color: #00235d; font-size: 1.8rem; font-weight: bold; margin: 0; }
    .metric-value-number { color: #00235d; font-size: 1.5rem; font-weight: bold; margin: 0; }
    .metric-subtitle-red { color: #dc3545; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-green { color: #28a745; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-blue { color: #17a2b8; font-size: 0.95rem; font-weight: bold; margin-top: 5px; }
    .metric-subtitle-gray { color: #888; font-size: 0.8rem; margin-top: 5px; }
    .kanban-col { background-color: #f8f9fa; border-radius: 8px; padding: 10px; border: 1px solid #e9ecef; }
</style>""", unsafe_allow_html=True)

# --- ENCABEZADO Y BOTÓN DE ACTUALIZACIÓN ---
col_tit, col_btn = st.columns([3, 1])
with col_tit:
    st.title("🚀 Sistema de Gestión Taller CENOA - Jujuy")
with col_btn:
    st.write("") 
    if st.button("🔄 Forzar Actualización desde Excel", use_container_width=True):
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        time.sleep(0.5)
        st.rerun()

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
    if pd.isna(texto) or str(texto).strip() == "": return None 
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

def clasificar_abc(panos):
    if panos <= 3: return 'A (1-3 paños)'
    elif panos <= 7: return 'B (4-7 paños)'
    else: return 'C (8+ paños)'

@st.cache_data(ttl=300)
def obtener_turnos():
    columnas_base = ['Tipo', 'Fecha', 'Hora', 'Vehiculo', 'Patente', 'Asesor', 'Precio', 'Paños', 'Observaciones', 'Tiempo_Entrega', 'Cliente', 'Seguro', 'Recibido', 'Fotos', 'Cancelado', 'OR', 'Eliminar']
    if GID_TURNOS == "PONER_AQUI_GID_TURNOS": return pd.DataFrame(columns=columnas_base)
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
            if fecha_turno is None: fecha_turno = datetime.now()
            asesor_raw = str(row.get('ASESOR', 'SIN ASIGNAR')).strip().upper()
            if asesor_raw not in ASESORES_LISTA: asesor_raw = "SIN ASIGNAR"
            col_tiempo = next((c for c in d.columns if 'TIEMPO' in c), None)
            filas.append({
                'Tipo': '📅 PROGRAMADO', 'Fecha': fecha_turno.date(), 'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(), 'Patente': str(row.get('PATENTE', '')).upper(),
                'Asesor': asesor_raw, 'Precio': str(row.get('PRECIO', '')).strip(), 'Paños': str(row.get('PAÑOS', '')).strip(),
                'Observaciones': str(row.get('OBSERVACIONES', '')).strip(), 'Tiempo_Entrega': str(row.get(col_tiempo, '')) if col_tiempo else "",
                'Cliente': str(row.get('CLIENTE', '')).upper(), 'Seguro': str(row.get('SEGURO', '')).upper(),
                'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
            })
        return pd.DataFrame(filas)
    except Exception as e: return pd.DataFrame(columns=columnas_base)

@st.cache_data(ttl=300)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            
            cols = list(d.columns)
            while len(cols) < 22:
                cols.append(f"VACIA_{len(cols)}")
                
            if len(cols) > 21: cols[21] = 'ESTADO_FAC'            # Columna V
            if len(cols) > 20: cols[20] = 'FASE_TALLER'           # Columna U
            if len(cols) > 19: cols[19] = 'ESTADO_TALLER'         # Columna T
            if len(cols) > 15: cols[15] = 'EMPRESA_TALLER'        # Columna P
            if len(cols) > 11: cols[11] = 'OBSERVACIONES_TALLER'  # Columna L
            if len(cols) > 8: cols[8] = 'FECHA_PROMESA_I'         # Columna I
            if len(cols) > 7: cols[7] = 'FECHA_TICKET'            # Columna H
            if len(cols) > 6: cols[6] = 'DIAS_TRABAJO'            # Columna G (Nueva: Días de reparación)
            if len(cols) > 0: cols[0] = 'FECHA_INGRESO_TALLER'    # Columna A
            d.columns = cols
            
            d.columns = d.columns.str.strip().str.upper()
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE']); d = d[d['PATENTE'].str.strip() != ""]; d['GRUPO_ORIGEN'] = n; dfs.append(d)
        except: pass
    if not dfs: return pd.DataFrame()
    df_raw = pd.concat(dfs, ignore_index=True)
    filas = []
    for _, row in df_raw.iterrows():
        f_fin = parsear_fecha_español(row.get('FECHA_PROMESA_I', ''))
        fecha_promesa_display = f_fin.date() if f_fin is not None else None
        if f_fin is None: f_fin = datetime.now() + timedelta(days=3650)
        mes_hist = f_fin.strftime('%Y-%m') if f_fin and f_fin.year < 2030 else "SIN FECHA"
        
        f_ingreso = parsear_fecha_español(row.get('FECHA_INGRESO_TALLER', ''))
        fecha_ingreso_disp = f_ingreso.date() if f_ingreso is not None else None
        
        f_ticket = parsear_fecha_español(row.get('FECHA_TICKET', ''))
        fecha_ticket_disp = f_ticket.date() if f_ticket is not None else None
        
        try:
            texto_panos = str(row.get('PAÑOS', '0')).replace(',', '.')
            if texto_panos.lower() == 'nan' or texto_panos.strip() == '': texto_panos = '0'
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            panos = float(numeros[0]) if numeros else 0.0
        except: panos = 0.0
        
        # LECTURA DE COLUMNA G (DÍAS DE TRABAJO)
        try:
            texto_dias = str(row.get('DIAS_TRABAJO', '0')).replace(',', '.')
            if texto_dias.lower() == 'nan' or texto_dias.strip() == '' or 'VACIA' in texto_dias: texto_dias = '0'
            nums_dias = re.findall(r"[-+]?\d*\.\d+|\d+", texto_dias)
            dias_reparacion = float(nums_dias[0]) if nums_dias else 0.0
        except: dias_reparacion = 0.0

        f_inicio = f_fin - timedelta(days=max(1, int(panos)))
        
        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: precio_val = float(precio_raw) if precio_raw != "" else 0.0
        except: precio_val = 0.0
        
        estado_taller = str(row.get('ESTADO_TALLER', '')).replace('nan', '').strip().upper()
        if not estado_taller: estado_taller = "SIN ESTADO"
        
        cliente_val = str(row.get('EMPRESA_TALLER', 'PARTICULAR')).replace('nan', '').strip().upper()
        if not cliente_val: cliente_val = "PARTICULAR"
        
        obs_val = str(row.get('OBSERVACIONES_TALLER', '')).replace('nan', '').strip()

        asesor_val = str(row.get('ASESOR', '')).strip().upper()
        if asesor_val == 'NAN' or asesor_val == '': asesor_val = "SIN ASIGNAR"

        fase_taller_val = str(row.get('FASE_TALLER', '')).replace('nan', '').strip().upper()
        if not fase_taller_val or fase_taller_val == 'VACIA_20': fase_taller_val = "SIN FASE ASIGNADA"

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'), 'Asesor': asesor_val, 'Cliente': cliente_val,
            'Patente': str(row.get('PATENTE', '')), 'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio, 'Fin': f_fin, 'Fecha_Promesa_Disp': fecha_promesa_display, 
            'Fecha_Ingreso': fecha_ingreso_disp, 'Fecha_Ticket': fecha_ticket_disp,
            'Mes_Hist': mes_hist, 'Paños': panos, 'Dias_Reparacion': dias_reparacion, 'Tipo_ABC': clasificar_abc(panos),
            'Estado_Fac': str(row.get('ESTADO_FAC', '')).strip().upper(), 
            'Estado_Taller': estado_taller, 'Fase_Taller': fase_taller_val, 
            'Precio': precio_val, 'Observaciones': obs_val
        })
    return pd.DataFrame(filas)

if 'memoria_turnos_v11' not in st.session_state:
    st.session_state.memoria_turnos_v11 = obtener_turnos()

df = obtener_datos_maestros()

tab_turnos, tab_prog, tab_portal, tab_fac, tab_kpi, tab_hist = st.tabs([
    "📋 Turnero Diario", 
    "🛠️ Programación y Kanban", 
    "🏢 PORTAL EMPRESAS (Externo)", 
    "💰 Facturación y Objetivos", 
    "📊 KPIs", 
    "📅 Históricos"
])

# ==========================================
# PESTAÑA 1: TURNERO DIARIO 
# ==========================================
with tab_turnos:
    st.subheader("Recepción de Vehículos")
    col_fecha, col_asesor, col_add = st.columns([1, 1, 2])
    with col_fecha:
        hoy = datetime.today().date()
        fechas_seleccionadas = st.date_input("📅 Rango de Fechas", value=(hoy, hoy), format="DD/MM/YYYY")
        if isinstance(fechas_seleccionadas, tuple):
            if len(fechas_seleccionadas) == 2: f_inicio, f_fin = fechas_seleccionadas
            else: f_inicio = f_fin = fechas_seleccionadas[0]
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
                idx_asesor = ASESORES_LISTA.index(asesor_filtro) if asesor_filtro in ASESORES_LISTA else 0
                nuevo_asesor = c_ase.selectbox("Asesor", ASESORES_LISTA, index=idx_asesor)
                st.caption("* Campos obligatorios para identificar el auto.")
                if st.form_submit_button("Agregar al Turnero"):
                    if nueva_patente and nuevo_vehiculo:
                        nuevo_ingreso = pd.DataFrame([{
                            'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_inicio, 'Hora': '-', 'Vehiculo': nuevo_vehiculo.upper(), 'Patente': nueva_patente.upper(),
                            'Asesor': nuevo_asesor, 'Precio': nuevo_precio, 'Paños': nuevo_panos, 'Observaciones': nueva_obs, 'Tiempo_Entrega': nuevo_tiempo,
                            'Cliente': nuevo_cliente, 'Seguro': nuevo_seguro.upper(), 'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
                        }])
                        st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, nuevo_ingreso], ignore_index=True)
                        st.success(f"Ingreso sin turno agregado con éxito."); time.sleep(0.5); st.rerun()
                    else: st.error("Por favor completa la Patente y el Vehículo.")

    st.divider()
    mask = (st.session_state.memoria_turnos_v11['Fecha'] >= f_inicio) & (st.session_state.memoria_turnos_v11['Fecha'] <= f_fin)
    df_rango = st.session_state.memoria_turnos_v11[mask].copy()
    if asesor_filtro != "TODOS": df_rango = df_rango[df_rango['Asesor'] == asesor_filtro]

    if df_rango.empty: st.info("No hay turnos para los filtros seleccionados.")
    else:
        df_rango['OR'] = df_rango['OR'].fillna("")
        df_cancelados = df_rango[df_rango['Cancelado'] == True]
        df_activos = df_rango[df_rango['Cancelado'] == False]
        mascara_recibidos = (df_activos['OR'].str.strip() != "") & (df_activos['Recibido'] == True) & (df_activos['Fotos'] == True)
        df_pendientes = df_activos[~mascara_recibidos].sort_values(['Fecha', 'Hora', 'Asesor'])
        df_recibidos = df_activos[mascara_recibidos].sort_values(['Fecha', 'Hora', 'Asesor'])

        st.write("### ⏱️ Turnos Pendientes")
        if not df_pendientes.empty:
            df_prog = df_pendientes[df_pendientes['Tipo'] == '📅 PROGRAMADO']
            df_sin = df_pendientes[df_pendientes['Tipo'] == '🚶‍♂️ SIN TURNO']
            edited_prog, edited_sin = pd.DataFrame(), pd.DataFrame()
            if not df_prog.empty:
                st.write("#### 📅 Programados")
                edited_prog = st.data_editor(df_prog[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']],
                    column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"), "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA), "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False), "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10), "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False)}, hide_index=True, use_container_width=True, key="editor_prog")
            if not df_sin.empty:
                st.write("#### 🚶‍♂️ Ingresos Adicionales (Sin Turno)")
                edited_sin = st.data_editor(df_sin[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado', 'Eliminar']],
                    column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"), "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA), "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False), "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10), "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False), "Eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False)}, hide_index=True, use_container_width=True, key="editor_sin")

            if st.button("💾 Guardar Cambios en Pendientes"):
                indices_a_borrar = []
                if not edited_prog.empty:
                    for idx, row in edited_prog.iterrows(): st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                if not edited_sin.empty:
                    for idx, row in edited_sin.iterrows():
                        if row.get('Eliminar', False): indices_a_borrar.append(idx)
                        else: st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                if indices_a_borrar: st.session_state.memoria_turnos_v11.drop(indices_a_borrar, inplace=True)
                st.success("Actualizado."); time.sleep(0.5); st.rerun() 

        st.divider()
        st.write("### 🏁 Turnos Recibidos (Con OR Abierta)")
        if not df_recibidos.empty:
            edited_recibidos = st.data_editor(df_recibidos[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Asesor', 'Recibido', 'Fotos', 'OR']],
                column_config={"Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", disabled=True), "Recibido": st.column_config.CheckboxColumn("✅ Recibido"), "Fotos": st.column_config.CheckboxColumn("📸 Fotos"), "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10)}, hide_index=True, use_container_width=True, key="editor_recibidos")
            if st.button("💾 Guardar Correcciones"):
                for idx, row in edited_recibidos.iterrows(): st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR']] = row[['Recibido', 'Fotos', 'OR']]
                st.success("Correcciones aplicadas."); time.sleep(0.5); st.rerun()

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN Y KANBAN
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación y Flujo de Trabajo (Kanban)")
    if not df.empty:
        col_filtro, _ = st.columns([1, 2])
        with col_filtro: asesor_filtro_prog = st.selectbox("👔 Filtrar por Asesor", ["TODOS"] + ASESORES_LISTA, key="filtro_asesor_prog")
            
        df_prog_filtrado = df.copy()
        if asesor_filtro_prog != "TODOS":
            nombre_corto = asesor_filtro_prog.split()[0].upper()
            df_prog_filtrado = df_prog_filtrado[df_prog_filtrado['Asesor'].str.contains(nombre_corto, case=False, na=False)]

        df_en_proceso = df_prog_filtrado[df_prog_filtrado['Estado_Taller'].str.contains("PROCESO", na=False)]
        
        # --- NUEVA SECCIÓN: TERMÓMETRO DE CAPACIDAD ---
        st.markdown("### 🚥 Termómetro de Capacidad y Asignación")
        st.write("Calcula la saturación actual sumando los días de trabajo pendientes de los vehículos EN PROCESO. Usá esto para decidir a qué grupo asignarle el próximo auto.")
        
        if not df_en_proceso.empty:
            resumen_capacidad = df_en_proceso.groupby('Grupo').agg(
                Autos=('Patente', 'count'),
                Panos_Activos=('Paños', 'sum'),
                Dias_Acumulados=('Dias_Reparacion', 'sum')
            ).reset_index()
            
            cols_cap = st.columns(len(resumen_capacidad))
            for i, row in resumen_capacidad.iterrows():
                with cols_cap[i]:
                    color_dias = "#28a745" if row['Dias_Acumulados'] < 20 else "#ffc107" if row['Dias_Acumulados'] < 40 else "#dc3545"
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        <h4 style='color: #00235d; margin-top: 0;'>{row['Grupo']}</h4>
                        <h1 style='color: {color_dias}; margin: 10px 0;'>{row['Dias_Acumulados']:.1f} días</h1>
                        <p style='color: #6c757d; margin-bottom: 0;'>Carga total estimada</p>
                        <hr style='margin: 10px 0;'>
                        <div style='display: flex; justify-content: space-around;'>
                            <span style='font-size: 0.9em;'>🚗 {row['Autos']} autos</span>
                            <span style='font-size: 0.9em;'>📦 {row['Panos_Activos']:.1f} paños</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No hay vehículos en proceso para calcular capacidad.")

        st.divider()

        st.markdown("### 📋 Tablero Kanban de Producción (Reemplazo Fichines)")
        st.write("Acá vas a ver los vehículos moviéndose según la columna 'Fase Taller' del Excel.")
        
        fases_detectadas = sorted(list(df_en_proceso['Fase_Taller'].unique()))
        if "SIN FASE ASIGNADA" not in fases_detectadas: fases_detectadas.append("SIN FASE ASIGNADA")
        
        cols_kanban = st.columns(len(fases_detectadas))
        for idx, fase in enumerate(fases_detectadas):
            with cols_kanban[idx]:
                st.markdown(f"<div class='kanban-col'><h4 style='text-align:center; color:#00235d;'>{fase}</h4></div>", unsafe_allow_html=True)
                df_fase = df_en_proceso[df_en_proceso['Fase_Taller'] == fase]
                if not df_fase.empty:
                    for _, row in df_fase.iterrows():
                        color_tipo = "#28a745" if "A" in row['Tipo_ABC'] else "#ffc107" if "B" in row['Tipo_ABC'] else "#dc3545"
                        st.markdown(f"""
                        <div style='background: white; padding: 10px; margin-top: 10px; border-radius: 5px; border-left: 5px solid {color_tipo}; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);'>
                            <strong>{row['Patente']}</strong> - {row['Vehiculo'][:15]}<br>
                            <span style='font-size: 0.8em; color: gray;'>📦 {row['Paños']} paños | ⏱️ {row['Dias_Reparacion']} Días</span><br>
                            <span style='font-size: 0.8em; color: #00235d;'>{row['Tipo_ABC']} - Grupo: {row['Grupo']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("Vacío")

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
        st.write("Vista exclusiva para que los responsables de AUTOSOL, AUTOLUX y CIEL puedan ver el estado de sus vehículos, fechas de entrega y observaciones.")
        
        df_grupo = df[df['Cliente'].str.contains('SOL|LUX|CIEL', case=False, na=False)].copy()
        
        if not df_grupo.empty:
            c_filtro, _ = st.columns([1, 2])
            with c_filtro:
                empresa_filtro = st.selectbox("Seleccionar Empresa", ["TODAS", "AUTOSOL", "AUTOLUX", "CIEL / AUTOCIEL"])
            
            df_vista_emp = df_grupo.copy()
            if empresa_filtro == "AUTOSOL": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('SOL', case=False, na=False)]
            elif empresa_filtro == "AUTOLUX": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('LUX', case=False, na=False)]
            elif empresa_filtro == "CIEL / AUTOCIEL": df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('CIEL', case=False, na=False)]
            
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

            vista_columnas = [
                'Cliente', 'Vehiculo', 'Patente', 'Fecha Ingreso', 'Fecha Ticket', 'Estado_Taller', 
                'Fecha Entrega', 'Asesor', 'Fecha Ingreso Concesionario', 'Asesor Concesionario', 'Observaciones'
            ]
            
            mask_entregados = df_vista_emp['Estado_Taller'].str.contains('ENTREGADO', na=False)
            df_pendientes = df_vista_emp[~mask_entregados][vista_columnas].rename(columns={'Estado_Taller': 'Estado Actual'})
            df_entregados = df_vista_emp[mask_entregados][vista_columnas].rename(columns={'Estado_Taller': 'Estado Actual'})
            
            st.write("#### ⏳ Vehículos en Taller (Pendientes de Entrega)")
            edited_pendientes = st.data_editor(
                df_pendientes, hide_index=True, use_container_width=True,
                column_config={
                    "Cliente": st.column_config.TextColumn("Cliente", disabled=True), "Vehiculo": st.column_config.TextColumn("Vehículo", disabled=True),
                    "Patente": st.column_config.TextColumn("Patente", disabled=True), "Fecha Ingreso": st.column_config.TextColumn("Ingreso Taller", disabled=True),
                    "Fecha Ticket": st.column_config.TextColumn("1ra Fecha Prom.", disabled=True), "Estado Actual": st.column_config.TextColumn("Estado Actual", disabled=True),
                    "Fecha Entrega": st.column_config.TextColumn("Fecha Entrega", disabled=True), "Asesor": st.column_config.TextColumn("Asesor Taller", disabled=True),
                    "Fecha Ingreso Concesionario": st.column_config.DateColumn("🗓️ Ingreso Conces.", format="DD/MM/YYYY"),
                    "Asesor Concesionario": st.column_config.TextColumn("👤 Asesor Conces."), "Observaciones": st.column_config.TextColumn("📝 Observaciones (Doble Clic)", width="large", max_chars=1000)
                }, key="editor_observaciones_pendientes"
            )

            st.write("#### 🚚 Vehículos Entregados (Historial Reciente)")
            st.dataframe(df_entregados, hide_index=True, use_container_width=True, column_config={"Observaciones": st.column_config.TextColumn("Observaciones", width="large")})
        else: st.info("No hay vehículos registrados para las empresas del grupo en este momento.")

# ==========================================
# PESTAÑA 4: FACTURACIÓN Y OBJETIVOS
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación, Paños y Objetivos")
        
        OBJETIVO_MENSUAL_PANOS = 505.0
        
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
        
        pesos_est = pesos_fac + pesos_si
        panos_est = panos_fac + panos_si
        
        porcentaje_logro = min((panos_est / OBJETIVO_MENSUAL_PANOS) * 100 if OBJETIVO_MENSUAL_PANOS > 0 else 0, 100)
        
        st.markdown("### 🎯 Control de Objetivo Mensual")
        c_obj1, c_obj2 = st.columns([3, 1])
        with c_obj1:
            st.progress(int(porcentaje_logro))
            st.caption(f"**Progreso del Mes:** {panos_est:.1f} paños asegurados de un objetivo de {OBJETIVO_MENSUAL_PANOS} paños.")
        with c_obj2:
            st.markdown(f"<h3 style='text-align: right; color: {'#28a745' if porcentaje_logro >= 95 else '#ffc107' if porcentaje_logro >= 75 else '#dc3545'}; margin-top: 0;'>{porcentaje_logro:.1f}%</h3>", unsafe_allow_html=True)
            
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
            return df_res.sort_values(by='📦 EST. CIERRE (FAC+SI)', ascending=False)

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

            st.write("#### 🥧 Porcentaje de Participación (Cierre Estimado)")
            col_g_p1, col_g_p2 = st.columns(2)
            df_pie_g = tabla_grupo.reset_index()
            with col_g_p1:
                df_panos_pie = df_pie_g[df_pie_g['📦 EST. CIERRE (FAC+SI)'] > 0]
                if not df_panos_pie.empty:
                    fig_pie_g_panos = px.pie(df_panos_pie, values='📦 EST. CIERRE (FAC+SI)', names='Grupo', hole=0.4, title='Distribución de Paños Totales')
                    st.plotly_chart(fig_pie_g_panos, use_container_width=True)
            with col_g_p2:
                df_pesos_pie = df_pie_g[df_pie_g['💰 EST. CIERRE (FAC+SI)'] > 0]
                if not df_pesos_pie.empty:
                    fig_pie_g_pesos = px.pie(df_pesos_pie, values='💰 EST. CIERRE (FAC+SI)', names='Grupo', hole=0.4, title='Distribución de Ingresos Totales ($)')
                    st.plotly_chart(fig_pie_g_pesos, use_container_width=True)

            st.dataframe(tabla_grupo.style.format({
                '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
            }), use_container_width=True)

        with tab_asesores:
            df_asesores_limpio = df_analisis[df_analisis['Asesor'] != 'SIN ASIGNAR'].copy()
            tabla_asesor = crear_tabla_resumen(df_asesores_limpio, 'Asesor')
            
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

            st.write("#### 🥧 Porcentaje de Participación (Cierre Estimado)")
            col_a_p1, col_a_p2 = st.columns(2)
            df_pie_a = tabla_asesor.reset_index()
            with col_a_p1:
                df_panos_pie_a = df_pie_a[df_pie_a['📦 EST. CIERRE (FAC+SI)'] > 0]
                if not df_panos_pie_a.empty:
                    fig_pie_a_panos = px.pie(df_panos_pie_a, values='📦 EST. CIERRE (FAC+SI)', names='Asesor', hole=0.4, title='Distribución de Paños Totales')
                    st.plotly_chart(fig_pie_a_panos, use_container_width=True)
            with col_a_p2:
                df_pesos_pie_a = df_pie_a[df_pie_a['💰 EST. CIERRE (FAC+SI)'] > 0]
                if not df_pesos_pie_a.empty:
                    fig_pie_a_pesos = px.pie(df_pesos_pie_a, values='💰 EST. CIERRE (FAC+SI)', names='Asesor', hole=0.4, title='Distribución de Ingresos Totales ($)')
                    st.plotly_chart(fig_pie_a_pesos, use_container_width=True)

            st.dataframe(tabla_asesor.style.format({
                '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
            }), use_container_width=True)

        with tab_empresas:
            col_e1, col_e2 = st.columns([1.5, 1])
            with col_e1:
                tabla_empresa = crear_tabla_resumen(df_analisis, 'Cliente')
                st.dataframe(tabla_empresa.style.format({
                    '📦 FAC': '{:.1f}', '📦 SI': '{:.1f}', '📦 EST. CIERRE (FAC+SI)': '{:.1f}', '📦 OTROS (En Taller)': '{:.1f}',
                    '💰 FAC': '${:,.0f}', '💰 SI': '${:,.0f}', '💰 EST. CIERRE (FAC+SI)': '${:,.0f}', '💰 OTROS (En Taller)': '${:,.0f}'
                }), use_container_width=True)
            with col_e2:
                df_cierre = df_analisis[df_analisis['Estado_Resumen'].isin(['Facturado (FAC)', 'Aprobado (SI)'])]
                if not df_cierre.empty:
                    res_empresa_pie = df_cierre.groupby('Cliente')[['Precio']].sum().reset_index()
                    fig_empresa = px.pie(res_empresa_pie, values='Precio', names='Cliente', hole=0.4, title="Participación en el Cierre Estimado ($)")
                    st.plotly_chart(fig_empresa, use_container_width=True)

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
        fig_asesor_kpi = px.bar(df_kpi_asesores, x="Asesor", color="Estado_Fac", barmode="group")
        st.plotly_chart(fig_asesor_kpi, use_container_width=True)

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
            fig_hist = px.bar(df_hist, x="Mes_Hist", y="Paños", color="Cliente", barmode="group", title="Paños Facturados/Proyectados por Mes")
            st.plotly_chart(fig_hist, use_container_width=True)
        else: st.info("No hay datos con fechas válidas para mostrar el historial.")
