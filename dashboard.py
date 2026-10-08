from pathlib import Path
from io import BytesIO
import base64
import html

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
TEXTO = "#17324D"
GRIS = "#CACACA"
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
    "Impacto potencial de servicios de salud": ("icono_servicios_potencial", "servicios_potencial"),
}

AMENAZAS_CORTAS = {
    "Sequía / agua": "Sequía",
    "Inundaciones / lluvias": "Inundaciones",
    "Incendios / quemadas": "Incendios",
    "Inseguridad alimentaria": "Inseguridad alimentaria",
    "Dengue / otras arbovirosis": "Arbovirosis",
    "Calidad del aire / riesgo respiratorio": "Aire",
    "Afectación de servicios de salud": "Afectación servicios",
    "Impacto potencial de servicios de salud": "Impacto potencial servicios",
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

        .map-card-marker {{display:none;}}
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

        .status-table-wrap {{
            width:100%;
            max-height:452px;
            overflow:auto;
            overscroll-behavior:contain;
            scrollbar-gutter:stable;
            border:none;
            border-radius:0;
            background:#FFFFFF;
            margin-bottom:.45rem;
        }}
        .status-table {{
            width:100%;
            border-collapse:separate;
            border-spacing:0;
            table-layout:fixed;
            font-size:.82rem;
            color:{TEXTO};
        }}
        .status-table thead th {{
            position:sticky;
            top:0;
            z-index:2;
            height:38px;
            box-sizing:border-box;
            background:#F4F8FB;
            color:#5C7182;
            text-transform:uppercase;
            letter-spacing:.035em;
            font-size:.70rem;
            font-weight:800;
            text-align:left;
            padding:.72rem .78rem;
            border-bottom:1px solid #DCE8EF;
        }}
        .status-table tbody tr {{
            height:46px;
        }}
        .status-table tbody td {{
            height:46px;
            box-sizing:border-box;
            padding:.48rem .78rem;
            border-bottom:1px solid #EDF2F5;
            vertical-align:middle;
        }}
        .status-table tbody tr:last-child td {{border-bottom:1px solid #DCE8EF;}}
        .status-table tbody tr:hover td {{background:#FAFCFD;}}
        .status-region-row td {{
            height:34px !important;
            padding:.42rem .78rem !important;
            background:#EDF5FA !important;
            color:{AZUL_OPS};
            font-size:.72rem;
            font-weight:800;
            text-transform:uppercase;
            letter-spacing:.045em;
            border-top:1px solid #D7E7F0;
            border-bottom:1px solid #D7E7F0 !important;
        }}
        .status-region-row:first-child td {{border-top:none;}}
        .status-region-count {{
            color:#6F8596;
            font-weight:700;
            text-transform:none;
            letter-spacing:0;
            margin-left:.45rem;
        }}
        .status-country-name {{
            color:{TEXTO};
            font-weight:800;
            line-height:1.2;
            white-space:nowrap;
        }}
        .status-country-sub {{
            color:#7B8D9B;
            font-size:.72rem;
            margin-top:.16rem;
            line-height:1.2;
            white-space:nowrap;
        }}
        .status-pill {{
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-height:25px;
            padding:.22rem .58rem;
            border-radius:999px;
            font-size:.73rem;
            font-weight:800;
            line-height:1.15;
            white-space:nowrap;
            text-align:center;
        }}
        .status-table-note {{
            color:#728596;
            font-size:.76rem;
            margin:.15rem 0 .58rem 0;
        }}
        .subregion-legend {{
            display:flex;
            flex-wrap:wrap;
            align-items:center;
            gap:.42rem 1rem;
            margin:-.1rem 0 .7rem 0;
            color:#60788A;
            font-size:.76rem;
        }}
        .subregion-legend-item {{
            display:inline-flex;
            align-items:center;
            gap:.38rem;
            white-space:nowrap;
        }}
        .subregion-legend-dot {{
            width:9px;
            height:9px;
            border-radius:50%;
            display:inline-block;
            flex:0 0 9px;
        }}
        @media (max-width: 900px) {{
            .status-table {{min-width:760px;}}
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

SUBREGION_ORDEN = [
    "América del Norte",
    "América Central",
    "Caribe",
    "Subregión Andina",
    "Brasil y Cono Sur",
]

SUBREGION_COLORES = {
    # Paleta OPS usada en los productos del SitRep: azul institucional,
    # azules secundarios y colores de apoyo ya presentes en la simbología.
    "América del Norte": "#004B87",
    "América Central": "#168BC9",
    "Caribe": "#008877",
    "Subregión Andina": "#7851A9",
    "Brasil y Cono Sur": "#F36C21",
    "Sin subregión": "#AAB7C2",
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
        xaxis_title="Países",
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
    etiquetas = [
        (
            "Inseguridad<br>alimentaria" if n == "Inseguridad alimentaria"
            else "Afectación<br>servicios" if n == "Afectación de servicios de salud"
            else "Impacto potencial<br>servicios" if n == "Impacto potencial de servicios de salud"
            else AMENAZAS_CORTAS[n]
        )
        for n in nombres
    ]
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


def tabla_respuesta_pais_html(datos):
    """Matriz por país de declaratoria, impacto en salud y atribución a El Niño."""
    if datos.empty:
        return '<div class="empty-state">No hay países para la selección actual.</div>'

    tmp = datos[
        ["pais", "subregion", "declaratoria_activa", "impacto_salud_documentado", "atribucion_elnino"]
    ].copy()
    tmp["Declaratoria"] = tmp["declaratoria_activa"].apply(
        lambda x: "Activa" if es_activo(x) else "No activa"
    )
    tmp["Impacto"] = tmp["impacto_salud_documentado"].apply(
        lambda x: "Documentado" if es_impacto(x) else "No documentado"
    )
    tmp["Atribución"] = tmp["atribucion_elnino"].apply(clasificar_atribucion)

    tmp["subregion"] = tmp["subregion"].fillna("Sin subregión")
    tmp["_suborden"] = pd.Categorical(
        tmp["subregion"],
        categories=SUBREGION_ORDEN + ["Sin subregión"],
        ordered=True,
    )
    tmp = tmp.sort_values(
        ["_suborden", "pais"],
        key=lambda s: s.astype(str).str.lower() if s.name == "pais" else s,
    )

    def pill(etiqueta, fondo, color):
        return (
            f'<span class="status-pill" '
            f'style="background:{fondo};color:{color};">{html.escape(etiqueta)}</span>'
        )

    filas = []
    for subregion, grupo in tmp.groupby("subregion", sort=False, observed=True):
        if grupo.empty:
            continue

        n_paises = len(grupo)
        filas.append(
            '<tr class="status-region-row">'
            f'<td colspan="4">{html.escape(str(subregion))}'
            f'<span class="status-region-count">· {n_paises} {"país" if n_paises == 1 else "países"}</span>'
            '</td></tr>'
        )

        for _, fila in grupo.iterrows():
            declaratoria = str(fila["Declaratoria"])
            impacto = str(fila["Impacto"])
            atribucion = str(fila["Atribución"])

            declaratoria_html = (
                pill(declaratoria, AZUL_OPS, "#FFFFFF")
                if declaratoria == "Activa"
                else pill(declaratoria, "#EDF2F5", "#60788A")
            )
            impacto_html = (
                pill(impacto, AZUL_SEC, "#FFFFFF")
                if impacto == "Documentado"
                else pill(impacto, "#EDF2F5", "#60788A")
            )

            color_atrib = ATRIBUCION_COLORES.get(atribucion, "#7B8C99")
            texto_atrib = (
                "#FFFFFF"
                if atribucion in {"Confirmada / relacionada", "Compatible / contextual", "Otra / por revisar"}
                else TEXTO
            )
            atribucion_html = pill(atribucion, color_atrib, texto_atrib)

            filas.append(
                "<tr>"
                f'<td><div class="status-country-name">{html.escape(texto(fila["pais"], "—"))}</div></td>'
                f"<td>{declaratoria_html}</td>"
                f"<td>{impacto_html}</td>"
                f"<td>{atribucion_html}</td>"
                "</tr>"
            )

    return (
        '<div class="status-table-wrap">'
        '<table class="status-table">'
        '<colgroup><col style="width:29%"><col style="width:19%"><col style="width:22%"><col style="width:30%"></colgroup>'
        "<thead><tr>"
        "<th>País</th>"
        "<th>Declaratoria</th>"
        "<th>Impacto en salud</th>"
        "<th>Atribución a El Niño</th>"
        "</tr></thead>"
        "<tbody>" + "".join(filas) + "</tbody>"
        "</table></div>"
    )


def leyenda_subregiones_html(datos):
    """Leyenda compartida de colores por subregión para los gráficos analíticos."""
    if datos.empty:
        return ""
    presentes = set(datos["subregion"].fillna("Sin subregión").astype(str))
    orden = [x for x in SUBREGION_ORDEN + ["Sin subregión"] if x in presentes]
    items = []
    for subregion in orden:
        items.append(
            f'<span class="subregion-legend-item">'
            f'<span class="subregion-legend-dot" style="background:{SUBREGION_COLORES[subregion]}"></span>'
            f'{html.escape(subregion)}</span>'
        )
    return '<div class="subregion-legend">' + "".join(items) + '</div>'


def grafico_estado_binario(datos, tipo, altura=300):
    """Resumen por estado, dividido por subregión; el hover lista los países."""
    if datos.empty:
        return go.Figure()

    if tipo == "declaratoria":
        serie = datos["declaratoria_activa"].apply(es_activo)
        orden = ["Activa", "No activa"]
        etiquetas = serie.map({True: "Activa", False: "No activa"})
    elif tipo == "impacto":
        serie = datos["impacto_salud_documentado"].apply(es_impacto)
        orden = ["Documentado", "No documentado"]
        etiquetas = serie.map({True: "Documentado", False: "No documentado"})
    else:
        raise ValueError(f"Tipo no reconocido: {tipo}")

    tmp = datos[["pais", "subregion"]].copy()
    tmp["subregion"] = tmp["subregion"].fillna("Sin subregión")
    tmp["Estado"] = etiquetas.values

    presentes = set(tmp["subregion"].astype(str))
    orden_sub = [x for x in SUBREGION_ORDEN + ["Sin subregión"] if x in presentes]

    fig = go.Figure()
    for subregion in orden_sub:
        x_vals = []
        hover_vals = []
        for estado in orden:
            sub = tmp[(tmp["Estado"] == estado) & (tmp["subregion"] == subregion)]
            nombres = sub["pais"].dropna().astype(str).sort_values().tolist()
            x_vals.append(len(nombres))
            hover_vals.append("<br>".join(nombres) if nombres else "Ninguno")

        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=orden,
                orientation="h",
                name=subregion,
                marker_color=SUBREGION_COLORES[subregion],
                text=[str(v) if v > 0 else "" for v in x_vals],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=11),
                customdata=hover_vals,
                hovertemplate=(
                    f"<b>{html.escape(subregion)}</b><br>"
                    "%{y}: %{x} países<br>%{customdata}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    totales_estado = tmp.groupby("Estado", dropna=False).size().reindex(orden, fill_value=0)
    max_n = max(1, int(totales_estado.max()))

    for estado, total in totales_estado.items():
        fig.add_annotation(
            x=float(total) + max(.28, max_n * .025),
            y=estado,
            text=f"<b>{int(total)}</b>",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=12, color=AZUL_OPS),
        )

    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=28, t=8, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        barmode="stack",
        xaxis_title="Países",
        yaxis_title=None,
        bargap=.42,
    )
    paso = max(1, int(np.ceil(max_n / 8)))
    fig.update_xaxes(
        gridcolor="#EAF0F4",
        dtick=paso,
        range=[0, max_n + max(1.35, max_n * .16)],
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
    """Atribución a El Niño dividida por subregión; el hover lista los países."""
    if datos.empty:
        return go.Figure()

    tmp = datos[["pais", "subregion", "atribucion_elnino"]].copy()
    tmp["subregion"] = tmp["subregion"].fillna("Sin subregión")
    tmp["Atribución"] = tmp["atribucion_elnino"].apply(clasificar_atribucion)

    categorias = [
        x for x in ATRIBUCION_ORDEN
        if x in set(tmp["Atribución"])
    ]
    presentes = set(tmp["subregion"].astype(str))
    orden_sub = [x for x in SUBREGION_ORDEN + ["Sin subregión"] if x in presentes]

    fig = go.Figure()
    for subregion in orden_sub:
        x_vals = []
        hover_vals = []
        for categoria in categorias:
            sub = tmp[
                (tmp["Atribución"] == categoria)
                & (tmp["subregion"] == subregion)
            ]
            nombres = sub["pais"].dropna().astype(str).sort_values().tolist()
            x_vals.append(len(nombres))
            hover_vals.append("<br>".join(nombres) if nombres else "Ninguno")

        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=categorias,
                orientation="h",
                name=subregion,
                marker_color=SUBREGION_COLORES[subregion],
                text=[str(v) if v > 0 else "" for v in x_vals],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=11),
                customdata=hover_vals,
                hovertemplate=(
                    f"<b>{html.escape(subregion)}</b><br>"
                    "%{y}: %{x} países<br>%{customdata}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    totales_atribucion = tmp.groupby("Atribución", dropna=False).size().reindex(categorias, fill_value=0)
    max_categoria = max(1, int(totales_atribucion.max()))

    for categoria, total in totales_atribucion.items():
        fig.add_annotation(
            x=float(total) + max(.22, max_categoria * .02),
            y=categoria,
            text=f"<b>{int(total)}</b>",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=12, color=AZUL_OPS),
        )

    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=28, t=8, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        barmode="stack",
        xaxis_title="Países",
        yaxis_title=None,
        bargap=.34,
    )
    fig.update_xaxes(
        gridcolor="#EAF0F4",
        dtick=1,
        range=[0, max_categoria + max(1.15, max_categoria * .14)],
        zeroline=False,
    )
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=categorias[::-1],
        showgrid=False,
        tickfont=dict(size=10),
    )
    return fig


def evolucion_prioridad(base, altura=330):
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
        height=altura,
        margin=dict(l=5, r=5, t=8, b=55),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title=None,
        yaxis_title="Países",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="top", y=-.17, xanchor="left", x=0, font=dict(size=10)),
    )
    fig.update_yaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def heatmap_evolucion(base, altura=None):
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
    if altura is None:
        altura = max(350, 25 * len(m) + 80)

    fig.update_layout(
        height=altura,
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

# El mapa usa el filtro general de Amenaza / impacto; si no hay selección,
# muestra todos los pictogramas.
amenazas_mapa = filtro_amenaza if filtro_amenaza else list(AMENAZAS.keys())

col_mapa, col_resumen = st.columns([4.15, 1.35], gap="medium")
with col_mapa:
    with st.container(border=True):
        st.markdown('<span class="map-card-marker"></span>', unsafe_allow_html=True)
        renderer = getattr(st, "_ops_render_interactive_map", None)
        if renderer is None:
            st.error("No fue posible inicializar el mapa interactivo.")
        else:
            renderer(globals())
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
        '<div class="map-side-panel">'
        '<div class="legend-card amenazas-card">'
        '<div class="legend-title">Principales amenazas</div>'
        '<div class="legend-body">' + ''.join(filas_amenazas) + '</div>'
        '</div>'
        '<div class="legend-card priority-card">'
        '<div class="legend-title">Nivel de prioridad</div>'
        '<div class="legend-body">' + ''.join(filas_prioridad) + '</div>'
        '</div>'
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
    "Países según declaratoria, impacto sanitario documentado y relación con El Niño, desagregados por subregión",
)
st.markdown(
    leyenda_subregiones_html(filtrado),
    unsafe_allow_html=True,
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

# Matriz integrada por país: permite identificar rápidamente qué países
# explican las barras superiores sin repetir tres listas independientes.
with st.container(border=True):
    st.markdown("**Matriz por país**")
    st.markdown(
        '<div class="status-table-note">Lectura integrada de declaratoria, impacto en salud documentado '
        'y atribución a El Niño, agrupada por subregión.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        tabla_respuesta_pais_html(filtrado),
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
    # Ambos gráficos usan exactamente la misma altura para que las tarjetas
    # queden alineadas. La altura se adapta al número de países del heatmap.
    n_paises_evolucion = max(1, int(base["pais"].nunique()))
    altura_evolucion = max(350, min(620, 25 * n_paises_evolucion + 80))

    e1, e2 = st.columns([1, 1.18], gap="medium")
    with e1:
        with st.container(border=True):
            st.markdown("**Países por nivel de prioridad**")
            st.plotly_chart(
                evolucion_prioridad(base, altura=altura_evolucion),
                use_container_width=True,
                config=CHART_CONFIG,
            )
    with e2:
        with st.container(border=True):
            st.markdown("**Evolución de prioridad por país**")
            st.plotly_chart(
                heatmap_evolucion(base, altura=altura_evolucion),
                use_container_width=True,
                config=CHART_CONFIG,
            )

# Detalle país
section_header("Detalle por país", "Lectura cualitativa y cifras disponibles para el corte seleccionado")
if filtrado.empty:
    st.warning("No hay países que cumplan los filtros seleccionados.")
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
                "País",
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
