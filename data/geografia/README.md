# Geografía

El archivo utilizado por el mapa es:

`data/geografia/paises_americas.gpkg`

Se genera automáticamente con `scripts/preparar_geografia.py` a partir de **Natural Earth Admin 0 Countries, escala 1:50m**.

Campos principales:

- `COUNTRY`: nombre del país o territorio.
- `ISO_CC`: código ISO3 usado para unir la geometría con la base maestra.
- `CONTINENT`: continente (`North America` o `South America`).
- `geometry`: geometría del país/territorio en EPSG:4326.

El proceso conserva las geometrías multipartes disponibles en Natural Earth y filtra únicamente las Américas. El workflow de GitHub Actions vuelve a generar este GeoPackage antes de producir cada mapa.

Natural Earth es un conjunto de datos cartográficos de dominio público.
