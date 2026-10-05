from pathlib import Path

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Imports para mapa interactivo con iconos personalizados.
if "from io import BytesIO" not in txt:
    txt = txt.replace("from pathlib import Path\n", "from pathlib import Path\nfrom io import BytesIO\n", 1)
if "import pydeck as pdk" not in txt:
    txt = txt.replace("import streamlit as st\n", "import streamlit as st\nimport pydeck as pdk\n", 1)

# 2) Helpers y constructor del mapa interactivo. Los iconos se rasterizan en memoria
#    a partir de EXACTAMENTE las funciones vectoriales de scripts/mapa_sitrep.py.
anchor = "\ndef construir_mapa_callouts_estatico(\n"
if "def construir_mapa_interactivo_iconos(" not in txt:
    bloque = r'''

def _hex_rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


@st.cache_data(show_spinner=False)
def _icono_vectorial_data_uri(clave, size=64):
    """Convierte el pictograma vectorial del mapa SitRep a PNG embebido para deck.gl."""
    fig = plt.figure(figsize=(.72, .72), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ab = mapa_ref.AnnotationBbox(
        mapa_ref.ICONOS[clave](size),
        (.5, .5),
        xycoords=ax.transAxes,
        frameon=False,
        box_alignment=(.5, .5),
    )
    ax.add_artist(ab)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, transparent=True, pad_inches=0)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def construir_mapa_interactivo_iconos(
    geo,
    contexto,
    datos_filtrados,
    hay_filtros=False,
    amenazas_visibles=None,
):
    """Mapa deck.gl interactivo con los mismos callouts e iconos del SitRep PDF/PNG."""
    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    cols = ["iso3", "pais", "prioridad", "situacion_predominante"]
    cols += [col for col, _ in AMENAZAS.values()]
    cols = [c for c in cols if c in contexto.columns]
    info = contexto[cols].drop_duplicates("iso3")
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")

    seleccionados = set(datos_filtrados["iso3"].dropna().astype(str))
    mapa["prioridad_mapa"] = mapa["prioridad"].fillna("Sin priorización")
    if hay_filtros:
        mask_fuera = mapa["iso3"].notna() & ~mapa["ISO_CC"].isin(seleccionados)
        mapa.loc[mask_fuera, "prioridad_mapa"] = "Fuera del filtro"

    mapa["nombre_mapa"] = mapa["pais"].fillna(mapa["COUNTRY"])
    mapa["situacion_mapa"] = mapa["situacion_predominante"].fillna("Sin hallazgos priorizados en este SitRep")
    mapa["amenazas_mapa"] = mapa.apply(
        lambda r: " · ".join(
            AMENAZAS_CORTAS[nombre]
            for nombre, _ in amenazas_de_fila(r)
        ) or "Sin amenazas / impactos priorizados",
        axis=1,
    )
    mapa["fill_color"] = mapa["prioridad_mapa"].map(
        lambda x: _hex_rgba(COLORES_PRIORIDAD.get(x, COLORES_PRIORIDAD["Sin priorización"]))
    )
    mapa["tooltip_title"] = mapa["nombre_mapa"]
    mapa["tooltip_line1"] = "Prioridad: " + mapa["prioridad_mapa"].astype(str)
    mapa["tooltip_line2"] = "Amenazas / impactos: " + mapa["amenazas_mapa"].astype(str)
    mapa["tooltip_line3"] = mapa["situacion_mapa"].astype(str)
    geojson = json.loads(mapa.to_json())

    amenazas_visibles = amenazas_visibles if amenazas_visibles is not None else list(AMENAZAS.keys())

    rutas = []
    anclas = []
    etiquetas = []
    iconos = []

    for _, fila in datos_filtrados.iterrows():
        iso = str(fila.get("iso3", "")).upper().strip()
        if iso not in mapa_ref.LABELS or iso not in mapa_ref.ROUTES or iso not in mapa_ref.TARGET:
            continue

        activas = []
        for nombre in amenazas_visibles:
            col, _ = AMENAZAS[nombre]
            if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
                activas.append(nombre)
        if not activas:
            continue

        x, y, nombre_pais = mapa_ref.LABELS[iso]
        rutas.append({"path": [list(pt) for pt in mapa_ref.ROUTES[iso]]})
        anclas.append({"position": list(mapa_ref.TARGET[iso])})
        etiquetas.append({"position": [x, y], "pais": nombre_pais})

        # Mismos pictogramas del SitRep, dispuestos en una fila bajo el nombre del país.
        inicio_x = x + .9 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0)
        y_iconos = y + mapa_ref.DESPLAZAMIENTO_ICONOS_Y
        separacion = 2.35
        for i, nombre in enumerate(activas):
            clave = AMENAZA_CLAVE_ESTATICA[nombre]
            iconos.append({
                "position": [inicio_x + i * separacion, y_iconos],
                "icon": {
                    "url": _icono_vectorial_data_uri(clave),
                    "width": 72,
                    "height": 72,
                    "anchorX": 36,
                    "anchorY": 36,
                },
                "size": 28,
                "tooltip_title": nombre_pais,
                "tooltip_line1": nombre,
                "tooltip_line2": "Amenaza / impacto reportado",
                "tooltip_line3": "",
            })

    capas = [
        pdk.Layer(
            "GeoJsonLayer",
            geojson,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            get_fill_color="properties.fill_color",
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=.8,
            highlight_color=[255, 255, 255, 55],
        )
    ]

    if rutas:
        capas.append(
            pdk.Layer(
                "PathLayer",
                rutas,
                get_path="path",
                get_color=[7, 85, 148, 190],
                width_min_pixels=1.2,
                pickable=False,
            )
        )
    if anclas:
        capas.append(
            pdk.Layer(
                "ScatterplotLayer",
                anclas,
                get_position="position",
                get_fill_color=[7, 85, 148, 255],
                get_radius=2.8,
                radius_units="pixels",
                pickable=False,
            )
        )
    if etiquetas:
        capas.append(
            pdk.Layer(
                "TextLayer",
                etiquetas,
                get_position="position",
                get_text="pais",
                get_color=[0, 62, 120, 255],
                get_size=14,
                size_units="pixels",
                get_text_anchor="'start'",
                get_alignment_baseline="'center'",
                font_weight=700,
                pickable=False,
            )
        )
    if iconos:
        capas.append(
            pdk.Layer(
                "IconLayer",
                iconos,
                get_icon="icon",
                get_position="position",
                get_size="size",
                size_units="pixels",
                pickable=True,
            )
        )

    estilo = {
        "version": 8,
        "sources": {},
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {"background-color": AZUL_MAR},
            }
        ],
    }

    vista = pdk.ViewState(
        longitude=-76.0,
        latitude=-10.0,
        zoom=2.18,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": (
            "<div style='font-family:Arial,sans-serif;max-width:330px'>"
            "<b style='color:#004B87'>{tooltip_title}</b><br>"
            "{tooltip_line1}<br>"
            "{tooltip_line2}<br>"
            "<span style='color:#60788A'>{tooltip_line3}</span>"
            "</div>"
        ),
        "style": {
            "backgroundColor": "white",
            "color": "#17324D",
            "fontSize": "12px",
            "border": "1px solid #D9E6EE",
            "borderRadius": "8px",
        },
    }

    return pdk.Deck(
        layers=capas,
        initial_view_state=vista,
        map_style=estilo,
        tooltip=tooltip,
    )
'''
    if anchor not in txt:
        raise RuntimeError("No se encontró el constructor estático para insertar la versión interactiva")
    txt = txt.replace(anchor, bloque + anchor, 1)

# 3) Prioridad + amenazas vuelve a ser interactivo. Prioridad sola conserva Plotly.
old = '''        if modo_mapa == "Prioridad + amenazas":
            fig_mapa = construir_mapa_callouts_estatico(
                geo,
                actual,
                filtrado,
                hay_filtros,
                amenazas_visibles=amenazas_mapa,
            )
            st.pyplot(fig_mapa, use_container_width=True)
            plt.close(fig_mapa)
        else:
'''
new = '''        if modo_mapa == "Prioridad + amenazas":
            deck_mapa = construir_mapa_interactivo_iconos(
                geo,
                actual,
                filtrado,
                hay_filtros,
                amenazas_visibles=amenazas_mapa,
            )
            st.pydeck_chart(deck_mapa, use_container_width=True, height=690)
        else:
'''
if old not in txt:
    raise RuntimeError("No se encontró el bloque estático actual del mapa")
txt = txt.replace(old, new, 1)

# 4) Nota del mapa: dejar claro que la vista sigue siendo interactiva.
nota_old = (
    "El color del país representa la prioridad. En la vista de amenazas se usan los mismos pictogramas vectoriales y callouts del mapa SitRep en PDF/PNG. "
    "Los controles solo cambian la visualización del mapa."
)
nota_new = (
    "El color del país representa la prioridad. La vista de amenazas es interactiva y usa los mismos pictogramas vectoriales y callouts del mapa SitRep en PDF/PNG; "
    "pasa el cursor sobre países o iconos para ver el detalle."
)
if nota_old in txt:
    txt = txt.replace(nota_old, nota_new, 1)

p.write_text(txt, encoding="utf-8")
print("Mapa de amenazas restaurado como interactivo con pictogramas vectoriales SitRep")
