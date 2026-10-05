"""Entrada Streamlit.

Conserva el dashboard original en ``app_legacy.py`` y reemplaza únicamente el
render estático de "Prioridad + amenazas" por un mapa deck.gl interactivo.
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


def _icono_data_uri(clave, size=66):
    cache = getattr(_icono_data_uri, "_cache", {})
    if clave in cache:
        return cache[clave]

    fig = plt.figure(figsize=(0.76, 0.76), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    dibujo = mapa_ref.ICONOS[clave](size)
    ax.add_artist(
        mapa_ref.AnnotationBbox(
            dibujo,
            (0.5, 0.5),
            xycoords=ax.transAxes,
            frameon=False,
            box_alignment=(0.5, 0.5),
        )
    )
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=100, transparent=True, pad_inches=0)
    plt.close(fig)
    uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    cache[clave] = uri
    _icono_data_uri._cache = cache
    return uri


def _feature_point(position, **props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": list(position)},
        "properties": props,
    }


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
    mapa["tooltip_line3"] = mapa["situacion_predominante"].fillna("Sin hallazgos priorizados en este SitRep")
    geojson = json.loads(mapa.to_json())

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
        etiquetas.append(
            _feature_point(
                (x, y),
                pais=nombre_pais,
                tooltip_title=nombre_pais,
                tooltip_line1="Callout de amenazas / impactos",
                tooltip_line2="Pasa el cursor sobre cada pictograma para ver su significado.",
                tooltip_line3="",
            )
        )

        inicio_x = x + 1.0 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0)
        y_iconos = y + mapa_ref.DESPLAZAMIENTO_ICONOS_Y
        separacion = 2.45
        for i, (nombre, clave) in enumerate(activas):
            iconos.append(
                _feature_point(
                    (inicio_x + i * separacion, y_iconos),
                    icon={
                        "url": _icono_data_uri(clave),
                        "width": 76,
                        "height": 76,
                        "anchorX": 38,
                        "anchorY": 38,
                    },
                    size=max(29, mapa_ref.TAMANOS_ICONOS.get(iso, 27) + 4),
                    tooltip_title=nombre_pais,
                    tooltip_line1=nombre,
                    tooltip_line2="Amenaza / impacto reportado",
                    tooltip_line3="",
                )
            )

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
            line_width_min_pixels=0.8,
            highlight_color=[255, 255, 255, 55],
        )
    ]

    if rutas:
        capas.append(
            pdk.Layer(
                "PathLayer",
                rutas,
                get_path="path",
                get_color=[7, 85, 148, 205],
                width_min_pixels=1.15,
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
                get_position="geometry.coordinates",
                get_text="properties.pais",
                get_color=[0, 62, 120, 255],
                get_size=14,
                size_units="pixels",
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
                get_icon="properties.icon",
                get_position="geometry.coordinates",
                get_size="properties.size",
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
    vista = pdk.ViewState(longitude=-76.0, latitude=-10.0, zoom=2.18, pitch=0, bearing=0)
    tooltip = {
        "html": (
            "<div style='font-family:Arial,sans-serif;max-width:340px'>"
            "<b style='color:#004B87'>{properties.tooltip_title}</b><br>"
            "{properties.tooltip_line1}<br>"
            "{properties.tooltip_line2}<br>"
            "<span style='color:#60788A'>{properties.tooltip_line3}</span>"
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
    return pdk.Deck(layers=capas, initial_view_state=vista, map_style=estilo, tooltip=tooltip)


# Streamlit conserva el módulo entre reruns; guardar la función original una sola vez.
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
