# El Niño - OPS

Repositorio para el monitoreo mensual del fenómeno de El Niño y sus implicaciones para la salud pública en la Región de las Américas.

## Estructura

- `data/base_maestra_elnino.xlsx`: base longitudinal maestra. Cada fila representa un país/territorio en un SitRep.
- `data/geografia/paises_americas.gpkg`: geometrías de países y territorios de las Américas usadas por el mapa.
- `scripts/mapa_sitrep.py`: genera el mapa de prioridad sanitaria y amenazas/impactos directamente desde la base maestra.
- `outputs/mapas/`: carpeta de salida esperada para los mapas generados (no es necesario versionar los productos si se generan localmente).

## Actualización mensual

1. Agregar a `data/base_maestra_elnino.xlsx` una nueva fila por país/territorio para el nuevo SitRep, sin reemplazar los registros anteriores.
2. Incrementar `sitrep_numero`, usar un nuevo `sitrep_id` y actualizar `fecha_publicacion` y `fecha_corte`.
3. Actualizar la prioridad, los siete indicadores binarios del mapa (`icono_*`) y los campos narrativos/cifras correspondientes.
4. Ejecutar `python scripts/mapa_sitrep.py`.

Por defecto el script selecciona automáticamente el SitRep con el número más alto y, dentro de este, la fecha de corte más reciente. También puede fijarse manualmente `SITREP_ID` dentro del script.

## Nota geográfica

El GeoPackage del repositorio contiene únicamente las geometrías de América del Norte y América del Sur y fue simplificado a 1 km para mantener el archivo liviano y apto para GitHub, conservando las múltiples geometrías/islas de cada país necesarias para la representación cartográfica regional.
