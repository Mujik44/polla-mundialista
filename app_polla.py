import streamlit as st
import pandas as pd
import gspread

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
    
    st.subheader("📊 Tabla de Posiciones Actual")
    st.table(df_tabla)
    st.success("La tabla se actualiza automáticamente desde Google Sheets.")

    with st.expander("📅 ¿Quieres ver cómo estaba la tabla en una fecha anterior?"):
        if 'Fecha' in df_general.columns:
            df_general['Fecha'] = pd.to_datetime(df_general['Fecha'], dayfirst=True)
            fechas_disponibles = sorted([f for f in df_general['Fecha'].unique() if f >= pd.Timestamp('2026-06-11')])
            
            if fechas_disponibles:
                fecha_sel = st.select_slider("Selecciona la fecha del histórico:", options=fechas_disponibles, format_func=lambda x: x.strftime('%d/%m/%Y'))
                df_hist = df_general[df_general['Fecha'] <= fecha_sel]
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
                df_tabla_hist.index += 1
                st.table(df_tabla_hist)
            else:
                st.write("No hay datos disponibles a partir del 11 de junio.")
        else:
            st.warning("La columna 'Fecha' no está configurada en la hoja GENERAL.")

    st.divider()
    st.subheader("🔍 Detalle por Partido")
    lista_partidos = [f"{row['Casa']} vs {row['Fuera']}" for _, row in df_general.iterrows()]
    partido_sel = st.selectbox("Selecciona un partido para ver el detalle:", lista_partidos)

    if partido_sel:
        c, f = partido_sel.split(" vs ")
        match = df_general[(df_general['Casa'] == c) & (df_general['Fuera'] == f)].iloc[0]
        st.write(f"**Resultado Real:** {match['Gol Casa']} - {match['Gol Fuera']}")
        
        detalle = []
        for nombre, df_p in dict_participantes.items():
            pred = df_p[(df_p['Casa'] == c) & (df_p['Fuera'] == f)]
            if not pred.empty:
                p = calcular_puntos(pred.iloc[0]['Gol Casa'], pred.iloc[0]['Gol Fuera'], match['Gol Casa'], match['Gol Fuera'])
                detalle.append({'Participante': nombre, 'Predicción': f"{pred.iloc[0]['Gol Casa']}-{pred.iloc[0]['Gol Fuera']}", 'Puntos': p})
        st.table(pd.DataFrame(detalle))

except Exception as e:
    st.error(f"Error al cargar datos: {e}")