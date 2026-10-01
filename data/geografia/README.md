# Geografía

El mapa espera el archivo:

`data/geografia/paises_americas.gpkg`

Campos requeridos:

- `ISO_CC`: código ISO3 usado para unir la geometría con la base maestra.
- `CONTINENT`: debe identificar al menos `North America` y `South America`.

Para el mapa regional conviene usar una versión recortada a las Américas y simplificada, conservando todas las partes relevantes de cada país/territorio. El script reproyecta automáticamente la capa a EPSG:4326.
