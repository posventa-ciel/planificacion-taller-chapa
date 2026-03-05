import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Sistema de Gestión Autociel")

# --- CONFIGURACIÓN ---
ID_NUEVO_SHEET = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_NUEVO_SHEET}/export?format=csv&gid="

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
def obtener_datos_maestros():
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
        
        # Procesar Paños
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.')
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            panos = float(numeros[0]) if numeros else 1.0
        except: panos = 1.0
            
        f_inicio = f_fin - timedelta(days=max(1, int(panos)))
        
        # Procesar Precio
        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try: precio_val = float(precio_raw) if precio_raw != "" else 0.0
        except: precio_val = 0.0

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Asesor': str(row.get('ASESOR', 'Sin Asesor')).strip().upper(),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio,
            'Fin': f_fin,
            'Paños': panos,
            'Estado': str(row.get('FAC', '')).strip().upper(),
            'Precio': precio_val
        })
    return pd.DataFrame(filas)

# --- CARGA ---
df = obtener_datos_maestros()

if df.empty:
    st.error("No se encontraron datos. Verifica la conexión con Google Sheets.")
else:
    # --- PESTAÑAS ---
    tab1, tab2, tab3 = st.tabs(["📅 Programación", "💰 Facturación", "📊 KPIs"])

    with tab1:
        st.subheader("Cronograma de Trabajo (Basado en Paños)")
        df_gantt = df[df['Estado'].isin(['SI', 'NO'])].copy()
        if not df_gantt.empty:
            df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo']
            fig = px.timeline(
                df_gantt, 
                x_start="Inicio", 
                x_end="Fin", 
                y="ID", 
                color="Grupo",
                text="Paños",
                hover_data=["Asesor", "Estado"],
                title="Carga de Taller por Grupo"
            )
            fig.update_yaxes(autorange="reversed")
            fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="HOY")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay vehículos pendientes.")

    with tab2:
        st.subheader("Análisis de Facturación")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("### Por Grupo")
            res_grupo = df.groupby(['Grupo', 'Estado'])['Precio'].sum().unstack(fill_value=0)
            st.dataframe(res_grupo.style.format("$ {:,.0f}"))
            
        with col_b:
            st.write("### Por Asesor")
            res_asesor = df.groupby(['Asesor', 'Estado'])['Precio'].sum().unstack(fill_value=0)
            st.dataframe(res_asesor.style.format("$ {:,.0f}"))

        fig_pie = px.sunburst(df, path=['Estado', 'Grupo'], values='Precio', title="Distribución de Montos")
        st.plotly_chart(fig_pie)

    with tab3:
        st.subheader("Indicadores Clave de Desempeño (KPI)")
        
        k1, k2, k3 = st.columns(3)
        
        # 1. Ticket Promedio
        ticket_promedio = df[df['Precio'] > 0]['Precio'].mean()
        k1.metric("Ticket Promedio", f"$ {ticket_promedio:,.0f}")
        
        # 2. Eficiencia de Paños (Promedio de paños por auto)
        promedio_panos = df['Paños'].mean()
        k2.metric("Paños Promedio / Auto", f"{promedio_panos:.2f}")
        
        # 3. % de Conversión (FAC vs SI)
        total_casos = len(df)
        casos_fac = len(df[df['Estado'] == 'FAC'])
        ratio = (casos_fac / total_casos * 100) if total_casos > 0 else 0
        k3.metric("% Facturación Realizada", f"{ratio:.1f}%")

        st.divider()
        st.write("### Volumen de Unidades por Grupo")
        fig_bar = px.bar(df, x="Grupo", color="Estado", barmode="group", title="Cantidad de Vehículos")
        st.plotly_chart(fig_bar)

# Botón de recarga en el sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150", caption="Autociel TPS")
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()
