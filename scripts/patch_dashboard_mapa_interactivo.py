from pathlib import Path

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# El error en Streamlit Cloud ocurre porque pydeck exige map_provider='mapbox'
# cuando map_style se entrega como diccionario. Para no depender de un token de
# Mapbox, dejamos el mapa sin basemap y dibujamos explícitamente el fondo azul
# del océano como una capa PolygonLayer detrás de los países.

old_capas = '''    capas = [\n        pdk.Layer(\n            "GeoJsonLayer",\n'''
new_capas = '''    fondo_oceano = [\n        {\n            "polygon": [\n                [-180.0, -85.0],\n                [180.0, -85.0],\n                [180.0, 85.0],\n                [-180.0, 85.0],\n            ]\n        }\n    ]\n\n    capas = [\n        pdk.Layer(\n            "PolygonLayer",\n            fondo_oceano,\n            get_polygon="polygon",\n            get_fill_color=[217, 238, 247, 255],\n            stroked=False,\n            pickable=False,\n        ),\n        pdk.Layer(\n            "GeoJsonLayer",\n'''

if old_capas in txt and "fondo_oceano = [" not in txt:
    txt = txt.replace(old_capas, new_capas, 1)

old_deck = 'return pdk.Deck(layers=capas, initial_view_state=vista, map_style=estilo, tooltip=tooltip)'
new_deck = 'return pdk.Deck(layers=capas, initial_view_state=vista, map_style=None, tooltip=tooltip)'
if old_deck in txt:
    txt = txt.replace(old_deck, new_deck, 1)
elif new_deck not in txt:
    raise RuntimeError("No se encontró la construcción pdk.Deck esperada")

# También cubrir el constructor antiguo si reaparece por algún merge/rebase.
txt = txt.replace('map_style=estilo,\n        tooltip=tooltip,', 'map_style=None,\n        tooltip=tooltip,')

p.write_text(txt, encoding="utf-8")
print("Mapa interactivo corregido: fondo azul propio y sin dependencia de Mapbox")
