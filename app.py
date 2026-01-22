import urllib.parse # Nueva importación necesaria

@st.cache_data(ttl=300)
def cargar_datos():
    pestanas = ["GRUPO UNO", "GRUPO DOS", "GRUPO 3", "TERCEROS"]
    lista_dfs = []
    for p in pestanas:
        try:
            # Codificamos el nombre de la pestaña para que acepte espacios (ej: GRUPO%20UNO)
            p_codificada = urllib.parse.quote(p)
            df_p = conn.read(spreadsheet=url, worksheet=p) 
            
            # Si el método anterior falla, usamos una alternativa más robusta:
            df_p.columns = df_p.columns.str.strip()
            df_p['GRUPO_ORIGEN'] = p
            lista_dfs.append(df_p)
        except Exception as e:
            # Si falla por el nombre, intentamos leerla sin espacios si es que usaste st.connection
            st.error(f"Error en pestaña {p}: {e}")
            
    if not lista_dfs:
        return pd.DataFrame() # Retorna vacío si no leyó nada
        
    return pd.concat(lista_dfs, ignore_index=True)
