"""Entrada Streamlit para el dashboard de El Niño OPS/OMS.

El dashboard visual original se conserva en ``app_legacy.py``. Esta entrada
intercepta únicamente el render estático de "Prioridad + amenazas" y lo
reemplaza por un mapa deck.gl interactivo con los mismos pictogramas del mapa
SitRep PDF/PNG, callouts y tooltips al pasar el cursor.
"""

from io import BytesIO
import base64
import importlib
import inspect
import json
import sys

import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
import streamlit as st

from scripts import mapa_sitrep as mapa_ref


AZUL_MAR = "#D9EEF7"
AZUL_OPS = "#004B87"
COLORES_PRIORIDAD = {
    "Alta": "#D71920",
    "Media": "#FF8618",
    "Baja": "#F6C344",
    "Sin priorización": "#BDBDBD",
    "Fuera del filtro": "#E7EDF1",
}
AMENAZAS = {
    "Sequía / agua": ("icono_agua", "agua"),
    "Inundaciones / lluvias": ("icono_inundaciones", "inundaciones"),
    "Incendios / quemadas": ("icono_incendios", "incendios"),
    "Inseguridad alimentaria": ("icono_alimentos", "alimentos"),
    "Dengue / otras arbovirosis": ("icono_arbovirosis", "arbovirosis"),
    "Calidad del aire / riesgo respiratorio": ("icono_respiratorio", "respiratorio"),
    "Afectación de servicios de salud": ("icono_servicios", "servicios"),
}


def _hex_rgba(valor, alpha=255):
    h = valor.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def _icono_data_uri(clave, size=64):
    """Rasteriza el pictograma SitRep sin recortar su contorno circular."""
    draw_size = 64
    cache_key = (clave, draw_size)
    cache = getattr(_icono_data_uri, "_cache", {})
    if cache_key in cache:
        return cache[cache_key]

    dpi = 100
    canvas_px = 112
    fig = plt.figure(figsize=(canvas_px / dpi, canvas_px / dpi), dpi=dpi)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    dibujo = mapa_ref.ICONOS[clave](draw_size)
    ax.add_artist(
        mapa_ref.AnnotationBbox(
            dibujo,
            (0.5, 0.5),
            xycoords=ax.transAxes,
            frameon=False,
            box_alignment=(0.5, 0.5),
            annotation_clip=False,
        )
    )

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        transparent=True,
        facecolor="none",
        edgecolor="none",
        pad_inches=0,
    )
    plt.close(fig)

    uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    cache[cache_key] = uri
    _icono_data_uri._cache = cache
    return uri


def _amenazas_activas(fila, seleccion):
    salida = []
    for nombre in seleccion:
        col, clave = AMENAZAS[nombre]
        if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
            salida.append((nombre, clave))
    return salida


def _construir_deck(frame_globals):
    geo = frame_globals["geo"].copy()
    actual = frame_globals["actual"].copy()
    filtrado = frame_globals["filtrado"].copy()
    hay_filtros = bool(frame_globals.get("hay_filtros", False))
    seleccion = frame_globals.get("amenazas_mapa") or list(AMENAZAS.keys())

    cols = ["iso3", "pais", "prioridad", "situacion_predominante"]
    cols += [v[0] for v in AMENAZAS.values()]
    cols = [c for c in cols if c in actual.columns]
    info = actual[cols].drop_duplicates("iso3")

    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")
    seleccionados = set(filtrado["iso3"].dropna().astype(str))
    mapa["prioridad_mapa"] = mapa["prioridad"].fillna("Sin priorización")
    if hay_filtros:
        mask = mapa["iso3"].notna() & ~mapa["ISO_CC"].isin(seleccionados)
        mapa.loc[mask, "prioridad_mapa"] = "Fuera del filtro"

    def amenazas_texto(r):
        activas = _amenazas_activas(r, list(AMENAZAS.keys()))
        return ", ".join(n for n, _ in activas) if activas else "Sin amenazas / impactos priorizados"

    mapa["fill_color"] = mapa["prioridad_mapa"].map(
        lambda p: _hex_rgba(COLORES_PRIORIDAD.get(p, COLORES_PRIORIDAD["Sin priorización"]))
    )
    mapa["tooltip_title"] = mapa["pais"].fillna(mapa["COUNTRY"])
    mapa["tooltip_line1"] = "Prioridad: " + mapa["prioridad_mapa"].astype(str)
    mapa["tooltip_line2"] = mapa.apply(lambda r: "Amenazas / impactos: " + amenazas_texto(r), axis=1)
    mapa["tooltip_line3"] = mapa["situacion_predominante"].fillna(
        "Sin hallazgos priorizados en este SitRep"
    )
    geojson = json.loads(mapa.to_json())
    # Duplicar campos de tooltip al nivel superior del Feature para que
    # el mismo template funcione en GeoJsonLayer, TextLayer e IconLayer.
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        for key in ("tooltip_title", "tooltip_line1", "tooltip_line2", "tooltip_line3"):
            feature[key] = props.get(key, "")

    rutas = []
    anclas = []
    etiquetas = []
    iconos = []

    for _, fila in filtrado.iterrows():
        iso = str(fila.get("iso3", "")).upper().strip()
        if iso not in mapa_ref.LABELS or iso not in mapa_ref.ROUTES or iso not in mapa_ref.TARGET:
            continue

        activas = _amenazas_activas(fila, seleccion)
        if not activas:
            continue

        x, y, nombre_pais = mapa_ref.LABELS[iso]
        rutas.append({"path": [list(pt) for pt in mapa_ref.ROUTES[iso]]})
        anclas.append({"position": list(mapa_ref.TARGET[iso])})
        etiquetas.append({
            "position": [x, y],
            "pais": nombre_pais,
            "tooltip_title": nombre_pais,
            "tooltip_line1": "Amenazas / impactos",
            "tooltip_line2": "Pasa el cursor sobre los pictogramas para ver el detalle.",
            "tooltip_line3": "",
        })

        inicio_x = x + 1.0 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0)
        y_iconos = y + mapa_ref.DESPLAZAMIENTO_ICONOS_Y
        separacion = 2.45
        for i, (nombre, clave) in enumerate(activas):
            iconos.append({
                "position": [inicio_x + i * separacion, y_iconos],
                "icon": {
                    "url": _icono_data_uri(clave),
                    "width": 112,
                    "height": 112,
                    "anchorX": 56,
                    "anchorY": 56,
                },
                "size": 16,
                "tooltip_title": nombre_pais,
                "tooltip_line1": nombre,
                "tooltip_line2": "Amenaza / impacto reportado",
                "tooltip_line3": "",
            })

    # Fondo azul propio. Así no dependemos de Mapbox, Carto ni de tokens externos.
    fondo_oceano = [{
        "polygon": [
            [-180.0, -85.0],
            [180.0, -85.0],
            [180.0, 85.0],
            [-180.0, 85.0],
        ]
    }]

    capas = [
        pdk.Layer(
            "PolygonLayer",
            fondo_oceano,
            get_polygon="polygon",
            get_fill_color=[217, 238, 247, 255],
            stroked=False,
            pickable=False,
        ),
        pdk.Layer(
            "GeoJsonLayer",
            geojson,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            get_fill_color="properties.fill_color",
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=0.8,
            highlight_color=[255, 255, 255, 55],
        ),
    ]

    if rutas:
        capas.append(
            pdk.Layer(
                "PathLayer",
                rutas,
                get_path="path",
                get_color=[7, 85, 148, 205],
                width_min_pixels=1.0,
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
                get_radius=2.2,
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
                get_size=9,
                size_units="pixels",
                size_scale=1,
                size_min_pixels=8,
                size_max_pixels=10,
                get_text_anchor="'start'",
                get_alignment_baseline="'center'",
                font_weight=700,
                pickable=True,
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
                size_scale=1,
                size_min_pixels=12,
                size_max_pixels=18,
                pickable=True,
            )
        )

    vista = pdk.ViewState(
        longitude=-76.0,
        latitude=-10.0,
        zoom=2.18,
        pitch=0,
        bearing=0,
    )
    tooltip = {
        "html": (
            "<div style='font-family:Arial,sans-serif;max-width:340px'>"
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

    # map_style=None evita el error de pydeck/Streamlit Cloud que exige
    # map_provider='mapbox' cuando se pasa un estilo como diccionario.
    return pdk.Deck(
        layers=capas,
        initial_view_state=vista,
        map_style=None,
        tooltip=tooltip,
    )


# Streamlit conserva el módulo entre reruns: guardar la función original una sola vez.
if not hasattr(st, "_ops_original_pyplot"):
    st._ops_original_pyplot = st.pyplot
_ORIGINAL_PYPLOT = st._ops_original_pyplot


def _pyplot_interactivo(fig=None, *args, **kwargs):
    caller = inspect.currentframe().f_back
    g = caller.f_globals if caller is not None else {}
    if g.get("modo_mapa") == "Prioridad + amenazas" and all(
        k in g for k in ("geo", "actual", "filtrado")
    ):
        try:
            deck = _construir_deck(g)
            return st.pydeck_chart(deck, use_container_width=True, height=690)
        except Exception as exc:
            st.warning(f"No fue posible cargar la capa interactiva de amenazas: {exc}")
    return _ORIGINAL_PYPLOT(fig, *args, **kwargs)


st.pyplot = _pyplot_interactivo

# Ejecutar el dashboard original en cada rerun de Streamlit.
if "app_legacy" in sys.modules:
    importlib.reload(sys.modules["app_legacy"])
else:
    importlib.import_module("app_legacy")
