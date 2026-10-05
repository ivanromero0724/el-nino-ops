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

# 3b) Hover robusto sobre países + encuadre inicial México-Sudamérica.
# Usar una única ruta de tooltip basada en `properties` para GeoJsonLayer,
# etiquetas e iconos. Así el popup funciona al pasar el cursor sobre el país.
txt = txt.replace(
    '            **_props_popup(\n                nombre_pais,\n                "Amenazas / impactos",\n                "Pasa el cursor sobre los pictogramas para ver el detalle.",\n            ),',
    '            "properties": _props_popup(\n                nombre_pais,\n                "Amenazas / impactos",\n                "Pasa el cursor sobre los pictogramas para ver el detalle.",\n            ),',
)
txt = txt.replace(
    '                **_props_popup(\n                    nombre_pais,\n                    nombre,\n                    "Amenaza / impacto reportado",\n                ),',
    '                "properties": _props_popup(\n                    nombre_pais,\n                    nombre,\n                    "Amenaza / impacto reportado",\n                ),',
)
txt = txt.replace('{tooltip_title}', '{properties.tooltip_title}')
txt = txt.replace('{tooltip_line1}', '{properties.tooltip_line1}')
txt = txt.replace('{tooltip_line2}', '{properties.tooltip_line2}')
txt = txt.replace('{tooltip_line3}', '{properties.tooltip_line3}')

# Resumir la situación del país en el popup para evitar tarjetas demasiado largas.
old_situacion = '''    mapa["tooltip_line3"] = mapa["situacion_predominante"].fillna(
        "Sin hallazgos priorizados en este SitRep"
    )
'''
new_situacion = '''    situacion_popup = mapa["situacion_predominante"].fillna(
        "Sin hallazgos priorizados en este SitRep"
    ).astype(str)
    situacion_popup = situacion_popup.apply(
        lambda s: s if len(s) <= 210 else s[:207].rstrip() + "..."
    )
    mapa["tooltip_line3"] = "Situación: " + situacion_popup
'''
if old_situacion in txt:
    txt = txt.replace(old_situacion, new_situacion, 1)

# Vista inicial pensada para mostrar completa la región desde México hasta
# el extremo sur de Sudamérica, sin desperdiciar espacio en Norteamérica.
txt = txt.replace(
    '''        longitude=-76.0,
        latitude=-10.0,
        zoom=2.25,
        min_zoom=2.0,
        max_zoom=5.25,''',
    '''        longitude=-76.5,
        latitude=-13.0,
        zoom=2.05,
        min_zoom=1.85,
        max_zoom=5.25,''',
    1,
)
txt = txt.replace(
    '"maxBounds": [[-130.0, -62.0], [-28.0, 43.0]],',
    '"maxBounds": [[-123.0, -60.0], [-30.0, 34.0]],',
    1,
)

p.write_text(txt, encoding="utf-8")

# ============================================================
# 4) Alinear correctamente las dos leyendas laterales
# ============================================================
p = Path("app_legacy.py")
legacy = p.read_text(encoding="utf-8")

css_marker = '''        .threat-count {{font-weight:800; color:{AZUL_OPS}; min-width:1.5rem; text-align:right;}}\n'''
css_extra = '''        .threat-count {{font-weight:800; color:{AZUL_OPS}; min-width:1.5rem; text-align:right;}}

        /* Leyendas laterales: título, iconos, texto y cifras en una misma grilla. */
        .legend-card {{
            border:1px solid {BORDE}; background:#FFFFFF; border-radius:14px;
            margin-bottom:.75rem; overflow:hidden;
        }}
        .legend-title {{
            min-height:52px; display:flex; align-items:center;
            padding:0 1rem; color:{AZUL_OPS}; font-size:.94rem; font-weight:800;
            border-bottom:1px solid #EAF0F4; line-height:1.2;
        }}
        .legend-body {{padding:.5rem 1rem .62rem 1rem;}}
        .legend-row {{
            display:grid; grid-template-columns:minmax(0,1fr) 2rem;
            align-items:center; column-gap:.75rem; min-height:38px;
            color:{TEXTO}; font-size:.84rem;
        }}
        .legend-row + .legend-row {{border-top:1px solid #EEF3F6;}}
        .legend-label {{
            display:flex; align-items:center; gap:.55rem; min-width:0;
            line-height:1.22;
        }}
        .threat-icon {{
            width:22px !important; height:22px !important; object-fit:contain;
            display:block; flex:0 0 22px; margin:0;
        }}
        .priority-dot {{
            width:14px; height:14px; border-radius:50%;
            display:block; flex:0 0 14px; margin-left:4px; margin-right:4px;
        }}
        .legend-count {{
            font-weight:800; color:{AZUL_OPS}; width:2rem;
            text-align:right; justify-self:end; line-height:1;
        }}
'''
if css_marker in legacy and '.legend-card {' not in legacy:
    legacy = legacy.replace(css_marker, css_extra, 1)

old_legend = '''with col_resumen:
    st.markdown('<div class="summary-card"><div class="summary-title">Principales amenazas</div>', unsafe_allow_html=True)
    for nombre, (col, icono) in AMENAZAS.items():
        n = int(filtrado[col].sum()) if col in filtrado.columns else 0
        st.markdown(
            f'<div class="threat-row"><span class="threat-label">{amenaza_icon_html(nombre)}{html.escape(nombre)}</span><span class="threat-count">{n}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="summary-card"><div class="summary-title">Nivel de prioridad</div>', unsafe_allow_html=True)
    for p in ORDEN_PRIORIDAD:
        n = int((filtrado["prioridad"] == p).sum())
        txt_color = "#5D4B00" if p == "Baja" else COLORES_PRIORIDAD[p]
        st.markdown(
            f'<div class="threat-row"><span><span style="color:{COLORES_PRIORIDAD[p]};font-size:1.1rem">●</span> {html.escape(p)}</span><span class="threat-count" style="color:{txt_color}">{n}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
'''
new_legend = '''with col_resumen:
    filas_amenazas = []
    for nombre, (col, icono) in AMENAZAS.items():
        n = int(filtrado[col].sum()) if col in filtrado.columns else 0
        filas_amenazas.append(
            f'<div class="legend-row">'
            f'<div class="legend-label">{amenaza_icon_html(nombre, size=22)}<span>{html.escape(nombre)}</span></div>'
            f'<div class="legend-count">{n}</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="legend-card">'
        '<div class="legend-title">Principales amenazas</div>'
        '<div class="legend-body">' + ''.join(filas_amenazas) + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    filas_prioridad = []
    for p in ORDEN_PRIORIDAD:
        n = int((filtrado["prioridad"] == p).sum())
        txt_color = "#5D4B00" if p == "Baja" else COLORES_PRIORIDAD[p]
        filas_prioridad.append(
            f'<div class="legend-row">'
            f'<div class="legend-label"><span class="priority-dot" style="background:{COLORES_PRIORIDAD[p]}"></span><span>{html.escape(p)}</span></div>'
            f'<div class="legend-count" style="color:{txt_color}">{n}</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="legend-card">'
        '<div class="legend-title">Nivel de prioridad</div>'
        '<div class="legend-body">' + ''.join(filas_prioridad) + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
'''
if old_legend in legacy:
    legacy = legacy.replace(old_legend, new_legend, 1)
elif 'filas_amenazas = []' not in legacy:
    raise RuntimeError('No se encontró el bloque lateral de leyendas para alinear')

# 5) Etiqueta más clara para el selector de pictogramas del mapa.
legacy = legacy.replace(
    '        "Iconos visibles",\n',
    '        "Seleccionar amenazas / impactos",\n',
    1,
)

# 6) Nombres resumidos más representativos para amenazas / impactos.
legacy = legacy.replace('    "Sequía / agua": "Agua",', '    "Sequía / agua": "Sequía",')
legacy = legacy.replace('    "Inundaciones / lluvias": "Lluvias",', '    "Inundaciones / lluvias": "Inundaciones",')
legacy = legacy.replace('    "Inseguridad alimentaria": "Alimentos",', '    "Inseguridad alimentaria": "Inseguridad alimentaria",')
legacy = legacy.replace('    "Afectación de servicios de salud": "Servicios",', '    "Afectación de servicios de salud": "Afectación servicios",')

# 7) En la matriz, partir el rótulo largo en dos líneas para que no se amontone.
legacy = legacy.replace(
    '    etiquetas = [AMENAZAS_CORTAS[n] for n in nombres]\n',
    '    etiquetas = [("Inseguridad<br>alimentaria" if n == "Inseguridad alimentaria" else AMENAZAS_CORTAS[n]) for n in nombres]\n',
    1,
)
legacy = legacy.replace(
    '    etiquetas = [("Inseguridad<br>alimentaria" if n == "Inseguridad alimentaria" else AMENAZAS_CORTAS[n]) for n in nombres]\n',
    '    etiquetas = [("Inseguridad<br>alimentaria" if n == "Inseguridad alimentaria" else "Afectación<br>servicios" if n == "Afectación de servicios de salud" else AMENAZAS_CORTAS[n]) for n in nombres]\n',
    1,
)

# 8) Dar más aire entre los rótulos de la matriz y los pictogramas.
# El rótulo de "Inseguridad alimentaria" ocupa dos líneas, por lo que todos
# los iconos se bajan a una misma línea base y se amplía el margen inferior.
legacy = legacy.replace(
    '        margin=dict(l=0, r=4, t=8, b=82),\n',
    '        margin=dict(l=0, r=4, t=8, b=104),\n',
    1,
)
legacy = legacy.replace(
    '            x=(i + .5) / len(nombres), y=-.085,\n',
    '            x=(i + .5) / len(nombres), y=-.145,\n',
    1,
)

# 9) Reorganizar la leyenda inferior de la matriz:
# pictograma arriba y nombre debajo, con iconos un poco más grandes.
legacy = legacy.replace(
    '        margin=dict(l=0, r=4, t=8, b=104),\n',
    '        margin=dict(l=0, r=4, t=8, b=138),\n',
    1,
)
legacy = legacy.replace(
    '    fig.update_xaxes(side="bottom", tickangle=0, tickfont=dict(size=10), showgrid=False)\n',
    '    fig.update_xaxes(side="bottom", showticklabels=False, ticks="", showgrid=False)\n',
    1,
)
legacy = legacy.replace(
    '            x=(i + .5) / len(nombres), y=-.145,\n',
    '            x=(i + .5) / len(nombres), y=-.072,\n',
    1,
)
legacy = legacy.replace(
    '            sizex=.038, sizey=.038,\n',
    '            sizex=.072, sizey=.072,\n',
    1,
)
legacy = legacy.replace(
    '            sizex=.052, sizey=.052,\n',
    '            sizex=.072, sizey=.072,\n',
    1,
)
legacy = legacy.replace(
    '            sizex=.060, sizey=.060,\n',
    '            sizex=.072, sizey=.072,\n',
    1,
)

# Añadir los nombres debajo de cada pictograma.
annotation_marker = '''        ))
    return fig


def evolucion_prioridad(base):'''
annotation_block = '''        ))
        etiqueta = etiquetas[i]
        fig.add_annotation(
            x=(i + .5) / len(nombres),
            y=-.155,
            xref="paper", yref="paper",
            text=etiqueta,
            showarrow=False,
            xanchor="center", yanchor="top",
            align="center",
            font=dict(size=10, color="#6F7589"),
        )
    return fig


def evolucion_prioridad(base):'''
if annotation_marker in legacy and 'y=-.155' not in legacy:
    legacy = legacy.replace(annotation_marker, annotation_block, 1)

p.write_text(legacy, encoding="utf-8")
print("OK: matriz con iconos arriba, nombres abajo e iconos ampliados")
