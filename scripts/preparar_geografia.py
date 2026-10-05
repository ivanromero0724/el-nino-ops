from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parents[1]
SALIDA = BASE / "data" / "geografia" / "paises_americas.gpkg"
TMP = BASE / "data" / "geografia" / "_natural_earth_50m.geojson"

URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)


def main():
    SALIDA.parent.mkdir(parents=True, exist_ok=True)

    print("Descargando Natural Earth 1:50m...")
    urlretrieve(URL, TMP)

    mundo = gpd.read_file(TMP)
    requeridas = {"ADMIN", "ISO_A3", "CONTINENT", "geometry"}
    faltan = requeridas - set(mundo.columns)
    if faltan:
        raise ValueError(f"Faltan campos en Natural Earth: {sorted(faltan)}")

    americas = mundo[mundo["CONTINENT"].isin(["North America", "South America"])].copy()

    # Natural Earth incorpora Guayana Francesa dentro de la geometría de Francia,
    # cuyo continente es Europa. Se extrae únicamente el componente sudamericano
    # para que aparezca en los mapas regionales sin añadir Francia metropolitana.
    francia = mundo[mundo["ADMIN"].astype(str).str.lower().eq("france")].copy()
    if not francia.empty:
        partes = francia[["geometry"]].explode(index_parts=False).reset_index(drop=True)
        puntos = partes.geometry.representative_point()
        guayana = partes[
            puntos.x.between(-60, -45)
            & puntos.y.between(0, 10)
        ].copy()
        if not guayana.empty:
            fila = francia.iloc[[0]].copy()
            fila["ADMIN"] = "Guayana Francesa"
            fila["ISO_A3"] = "GUF"
            fila["CONTINENT"] = "South America"
            fila.geometry = [guayana.geometry.unary_union]
            americas = gpd.GeoDataFrame(
                pd.concat([americas, fila], ignore_index=True),
                crs=mundo.crs,
            )
            print("Guayana Francesa incluida como GUF")
        else:
            print("⚠️ No se pudo aislar la geometría de Guayana Francesa")

    americas["ISO_CC"] = americas["ISO_A3"].astype(str)

    # Fallback para casos donde Natural Earth usa -99 en ISO_A3.
    if "ISO_A3_EH" in americas.columns:
        mask = americas["ISO_CC"].isin(["-99", "nan", "None", ""])
        americas.loc[mask, "ISO_CC"] = americas.loc[mask, "ISO_A3_EH"].astype(str)

    americas = americas.rename(columns={"ADMIN": "COUNTRY"})
    americas = americas[["COUNTRY", "ISO_CC", "CONTINENT", "geometry"]]
    americas = americas.to_crs("EPSG:4326")

    if SALIDA.exists():
        SALIDA.unlink()

    americas.to_file(SALIDA, layer="paises_americas", driver="GPKG")
    TMP.unlink(missing_ok=True)

    print(f"GeoPackage: {SALIDA}")
    print(f"Registros: {len(americas)}")


if __name__ == "__main__":
    main()
