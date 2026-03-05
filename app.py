import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Tablero de Control - TPS (Nuevo Origen)")

if st.button("🧹 Limpiar Memoria y Recargar"):
    st.cache_data.clear()

# --- CONFIGURACIÓN DEL NUEVO SHEET ---
# ID del nuevo archivo: 1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg
ID_NUEVO_SHEET = "1yoJk6hD6YianjGHUofs7q-RvEBJOZg51tFMZx-GVxNg"
URL_BASE = f"https://docs.google.com/spreadsheets/d/{ID_NUEVO_SHEET}/export?format=csv&gid="

# GIDs actualizados según el nuevo archivo
GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

# --- DICCIONARIO PARA TRADUCIR MESES ---
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

@st.cache_data(ttl=60)
def cargar_datos():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            # Leemos como texto para evitar problemas con formatos de moneda o fechas extrañas
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip()
            
            # Buscamos la columna de fecha (cualquiera que empiece con FECH o sea 'PROMESA')
            col_fecha = next((c for c in d.columns if 'FECH' in c.upper() or 'PROMESA' in c.upper()), None)
            if col_fecha:
                d = d.rename(columns={col_fecha: 'FECHA_PROMESA_RAW'})
            
            # Filtramos filas vacías basándonos en PATENTE o VEHICULO
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                # Limpiar filas donde la patente sea un string vacío o solo espacios
                d = d[d['PATENTE'].str.strip() != ""]
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except Exception as e:
            # st.write(f"Error cargando {n}: {e}") # Descomentar para debug
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# [Las funciones parsear_fecha_español y limpiar_y_procesar se mantienen igual]
def parsear_fecha_español(texto):
    if pd.isna(texto) or str(texto).strip() == "": return datetime.now()
    texto = str(texto).lower()
    try:
        return pd.to_datetime(texto, dayfirst=True)
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
    return datetime.now()

def limpiar_y_procesar(df_in):
    filas = []
    hoy = datetime.now()
    for _, row in df_in.iterrows():
        texto_fecha = row.get('FECHA_PROMESA_RAW', '')
        f_fin = parsear_fecha_español(texto_fecha)
        
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.')
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            dias = float(numeros[0]) if numeros else 1.0
            if dias < 0.5: dias = 1.0
        except:
            dias = 1.0
            
        f_inicio = f_fin - timedelta(days=dias)
        
        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio,
            'Fin': f_fin,
            'Dias': dias,
            'Estado': str(row.get('FAC', '')).strip().upper(),
            'Precio': str(row.get('PRECIO', '0'))
        })
    return pd.DataFrame(filas)

# --- LÓGICA DE VISUALIZACIÓN ---
try:
    df_raw = cargar_datos()
    
    if not df_raw.empty:
        df_clean = limpiar_y_procesar(df_raw)
        
        # 1. MÉTRICAS
        st.subheader("💰 Resumen Financiero")
        try:
            # Limpieza robusta de la columna precio
            df_clean['Precio_Num'] = df_clean['Precio'].astype(str).str.replace(r'[$. ]', '', regex=True).str.replace(',', '.')
            df_clean['Precio_Num'] = pd.to_numeric(df_clean['Precio_Num'], errors='coerce').fillna(0)
            
            c1, c2, c3 = st.columns(3)
            fac = df_clean[df_clean['Estado'] == 'FAC']['Precio_Num'].sum()
            si = df_clean[df_clean['Estado'] == 'SI']['Precio_Num'].sum()
            no = df_clean[df_clean['Estado'] == 'NO']['Precio_Num'].sum()
            
            c1.metric("Facturado (FAC)", f"$ {fac:,.0f}")
            c2.metric("Confirmado (SI)", f"$ {si:,.0f}")
            c3.metric("Pendiente (NO)", f"$ {no:,.0f}")
        except:
            st.warning("Revisa el formato de la columna PRECIO en el Sheet.")

        st.divider()

        # 2. GANTT
        st.subheader("📅 Cronograma de Trabajos")
        df_gantt = df_clean[df_clean['Estado'].isin(['SI', 'NO'])].copy()
        
        if not df_gantt.empty:
            df_gantt['ID'] = df_gantt['Patente'] + " - " + df_gantt['Vehiculo'].str[:15]
            
            fig = px.timeline(
                df_gantt,
                x_start="Inicio",
                x_end="Fin",
                y="ID",
                color="Grupo",
                hover_data=["Dias", "Estado"],
                title="Distribución de Cargas por Grupo"
            )
            fig.update_yaxes(autorange="reversed", title="")
            fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="HOY")
            
            h = max(400, len(df_gantt) * 45)
            fig.update_layout(height=h, margin=dict(t=50, b=50, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay vehículos con estado 'SI' o 'NO' para mostrar en el gráfico.")
            
        with st.expander("Ver Tabla Completa de Datos"):
            st.write(f"Total de registros cargados: {len(df_clean)}")
            st.dataframe(df_clean)

    else:
        st.error("No se pudo obtener información del nuevo Sheet. Verifica que el archivo sea público (Cualquier persona con el enlace puede leer).")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
