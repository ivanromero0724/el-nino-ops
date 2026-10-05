from pathlib import Path

# Aplicación temporal del ajuste visual solicitado para el mapa del dashboard.
p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Reutilizar exactamente los iconos y posiciones del mapa PDF/PNG.
if "from scripts import mapa_sitrep as mapa_ref" not in txt:
    txt = txt.replace(
        "import streamlit as st\n",
        "import streamlit as st\nimport matplotlib.pyplot as plt\nfrom scripts import mapa_sitrep as mapa_ref\n",
        1,
    )

# 2) Mapeo entre nombres del dashboard y claves usadas por el mapa estático.
if "AMENAZA_CLAVE_ESTATICA =" not in txt:
    anchor = '''AMENAZAS_CORTAS = {
    "Sequía / agua": "Agua",
    "Inundaciones / lluvias": "Lluvias",
    "Incendios / quemadas": "Incendios",
    "Inseguridad alimentaria": "Alimentos",
    "Dengue / otras arbovirosis": "Arbovirosis",
    "Calidad del aire / riesgo respiratorio": "Aire",
    "Afectación de servicios de salud": "Servicios",
}
'''
    block = anchor + '''
AMENAZA_CLAVE_ESTATICA = {
    "Sequía / agua": "agua",
    "Inundaciones / lluvias": "inundaciones",
    "Incendios / quemadas": "incendios",
    "Inseguridad alimentaria": "alimentos",
    "Dengue / otras arbovirosis": "arbovirosis",
    "Calidad del aire / riesgo respiratorio": "respiratorio",
    "Afectación de servicios de salud": "servicios",
}
'''
    if anchor not in txt:
        raise RuntimeError("No se encontró AMENAZAS_CORTAS")
    txt = txt.replace(anchor, block, 1)

# 3) Nuevo render para Prioridad + amenazas. Usa los mismos iconos vectoriales,
#    callouts, rutas y posiciones que scripts/mapa_sitrep.py.
if "def construir_mapa_callouts_estatico(" not in txt:
    anchor = "\ndef grafico_subregion(datos, altura=560):\n"
    funcion = r'''

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
'''
    if anchor not in txt:
        raise RuntimeError("No se encontró el inicio de grafico_subregion")
    txt = txt.replace(anchor, funcion + anchor, 1)

# 4) Usar el render estático compartido cuando se activan amenazas; conservar
#    Plotly interactivo cuando se visualiza solo prioridad.
old = '''with col_mapa:
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
new = '''with col_mapa:
    with st.container(border=True):
        if modo_mapa == "Prioridad + amenazas":
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
'''
if old not in txt:
    raise RuntimeError("No se encontró el bloque de render del mapa")
txt = txt.replace(old, new, 1)

# 5) Nota coherente con el nuevo render.
notas_previas = [
    "El color del país representa la prioridad. Los callouts conectan cada país con sus amenazas / impactos reportados; al pasar el cursor se ve el detalle completo. Estos controles solo cambian la visualización del mapa.",
    "El color del país representa la prioridad. Cada burbuja resume las amenazas / impactos reportados por país; al pasar el cursor se ve el detalle completo. Estos controles solo cambian la visualización del mapa.",
]
nota_nueva = (
    "El color del país representa la prioridad. En la vista de amenazas se usan los mismos pictogramas vectoriales y callouts del mapa SitRep en PDF/PNG. "
    "Los controles solo cambian la visualización del mapa."
)
for nota in notas_previas:
    if nota in txt:
        txt = txt.replace(nota, nota_nueva, 1)
        break

p.write_text(txt, encoding="utf-8")
print("Dashboard ajustado para reutilizar callouts e iconos del mapa estático")
