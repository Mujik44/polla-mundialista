import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import pytz
import plotly.express as px 

# --- CONFIGURACIÓN ---
PERU_TZ = pytz.timezone('America/Lima')

# DICCIONARIO DE BANDERAS (Mismo de antes)
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

# --- FUNCIÓN CARGAR_DATOS (LA QUE FALTABA) ---
@st.cache_data(ttl=600)
def cargar_datos():
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

# --- LÓGICA DE PUNTOS V2 ---
def calcular_puntos(pred_gc, pred_gf, pred_cl, real_gc, real_gf, real_cl):
    pts = 0
    try:
        p_gc, p_gf = int(str(pred_gc)), int(str(pred_gf))
        r_gc, r_gf = int(str(real_gc)), int(str(real_gf))
        if (p_gc == r_gc) and (p_gf == r_gf): pts += 5
        elif (1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)) == (1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)): pts += 2
        if str(pred_cl).strip().upper() == str(real_cl).strip().upper(): pts += 1
    except: pass
    return pts

def obtener_tabla(df_general, dict_participantes, fecha_corte=None):
    data = []
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            partido = df_general[(df_general['Casa'] == casa) & (df_general['Fuera'] == fuera)]
            if not partido.empty and pd.notna(partido.iloc[0]['Gol Casa']):
                if fecha_corte and partido.iloc[0]['Fecha'].date() > fecha_corte.date(): continue
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], row['Clasifica'], 
                                       partido.iloc[0]['Gol Casa'], partido.iloc[0]['Gol Fuera'], partido.iloc[0]['Clasifica'])
        data.append({'NOMBRE': nombre, 'PUNTOS': pts})
    return pd.DataFrame(data).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)

# --- APP ---
st.set_page_config(page_title="Polla Mundialista 2026", layout="wide")
st.title("🏆 Polla Mundialista 2026")

df_general, dict_participantes = cargar_datos()

# 1. TABLA PRINCIPAL
st.subheader("📊 Tabla de Posiciones General")
st.table(obtener_tabla(df_general, dict_participantes))

st.markdown("---")

# 2. HISTÓRICO
st.subheader("📅 Historial y Jornadas")
fecha_actual = datetime.now(PERU_TZ).date()
fecha_sel = st.date_input("Seleccionar fecha:", value=fecha_actual, min_value=datetime(2026, 6, 28).date(), max_value=fecha_actual)

st.table(obtener_tabla(df_general, dict_participantes, pd.Timestamp(fecha_sel)))

# 3. RESULTADOS DEL DÍA
st.markdown(f"#### ⚽ Resultados del {fecha_sel.strftime('%d/%m/%Y')}")
partidos = df_general[df_general['Fecha'].dt.date == fecha_sel]
puntos_dia_lista = [] # <--- AÑADIDO: Inicialización necesaria

if not partidos.empty:
    for _, partido in partidos.iterrows():
        # Encabezado del partido
        st.write(f"---")
        st.write(f"### {obtener_bandera(partido['Casa'])} {partido['Casa']} vs {partido['Fuera']} {obtener_bandera(partido['Fuera'])}")
        st.write(f"**Resultado Real:** {partido['Gol Casa']}-{partido['Gol Fuera']} | **Clasifica:** {partido['Clasifica']}")
        
        # Tabla para mostrar predicciones de todos los participantes
        predicciones_partido = []
        for nombre, df_p in dict_participantes.items():
            pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
            if not pred.empty:
                p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], pred.iloc[0]['Clasifica'], 
                                    partido['Gol Casa'], partido['Gol Fuera'], partido['Clasifica'])
                predicciones_partido.append({
                    "Participante": nombre,
                    "Predicción": f"{pred.iloc[0]['Gol Casa']}-{pred.iloc[0]['Gol Fuera']}",
                    "Clasifica": pred.iloc[0]['Clasifica'],
                    "Puntos": p
                })
                puntos_dia_lista.append({'Participante': nombre, 'Puntos': p})
        
        # Mostrar predicciones en tabla
        if predicciones_partido:
            df_pred = pd.DataFrame(predicciones_partido)
            st.table(df_pred)
    
    # Gráfico de puntos diarios
    if puntos_dia_lista:
        df_dia = pd.DataFrame(puntos_dia_lista).groupby('Participante')['Puntos'].sum().reset_index()
        st.subheader("📈 Rendimiento del día")
        fig = px.bar(df_dia, x='Participante', y='Puntos', color='Puntos', text='Puntos', color_continuous_scale='Bluered')
        st.plotly_chart(fig, use_container_width=True)
        
else:
    st.info("No hay partidos programados para esta fecha.")