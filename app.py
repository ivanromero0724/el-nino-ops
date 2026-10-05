from pathlib import Path
import base64
import html
import json

import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


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
    "Sequía / agua": ("icono_agua", "💧"),
    "Inundaciones / lluvias": ("icono_inundaciones", "🌧️"),
    "Incendios / quemadas": ("icono_incendios", "🔥"),
    "Inseguridad alimentaria": ("icono_alimentos", "🌾"),
    "Dengue / otras arbovirosis": ("icono_arbovirosis", "🦟"),
    "Calidad del aire / riesgo respiratorio": ("icono_respiratorio", "🫁"),
    "Afectación de servicios de salud": ("icono_servicios", "✚"),
}

AMENAZAS_CORTAS = {
    "Sequía / agua": "Agua",
    "Inundaciones / lluvias": "Lluvias",
    "Incendios / quemadas": "Incendios",
    "Inseguridad alimentaria": "Alimentos",
    "Dengue / otras arbovirosis": "Arbovirosis",
    "Calidad del aire / riesgo respiratorio": "Aire",
    "Afectación de servicios de salud": "Servicios",
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
    page_icon="🌎",
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
            f"{icono} {AMENAZAS_CORTAS[nombre]}"
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
        margin=dict(l=0, r=8, t=8, b=70),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="",
        xaxis_title="Países/territorios",
        yaxis_title=None,
        bargap=.38,
        legend=dict(orientation="h", yanchor="top", y=-.17, xanchor="left", x=0, font=dict(size=10)),
    )
    fig.update_xaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero", zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig


def matriz_amenazas(datos, altura=560):
    if datos.empty:
        return go.Figure()

    columnas = [v[0] for v in AMENAZAS.values()]
    nombres = list(AMENAZAS.keys())
    etiquetas = [f"{AMENAZAS[n][1]} {AMENAZAS_CORTAS[n]}" for n in nombres]
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
        margin=dict(l=0, r=4, t=8, b=52),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(side="bottom", tickangle=0, tickfont=dict(size=10), showgrid=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), showgrid=False)
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
        </div>
        <div>{logo_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Filtros
with st.container(border=True):
    st.markdown('<div class="filter-label">Filtros de consulta</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([1.15, 1.35, 1.15, 1.85], gap="medium")
    with f1:
        sitrep_id = st.selectbox("SitRep / fecha", ids, format_func=lambda x: labels_sitrep.get(x, x))

    actual = base[base["sitrep_id"] == sitrep_id].copy()

    with f2:
        opciones_sub = sorted(actual["subregion"].dropna().astype(str).unique())
        filtro_sub = st.multiselect("Subregión", opciones_sub, placeholder="Todas")
    with f3:
        opciones_pri = [p for p in ORDEN_PRIORIDAD if p in set(actual["prioridad"].dropna())]
        filtro_pri = st.multiselect("Prioridad", opciones_pri, placeholder="Todas")
    with f4:
        filtro_amenaza = st.multiselect("Amenaza / impacto", list(AMENAZAS.keys()), placeholder="Todas")
    st.markdown('<div class="filter-note">Los filtros actualizan todos los indicadores y visualizaciones del corte seleccionado.</div>', unsafe_allow_html=True)

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
k1.metric("Países / territorios", int(len(filtrado)))
k2.metric("🔴 Prioridad alta", int((filtrado["prioridad"] == "Alta").sum()))
k3.metric("🟠 Prioridad media", int((filtrado["prioridad"] == "Media").sum()))
k4.metric("Declaratoria activa", int(filtrado["declaratoria_activa"].apply(es_activo).sum()))
k5.metric("Impacto en salud", int(filtrado["impacto_salud_documentado"].apply(es_impacto).sum()))

# Mapa y resumen
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
with col_resumen:
    st.markdown('<div class="summary-card"><div class="summary-title">Principales amenazas</div>', unsafe_allow_html=True)
    for nombre, (col, icono) in AMENAZAS.items():
        n = int(filtrado[col].sum()) if col in filtrado.columns else 0
        st.markdown(
            f'<div class="threat-row"><span>{icono} {html.escape(nombre)}</span><span class="threat-count">{n}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="summary-card"><div class="summary-title">Nivel de prioridad</div>', unsafe_allow_html=True)
    for p in ORDEN_PRIORIDAD:
        n = int((filtrado["prioridad"] == p).sum())
        txt_color = "#5D4B00" if p == "Baja" else COLORES_PRIORIDAD[p]
        st.markdown(
            f'<div class="threat-row"><span><span style="color:{COLORES_PRIORIDAD[p]};font-size:1.1rem">●</span> {html.escape(p)}</span><span class="threat-count" style="color:{txt_color}">{n}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# Situación regional
section_header("Situación regional", "Comparación territorial y perfil de amenazas")
# Los dos gráficos usan exactamente la misma altura para que sus tarjetas
# comiencen y terminen alineadas. La altura se adapta al número de países
# visibles, pero se limita para evitar paneles demasiado altos o bajos.
altura_situacion = max(520, min(620, 25 * max(1, len(filtrado)) + 90))
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
            pais_sel = st.selectbox("País / territorio", paises)

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
