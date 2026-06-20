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

    # --- DASHBOARD DE JORNADA (SOLO EL DÍA SELECCIONADO) ---
    with st.expander("📅 Ver resumen de una jornada específica"):
        if 'Fecha' in df_general.columns:
            # 1. Configuración de fechas y formato
            df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True, errors='coerce')
            inicio_rango = pd.Timestamp(2026, 6, 11).date()
            fin_rango = pd.Timestamp(2026, 6, 27).date()
            
            fecha_sel = st.date_input("Selecciona el día:", value=min(max(pd.Timestamp.now().date(), inicio_rango), fin_rango), 
                                      min_value=inicio_rango, max_value=fin_rango)
            
            # --- TABLA ACUMULADA HASTA ESA FECHA ---
            st.subheader(f"🏆 Tabla Acumulada al {fecha_sel.strftime('%d/%m/%Y')}")
            df_acumulada = calcular_tabla_hasta_fecha(fecha_sel) # Asegúrate de tener esta función o lógica
            st.table(df_acumulada.reset_index(drop=True))

            # 2. Filtrar partidos del día
            partidos_dia = df_general[df_general['Fecha'].dt.date == fecha_sel]
            
            if not partidos_dia.empty:
                st.subheader(f"⚽ Resultados y Predicciones: {fecha_sel.strftime('%d/%m/%Y')}")
                
                # Preparar datos de puntos del día
                puntos_dia_data = []
                
                for _, partido in partidos_dia.iterrows():
                    st.markdown(f"**{partido['Casa']} vs {partido['Fuera']}** | Resultado Real: {partido['Gol Casa']} - {partido['Gol Fuera']}")
                    
                    # Mostrar predicciones individuales por partido
                    for nombre, df_p in dict_participantes.items():
                        pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
                        if not pred.empty:
                            p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], partido['Gol Casa'], partido['Gol Fuera'])
                            st.write(f"- **{nombre}**: {pred.iloc[0]['Gol Casa']}-{pred.iloc[0]['Gol Fuera']} ({p} pts)")
                            puntos_dia_data.append({'Participante': nombre, 'Puntos': p})
                    st.divider()

                # 3. Gráfico y tabla de puntos del día
                df_puntos_dia = pd.DataFrame(puntos_dia_data).groupby('Participante')['Puntos'].sum().reset_index()
                
                st.subheader("📈 Rendimiento del día")
                import plotly.express as px
                fig = px.bar(df_puntos_dia, x='Participante', y='Puntos', 
                             title=f"Puntos obtenidos solo el {fecha_sel.strftime('%d/%m/%Y')}",
                             color='Puntos', color_continuous_scale='Blues')
                st.plotly_chart(fig, use_container_width=True)
                
                st.table(df_puntos_dia.sort_values(by='Puntos', ascending=False).reset_index(drop=True))
            else:
                st.info("No hay partidos jugados en esta fecha.")

except Exception as e:
    st.error(f"Error al cargar datos: {e}")