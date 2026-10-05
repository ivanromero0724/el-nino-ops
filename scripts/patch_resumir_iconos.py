from pathlib import Path
import re

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# 1) Helper para condensar amenazas en una sola burbuja por país.
if "def resumen_iconos_pais" not in txt:
    anchor = '''    return salida\n\n\ndef posiciones_pais'''
    helper = '''    return salida\n\n\ndef resumen_iconos_pais(fila, seleccion=None, max_iconos=2):\n    activas = amenazas_de_fila(fila, seleccion)\n    if not activas:\n        return None, []\n\n    iconos = [icono for _, icono in activas]\n    nombres = [nombre for nombre, _ in activas]\n\n    etiqueta = "".join(iconos[:max_iconos])\n    extra = len(iconos) - max_iconos\n    if extra > 0:\n        etiqueta += f"+{extra}"\n\n    return etiqueta, nombres\n\n\ndef posiciones_pais'''
    if anchor not in txt:
        raise RuntimeError("No se encontró el punto de inserción para resumen_iconos_pais")
    txt = txt.replace(anchor, helper, 1)

# 2) Sustituir múltiples círculos por una sola burbuja resumen por país.
patron = re.compile(r'''    if mostrar_amenazas:\n.*?\n    fig\.update_geos\(''', re.S)
reemplazo = '''    if mostrar_amenazas:\n        if amenazas_visibles is None:\n            amenazas_visibles = list(AMENAZAS.keys())\n\n        posiciones = posiciones_pais(geo)\n        lon_list, lat_list, text_list, hover_list, size_list = [], [], [], [], []\n\n        for _, fila in datos_filtrados.iterrows():\n            iso = str(fila.get("iso3", ""))\n            if iso not in posiciones:\n                continue\n\n            etiqueta, nombres = resumen_iconos_pais(\n                fila,\n                seleccion=amenazas_visibles,\n                max_iconos=2,\n            )\n            if not etiqueta:\n                continue\n\n            lon0, lat0 = posiciones[iso]\n            detalle = "<br>".join(\n                f"{AMENAZAS[n][1]} {html.escape(n)}" for n in nombres\n            )\n\n            lon_list.append(lon0)\n            lat_list.append(lat0)\n            text_list.append(etiqueta)\n            hover_list.append(\n                f"<b>{html.escape(texto(fila.get('pais'), iso))}</b><br>{detalle}"\n            )\n            size_list.append(38 if len(nombres) > 2 else 34)\n\n        if lon_list:\n            fig.add_trace(\n                go.Scattergeo(\n                    lon=lon_list,\n                    lat=lat_list,\n                    mode="markers+text",\n                    marker=dict(\n                        size=size_list,\n                        color="rgba(255,255,255,.97)",\n                        line=dict(color="rgba(0,75,135,.55)", width=1.3),\n                    ),\n                    text=text_list,\n                    textposition="middle center",\n                    textfont=dict(size=13, color=TEXTO),\n                    hovertext=hover_list,\n                    hovertemplate="%{hovertext}<extra></extra>",\n                    hoverlabel=dict(\n                        bgcolor="white",\n                        font_size=12,\n                        font_color=TEXTO,\n                    ),\n                    showlegend=False,\n                )\n            )\n\n    fig.update_geos('''

txt, n = patron.subn(reemplazo, txt, count=1)
if n != 1:
    raise RuntimeError(f"No se pudo reemplazar el bloque de iconos; coincidencias={n}")

# 3) Actualizar la nota para explicar la burbuja resumen.
old_note = "El color del país representa la prioridad. Los iconos muestran amenazas / impactos reportados. Estos controles solo cambian la visualización del mapa."
new_note = "El color del país representa la prioridad. Cada burbuja resume las amenazas / impactos reportados por país; al pasar el cursor se ve el detalle completo. Estos controles solo cambian la visualización del mapa."
if old_note in txt:
    txt = txt.replace(old_note, new_note, 1)

p.write_text(txt, encoding="utf-8")
print("Iconos del mapa resumidos a una burbuja por país")
