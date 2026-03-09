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
            
            if len(d.columns) > 19:
                cols = list(d.columns)
                cols[19] = 'ESTADO_TALLER'
                d.columns = cols
            
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
    for old_key in ['df_turnos_memoria', 'memoria_turnos_v4', 'memoria_turnos_v5', 'memoria_turnos_v6', 'memoria_turnos_v7', 'memoria_turnos_v8', 'memoria_turnos_v9', 'memoria_turnos_v10']:
        if old_key in st.session_state:
            del st.session_state[old_key]

# --- EJECUCIÓN ---
df = obtener_datos_maestros()

tab_turnos, tab_prog, tab_fac, tab_kpi = st.tabs(["📋 Turnero Diario", "🛠️ Programación", "💰 Facturación", "📊 KPIs"])

# ==========================================
# PESTAÑA 1: TURNERO DIARIO (IGUAL QUE ANTES)
# ==========================================
with tab_turnos:
    st.subheader("Recepción de Vehículos")
    
    col_fecha, col_asesor, col_add = st.columns([1, 1, 2])
    
    with col_fecha:
        hoy = datetime.today().date()
        fechas_seleccionadas = st.date_input("📅 Rango de Fechas", value=(hoy, hoy), format="DD/MM/YYYY")
        if isinstance(fechas_seleccionadas, tuple):
            if len(fechas_seleccionadas) == 2:
                f_inicio, f_fin = fechas_seleccionadas
            else:
                f_inicio = f_fin = fechas_seleccionadas[0]
        else:
            f_inicio = f_fin = fechas_seleccionadas

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
                            'Tipo': '🚶‍♂️ SIN TURNO', 'Fecha': f_inicio, 'Hora': '-',
                            'Vehiculo': nuevo_vehiculo.upper(), 'Patente': nueva_patente.upper(),
                            'Asesor': nuevo_asesor, 'Precio': nuevo_precio, 'Paños': nuevo_panos,
                            'Observaciones': nueva_obs, 'Tiempo_Entrega': nuevo_tiempo,
                            'Cliente': nuevo_cliente, 'Seguro': nuevo_seguro.upper(),
                            'Recibido': False, 'Fotos': False, 'Cancelado': False, 'OR': "", 'Eliminar': False
                        }])
                        st.session_state.memoria_turnos_v11 = pd.concat([st.session_state.memoria_turnos_v11, nuevo_ingreso], ignore_index=True)
                        st.success(f"Ingreso sin turno agregado con éxito.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Por favor completa la Patente y el Vehículo.")

    st.divider()

    mask = (st.session_state.memoria_turnos_v11['Fecha'] >= f_inicio) & (st.session_state.memoria_turnos_v11['Fecha'] <= f_fin)
    df_rango = st.session_state.memoria_turnos_v11[mask].copy()

    if asesor_filtro != "TODOS":
        df_rango = df_rango[df_rango['Asesor'] == asesor_filtro]

    if df_rango.empty:
        st.info("No hay turnos para los filtros seleccionados.")
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
                edited_prog = st.data_editor(
                    df_prog[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']],
                    column_config={
                        "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA),
                        "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False),
                        "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False),
                        "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10),
                        "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False)
                    }, hide_index=True, use_container_width=True, key="editor_prog"
                )

            if not df_sin.empty:
                st.write("#### 🚶‍♂️ Ingresos Adicionales (Sin Turno)")
                edited_sin = st.data_editor(
                    df_sin[['Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Seguro', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado', 'Eliminar']],
                    column_config={
                        "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                        "Asesor": st.column_config.SelectboxColumn("Asesor", options=ASESORES_LISTA),
                        "Recibido": st.column_config.CheckboxColumn("✅ Recibido", default=False),
                        "Fotos": st.column_config.CheckboxColumn("📸 Fotos", default=False),
                        "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10),
                        "Cancelado": st.column_config.CheckboxColumn("❌ Cancelar", default=False),
                        "Eliminar": st.column_config.CheckboxColumn("🗑️ Borrar", default=False)
                    }, hide_index=True, use_container_width=True, key="editor_sin"
                )

            if st.button("💾 Guardar Cambios en Pendientes"):
                indices_a_borrar = []
                if not edited_prog.empty:
                    for idx, row in edited_prog.iterrows():
                        st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                if not edited_sin.empty:
                    for idx, row in edited_sin.iterrows():
                        if row.get('Eliminar', False): indices_a_borrar.append(idx)
                        else: st.session_state.memoria_turnos_v11.loc[idx, ['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']] = row[['Fecha', 'Hora', 'Asesor', 'Recibido', 'Fotos', 'OR', 'Cancelado']]
                
                if indices_a_borrar: st.session_state.memoria_turnos_v11.drop(indices_a_borrar, inplace=True)
                st.success("Actualizado."); time.sleep(0.5); st.rerun() 

        st.divider()
        st.write("### 🏁 Turnos Recibidos (Con OR Abierta)")
        if not df_recibidos.empty:
            edited_recibidos = st.data_editor(
                df_recibidos[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Cliente', 'Asesor', 'Recibido', 'Fotos', 'OR']],
                column_config={
                    "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", disabled=True),
                    "Recibido": st.column_config.CheckboxColumn("✅ Recibido"),
                    "Fotos": st.column_config.CheckboxColumn("📸 Fotos"),
                    "OR": st.column_config.TextColumn("📝 N° de OR", max_chars=10)
                }, hide_index=True, use_container_width=True, key="editor_recibidos"
            )
            if st.button("💾 Guardar Correcciones"):
                for idx, row in edited_recibidos.iterrows():
                    st.session_state.memoria_turnos_v11.loc[idx, ['Recibido', 'Fotos', 'OR']] = row[['Recibido', 'Fotos', 'OR']]
                st.success("Correcciones aplicadas."); time.sleep(0.5); st.rerun()
                
        if not df_cancelados.empty:
            st.write("### 🗑️ Turnos Cancelados")
            df_canc_view = df_cancelados[['Tipo', 'Fecha', 'Hora', 'Patente', 'Vehiculo', 'Asesor']].copy()
            df_canc_view['Fecha'] = pd.to_datetime(df_canc_view['Fecha']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_canc_view, hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN DEL TALLER (CON FILTRO CORREGIDO)
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación y Estado del Taller")
    
    if not df.empty:
        col_filtro, _ = st.columns([1, 2])
        with col_filtro:
            asesor_filtro_prog = st.selectbox("👔 Filtrar por Asesor", ["TODOS"] + ASESORES_LISTA, key="filtro_asesor_prog")
            
        df_prog_filtrado = df.copy()
        if asesor_filtro_prog != "TODOS":
            nombre_corto = asesor_filtro_prog.split()[0].upper()
            df_prog_filtrado = df_prog_filtrado[df_prog_filtrado['Asesor'].str.contains(nombre_corto, case=False, na=False)]

        estados_map = [
            ("⏳ EN PROCESO", "PROCESO"), 
            ("⛔ DETENIDOS", "DETENIDO"), 
            ("✅ TERMINADOS (Pte. Fact/Entr)", "TERM PEND"), 
            ("🚚 ENTREGADOS", "ENTREGADO")
        ]
        
        st.divider()

        for titulo, match in estados_map:
            if "DETENIDO" in match:
                st.error(f"### {titulo}")
            else:
                st.write(f"### {titulo}")
                
            col1, col2 = st.columns(2)
            
            def dibujar_tabla(col, grupo_nombre, m_key):
                d_g = df_prog_filtrado[df_prog_filtrado['Grupo'] == grupo_nombre].copy()
                d_e = d_g[d_g['Estado_Taller'].str.contains(m_key, na=False)].copy()
                with col:
                    st.caption(f"**{grupo_nombre}**")
                    if not d_e.empty:
                        d_e = d_e.sort_values(by='Fin', ascending=True)
                        d_e['Fecha Prom.'] = d_e['Fecha_Promesa_Disp'].apply(
                            lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha"
                        )
                        df_vista = d_e[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Paños', 'Asesor']]
                        df_vista.columns = ['Estado Taller (Col T)', 'Fecha Prom.', 'Patente', 'Vehículo', 'Paños', 'Asesor']
                        st.dataframe(df_vista, hide_index=True, use_container_width=True, key=f"{grupo_nombre}_{m_key}_{asesor_filtro_prog}")
                    else:
                        st.caption(f"Sin vehículos asignados.")

            dibujar_tabla(col1, "GRUPO UNO", match)
            dibujar_tabla(col2, "GRUPO DOS", match)
            
            st.divider()
        
        with st.expander("📊 Ver Gráfico de Gantt (Carga General del Taller)"):
            df_gantt = df_prog_filtrado[df_prog_filtrado['Estado_Fac'].isin(['SI', 'NO'])].copy()
            if not df_gantt.empty:
                df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo'].str[:15]
                fig = px.timeline(
                    df_gantt, x_start="Inicio", x_end="Fin", y="ID", color="Grupo", text="Paños",
                    hover_data=["Asesor", "Estado_Taller"], title="Carga de Taller por Grupo"
                )
                fig.update_yaxes(autorange="reversed")
                
                milisegundos_hoy = datetime.now().timestamp() * 1000
                fig.add_vline(x=milisegundos_hoy, line_dash="dash", line_color="red")
                fig.add_annotation(x=milisegundos_hoy, y=1.05, yref="paper", text="HOY", showarrow=False, font=dict(color="red", size=12))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay vehículos para mostrar en el gráfico.")

# ==========================================
# PESTAÑA 3: FACTURACIÓN
# ==========================================
with tab_fac:
    if not df.empty:
        st.subheader("Análisis de Facturación y Paños")
        
        # Filtros para métricas
        df_fac = df[df['Estado_Fac'] == 'FAC']
        df_term_pend = df[df['Estado_Taller'].str.contains("TERM PEND", na=False)]
        df_proceso = df[df['Estado_Taller'].str.contains("PROCESO", na=False)]
        df_detenidos = df[df['Estado_Taller'].str.contains("DETENIDO", na=False)]
        
        # Cálculos globales
        pesos_fac = df_fac['Precio'].sum()
        panos_fac = df_fac['Paños'].sum()
        ratio_peso_pano = (pesos_fac / panos_fac) if panos_fac > 0 else 0
        
        st.write("### 💰 Rendimiento Actual")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Facturado (Pesos)", f"$ {pesos_fac:,.0f}")
        m2.metric("Facturado (Paños)", f"{panos_fac:.1f}")
        m3.metric("Ratio ($ / Paño)", f"$ {ratio_peso_pano:,.0f}")
        m4.metric("Confirmado (Pesos - SI)", f"$ {df[df['Estado_Fac'] == 'SI']['Precio'].sum():,.0f}")
        
        st.divider()
        
        st.write("### 🚨 Oportunidades y Proyección de Taller")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Terminados (Pte. Facturar)", f"{df_term_pend['Paños'].sum():.1f} paños", "¡Apurar Asesores!", delta_color="inverse")
        c2.metric("Plata Inmovilizada", f"$ {df_term_pend['Precio'].sum():,.0f}", "Terminados no facturados", delta_color="inverse")
        c3.metric("En Proceso (Taller)", f"{df_proceso['Paños'].sum():.1f} paños", "Proyección a fin de mes")
        c4.metric("Detenidos", f"{df_detenidos['Paños'].sum():.1f} paños", "Riesgo", delta_color="inverse")
        
        st.divider()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### 👥 Pesos por Grupo y Estado")
            res_grupo = df.groupby(['Grupo', 'Estado_Fac'])['Precio'].sum().unstack(fill_value=0)
            st.table(res_grupo.style.format("$ {:,.0f}"))
            
            st.write("### 🧑‍🔧 Paños por Grupo y Estado Taller")
            res_grupo_panos = df.groupby(['Grupo', 'Estado_Taller'])['Paños'].sum().unstack(fill_value=0)
            st.dataframe(res_grupo_panos.style.format("{:.1f}"), use_container_width=True)
            
        with col_b:
            st.write("### 👔 Pesos por Asesor")
            res_asesor = df.groupby(['Asesor', 'Estado_Fac'])['Precio'].sum().unstack(fill_value=0)
            st.table(res_asesor.style.format("$ {:,.0f}"))
            
            st.write("### ⏳ Term. Pendientes a facturar por Asesor")
            if not df_term_pend.empty:
                res_pendientes = df_term_pend.groupby('Asesor')[['Paños', 'Precio']].sum().reset_index()
                st.dataframe(res_pendientes.style.format({'Precio': "$ {:,.0f}", 'Paños': "{:.1f}"}), hide_index=True, use_container_width=True)
            else:
                st.success("¡Excelente! No hay vehículos terminados pendientes de facturar.")

# ==========================================
# PESTAÑA 4: KPIs
# ==========================================
with tab_kpi:
    if not df.empty:
        st.subheader("Indicadores Clave de Desempeño (KPI)")
        k1, k2, k3 = st.columns(3)
        
        df_fac = df[df['Estado_Fac'] == 'FAC']
        ticket = df_fac['Precio'].mean() if not df_fac.empty else 0
        k1.metric("Ticket Promedio (FAC)", f"$ {ticket:,.0f}")
        
        intensidad = df['Paños'].mean()
        k2.metric("Paños Promedio / Auto", f"{intensidad:.2f}")
        
        total_casos = len(df[df['Estado_Fac'].isin(['FAC', 'SI', 'NO'])])
        casos_fac = len(df_fac)
        ratio = (casos_fac / total_casos * 100) if total_casos > 0 else 0
        k3.metric("% Conversión a Facturado", f"{ratio:.1f}%")

        st.divider()
        st.write("### Cantidad de Vehículos por Asesor")
        fig_asesor = px.bar(df, x="Asesor", color="Estado_Fac", barmode="group")
        st.plotly_chart(fig_asesor, use_container_width=True)

with st.sidebar:
    if st.button("🔄 Refrescar Datos desde Sheet"):
        st.cache_data.clear()
        if 'memoria_turnos_v11' in st.session_state:
            del st.session_state['memoria_turnos_v11']
        st.rerun()
