from pathlib import Path
import re

# Ajuste visual del mapa interactivo:
# - mantener visibles los nombres de los países aunque se oculten amenazas
# - soportar correctamente tildes/ñ en TextLayer
# - aumentar pictogramas y mantenerlos pegados al nombre/callout

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Los nombres/callouts no deben desaparecer cuando el usuario desmarca
#    una amenaza. Las amenazas controlan únicamente los pictogramas visibles.
txt = txt.replace(
    '        activas = _amenazas_activas(fila, seleccion)\n'
    '        if not activas:\n'
    '            continue\n\n'
    '        x, y, nombre_pais = mapa_ref.LABELS[iso]\n',
    '        activas = _amenazas_activas(fila, seleccion)\n\n'
    '        x, y, nombre_pais = mapa_ref.LABELS[iso]\n',
)

# 2) Nombres más legibles y con un atlas explícito de caracteres latinos.
#    character_set="auto" ha sido inestable en Streamlit Cloud/deck.gl.
txt = txt.replace('                get_size=9,\n', '                get_size=11,\n')
txt = txt.replace('                size_min_pixels=8,\n                size_max_pixels=10,\n',
                  '                size_min_pixels=10,\n                size_max_pixels=12,\n')
txt = re.sub(
    r'                character_set=.*?\n                font_family=',
    '                character_set=list(" ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚÜÑáéíóúüñ"),\n'
    '                font_family=',
    txt,
    count=1,
)

# 3) Iconos más grandes y más cerca del nombre del país. El offset es en
#    píxeles para que la separación se mantenga estable al hacer zoom/pan.
txt = re.sub(
    r'                "pixel_offset": \[[^\]]+\],\n',
    '                "pixel_offset": [6 + i * 24, 19],\n',
    txt,
    count=1,
)
txt = re.sub(
    r'                "size": \d+,\n',
    '                "size": 20,\n',
    txt,
    count=1,
)
txt = txt.replace('                size_min_pixels=11,\n                size_max_pixels=15,\n',
                  '                size_min_pixels=18,\n                size_max_pixels=22,\n')

# Mantener el punto de anclaje pequeño.
txt = txt.replace('                get_radius=0.75,\n', '                get_radius=0.65,\n')
txt = txt.replace('                radius_min_pixels=0.75,\n                radius_max_pixels=1.25,\n',
                  '                radius_min_pixels=0.65,\n                radius_max_pixels=0.95,\n')

p.write_text(txt, encoding="utf-8")
print("OK: nombres visibles con tildes e iconos del mapa ampliados")
