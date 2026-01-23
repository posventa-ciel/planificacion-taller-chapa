# --- LÓGICA DEL GANTT (CORREGIDA) ---
        # Aseguramos que PAÑOS sea entero para el cálculo
        df_gantt['PAÑOS'] = df_gantt['PAÑOS'].astype(int)
        
        # Nueva forma de calcular Fecha_Inicio para evitar el error
        df_gantt['Fecha_Inicio'] = df_gantt.apply(lambda x: x['FECH/PROM'] - pd.Timedelta(days=x['PAÑOS']), axis=1)
        
        # Etiqueta para el gráfico
        df_gantt['Detalle'] = df_gantt['PATENTE'].astype(str) + " - " + df_gantt['VEHICULO'].astype(str)

        if not df_gantt.empty:
            st.subheader("📅 Cronograma de Trabajos (Gantt)")
            
            # Usamos plotly.express para el Gantt
            fig = px.timeline(
                df_gantt, 
                x_start="Fecha_Inicio", 
                x_end="FECH/PROM", 
                y="GRUPO_ORIGEN", 
                color="GRUPO_ORIGEN",
                hover_name="Detalle",
                text="PATENTE", # Esto pone la patente adentro de la barra
                labels={"GRUPO_ORIGEN": "Grupo de Trabajo"},
                title="Programación por Grupo (Estimada: 1 día por paño)"
            )
            
            # Ajustes visuales para que se vea más profesional
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(textposition='inside', insidetextanchor='middle')
            fig.update_layout(
                height=500, 
                showlegend=True,
                xaxis_title="Calendario",
                yaxis_title="Grupo de Trabajo"
            )
            
            st.plotly_chart(fig, use_container_width=True)
