import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import pytz
import plotly.express as px 

# --- DISEÑO MUNDIALISTA 2026 ---
st.markdown("""
    <style>
    /* Tipografía y fondos */
    .main {
        background-color: #F8F9FA;
    }
    
    /* Personalización de métricas */
    [data-testid="stMetricValue"] {
        color: #011E41;
        font-family: 'Arial', sans-serif;
    }
    
    /* Barra lateral */
    [data-testid="stSidebar"] {
        background-color: #011E41;
        color: white;
    }
    
    /* Botones y botones de acción */
    div.stButton > button:first-child {
        background-color: #FFD700;
        color: #011E41;
        font-weight: bold;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #011E41;
        font-family: 'Helvetica Neue', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- MENÚ LATERAL: REGLAS Y MÁS ---
with st.sidebar:
    st.header("ℹ️ Información")
    with st.expander("📜 Reglas de Puntuación"):
        st.write("""
        Para asegurar una competencia justa, estas son las reglas:
        
        * **Resultado Exacto**: 3 puntos.
        * **Acertar Ganador (1X2)**: 2 puntos.
        * **Acertar Clasificado**: 1 punto.
        * **Resultado Errado**: 0 puntos.
        
        *Nota: Se considera el resultado final (90 min).*
        """)
    
    st.divider()
    st.write("💡 *Tip: Puedes ver el historial de la tabla desplegando la opción debajo de la tabla principal.*")

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
        
        # Buscamos el partido en el df_general para obtener los resultados REALES
        partido = df_general[(df_general['Casa'] == casa) & (df_general['Fuera'] == fuera)]
        
        if not partido.empty and pd.notna(partido.iloc[0]['Gol Casa']):
            r_gc = partido.iloc[0]['Gol Casa']
            r_gf = partido.iloc[0]['Gol Fuera']
            r_cl = partido.iloc[0]['Clasifica'] # Obtenemos el clasificado REAL
            
            # Pasamos todos los argumentos, incluyendo la predicción y el real de clasificación
            pts += calcular_puntos(
                row['Gol Casa'], row['Gol Fuera'], row['Clasifica'], 
                r_gc, r_gf, r_cl
            )
            
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
            if calcular_puntos(row['Gol Casa'], row['Gol Fuera'], row['Clasifica'], r_gc, r_gf, None) >= 5:
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