from pathlib import Path
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
GRIS_CLARO = "#F4F8FA"
BORDE = "#D9E6EE"

COLORES_PRIORIDAD = {
    "Alta": "#D71920",
    "Media": "#FF8618",
    "Baja": "#F6C344",
    "Sin priorización": "#BDBDBD",
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

CIFRAS = {
    "personas_afectadas": "Personas afectadas",
    "personas_damnificadas": "Personas damnificadas",
    "familias_afectadas": "Familias afectadas",
    "muertes": "Muertes",
    "heridos": "Heridos",
    "personas_inseguridad_alimentaria_min": "Personas con inseguridad alimentaria (mín.)",
    "personas_inseguridad_alimentaria_max": "Personas con inseguridad alimentaria (máx.)",
    "personas_emergencia_alimentaria": "Personas en emergencia alimentaria",
    "establecimientos_salud_afectados": "Establecimientos de salud afectados",
    "establecimientos_salud_expuestos": "Establecimientos de salud expuestos",
    "hectareas_incendios": "Hectáreas afectadas por incendios",
    "municipios_afectados": "Municipios afectados",
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
        .block-container {{padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}}
        h1, h2, h3 {{color: {AZUL_OPS};}}
        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid {BORDE};
            border-radius: 14px;
            padding: 0.75rem 0.9rem;
            box-shadow: 0 2px 8px rgba(0, 75, 135, 0.05);
        }}
        div[data-testid="stMetricLabel"] {{color: #51697D;}}
        div[data-testid="stMetricValue"] {{color: {AZUL_OPS};}}
        .ops-header {{
            border-bottom: 3px solid {AZUL_SEC};
            padding-bottom: 0.65rem;
            margin-bottom: 0.9rem;
        }}
        .ops-kicker {{color: {AZUL_SEC}; font-weight: 700; font-size: 0.82rem; letter-spacing: .04em; text-transform: uppercase;}}
        .ops-title {{color: {AZUL_OPS}; font-weight: 800; font-size: 2rem; line-height: 1.1; margin-top: .15rem;}}
        .ops-subtitle {{color: #5A7286; font-size: .95rem; margin-top: .25rem;}}
        .section-title {{color: {AZUL_OPS}; font-weight: 800; font-size: 1.15rem; margin: .5rem 0 .45rem 0;}}
        .priority-pill {{display:inline-block; padding:.28rem .65rem; border-radius:999px; color:white; font-weight:700; font-size:.86rem;}}
        .detail-card {{background:{GRIS_CLARO}; border:1px solid {BORDE}; border-radius:12px; padding:.85rem 1rem; min-height:138px;}}
        .detail-card h4 {{color:{AZUL_OPS}; margin:0 0 .45rem 0; font-size:.95rem;}}
        .detail-card p {{color:{TEXTO}; margin:0; font-size:.92rem; line-height:1.45;}}
        .threat-row {{display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #E8F0F4; padding:.37rem 0; font-size:.9rem;}}
        .threat-count {{font-weight:800; color:{AZUL_OPS};}}
        .caption-box {{font-size:.79rem; color:#6B7F90;}}
        div[data-testid="stSelectbox"], div[data-testid="stMultiSelect"] {{font-size:.92rem;}}
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


def construir_mapa(geo, datos):
    mapa = geo[["COUNTRY", "ISO_CC", "geometry"]].copy()
    cols = ["iso3", "pais", "prioridad", "situacion_predominante", "impacto_salud_documentado"]
    cols = [c for c in cols if c in datos.columns]
    info = datos[cols].drop_duplicates("iso3")
    mapa = mapa.merge(info, left_on="ISO_CC", right_on="iso3", how="left")
    mapa["prioridad_mapa"] = mapa["prioridad"].fillna("Sin priorización")
    mapa["nombre_mapa"] = mapa["pais"].fillna(mapa["COUNTRY"])
    mapa["situacion_mapa"] = mapa["situacion_predominante"].fillna("Sin hallazgos priorizados en este SitRep")

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
            "situacion_mapa": True,
        },
        labels={"prioridad_mapa": "Prioridad", "situacion_mapa": "Situación"},
        color_discrete_map=COLORES_PRIORIDAD,
        category_orders={"prioridad_mapa": ORDEN_PRIORIDAD},
    )

    fig.update_geos(
        projection_type="equirectangular",
        lonaxis_range=[-121.5, -31],
        lataxis_range=[-58, 37.5],
        showcoastlines=False,
        showcountries=True,
        countrycolor="white",
        countrywidth=0.6,
        showland=False,
        showocean=True,
        oceancolor=AZUL_MAR,
        bgcolor=AZUL_MAR,
        visible=False,
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.65)
    fig.update_layout(
        height=680,
        margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor="white",
        plot_bgcolor=AZUL_MAR,
        legend_title_text="Nivel de prioridad",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="left",
            x=0.02,
            bgcolor="rgba(255,255,255,.88)",
            bordercolor=BORDE,
            borderwidth=1,
        ),
    )
    return fig


def grafico_subregion(datos):
    if datos.empty:
        return go.Figure()
    t = (
        datos.groupby(["subregion", "prioridad"], dropna=False)
        .size()
        .reset_index(name="Países")
    )
    fig = px.bar(
        t,
        x="subregion",
        y="Países",
        color="prioridad",
        color_discrete_map=COLORES_PRIORIDAD,
        category_orders={"prioridad": ORDEN_PRIORIDAD},
        barmode="stack",
    )
    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=10, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="Prioridad",
        xaxis_title=None,
        yaxis_title="Países/territorios",
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(tickangle=-15, showgrid=False)
    fig.update_yaxes(gridcolor="#EAF0F4", rangemode="tozero", dtick=1)
    return fig


def matriz_amenazas(datos):
    if datos.empty:
        return go.Figure()

    columnas = [v[0] for v in AMENAZAS.values()]
    etiquetas = [f"{icono} {nombre}" for nombre, (_, icono) in AMENAZAS.items()]
    m = datos.set_index("pais")[columnas].copy()
    m = m.loc[m.sum(axis=1).sort_values(ascending=False).index]

    fig = go.Figure(
        data=go.Heatmap(
            z=m.values,
            x=etiquetas,
            y=m.index,
            zmin=0,
            zmax=1,
            colorscale=[[0, "#F1F5F7"], [0.499, "#F1F5F7"], [0.5, AZUL_SEC], [1, AZUL_SEC]],
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate="<b>%{y}</b><br>%{x}<br>%{z}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(330, 28 * len(m) + 120),
        margin=dict(l=10, r=10, t=10, b=120),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(side="bottom", tickangle=-38, tickfont=dict(size=10))
    fig.update_yaxes(autorange="reversed")
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
        margin=dict(l=10, r=10, t=10, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title=None,
        yaxis_title="Países/territorios",
        legend_title_text="Prioridad",
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_yaxes(gridcolor="#EAF0F4", dtick=1, rangemode="tozero")
    return fig


def heatmap_evolucion(base):
    orden_s = (
        base[["sitrep_numero", "fecha_corte", "sitrep_id"]]
        .drop_duplicates()
        .sort_values(["sitrep_numero", "fecha_corte"])
    )
    etiquetas_s = {
        r.sitrep_id: f"S{int(r.sitrep_numero):02d}" for r in orden_s.itertuples()
    }
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
            xgap=2,
            ygap=2,
            customdata=texto_hover,
            hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(350, 27 * len(m) + 120),
        margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_yaxes(autorange="reversed")
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

# Encabezado
h_logo, h_texto = st.columns([1.2, 5.8], vertical_alignment="center")
with h_logo:
    if RUTA_LOGO.exists():
        st.image(str(RUTA_LOGO), width=250)
with h_texto:
    st.markdown(
        """
        <div class="ops-header">
            <div class="ops-kicker">Monitoreo regional</div>
            <div class="ops-title">El Niño y salud pública en las Américas</div>
            <div class="ops-subtitle">Prioridades sanitarias, amenazas, impactos y respuesta de OPS/OMS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Selector temporal
sit = (
    base[["sitrep_id", "sitrep_numero", "fecha_corte"]]
    .drop_duplicates()
    .sort_values(["sitrep_numero", "fecha_corte"], ascending=[False, False])
)
labels_sitrep = {r.sitrep_id: sitrep_etiqueta(pd.Series(r._asdict())) for r in sit.itertuples(index=False)}
ids = sit["sitrep_id"].tolist()

f1, f2, f3, f4 = st.columns([1.1, 1.4, 1.2, 2.0])
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

filtrado = actual.copy()
if filtro_sub:
    filtrado = filtrado[filtrado["subregion"].isin(filtro_sub)]
if filtro_pri:
    filtrado = filtrado[filtrado["prioridad"].isin(filtro_pri)]
if filtro_amenaza:
    cols = [AMENAZAS[a][0] for a in filtro_amenaza]
    filtrado = filtrado[filtrado[cols].eq(1).any(axis=1)]

# KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Países/territorios", int(len(filtrado)))
k2.metric("🔴 Prioridad alta", int((filtrado["prioridad"] == "Alta").sum()))
k3.metric("🟠 Prioridad media", int((filtrado["prioridad"] == "Media").sum()))
k4.metric("Declaratoria activa", int(filtrado["declaratoria_activa"].apply(es_activo).sum()))
k5.metric("Impacto en salud documentado", int(filtrado["impacto_salud_documentado"].apply(es_impacto).sum()))

st.markdown('<div class="section-title">Panorama regional</div>', unsafe_allow_html=True)
col_mapa, col_resumen = st.columns([3.8, 1.2], gap="large")
with col_mapa:
    fig_mapa = construir_mapa(geo, filtrado)
    st.plotly_chart(fig_mapa, use_container_width=True, config={"displayModeBar": False})
with col_resumen:
    st.markdown("#### Principales amenazas")
    for nombre, (col, icono) in AMENAZAS.items():
        n = int(filtrado[col].sum()) if col in filtrado.columns else 0
        st.markdown(
            f'<div class="threat-row"><span>{icono} {nombre}</span><span class="threat-count">{n}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Prioridad")
    for p in ORDEN_PRIORIDAD:
        n = int((filtrado["prioridad"] == p).sum())
        st.markdown(
            f'<div class="threat-row"><span><span style="color:{COLORES_PRIORIDAD[p]};font-size:1.25rem">●</span> {p}</span><span class="threat-count">{n}</span></div>',
            unsafe_allow_html=True,
        )

# Situación regional
st.markdown('<div class="section-title">Situación regional</div>', unsafe_allow_html=True)
g1, g2 = st.columns([1.0, 1.35], gap="large")
with g1:
    st.markdown("**Prioridad por subregión**")
    st.plotly_chart(grafico_subregion(filtrado), use_container_width=True, config={"displayModeBar": False})
with g2:
    st.markdown("**País × amenaza / impacto**")
    st.plotly_chart(matriz_amenazas(filtrado), use_container_width=True, config={"displayModeBar": False})

# Evolución temporal
st.markdown('<div class="section-title">Evolución temporal</div>', unsafe_allow_html=True)
if base["sitrep_id"].nunique() < 2:
    st.info("La evolución temporal se activará automáticamente cuando la base contenga dos o más SitRep. La estructura ya está preparada.")
else:
    e1, e2 = st.columns([1, 1.15], gap="large")
    with e1:
        st.markdown("**Países por nivel de prioridad**")
        st.plotly_chart(evolucion_prioridad(base), use_container_width=True, config={"displayModeBar": False})
    with e2:
        st.markdown("**Evolución de prioridad por país**")
        st.plotly_chart(heatmap_evolucion(base), use_container_width=True, config={"displayModeBar": False})

# Detalle país
st.markdown('<div class="section-title">Detalle por país / territorio</div>', unsafe_allow_html=True)
if filtrado.empty:
    st.warning("No hay países/territorios que cumplan los filtros seleccionados.")
else:
    paises = filtrado.sort_values(["prioridad", "pais"])["pais"].tolist()
    pais_sel = st.selectbox("Selecciona un país o territorio", paises)
    fila = filtrado[filtrado["pais"] == pais_sel].iloc[0]
    prioridad = texto(fila.get("prioridad"), "Sin priorización")
    color_p = COLORES_PRIORIDAD.get(prioridad, GRIS)

    d1, d2, d3 = st.columns([1.8, 1.25, 1.25])
    with d1:
        st.markdown(f"### {pais_sel}")
        st.markdown(
            f'<span class="priority-pill" style="background:{color_p}">{prioridad}</span>',
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown("**Situación predominante**")
        st.write(texto(fila.get("situacion_predominante")))
    with d3:
        st.markdown("**Atribución a El Niño**")
        st.write(texto(fila.get("atribucion_elnino")))

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    bloques = [
        (c1, "Amenazas", fila.get("amenazas_resumen")),
        (c2, "Impacto en salud", fila.get("impacto_salud_resumen")),
        (c3, "Alistamiento / respuesta", fila.get("alistamiento_respuesta")),
        (c4, "Acciones OPS/OMS", fila.get("acciones_ops")),
    ]
    for col, titulo, contenido in bloques:
        with col:
            st.markdown(
                f'<div class="detail-card"><h4>{titulo}</h4><p>{texto(contenido)}</p></div>',
                unsafe_allow_html=True,
            )

    cifras_disponibles = []
    for col, etiqueta in CIFRAS.items():
        if col in fila.index and pd.notna(fila[col]):
            cifras_disponibles.append((etiqueta, formato_numero(float(fila[col]))))

    if cifras_disponibles:
        st.markdown("**Cifras reportadas en el SitRep**")
        columnas = st.columns(min(6, len(cifras_disponibles)))
        for i, (etiqueta, valor) in enumerate(cifras_disponibles):
            columnas[i % len(columnas)].metric(etiqueta, valor)

    pie = []
    if "declaratoria_activa" in fila.index:
        pie.append(f"Declaratoria: {texto(fila.get('declaratoria_activa'))}")
    if "nivel_declaratoria" in fila.index:
        pie.append(texto(fila.get("nivel_declaratoria"), ""))
    if "fuentes_resumen" in fila.index:
        pie.append(f"Fuentes: {texto(fila.get('fuentes_resumen'))}")
    st.markdown(f'<div class="caption-box">{" · ".join([x for x in pie if x])}</div>', unsafe_allow_html=True)

st.divider()
st.caption("Fuente: base maestra de monitoreo de El Niño de OPS/OMS. El tablero toma automáticamente el SitRep seleccionado y conserva la serie histórica para análisis temporal.")
