import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re # Librería para buscar números dentro de texto

# 1. Configuración de la página
st.set_page_config(page_title="Gestión de Taller Autociel", layout="wide")
st.title("🚀 Sistema de Gestión TPS - Chapa y Pintura")

# Botón de recarga
if st.button("🔄 Forzar Recarga de Datos"):
    st.cache_data.clear()

# --- CONFIGURACIÓN DE GIDs ---
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
            # Leemos todo como texto para que no falle nada
            df_p = pd.read_csv(url, dtype=str)
            df_p.columns = df_p.columns.str.strip()
            
            if 'PATENTE' in df_p.columns:
                df_p = df_p.dropna(subset=['PATENTE'])
                df_p['GRUPO_ORIGEN'] = nombre
                lista_dfs.append(df_p)
        except Exception as e:
            st.error(f"Error en pestaña {nombre}: {e}")
    
    if not lista_dfs: return pd.DataFrame()
    return pd.concat(lista_dfs, ignore_index=True)

# --- FUNCIÓN DE LIMPIEZA INTELIGENTE ---
def extraer_numero(texto):
    """Busca el primer número en un texto sucio. Ej: '3 aprox' -> 3.0"""
    try:
        texto = str(texto)
        # Busca cualquier secuencia de dígitos
        numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto)
        if numeros:
            return float(numeros[0])
        return 1.0 # Si no encuentra números, asume 1 día
    except:
        return 1.0

try:
    df_raw = cargar_datos_taller()
    
    if not df_raw.empty:
        df = df_raw.copy()
        hoy = datetime.now()

        # 1. Limpieza de Precios
        df['PRECIO'] = df['PRECIO'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.')
        df['PRECIO'] = pd.to_numeric(df['PRECIO'], errors='coerce').fillna(0)

        # 2. Limpieza de Fechas (Promesa)
        df['FECH/PROM_DT'] = pd.to_datetime(df['FECH/PROM'], dayfirst=True, errors='coerce')
        
        # 3. Limpieza de Paños (USANDO REGEX)
        # Aplicamos la función extraer_numero fila por fila
        df['PAÑOS_FLOAT'] = df['PAÑOS'].apply(extraer_numero)
        
        # Corrección: si dio 0 o negativo, ponemos 1
        df.loc[df['PAÑOS_FLOAT'] < 0.5, 'PAÑOS_FLOAT'] = 1.0

        # --- CÁLCULO DE FECHAS SEGURO ---
        fechas_fin = []
        fechas_inicio = []
        
        for fecha_promesa, paños in zip(df['FECH/PROM_DT'], df['PAÑOS_FLOAT']):
            # Definir Fin
            if pd.isna(fecha_promesa):
                fin = hoy
            else:
                fin = fecha_promesa
            
            # Definir Inicio (Fin - Días)
            try:
                # timedelta solo acepta floats estándar, no cosas raras
                inicio = fin - timedelta(days=float(paños))
            except:
                inicio = fin # Si falla, la barra es un punto en el día de hoy
            
            fechas_fin.append(fin)
            fechas_inicio.append(inicio)

        df['Fecha_Fin_Real'] = fechas_fin
        df['Fecha_Inicio_Real'] = fechas_inicio

        # --- VISUALIZACIÓN ---
        st.subheader("💰 Resumen Financiero")
        c1, c2, c3 = st.columns(3)
        c1.metric("Ya Facturado (FAC)", f"$ {df[df['FAC'] == 'FAC']['PRECIO'].sum():,.0f}")
        c2.metric("A Facturar Mes (SI)", f"$ {df[df['FAC'] == 'SI']['PRECIO'].sum():,.0f}")
        c3.metric("Próximo Mes (NO)", f"$ {df[df['FAC'] == 'NO']['PRECIO'].sum():,.0f}")

        st.divider()

        st.subheader("📅 Cronograma de Taller (Gantt)")
        
        # Filtros
        df_gantt = df[df['FAC'].isin(['SI', 'NO'])].copy()
        grupos = df_gantt['GRUPO_ORIGEN'].unique().tolist()
        sel_grupos = st.multiselect("Filtrar Grupos:", grupos, default=grupos)
        df_gantt = df_gantt[df_gantt['GRUPO_ORIGEN'].isin(sel_grupos)]

        if not df_gantt.empty:
            df_gantt['ID_AUTO'] = df_gantt['PATENTE'].astype(str) + " (" + df_gantt['VEHICULO'].astype(str).str[:15] + ")"

            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio_Real", 
                x_end="Fecha_Fin_Real", 
                y="ID_AUTO", 
                color="GRUPO_ORIGEN",
                hover_name="ID_AUTO",
                text="PAÑOS_FLOAT",
                title="Planificación (Días extraídos de la columna Paños)"
            )
            
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            fig.add_vline(x=hoy, line_dash="dash", line_color="red", annotation_text="HOY")
            
            # Altura dinámica
            altura = max(400, len(df_gantt) * 35)
            fig.update_layout(height=altura)
            
            st.plotly_chart(fig, use_container_width=True)
            st.caption("ℹ️ El sistema extrajo automáticamente los números de la columna Paños. Si decía '3 aprox', calculó 3 días.")
        else:
            st.info("No hay unidades pendientes para mostrar.")
            
        with st.expander("🔍 Ver Datos Crudos"):
            st.dataframe(df)

except Exception as e:
    st.error(f"Error inesperado: {e}")
