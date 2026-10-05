from pathlib import Path
import re

# ============================================================
# 1) MAPA INTERACTIVO: tamaños correctos y tooltips consistentes
# ============================================================
p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# Aplanar los objetos de etiquetas/iconos para que deck.gl resuelva bien
# position, size y tooltip. Esto evita que use tamaños por defecto gigantes.
old_etiqueta = '''        etiquetas.append(\n            _feature_point(\n                (x, y),\n                pais=nombre_pais,\n                tooltip_title=nombre_pais,\n                tooltip_line1="Callout de amenazas / impactos",\n                tooltip_line2="Pasa el cursor sobre cada pictograma para ver su significado.",\n                tooltip_line3="",\n            )\n        )\n'''
new_etiqueta = '''        etiquetas.append({\n            "position": [x, y],\n            "pais": nombre_pais,\n            "tooltip_title": nombre_pais,\n            "tooltip_line1": "Callout de amenazas / impactos",\n            "tooltip_line2": "Pasa el cursor sobre cada pictograma para ver su significado.",\n            "tooltip_line3": "",\n        })\n'''
if old_etiqueta in txt:
    txt = txt.replace(old_etiqueta, new_etiqueta, 1)

old_iconos = '''            iconos.append(\n                _feature_point(\n                    (inicio_x + i * separacion, y_iconos),\n                    icon={\n                        "url": _icono_data_uri(clave),\n                        "width": 76,\n                        "height": 76,\n                        "anchorX": 38,\n                        "anchorY": 38,\n                    },\n                    size=max(29, mapa_ref.TAMANOS_ICONOS.get(iso, 27) + 4),\n                    tooltip_title=nombre_pais,\n                    tooltip_line1=nombre,\n                    tooltip_line2="Amenaza / impacto reportado",\n                    tooltip_line3="",\n                )\n            )\n'''
new_iconos = '''            iconos.append({\n                "position": [inicio_x + i * separacion, y_iconos],\n                "icon": {\n                    "url": _icono_data_uri(clave),\n                    "width": 44,\n                    "height": 44,\n                    "anchorX": 22,\n                    "anchorY": 22,\n                },\n                "size": 16,\n                "tooltip_title": nombre_pais,\n                "tooltip_line1": nombre,\n                "tooltip_line2": "Amenaza / impacto reportado",\n                "tooltip_line3": "",\n            })\n'''
if old_iconos in txt:
    txt = txt.replace(old_iconos, new_iconos, 1)

# Si el bloque ya fue transformado parcialmente, asegurar tamaños pequeños.
txt = txt.replace('"width": 76,', '"width": 44,')
txt = txt.replace('"height": 76,', '"height": 44,')
txt = txt.replace('"anchorX": 38,', '"anchorX": 22,')
txt = txt.replace('"anchorY": 38,', '"anchorY": 22,')
txt = re.sub(r'"size":max\([^\n]+\),', '"size": 16,', txt)
txt = re.sub(r'"size": max\([^\n]+\),', '"size": 16,', txt)

# Capas de texto e iconos: accessors planos y límites estrictos en píxeles.
txt = txt.replace('get_position="geometry.coordinates",\n                get_text="properties.pais",', 'get_position="position",\n                get_text="pais",')
txt = txt.replace('get_position="geometry.coordinates",\n                get_icon="properties.icon",', 'get_position="position",\n                get_icon="icon",')
txt = txt.replace('get_size="properties.size",', 'get_size="size",')

txt = txt.replace('get_size=14,\n                size_units="pixels",', 'get_size=9,\n                size_units="pixels",\n                size_scale=1,\n                size_min_pixels=8,\n                size_max_pixels=10,')

# Agregar límites al IconLayer si aún no existen.
old_icon_layer = '''                get_size="size",\n                size_units="pixels",\n                pickable=True,\n'''
new_icon_layer = '''                get_size="size",\n                size_units="pixels",\n                size_scale=1,\n                size_min_pixels=12,\n                size_max_pixels=18,\n                pickable=True,\n'''
if old_icon_layer in txt:
    txt = txt.replace(old_icon_layer, new_icon_layer, 1)

# Tooltips: usar propiedades planas también en GeoJSON.
needle = '    geojson = json.loads(mapa.to_json())\n'
if needle in txt and 'feature["tooltip_title"]' not in txt:
    txt = txt.replace(
        needle,
        needle + '''    # Duplicar campos de tooltip al nivel superior del Feature para que\n    # el mismo template funcione en GeoJsonLayer, TextLayer e IconLayer.\n    for feature in geojson.get("features", []):\n        props = feature.get("properties", {})\n        for key in ("tooltip_title", "tooltip_line1", "tooltip_line2", "tooltip_line3"):\n            feature[key] = props.get(key, "")\n''',
        1,
    )

txt = txt.replace('{properties.tooltip_title}', '{tooltip_title}')
txt = txt.replace('{properties.tooltip_line1}', '{tooltip_line1}')
txt = txt.replace('{properties.tooltip_line2}', '{tooltip_line2}')
txt = txt.replace('{properties.tooltip_line3}', '{tooltip_line3}')

# Líneas/anclas un poco más discretas.
txt = txt.replace('width_min_pixels=1.15,', 'width_min_pixels=1.0,')
txt = txt.replace('get_radius=2.8,', 'get_radius=2.2,')

p.write_text(txt, encoding="utf-8")

# ============================================================
# 2) DASHBOARD COMPLETO: reemplazar emojis por pictogramas SitRep
# ============================================================
p = Path("app_legacy.py")
txt = p.read_text(encoding="utf-8")

if 'from io import BytesIO' not in txt:
    txt = txt.replace('from pathlib import Path\n', 'from pathlib import Path\nfrom io import BytesIO\n', 1)

old_amenazas = '''AMENAZAS = {\n    "Sequía / agua": ("icono_agua", "💧"),\n    "Inundaciones / lluvias": ("icono_inundaciones", "🌧️"),\n    "Incendios / quemadas": ("icono_incendios", "🔥"),\n    "Inseguridad alimentaria": ("icono_alimentos", "🌾"),\n    "Dengue / otras arbovirosis": ("icono_arbovirosis", "🦟"),\n    "Calidad del aire / riesgo respiratorio": ("icono_respiratorio", "🫁"),\n    "Afectación de servicios de salud": ("icono_servicios", "✚"),\n}\n'''
new_amenazas = '''AMENAZAS = {\n    "Sequía / agua": ("icono_agua", "agua"),\n    "Inundaciones / lluvias": ("icono_inundaciones", "inundaciones"),\n    "Incendios / quemadas": ("icono_incendios", "incendios"),\n    "Inseguridad alimentaria": ("icono_alimentos", "alimentos"),\n    "Dengue / otras arbovirosis": ("icono_arbovirosis", "arbovirosis"),\n    "Calidad del aire / riesgo respiratorio": ("icono_respiratorio", "respiratorio"),\n    "Afectación de servicios de salud": ("icono_servicios", "servicios"),\n}\n'''
if old_amenazas in txt:
    txt = txt.replace(old_amenazas, new_amenazas, 1)

# Favicon institucional en vez de emoji.
txt = txt.replace('page_icon="🌎",', 'page_icon=str(RUTA_LOGO),')

# CSS para pictogramas pequeños del tablero.
css_anchor = '        .threat-row:last-child {border-bottom:none;}\n'
if css_anchor in txt and '.threat-icon {' not in txt:
    txt = txt.replace(
        css_anchor,
        css_anchor + '''        .threat-icon {\n            width:20px; height:20px; object-fit:contain; vertical-align:middle;\n            margin-right:.38rem; flex:0 0 auto;\n        }\n        .threat-label {display:flex; align-items:center; min-width:0;}\n''',
        1,
    )

# Helpers de pictogramas reutilizan EXACTAMENTE las funciones vectoriales del mapa PDF/PNG.
helper_anchor = '''def logo_data_uri():\n    if not RUTA_LOGO.exists():\n        return None\n    encoded = base64.b64encode(RUTA_LOGO.read_bytes()).decode("ascii")\n    return f"data:image/png;base64,{encoded}"\n'''
if helper_anchor in txt and 'def amenaza_icon_data_uri(' not in txt:
    helper = helper_anchor + '''\n\n@st.cache_data(show_spinner=False)\ndef amenaza_icon_data_uri(nombre, size=42):\n    clave = AMENAZAS[nombre][1]\n    fig = plt.figure(figsize=(.50, .50), dpi=100)\n    ax = fig.add_axes([0, 0, 1, 1])\n    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")\n    ax.add_artist(mapa_ref.AnnotationBbox(\n        mapa_ref.ICONOS[clave](size), (.5, .5), xycoords=ax.transAxes,\n        frameon=False, box_alignment=(.5, .5)\n    ))\n    buf = BytesIO()\n    fig.savefig(buf, format="png", dpi=100, transparent=True, pad_inches=0)\n    plt.close(fig)\n    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")\n\n\ndef amenaza_icon_html(nombre, size=20):\n    return f'<img class="threat-icon" src="{amenaza_icon_data_uri(nombre)}" width="{size}" height="{size}" alt="">'\n'''
    txt = txt.replace(helper_anchor, helper, 1)

# Quitar emojis/texto-clave de hovers y callouts Plotly de respaldo.
txt = txt.replace('f"{icono} {AMENAZAS_CORTAS[nombre]}"', 'f"{AMENAZAS_CORTAS[nombre]}"')
txt = txt.replace('iconos = "  ".join(icono for _, icono in activas)', 'iconos = " · ".join(AMENAZAS_CORTAS[nombre] for nombre, _ in activas)')
txt = txt.replace('f"{icono} {html.escape(nombre)}" for nombre, icono in activas', 'f"{html.escape(nombre)}" for nombre, _ in activas')

# KPI sin emojis.
txt = txt.replace('k2.metric("🔴 Prioridad alta",', 'k2.metric("Prioridad alta",')
txt = txt.replace('k3.metric("🟠 Prioridad media",', 'k3.metric("Prioridad media",')

# Selectores: texto limpio; los pictogramas reales aparecen en mapa y visuales.
txt = txt.replace('format_func=lambda x: f"{AMENAZAS[x][1]} {AMENAZAS_CORTAS[x]}",', 'format_func=lambda x: AMENAZAS_CORTAS[x],')

# Resumen lateral con los mismos iconos del SitRep.
old_row = '''            f'<div class="threat-row"><span>{icono} {html.escape(nombre)}</span><span class="threat-count">{n}</span></div>',\n'''
new_row = '''            f'<div class="threat-row"><span class="threat-label">{amenaza_icon_html(nombre)}{html.escape(nombre)}</span><span class="threat-count">{n}</span></div>',\n'''
if old_row in txt:
    txt = txt.replace(old_row, new_row, 1)

# Matriz: quitar emojis de ticks y agregar pictogramas vectoriales debajo.
txt = txt.replace('etiquetas = [f"{AMENAZAS[n][1]} {AMENAZAS_CORTAS[n]}" for n in nombres]', 'etiquetas = [AMENAZAS_CORTAS[n] for n in nombres]')
txt = txt.replace('margin=dict(l=0, r=4, t=8, b=52),', 'margin=dict(l=0, r=4, t=8, b=82),', 1)

matrix_anchor = '''    fig.update_xaxes(side="bottom", tickangle=0, tickfont=dict(size=10), showgrid=False)\n    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), showgrid=False)\n    return fig\n'''
if matrix_anchor in txt and 'amenaza_icon_data_uri(nombres[i]' not in txt:
    matrix_new = '''    fig.update_xaxes(side="bottom", tickangle=0, tickfont=dict(size=10), showgrid=False)\n    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), showgrid=False)\n    for i, nombre in enumerate(nombres):\n        fig.add_layout_image(dict(\n            source=amenaza_icon_data_uri(nombre, 34),\n            xref="paper", yref="paper",\n            x=(i + .5) / len(nombres), y=-.085,\n            sizex=.038, sizey=.038,\n            xanchor="center", yanchor="middle", layer="above"\n        ))\n    return fig\n'''
    txt = txt.replace(matrix_anchor, matrix_new, 1)

# Evitar que resumen_iconos_pais construya cadenas con claves internas.
old_resumen = '''    iconos = [icono for _, icono in activas]\n    nombres = [nombre for nombre, _ in activas]\n\n    etiqueta = "".join(iconos[:max_iconos])\n    extra = len(iconos) - max_iconos\n    if extra > 0:\n        etiqueta += f"+{extra}"\n'''
new_resumen = '''    nombres = [nombre for nombre, _ in activas]\n    etiqueta = " · ".join(AMENAZAS_CORTAS[n] for n in nombres[:max_iconos])\n    extra = len(nombres) - max_iconos\n    if extra > 0:\n        etiqueta += f" +{extra}"\n'''
if old_resumen in txt:
    txt = txt.replace(old_resumen, new_resumen, 1)

p.write_text(txt, encoding="utf-8")
print("OK: iconos interactivos reducidos y pictogramas SitRep unificados en el dashboard")
