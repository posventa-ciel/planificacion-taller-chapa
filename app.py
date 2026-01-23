import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Gestión Taller Autociel", layout="wide")
st.title("🚀 Tablero de Control - TPS (Modo Seguro)")

# Botón para limpiar cualquier basura en memoria
if st.button("🧹 Limpiar y Recargar"):
    st.cache_data.clear()

# --- DATOS ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/export?format=csv&gid="
GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

@st.cache_data(ttl=60)
def cargar_datos():
    dfs = []
    for n, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            # Leemos TODO como texto para evitar que pandas "piense" demasiado
            d = pd.read_csv(url, dtype=str)
            d.columns = d.columns.str.strip() # Limpiar espacios en nombres de columnas
            
            # --- DETECCIÓN AUTOMÁTICA DE COLUMNAS ---
            # Buscamos la columna que tenga la fecha, empiece como empiece
            col_fecha = next((c for c in d.columns if c.startswith('FECH')), None)
            if col_fecha:
                d = d.rename(columns={col_fecha: 'FECHA_PROMESA_STD'})
            
            if 'PATENTE' in d.columns:
                d = d.dropna(subset=['PATENTE'])
                d['GRUPO_ORIGEN'] = n
                dfs.append(d)
        except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# --- CÁLCULO MANUAL (SIN PANDAS) ---
def procesar_fechas(df_in):
    filas_listas = []
    hoy = datetime.now()

    for idx, row in df_in.iterrows():
        # 1. FECHA FIN
        try:
            # Intentamos leer la columna estandarizada
            texto_fecha = str(row.get('FECHA_PROMESA_STD', ''))
            f_fin = pd.to_datetime(texto_fecha, dayfirst=True)
            if pd.isna(f_fin): f_fin = hoy
        except: f_fin = hoy
        
        # 2. PAÑOS (DÍAS)
        try:
            texto_panos = str(row.get('PAÑOS', '1'))
            # Buscamos números
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", texto_panos)
            dias = float(nums[0]) if nums else 1.0
            if dias < 0.5: dias = 1.0
        except: dias = 1.0

        # 3. FECHA INICIO (MATEMÁTICA SEGURA)
        try:
            f_inicio = f_fin - timedelta(days=dias)
        except:
            f_inicio = f_fin

        # 4. GUARDAR COMO TEXTO (ESTO EVITA EL ERROR CRÍTICO EN PLOTLY)
        # Convertimos a string YYYY-MM-DD para que Plotly no haga cuentas raras
        filas_listas.append({
            "Grupo": row.get('GRUPO_ORIGEN', 'Desconocido'),
            "Patente": str(row.get('PATENTE', '')),
            "Vehiculo": str(row.get('VEHICULO', '')),
            "Inicio": f_inicio.strftime('%Y-%m-%d'), # <--- Clave: Pasamos texto
            "Fin": f_fin.strftime('%Y-%m-%d'),       # <--- Clave: Pasamos texto
            "Dias": f"{dias:.1f}",
            "Estado": str(row.get('FAC', '')),
            "Precio_Raw": str(row.get('PRECIO', '0'))
        })
    
    return pd.DataFrame(filas_listas)

# --- APP ---
try:
    df_raw = cargar_datos()
    
    if not df_raw.empty:
        # Procesamos los datos en un dataframe nuevo y limpio
        df_clean = procesar_fechas(df_raw)

        # 1. MÉTRICAS (Bloque Try/Except aislado para que no rompa el Gantt)
        st.subheader("💰 Finanzas")
        try:
            # Limpieza de precios sobre el dataframe limpio
            df_clean['Precio_Num'] = df_clean['Precio_Raw'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
            df_clean['Precio_Num'] = pd.to_numeric(df_clean['Precio_Num'], errors='coerce').fillna(0)
            
            c1, c2, c3 = st.columns(3)
            fac = df_clean[df_clean['Estado'] == 'FAC']['Precio_Num'].sum()
            si = df_clean[df_clean['Estado'] == 'SI']['Precio_Num'].sum()
            no = df_clean[df_clean['Estado'] == 'NO']['Precio_Num'].sum()
            
            c1.metric("Facturado", f"$ {fac:,.0f}")
            c2.metric("A Facturar (SI)", f"$ {si:,.0f}")
            c3.metric("Proyectado (NO)", f"$ {no:,.0f}")
        except Exception as e:
            st.warning(f"No se pudieron calcular los montos (Error: {e}), pero aquí tienes el Gantt:")

        st.divider()

        # 2. GANTT
        st.subheader("📅 Cronograma")
        
        # Filtramos SI/NO
        df_gantt = df_clean[df_clean['Estado'].isin(['SI', 'NO'])].copy()
        
        if not df_gantt.empty:
            # ID Visual
            df_gantt['ID'] = df_gantt['Patente'] + " " + df_gantt['Vehiculo'].str[:10]

            fig = px.timeline(
                df_gantt,
                x_start="Inicio", 
                x_end="Fin",
                y="ID",
                color="Grupo",
                text="Dias",
                title="Planificación de Trabajos"
            )
            fig.update_yaxes(autorange="reversed", title="")
            
            # Línea de HOY (calculada manualmente para evitar error de tipos)
            hoy_str = datetime.now().strftime('%Y-%m-%d')
            fig.add_vline(x=hoy_str, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura
            h = max(400, len(df_gantt) * 40)
            fig.update_layout(height=h)
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("ℹ️ Datos leídos de la columna que empieza con 'FECH...' y 'PAÑOS'.")
        else:
            st.info("No hay turnos pendientes (Estados SI/NO) para mostrar.")

        with st.expander("Ver Datos Procesados"):
            st.dataframe(df_clean)
    else:
        st.error("No se pudieron cargar datos. Verifica los permisos del Sheet.")

except Exception as e:
    st.error(f"Error desconocido: {e}")
