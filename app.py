import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Tablero de Control - TPS (Versión Español)")

if st.button("🧹 Limpiar Memoria y Recargar"):
    st.cache_data.clear()

# --- CONFIGURACIÓN ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/export?format=csv&gid="
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
            # Leemos como texto para evitar problemas iniciales
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip()
            
            # Buscamos la columna de fecha (cualquiera que empiece con FECH)
            col_fecha = next((c for c in d.columns if c.startswith('FECH')), None)
            if col_fecha:
                d = d.rename(columns={col_fecha: 'FECHA_PROMESA_RAW'})
            
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def parsear_fecha_español(texto):
    """Convierte 'miércoles, 21 de enero de 2026' en una fecha real."""
    if pd.isna(texto): return datetime.now()
    texto = str(texto).lower()
    
    # 1. Intento rápido: Formato corto (DD/MM/YYYY)
    try:
        return pd.to_datetime(texto, dayfirst=True)
    except:
        pass
        
    # 2. Intento manual: Buscar día, mes (texto) y año
    try:
        # Regex busca: (digitos) ... (palabras) ... (digitos)
        match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)', texto)
        if match:
            dia, mes_txt, anio = match.groups()
            mes_num = MESES_ES.get(mes_txt, 1) # Si no encuentra el mes, pone 1
            return datetime(int(anio), int(mes_num), int(dia))
    except:
        pass
        
    # 3. Si todo falla, devuelve HOY
    return datetime.now()

def limpiar_y_procesar(df_in):
    filas = []
    hoy = datetime.now()
    
    for _, row in df_in.iterrows():
        # A. PROCESAR FECHA CON EL TRADUCTOR
        texto_fecha = row.get('FECHA_PROMESA_RAW', '')
        f_fin = parsear_fecha_español(texto_fecha)
        
        # B. PROCESAR PAÑOS (Detecta '1,00' o '1' o '3 aprox')
        try:
            texto_panos = str(row.get('PAÑOS', '1')).replace(',', '.') # Cambiar coma por punto
            numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            dias = float(numeros[0]) if numeros else 1.0
            if dias < 0.5: dias = 1.0
        except:
            dias = 1.0
            
        # C. CALCULAR INICIO
        try:
            f_inicio = f_fin - timedelta(days=dias)
        except:
            f_inicio = hoy
            
        # Guardamos en formato lista
        filas.append({
            'Grupo': row.get('GRUPO_ORIGEN'),
            'Patente': str(row.get('PATENTE', '')),
            'Vehiculo': str(row.get('VEHICULO', '')),
            'Inicio': f_inicio, # Objeto fecha real
            'Fin': f_fin,       # Objeto fecha real
            'Dias': dias,
            'Estado': str(row.get('FAC', '')),
            'Precio': str(row.get('PRECIO', '0'))
        })
        
    return pd.DataFrame(filas)

# --- APP ---
try:
    df_raw = cargar_datos()
    
    if not df_raw.empty:
        # Procesamos con el traductor
        df_clean = limpiar_y_procesar(df_raw)
        
        # 1. MÉTRICAS (A prueba de errores)
        st.subheader("💰 Finanzas")
        try:
            df_clean['Precio_Num'] = df_clean['Precio'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
            df_clean['Precio_Num'] = pd.to_numeric(df_clean['Precio_Num'], errors='coerce').fillna(0)
            
            c1, c2, c3 = st.columns(3)
            fac = df_clean[df_clean['Estado'] == 'FAC']['Precio_Num'].sum()
            si = df_clean[df_clean['Estado'] == 'SI']['Precio_Num'].sum()
            no = df_clean[df_clean['Estado'] == 'NO']['Precio_Num'].sum()
            
            c1.metric("Facturado", f"$ {fac:,.0f}")
            c2.metric("A Facturar (SI)", f"$ {si:,.0f}")
            c3.metric("Proyectado (NO)", f"$ {no:,.0f}")
        except:
            st.warning("No se pudieron calcular los totales, revisa la columna PRECIO.")

        st.divider()

        # 2. GANTT
        st.subheader("📅 Planificación Visual")
        
        # Filtro SI / NO
        df_gantt = df_clean[df_clean['Estado'].isin(['SI', 'NO'])].copy()
        
        if not df_gantt.empty:
            df_gantt['ID'] = df_gantt['Patente'] + " " + df_gantt['Vehiculo'].str[:10]
            
            fig = px.timeline(
                df_gantt,
                x_start="Inicio",
                x_end="Fin",
                y="ID",
                color="Grupo",
                text="Dias",
                title="Cronograma de Taller"
            )
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_traces(textposition='inside')
            
            # Línea HOY
            fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura
            h = max(400, len(df_gantt) * 40)
            fig.update_layout(height=h)
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("Nota: Se interpretaron automáticamente las fechas en español (ej: '21 de enero').")
        else:
            st.info("No hay autos pendientes para mostrar.")
            
        with st.expander("Ver Datos Procesados"):
            st.dataframe(df_clean)

except Exception as e:
    st.error(f"Error desconocido: {e}")
