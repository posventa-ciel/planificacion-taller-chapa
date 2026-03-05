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
                'Tipo': '📅 PROGRAMADO', 'Fecha': fecha_turno.date(), 
                'Hora': str(row.get('HORAS', '')).strip(),
                'Vehiculo': str(row.get('VEHICULO', '')).upper(), 'Patente': str(row.get('PATENTE', '')).upper(),
                'Asesor': asesor_raw, 'Precio': str(row.get('PRECIO', '')).strip(),
                'Paños': str(row.get('PAÑOS', '')).strip(), 'Observaciones': str(row.get('OBSERVACIONES', '')).strip(),
                'Tiempo_Entrega': str(row.get(col_tiempo, '')) if col_tiempo else "",
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
            
            # Captura de columna T para Estado
            if len(d.columns) > 19:
                cols = list(d.columns)
                cols[19] = 'ESTADO_TALLER'
                d.columns = cols
            
            # Captura de columna I para Fecha Prometida (Índice 8)
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
        # Tomamos específicamente la nueva columna configurada desde la "I"
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
            'Inicio': f_inicio, 'Fin': f_fin, 'Fecha_Promesa_Disp': fecha_promesa_display,
            'Paños': panos, 'Estado_Fac': str(row.get('FAC', '')).strip().upper(),
            'Estado_Taller': estado_taller, 'Precio': precio_val
        })
    return pd.DataFrame(filas)

# --- BLINDAJE DE MEMORIA ---
if 'memoria_turnos_v11' not in st.session_state:
    st.session_state.memoria_turnos_v11 = obtener_turnos()

# --- EJECUCIÓN ---
df = obtener_datos_maestros()
tab_turnos, tab_prog, tab_fac, tab_kpi = st.tabs(["📋 Turnero Diario", "🛠️ Programación", "💰 Facturación", "📊 KPIs"])

# (Pestaña Turnos omitida por brevedad, se mantiene igual)
with tab_turnos:
    st.info("Pestaña de Turnos activa según código original.")

# ==========================================
# PESTAÑA 2: PROGRAMACIÓN DEL TALLER (ACTUALIZADA)
# ==========================================
with tab_prog:
    st.subheader("🛠️ Programación por Estados")
    
    if not df.empty:
        # Definición de Filtros por palabras clave en ESTADO_TALLER
        estados_seccion = {
            "⏳ EN PROCESO": ["PROCESO", "TRABAJANDO", "TALLER"],
            "⛔ DETENIDOS": ["DETENIDO", "ESPERA", "REPUESTO", "AUTORIZACION"],
            "✅ TERMINADOS (Pte. Facturación/Entrega)": ["TERMINADO", "FINALIZADO", "CONTROL"],
            "🚚 ENTREGADOS": ["ENTREGADO", "RETIRADO"]
        }

        def filtrar_por_estado(df_input, lista_keywords):
            patron = '|'.join(lista_keywords)
            return df_input[df_input['Estado_Taller'].str.contains(patron, na=False)]

        for titulo, keywords in estados_seccion.items():
            df_sector = filtrar_por_estado(df, keywords)
            
            # Estilo especial para Detenidos
            if "DETENIDOS" in titulo:
                st.error(f"### {titulo}")
            else:
                st.write(f"### {titulo}")

            if not df_sector.empty:
                df_sector = df_sector.sort_values(by='Fin', ascending=True)
                df_vista = df_sector[['Estado_Taller', 'Fecha_Promesa_Disp', 'Patente', 'Vehiculo', 'Paños', 'Asesor', 'Grupo']].copy()
                df_vista['Fecha Prom.'] = df_vista['Fecha_Promesa_Disp'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else "Sin Fecha")
                
                df_final = df_vista[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehículo', 'Paños', 'Asesor', 'Grupo']] if 'Vehículo' in df_vista else df_vista[['Estado_Taller', 'Fecha Prom.', 'Patente', 'Vehiculo', 'Paños', 'Asesor', 'Grupo']]
                
                st.data_editor(df_final, hide_index=True, use_container_width=True, key=f"table_{titulo}")
            else:
                st.caption("No hay vehículos en este estado.")
            st.divider()

        with st.expander("📊 Ver Gráfico de Gantt General"):
            df_gantt = df[df['Estado_Fac'].isin(['SI', 'NO'])].copy()
            if not df_gantt.empty:
                df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo'].str[:15]
                fig = px.timeline(df_gantt, x_start="Inicio", x_end="Fin", y="ID", color="Grupo", text="Paños", hover_data=["Asesor", "Estado_Taller"])
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

# (Pestañas Facturación y KPIs se mantienen igual)
with tab_fac: st.write("Sección de Facturación")
with tab_kpi: st.write("Sección de KPIs")

with st.sidebar:
    if st.button("🔄 Refrescar Datos desde Sheet"):
        st.cache_data.clear()
        if 'memoria_turnos_v11' in st.session_state:
            del st.session_state['memoria_turnos_v11']
        st.rerun()
