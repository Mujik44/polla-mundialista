import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import pytz

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

# --- LÓGICA DE PUNTOS V2 (ACUMULATIVA) ---
def calcular_puntos(pred_gc, pred_gf, pred_cl, real_gc, real_gf, real_cl):
    pts = 0
    try:
        p_gc, p_gf = int(str(pred_gc)), int(str(pred_gf))
        r_gc, r_gf = int(str(real_gc)), int(str(real_gf))
        # 3 (Exacto) + 2 (Ganador) + 1 (Clasifica) = 6 máximo
        if (p_gc == r_gc) and (p_gf == r_gf):
            pts += 5 # 3+2
        elif (1 if r_gc > r_gf else (-1 if r_gc < r_gf else 0)) == (1 if p_gc > p_gf else (-1 if p_gc < p_gf else 0)):
            pts += 2
        if str(pred_cl).strip().upper() == str(real_cl).strip().upper():
            pts += 1
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

# 1. TABLA PRINCIPAL (FIJA)
st.subheader("📊 Tabla de Posiciones General")
st.table(obtener_tabla(df_general, dict_participantes))

st.markdown("---")

# 2. HISTÓRICO Y CALENDARIO (EN FILAS)
st.subheader("📅 Historial y Jornadas")
fecha_actual = datetime.now(PERU_TZ).date()
fecha_sel = st.date_input("Seleccionar fecha para consultar:", 
                          value=fecha_actual, 
                          min_value=datetime(2026, 6, 28).date(), 
                          max_value=fecha_actual)

# Fila 1: Tabla Acumulada
st.markdown(f"#### 📈 Tabla Acumulada al {fecha_sel.strftime('%d/%m/%Y')}")
st.table(obtener_tabla(df_general, dict_participantes, pd.Timestamp(fecha_sel)))

# Fila 2: Resultados del Día
st.markdown(f"#### ⚽ Resultados del {fecha_sel.strftime('%d/%m/%Y')}")
partidos = df_general[df_general['Fecha'].dt.date == fecha_sel]

if not partidos.empty:
    for _, partido in partidos.iterrows():
        st.write(f"**{obtener_bandera(partido['Casa'])} {partido['Casa']} vs {partido['Fuera']} {obtener_bandera(partido['Fuera'])}** | Final: {partido['Gol Casa']}-{partido['Gol Fuera']} | Clasifica: {partido['Clasifica']}")
        for nombre, df_p in dict_participantes.items():
            pred = df_p[(df_p['Casa'] == partido['Casa']) & (df_p['Fuera'] == partido['Fuera'])]
            if not pred.empty:
                p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], pred.iloc[0]['Clasifica'], 
                                    partido['Gol Casa'], partido['Gol Fuera'], partido['Clasifica'])
                puntos_dia_lista.append({'Participante': nombre, 'Puntos': p})
        st.divider()
    
    # Gráfico de puntos diarios
    if puntos_dia_lista:
        df_dia = pd.DataFrame(puntos_dia_lista).groupby('Participante')['Puntos'].sum().reset_index()
        st.subheader("📈 Rendimiento del día")
        st.plotly_chart(px.bar(df_dia, x='Participante', y='Puntos', color='Puntos', text='Puntos', color_continuous_scale='Bluered'))
        
else:
    st.info("No hay partidos programados para esta fecha.")

