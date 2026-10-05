from pathlib import Path
import re

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# Posiciones manuales de los callouts. El primer punto sigue siendo el punto
# representativo del país; este diccionario controla dónde se dibuja la etiqueta.
if "POSICIONES_CALLOUTS =" not in txt:
    marker = "\nCIFRAS = {"
    block = '''

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
'''
    if marker not in txt:
        raise RuntimeError("No se encontró el punto de inserción antes de CIFRAS")
    txt = txt.replace(marker, block + marker, 1)

# Reemplazar las burbujas por callouts: línea fina desde el país y texto limpio
# con el nombre del país y TODOS los iconos seleccionados. El detalle completo
# permanece en hover.
patron = re.compile(r'''    if mostrar_amenazas:\n.*?\n    fig\.update_geos\(''', re.S)
reemplazo = '''    if mostrar_amenazas:
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
            iconos = "  ".join(icono for _, icono in activas)
            detalle = "<br>".join(
                f"{icono} {html.escape(nombre)}" for nombre, icono in activas
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

    fig.update_geos('''

txt, n = patron.subn(reemplazo, txt, count=1)
if n != 1:
    raise RuntimeError(f"No se pudo reemplazar la capa de amenazas; coincidencias={n}")

old_note = (
    "El color del país representa la prioridad. Cada burbuja resume las amenazas / impactos reportados por país; "
    "al pasar el cursor se ve el detalle completo. Estos controles solo cambian la visualización del mapa."
)
new_note = (
    "El color del país representa la prioridad. Los callouts conectan cada país con sus amenazas / impactos reportados; "
    "al pasar el cursor se ve el detalle completo. Estos controles solo cambian la visualización del mapa."
)
if old_note in txt:
    txt = txt.replace(old_note, new_note, 1)

p.write_text(txt, encoding="utf-8")
print("Mapa cambiado de burbujas a callouts")
