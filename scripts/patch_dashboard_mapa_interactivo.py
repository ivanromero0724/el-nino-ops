from pathlib import Path
import re

# Corrige el rasterizado de los pictogramas del SitRep. Matplotlib usa puntos
# tipográficos para DrawingArea; si el lienzo PNG es demasiado pequeño, el
# círculo se recorta y termina viéndose como un cuadrado con esquinas redondas.
# Se usa un lienzo transparente de 112x112 px y un pictograma de 64 pt, dejando
# margen real alrededor del círculo.

# ============================================================
# 1) MAPA INTERACTIVO (app.py)
# ============================================================
p = Path("app.py")
txt = p.read_text(encoding="utf-8")

patron_app = re.compile(
    r"def _icono_data_uri\(clave, size=\d+\):.*?\n\ndef _amenazas_activas",
    re.S,
)

nuevo_app = '''def _icono_data_uri(clave, size=64):
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


def _amenazas_activas'''

if not patron_app.search(txt):
    raise RuntimeError("No se encontró _icono_data_uri en app.py")
txt = patron_app.sub(nuevo_app, txt, count=1)

# El atlas de IconLayer debe declarar las dimensiones REALES del PNG generado.
# Si width/height son menores que la imagen, deck.gl recorta el centro del icono.
txt = txt.replace('"width": 44,', '"width": 112,')
txt = txt.replace('"height": 44,', '"height": 112,')
txt = txt.replace('"anchorX": 22,', '"anchorX": 56,')
txt = txt.replace('"anchorY": 22,', '"anchorY": 56,')

p.write_text(txt, encoding="utf-8")

# ============================================================
# 2) RESTO DEL DASHBOARD (app_legacy.py)
# ============================================================
p = Path("app_legacy.py")
txt = p.read_text(encoding="utf-8")

patron_legacy = re.compile(
    r"@st\.cache_data\(show_spinner=False\)\ndef amenaza_icon_data_uri\(nombre, size=\d+\):.*?\n\ndef amenaza_icon_html",
    re.S,
)

nuevo_legacy = '''@st.cache_data(show_spinner=False)
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


def amenaza_icon_html'''

if not patron_legacy.search(txt):
    raise RuntimeError("No se encontró amenaza_icon_data_uri en app_legacy.py")
txt = patron_legacy.sub(nuevo_legacy, txt, count=1)

# Todos los usos parten del mismo PNG circular, sin versiones más pequeñas que
# puedan volver a recortar el dibujo.
txt = txt.replace('amenaza_icon_data_uri(nombre, 34)', 'amenaza_icon_data_uri(nombre)')

# Mantener siempre el contenedor visual circular y sin clipping CSS.
txt = txt.replace(
    'width:20px; height:20px; object-fit:contain; vertical-align:middle;',
    'width:20px; height:20px; object-fit:contain; vertical-align:middle; border-radius:50%; overflow:visible;',
)

p.write_text(txt, encoding="utf-8")
print("OK: pictogramas circulares renderizados con margen transparente y sin recorte")
