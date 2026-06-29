import streamlit as st
import pandas as pd
import gspread
import plotly.express as px

# --- DICCIONARIO DE BANDERAS ---
BANDERAS = {
    "ALEMANIA": "🇩🇪", "ARABIA SAUDÍ": "🇸🇦", "ARGELIA": "🇩🇿", "ARGENTINA": "🇦🇷", 
    "AUSTRALIA": "🇦🇺", "AUSTRIA": "🇦🇹", "BÉLGICA": "🇧🇪", "BOSNIA Y HERZEGOVINA": "🇧🇦", 
    "BRASIL": "🇧🇷", "CABO VERDE": "🇨🇻", "CANADÁ": "🇨🇦", "CHEQUIA (REPÚBLICA CHECA)": "🇨🇿", 
    "COLOMBIA": "🇨🇴", "COREA DEL SUR": "🇰🇷", "COSTA DE MARFIL": "🇨🇮", "CROACIA": "🇭🇷", 
    "CURAZAO": "🇨🇼", "ECUADOR": "🇪🇨", "EGIPTO": "🇪🇬", "EMIRATOS ÁRABES UNIDOS": "🇦🇪", 
    "ESCOCIA": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "ESPAÑA": "🇪🇸", "ESTADOS UNIDOS": "🇺🇸", "FRANCIA": "🇫🇷", 
    "GHANA": "🇬🇭", "HAITÍ": "🇭🇹", "INGLATERRA": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "IRÁN": "🇮🇷", 
    "IRAK": "🇮🇶", "JAPÓN": "🇯🇵", "JORDANIA": "🇯🇴", "MARRUECOS": "🇲🇦", 
    "MÉXICO": "🇲🇽", "NORUEGA": "🇳🇴", "NUEVA ZELANDA": "🇳🇿", "PAÍSES BAJOS": "🇳🇱", 
    "PANAMÁ": "🇵🇦", "PARAGUAY": "🇵🇾", "PORTUGAL": "🇵🇹", "QATAR": "🇶🇦", 
    "REPÚBLICA DEMOCRÁTICA DEL CONGO": "🇨🇩", "SENEGAL": "🇸🇳", "SUDÁFRICA": "🇿🇦", 
    "SUECIA": "🇸🇪", "SUIZA": "🇨🇭", "TÜRKIYE (TURQUÍA)": "🇹🇷", "TÚNEZ": "🇹🇳", 
    "UZBEKISTÁN": "🇺🇿"
}

def obtener_bandera(pais):
    return BANDERAS.get(str(pais).upper().strip(), "⚽")

# --- FUNCIONES BASE ---
def calcular_puntos(pred_gc, pred_gf, real_gc, real_gf):
    try:
        p_gc, p_gf = int(str(pred_gc)), int(str(pred_gf))
        r_gc, r_gf = int(str(real_gc)), int(str(real_gf))
        if (p_gc == r_gc) and (p_gf == r_gf): return 2
        real_res = 1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)
        pred_res = 1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)
        return 1 if real_res == pred_res else 0
    except: return 0

def calcular_tabla_hasta_fecha(fecha_corte, df_general, dict_participantes):
    hist_data = []
    df_corte = df_general[df_general['Fecha'].dt.date <= pd.Timestamp(fecha_corte).date()]
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            partido = df_corte[(df_corte['Casa'] == casa) & (df_corte['Fuera'] == fuera)]
            if not partido.empty and pd.notna(partido.iloc[0]['Gol Casa']):
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], partido.iloc[0]['Gol Casa'], partido.iloc[0]['Gol Fuera'])
        hist_data.append({'NOMBRE': nombre, 'PUNTOS': pts})
    return pd.DataFrame(hist_data).sort_values(by='PUNTOS', ascending=False)

@st.cache_data(ttl=600)
def cargar_datos():
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open("POLLA MUNDIAL 2026")
    df_gen = pd.DataFrame(sh.worksheet("GENERAL").get_all_records())
    df_gen = df_gen.loc[:, ~df_gen.columns.str.contains('^Unnamed')]
    participantes = ['ANGEL', 'RAI', 'JEFRY', 'JOSE MIGUEL', 'DIEGO', 'PITUS']
    dict_part = {}
    for p in participantes:
        try:
            df_p = pd.DataFrame(sh.worksheet(p).get_all_records())
            dict_part[p] = df_p.loc[:, ~df_p.columns.str.contains('^Unnamed')]
        except: continue
    return df_gen, dict_part

# --- APP ---
st.set_page_config(page_title="Polla Mundialista 2026", layout="wide")
st.title("🏆 Polla Mundialista 2026 - Dashboard en Vivo")

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

    # --- SISTEMA DE PREMIOS Y LOGROS ---
    st.subheader("🏆 Estadísticas Destacadas")

    # Calcular "El Oráculo": contador de aciertos exactos (2 puntos)
    data_aciertos = []
    for nombre, df_p in dict_participantes.items():
        exactos = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            if (casa, fuera) in resultados_reales:
                r_gc, r_gf = resultados_reales[(casa, fuera)]
                if calcular_puntos(row['Gol Casa'], row['Gol Fuera'], r_gc, r_gf) == 2:
                    exactos += 1
        data_aciertos.append({'Participante': nombre, 'Aciertos': exactos})

    df_exactos = pd.DataFrame(data_aciertos).sort_values(by='Aciertos', ascending=False).reset_index(drop=True)
    peor_oraculo = df_exactos.iloc[-1] # El último de la lista ordenada

    # --- FILA DE 4 COLUMNAS ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Líder General", df_tabla.iloc[0]['NOMBRE'], f"{df_tabla.iloc[0]['PUNTOS']} pts")

    with col2:
        st.metric("🍆 La Posha mas grande", df_exactos.iloc[0]['Participante'], f"{df_exactos.iloc[0]['Aciertos']} exactos")

    with col3:
        st.metric("🤏🐛 La Posha mas chica (chipi)", peor_oraculo['Participante'], f"{peor_oraculo['Aciertos']} exactos", delta_color="inverse")

    with col4:
        # Botón con ventana flotante (popover)
        with st.popover("📊 Tabla Aciertos"):
            st.write("### Ranking de Aciertos Exactos")
            st.table(df_exactos)

    st.info("💡 **Logro 'La Posha mas grande'**: Es para el enfermo con la mayor cantidad de resultados exactos (2 pts) acertados hasta el momento.")
    
    st.subheader("📊 Tabla de Posiciones Actual")
    st.table(df_tabla)
    st.success("La tabla se actualiza automáticamente desde Google Sheets.")

    df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True, errors='coerce')
    
    # Tabla General Actual
    tabla_actual = calcular_tabla_hasta_fecha(pd.Timestamp.now(), df_general, dict_participantes)

    # --- DASHBOARD DE JORNADA ---
    with st.expander("📅 Ver resumen de una jornada específica"):
        inicio_rango = pd.Timestamp(2026, 6, 11).date()
        fin_rango = pd.Timestamp(2026, 6, 27).date()
        fecha_sel = st.date_input("Selecciona el día:", value=min(max(pd.Timestamp.now().date(), inicio_rango), fin_rango), 
                                  min_value=inicio_rango, max_value=fin_rango)
        
        st.subheader(f"🏆 Tabla Acumulada al {fecha_sel.strftime('%d/%m/%Y')}")
        st.table(calcular_tabla_hasta_fecha(pd.Timestamp(fecha_sel), df_general, dict_participantes).reset_index(drop=True))

        partidos_dia = df_general[df_general['Fecha'].dt.date == pd.Timestamp(fecha_sel).date()]
        if not partidos_dia.empty:
            st.subheader(f"⚽ Resultados y Predicciones: {fecha_sel.strftime('%d/%m/%Y')}")
            puntos_dia_data = []
            for _, partido in partidos_dia.iterrows():
                st.markdown(f"**{obtener_bandera(partido['Casa'])} {partido['Casa']} vs {obtener_bandera(partido['Fuera'])} {partido['Fuera']}** | {partido['Gol Casa']} - {partido['Gol Fuera']}")
                for nombre, df_p in dict_participantes.items():
                    pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
                    if not pred.empty:
                        p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], partido['Gol Casa'], partido['Gol Fuera'])
                        st.write(f"- **{nombre}**: {pred.iloc[0]['Gol Casa']}-{pred.iloc[0]['Gol Fuera']} ({p} pts)")
                        puntos_dia_data.append({'Participante': nombre, 'Puntos': p})
                st.divider()

            df_puntos_dia = pd.DataFrame(puntos_dia_data).groupby('Participante')['Puntos'].sum().reset_index()
            st.subheader("📈 Rendimiento del día")
            st.plotly_chart(px.bar(df_puntos_dia, x='Participante', y='Puntos', color='Puntos', color_continuous_scale='Blues'), use_container_width=True)
            st.table(df_puntos_dia.sort_values(by='Puntos', ascending=False).reset_index(drop=True))
        else:
            st.info("No hay partidos en esta fecha.")

except Exception as e:
    st.error(f"Error: {e}")