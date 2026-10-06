"""Entrada Streamlit para el dashboard de El Niño OPS/OMS.

El dashboard visual original se conserva en ``app_legacy.py``. Esta entrada
intercepta el render del mapa regional y lo reemplaza por un mapa deck.gl
interactivo con prioridad, pictogramas SitRep, callouts y tooltips.
"""

from io import BytesIO
import base64
import runpy
import inspect
import json
import sys
import html
import os

import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import pydeck as pdk
import streamlit as st
import folium
from folium.features import DivIcon
from shapely.geometry import box

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

# Ajustes exclusivos del dashboard interactivo para dar más aire a los callouts.
# No modifican las posiciones del mapa estático de SitRep.
CALLOUT_ROUTES_DASHBOARD = {
    # México / Centroamérica: filas amplias y separadas.
    "MEX": [(-101.0, 34.0), (-101.5, 29.5), (-102.0, 23.5)],
    "GTM": [(-114.0, 27.0), (-104.0, 26.0), (-96.0, 21.0), (-90.4, 15.7)],
    "HND": [(-114.0, 18.5), (-104.0, 18.2), (-95.0, 16.3), (-86.7, 14.8)],
    "SLV": [(-114.0, 10.0), (-104.0, 10.3), (-96.0, 12.0), (-88.9, 13.7)],
    "CRI": [(-114.0, 2.8), (-104.0, 3.3), (-95.0, 5.4), (-88.0, 7.8), (-84.2, 9.8)],
    "PAN": [(-73.5, 14.5), (-76.0, 12.5), (-78.8, 10.6), (-80.3, 8.5)],

    # Caribe: separar México, Jamaica, Puerto Rico y Trinidad y Tobago.
    "JAM": [(-75.0, 34.5), (-76.0, 26.0), (-77.3, 18.2)],
    "PRI": [(-58.0, 28.0), (-62.0, 24.0), (-66.4, 18.2)],
    "TTO": [(-49.0, 20.0), (-56.0, 15.5), (-61.2, 10.5)],

    # Costa pacífica de Sudamérica: columnas y filas separadas.
    "COL": [(-94.0, -4.5), (-85.0, -4.5), (-78.5, 0.5), (-74.5, 4.2)],
    "ECU": [(-94.0, -14.5), (-86.0, -14.5), (-79.0, -7.0), (-78.4, -1.5)],
    "PER": [(-94.0, -24.5), (-86.0, -24.5), (-80.0, -15.0), (-75.5, -9.5)],
    "BOL": [(-82.0, -32.0), (-74.0, -32.0), (-68.0, -22.0), (-64.8, -16.8)],
    "CHL": [(-105.0, -40.5), (-88.0, -40.5), (-77.0, -36.0), (-71.2, -33.5)],
}


def _hex_rgba(valor, alpha=255):
    h = valor.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


@st.cache_data(show_spinner=False)
def _icono_data_uri(clave, size=64):
    """Rasteriza el pictograma SitRep completo, circular y sin recorte.

    El resultado queda cacheado entre reruns para que cambiar un filtro no
    vuelva a abrir decenas de figuras Matplotlib.
    """
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


def _label_data_uri(texto):
    """Rasteriza una etiqueta de país con soporte completo de tildes/ñ."""
    texto = str(texto or "")
    cache = getattr(_label_data_uri, "_cache", {})
    if texto in cache:
        return cache[texto]

    font_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    font = ImageFont.truetype(font_path, 20)
    tmp = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), texto, font=font)
    pad_x, pad_y = 5, 4
    width = max(8, bbox[2] - bbox[0] + 2 * pad_x)
    height = max(8, bbox[3] - bbox[1] + 2 * pad_y)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text(
        (pad_x - bbox[0], pad_y - bbox[1]),
        texto,
        font=font,
        fill=(0, 62, 120, 255),
    )

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    resultado = (uri, width, height)
    cache[texto] = resultado
    _label_data_uri._cache = cache
    return resultado


def _amenazas_activas(fila, seleccion):
    salida = []
    for nombre in seleccion:
        col, clave = AMENAZAS[nombre]
        if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
            salida.append((nombre, clave))
    return salida


def _props_popup(titulo, linea1="", linea2="", linea3=""):
    """Estructura uniforme para hover/click en todas las capas."""
    return {
        "tooltip_title": str(titulo or ""),
        "tooltip_line1": str(linea1 or ""),
        "tooltip_line2": str(linea2 or ""),
        "tooltip_line3": str(linea3 or ""),
    }



def _filtrar_geografia_mapa(mapa, filtrado, hay_filtros, filtro_prioridad):
    """Mantiene el contexto geográfico completo y resalta lo filtrado.

    Regla visual:
    - sin filtros, cada país conserva su prioridad normal;
    - con filtros, los países que cumplen conservan su prioridad y los demás
      siguen visibles en el color "Fuera del filtro";
    - si se selecciona "Sin priorización", los países del GeoPackage que no
      tienen fila en el SitRep permanecen como "Sin priorización" en vez de
      pasar a "Fuera del filtro".
    """
    salida = mapa.copy()
    salida["prioridad_mapa"] = salida["prioridad"].fillna("Sin priorización")

    if not hay_filtros:
        return salida

    seleccionados = set(filtrado["iso3"].dropna().astype(str))
    fuera = ~salida["ISO_CC"].isin(seleccionados)

    prioridad_sel = set(str(x) for x in (filtro_prioridad or []))
    if "Sin priorización" in prioridad_sel:
        # Países sin fila en la base son justamente los que deben seguir
        # representándose como "Sin priorización".
        fuera = fuera & salida["iso3"].notna()

    salida.loc[fuera, "prioridad_mapa"] = "Fuera del filtro"
    return salida


def _construir_folium(frame_globals):
    """Mapa Leaflet interactivo con hover por país, callouts e iconos SitRep."""
    geo = frame_globals["geo"].copy()
    actual = frame_globals["actual"].copy()
    filtrado = frame_globals["filtrado"].copy()
    hay_filtros = bool(frame_globals.get("hay_filtros", False))
    filtro_prioridad = frame_globals.get("filtro_pri", [])
    seleccion = frame_globals.get("amenazas_mapa")
    if seleccion is None:
        seleccion = list(AMENAZAS.keys())

    nombres_cortos = frame_globals.get("AMENAZAS_CORTAS", {})

    cols = ["iso3", "pais", "prioridad", "situacion_predominante"]
    cols += [v[0] for v in AMENAZAS.values()]
    cols = [c for c in cols if c in actual.columns]
    info = actual[cols].drop_duplicates("iso3")

    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")

    # Recortar la geografía a la ventana continental de interés.
    # Esto elimina Hawái y otros fragmentos muy occidentales del multipolígono
    # de Estados Unidos sin afectar México, Canadá continental ni Sudamérica.
    clip_americas = box(-135.0, -62.0, -25.0, 85.0)
    mapa["geometry"] = mapa.geometry.intersection(clip_americas)
    mapa = _filtrar_geografia_mapa(
        mapa,
        filtrado=filtrado,
        hay_filtros=hay_filtros,
        filtro_prioridad=filtro_prioridad,
    )

    def amenazas_texto(r):
        activas = _amenazas_activas(r, list(AMENAZAS.keys()))
        if not activas:
            return "Sin amenazas / impactos priorizados"
        return ", ".join(nombres_cortos.get(n, n) for n, _ in activas)

    mapa["pais_popup"] = mapa["pais"].fillna(mapa["COUNTRY"]).astype(str)
    mapa["prioridad_popup"] = mapa["prioridad_mapa"].astype(str)
    mapa["amenazas_popup"] = mapa.apply(amenazas_texto, axis=1)

    mapa["fill_hex"] = mapa["prioridad_mapa"].map(
        lambda p: COLORES_PRIORIDAD.get(p, COLORES_PRIORIDAD["Sin priorización"])
    )

    # Sin teselas externas: océano uniforme y navegación por las Américas,
    # permitiendo subir hasta Canadá sin perder el encuadre inicial México-Sudamérica.
    m = folium.Map(
        location=[-11.5, -76.0],
        zoom_start=3.0,
        tiles=None,
        min_zoom=2,
        max_zoom=7,
        min_lat=-85,
        max_lat=85,
        min_lon=-190,
        max_lon=60,
        max_bounds=True,
        world_copy_jump=False,
        zoom_control=True,
        control_scale=False,
        prefer_canvas=False,
        zoom_snap=0.1,
        zoom_delta=0.25,
    )
    m.get_root().html.add_child(
        folium.Element(
            "<style>"
            ".leaflet-container{background:#D9EEF7!important;}"
            ".leaflet-interactive:focus,"
            ".leaflet-interactive:focus-visible{outline:none!important;box-shadow:none!important;}"
            ".leaflet-tooltip.ops-tooltip{"
            "background:white;border:1px solid #D9E6EE;border-radius:9px;"
            "box-shadow:0 4px 16px rgba(0,0,0,.14);color:#17324D;"
            "font-family:Arial,sans-serif;font-size:12px;padding:8px 10px;"
            "max-width:360px;white-space:normal;line-height:1.35;}"
            ".leaflet-tooltip.ops-tooltip:before{display:none;}"
            "</style>"
        )
    )

    geojson_data = json.loads(mapa.to_json())
    capa_paises = folium.GeoJson(
        data=geojson_data,
        name="Países",
        style_function=lambda feat: {
            "fillColor": feat["properties"].get("fill_hex", "#BDBDBD"),
            "color": "#FFFFFF",
            "weight": 0.8,
            "fillOpacity": 1.0,
        },
        highlight_function=lambda feat: {
            "weight": 1.5,
            "color": "#004B87",
            "fillOpacity": 0.88,
        },
        smooth_factor=0.3,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "pais_popup",
                "prioridad_popup",
                "amenazas_popup",
            ],
            aliases=[
                "<b>País:</b>",
                "<b>Prioridad:</b>",
                "<b>Amenazas / impactos:</b>",
            ],
            localize=False,
            sticky=True,
            labels=True,
            style=(
                "background-color:white;color:#17324D;"
                "font-family:Arial,sans-serif;font-size:12px;"
                "padding:8px 10px;min-width:300px;max-width:360px;white-space:normal;"
            ),
        ),
    )
    capa_paises.add_to(m)

    # Mantener hover, pero evitar cualquier efecto visual/acción al hacer clic
    # sobre un país (Leaflet/SVG puede dejar un rectángulo de foco azul).
    # Mantener hover, pero impedir que un clic enfoque/seleccione visualmente
    # los polígonos SVG de Leaflet. Se usan listeners delegados para que funcione
    # aunque los paths se creen después de ejecutar este script.
    m.get_root().script.add_child(
        folium.Element(
            """
            (function() {
                function esPaisLeaflet(el) {
                    return !!(el && el.classList && el.classList.contains('leaflet-interactive'));
                }

                document.addEventListener('focusin', function(ev) {
                    if (esPaisLeaflet(ev.target) && ev.target.blur) {
                        ev.target.blur();
                    }
                }, true);

                document.addEventListener('click', function(ev) {
                    if (!esPaisLeaflet(ev.target)) return;
                    ev.preventDefault();
                    ev.stopPropagation();
                    if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
                    if (ev.target.blur) ev.target.blur();
                }, true);
            })();
            """
        )
    )

    # Callouts e iconos seleccionados. Se dibujan encima de los polígonos.
    for _, fila in filtrado.iterrows():
        iso = str(fila.get("iso3", "")).upper().strip()
        if iso not in mapa_ref.LABELS or iso not in mapa_ref.ROUTES or iso not in mapa_ref.TARGET:
            continue

        _, _, nombre_pais = mapa_ref.LABELS[iso]
        ruta_lonlat = list(CALLOUT_ROUTES_DASHBOARD.get(iso, mapa_ref.ROUTES[iso]))
        ruta = [(lat, lon) for lon, lat in ruta_lonlat]
        target_lon, target_lat = mapa_ref.TARGET[iso]
        activas = _amenazas_activas(fila, seleccion)

        # El primer punto de cada ruta ya está diseñado como punto exterior
        # del callout. Usarlo como borde del bloque evita que los pictogramas
        # se proyecten sobre el país y garantiza que la línea salga desde el
        # borde del callout, sin atravesar los iconos.
        callout_lon, callout_lat = ruta_lonlat[0]
        callout_a_la_izquierda = callout_lon < target_lon

        ancho_por_iconos = len(activas) * 30 + 8
        ancho_por_nombre = max(90, len(nombre_pais) * 7 + 12)
        ancho_callout = min(230, max(120, ancho_por_iconos, ancho_por_nombre))
        anchor_x = ancho_callout if callout_a_la_izquierda else 0
        alineacion = "right" if callout_a_la_izquierda else "left"
        justificar = "flex-end" if callout_a_la_izquierda else "flex-start"

        folium.PolyLine(
            ruta,
            color="#075594",
            weight=1.15,
            opacity=0.86,
            interactive=False,
        ).add_to(m)

        folium.CircleMarker(
            location=[target_lat, target_lon],
            radius=1.35,
            color="#075594",
            fill=True,
            fill_color="#075594",
            fill_opacity=1,
            weight=0,
            interactive=False,
        ).add_to(m)

        imgs = "".join(
            f'<img src="{_icono_data_uri(clave)}" '
            f'style="width:27px;height:27px;object-fit:contain;vertical-align:middle;">'
            for _, clave in activas
        )
        bloque_iconos = (
            f'<div class="ops-callout-icons" data-iso="{html.escape(iso)}" '
            f'style="display:flex;gap:3px;align-items:center;justify-content:{justificar};'
            f'margin-top:3px;width:{ancho_callout}px;">{imgs}</div>'
            if imgs else ""
        )
        label_html = (
            f'<div class="ops-callout" data-iso="{html.escape(iso)}" '
            f'style="width:{ancho_callout}px;white-space:nowrap;pointer-events:none;'
            f'font-family:Arial,sans-serif;color:#004B87;text-align:{alineacion};">'
            f'<div style="font-size:12px;font-weight:700;line-height:1.05;">{html.escape(nombre_pais)}</div>'
            f'{bloque_iconos}'
            '</div>'
        )

        folium.Marker(
            location=[callout_lat, callout_lon],
            icon=DivIcon(
                icon_size=(ancho_callout, 55),
                icon_anchor=(anchor_x, 13),
                html=label_html,
            ),
            interactive=False,
        ).add_to(m)

    # Vista inicial determinística: centro continental y zoom suficiente para
    # mostrar México, Centroamérica y toda Sudamérica sin pegar el continente
    # a ninguno de los bordes. Hawái no se dibuja porque la geometría fue
    # recortada previamente a -135°.
    return m


def _construir_deck(frame_globals):
    geo = frame_globals["geo"].copy()
    actual = frame_globals["actual"].copy()
    filtrado = frame_globals["filtrado"].copy()
    hay_filtros = bool(frame_globals.get("hay_filtros", False))
    filtro_prioridad = frame_globals.get("filtro_pri", [])
    seleccion = frame_globals.get("amenazas_mapa")
    if seleccion is None:
        seleccion = list(AMENAZAS.keys())

    cols = ["iso3", "pais", "prioridad", "situacion_predominante"]
    cols += [v[0] for v in AMENAZAS.values()]
    cols = [c for c in cols if c in actual.columns]
    info = actual[cols].drop_duplicates("iso3")

    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")
    mapa = _filtrar_geografia_mapa(
        mapa,
        filtrado=filtrado,
        hay_filtros=hay_filtros,
        filtro_prioridad=filtro_prioridad,
    )

    def amenazas_texto(r):
        activas = _amenazas_activas(r, list(AMENAZAS.keys()))
        return ", ".join(n for n, _ in activas) if activas else "Sin amenazas / impactos priorizados"

    mapa["fill_color"] = mapa["prioridad_mapa"].map(
        lambda p: _hex_rgba(COLORES_PRIORIDAD.get(p, COLORES_PRIORIDAD["Sin priorización"]))
    )
    mapa["tooltip_title"] = mapa["pais"].fillna(mapa["COUNTRY"])
    mapa["tooltip_line1"] = "Prioridad: " + mapa["prioridad_mapa"].astype(str)
    mapa["tooltip_line2"] = mapa.apply(lambda r: "Amenazas / impactos: " + amenazas_texto(r), axis=1)
    situacion_popup = mapa["situacion_predominante"].fillna(
        "Sin hallazgos priorizados en este SitRep"
    ).astype(str)
    situacion_popup = situacion_popup.apply(
        lambda s: s if len(s) <= 210 else s[:207].rstrip() + "..."
    )
    mapa["tooltip_line3"] = "Situación: " + situacion_popup
    geojson = json.loads(mapa.to_json())
    # Duplicar campos del popup al nivel raíz del Feature para que el hover
    # funcione de forma uniforme en GeoJsonLayer e IconLayer.
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

        x, y, nombre_pais = mapa_ref.LABELS[iso]
        rutas.append({"path": [list(pt) for pt in mapa_ref.ROUTES[iso]]})
        anclas.append({"position": list(mapa_ref.TARGET[iso])})
        label_uri, label_w, label_h = _label_data_uri(nombre_pais)
        etiquetas.append({
            "position": [x, y],
            "icon": {
                "url": label_uri,
                "width": label_w,
                "height": label_h,
                "anchorX": 0,
                "anchorY": label_h / 2,
            },
            "size": 13,
            **_props_popup(
                nombre_pais,
                "Amenazas / impactos",
                "Pasa el cursor sobre los pictogramas para ver el detalle.",
            ),
        })

        # Todos los iconos comparten la coordenada del nombre y se separan en
        # píxeles. Esto los mantiene pegados al callout al hacer zoom/pan.
        for i, (nombre, clave) in enumerate(activas):
            iconos.append({
                "position": [x, y],
                "pixel_offset": [i * 24, 22],
                "icon": {
                    "url": _icono_data_uri(clave),
                    "width": 112,
                    "height": 112,
                    "anchorX": 56,
                    "anchorY": 56,
                },
                "size": 20,
                **_props_popup(
                    nombre_pais,
                    nombre,
                    "Amenaza / impacto reportado",
                ),
            })

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
            id="oceano",
            get_polygon="polygon",
            get_fill_color=[217, 238, 247, 255],
            stroked=False,
            pickable=False,
        ),
        pdk.Layer(
            "GeoJsonLayer",
            geojson,
            id="paises",
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            get_fill_color="properties.fill_color",
            get_line_color=[255, 255, 255, 255],
            line_width_min_pixels=0.8,
            highlight_color=[255, 255, 255, 70],
        ),
    ]

    if rutas:
        capas.append(
            pdk.Layer(
                "PathLayer",
                rutas,
                id="callouts",
                get_path="path",
                get_color=[7, 85, 148, 205],
                width_min_pixels=0.85,
                pickable=False,
            )
        )
    if anclas:
        capas.append(
            pdk.Layer(
                "ScatterplotLayer",
                anclas,
                id="anclas",
                get_position="position",
                get_fill_color=[7, 85, 148, 255],
                get_radius=0.65,
                radius_units="pixels",
                radius_min_pixels=0.65,
                radius_max_pixels=0.95,
                pickable=False,
            )
        )
    if etiquetas:
        capas.append(
            pdk.Layer(
                "IconLayer",
                etiquetas,
                id="etiquetas-paises",
                get_icon="icon",
                get_position="position",
                get_size="size",
                size_units="pixels",
                size_scale=1,
                size_min_pixels=12,
                size_max_pixels=15,
                pickable=True,
            )
        )
    if iconos:
        capas.append(
            pdk.Layer(
                "IconLayer",
                iconos,
                id="iconos-amenazas",
                get_icon="icon",
                get_position="position",
                get_pixel_offset="pixel_offset",
                get_size="size",
                size_units="pixels",
                size_scale=1,
                size_min_pixels=18,
                size_max_pixels=22,
                pickable=True,
            )
        )

    vista = pdk.ViewState(
        longitude=-76.0,
        latitude=-13.5,
        zoom=1.72,
        min_zoom=1.45,
        max_zoom=5.25,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": (
            "<div style='font-family:Arial,sans-serif;max-width:360px;line-height:1.35'>"
            "<b style='color:#004B87;font-size:13px'>{tooltip_title}</b><br>"
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
            "boxShadow": "0 4px 16px rgba(0,0,0,.12)",
        },
    }

    # Pan y zoom habilitados, pero acotados a las Américas.
    vista_mapa = pdk.View(
        type="MapView",
        controller={
            "dragPan": True,
            "dragRotate": False,
            "scrollZoom": True,
            "doubleClickZoom": True,
            "touchZoom": True,
            "keyboard": True,
            "maxBounds": [[-122.0, -62.0], [-30.0, 35.0]],
            "maxBoundsPadding": 0,
            "rubberBand": False,
        },
        repeat=False,
    )

    return pdk.Deck(
        layers=capas,
        initial_view_state=vista,
        views=[vista_mapa],
        map_style=None,
        tooltip=tooltip,
    )


def _mostrar_seleccion_mapa(evento):
    """Muestra una ficha persistente al hacer clic sobre país/icono/etiqueta."""
    if evento is None:
        return
    try:
        seleccion = evento.selection
        objetos = seleccion.get("objects", {}) if seleccion else {}
    except Exception:
        return

    elegido = None
    # Priorizar país; si no, aceptar icono o etiqueta.
    for layer_id in ("paises", "iconos-amenazas", "etiquetas-paises"):
        candidatos = objetos.get(layer_id, []) if isinstance(objetos, dict) else []
        if candidatos:
            elegido = candidatos[0]
            break
    if not elegido:
        return

    props = elegido.get("properties", {}) if isinstance(elegido, dict) else {}
    if not props:
        return

    titulo = props.get("tooltip_title", "")
    l1 = props.get("tooltip_line1", "")
    l2 = props.get("tooltip_line2", "")
    l3 = props.get("tooltip_line3", "")
    if titulo:
        st.markdown(
            f"""
            <div style="margin-top:.45rem;padding:.72rem .9rem;border:1px solid #D9E6EE;
                        border-radius:10px;background:#F8FBFD;color:#17324D;">
                <div style="font-weight:700;color:#004B87;margin-bottom:.18rem;">{titulo}</div>
                <div>{l1}</div>
                <div>{l2}</div>
                <div style="color:#60788A;font-size:.9rem;">{l3}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_mapa_interactivo(frame_globals):
    """Render unidireccional y estable del mapa Folium.

    El tablero no necesita devolver clics/estado del mapa a Python, así que se
    usa el iframe nativo de Streamlit. Esto evita callbacks del componente y
    reduce el riesgo de reruns/iframes huérfanos al cambiar filtros.
    """
    mapa_folium = _construir_folium(frame_globals)
    html_mapa = mapa_folium.get_root().render()
    return st.iframe(
        html_mapa,
        width="stretch",
        height=652,
    )


# Exponer el renderer al dashboard legacy. Así los cambios de filtros no
# construyen una figura GeoPandas/Matplotlib que luego era descartada.
st._ops_render_interactive_map = _render_mapa_interactivo


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
            return _render_mapa_interactivo(g)
        except Exception as exc:
            st.warning(f"No fue posible cargar el mapa interactivo: {exc}")
    return _ORIGINAL_PYPLOT(fig, *args, **kwargs)


st.pyplot = _pyplot_interactivo

# Ejecutar el dashboard original en cada rerun de Streamlit.
# Se usa run_path para ejecutar una copia fresca en cada rerun sin depender del
# estado de sys.modules, que puede quedar inconsistente durante reruns rápidos.
# En CI se puede importar este módulo sin lanzar toda la app para probar el mapa.
if os.environ.get("OPS_MAP_SMOKE_TEST") != "1":
    runpy.run_path(
        os.path.join(os.path.dirname(__file__), "app_legacy.py"),
        run_name="app_legacy_runtime",
    )
