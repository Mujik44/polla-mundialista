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

# --- FUNCIONES ACTUALIZADAS V2 ---
def calcular_puntos(pred_gc, pred_gf, pred_cl, real_gc, real_gf, real_cl):
    pts = 0
    try:
        p_gc, p_gf = int(str(pred_gc)), int(str(pred_gf))
        r_gc, r_gf = int(str(real_gc)), int(str(real_gf))
        
        # 1. Puntaje por Marcador y Ganador
        if (p_gc == r_gc) and (p_gf == r_gf):
            pts += 3  # Marcador Exacto
            pts += 2  # También es ganador
        else:
            real_res = 1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)
            pred_res = 1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)
            if real_res == pred_res:
                pts += 2  # Solo ganador
        
        # 2. Puntaje por Clasifica
        if str(pred_cl).strip().upper() == str(real_cl).strip().upper():
            pts += 1
            
    except: 
        pass
    return pts

def calcular_tabla_hasta_fecha(fecha_corte, df_general, dict_participantes):
    hist_data = []
    df_corte = df_general[df_general['Fecha'].dt.date <= pd.Timestamp(fecha_corte).date()]
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            partido = df_corte[(df_corte['Casa'] == casa) & (df_corte['Fuera'] == fuera)]
            if not partido.empty and pd.notna(partido.iloc[0]['Gol Casa']):
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], row['Clasifica'], 
                                       partido.iloc[0]['Gol Casa'], partido.iloc[0]['Gol Fuera'], partido.iloc[0]['Clasifica'])
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
st.set_page_config(page_title="Polla V2 - Fase KO", layout="wide")
st.title("🏆 Polla Mundialista 2026 - Fase KO (V2)")

with st.sidebar:
    st.header("ℹ️ Reglas V2")
    st.write("""
    * **Marcador Exacto**: 3 pts
    * **Acertar Ganador**: 2 pts
    * **Acertar Clasificado**: 1 pt
    * **Máximo por partido**: 6 pts (Exacto + Clasifica)
    """)

try:
    df_general, dict_participantes = cargar_datos()
    df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True, errors='coerce')

    # Calcular Tabla
    puntos_totales = []
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            partido_real = df_general[(df_general['Casa'] == casa) & (df_general['Fuera'] == fuera)]
            if not partido_real.empty and pd.notna(partido_real.iloc[0]['Gol Casa']):
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], row['Clasifica'],
                                       partido_real.iloc[0]['Gol Casa'], partido_real.iloc[0]['Gol Fuera'], partido_real.iloc[0]['Clasifica'])
        puntos_totales.append({'NOMBRE': nombre, 'PUNTOS': pts})

    df_tabla = pd.DataFrame(puntos_totales).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)
    
    st.subheader("📊 Tabla de Posiciones V2")
    st.table(df_tabla)

    # Resumen Jornada
    st.subheader("📅 Resultados Fase KO")
    fecha_sel = st.date_input("Selecciona fecha:", min_value=df_general['Fecha'].min(), max_value=df_general['Fecha'].max())
    partidos_dia = df_general[df_general['Fecha'].dt.date == fecha_sel]
    
    for _, partido in partidos_dia.iterrows():
        st.write(f"**{partido['Casa']} vs {partido['Fuera']}** | Resultado: {partido['Gol Casa']}-{partido['Gol Fuera']} | Clasifica: {partido['Clasifica']}")
        for nombre, df_p in dict_participantes.items():
            pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
            if not pred.empty:
                p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], pred.iloc[0]['Clasifica'], 
                                    partido['Gol Casa'], partido['Gol Fuera'], partido['Clasifica'])
                st.write(f"- {nombre}: {pred.iloc[0]['Gol Casa']}-{pred.iloc[0]['Gol Fuera']} (Clasifica: {pred.iloc[0]['Clasifica']}) -> **{p} pts**")
        st.divider()

except Exception as e:
    st.error(f"Error: {e}")