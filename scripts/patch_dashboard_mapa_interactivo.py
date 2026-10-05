from pathlib import Path
import re

# Corrige definitivamente las etiquetas del mapa interactivo. TextLayer ha sido
# inestable en Streamlit Cloud, por lo que los nombres de país se rasterizan a
# PNG transparente y se dibujan con IconLayer (la misma tecnología que ya está
# funcionando para los pictogramas de amenazas).

p = Path("app.py")
txt = p.read_text(encoding="utf-8")

# Dependencias para generar etiquetas PNG con tildes/ñ usando DejaVu Sans,
# incluida con Matplotlib.
if "from PIL import Image, ImageDraw, ImageFont" not in txt:
    txt = txt.replace(
        "import matplotlib.pyplot as plt\n",
        "import matplotlib.pyplot as plt\nfrom matplotlib import font_manager\nfrom PIL import Image, ImageDraw, ImageFont\n",
        1,
    )

# Helper robusto para nombres de país. Se cachea para no regenerar imágenes en
# cada rerun de Streamlit.
if "def _label_data_uri(" not in txt:
    helper = '''\n\ndef _label_data_uri(texto):\n    \"\"\"Rasteriza una etiqueta de país con soporte completo de tildes/ñ.\"\"\"\n    texto = str(texto or \"\")\n    cache = getattr(_label_data_uri, \"_cache\", {})\n    if texto in cache:\n        return cache[texto]\n\n    font_path = font_manager.findfont(\n        font_manager.FontProperties(family=\"DejaVu Sans\", weight=\"bold\")\n    )\n    font = ImageFont.truetype(font_path, 26)\n    tmp = Image.new(\"RGBA\", (8, 8), (0, 0, 0, 0))\n    draw = ImageDraw.Draw(tmp)\n    bbox = draw.textbbox((0, 0), texto, font=font)\n    pad_x, pad_y = 5, 4\n    width = max(8, bbox[2] - bbox[0] + 2 * pad_x)\n    height = max(8, bbox[3] - bbox[1] + 2 * pad_y)\n\n    img = Image.new(\"RGBA\", (width, height), (0, 0, 0, 0))\n    draw = ImageDraw.Draw(img)\n    draw.text(\n        (pad_x - bbox[0], pad_y - bbox[1]),\n        texto,\n        font=font,\n        fill=(0, 62, 120, 255),\n    )\n\n    buffer = BytesIO()\n    img.save(buffer, format=\"PNG\")\n    uri = \"data:image/png;base64,\" + base64.b64encode(buffer.getvalue()).decode(\"ascii\")\n    resultado = (uri, width, height)\n    cache[texto] = resultado\n    _label_data_uri._cache = cache\n    return resultado\n'''
    txt = txt.replace("\n\ndef _amenazas_activas", helper + "\n\ndef _amenazas_activas", 1)

# Sustituir la construcción de etiquetas para que cada nombre tenga su propia
# imagen transparente y conserve las propiedades de hover/click.
patron_append = re.compile(
    r'''        etiquetas\.append\(\{\n'''
    r'''            \"position\": \[x, y\],\n'''
    r'''            \"pais\": nombre_pais,\n'''
    r'''            \"properties\": _props_popup\(\n'''
    r'''                nombre_pais,\n'''
    r'''                \"Amenazas / impactos\",\n'''
    r'''                \"Pasa el cursor sobre los pictogramas para ver el detalle\.\",\n'''
    r'''            \),\n'''
    r'''        \}\)\n''',
    re.S,
)
nuevo_append = '''        label_uri, label_w, label_h = _label_data_uri(nombre_pais)\n        etiquetas.append({\n            \"position\": [x, y],\n            \"icon\": {\n                \"url\": label_uri,\n                \"width\": label_w,\n                \"height\": label_h,\n                \"anchorX\": 0,\n                \"anchorY\": label_h / 2,\n            },\n            \"size\": 18,\n            \"properties\": _props_popup(\n                nombre_pais,\n                \"Amenazas / impactos\",\n                \"Pasa el cursor sobre los pictogramas para ver el detalle.\",\n            ),\n        })\n'''
if patron_append.search(txt):
    txt = patron_append.sub(nuevo_append, txt, count=1)

# Si ya fue aplicada parcialmente, no volver a tocar el bloque.
if 'id="etiquetas-paises"' in txt and '"TextLayer"' in txt:
    patron_layer = re.compile(
        r'''    if etiquetas:\n'''
        r'''        capas\.append\(\n'''
        r'''            pdk\.Layer\(\n'''
        r'''                \"TextLayer\",.*?'''
        r'''        \)\n'''
        r'''    if iconos:\n''',
        re.S,
    )
    nuevo_layer = '''    if etiquetas:\n        capas.append(\n            pdk.Layer(\n                \"IconLayer\",\n                etiquetas,\n                id=\"etiquetas-paises\",\n                get_icon=\"icon\",\n                get_position=\"position\",\n                get_size=\"size\",\n                size_units=\"pixels\",\n                size_scale=1,\n                size_min_pixels=17,\n                size_max_pixels=20,\n                pickable=True,\n            )\n        )\n    if iconos:\n'''
    if not patron_layer.search(txt):
        raise RuntimeError("No se encontró el TextLayer de etiquetas para reemplazar")
    txt = patron_layer.sub(nuevo_layer, txt, count=1)

# Iconos inmediatamente debajo del nombre del país; la separación se mantiene
# en píxeles al hacer zoom o mover el mapa.
txt = re.sub(
    r'                \"pixel_offset\": \[[^\]]+\],\n',
    '                \"pixel_offset\": [i * 24, 22],\n',
    txt,
    count=1,
)

p.write_text(txt, encoding="utf-8")
print("OK: nombres de países renderizados con IconLayer y soporte de tildes/ñ")
