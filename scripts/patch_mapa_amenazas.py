from pathlib import Path
import re

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Posiciones cartográficas ajustadas para los iconos.
if "POSICIONES_AMENAZAS =" not in txt:
    posiciones = '''

# Posiciones de referencia para evitar solapamientos en países pequeños.
# Para cualquier país no incluido aquí se usa un punto representativo
# calculado a partir de su geometría.
POSICIONES_AMENAZAS = {
    "MEX": (-102.0, 24.0),
    "GTM": (-91.4, 16.4),
    "HND": (-86.7, 15.2),
    "SLV": (-89.1, 13.6),
    "CRI": (-84.3, 9.7),
    "PAN": (-80.6, 8.7),
    "JAM": (-77.2, 18.3),
    "PRI": (-66.4, 18.2),
    "TTO": (-61.2, 10.7),
    "COL": (-74.0, 4.7),
    "ECU": (-78.3, -1.3),
    "PER": (-75.2, -9.2),
    "BOL": (-64.8, -16.6),
    "BRA": (-52.0, -10.0),
    "CHL": (-71.0, -29.0),
    "ARG": (-64.0, -34.0),
    "URY": (-56.0, -32.8),
    "PRY": (-58.4, -23.4),
    "USA": (-98.0, 31.0),
}
'''
    if "\nCIFRAS = {" not in txt:
        raise RuntimeError("No se encontró CIFRAS para insertar posiciones")
    txt = txt.replace("\nCIFRAS = {", posiciones + "\nCIFRAS = {", 1)

# 2) Estilo de la nota de controles del mapa.
if ".map-note" not in txt:
    css = '''        .map-note {{
            color:#6D8191;
            font-size:.76rem;
            line-height:1.35;
            margin-top:-.2rem;
            margin-bottom:.7rem;
        }}

'''
    marker = '        .section-head {{margin:1.25rem 0 .55rem 0;}}'
    if marker not in txt:
        raise RuntimeError("No se encontró section-head para insertar map-note")
    txt = txt.replace(marker, css + marker, 1)

# 3) Helpers para amenazas y posiciones.
if "def amenazas_de_fila" not in txt:
    old = "def construir_mapa(geo, contexto, datos_filtrados, hay_filtros=False):"
    helper = '''def amenazas_de_fila(fila, seleccion=None):
    if seleccion is None:
        seleccion = list(AMENAZAS.keys())
    salida = []
    for nombre in seleccion:
        col, icono = AMENAZAS[nombre]
        if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
            salida.append((nombre, icono))
    return salida


def posiciones_pais(geo):
    posiciones = dict(POSICIONES_AMENAZAS)
    faltantes = set(geo["ISO_CC"].dropna().astype(str)) - set(posiciones)
    if faltantes:
        dis = geo[geo["ISO_CC"].isin(faltantes)][["ISO_CC", "geometry"]].dissolve(by="ISO_CC")
        for iso, geom in dis.geometry.items():
            if geom is not None and not geom.is_empty:
                pt = geom.representative_point()
                posiciones[str(iso)] = (float(pt.x), float(pt.y))
    return posiciones


def construir_mapa(
    geo,
    contexto,
    datos_filtrados,
    hay_filtros=False,
    mostrar_amenazas=False,
    amenazas_visibles=None,
):'''
    if old not in txt:
        raise RuntimeError("No se encontró construir_mapa")
    txt = txt.replace(old, helper, 1)

# 4) Incluir columnas de amenazas en la unión del mapa.
old_cols = '    cols = ["iso3", "pais", "prioridad", "situacion_predominante", "impacto_salud_documentado"]\n    cols = [c for c in cols if c in contexto.columns]'
new_cols = '    cols = ["iso3", "pais", "prioridad", "situacion_predominante", "impacto_salud_documentado"]\n    cols += [col for col, _ in AMENAZAS.values()]\n    cols = [c for c in cols if c in contexto.columns]'
if old_cols in txt:
    txt = txt.replace(old_cols, new_cols, 1)

# 5) Resumen de amenazas para el hover.
if 'mapa["amenazas_mapa"]' not in txt:
    old_geojson = '    mapa["nombre_mapa"] = mapa["pais"].fillna(mapa["COUNTRY"])\n    mapa["situacion_mapa"] = mapa["situacion_predominante"].fillna("Sin hallazgos priorizados en este SitRep")\n    geojson = json.loads(mapa.to_json())'
    new_geojson = '''    mapa["nombre_mapa"] = mapa["pais"].fillna(mapa["COUNTRY"])
    mapa["situacion_mapa"] = mapa["situacion_predominante"].fillna("Sin hallazgos priorizados en este SitRep")
    mapa["amenazas_mapa"] = mapa.apply(
        lambda r: " · ".join(
            f"{icono} {AMENAZAS_CORTAS[nombre]}"
            for nombre, icono in amenazas_de_fila(r)
        ) or "Sin amenazas / impactos priorizados",
        axis=1,
    )
    geojson = json.loads(mapa.to_json())'''
    if old_geojson not in txt:
        raise RuntimeError("No se encontró bloque previo a geojson")
    txt = txt.replace(old_geojson, new_geojson, 1)

# 6) Amenazas en el hover del coroplético.
if '"amenazas_mapa": True' not in txt:
    old_hover = '''            "prioridad_mapa": True,
            "situacion_mapa": True,
        },
        labels={"prioridad_mapa": "Prioridad", "situacion_mapa": "Situación"},'''
    new_hover = '''            "prioridad_mapa": True,
            "amenazas_mapa": True,
            "situacion_mapa": True,
        },
        labels={
            "prioridad_mapa": "Prioridad",
            "amenazas_mapa": "Amenazas / impactos",
            "situacion_mapa": "Situación",
        },'''
    if old_hover not in txt:
        raise RuntimeError("No se encontró bloque hover_data")
    txt = txt.replace(old_hover, new_hover, 1)

# 7) Burbujas de iconos como Scattergeo.
if "capas_iconos =" not in txt:
    iconos = '''    if mostrar_amenazas:
        if amenazas_visibles is None:
            amenazas_visibles = list(AMENAZAS.keys())
        posiciones = posiciones_pais(geo)
        capas_iconos = {nombre: {"lon": [], "lat": [], "hover": []} for nombre in amenazas_visibles}

        for _, fila in datos_filtrados.iterrows():
            iso = str(fila.get("iso3", ""))
            if iso not in posiciones:
                continue
            activas = amenazas_de_fila(fila, amenazas_visibles)
            if not activas:
                continue

            lon0, lat0 = posiciones[iso]
            paso = 1.55
            for i, (nombre, icono) in enumerate(activas):
                offset = (i - (len(activas) - 1) / 2) * paso
                capas_iconos[nombre]["lon"].append(lon0 + offset)
                capas_iconos[nombre]["lat"].append(lat0)
                capas_iconos[nombre]["hover"].append(
                    f"<b>{html.escape(texto(fila.get('pais'), iso))}</b><br>"
                    f"{icono} {html.escape(nombre)}"
                )

        for nombre in amenazas_visibles:
            datos_capa = capas_iconos[nombre]
            if not datos_capa["lon"]:
                continue
            _, icono = AMENAZAS[nombre]
            fig.add_trace(
                go.Scattergeo(
                    lon=datos_capa["lon"],
                    lat=datos_capa["lat"],
                    mode="markers+text",
                    marker=dict(
                        size=28,
                        color="rgba(255,255,255,.94)",
                        line=dict(color="rgba(0,75,135,.35)", width=1),
                    ),
                    text=[icono] * len(datos_capa["lon"]),
                    textposition="middle center",
                    textfont=dict(size=14, color=TEXTO),
                    hovertext=datos_capa["hover"],
                    hovertemplate="%{hovertext}<extra></extra>",
                    hoverlabel=dict(bgcolor="white", font_size=12, font_color=TEXTO),
                    showlegend=False,
                )
            )

'''
    marker = '    fig.update_geos(\n'
    if marker not in txt:
        raise RuntimeError("No se encontró fig.update_geos")
    txt = txt.replace(marker, iconos + marker, 1)

# Evitar que el estilo del borde del coroplético sobrescriba los iconos.
txt = txt.replace(
    '    fig.update_traces(marker_line_color="white", marker_line_width=0.7)',
    '    fig.update_traces(marker_line_color="white", marker_line_width=0.7, selector=dict(type="choropleth"))',
    1,
)

# 8) Controles interactivos encima del mapa.
if 'key="modo_mapa"' not in txt:
    patron = re.compile(
        r'# Mapa y resumen\n'
        r'section_header\("Panorama regional", "Distribución de prioridades y amenazas reportadas"\)\n'
        r'col_mapa, col_resumen = st\.columns\(\[4\.15, 1\.35\], gap="medium"\)\n'
        r'with col_mapa:\n'
        r'    with st\.container\(border=True\):\n'
        r'        fig_mapa = construir_mapa\(geo, actual, filtrado, hay_filtros\)\n'
        r'        st\.plotly_chart\(fig_mapa, use_container_width=True, config=CHART_CONFIG\)\n'
    )
    nuevo = '''# Mapa y resumen
section_header("Panorama regional", "Distribución de prioridades y amenazas reportadas")

with st.container(border=True):
    vm1, vm2 = st.columns([1.25, 2.75], gap="medium")
    with vm1:
        modo_mapa = st.radio(
            "Visualizar",
            ["Prioridad", "Prioridad + amenazas"],
            index=1,
            horizontal=True,
            key="modo_mapa",
        )
    with vm2:
        if modo_mapa == "Prioridad + amenazas":
            amenazas_mapa = st.multiselect(
                "Iconos visibles",
                list(AMENAZAS.keys()),
                default=list(AMENAZAS.keys()),
                format_func=lambda x: f"{AMENAZAS[x][1]} {AMENAZAS_CORTAS[x]}",
                key="amenazas_mapa",
            )
        else:
            amenazas_mapa = []
    st.markdown(
        '<div class="map-note">El color del país representa la prioridad. Los iconos muestran amenazas / impactos reportados. Estos controles solo cambian la visualización del mapa.</div>',
        unsafe_allow_html=True,
    )

col_mapa, col_resumen = st.columns([4.15, 1.35], gap="medium")
with col_mapa:
    with st.container(border=True):
        fig_mapa = construir_mapa(
            geo,
            actual,
            filtrado,
            hay_filtros,
            mostrar_amenazas=(modo_mapa == "Prioridad + amenazas"),
            amenazas_visibles=amenazas_mapa,
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config=CHART_CONFIG)
'''
    txt, n = patron.subn(nuevo, txt, count=1)
    if n != 1:
        raise RuntimeError("No se pudo reemplazar el bloque Panorama regional")

p.write_text(txt, encoding="utf-8")
print("Mapa interactivo con amenazas incorporado")
