import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Taller Autociel", layout="wide")

# --- TÍTULO ---
st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

# --- CONFIGURACIÓN DE GIDs REALES ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1HeZ4LyRHndRE3OiBAUjpVVk3j6GBXy7qzi5QVby6RWw/export?format=csv&gid="

GIDS = {
    "GRUPO UNO": "609774337",
    "GRUPO DOS": "1212138688",
    "GRUPO TRES": "527300176",
    "TERCEROS": "431495457",
    "PARABRISAS": "37356499"
}

@st.cache_data(ttl=60)
def cargar_datos_taller():
    lista_dfs = []
    for nombre, gid in GIDS.items():
        try:
            url = f"{URL_BASE}{gid}"
            # Forzamos la lectura como texto para evitar errores de interpretación automática
            df_p = pd.read_csv(url, dtype=str)
            df_p.columns = df_p.columns.str.strip()
            
            if 'PATENTE' in df_p.columns:
                df_p = df_p.dropna(subset=['PATENTE'])
                df_p['GRUPO_ORIGEN'] = nombre
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error cargando pestaña {nombre}: {e}")
    
    if not lista_dfs: return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

# --- LÓGICA DE CÁLCULO SEGURA (FILA POR FILA) ---
def calcular_fecha_inicio(row, hoy):
    try:
        # 1. Obtener Fecha Fin
        fecha_fin = pd.to_datetime(row['FECH/PROM'], dayfirst=True, errors='coerce')
        if pd.isna(fecha_fin):
            fecha_fin = hoy # Si no hay fecha, usamos HOY
        
        # 2. Obtener Paños (Días)
        try:
            dias = float(row['PAÑOS'])
            if dias < 1: dias = 1
        except:
            dias = 1.0 # Si falla la conversión, asumimos 1 día
            
        # 3. Restar usando Timedelta explícito
        return fecha_fin - pd.Timedelta(days=dias), fecha_fin, dias
    except:
        return hoy, hoy, 1.0 # En caso de error total, devolvemos HOY

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        hoy_dt = pd.Timestamp(datetime.now().date())

        # --- LIMPIEZA Y PREPARACIÓN ---
        # Aplicamos la función segura fila por fila
        resultado_fechas = df.apply(lambda row: calcular_fecha_inicio(row, hoy_dt), axis=1, result_type='expand')
        df['Fecha_Inicio'] = resultado_fechas[0]
        df['Fecha_Fin_Ref'] = resultado_fechas[1]
        df['Paños_Calc'] = resultado_fechas[2]

        # Limpieza de Precios (Formato Argentina)
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # --- 1. MÉTRICAS (KPIs) ---
        st.subheader("💰 Tablero Financiero")
        c1, c2, c3 = st.columns(3)
        
        # Filtrado simple por columna FAC
        fac_si = df[df['FAC'] == 'SI']
        fac_no = df[df['FAC'] == 'NO']
        ya_fac = df[df['FAC'] == 'FAC']

        c1.metric("Ya Facturado (FAC)", f"$ {ya_fac['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {fac_si['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {fac_no['PRECIO'].sum():,.0f}")

        st.divider()

        # --- 2. GANTT VISUAL ---
        st.subheader("📅 Cronograma de Taller (Gantt)")
        
        # Filtramos solo lo pendiente (SI / NO)
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()
        
        # Filtro de Grupo Opcional
        grupos_unicos = df_gantt['GRUPO_ORIGEN'].unique()
        grupo_sel = st.multiselect("Filtrar por Grupo:", grupos_unicos, default=grupos_unicos)
        df_gantt = df_gantt[df_gantt['GRUPO_ORIGEN'].isin(grupo_sel)]

        if not df_gantt.empty:
            # Creamos etiqueta visual
            df_gantt['ID_VISUAL'] = df_gantt['PATENTE'].fillna('S/P') + " " + df_gantt['VEHICULO'].fillna('')

            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="Fecha_Fin_Ref", 
                y="ID_VISUAL", 
                color="GRUPO_ORIGEN",
                hover_name="ID_VISUAL",
                text="Paños_Calc",
                title="Planificación de Unidades"
            )
            
            fig.update_yaxes(autorange="reversed", title="") # Invertir para ver lista de arriba a abajo
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            
            # Línea Roja de HOY
            fig.add_vline(x=hoy_dt, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura automática: 40 pixeles por auto
            altura = max(400, len(df_gantt) * 40)
            fig.update_layout(height=altura)
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("ℹ️ El número en la barra son los paños estimados. La línea roja es la fecha de hoy.")
        else:
            st.info("No hay trabajos pendientes (SI/NO) para mostrar en el gráfico.")

        # --- 3. TABLA DE DATOS ---
        with st.expander("📂 Ver Planilla Completa"):
            st.dataframe(df[['GRUPO_ORIGEN', 'PATENTE', 'VEHICULO', 'PAÑOS', 'FECH/PROM', 'FAC', 'ASESOR']], use_container_width=True)

        # --- DIAGNÓSTICO (Solo visible si hay problemas) ---
        # st.write("Diagnóstico de Tipos de Datos:", df.dtypes) 

except Exception as e:
    st.error(f"Error detectado: {e}")
    st.warning("Prueba recargando la página. Si persiste, verifica que la columna PAÑOS solo tenga números.")
