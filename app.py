import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import re
import time

st.set_page_config(page_title="Gestión Taller CENOA", layout="wide")

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
</style>""", unsafe_allow_html=True)

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

@st.cache_data(ttl=60)
def obtener_datos_maestros():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            
            # FORZAMOS LA LECTURA ESTRICTA DE LAS COLUMNAS POR SU POSICIÓN
            cols = list(d.columns)
            if len(cols) > 19: cols[19] = 'ESTADO_TALLER'
            if len(cols) > 15: cols[15] = 'EMPRESA_TALLER'        # Columna P
            if len(cols) > 11: cols[11] = 'OBSERVACIONES_TALLER'  # Columna L
            if len(cols) > 8: cols[8] = 'FECHA_PROMESA_I'         # Columna I
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
        
        # Leemos forzosamente la Empresa (Columna P)
        cliente_val = str(row.get('EMPRESA_TALLER', 'PARTICULAR')).replace('nan', '').strip().upper()
        if not cliente_val: cliente_val = "PARTICULAR"
        
        # Leemos forzosamente las Observaciones (Columna L)
        obs_val = str(row.get('OBSERVACIONES_TALLER', '')).replace('nan', '').strip()

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'), 'Asesor': str(row.get('ASESOR', 'SIN ASESOR')).strip().upper(),
            'Cliente': cliente_val, 'Patente': str(row.get('PATENTE', '')), 'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio, 'Fin': f_fin, 'Fecha_Promesa_Disp': fecha_promesa_display, 'Mes_Hist': mes_hist,
            'Paños': panos, 'Estado_Fac': str(row.get('FAC', '')).strip().upper(), 'Estado_Taller': estado_taller, 
            'Precio': precio_val, 'Observaciones': obs_val
        })
    return pd.DataFrame(filas)

if 'memoria_turnos_v11' not in st.session_state:
    st.session_state.memoria_turnos_v11 = obtener_turnos()

df = obtener_datos_maestros()

# AGREGAMOS LA NUEVA PESTAÑA AL MENÚ
tab_turnos, tab_prog, tab_fac, tab_kpi, tab_hist, tab_portal = st.tabs(["📋 Turnero Diario", "🛠️ Programación", "💰 Facturación", "📊 KPIs", "📅 Históricos", "🏢 Portal Empresas"])

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
                
        if not df_cancelados.empty:
            st.write("### 🗑️ Turnos Cancelados")
            df_canc_view = df_cancelados[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Asesor']].copy()
            df_canc_view['Fecha'] = pd.to_datetime(df_canc_view['Fecha']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_canc_view, hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN DEL TALLER
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación y Estado del Taller")
    if not df.empty:
        col_filtro, _ = st.columns([1, 2])
        with col_filtro: asesor_filtro_prog = st.selectbox("👔 Filtrar por Asesor", ["TODOS"] + ASESORES_LISTA, key="filtro_asesor_prog")
            
        df_prog_filtrado = df.copy()
        if asesor_filtro_prog != "TODOS":
            nombre_corto = asesor_filtro_prog.split()[0].upper()
            df_prog_filtrado = df_prog_filtrado[df_prog_filtrado['Asesor'].str.contains(nombre_corto, case=False, na=False)]

        estados_map = [("⏳ EN PROCESO", "PROCESO"), ("⛔ DETENIDOS", "DETENIDO"), ("✅ TERMINADOS (Pte. Fact/Entr)", "TERM PEND"), ("🚚 ENTREGADOS", "ENTREGADO")]
        st.divider()

        for titulo, match in estados_map:
            if "DETENIDO" in match: st.error(f"### {titulo}")
            else: st.write(f"### {titulo}")
            col1, col2 = st.columns(2)
            
            def dibujar_tabla(col, grupo_nombre, m_key):
                d_g = df_prog_filtrado[df_prog_filtrado['Grupo'] == grupo_nombre].copy()
                d_e = d_g[d_g['Estado_Taller'].str.contains(m_key, na=False)].copy()
                with col:
                    st.caption(f"**{grupo_nombre}**")
                    if not d_e.empty:
                        d_e = d_e.sort_values(by='Fin', ascending=True)
                        d_e['Fecha Prom.'] = d_e['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
                        df_vista = d_e[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Paños', 'Asesor']]
                        df_vista.columns = ['Estado Taller (Col T)', 'Fecha Prom.', 'Patente', 'Vehículo', 'Paños', 'Asesor']
                        st.dataframe(df_vista, hide_index=True, use_container_width=True, key=f"{grupo_nombre}_{m_key}_{asesor_filtro_prog}")
                    else: st.caption(f"Sin vehículos asignados.")

            dibujar_tabla(col1, "GRUPO UNO", match)
            dibujar_tabla(col2, "GRUPO DOS", match)
            st.divider()
        
        with st.expander("📊 Ver Gráfico de Gantt (Carga General del Taller)"):
            df_gantt = df_prog_filtrado[df_prog_filtrado['Estado_Fac'].isin(['SI', 'NO'])].copy()
            if not df_gantt.empty:
                df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo'].str[:15]
                fig = px.timeline(df_gantt, x_start="Inicio", x_end="Fin", y="ID", color="Grupo", text="Paños", hover_data=["Asesor", "Estado_Taller"], title="Carga de Taller por Grupo")
                fig.update_yaxes(autorange="reversed")
                milisegundos_hoy = datetime.now().timestamp() * 1000
                fig.add_vline(x=milisegundos_hoy, line_dash="dash", line_color="red")
                fig.add_annotation(x=milisegundos_hoy, y=1.05, yref="paper", text="HOY", showarrow=False, font=dict(color="red", size=12))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay vehículos para mostrar en el gráfico.")

# ==========================================
# PESTAÑA 3: FACTURACIÓN
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación y Paños")
        
        df_fac = df[df['Estado_Fac'] == 'FAC']
        df_tpf = df[df['Estado_Taller'].str.contains("TERM PEND FACT", na=False)]
        df_tpe = df[df['Estado_Taller'].str.contains("TERM PEND ENTREG", na=False)]
        df_epf = df[df['Estado_Taller'].str.contains("ENTREGADO PEND FACT", na=False)]
        
        pesos_fac = df_fac['Precio'].sum()
        panos_fac = df_fac['Paños'].sum()
        ratio_peso_pano = (pesos_fac / panos_fac) if panos_fac > 0 else 0
        
        st.write("### 💰 Rendimiento Actual")
        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
        c_r1.markdown(f'<div class="metric-card"><div class="metric-title">Facturado (Pesos)</div><div class="metric-value-money">${pesos_fac:,.0f}</div><div class="metric-subtitle-gray">Total Estado FAC</div></div>', unsafe_allow_html=True)
        c_r2.markdown(f'<div class="metric-card"><div class="metric-title">Facturado (Paños)</div><div class="metric-value-number">{panos_fac:.1f}</div><div class="metric-subtitle-gray">Total Estado FAC</div></div>', unsafe_allow_html=True)
        c_r3.markdown(f'<div class="metric-card"><div class="metric-title">Ratio ($ / Paño)</div><div class="metric-value-money">${ratio_peso_pano:,.0f}</div><div class="metric-subtitle-gray">Promedio de Venta</div></div>', unsafe_allow_html=True)
        c_r4.markdown(f'<div class="metric-card"><div class="metric-title">Confirmado (Pesos)</div><div class="metric-value-money">${df[df["Estado_Fac"] == "SI"]["Precio"].sum():,.0f}</div><div class="metric-subtitle-green">Estado SI (Pendiente Cierre)</div></div>', unsafe_allow_html=True)
        
        st.divider()
        
        st.write("### 🚨 Detalle de Estados Pendientes (Plata Inmovilizada)")
        c_e1, c_e2, c_e3 = st.columns(3)
        c_e1.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Facturar</div><div class="metric-value-money">${df_tpf["Precio"].sum():,.0f}</div><div class="metric-subtitle-red">⚠️ {df_tpf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e2.markdown(f'<div class="metric-card"><div class="metric-title">Terminado Pend. Entregar</div><div class="metric-value-money">${df_tpe["Precio"].sum():,.0f}</div><div class="metric-subtitle-blue">⏳ {df_tpe["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        c_e3.markdown(f'<div class="metric-card"><div class="metric-title">Entregado Pend. Facturar</div><div class="metric-value-money">${df_epf["Precio"].sum():,.0f}</div><div class="metric-subtitle-green">🚚 {df_epf["Paños"].sum():.1f} paños físicos</div></div>', unsafe_allow_html=True)
        
        st.divider()

        st.write("### 📊 Análisis de Producción: Grupos y Asesores")
        df_analisis = df.copy()
        df_analisis['Estado_Resumen'] = df_analisis['Estado_Fac'].apply(lambda x: 'Facturado' if x == 'FAC' else 'Proyectado (Por Facturar)')

        tab_grupos, tab_asesores, tab_empresas = st.tabs(["👥 Comparativa por Grupos", "👔 Comparativa por Asesores", "🏢 Desglose por Empresa"])

        with tab_grupos:
            st.markdown("Comparativa de producción real y proyección a futuro por equipo de trabajo.")
            grupo_stats = df_analisis.groupby(['Grupo', 'Estado_Resumen'])[['Paños', 'Precio']].sum().reset_index()
            col_g_tab, col_g_g1, col_g_g2 = st.columns([1, 1.5, 1.5])
            with col_g_tab:
                res_grupo_tabla = df_analisis.groupby(['Grupo', 'Estado_Resumen'])[['Paños', 'Precio']].sum().unstack(fill_value=0)
                res_grupo_tabla.columns = [f"{col[1]} ({col[0]})" for col in res_grupo_tabla.columns]
                st.dataframe(res_grupo_tabla.style.format("{:,.0f}"), use_container_width=True)
            with col_g_g1:
                fig_g_panos = px.bar(grupo_stats, x='Grupo', y='Paños', color='Estado_Resumen', barmode='group', text_auto='.1f', title='📦 Paños Totales', color_discrete_map={'Facturado': '#28a745', 'Proyectado (Por Facturar)': '#00A8E8'})
                fig_g_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_g_panos, use_container_width=True)
            with col_g_g2:
                fig_g_pesos = px.bar(grupo_stats, x='Grupo', y='Precio', color='Estado_Resumen', barmode='group', text_auto='$.2s', title='💰 Montos en Pesos', color_discrete_map={'Facturado': '#28a745', 'Proyectado (Por Facturar)': '#00A8E8'})
                fig_g_pesos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_g_pesos, use_container_width=True)

        with tab_asesores:
            st.markdown("Rendimiento individual y cartera de vehículos asignada por asesor.")
            asesor_stats = df_analisis.groupby(['Asesor', 'Estado_Resumen'])[['Paños', 'Precio']].sum().reset_index()
            col_a_tab, col_a_g1, col_a_g2 = st.columns([1, 1.5, 1.5])
            with col_a_tab:
                res_asesor_tabla = df_analisis.groupby(['Asesor', 'Estado_Resumen'])[['Paños', 'Precio']].sum().unstack(fill_value=0)
                res_asesor_tabla.columns = [f"{col[1]} ({col[0]})" for col in res_asesor_tabla.columns]
                st.dataframe(res_asesor_tabla.style.format("{:,.0f}"), use_container_width=True)
            with col_a_g1:
                fig_a_panos = px.bar(asesor_stats, x='Asesor', y='Paños', color='Estado_Resumen', barmode='group', text_auto='.1f', title='📦 Paños por Asesor', color_discrete_map={'Facturado': '#28a745', 'Proyectado (Por Facturar)': '#ffc107'})
                fig_a_panos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_a_panos, use_container_width=True)
            with col_a_g2:
                fig_a_pesos = px.bar(asesor_stats, x='Asesor', y='Precio', color='Estado_Resumen', barmode='group', text_auto='$.2s', title='💰 Montos por Asesor', color_discrete_map={'Facturado': '#28a745', 'Proyectado (Por Facturar)': '#ffc107'})
                fig_a_pesos.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_a_pesos, use_container_width=True)

        with tab_empresas:
            col_e1, col_e2 = st.columns([1, 2])
            with col_e1:
                st.write("#### 🏢 Desglose General (Cliente)")
                res_empresa = df.groupby('Cliente')[['Paños', 'Precio']].sum().reset_index().sort_values(by='Paños', ascending=False)
                st.dataframe(res_empresa.style.format({'Precio': "$ {:,.0f}", 'Paños': "{:.1f}"}), hide_index=True, use_container_width=True)
            with col_e2:
                if not res_empresa.empty:
                    fig_empresa = px.pie(res_empresa, values='Precio', names='Cliente', hole=0.4, title="Participación de Clientes (Volumen en $)")
                    st.plotly_chart(fig_empresa, use_container_width=True)

# ==========================================
# PESTAÑA 4: KPIs
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
        fig_asesor_kpi = px.bar(df, x="Asesor", color="Estado_Fac", barmode="group")
        st.plotly_chart(fig_asesor_kpi, use_container_width=True)

# ==========================================
# PESTAÑA 5: HISTÓRICOS
# ==========================================
with tab_hist:
    if not df.empty:
        st.subheader("📅 Histórico Mensual")
        st.write("Evolución de paños y pesos a lo largo del tiempo, agrupados por mes de finalización y empresa.")
        df_hist = df[df['Mes_Hist'] != 'SIN FECHA'].sort_values('Mes_Hist')
        
        if not df_hist.empty:
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                st.write("#### 🧑‍🔧 Paños por Mes y Empresa")
                pivot_panos = pd.pivot_table(df_hist, values='Paños', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_panos.style.format("{:.1f}"), use_container_width=True)
            with c_h2:
                st.write("#### 💰 Pesos por Mes y Empresa")
                pivot_pesos = pd.pivot_table(df_hist, values='Precio', index='Mes_Hist', columns='Cliente', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_pesos.style.format("$ {:,.0f}"), use_container_width=True)
                
            st.divider()
            st.write("#### 📈 Evolución de Paños")
            fig_hist = px.bar(df_hist, x="Mes_Hist", y="Paños", color="Cliente", barmode="group", title="Paños Facturados/Proyectados por Mes")
            st.plotly_chart(fig_hist, use_container_width=True)
        else: st.info("No hay datos con fechas válidas para mostrar el historial.")

# ==========================================
# PESTAÑA 6: PORTAL EMPRESAS (NUEVO)
# ==========================================
with tab_portal:
    if not df.empty:
        st.subheader("🏢 Seguimiento de Unidades: Empresas del Grupo")
        st.write("Vista exclusiva para que los responsables de AUTOSOL, AUTOLUX y CIEL puedan ver el estado de sus vehículos, fechas de entrega y observaciones.")
        
        # Filtramos buscando palabras clave en el nombre de la empresa
        df_grupo = df[df['Cliente'].str.contains('SOL|LUX|CIEL', case=False, na=False)].copy()
        
        if not df_grupo.empty:
            c_filtro, _ = st.columns([1, 2])
            with c_filtro:
                empresa_filtro = st.selectbox("Seleccionar Empresa", ["TODAS", "AUTOSOL", "AUTOLUX", "CIEL / AUTOCIEL"])
            
            df_vista_emp = df_grupo.copy()
            if empresa_filtro == "AUTOSOL":
                df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('SOL', case=False, na=False)]
            elif empresa_filtro == "AUTOLUX":
                df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('LUX', case=False, na=False)]
            elif empresa_filtro == "CIEL / AUTOCIEL":
                df_vista_emp = df_vista_emp[df_vista_emp['Cliente'].str.contains('CIEL', case=False, na=False)]
            
            # Tarjetas de resumen para la empresa seleccionada
            en_proceso = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("PROCESO", na=False)])
            detenidos = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("DETENIDO", na=False)])
            terminados = len(df_vista_emp[df_vista_emp['Estado_Taller'].str.contains("TERM", na=False)])
            
            ce1, ce2, ce3 = st.columns(3)
            ce1.markdown(f'<div class="metric-card"><div class="metric-title">En Proceso</div><div class="metric-value-number">{en_proceso}</div><div class="metric-subtitle-blue">Vehículos en Taller</div></div>', unsafe_allow_html=True)
            ce2.markdown(f'<div class="metric-card"><div class="metric-title">Detenidos (Con Novedad)</div><div class="metric-value-number" style="color:#dc3545;">{detenidos}</div><div class="metric-subtitle-red">Revisar Observaciones</div></div>', unsafe_allow_html=True)
            ce3.markdown(f'<div class="metric-card"><div class="metric-title">Terminados (Pte. Entregar)</div><div class="metric-value-number" style="color:#28a745;">{terminados}</div><div class="metric-subtitle-green">Listos / Facturando</div></div>', unsafe_allow_html=True)
            
            st.divider()
            
            # Formatear la vista de la tabla
            df_vista_emp['Fecha Entrega'] = df_vista_emp['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
            
            vista_columnas = ['Cliente', 'Vehiculo', 'Patente', 'Estado_Taller', 'Fecha Entrega', 'Asesor', 'Observaciones']
            df_mostrar = df_vista_emp[vista_columnas].rename(columns={'Estado_Taller': 'Estado Actual'})
            
            st.dataframe(df_mostrar, hide_index=True, use_container_width=True)
        else:
            st.info("No hay vehículos registrados para las empresas del grupo en este momento.")

with st.sidebar:
    if st.button("🔄 Refrescar Datos desde Sheet"):
        st.cache_data.clear()
        if 'memoria_turnos_v11' in st.session_state: del st.session_state['memoria_turnos_v11']
        st.rerun()
