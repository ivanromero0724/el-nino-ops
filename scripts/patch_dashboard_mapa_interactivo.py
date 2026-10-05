from pathlib import Path
import re

# Ajuste final del mapa del dashboard:
# - una sola vista interactiva (prioridad + amenazas)
# - selector de pictogramas visibles
# - anclas de callout pequeñas
# - pictogramas compactos y cercanos al nombre del país
# - navegación restringida a la vista de las Américas (sin desplazamiento global)

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

# Acercar pictogramas al nombre del país y compactar los grupos.
txt = txt.replace(
    '        inicio_x = x + 1.0 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0)\n'
    '        y_iconos = y + mapa_ref.DESPLAZAMIENTO_ICONOS_Y\n'
    '        separacion = 2.45\n',
    '        # Los pictogramas quedan justo debajo del nombre, como en el mapa SitRep,\n'
    '        # pero con una separación más compacta para evitar cruces entre callouts.\n'
    '        inicio_x = x + 0.55 + mapa_ref.DESPLAZAMIENTO_ICONOS_X.get(iso, 0)\n'
    '        y_iconos = y - 2.15\n'
    '        separacion = 1.95\n',
)

# Iconos ligeramente más pequeños y consistentes en pantalla.
txt = txt.replace('                "size": 16,\n', '                "size": 14,\n')
txt = txt.replace('                size_min_pixels=12,\n                size_max_pixels=18,\n',
                  '                size_min_pixels=11,\n                size_max_pixels=15,\n')

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

# Vista inicial centrada en las Américas.
txt = txt.replace('        longitude=-76.0,\n        latitude=-10.0,\n        zoom=2.18,\n',
                  '        longitude=-76.0,\n        latitude=-10.0,\n        zoom=2.25,\n')

# Restringir la navegación: se conserva zoom + hover, pero no se puede arrastrar
# el mapa hacia otras partes del mundo.
old_deck = '''    return pdk.Deck(\n        layers=capas,\n        initial_view_state=vista,\n        map_style=None,\n        tooltip=tooltip,\n    )\n'''
new_deck = '''    vista_mapa = pdk.View(\n        type="MapView",\n        controller={\n            "dragPan": False,\n            "dragRotate": False,\n            "scrollZoom": True,\n            "doubleClickZoom": True,\n            "touchZoom": True,\n            "keyboard": False,\n        },\n    )\n\n    return pdk.Deck(\n        layers=capas,\n        initial_view_state=vista,\n        views=[vista_mapa],\n        map_style=None,\n        tooltip=tooltip,\n    )\n'''
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
# siempre la prioridad por color y las amenazas mediante pictogramas/callouts.
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
print("OK: mapa único interactivo, callouts compactos y navegación restringida a las Américas")
