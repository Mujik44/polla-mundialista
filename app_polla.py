import streamlit as st
import pandas as pd

st.set_page_config(page_title="Polla Mundialista 2026", layout="wide")

st.title("🏆 Polla Mundialista 2026 - Dashboard")

# Función de cálculo de puntos
def calcular_puntos(pred_gc, pred_gf, real_gc, real_gf):
    if (pred_gc == real_gc) and (pred_gf == real_gf):
        return 2
    real_res = (real_gc > real_gf) - (real_gc < real_gf)
    pred_res = (pred_gc > pred_gf) - (pred_gc < pred_gf)
    if real_res == pred_res:
        return 1
    return 0

uploaded_file = st.file_uploader("Sube tu archivo Excel de la Polla", type=["xlsx"])

if uploaded_file:
    # Leer archivo
    xls = pd.ExcelFile(uploaded_file)
    
    # 1. Obtener resultados reales desde la hoja 'GENERAL'
    df_gen = pd.read_excel(xls, sheet_name='GENERAL', header=None)
    resultados_reales = {}
    for i in range(len(df_gen)):
        if pd.isna(df_gen.iloc[i, 4]) or str(df_gen.iloc[i, 4]).strip() in ['Casa', 'nan', 'RESULTADOS FINALES']: continue
        if pd.isna(df_gen.iloc[i, 5]) or pd.isna(df_gen.iloc[i, 6]): continue
        casa, fuera = str(df_gen.iloc[i, 4]).strip(), str(df_gen.iloc[i, 7]).strip()
        resultados_reales[(casa, fuera)] = (int(df_gen.iloc[i, 5]), int(df_gen.iloc[i, 6]))

    # 2. Calcular puntos para los participantes
    participantes = [s for s in xls.sheet_names if s != 'GENERAL']
    puntos_totales = []

    for p in participantes:
        df_p = pd.read_excel(xls, sheet_name=p, header=None)
        pts = 0
        for i in range(len(df_p)):
            if pd.isna(df_p.iloc[i, 4]): continue
            casa, fuera = str(df_p.iloc[i, 4]).strip(), str(df_p.iloc[i, 7]).strip()
            if (casa, fuera) in resultados_reales:
                r_gc, r_gf = resultados_reales[(casa, fuera)]
                p_gc, p_gf = df_p.iloc[i, 5], df_p.iloc[i, 6]
                if pd.notna(p_gc) and pd.notna(p_gf):
                    pts += calcular_puntos(int(p_gc), int(p_gf), r_gc, r_gf)
        puntos_totales.append({'NOMBRE': p, 'PUNTOS': pts})

    # 3. Mostrar Tabla
    df_tabla = pd.DataFrame(puntos_totales).sort_values(by='PUNTOS', ascending=False).reset_index(drop=True)
    df_tabla.index += 1
    
    st.subheader("📊 Tabla de Posiciones Actualizada")
    st.table(df_tabla)
    
    st.success("La tabla se ha calculado automáticamente basándose en las reglas (2 pts Exacto, 1 pt Resultado).")
