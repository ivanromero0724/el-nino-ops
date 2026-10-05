from pathlib import Path
import re

# Ajuste final del mapa del dashboard:
# - una sola vista interactiva (prioridad + amenazas)
# - selector de pictogramas visibles
# - anclas de callout pequeñas
# - pictogramas pegados al nombre del país mediante offsets en píxeles
# - rutas del SitRep para evitar cruces
# - navegación restringida a la vista de las Américas

# ============================================================
# 1) MAPA INTERACTIVO (app.py)
# ============================================================
p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# Si el usuario desmarca todos los iconos, respetar la selección vacía.
txt = txt.replace(
    '    seleccion = frame_globals.get("amenazas_mapa") or list(AMENAZAS.keys())\n',
    '    seleccion = frame_globals.get("amenazas_mapa")\n'
    '    if seleccion is None:\n'
    '        seleccion = list(AMENAZAS.keys())\n',
)

# Los iconos comparten la MISMA coordenada geográfica de la etiqueta y se
# separan con getPixelOffset. Así permanecen pegados al nombre incluso al hacer
# zoom y no se abren ni se cruzan por usar grados geográficos como separación.
txt = re.sub(
    r'        inicio_x = .*?\n        y_iconos = .*?\n        separacion = .*?\n',
    '        posicion_iconos = [x, y]\n',
    txt,
    count=1,
)
txt = txt.replace(
    '                "position": [inicio_x + i * separacion, y_iconos],\n',
    '                "position": posicion_iconos,\n'
    '                "pixel_offset": [4 + i * 18, 15],\n',
)

# Si una ejecución previa ya dejó otro bloque de posición, normalizarlo.
txt = txt.replace(
    '                "position": [x + 0.55 + i * 1.95, y - 2.15],\n',
    '                "position": [x, y],\n'
    '                "pixel_offset": [4 + i * 18, 15],\n',
)

# Iconos pequeños y consistentes en pantalla.
txt = txt.replace('                "size": 16,\n', '                "size": 14,\n')
txt = txt.replace('                size_min_pixels=12,\n                size_max_pixels=18,\n',
                  '                size_min_pixels=11,\n                size_max_pixels=15,\n')

# IconLayer usa el offset en píxeles guardado por pictograma.
needle_icon = '                get_position="position",\n                get_size="size",\n'
if needle_icon in txt and 'get_pixel_offset="pixel_offset"' not in txt:
    txt = txt.replace(
        needle_icon,
        '                get_position="position",\n'
        '                get_pixel_offset="pixel_offset",\n'
        '                get_size="size",\n',
        1,
    )

# Línea y punto de anclaje discretos.
txt = txt.replace('                width_min_pixels=1.0,\n', '                width_min_pixels=0.85,\n')
txt = txt.replace(
    '                get_radius=2.2,\n'
    '                radius_units="pixels",\n'
    '                pickable=False,\n',
    '                get_radius=0.75,\n'
    '                radius_units="pixels",\n'
    '                radius_min_pixels=0.75,\n'
    '                radius_max_pixels=1.25,\n'
    '                pickable=False,\n',
)

# Si el bloque ya tiene radio pequeño, no duplicar límites.
if 'get_radius=0.75,' in txt and 'radius_min_pixels=0.75,' not in txt:
    txt = txt.replace(
        '                get_radius=0.75,\n                radius_units="pixels",\n',
        '                get_radius=0.75,\n'
        '                radius_units="pixels",\n'
        '                radius_min_pixels=0.75,\n'
        '                radius_max_pixels=1.25,\n',
        1,
    )

# Vista inicial centrada en las Américas y límites de zoom para que nunca se
# aleje hasta mostrar el mundo completo.
txt = txt.replace('        longitude=-76.0,\n        latitude=-10.0,\n        zoom=2.18,\n',
                  '        longitude=-76.0,\n        latitude=-10.0,\n        zoom=2.25,\n        min_zoom=2.05,\n        max_zoom=5.25,\n')
if 'zoom=2.25,\n        min_zoom=' not in txt:
    txt = txt.replace('        zoom=2.25,\n        pitch=0,\n',
                      '        zoom=2.25,\n        min_zoom=2.05,\n        max_zoom=5.25,\n        pitch=0,\n')

# Restringir navegación: zoom + hover sí; desplazamiento/rotación no.
old_deck = '''    return pdk.Deck(\n        layers=capas,\n        initial_view_state=vista,\n        map_style=None,\n        tooltip=tooltip,\n    )\n'''
new_deck = '''    vista_mapa = pdk.View(\n        type="MapView",\n        controller={\n            "dragPan": False,\n            "dragRotate": False,\n            "scrollZoom": True,\n            "doubleClickZoom": True,\n            "touchZoom": True,\n            "keyboard": False,\n        },\n        repeat=False,\n    )\n\n    return pdk.Deck(\n        layers=capas,\n        initial_view_state=vista,\n        views=[vista_mapa],\n        map_style=None,\n        tooltip=tooltip,\n    )\n'''
if old_deck in txt:
    txt = txt.replace(old_deck, new_deck, 1)
elif 'views=[vista_mapa]' not in txt:
    raise RuntimeError("No se encontró la construcción final de pdk.Deck")

p.write_text(txt, encoding="utf-8")

# ============================================================
# 2) CONTROLES DEL DASHBOARD (app_legacy.py)
# ============================================================
p = Path("app_legacy.py")
txt = p.read_text(encoding="utf-8")

# Quitar el selector Prioridad / Prioridad + amenazas. El único mapa muestra
# siempre prioridad por color + amenazas/impactos mediante callouts.
patron_controles = re.compile(
    r'''with st\.container\(border=True\):\n'''
    r'''    vm1, vm2 = st\.columns\(\[1\.25, 2\.75\], gap="medium"\)\n'''
    r'''    with vm1:\n.*?'''
    r'''    st\.markdown\(\n'''
    r'''        '<div class="map-note">.*?</div>',\n'''
    r'''        unsafe_allow_html=True,\n'''
    r'''    \)\n''',
    re.S,
)

nuevo_controles = '''with st.container(border=True):
    # Una sola vista: prioridad por color + amenazas/impactos mediante callouts.
    modo_mapa = "Prioridad + amenazas"
    amenazas_mapa = st.multiselect(
        "Iconos visibles",
        list(AMENAZAS.keys()),
        default=list(AMENAZAS.keys()),
        format_func=lambda x: AMENAZAS_CORTAS[x],
        key="amenazas_mapa",
    )
    st.markdown(
        '<div class="map-note">El color del país representa el nivel de prioridad. Los pictogramas muestran las amenazas / impactos seleccionados. Puedes hacer zoom y pasar el cursor sobre países e iconos para ver el detalle.</div>',
        unsafe_allow_html=True,
    )
'''

if patron_controles.search(txt):
    txt = patron_controles.sub(nuevo_controles, txt, count=1)
elif 'modo_mapa = "Prioridad + amenazas"' not in txt:
    raise RuntimeError("No se encontró el bloque de controles del mapa")

p.write_text(txt, encoding="utf-8")
print("OK: mapa único interactivo, iconos fijados a los callouts y navegación restringida a las Américas")
