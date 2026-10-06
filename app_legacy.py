from pathlib import Path
from io import BytesIO
import base64
import html
import json

import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import matplotlib.pyplot as plt
from scripts import mapa_sitrep as mapa_ref


# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE = Path(__file__).resolve().parent
RUTA_BASE = BASE / "data" / "base_maestra_elnino.csv"
RUTA_GPKG = BASE / "data" / "geografia" / "paises_americas.gpkg"
RUTA_LOGO = BASE / "assets" / "ops_oms.png"

AZUL_OPS = "#004B87"
AZUL_SEC = "#0072CE"
AZUL_MAR = "#D9EEF7"
TEXTO = "#17324D"
GRIS = "#CACACA"
GRIS_CLARO = "#F5F8FA"
BORDE = "#D9E6EE"

COLORES_PRIORIDAD = {
    "Alta": "#D71920",
    "Media": "#FF8618",
    "Baja": "#F6C344",
    "Sin priorización": "#BDBDBD",
    "Fuera del filtro": "#E7EDF1",
}
ORDEN_PRIORIDAD = ["Alta", "Media", "Baja", "Sin priorización"]

AMENAZAS = {
    "Sequía / agua": ("icono_agua", "agua"),
    "Inundaciones / lluvias": ("icono_inundaciones", "inundaciones"),
    "Incendios / quemadas": ("icono_incendios", "incendios"),
    "Inseguridad alimentaria": ("icono_alimentos", "alimentos"),
    "Dengue / otras arbovirosis": ("icono_arbovirosis", "arbovirosis"),
    "Calidad del aire / riesgo respiratorio": ("icono_respiratorio", "respiratorio"),
    "Afectación de servicios de salud": ("icono_servicios", "servicios"),
}

AMENAZAS_CORTAS = {
    "Sequía / agua": "Sequía",
    "Inundaciones / lluvias": "Inundaciones",
    "Incendios / quemadas": "Incendios",
    "Inseguridad alimentaria": "Inseguridad alimentaria",
    "Dengue / otras arbovirosis": "Arbovirosis",
    "Calidad del aire / riesgo respiratorio": "Aire",
    "Afectación de servicios de salud": "Afectación servicios",
}

AMENAZA_CLAVE_ESTATICA = {
    "Sequía / agua": "agua",
    "Inundaciones / lluvias": "inundaciones",
    "Incendios / quemadas": "incendios",
    "Inseguridad alimentaria": "alimentos",
    "Dengue / otras arbovirosis": "arbovirosis",
    "Calidad del aire / riesgo respiratorio": "respiratorio",
    "Afectación de servicios de salud": "servicios",
}


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


# Posición de las etiquetas de amenazas. Se ubican principalmente sobre océano
# o espacios libres para evitar tapar los países y mejorar la lectura.
POSICIONES_CALLOUTS = {
    "MEX": (-112.5, 27.0),
    "GTM": (-107.0, 20.0),
    "HND": (-104.0, 16.1),
    "SLV": (-103.0, 11.7),
    "CRI": (-98.3, 7.4),
    "PAN": (-92.0, 3.5),
    "JAM": (-76.0, 25.5),
    "PRI": (-64.0, 25.5),
    "TTO": (-49.0, 13.0),
    "COL": (-90.0, 0.0),
    "ECU": (-91.0, -6.0),
    "PER": (-91.0, -12.5),
    "BOL": (-48.0, -18.0),
    "BRA": (-39.5, -8.5),
    "CHL": (-88.0, -29.5),
    "ARG": (-79.0, -40.0),
    "URY": (-45.0, -34.0),
}

CIFRAS = {
    "personas_afectadas": "Personas afectadas",
    "personas_damnificadas": "Personas damnificadas",
    "familias_afectadas": "Familias afectadas",
    "muertes": "Muertes",
    "heridos": "Heridos",
    "personas_inseguridad_alimentaria_min": "Inseguridad alimentaria (mín.)",
    "personas_inseguridad_alimentaria_max": "Inseguridad alimentaria (máx.)",
    "personas_emergencia_alimentaria": "Emergencia alimentaria",
    "establecimientos_salud_afectados": "Establecimientos afectados",
    "establecimientos_salud_expuestos": "Establecimientos expuestos",
    "hectareas_incendios": "Hectáreas por incendios",
    "municipios_afectados": "Municipios afectados",
}

CHART_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "responsive": True,
}

st.set_page_config(
    page_title="El Niño y salud pública | OPS/OMS",
    page_icon=str(RUTA_LOGO),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"""
    <style>
        :root {{ --ops-blue:{AZUL_OPS}; --ops-blue2:{AZUL_SEC}; --ops-border:{BORDE}; }}
        .block-container {{
            padding-top: 4.25rem !important;
            padding-bottom: 2.2rem;
            max-width: 1420px;
        }}
        h1, h2, h3 {{color:{AZUL_OPS};}}
        [data-testid="stHeader"] {{background:rgba(255,255,255,.96);}}

        .ops-hero {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:2rem;
            background:linear-gradient(105deg,#FFFFFF 0%,#FFFFFF 62%,#EEF8FC 100%);
            border:1px solid {BORDE};
            border-radius:18px;
            padding:1.15rem 1.45rem;
            box-shadow:0 4px 18px rgba(0,75,135,.07);
            margin-top:.25rem;
            margin-bottom:.9rem;
            position:relative;
            z-index:1;
        }}
        .ops-hero-copy {{min-width:0;}}
        .ops-kicker {{
            color:{AZUL_SEC}; font-weight:800; font-size:.76rem;
            letter-spacing:.08em; text-transform:uppercase; margin-bottom:.28rem;
        }}
        .ops-title {{
            color:{AZUL_OPS}; font-weight:800; font-size:2rem;
            line-height:1.08; letter-spacing:-.025em; margin:0;
        }}
        .ops-subtitle {{
            color:#5A7286; font-size:.94rem; margin-top:.42rem; line-height:1.45;
        }}
        .ops-area {{
            color:{AZUL_OPS};
            font-size:.82rem;
            font-weight:700;
            margin-top:.46rem;
            line-height:1.35;
        }}
        .ops-logo {{width:220px; max-width:24vw; height:auto; display:block;}}

        .filter-label {{
            color:{AZUL_OPS}; font-weight:800; font-size:.92rem;
            margin-bottom:.25rem;
        }}
        .filter-note {{
            color:#728596;
            font-size:.78rem;
            line-height:1.4;
            margin-top:.35rem;
            margin-bottom:1rem;
            padding:.55rem .75rem;
            background:#F7FAFC;
            border:1px solid #E6EEF3;
            border-radius:9px;
        }}

        .map-note {{
            color:#6D8191;
            font-size:.76rem;
            line-height:1.35;
            margin-top:-.2rem;
            margin-bottom:.7rem;
        }}

        .section-head {{margin:1.25rem 0 .55rem 0;}}
        .section-title {{
            color:{AZUL_OPS}; font-weight:800; font-size:1.18rem;
            letter-spacing:-.01em; line-height:1.2;
        }}
        .section-subtitle {{color:#728596; font-size:.82rem; margin-top:.12rem;}}

        div[data-testid="stMetric"] {{
            background:#FFFFFF;
            border:1px solid {BORDE};
            border-radius:14px;
            padding:.8rem .9rem;
            box-shadow:0 2px 10px rgba(0,75,135,.045);
            min-height:100px;
        }}
        div[data-testid="stMetricLabel"] {{color:#5C7182; font-size:.78rem; line-height:1.2;}}
        div[data-testid="stMetricValue"] {{color:{AZUL_OPS}; font-size:1.75rem; font-weight:800;}}

        .summary-card {{
            border:1px solid {BORDE}; background:#FFFFFF; border-radius:14px;
            padding:.75rem .95rem; margin-bottom:.65rem;
        }}
        .summary-title {{
            color:{AZUL_OPS}; font-size:.91rem; font-weight:800;
            margin:0 0 .42rem 0;
        }}
        .threat-row {{
            display:flex; justify-content:space-between; align-items:center; gap:.75rem;
            border-bottom:1px solid #EAF0F4; padding:.35rem 0; font-size:.84rem;
            color:{TEXTO};
        }}
        .threat-row:last-child {{border-bottom:none;}}
        .threat-count {{font-weight:800; color:{AZUL_OPS}; min-width:1.5rem; text-align:right;}}

        /* Leyendas laterales: título, iconos, texto y cifras en una misma grilla. */
        .legend-card {{
            border:1px solid {BORDE}; background:#FFFFFF; border-radius:14px;
            margin-bottom:.75rem; overflow:hidden;
        }}
        .legend-card.priority-card {{margin-bottom:0;}}
        .legend-title {{
            min-height:52px; display:flex; align-items:center;
            padding:0 1rem; color:{AZUL_OPS}; font-size:.94rem; font-weight:800;
            border-bottom:1px solid #EAF0F4; line-height:1.2;
        }}
        .legend-body {{padding:.5rem 1rem .62rem 1rem;}}
        .legend-row {{
            display:grid; grid-template-columns:minmax(0,1fr) 2rem;
            align-items:center; column-gap:.75rem; min-height:38px;
            color:{TEXTO}; font-size:.84rem;
        }}
        .legend-row + .legend-row {{border-top:1px solid #EEF3F6;}}
        .legend-card.amenazas-card .legend-row {{
            min-height:56px;
        }}
        .legend-label {{
            display:flex; align-items:center; gap:.55rem; min-width:0;
            line-height:1.22;
        }}
        .threat-icon {{
            width:22px !important; height:22px !important; object-fit:contain;
            display:block; flex:0 0 22px; margin:0;
        }}
        .priority-dot {{
            width:14px; height:14px; border-radius:50%;
            display:block; flex:0 0 14px; margin-left:4px; margin-right:4px;
        }}
        .legend-count {{
            font-weight:800; color:{AZUL_OPS}; width:2rem;
            text-align:right; justify-self:end; line-height:1;
        }}

        .country-breakdown {{
            border-top:1px solid #EAF0F4;
            margin-top:.1rem;
            padding:.35rem .1rem .15rem .1rem;
        }}
        .country-breakdown-row {{
            padding:.42rem 0;
        }}
        .country-breakdown-row + .country-breakdown-row {{
            border-top:1px solid #EEF3F6;
        }}
        .country-breakdown-head {{
            display:flex; align-items:center; justify-content:space-between; gap:.6rem;
            color:#5C7182; font-size:.74rem; font-weight:800; line-height:1.2;
        }}
        .country-breakdown-label {{
            display:flex; align-items:center; gap:.38rem;
        }}
        .country-breakdown-dot {{
            width:8px; height:8px; border-radius:50%; display:inline-block; flex:0 0 8px;
        }}
        .country-breakdown-count {{
            color:{AZUL_OPS}; font-weight:800;
        }}
        .country-breakdown-names {{
            color:{TEXTO}; font-size:.79rem; line-height:1.38; margin-top:.2rem;
        }}

        .country-summary {{
            display:grid; grid-template-columns:minmax(180px,.8fr) 1.35fr 1fr;
            gap:1rem; align-items:start; background:#F8FBFD;
            border:1px solid {BORDE}; border-radius:14px; padding:1rem 1.05rem;
            margin:.25rem 0 .75rem 0;
        }}
        .country-name {{color:{AZUL_OPS}; font-weight:800; font-size:1.32rem; margin-bottom:.45rem;}}
        .summary-label {{color:#6C8192; font-size:.73rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; margin-bottom:.2rem;}}
        .summary-text {{color:{TEXTO}; font-size:.9rem; line-height:1.4;}}
        .priority-pill {{
            display:inline-block; padding:.28rem .68rem; border-radius:999px;
            color:white; font-weight:800; font-size:.8rem;
        }}
        .priority-pill.light {{color:#5D4B00;}}

        .detail-card {{
            background:#FFFFFF; border:1px solid {BORDE}; border-radius:14px;
            padding:.95rem 1.05rem; min-height:158px; height:100%;
            box-shadow:0 2px 9px rgba(0,75,135,.035);
            margin-bottom:.85rem;
        }}
        .detail-card h4 {{color:{AZUL_OPS}; margin:0 0 .48rem 0; font-size:.94rem;}}
        .detail-card p {{color:{TEXTO}; margin:0; font-size:.88rem; line-height:1.48;}}

        .empty-state {{
            background:#F7FAFC; border:1px dashed #BFD4E1; border-radius:13px;
            padding:.95rem 1.05rem; color:#62798B; font-size:.87rem;
        }}
        .caption-box {{
            font-size:.77rem;
            color:#6B7F90;
            line-height:1.45;
            margin-top:.85rem;
            margin-bottom:1rem;
            padding:.62rem .78rem;
            background:#F7FAFC;
            border:1px solid #E6EEF3;
            border-radius:9px;
        }}
        div[data-testid="stSelectbox"], div[data-testid="stMultiSelect"] {{font-size:.9rem;}}

        @media (max-width: 900px) {{
            .block-container {{padding-top:4.75rem !important;}}
            .ops-hero {{padding:1rem; gap:1rem;}}
            .ops-title {{font-size:1.55rem;}}
            .ops-logo {{width:165px; max-width:32vw;}}
            .country-summary {{grid-template-columns:1fr;}}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATOS
# ============================================================
@st.cache_data(show_spinner=False)
def cargar_base():
    if not RUTA_BASE.exists():
        raise FileNotFoundError(f"No se encontró {RUTA_BASE}")

    df = pd.read_csv(RUTA_BASE, encoding="utf-8")
    df["fecha_corte"] = pd.to_datetime(df["fecha_corte"], errors="coerce")
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], errors="coerce")
    df["sitrep_numero"] = pd.to_numeric(df["sitrep_numero"], errors="coerce")

    for col in CIFRAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col, _ in AMENAZAS.values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


@st.cache_resource(show_spinner=False)
def cargar_geografia():
    if not RUTA_GPKG.exists():
        raise FileNotFoundError(f"No se encontró {RUTA_GPKG}")
    try:
        gdf = gpd.read_file(RUTA_GPKG, engine="pyogrio")
    except Exception:
        gdf = gpd.read_file(RUTA_GPKG)
    return gdf.to_crs("EPSG:4326")


def texto(valor, fallback="Sin información reportada"):
    if pd.isna(valor):
        return fallback
    valor = str(valor).strip()
    return valor if valor and valor.lower() != "nan" else fallback


def texto_html(valor, fallback="Sin información reportada"):
    return html.escape(texto(valor, fallback)).replace("\n", "<br>")


def formato_numero(valor):
    if pd.isna(valor):
        return None
    if abs(valor - int(valor)) < 1e-9:
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def es_activo(valor):
    t = texto(valor, "").lower()
    return bool(t) and not t.startswith("no") and t not in {"sin declaratoria", "sin información"}


def es_impacto(valor):
    t = texto(valor, "").lower()
    return bool(t) and not t.startswith("no")


def clasificar_atribucion(valor):
    """Agrupa la atribución a El Niño en categorías comparables para el tablero."""
    t = texto(valor, "").strip().lower()
    if not t or t in {"no aplica", "sin información", "sin informacion"}:
        return "No aplica / sin información"
    if "descart" in t or t.startswith("no confirm") or "no confirmada" in t:
        return "No confirmada / descartada"
    if "confirmada/relacionada" in t or "confirmada / relacionada" in t or t.startswith("confirmada"):
        return "Confirmada / relacionada"
    if "compatible" in t or "contextual" in t:
        return "Compatible / contextual"
    if "prospect" in t:
        return "Prospectiva"
    return "Otra / por revisar"


ATRIBUCION_ORDEN = [
    "Confirmada / relacionada",
    "Compatible / contextual",
    "Prospectiva",
    "No confirmada / descartada",
    "No aplica / sin información",
    "Otra / por revisar",
]

ATRIBUCION_COLORES = {
    "Confirmada / relacionada": "#004B87",
    "Compatible / contextual": "#0072CE",
    "Prospectiva": "#6FB7E9",
    "No confirmada / descartada": "#AAB7C2",
    "No aplica / sin información": "#D8E1E7",
    "Otra / por revisar": "#7B8C99",
}


def sitrep_etiqueta(fila):
    numero = int(fila["sitrep_numero"]) if pd.notna(fila["sitrep_numero"]) else "—"
    fecha = fila["fecha_corte"].strftime("%d/%m/%Y") if pd.notna(fila["fecha_corte"]) else "sin fecha"
    return f"SitRep {numero:02d} · {fecha}" if isinstance(numero, int) else f"SitRep {numero} · {fecha}"


def section_header(titulo, subtitulo=None):
    sub = f'<div class="section-subtitle">{html.escape(subtitulo)}</div>' if subtitulo else ""
    st.markdown(
        f'<div class="section-head"><div class="section-title">{html.escape(titulo)}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def logo_data_uri():
    if not RUTA_LOGO.exists():
        return None
    encoded = base64.b64encode(RUTA_LOGO.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@st.cache_data(show_spinner=False)
def amenaza_icon_data_uri(nombre, size=64):
    """Devuelve el pictograma SitRep completo, circular y con margen transparente."""
    clave = AMENAZAS[nombre][1]
    dpi = 100
    canvas_px = 112
    draw_size = 64

    fig = plt.figure(figsize=(canvas_px / dpi, canvas_px / dpi), dpi=dpi)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_artist(
        mapa_ref.AnnotationBbox(
            mapa_ref.ICONOS[clave](draw_size),
            (.5, .5),
            xycoords=ax.transAxes,
            frameon=False,
            box_alignment=(.5, .5),
            annotation_clip=False,
        )
    )

    buf = BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        transparent=True,
        facecolor="none",
        edgecolor="none",
        pad_inches=0,
    )
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def amenaza_icon_html(nombre, size=20):
    return f'<img class="threat-icon" src="{amenaza_icon_data_uri(nombre)}" width="{size}" height="{size}" alt="">'


# ============================================================
# GRÁFICOS
# ============================================================
def amenazas_de_fila(fila, seleccion=None):
    if seleccion is None:
        seleccion = list(AMENAZAS.keys())
    salida = []
    for nombre in seleccion:
        col, icono = AMENAZAS[nombre]
        if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
            salida.append((nombre, icono))
    return salida


def resumen_iconos_pais(fila, seleccion=None, max_iconos=2):
    activas = amenazas_de_fila(fila, seleccion)
    if not activas:
        return None, []

    nombres = [nombre for nombre, _ in activas]
    etiqueta = " · ".join(AMENAZAS_CORTAS[n] for n in nombres[:max_iconos])
    extra = len(nombres) - max_iconos
    if extra > 0:
        etiqueta += f" +{extra}"

    return etiqueta, nombres


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
):
    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    cols = ["iso3", "pais", "prioridad", "situacion_predominante", "impacto_salud_documentado"]
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
            f"{AMENAZAS_CORTAS[nombre]}"
            for nombre, icono in amenazas_de_fila(r)
        ) or "Sin amenazas / impactos priorizados",
        axis=1,
    )
    geojson = json.loads(mapa.to_json())

    fig = px.choropleth(
        mapa,
        geojson=geojson,
        locations="ISO_CC",
        featureidkey="properties.ISO_CC",
        color="prioridad_mapa",
        hover_name="nombre_mapa",
        hover_data={
            "ISO_CC": False,
            "prioridad_mapa": True,
            "amenazas_mapa": True,
            "situacion_mapa": True,
        },
        labels={
            "prioridad_mapa": "Prioridad",
            "amenazas_mapa": "Amenazas / impactos",
            "situacion_mapa": "Situación",
        },
        color_discrete_map=COLORES_PRIORIDAD,
        category_orders={"prioridad_mapa": ORDEN_PRIORIDAD + ["Fuera del filtro"]},
    )

    if mostrar_amenazas:
        if amenazas_visibles is None:
            amenazas_visibles = list(AMENAZAS.keys())

        posiciones = posiciones_pais(geo)
        line_lon, line_lat = [], []
        anchor_lon, anchor_lat = [], []
        label_lon, label_lat, label_text, label_hover = [], [], [], []

        for _, fila in datos_filtrados.iterrows():
            iso = str(fila.get("iso3", ""))
            if iso not in posiciones or iso not in POSICIONES_CALLOUTS:
                continue

            activas = amenazas_de_fila(fila, amenazas_visibles)
            if not activas:
                continue

            lon0, lat0 = posiciones[iso]
            lon1, lat1 = POSICIONES_CALLOUTS[iso]
            pais = texto(fila.get("pais"), iso)
            iconos = " · ".join(AMENAZAS_CORTAS[nombre] for nombre, _ in activas)
            detalle = "<br>".join(
                f"{html.escape(nombre)}" for nombre, _ in activas
            )

            # Segmentos independientes separados por None.
            line_lon.extend([lon0, lon1, None])
            line_lat.extend([lat0, lat1, None])
            anchor_lon.append(lon0)
            anchor_lat.append(lat0)
            label_lon.append(lon1)
            label_lat.append(lat1)
            label_text.append(f"<b>{html.escape(pais)}</b><br>{iconos}")
            label_hover.append(f"<b>{html.escape(pais)}</b><br>{detalle}")

        if label_lon:
            fig.add_trace(
                go.Scattergeo(
                    lon=line_lon,
                    lat=line_lat,
                    mode="lines",
                    line=dict(color="rgba(0,75,135,.72)", width=1.15),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scattergeo(
                    lon=anchor_lon,
                    lat=anchor_lat,
                    mode="markers",
                    marker=dict(size=5, color=AZUL_OPS),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scattergeo(
                    lon=label_lon,
                    lat=label_lat,
                    mode="text",
                    text=label_text,
                    textposition="middle center",
                    textfont=dict(size=11, color=AZUL_OPS),
                    hovertext=label_hover,
                    hovertemplate="%{hovertext}<extra></extra>",
                    hoverlabel=dict(bgcolor="white", font_size=12, font_color=TEXTO),
                    showlegend=False,
                )
            )

    fig.update_geos(
        projection_type="equirectangular",
        lonaxis_range=[-121.5, -31],
        lataxis_range=[-58, 37.5],
        showcoastlines=False,
        showcountries=True,
        countrycolor="white",
        countrywidth=0.65,
        showland=False,
        showocean=True,
        oceancolor=AZUL_MAR,
        bgcolor=AZUL_MAR,
        visible=False,
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.7, selector=dict(type="choropleth"))
    fig.update_layout(
        height=590,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=AZUL_MAR,
        plot_bgcolor=AZUL_MAR,
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13, font_color=TEXTO),
    )
    return fig



def construir_mapa_callouts_estatico(
    geo,
    contexto,
    datos_filtrados,
    hay_filtros=False,
    amenazas_visibles=None,
):
    """Mapa del dashboard con la misma simbología vectorial del SitRep PDF/PNG."""
    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    info = contexto[["iso3", "prioridad"]].drop_duplicates("iso3")
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")

    mapa["prioridad_mapa"] = mapa["prioridad"].fillna("Sin priorización")
    if hay_filtros:
        seleccionados = set(datos_filtrados["iso3"].dropna().astype(str))
        mask_fuera = mapa["iso3"].notna() & ~mapa["ISO_CC"].isin(seleccionados)
        mapa.loc[mask_fuera, "prioridad_mapa"] = "Fuera del filtro"

    fig, ax = plt.subplots(figsize=(8.7, 9.15), facecolor=AZUL_MAR)
    ax.set_facecolor(AZUL_MAR)
    ax.set_xlim(-121.5, -31)
    ax.set_ylim(-58, 37.5)
    ax.set_aspect("equal", adjustable="box")

    # Base regional, incluida Guayana Francesa cuando está en el GeoPackage.
    mapa.plot(ax=ax, color=COLORES_PRIORIDAD["Sin priorización"], edgecolor="white", linewidth=.46, zorder=1)
    for prioridad, color in COLORES_PRIORIDAD.items():
        sub = mapa[mapa["prioridad_mapa"] == prioridad]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="white", linewidth=.82, zorder=3)

    amenazas_visibles = amenazas_visibles if amenazas_visibles is not None else list(AMENAZAS.keys())

    # Se usan exactamente LABELS, ROUTES, TARGET y poner_iconos del mapa PDF/PNG.
    for _, fila in datos_filtrados.iterrows():
        iso = str(fila.get("iso3", "")).upper().strip()
        if iso not in mapa_ref.LABELS or iso not in mapa_ref.ROUTES:
            continue

        claves = []
        for nombre in amenazas_visibles:
            col, _ = AMENAZAS[nombre]
            if col in fila.index and pd.notna(fila[col]) and int(fila[col]) == 1:
                claves.append(AMENAZA_CLAVE_ESTATICA[nombre])
        if not claves:
            continue

        x, y, nombre_pais = mapa_ref.LABELS[iso]
        ax.text(
            x, y, nombre_pais,
            fontsize=9.0, fontweight="bold", color=mapa_ref.TEXTO,
            ha="left", va="center", zorder=30,
        )
        mapa_ref.poner_iconos(
            ax,
            x + .15 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0),
            y + mapa_ref.DESPLAZAMIENTO_ICONOS_Y,
            claves,
            size=mapa_ref.TAMANOS_ICONOS.get(iso, 26),
        )
        ruta = mapa_ref.ROUTES[iso]
        ax.plot(
            [pt[0] for pt in ruta], [pt[1] for pt in ruta],
            color=mapa_ref.AZUL_LINEA, linewidth=.72,
            solid_capstyle="round", solid_joinstyle="round", zorder=10,
        )
        tx, ty = mapa_ref.TARGET[iso]
        ax.scatter([tx], [ty], s=11, color=mapa_ref.AZUL_LINEA, zorder=11)

    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return fig

def grafico_subregion(datos, altura=560):
    if datos.empty:
        return go.Figure()
    t = (
        datos.groupby(["subregion", "prioridad"], dropna=False)
        .size()
        .reset_index(name="Países")
    )
    orden_sub = (
        datos.groupby("subregion", dropna=False).size().sort_values(ascending=True).index.tolist()
    )
    fig = px.bar(
        t,
        y="subregion",
        x="Países",
        color="prioridad",
        orientation="h",
        color_discrete_map=COLORES_PRIORIDAD,
        category_orders={"prioridad": ORDEN_PRIORIDAD, "subregion": orden_sub},
        barmode="stack",
    )
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=8, t=8, b=72),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="",
        xaxis_title="Países/territorios",
        yaxis_title=None,
        bargap=.38,
        legend=dict(orientation="h", yanchor="top", y=-.20, xanchor="center", x=.5, font=dict(size=10)),
    )
    fig.update_xaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero", zeroline=False, title_standoff=6)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig


def matriz_amenazas(datos, altura=560):
    if datos.empty:
        return go.Figure()

    columnas = [v[0] for v in AMENAZAS.values()]
    nombres = list(AMENAZAS.keys())
    etiquetas = [("Inseguridad<br>alimentaria" if n == "Inseguridad alimentaria" else "Afectación<br>servicios" if n == "Afectación de servicios de salud" else AMENAZAS_CORTAS[n]) for n in nombres]
    m = datos.set_index("pais")[columnas].copy()
    m = m.loc[m.sum(axis=1).sort_values(ascending=False).index]

    hover_text = []
    for pais, valores in m.iterrows():
        fila_hover = []
        for i, valor in enumerate(valores):
            estado = "Reportado" if int(valor) == 1 else "No priorizado"
            fila_hover.append(f"<b>{html.escape(str(pais))}</b><br>{html.escape(nombres[i])}<br>{estado}")
        hover_text.append(fila_hover)

    fig = go.Figure(
        data=go.Heatmap(
            z=m.values,
            x=etiquetas,
            y=m.index,
            zmin=0,
            zmax=1,
            colorscale=[[0, "#F1F5F7"], [0.499, "#F1F5F7"], [0.5, AZUL_SEC], [1, AZUL_SEC]],
            showscale=False,
            xgap=4,
            ygap=3,
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=4, t=8, b=104),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(side="bottom", showticklabels=False, ticks="", showgrid=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), showgrid=False)
    for i, nombre in enumerate(nombres):
        fig.add_layout_image(dict(
            source=amenaza_icon_data_uri(nombre),
            xref="paper", yref="paper",
            x=(i + .5) / len(nombres), y=-.050,
            sizex=.072, sizey=.072,
            xanchor="center", yanchor="middle", layer="above"
        ))
        etiqueta = etiquetas[i]
        fig.add_annotation(
            x=(i + .5) / len(nombres),
            y=-.122,
            xref="paper", yref="paper",
            text=etiqueta,
            showarrow=False,
            xanchor="center", yanchor="top",
            align="center",
            font=dict(size=10, color="#6F7589"),
        )
    return fig


def lista_paises_estado_html(datos, tipo):
    """Lista visible de países para acompañar los gráficos binarios."""
    if datos.empty:
        return '<div class="country-breakdown"></div>'

    if tipo == "declaratoria":
        serie = datos["declaratoria_activa"].apply(es_activo)
        orden = ["Activa", "No activa"]
        etiquetas = serie.map({True: "Activa", False: "No activa"})
        colores = {"Activa": AZUL_OPS, "No activa": "#B8C5CF"}
    elif tipo == "impacto":
        serie = datos["impacto_salud_documentado"].apply(es_impacto)
        orden = ["Documentado", "No documentado"]
        etiquetas = serie.map({True: "Documentado", False: "No documentado"})
        colores = {"Documentado": AZUL_SEC, "No documentado": "#B8C5CF"}
    else:
        raise ValueError(f"Tipo no reconocido: {tipo}")

    tmp = datos[["pais"]].copy()
    tmp["Estado"] = etiquetas.values
    filas = []
    for estado in orden:
        nombres = (
            tmp.loc[tmp["Estado"] == estado, "pais"]
            .dropna()
            .astype(str)
            .sort_values()
            .tolist()
        )
        nombres_txt = " · ".join(html.escape(x) for x in nombres) if nombres else "Ninguno"
        filas.append(
            f'<div class="country-breakdown-row">'
            f'<div class="country-breakdown-head">'
            f'<span class="country-breakdown-label">'
            f'<span class="country-breakdown-dot" style="background:{colores[estado]}"></span>'
            f'{html.escape(estado)}</span>'
            f'<span class="country-breakdown-count">{len(nombres)}</span>'
            f'</div>'
            f'<div class="country-breakdown-names">{nombres_txt}</div>'
            f'</div>'
        )
    return '<div class="country-breakdown">' + "".join(filas) + '</div>'


def lista_paises_atribucion_html(datos):
    """Lista visible de países por categoría de atribución a El Niño."""
    if datos.empty:
        return '<div class="country-breakdown"></div>'

    tmp = datos[["pais", "atribucion_elnino"]].copy()
    tmp["Atribución"] = tmp["atribucion_elnino"].apply(clasificar_atribucion)
    filas = []
    for categoria in ATRIBUCION_ORDEN:
        nombres = (
            tmp.loc[tmp["Atribución"] == categoria, "pais"]
            .dropna()
            .astype(str)
            .sort_values()
            .tolist()
        )
        if not nombres:
            continue
        nombres_txt = " · ".join(html.escape(x) for x in nombres)
        filas.append(
            f'<div class="country-breakdown-row">'
            f'<div class="country-breakdown-head">'
            f'<span class="country-breakdown-label">'
            f'<span class="country-breakdown-dot" style="background:{ATRIBUCION_COLORES[categoria]}"></span>'
            f'{html.escape(categoria)}</span>'
            f'<span class="country-breakdown-count">{len(nombres)}</span>'
            f'</div>'
            f'<div class="country-breakdown-names">{nombres_txt}</div>'
            f'</div>'
        )
    return '<div class="country-breakdown">' + "".join(filas) + '</div>'


def grafico_estado_binario(datos, tipo, altura=300):
    """Resumen de países por declaratoria o impacto, con nombres en el hover."""
    if datos.empty:
        return go.Figure()

    if tipo == "declaratoria":
        serie = datos["declaratoria_activa"].apply(es_activo)
        orden = ["Activa", "No activa"]
        etiquetas = serie.map({True: "Activa", False: "No activa"})
        colores = {"Activa": AZUL_OPS, "No activa": "#D8E1E7"}
    elif tipo == "impacto":
        serie = datos["impacto_salud_documentado"].apply(es_impacto)
        orden = ["Documentado", "No documentado"]
        etiquetas = serie.map({True: "Documentado", False: "No documentado"})
        colores = {"Documentado": AZUL_SEC, "No documentado": "#D8E1E7"}
    else:
        raise ValueError(f"Tipo no reconocido: {tipo}")

    tmp = datos[["pais"]].copy()
    tmp["Estado"] = etiquetas.values

    fig = go.Figure()
    for estado in orden:
        sub = tmp[tmp["Estado"] == estado]
        nombres = sub["pais"].dropna().astype(str).sort_values().tolist()
        cantidad = len(nombres)
        fig.add_trace(
            go.Bar(
                x=[cantidad],
                y=[estado],
                orientation="h",
                marker_color=colores[estado],
                text=[cantidad],
                textposition="outside" if cantidad == 0 else "inside",
                textfont=dict(color="white" if cantidad > 0 else TEXTO, size=12),
                customdata=["<br>".join(nombres) if nombres else "Ninguno"],
                hovertemplate=(
                    f"<b>{estado}</b><br>%{{x}} países/territorios<br>"
                    "%{customdata}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    max_n = max(1, len(datos))
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=20, t=8, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        barmode="group",
        xaxis_title="Países/territorios",
        yaxis_title=None,
        bargap=.42,
    )
    paso = max(1, int(np.ceil(max_n / 8)))
    fig.update_xaxes(
        gridcolor="#EAF0F4",
        dtick=paso,
        range=[0, max_n + max(1, max_n * .12)],
        zeroline=False,
        tickangle=0,
    )
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=orden[::-1],
        showgrid=False,
        tickfont=dict(size=11),
    )
    return fig


def grafico_atribucion_elnino(datos, altura=300):
    """Distribución de la atribución a El Niño; el hover lista los países."""
    if datos.empty:
        return go.Figure()

    tmp = datos[["pais", "atribucion_elnino"]].copy()
    tmp["Atribución"] = tmp["atribucion_elnino"].apply(clasificar_atribucion)

    registros = []
    for categoria in ATRIBUCION_ORDEN:
        sub = tmp[tmp["Atribución"] == categoria]
        if sub.empty:
            continue
        nombres = sub["pais"].dropna().astype(str).sort_values().tolist()
        registros.append({
            "Atribución": categoria,
            "Países": len(nombres),
            "Países_lista": "<br>".join(nombres),
        })

    t = pd.DataFrame(registros)
    if t.empty:
        return go.Figure()

    fig = go.Figure(
        go.Bar(
            x=t["Países"],
            y=t["Atribución"],
            orientation="h",
            marker_color=[ATRIBUCION_COLORES[x] for x in t["Atribución"]],
            text=t["Países"],
            textposition="inside",
            textfont=dict(color="white", size=12),
            customdata=t["Países_lista"],
            hovertemplate="<b>%{y}</b><br>%{x} países/territorios<br>%{customdata}<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=20, t=8, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title="Países/territorios",
        yaxis_title=None,
        bargap=.34,
    )
    fig.update_xaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero", zeroline=False)
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=[x for x in ATRIBUCION_ORDEN[::-1] if x in set(t["Atribución"])],
        showgrid=False,
        tickfont=dict(size=10),
    )
    return fig


def evolucion_prioridad(base):
    t = (
        base.groupby(["sitrep_numero", "fecha_corte", "prioridad"])
        .size()
        .reset_index(name="Países")
        .sort_values(["sitrep_numero", "prioridad"])
    )
    t["Corte"] = t.apply(
        lambda r: f"S{int(r['sitrep_numero']):02d}<br>{r['fecha_corte'].strftime('%d/%m/%Y') if pd.notna(r['fecha_corte']) else ''}",
        axis=1,
    )
    fig = px.line(
        t,
        x="Corte",
        y="Países",
        color="prioridad",
        markers=True,
        color_discrete_map=COLORES_PRIORIDAD,
        category_orders={"prioridad": ORDEN_PRIORIDAD},
    )
    fig.update_layout(
        height=330,
        margin=dict(l=5, r=5, t=8, b=55),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title=None,
        yaxis_title="Países/territorios",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="top", y=-.17, xanchor="left", x=0, font=dict(size=10)),
    )
    fig.update_yaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def heatmap_evolucion(base):
    orden_s = (
        base[["sitrep_numero", "fecha_corte", "sitrep_id"]]
        .drop_duplicates()
        .sort_values(["sitrep_numero", "fecha_corte"])
    )
    etiquetas_s = {r.sitrep_id: f"S{int(r.sitrep_numero):02d}" for r in orden_s.itertuples()}
    cod = {"Sin priorización": 0, "Baja": 1, "Media": 2, "Alta": 3}
    t = base.copy()
    t["sitrep_label"] = t["sitrep_id"].map(etiquetas_s)
    t["prioridad_cod"] = t["prioridad"].map(cod)
    m = t.pivot_table(index="pais", columns="sitrep_label", values="prioridad_cod", aggfunc="first")
    orden_cols = [etiquetas_s[x] for x in orden_s["sitrep_id"] if etiquetas_s[x] in m.columns]
    m = m.reindex(columns=orden_cols)

    escala = [
        [0.00, COLORES_PRIORIDAD["Sin priorización"]], [0.249, COLORES_PRIORIDAD["Sin priorización"]],
        [0.25, COLORES_PRIORIDAD["Baja"]], [0.499, COLORES_PRIORIDAD["Baja"]],
        [0.50, COLORES_PRIORIDAD["Media"]], [0.749, COLORES_PRIORIDAD["Media"]],
        [0.75, COLORES_PRIORIDAD["Alta"]], [1.00, COLORES_PRIORIDAD["Alta"]],
    ]
    inv = {v: k for k, v in cod.items()}
    texto_hover = np.empty(m.shape, dtype=object)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.iloc[i, j]
            texto_hover[i, j] = "Sin dato" if pd.isna(v) else inv.get(int(v), "Sin dato")

    fig = go.Figure(
        data=go.Heatmap(
            z=m.values,
            x=m.columns,
            y=m.index,
            zmin=0,
            zmax=3,
            colorscale=escala,
            showscale=False,
            xgap=3,
            ygap=3,
            customdata=texto_hover,
            hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(350, 25 * len(m) + 80),
        margin=dict(l=0, r=4, t=8, b=35),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    return fig


# ============================================================
# APP
# ============================================================
try:
    base = cargar_base()
    geo = cargar_geografia()
except Exception as exc:
    st.error(f"No fue posible cargar los datos del dashboard: {exc}")
    st.stop()

# SitRep disponibles
sit = (
    base[["sitrep_id", "sitrep_numero", "fecha_corte"]]
    .drop_duplicates()
    .sort_values(["sitrep_numero", "fecha_corte"], ascending=[False, False])
)
labels_sitrep = {r.sitrep_id: sitrep_etiqueta(pd.Series(r._asdict())) for r in sit.itertuples(index=False)}
ids = sit["sitrep_id"].tolist()

# Encabezado institucional
logo_uri = logo_data_uri()
logo_html = f'<img class="ops-logo" src="{logo_uri}" alt="OPS/OMS">' if logo_uri else ""
st.markdown(
    f"""
    <div class="ops-hero">
        <div class="ops-hero-copy">
            <div class="ops-kicker">Monitoreo regional · Actualización mensual</div>
            <div class="ops-title">El Niño y salud pública en las Américas</div>
            <div class="ops-subtitle">Prioridades sanitarias, amenazas, impactos y respuesta de OPS/OMS.</div>
            <div class="ops-area">PAHO Health Emergencies Department (PHE) · Emergency Operations Center (EOC)</div>
        </div>
        <div>{logo_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Filtros
with st.container(border=True):
    st.markdown('<div class="filter-label">Filtros de consulta</div>', unsafe_allow_html=True)
    # Los filtros se agrupan en un formulario para evitar un rerun completo por
    # cada clic. El tablero se recalcula una sola vez al pulsar "Aplicar filtros",
    # lo que hace la navegación mucho más estable en Streamlit Cloud.
    with st.form("form_filtros_consulta", border=False):
        f1, f2, f3, f4 = st.columns([1.15, 1.35, 1.15, 1.85], gap="medium")
        with f1:
            sitrep_id = st.selectbox(
                "SitRep / fecha",
                ids,
                format_func=lambda x: labels_sitrep.get(x, x),
                key="filtro_sitrep",
            )

        actual = base[base["sitrep_id"] == sitrep_id].copy()

        with f2:
            opciones_sub = sorted(actual["subregion"].dropna().astype(str).unique())
            filtro_sub = st.multiselect(
                "Subregión", opciones_sub, placeholder="Todas", key="filtro_subregion"
            )
        with f3:
            opciones_pri = [p for p in ORDEN_PRIORIDAD if p in set(actual["prioridad"].dropna())]
            filtro_pri = st.multiselect(
                "Prioridad", opciones_pri, placeholder="Todas", key="filtro_prioridad"
            )
        with f4:
            filtro_amenaza = st.multiselect(
                "Amenaza / impacto",
                list(AMENAZAS.keys()),
                placeholder="Todas",
                key="filtro_amenaza",
            )

        aplicar_filtros = st.form_submit_button(
            "Aplicar filtros",
            type="primary",
            width="stretch",
        )

filtrado = actual.copy()
if filtro_sub:
    filtrado = filtrado[filtrado["subregion"].isin(filtro_sub)]
if filtro_pri:
    filtrado = filtrado[filtrado["prioridad"].isin(filtro_pri)]
if filtro_amenaza:
    cols = [AMENAZAS[a][0] for a in filtro_amenaza]
    filtrado = filtrado[filtrado[cols].eq(1).any(axis=1)]

hay_filtros = bool(filtro_sub or filtro_pri or filtro_amenaza)

# KPIs
section_header("Panorama del corte", "Indicadores principales para la selección actual")
k1, k2, k3, k4, k5 = st.columns(5, gap="medium")
k1.metric("Países", int(len(filtrado)))
k2.metric("Países en prioridad alta", int((filtrado["prioridad"] == "Alta").sum()))
k3.metric("Países en prioridad media", int((filtrado["prioridad"] == "Media").sum()))
k4.metric("Países con declaratoria activa", int(filtrado["declaratoria_activa"].apply(es_activo).sum()))
k5.metric("Países con impacto en salud documentado", int(filtrado["impacto_salud_documentado"].apply(es_impacto).sum()))

# Mapa y resumen
section_header("Panorama regional", "Distribución de prioridades y amenazas reportadas")

# El mapa usa directamente el filtro general de Amenaza / impacto. Si no hay
# selección, muestra todos los pictogramas; si hay selección, muestra solo los
# correspondientes a ese mismo filtro. Así se evita duplicar controles.
modo_mapa = "Prioridad + amenazas"
amenazas_mapa = filtro_amenaza if filtro_amenaza else list(AMENAZAS.keys())

col_mapa, col_resumen = st.columns([4.15, 1.35], gap="medium")
with col_mapa:
    with st.container(border=True):
        if modo_mapa == "Prioridad + amenazas":
            renderer = getattr(st, "_ops_render_interactive_map", None)
            if renderer is not None:
                # Render directo: evita construir primero una figura Matplotlib
                # pesada que luego era reemplazada por Folium en cada rerun.
                renderer(globals())
            else:
                # Fallback por si app_legacy.py se ejecuta de forma independiente.
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
            fig_mapa = construir_mapa(
                geo,
                actual,
                filtrado,
                hay_filtros,
                mostrar_amenazas=False,
                amenazas_visibles=[],
            )
            st.plotly_chart(fig_mapa, use_container_width=True, config=CHART_CONFIG)
with col_resumen:
    filas_amenazas = []
    for nombre, (col, icono) in AMENAZAS.items():
        n = int(filtrado[col].sum()) if col in filtrado.columns else 0
        filas_amenazas.append(
            f'<div class="legend-row">'
            f'<div class="legend-label">{amenaza_icon_html(nombre, size=22)}<span>{html.escape(nombre)}</span></div>'
            f'<div class="legend-count">{n}</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="legend-card amenazas-card">'
        '<div class="legend-title">Principales amenazas</div>'
        '<div class="legend-body">' + ''.join(filas_amenazas) + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    filas_prioridad = []
    for p in ORDEN_PRIORIDAD:
        n = int((filtrado["prioridad"] == p).sum())
        txt_color = "#5D4B00" if p == "Baja" else COLORES_PRIORIDAD[p]
        filas_prioridad.append(
            f'<div class="legend-row">'
            f'<div class="legend-label"><span class="priority-dot" style="background:{COLORES_PRIORIDAD[p]}"></span><span>{html.escape(p)}</span></div>'
            f'<div class="legend-count" style="color:{txt_color}">{n}</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="legend-card priority-card">'
        '<div class="legend-title">Nivel de prioridad</div>'
        '<div class="legend-body">' + ''.join(filas_prioridad) + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# Situación regional
section_header("Situación regional", "Comparación territorial y perfil de amenazas")
# Los dos gráficos usan exactamente la misma altura para que sus tarjetas
# comiencen y terminen alineadas. La altura se adapta al número de países
# visibles, pero se limita para evitar paneles demasiado altos o bajos.
altura_situacion = max(430, min(520, 20 * max(1, len(filtrado)) + 70))
g1, g2 = st.columns([1.0, 1.45], gap="medium")
with g1:
    with st.container(border=True):
        st.markdown("**Prioridad por subregión**")
        st.plotly_chart(
            grafico_subregion(filtrado, altura=altura_situacion),
            use_container_width=True,
            config=CHART_CONFIG,
        )
with g2:
    with st.container(border=True):
        st.markdown("**País × amenaza / impacto**")
        st.plotly_chart(
            matriz_amenazas(filtrado, altura=altura_situacion),
            use_container_width=True,
            config=CHART_CONFIG,
        )

# Respuesta, impacto y atribución
section_header(
    "Respuesta, impacto y atribución",
    "Países/territorios según declaratoria, impacto sanitario documentado y relación con El Niño",
)
r1, r2, r3 = st.columns([1.0, 1.0, 1.35], gap="medium")
with r1:
    with st.container(border=True):
        st.markdown("**Declaratoria**")
        st.plotly_chart(
            grafico_estado_binario(filtrado, "declaratoria"),
            use_container_width=True,
            config=CHART_CONFIG,
        )
with r2:
    with st.container(border=True):
        st.markdown("**Impacto en salud documentado**")
        st.plotly_chart(
            grafico_estado_binario(filtrado, "impacto"),
            use_container_width=True,
            config=CHART_CONFIG,
        )
with r3:
    with st.container(border=True):
        st.markdown("**Atribución a El Niño**")
        st.plotly_chart(
            grafico_atribucion_elnino(filtrado),
            use_container_width=True,
            config=CHART_CONFIG,
        )

# Detalle visible de países en un único bloque para mantener las tres
# tarjetas de gráficos perfectamente alineadas.
with st.container(border=True):
    st.markdown("**Países / territorios por categoría**")
    d1, d2, d3 = st.columns([1.0, 1.0, 1.35], gap="large")
    with d1:
        st.markdown('<div class="summary-label">Declaratoria</div>', unsafe_allow_html=True)
        st.markdown(
            lista_paises_estado_html(filtrado, "declaratoria"),
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown('<div class="summary-label">Impacto en salud documentado</div>', unsafe_allow_html=True)
        st.markdown(
            lista_paises_estado_html(filtrado, "impacto"),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown('<div class="summary-label">Atribución a El Niño</div>', unsafe_allow_html=True)
        st.markdown(
            lista_paises_atribucion_html(filtrado),
            unsafe_allow_html=True,
        )

# Evolución temporal
section_header("Evolución temporal", "Cambios entre cortes mensuales del SitRep")
if base["sitrep_id"].nunique() < 2:
    st.markdown(
        '<div class="empty-state"><b>Serie temporal aún no disponible.</b> Esta sección se activará automáticamente cuando la base contenga dos o más SitRep.</div>',
        unsafe_allow_html=True,
    )
else:
    e1, e2 = st.columns([1, 1.18], gap="medium")
    with e1:
        with st.container(border=True):
            st.markdown("**Países por nivel de prioridad**")
            st.plotly_chart(evolucion_prioridad(base), use_container_width=True, config=CHART_CONFIG)
    with e2:
        with st.container(border=True):
            st.markdown("**Evolución de prioridad por país**")
            st.plotly_chart(heatmap_evolucion(base), use_container_width=True, config=CHART_CONFIG)

# Detalle país
section_header("Detalle por país / territorio", "Lectura cualitativa y cifras disponibles para el corte seleccionado")
if filtrado.empty:
    st.warning("No hay países/territorios que cumplan los filtros seleccionados.")
else:
    with st.container(border=True):
        selector_col, _ = st.columns([1.25, 2.75])
        with selector_col:
            paises = filtrado.sort_values(["prioridad", "pais"])["pais"].tolist()
            # El filtro puede cambiar completamente la lista de países. Mantener
            # explícitamente un valor válido evita que el widget downstream quede
            # con un estado obsoleto durante el rerun de Streamlit.
            if st.session_state.get("pais_detalle") not in paises:
                st.session_state["pais_detalle"] = paises[0]
            pais_sel = st.selectbox(
                "País / territorio",
                paises,
                key="pais_detalle",
            )

        fila = filtrado[filtrado["pais"] == pais_sel].iloc[0]
        prioridad = texto(fila.get("prioridad"), "Sin priorización")
        color_p = COLORES_PRIORIDAD.get(prioridad, GRIS)
        badge_class = "priority-pill light" if prioridad == "Baja" else "priority-pill"

        st.markdown(
            f"""
            <div class="country-summary">
                <div>
                    <div class="country-name">{html.escape(pais_sel)}</div>
                    <span class="{badge_class}" style="background:{color_p}">{html.escape(prioridad)}</span>
                </div>
                <div>
                    <div class="summary-label">Situación predominante</div>
                    <div class="summary-text">{texto_html(fila.get('situacion_predominante'))}</div>
                </div>
                <div>
                    <div class="summary-label">Atribución a El Niño</div>
                    <div class="summary-text">{texto_html(fila.get('atribucion_elnino'))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        r1a, r1b = st.columns(2, gap="medium")
        r2a, r2b = st.columns(2, gap="medium")
        bloques = [
            (r1a, "Amenazas", fila.get("amenazas_resumen")),
            (r1b, "Impacto en salud", fila.get("impacto_salud_resumen")),
            (r2a, "Alistamiento / respuesta", fila.get("alistamiento_respuesta")),
            (r2b, "Acciones OPS/OMS", fila.get("acciones_ops")),
        ]
        for col, titulo, contenido in bloques:
            with col:
                st.markdown(
                    f'<div class="detail-card"><h4>{html.escape(titulo)}</h4><p>{texto_html(contenido)}</p></div>',
                    unsafe_allow_html=True,
                )

        cifras_disponibles = []
        for col, etiqueta in CIFRAS.items():
            if col in fila.index and pd.notna(fila[col]):
                cifras_disponibles.append((etiqueta, formato_numero(float(fila[col]))))

        if cifras_disponibles:
            st.markdown("<br>**Cifras reportadas en el SitRep**", unsafe_allow_html=True)
            for inicio in range(0, len(cifras_disponibles), 4):
                lote = cifras_disponibles[inicio:inicio + 4]
                columnas = st.columns(len(lote), gap="medium")
                for columna, (etiqueta, valor) in zip(columnas, lote):
                    columna.metric(etiqueta, valor)

        pie = []
        if "declaratoria_activa" in fila.index:
            pie.append(f"Declaratoria: {texto(fila.get('declaratoria_activa'))}")
        if "nivel_declaratoria" in fila.index:
            pie.append(texto(fila.get("nivel_declaratoria"), ""))
        if "fuentes_resumen" in fila.index:
            pie.append(f"Fuentes: {texto(fila.get('fuentes_resumen'))}")
        st.markdown(
            f'<div class="caption-box">{html.escape(" · ".join([x for x in pie if x]))}</div>',
            unsafe_allow_html=True,
        )

st.divider()
st.caption(
    "Fuente: base maestra de monitoreo de El Niño de OPS/OMS. El tablero toma automáticamente el SitRep seleccionado y conserva la serie histórica para análisis temporal."
)
