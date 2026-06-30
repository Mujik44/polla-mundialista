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

# --- FUNCIONES V2 (PUNTUACIÓN ACUMULATIVA) ---
def calcular_puntos(pred_gc, pred_gf, pred_cl, real_gc, real_gf, real_cl):
    pts = 0
    try:
        p_gc, p_gf = int(str(pred_gc)), int(str(pred_gf))
        r_gc, r_gf = int(str(real_gc)), int(str(real_gf))
        
        if (p_gc == r_gc) and (p_gf == r_gf):
            pts += 3  # Exacto
            pts += 2  # + Ganador
        else:
            real_res = 1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)
            pred_res = 1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)
            if real_res == pred_res:
                pts += 2  # Solo ganador
        
        if str(pred_cl).strip().upper() == str(real_cl).strip().upper():
            pts += 1
    except: pass
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
    return pd.DataFrame(hist_data).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def cargar_datos():
    # Asegúrate de tener tus credenciales en st.secrets
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open("POLLA MUNDIAL 2026")
    df_gen = pd.DataFrame(sh.worksheet("GENERAL").get_all_records())
    df_gen['Fecha'] = pd.to_datetime(df_gen['Fecha'], dayfirst=True, errors='coerce')
    
    participantes = ['ANGEL', 'RAI', 'JEFRY', 'JOSE MIGUEL', 'DIEGO', 'PITUS']
    dict_part = {}
    for p in participantes:
        try:
            df_p = pd.DataFrame(sh.worksheet(p).get_all_records())
            dict_part[p] = df_p.loc[:, ~df_p.columns.str.contains('^Unnamed')]
        except: continue
    return df_gen, dict_part

# --- APP ---
st.set_page_config(page_title="Polla V2", layout="wide")
st.title("🏆 Polla Mundialista 2026 - Fase KO (V2)")

df_general, dict_participantes = cargar_datos()

# --- MÓDULO DE JORNADA Y TABLA HISTÓRICA ---
with st.expander("📅 Ver resumen de jornada y tabla histórica", expanded=True):
    fecha_sel = st.date_input("Selecciona el día:", value=df_general['Fecha'].max().date())
    
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader(f"📊 Tabla Acumulada al {fecha_sel.strftime('%d/%m/%Y')}")
        st.table(calcular_tabla_hasta_fecha(pd.Timestamp(fecha_sel), df_general, dict_participantes))
        
    with col_b:
        partidos_dia = df_general[df_general['Fecha'].dt.date == fecha_sel]
        st.subheader(f"⚽ Partidos: {fecha_sel.strftime('%d/%m/%Y')}")
        
        puntos_dia_data = []
        for _, partido in partidos_dia.iterrows():
            st.markdown(f"**{obtener_bandera(partido['Casa'])} {partido['Casa']}** vs **{obtener_bandera(partido['Fuera'])} {partido['Fuera']}** | Res: {partido['Gol Casa']}-{partido['Gol Fuera']} | Cla: {partido['Clasifica']}")
            for nombre, df_p in dict_participantes.items():
                pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
                if not pred.empty:
                    p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], pred.iloc[0]['Clasifica'], 
                                        partido['Gol Casa'], partido['Gol Fuera'], partido['Clasifica'])
                    st.write(f"- {nombre}: {p} pts")
                    puntos_dia_data.append({'Participante': nombre, 'Puntos': p})
            st.divider()

        if puntos_dia_data:
            st.subheader("📈 Rendimiento del día")
            df_puntos_dia = pd.DataFrame(puntos_dia_data).groupby('Participante')['Puntos'].sum().reset_index()
            fig = px.bar(df_puntos_dia, x='Participante', y='Puntos', color='Puntos', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)