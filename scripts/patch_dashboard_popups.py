from pathlib import Path

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# Los chips del control quedan sin emojis; los pictogramas reales se muestran en el mapa.
txt = txt.replace(
    'format_func=lambda x: f"{AMENAZAS[x][1]} {AMENAZAS_CORTAS[x]}",',
    'format_func=lambda x: AMENAZAS_CORTAS[x],',
)

# Hacer que también el nombre del país en el callout tenga popup.
txt = txt.replace(
    'etiquetas.append({"position": [x, y], "pais": nombre_pais})',
    'etiquetas.append({"position": [x, y], "pais": nombre_pais, "tooltip_title": nombre_pais, "tooltip_line1": "Callout de amenazas / impactos", "tooltip_line2": "Pasa el cursor sobre los pictogramas para ver cada amenaza", "tooltip_line3": ""})',
)

old = '''                get_alignment_baseline="'center'",
                font_weight=700,
                pickable=False,
            )
        )
    if iconos:
'''
new = '''                get_alignment_baseline="'center'",
                font_weight=700,
                pickable=True,
            )
        )
    if iconos:
'''
if old in txt:
    txt = txt.replace(old, new, 1)

p.write_text(txt, encoding="utf-8")
print("Popups activados en países, nombres de callout e iconos; controles del mapa sin emojis")
