import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from datetime import datetime
import pytz
import plotly.express as px
import re

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

# --- BRACKET MUNDIALISTA ---

def _num_partido(orden):
    """Extrae el número entero de un texto tipo 'Partido 7' -> 7"""
    m = re.search(r'\d+', str(orden))
    return int(m.group()) if m else 0

def _es_tercer_puesto(fase):
    fase_norm = str(fase or '').strip().lower()
    return ('3er' in fase_norm) or ('tercer' in fase_norm)

def _preparar_rondas_sheet(df_general):
    """Agrupa las filas del sheet por Fase y las ordena por número de Orden.
    Devuelve un dict {tamaño_ronda: [partidos...]}. El partido de 3er puesto
    se excluye acá porque tiene 1 solo partido, igual que la Final, y chocaría
    con ella al agrupar por tamaño."""
    df = df_general.copy()
    df = df[~df['Fase'].apply(_es_tercer_puesto)]
    df['NumPartido'] = df['Orden'].apply(_num_partido)
    rondas = {}
    for _, grupo in df.groupby('Fase'):
        grupo_ordenado = grupo.sort_values('NumPartido')
        rondas[len(grupo_ordenado)] = grupo_ordenado.to_dict('records')
    return rondas

def _generar_ronda_siguiente(ronda_actual, tam_siguiente):
    """Si la siguiente ronda todavía no existe en el sheet, la construye
    a partir de los Clasifica de la ronda anterior (partidos 2k-1 y 2k -> partido k)."""
    siguiente = []
    for k in range(tam_siguiente):
        m1 = ronda_actual[2 * k] if 2 * k < len(ronda_actual) else {}
        m2 = ronda_actual[2 * k + 1] if 2 * k + 1 < len(ronda_actual) else {}
        eq1 = str(m1.get('Clasifica', '') or '').strip()
        eq2 = str(m2.get('Clasifica', '') or '').strip()
        siguiente.append({
            'Casa': eq1, 'Fuera': eq2,
            'Gol Casa': None, 'Gol Fuera': None,
            'Clasifica': '', 'Fecha': None
        })
    return siguiente

def _armar_bracket_completo(df_general):
    """Combina lo que ya existe en el sheet con lo que hay que inferir,
    devolviendo un dict {tamaño_ronda: [partidos]} desde 16avos hasta la Final."""
    rondas_sheet = _preparar_rondas_sheet(df_general)
    if not rondas_sheet:
        return {}
    tamanos = sorted(rondas_sheet.keys(), reverse=True)
    tam_actual = tamanos[0]
    bracket = {tam_actual: rondas_sheet[tam_actual]}
    tam = tam_actual
    while tam > 1:
        tam_sig = tam // 2
        if tam_sig in rondas_sheet:
            bracket[tam_sig] = rondas_sheet[tam_sig]
        else:
            bracket[tam_sig] = _generar_ronda_siguiente(bracket[tam], tam_sig)
        tam = tam_sig
    return bracket

def _obtener_partido_tercer_puesto(df_general, bracket):
    """Si ya existe en el sheet (Fase con '3er' o 'tercer'), usa esos datos.
    Si todavía no está, lo arma con los perdedores de las 2 semifinales."""
    df = df_general.copy()
    filas = df[df['Fase'].apply(_es_tercer_puesto)]
    if not filas.empty:
        filas = filas.copy()
        filas['NumPartido'] = filas['Orden'].apply(_num_partido)
        return filas.sort_values('NumPartido').iloc[0].to_dict()

    semis = bracket.get(2, [])
    if len(semis) < 2:
        return {'Casa': '', 'Fuera': '', 'Gol Casa': None, 'Gol Fuera': None, 'Clasifica': ''}

    def _perdedor(m):
        casa = str(m.get('Casa', '') or '').strip()
        fuera = str(m.get('Fuera', '') or '').strip()
        clasifica = str(m.get('Clasifica', '') or '').strip().upper()
        if not clasifica or not casa or not fuera:
            return ''
        return fuera if clasifica == casa.upper() else casa

    return {
        'Casa': _perdedor(semis[0]), 'Fuera': _perdedor(semis[1]),
        'Gol Casa': None, 'Gol Fuera': None, 'Clasifica': ''
    }

def _fila_equipo_html(nombre, gol, gano):
    nombre = (nombre or '').strip()
    if not nombre:
        return '<div class="equipo vacio"><span class="nombre">Por definir</span></div>'
    bandera = obtener_bandera(nombre)
    if gol is None or (isinstance(gol, float) and pd.isna(gol)) or str(gol).strip() == '':
        gol_html = ''
    else:
        try:
            gol_html = f'<span class="gol">{int(float(gol))}</span>'
        except (ValueError, TypeError):
            gol_html = ''
    clase = 'equipo ganador' if gano else 'equipo'
    return f'<div class="{clase}"><span class="bandera">{bandera}</span><span class="nombre">{nombre}</span>{gol_html}</div>'

def _match_html(match):
    casa = str(match.get('Casa', '') or '').strip()
    fuera = str(match.get('Fuera', '') or '').strip()
    gc = match.get('Gol Casa')
    gf = match.get('Gol Fuera')
    clasifica = str(match.get('Clasifica', '') or '').strip().upper()
    casa_gana = bool(casa) and clasifica == casa.upper()
    fuera_gana = bool(fuera) and clasifica == fuera.upper()
    return (
        '<div class="match">'
        + _fila_equipo_html(casa, gc, casa_gana)
        + _fila_equipo_html(fuera, gf, fuera_gana)
        + '</div>'
    )

_NOMBRES_RONDA_FALLBACK = {16: '16avos', 8: '8vos', 4: '4tos', 2: 'Semifinal', 1: 'Final'}

def _nombre_ronda(tam, matches):
    if matches:
        fase = str(matches[0].get('Fase', '') or '').strip()
        if fase:
            return fase
    return _NOMBRES_RONDA_FALLBACK.get(tam, f'Ronda de {tam}')

def _ronda_html(matches, es_ultima_del_lado, etiqueta=None):
    clase_extra = ' ultima' if es_ultima_del_lado else ''
    etiqueta_html = f'<div class="round-label">{etiqueta}</div>' if etiqueta else ''
    filas = ''.join(_match_html(m) for m in matches)
    return f'<div class="round{clase_extra}">{etiqueta_html}{filas}</div>'

def construir_bracket_html(df_general):
    bracket = _armar_bracket_completo(df_general)
    if not bracket:
        return "<p style='color:white'>No hay datos de bracket disponibles todavía.</p>"

    tamanos = sorted(bracket.keys(), reverse=True)  # ej: [16, 8, 4, 2, 1]
    tam_final = tamanos[-1]
    rondas_previas = tamanos[:-1]  # todo menos la final

    columnas_izq, columnas_der = [], []
    n_rondas = len(rondas_previas)
    for idx, tam in enumerate(rondas_previas):
        matches = bracket[tam]
        etiqueta = _nombre_ronda(tam, matches)
        mitad = len(matches) // 2
        izq = matches[:mitad] if len(matches) > 1 else matches
        der = matches[mitad:] if len(matches) > 1 else []
        es_ultima = (idx == n_rondas - 1)
        columnas_izq.append(_ronda_html(izq, es_ultima, etiqueta))
        columnas_der.append(_ronda_html(der, es_ultima, etiqueta))

    final_match = bracket[tam_final][0] if bracket[tam_final] else {}
    tercer_match = _obtener_partido_tercer_puesto(df_general, bracket)
    html_final = f'''
    <div class="final-col">
        <div class="final-label">FINAL</div>
        {_match_html(final_match)}
        <div class="tercer-label">🥉 3er puesto</div>
        {_match_html(tercer_match)}
    </div>
    '''

    izq_html = ''.join(columnas_izq)
    der_html = ''.join(reversed(columnas_der))

    css = """
    <style>
        :root {
            --conn-w: clamp(4px, 1.1vw, 16px);
            --match-gap-v: clamp(1px, 0.5vw, 8px);
            --match-gap-h: clamp(0px, 0.2vw, 5px);
            --round-gap: clamp(2px, 1vw, 22px);
            --side-gap: clamp(1px, 0.5vw, 8px);
        }
        .bracket-fondo {
            padding: clamp(4px, 1.5vw, 20px) clamp(2px, 1vw, 15px);
            font-family: 'Segoe UI', Arial, sans-serif;
            width: 100%;
            box-sizing: border-box;
            overflow-x: hidden;
        }
        .bracket-wrapper {
            display: flex;
            justify-content: center;
            align-items: stretch;
            gap: var(--side-gap);
            width: 100%;
        }
        .bracket-lado {
            display: flex;
            gap: var(--round-gap);
            flex: 1 1 0;
            min-width: 0;
        }
        .bracket-lado.derecha { flex-direction: row; }
        .round {
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            flex: 1 1 0;
            min-width: 0;
        }
        .match {
            background: #ffffff;
            border-radius: clamp(3px, 0.6vw, 8px);
            margin: var(--match-gap-v) var(--match-gap-h);
            box-shadow: 0 1px 3px rgba(0,0,0,0.25);
            position: relative;
            min-width: 0;
        }
        .bracket-lado.izquierda .round:not(.ultima) .match::after {
            content: '';
            position: absolute;
            right: calc(-1 * var(--conn-w));
            top: 50%;
            width: var(--conn-w);
            height: 2px;
            background: #4a5a7a;
        }
        .bracket-lado.derecha .round:not(.ultima) .match::after {
            content: '';
            position: absolute;
            left: calc(-1 * var(--conn-w));
            top: 50%;
            width: var(--conn-w);
            height: 2px;
            background: #4a5a7a;
        }
        .round:not(.ultima) .match:nth-child(odd)::before {
            content: '';
            position: absolute;
            top: 50%;
            height: calc(50% + var(--match-gap-v) + 2px);
            width: 2px;
            background: #4a5a7a;
        }
        .round:not(.ultima) .match:nth-child(even)::before {
            content: '';
            position: absolute;
            bottom: 50%;
            height: calc(50% + var(--match-gap-v) + 2px);
            width: 2px;
            background: #4a5a7a;
        }
        .bracket-lado.izquierda .round:not(.ultima) .match::before { right: calc(-1 * var(--conn-w)); }
        .bracket-lado.derecha .round:not(.ultima) .match::before { left: calc(-1 * var(--conn-w)); }
        .equipo {
            display: flex;
            align-items: center;
            padding: clamp(1px, 0.4vw, 6px) clamp(2px, 0.6vw, 10px);
            font-size: clamp(7px, 1vw, 13px);
            font-weight: 600;
            color: #0b1f4d;
            border-bottom: 1px solid #e0e0e0;
            min-width: 0;
        }
        .equipo:last-child { border-bottom: none; }
        .equipo.vacio { color: #9aa0ab; font-style: italic; font-weight: 400; }
        .equipo.ganador { background: #fff3c4; }
        .bandera { margin-right: clamp(1px, 0.3vw, 6px); font-size: clamp(8px, 1.1vw, 15px); flex-shrink: 0; }
        .nombre {
            flex: 1;
            min-width: 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .gol { margin-left: clamp(1px, 0.3vw, 6px); font-weight: 800; color: #142d6e; flex-shrink: 0; }
        .final-col {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 0 clamp(3px, 1vw, 20px);
            flex-shrink: 0;
        }
        .final-label {
            background: #ffd200;
            color: #0b1f4d;
            font-weight: 900;
            font-size: clamp(8px, 1.2vw, 14px);
            padding: clamp(2px, 0.5vw, 6px) clamp(4px, 1vw, 18px);
            border-radius: 20px;
            margin-bottom: clamp(3px, 0.8vw, 12px);
            letter-spacing: 1px;
            white-space: nowrap;
        }
        .tercer-label {
            color: #cd7f32;
            font-weight: 800;
            font-size: clamp(7px, 1vw, 11px);
            margin: clamp(10px, 2vw, 22px) 0 clamp(2px, 0.6vw, 6px) 0;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .final-col .match:last-of-type {
            transform: scale(0.85);
        }
        .round-label {
            display: none;
        }
    </style>
    """

    html = f"""
    {css}
    <div class="bracket-fondo">
        <div class="bracket-wrapper">
            <div class="bracket-lado izquierda">{izq_html}</div>
            {html_final}
            <div class="bracket-lado derecha">{der_html}</div>
        </div>
    </div>
    <script>
        function _ajustarAlturaBracket() {{
            const alto = document.body.scrollHeight;
            window.parent.postMessage({{type: "streamlit:setFrameHeight", height: alto}}, "*");
        }}
        window.addEventListener('load', _ajustarAlturaBracket);
        window.addEventListener('resize', _ajustarAlturaBracket);
        new ResizeObserver(_ajustarAlturaBracket).observe(document.body);
        setTimeout(_ajustarAlturaBracket, 300);
    </script>
    """
    return html

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

st.info("💡 **Logro 'La Posha mas grande'**: Es para el enfermo con la mayor cantidad de resultados exactos acertados hasta el momento.")

# 1. TABLA PRINCIPAL
st.subheader("📊 Tabla de Posiciones General")
st.table(obtener_tabla(df_general, dict_participantes))

st.markdown("---")

# 2. HISTÓRICO
st.subheader("📅 Historial y Jornadas")
fecha_actual = datetime.now(PERU_TZ).date()
fecha_sel = st.date_input("Seleccionar fecha:", value=fecha_actual, min_value=datetime(2026, 6, 28).date(), max_value=datetime(2026, 7, 19).date())

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
    
    # --- GRÁFICO DE PUNTOS DIARIOS (ESTILO MUNDIALISTA) ---
if puntos_dia_lista:
    df_dia = pd.DataFrame(puntos_dia_lista).groupby('Participante')['Puntos'].sum().reset_index()
    st.subheader("📈 Rendimiento del día")
    
    # Paleta de colores extraída del logo (Naranja, Verde, Azul, Dorado)
    color_scale = ['#FF4500', '#32CD32', '#1E90FF', '#FFD700']
    
    fig = px.bar(
        df_dia, 
        x='Participante', 
        y='Puntos', 
        color='Participante', # Color por participante para mejor contraste
        text='Puntos', 
        color_discrete_sequence=color_scale
    )
    
    # Ajuste de estilo para modo oscuro/claro
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="#FFFFFF" if st.session_state.get('theme', 'dark') == 'dark' else "#000000",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
        
else:
    st.info("No hay partidos programados para esta fecha.")

st.markdown("---")

# 4. BRACKET MUNDIALISTA
st.subheader("🏆 Bracket Mundial")
html_bracket = construir_bracket_html(df_general)
components.html(html_bracket, height=950, scrolling=False)