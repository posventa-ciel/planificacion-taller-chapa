import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Tablero de Control - TPS")

if st.button("扫 Limpiar Memoria y Recargar"):
    st.cache_data.clear()

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

def parsear_fecha_español(texto):
    """Convierte texto a fecha. Corregido para evitar errores de tipo."""
    if pd.isna(texto) or str(texto).strip() == "": 
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    texto = str(texto).lower().strip()
    
    # 1. Intento DD/MM/YYYY
    try:
        return pd.to_datetime(texto, dayfirst=True)
    except:
        pass
        
    # 2. Intento formato largo "21 de enero de 2026"
    try:
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match:
            dia, mes_txt, anio = match.groups()
            mes_num = MESES_ES.get(mes_txt, 1)
            return datetime(int(anio), int(mes_num), int(dia))
    except:
        pass
        
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

@st.cache_data(ttl=60)
def cargar_datos():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip().str.upper() # Columnas en mayúsculas para evitar errores
            
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d = d[d['PATENTE'].str.strip() != ""]
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def limpiar_y_procesar(df_in):
    filas = []
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for _, row in df_in.iterrows():
        # Buscar columna de fecha dinámicamente
        col_fecha = next((c for c in df_in.columns if 'FECH' in c or 'PROMESA' in c), None)
        f_fin = parsear_fecha_español(row.get(col_fecha, ''))
        
        # Procesar Paños / Días
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.')
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            dias = float(numeros[0]) if numeros else 1.0
        except:
            dias = 1.0
            
        f_inicio = f_fin - timedelta(days=max(1, int(dias)))
        
        # Limpieza de Precio
        precio_raw = str(row.get('PRECIO', '0')).replace('$', '').replace('.', '').replace(',', '.').strip()
        try:
            precio_val = float(precio_raw) if precio_raw != "" else 0.0
        except:
            precio_val = 0.0

        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio,
            'Fin': f_fin,
            'Dias': dias,
            'Estado': str(row.get('FAC', '')).strip().upper(),
            'Precio': precio_val
        })
        
    return pd.DataFrame(filas)

# --- EJECUCIÓN ---
try:
    df_raw = cargar_datos()
    
    if not df_raw.empty:
        df_clean = limpiar_y_procesar(df_raw)
        
        # --- SECCIÓN FINANCIERA POR GRUPO ---
        st.subheader("💰 Resumen Financiero por Grupo")
        
        # Agrupamos por Grupo y Estado
        resumen_grupo = df_clean.groupby(['Grupo', 'Estado'])['Precio'].sum().unstack(fill_value=0)
        
        # Aseguramos que existan las columnas para evitar errores si no hay datos
        for col in ['FAC', 'SI', 'NO']:
            if col not in resumen_grupo.columns:
                resumen_grupo[col] = 0.0

        # Mostrar métricas generales arriba
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Facturado (FAC)", f"$ {df_clean[df_clean['Estado'] == 'FAC']['Precio'].sum():,.0f}")
        m2.metric("Total Confirmado (SI)", f"$ {df_clean[df_clean['Estado'] == 'SI']['Precio'].sum():,.0f}")
        m3.metric("Total Proyectado (NO)", f"$ {df_clean[df_clean['Estado'] == 'NO']['Precio'].sum():,.0f}")

        # Tabla de detalle por grupo
        st.write("### Detalle por Equipo")
        resumen_formateado = resumen_grupo[['FAC', 'SI', 'NO']].copy()
        resumen_formateado.columns = ['Facturado (FAC)', 'Confirmado (SI)', 'Pendiente (NO)']
        st.table(resumen_formateado.style.format("$ {:,.0f}"))

        st.divider()

        # --- GANTT ---
        st.subheader("📅 Planificación Visual")
        df_gantt = df_clean[df_clean['Estado'].isin(['SI', 'NO'])].copy()
        
        if not df_gantt.empty:
            df_gantt['ID'] = df_gantt['Patente'] + " " + df_gantt['Vehiculo'].str[:10]
            fig = px.timeline(df_gantt, x_start="Inicio", x_end="Fin", y="ID", color="Grupo", text="Dias")
            fig.update_yaxes(autorange="reversed")
            fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver base de datos completa"):
            st.dataframe(df_clean)
    else:
        st.warning("No hay datos disponibles en el Sheet. Revisa los permisos de compartir.")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
