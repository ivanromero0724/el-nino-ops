# Geografía

El archivo utilizado por el mapa es:

`data/geografia/paises_americas.gpkg`

Se genera con `scripts/preparar_geografia.py` a partir de **Natural Earth Admin 0 Countries, escala 1:50m**.

Campos principales:

- `COUNTRY`: nombre del país o territorio.
- `ISO_CC`: código ISO3 usado para unir la geometría con la base maestra.
- `CONTINENT`: continente (`North America` o `South America`).
- `geometry`: geometría del país/territorio en EPSG:4326.

El proceso conserva las geometrías multipartes disponibles en Natural Earth y filtra únicamente las Américas. El GeoPackage se versiona en el repositorio y solo se reconstruye cuando es necesario actualizar la geografía; el workflow del mapa usa directamente este archivo.

Natural Earth es un conjunto de datos cartográficos de dominio público.
