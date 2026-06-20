import streamlit as st
import pandas as pd
import gspread

# --- MENÚ LATERAL: REGLAS Y MÁS ---
with st.sidebar:
    st.header("ℹ️ Información")
    with st.expander("📜 Reglas de Puntuación"):
        st.write("""
        Para asegurar una competencia justa, estas son las reglas:
        
        * **Resultado Exacto**: 2 puntos.
        * **Acertar Ganador (1X2)**: 1 punto.
        * **Resultado Errado**: 0 puntos.
        
        *Nota: Se considera el resultado final (90 min).*
        """)
    
    st.divider()
    st.write("💡 *Tip: Puedes ver el historial de la tabla desplegando la opción debajo de la tabla principal.*")

# Configuración de la página
st.set_page_config(page_title="Polla Mundialista 2026", layout="wide")
st.title("🏆 Polla Mundialista 2026 - Dashboard en Vivo")

def calcular_puntos(pred_gc, pred_gf, real_gc, real_gf):
    pred_gc, pred_gf = str(pred_gc).strip(), str(pred_gf).strip()
    real_gc, real_gf = str(real_gc).strip(), str(real_gf).strip()
    
    if not pred_gc or not pred_gf or not real_gc or not real_gf:
        return 0
    
    try:
        p_gc, p_gf = int(pred_gc), int(pred_gf)
        r_gc, r_gf = int(real_gc), int(real_gf)
        
        if (p_gc == r_gc) and (p_gf == r_gf):
            return 2
        real_res = 1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)
        pred_res = 1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)
        return 1 if real_res == pred_res else 0
    except ValueError:
        return 0

@st.cache_data(ttl=600)
def cargar_datos():
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open("POLLA MUNDIAL 2026")
    
    ws_gen = sh.worksheet("GENERAL")
    df_gen = pd.DataFrame(ws_gen.get_all_records())
    df_gen = df_gen.loc[:, ~df_gen.columns.str.contains('^Unnamed')]

    participantes = ['ANGEL', 'RAI', 'JEFRY', 'JOSE MIGUEL', 'DIEGO', 'PITUS']
    dict_participantes = {}
    
    for p in participantes:
        try:
            ws_p = sh.worksheet(p)
            df_p = pd.DataFrame(ws_p.get_all_records())
            dict_participantes[p] = df_p.loc[:, ~df_p.columns.str.contains('^Unnamed')]
        except:
            continue
            
    return df_gen, dict_participantes

try:
    df_general, dict_participantes = cargar_datos()
    
    resultados_reales = {}
    for _, row in df_general.iterrows():
        casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
        if pd.notna(row['Gol Casa']) and pd.notna(row['Gol Fuera']):
            resultados_reales[(casa, fuera)] = (row['Gol Casa'], row['Gol Fuera'])

    puntos_totales = []
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            if (casa, fuera) in resultados_reales:
                r_gc, r_gf = resultados_reales[(casa, fuera)]
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], r_gc, r_gf)
        puntos_totales.append({'NOMBRE': nombre, 'PUNTOS': pts})

    df_tabla = pd.DataFrame(puntos_totales).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)
    df_tabla.index += 1

    # --- 3. SISTEMA DE PREMIOS Y LOGROS ---
    st.subheader("🏆 Estadísticas Destacadas")

    # Calcular "El Oráculo": contador de aciertos exactos (2 puntos)
    oraculos = {}
    for nombre, df_p in dict_participantes.items():
        aciertos_exactos = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            if (casa, fuera) in resultados_reales:
                r_gc, r_gf = resultados_reales[(casa, fuera)]
                # Si calcular_puntos devuelve 2, es un acierto exacto
                if calcular_puntos(row['Gol Casa'], row['Gol Fuera'], r_gc, r_gf) == 2:
                    aciertos_exactos += 1
        oraculos[nombre] = aciertos_exactos

    # Identificar al mejor
    mejor_oraculo = max(oraculos, key=oraculos.get)
    cantidad_aciertos = oraculos[mejor_oraculo]

    # Mostrar métricas
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Líder General", df_tabla.iloc[0]['NOMBRE'], f"{df_tabla.iloc[0]['PUNTOS']} pts")
    with col2:
        st.metric("🏆 La Posha mas grande", mejor_oraculo, f"{cantidad_aciertos} aciertos exactos")

    st.info("💡 **Logro 'La Posha mas grande'**: Es para el enfermo con la mayor cantidad de resultados exactos (2 pts) acertados hasta el momento.")
    
    st.subheader("📊 Tabla de Posiciones Actual")
    st.table(df_tabla)
    st.success("La tabla se actualiza automáticamente desde Google Sheets.")

    # --- DASHBOARD DE JORNADA HISTÓRICA ---
    with st.expander("📅 Ver estado de la Polla en una fecha específica"):
        if 'Fecha' in df_general.columns:
            # 1. Aseguramos formato correcto (día/mes/año) convirtiendo a datetime
            df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True, errors='coerce')
            
            # 2. Definimos límites estrictos del calendario (11 al 27 de junio de 2026)
            inicio_rango = pd.Timestamp(2026, 6, 11).date()
            fin_rango = pd.Timestamp(2026, 6, 27).date()
            
            # 3. Calendario con restricciones de rango
            fecha_sel = st.date_input(
                "Selecciona el día de la jornada:",
                value=min(max(pd.Timestamp.now().date(), inicio_rango), fin_rango),
                min_value=inicio_rango,
                max_value=fin_rango
            )
            
            fecha_sel = pd.Timestamp(fecha_sel) # Convertimos a Timestamp para comparar

            # 1. Tabla acumulada al final de ese día
            df_hist = df_general[df_general['Fecha'] <= fecha_sel]
            
            # Cálculo de tabla acumulada
            hist_data = []
            for nombre, df_p in dict_participantes.items():
                pts = 0
                for _, row in df_p.iterrows():
                    casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
                    partido = df_hist[(df_hist['Casa'] == casa) & (df_hist['Fuera'] == fuera)]
                    if not partido.empty and pd.notna(partido.iloc[0]['Gol Casa']):
                        pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], partido.iloc[0]['Gol Casa'], partido.iloc[0]['Gol Fuera'])
                hist_data.append({'Participante': nombre, 'Puntos': pts})
            
            df_tabla_hist = pd.DataFrame(hist_data).sort_values(by='Puntos', ascending=False).reset_index(drop=True)
            
            st.subheader(f"📊 Tabla al {fecha_sel.strftime('%d/%m/%Y')}")
            st.table(df_tabla_hist)

            # 2. Resultados de los partidos de ese día exacto
            st.subheader(f"⚽ Partidos jugados el {fecha_sel.strftime('%d/%m/%Y')}")
            partidos_dia = df_general[df_general['Fecha'] == fecha_sel]
            
            if not partidos_dia.empty:
                for _, p in partidos_dia.iterrows():
                    st.write(f"**{p['Casa']} vs {p['Fuera']}**: {p['Gol Casa']} - {p['Gol Fuera']}")
                
                # 3. Gráfico comparativo de Puntos Totales (Plotly)
                import plotly.express as px
                fig = px.bar(df_tabla_hist, x='Participante', y='Puntos', 
                             title=f"Rendimiento acumulado al {fecha_sel.strftime('%d/%m/%Y')}",
                             color='Puntos', color_continuous_scale='Greens')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se jugaron partidos en esta fecha.")
        else:
            st.warning("Columna 'Fecha' no encontrada.")

except Exception as e:
    st.error(f"Error al cargar datos: {e}")