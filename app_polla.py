import streamlit as st
import pandas as pd
import gspread

# Configuración de la página
st.set_page_config(page_title="Polla Mundialista 2026", layout="wide")
st.title("🏆 Polla Mundialista 2026 - Dashboard en Vivo")

# Función para calcular puntos según tus reglas
def calcular_puntos(pred_gc, pred_gf, real_gc, real_gf):
    if pd.isna(pred_gc) or pd.isna(pred_gf) or pd.isna(real_gc) or pd.isna(real_gf):
        return 0
    if (int(pred_gc) == int(real_gc)) and (int(pred_gf) == int(real_gf)):
        return 2
    real_res = 1 if int(real_gc) > int(real_gf) else (-1 if int(real_gc) < int(real_gf) else 0)
    pred_res = 1 if int(pred_gc) > int(pred_gf) else (-1 if int(pred_gc) < int(pred_gf) else 0)
    return 1 if real_res == pred_res else 0

# Cargar datos desde Google Sheets
@st.cache_data(ttl=600)
def cargar_datos():
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open("POLLA MUNDIAL 2026")
    
    # Obtener resultados reales
    df_gen = pd.DataFrame(sh.worksheet("GENERAL").get_all_records())
    
    # Obtener nombres de hojas (participantes)
    hojas = [ws.title for ws in sh.worksheets() if ws.title != 'GENERAL']
    
    return df_gen, {nombre: pd.DataFrame(sh.worksheet(nombre).get_all_records()) for nombre in hojas}

try:
    df_general, dict_participantes = cargar_datos()
    
    # Procesar resultados reales
    resultados_reales = {}
    for _, row in df_general.iterrows():
        casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
        if pd.notna(row['Gol Casa']) and pd.notna(row['Gol Fuera']):
            resultados_reales[(casa, fuera)] = (row['Gol Casa'], row['Gol Fuera'])

    # Calcular puntos
    puntos_totales = []
    for nombre, df_p in dict_participantes.items():
        pts = 0
        for _, row in df_p.iterrows():
            casa, fuera = str(row['Casa']).strip(), str(row['Fuera']).strip()
            if (casa, fuera) in resultados_reales:
                r_gc, r_gf = resultados_reales[(casa, fuera)]
                pts += calcular_puntos(row['Gol Casa'], row['Gol Fuera'], r_gc, r_gf)
        puntos_totales.append({'NOMBRE': nombre, 'PUNTOS': pts})

    # Mostrar tabla
    df_tabla = pd.DataFrame(puntos_totales).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)
    df_tabla.index += 1
    
    st.subheader("📊 Tabla de Posiciones")
    st.table(df_tabla)
    
    st.success("La tabla se actualiza automáticamente desde Google Sheets.")

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.write("Asegúrate de que el nombre del archivo en Google Drive sea exactamente 'POLLA MUNDIAL 2026' y que las hojas tengan los encabezados correctos.")