# El Niño - OPS

Repositorio para el monitoreo mensual del fenómeno de El Niño y sus implicaciones para la salud pública en la Región de las Américas.

## Estructura

- `data/base_maestra_elnino.csv`: base longitudinal maestra. Cada fila representa un país/territorio en un SitRep.
- `data/geografia/paises_americas.gpkg`: GeoPackage de países y territorios de las Américas usado por el mapa y el dashboard.
- `scripts/preparar_geografia.py`: genera el GeoPackage regional a partir de Natural Earth 1:50m.
- `scripts/mapa_sitrep.py`: genera el mapa estático de prioridad sanitaria y amenazas/impactos directamente desde la base maestra.
- `app.py`: dashboard regional interactivo en Streamlit.
- `.streamlit/config.toml`: tema visual del dashboard basado en la línea gráfica OPS/OMS.
- `outputs/mapas/`: PNG y PDF generados para cada SitRep.
- `.github/workflows/generar_mapa.yml`: automatización que prepara la geografía, genera el mapa y versiona los productos.
- `.github/workflows/validar_dashboard.yml`: valida sintaxis, dependencias y carga del dashboard.
- `requirements.txt`: dependencias de Python.

## Base maestra

La base mantiene una sola tabla. Para cada actualización mensual se agregan nuevas filas y se conservan los SitRep anteriores.

La llave temporal es `sitrep_id`; dentro de cada SitRep debe existir una sola fila por `iso3`.

Las variables `icono_agua`, `icono_inundaciones`, `icono_incendios`, `icono_alimentos`, `icono_arbovirosis`, `icono_respiratorio` e `icono_servicios` usan valores 0/1 y alimentan directamente los iconos del mapa y la matriz de amenazas del dashboard.

## Dashboard regional

El dashboard se alimenta directamente de `data/base_maestra_elnino.csv` y `data/geografia/paises_americas.gpkg`. No requiere una base paralela.

La vista inicial incluye:

- selector de SitRep/fecha;
- filtros por subregión, prioridad y amenaza/impacto;
- indicadores regionales;
- mapa interactivo de prioridad sanitaria;
- resumen de amenazas e impactos;
- prioridad por subregión;
- matriz país × amenaza;
- evolución temporal, que se activa automáticamente cuando existan dos o más SitRep;
- ficha detallada por país con amenazas, impactos, alistamiento, acciones OPS/OMS y cifras disponibles.

Para ejecutarlo localmente:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para desplegarlo en Streamlit Community Cloud, seleccionar este repositorio, la rama `main` y `app.py` como archivo principal. La actualización mensual del CSV se reflejará automáticamente en el tablero al reiniciarse la aplicación.

## Actualización mensual

1. Agregar a `data/base_maestra_elnino.csv` una nueva fila por país/territorio para el nuevo SitRep, sin reemplazar registros anteriores.
2. Incrementar `sitrep_numero`, crear un nuevo `sitrep_id` y actualizar `fecha_publicacion` y `fecha_corte`.
3. Actualizar prioridad, estado de monitoreo, declaratoria, atribución, textos, cifras e indicadores `icono_*`.
4. Hacer commit/push de la base actualizada.

El workflow `Generar mapa SitRep` se ejecuta automáticamente cuando cambia la base maestra, el código cartográfico o la configuración relacionada. El workflow:

1. instala las dependencias;
2. genera `data/geografia/paises_americas.gpkg`;
3. ejecuta `scripts/mapa_sitrep.py`;
4. guarda el PNG y el PDF en `outputs/mapas/`;
5. hace commit automático de los productos generados.

También puede ejecutarse manualmente desde **Actions → Generar mapa SitRep → Run workflow**.

## Ejecución local del mapa

```bash
pip install -r requirements.txt
python scripts/preparar_geografia.py
python scripts/mapa_sitrep.py
```

Por defecto el script toma automáticamente el SitRep con el número más alto y, dentro de este, la fecha de corte más reciente. Para reproducir un corte específico puede fijarse `SITREP_ID` dentro del script.

## Geografía

La geografía regional se genera a partir de Natural Earth Admin 0 Countries, escala 1:50m. El archivo final conserva `COUNTRY`, `ISO_CC`, `CONTINENT` y `geometry`, en EPSG:4326. La unión con la base se realiza mediante `iso3` ↔ `ISO_CC`.
