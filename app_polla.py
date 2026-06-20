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
    df_corte = df_general[df_general['Fecha'].dt.date <= fecha_corte]
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

with st.sidebar:
    st.header("ℹ️ Información")
    with st.expander("📜 Reglas de Puntuación"):
        st.write("* **Resultado Exacto**: 2 pts | **Ganador**: 1 pt | **Error**: 0 pts.")

try:
    df_general, dict_participantes = cargar_datos()
    df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True, errors='coerce')
    
    # Tabla General Actual
    tabla_actual = calcular_tabla_hasta_fecha(pd.Timestamp.now(), df_general, dict_participantes)
    
    st.subheader("📊 Tabla de Posiciones Actual")
    st.table(tabla_actual.reset_index(drop=True))

    # --- DASHBOARD DE JORNADA ---
    with st.expander("📅 Ver resumen de una jornada específica"):
        inicio_rango = pd.Timestamp(2026, 6, 11).date()
        fin_rango = pd.Timestamp(2026, 6, 27).date()
        fecha_sel = st.date_input("Selecciona el día:", value=min(max(pd.Timestamp.now().date(), inicio_rango), fin_rango), 
                                  min_value=inicio_rango, max_value=fin_rango)
        
        st.subheader(f"🏆 Tabla Acumulada al {fecha_sel.strftime('%d/%m/%Y')}")
        st.table(calcular_tabla_hasta_fecha(pd.Timestamp(fecha_sel), df_general, dict_participantes).reset_index(drop=True))

        partidos_dia = df_general[df_general['Fecha'].dt.date == fecha_sel]
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