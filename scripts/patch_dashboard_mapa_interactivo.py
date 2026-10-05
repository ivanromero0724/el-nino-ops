from pathlib import Path

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Etiquetas de países más pequeñas y robustas.
txt = txt.replace('font = ImageFont.truetype(font_path, 26)', 'font = ImageFont.truetype(font_path, 20)')
txt = txt.replace('            "size": 18,\n            "properties": _props_popup(', '            "size": 13,\n            **_props_popup(')
txt = txt.replace('                size_min_pixels=17,\n                size_max_pixels=20,', '                size_min_pixels=12,\n                size_max_pixels=15,')

# 2) Guardar los campos de tooltip en el nivel superior de cada objeto.
# Esto hace que el mismo tooltip funcione de forma consistente para países,
# nombres e iconos en deck.gl/Streamlit.
txt = txt.replace('                "properties": _props_popup(\n                    nombre_pais,\n                    nombre,\n                    "Amenaza / impacto reportado",\n                ),', '                **_props_popup(\n                    nombre_pais,\n                    nombre,\n                    "Amenaza / impacto reportado",\n                ),')

marker = '    geojson = json.loads(mapa.to_json())\n'
insert = '''    geojson = json.loads(mapa.to_json())
    # Duplicar campos del popup al nivel raíz del Feature para que el hover
    # funcione de forma uniforme en GeoJsonLayer e IconLayer.
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        for key in ("tooltip_title", "tooltip_line1", "tooltip_line2", "tooltip_line3"):
            feature[key] = props.get(key, "")
'''
if marker in txt and 'Duplicar campos del popup al nivel raíz del Feature' not in txt:
    txt = txt.replace(marker, insert, 1)

# Tooltip global usando claves raíz.
txt = txt.replace('{properties.tooltip_title}', '{tooltip_title}')
txt = txt.replace('{properties.tooltip_line1}', '{tooltip_line1}')
txt = txt.replace('{properties.tooltip_line2}', '{tooltip_line2}')
txt = txt.replace('{properties.tooltip_line3}', '{tooltip_line3}')

# 3) Solo hover: quitar selección/clic y la ficha persistente inferior.
old_chart = '''            evento = st.pydeck_chart(
                deck,
                use_container_width=True,
                height=690,
                on_select="rerun",
                selection_mode="single-object",
                key="mapa-regional-elnino",
            )
            _mostrar_seleccion_mapa(evento)
            return evento
'''
new_chart = '''            return st.pydeck_chart(
                deck,
                use_container_width=True,
                height=690,
                key="mapa-regional-elnino",
            )
'''
if old_chart in txt:
    txt = txt.replace(old_chart, new_chart, 1)

p.write_text(txt, encoding="utf-8")
print("OK: labels reducidos, hover restaurado y selección por clic desactivada")
