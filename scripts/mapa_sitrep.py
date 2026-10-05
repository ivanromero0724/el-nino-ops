from pathlib import Path
import math
import os
import hashlib

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Ellipse, PathPatch, Polygon
from matplotlib.path import Path as MplPath
from matplotlib.offsetbox import AnnotationBbox, DrawingArea, OffsetImage, HPacker
from PIL import Image, ImageChops

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE = Path(__file__).resolve().parents[1]
RUTA_BASE = BASE / "data" / "base_maestra_elnino.csv"
RUTA_GPKG = BASE / "data" / "geografia" / "paises_americas.gpkg"
SALIDA_DIR = BASE / "outputs" / "mapas"
SALIDA_DIR.mkdir(parents=True, exist_ok=True)

# None = toma automáticamente el SitRep más reciente de la base.
SITREP_ID = None

POSIBLES_LOGOS = [
    BASE / "assets" / "ops_oms.png",
    BASE / "ops_oms.png",
    BASE / "ops_oms(1).png",
]
RUTA_LOGO = next((p for p in POSIBLES_LOGOS if p.exists()), None)

# ============================================================
# ESTILO OPS
# ============================================================
AZUL_OPS = "#004B87"
AZUL_LINEA = "#075594"
AZUL_MAR = "#D9EEF7"
AZUL_OCEANO = "#1592D2"
BLANCO = "#FFFFFF"
GRIS_BASE = "#CACACA"
GRIS_LEYENDA = "#BDBDBD"
TEXTO = "#003E78"
BORDE_PANEL = "#70B8E8"

COLORES_PRIORIDAD = {
    "Alta": "#D71920",
    "Media": "#FF8618",
    "Baja": "#F6C344",
}

COLORES_AMENAZA = {
    "agua": "#168BC9",
    "inundaciones": "#1576B8",
    "incendios": "#F36C21",
    "alimentos": "#F5A623",
    "arbovirosis": "#008877",
    "respiratorio": "#7851A9",
    "servicios": "#0067B1",
}

ETIQUETAS_AMENAZA = {
    "agua": "Sequía / agua",
    "inundaciones": "Inundaciones / lluvias",
    "incendios": "Incendios / quemadas",
    "alimentos": "Inseguridad alimentaria",
    "arbovirosis": "Dengue / otras arbovirosis",
    "respiratorio": "Calidad del aire / riesgo respiratorio",
    "servicios": "Afectación de servicios de salud",
}

MAPEO_ICONOS = {
    "icono_agua": "agua",
    "icono_inundaciones": "inundaciones",
    "icono_incendios": "incendios",
    "icono_alimentos": "alimentos",
    "icono_arbovirosis": "arbovirosis",
    "icono_respiratorio": "respiratorio",
    "icono_servicios": "servicios",
}

# ============================================================
# POSICIONES DEL MAPA / CALLOUTS
# ============================================================
LABELS = {
    "MEX": (-96.5, 28.5, "México"),
    "GTM": (-121.0, 29.0, "Guatemala"),
    "HND": (-121.0, 21.3, "Honduras"),
    "SLV": (-121.0, 13.7, "El Salvador"),
    "CRI": (-121.0, 6.1, "Costa Rica"),
    "PAN": (-74.5, 16.0, "Panamá"),
    "COL": (-100.0, -1.3, "Colombia"),
    "ECU": (-100.0, -8.7, "Ecuador"),
    "PER": (-100.0, -17.0, "Perú"),
    "BOL": (-87.0, -28.7, "Bolivia"),
    "BRA": (-44.0, -7.3, "Brasil"),
    "CHL": (-113.0, -37.0, "Chile"),
    "ARG": (-47.0, -36.0, "Argentina"),
    "PRY": (-47.0, -24.5, "Paraguay"),
    "URY": (-47.0, -45.0, "Uruguay"),
    "JAM": (-81.5, 29.2, "Jamaica"),
    "PRI": (-68.8, 29.2, "Puerto Rico"),
    "TTO": (-59.0, 20.5, "Trinidad y Tobago"),
}

TARGET = {
    "MEX": (-102.0, 23.5), "GTM": (-90.4, 15.7), "HND": (-86.7, 14.8),
    "SLV": (-88.9, 13.7), "CRI": (-84.2, 9.8), "PAN": (-80.3, 8.5),
    "COL": (-74.5, 4.2), "ECU": (-78.4, -1.5), "PER": (-75.5, -9.5),
    "BOL": (-64.8, -16.8), "BRA": (-52.0, -10.0), "CHL": (-71.2, -33.5),
    "ARG": (-63.5, -34.5), "PRY": (-58.4, -23.4), "URY": (-56.0, -32.8),
    "JAM": (-77.3, 18.2), "PRI": (-66.4, 18.2), "TTO": (-61.2, 10.5),
}

ROUTES = {
    "MEX": [(-90.0, 25.4), (-94.0, 25.0), (-98.0, 24.3), TARGET["MEX"]],
    "GTM": [(-108.0, 25.9), (-99.0, 25.0), (-94.0, 20.8), TARGET["GTM"]],
    "HND": [(-108.0, 18.2), (-99.0, 17.5), (-93.0, 16.0), TARGET["HND"]],
    "SLV": [(-108.0, 10.6), (-99.0, 10.8), (-94.0, 12.4), TARGET["SLV"]],
    "CRI": [(-108.0, 3.0), (-99.0, 3.8), (-93.0, 5.5), (-88.0, 7.8), TARGET["CRI"]],
    "PAN": [(-76.0, 13.1), (-77.2, 12.3), (-78.5, 10.8), (-79.4, 9.5), TARGET["PAN"]],
    "COL": [(-86.0, -1.5), (-81.0, -1.5), (-77.5, 1.0), TARGET["COL"]],
    "ECU": [(-88.0, -9.0), (-82.0, -9.0), (-77.0, -6.2), (-77.0, -3.5), TARGET["ECU"]],
    "PER": [(-87.0, -17.3), (-81.5, -17.3), (-78.5, -12.0), TARGET["PER"]],
    "BOL": [(-78.0, -28.8), (-71.5, -28.8), (-67.5, -21.5), TARGET["BOL"]],
    "BRA": [(-45.0, -8.1), (-48.5, -8.1), TARGET["BRA"]],
    "CHL": [(-100.0, -39.5), (-84.0, -39.5), (-75.0, -35.5), TARGET["CHL"]],
    "ARG": [(-48.0, -36.5), (-55.0, -36.5), TARGET["ARG"]],
    "PRY": [(-48.0, -25.0), (-53.0, -25.0), TARGET["PRY"]],
    "URY": [(-48.0, -45.5), (-52.5, -42.0), (-54.5, -36.0), TARGET["URY"]],
    "JAM": [(-76.8, 28.0), (-76.8, 23.0), TARGET["JAM"]],
    "PRI": [(-64.8, 28.0), (-65.4, 23.0), TARGET["PRI"]],
    "TTO": [(-58.0, 19.5), (-59.0, 16.4), TARGET["TTO"]],
}

TAMANOS_ICONOS = {"MEX": 24, "GTM": 25, "COL": 23, "PER": 23, "ECU": 24}
DESPLAZAMIENTO_ICONOS_X = {"COL": -6.0}
DESPLAZAMIENTO_ICONOS_Y = -3.0

# ============================================================
# CARGA DE LA BASE
# ============================================================
def cargar_sitrep():
    if not RUTA_BASE.exists():
        raise FileNotFoundError(f"No se encontró la base maestra: {RUTA_BASE}")

    base = pd.read_csv(RUTA_BASE, encoding="utf-8")
    requeridas = ["sitrep_id", "sitrep_numero", "fecha_corte", "iso3", "pais", "prioridad", *MAPEO_ICONOS]
    faltan = [c for c in requeridas if c not in base.columns]
    if faltan:
        raise ValueError("Faltan columnas en la base maestra: " + ", ".join(faltan))

    base["fecha_corte"] = pd.to_datetime(base["fecha_corte"], errors="coerce")
    base["sitrep_numero"] = pd.to_numeric(base["sitrep_numero"], errors="coerce")

    if SITREP_ID is None:
        n = base["sitrep_numero"].max()
        cand = base[base["sitrep_numero"] == n]
        f = cand["fecha_corte"].max()
        sitrep_id = cand.loc[cand["fecha_corte"] == f, "sitrep_id"].astype(str).iloc[0]
    else:
        sitrep_id = SITREP_ID

    s = base[base["sitrep_id"].astype(str) == str(sitrep_id)].copy()
    if s.empty:
        raise ValueError(f"No hay registros para {sitrep_id}")
    if s["iso3"].duplicated().any():
        dup = sorted(s.loc[s["iso3"].duplicated(False), "iso3"].astype(str).unique())
        raise ValueError("ISO3 duplicados dentro del SitRep: " + ", ".join(dup))

    for c in MAPEO_ICONOS:
        s[c] = pd.to_numeric(s[c], errors="coerce").fillna(0).astype(int)
        if not set(s[c].unique()).issubset({0, 1}):
            raise ValueError(f"{c} solo puede contener 0/1")

    validas = {"Alta", "Media", "Baja", "Sin priorización"}
    if not set(s["prioridad"].dropna()).issubset(validas):
        raise ValueError("Hay prioridades no reconocidas en la base maestra")

    def amenazas(fila):
        return [clave for col, clave in MAPEO_ICONOS.items() if fila[col] == 1]

    df = pd.DataFrame({
        "pais": s["pais"].astype(str),
        "iso": s["iso3"].astype(str).str.upper().str.strip(),
        "prioridad": s["prioridad"].astype(str).str.strip(),
    })
    df["amenazas"] = s.apply(amenazas, axis=1).tolist()

    return s, df, str(sitrep_id)

# ============================================================
# ICONOS VECTORIALES
# ============================================================
def segmento(x1, y1, x2, y2, ancho, color="white"):
    dx, dy = x2 - x1, y2 - y1
    longitud = math.hypot(dx, dy) or 1
    px, py = -dy / longitud * ancho / 2, dx / longitud * ancho / 2
    return Polygon([(x1+px,y1+py),(x2+px,y2+py),(x2-px,y2-py),(x1-px,y1-py)], closed=True, facecolor=color, edgecolor="none")

def base_icono(size, color):
    da = DrawingArea(size, size, 0, 0)
    r = size / 2
    da.add_artist(Circle((r, r), r-1, facecolor=color, edgecolor="white", linewidth=.8))
    return da

def icono_agua(size=27):
    da = base_icono(size, COLORES_AMENAZA["agua"])
    v=[(.50,.82),(.61,.67),(.70,.51),(.69,.37),(.68,.22),(.60,.13),(.50,.13),(.40,.13),(.32,.22),(.31,.37),(.30,.51),(.39,.67),(.50,.82),(.50,.82)]
    codes=[MplPath.MOVETO]+[MplPath.CURVE4]*12+[MplPath.CLOSEPOLY]
    da.add_artist(PathPatch(MplPath([(size*x,size*y) for x,y in v],codes),facecolor="white",edgecolor="none"))
    return da

def icono_incendios(size=27):
    da=base_icono(size,COLORES_AMENAZA["incendios"])
    pts=[(.50,.82),(.39,.63),(.42,.51),(.32,.38),(.37,.23),(.50,.14),(.63,.22),(.69,.38),(.60,.53),(.58,.67)]
    da.add_artist(Polygon([(size*x,size*y) for x,y in pts],closed=True,facecolor="white",edgecolor="none"))
    da.add_artist(Ellipse((size*.50,size*.34),size*.13,size*.22,facecolor=COLORES_AMENAZA["incendios"],edgecolor="none"))
    return da

def icono_inundaciones(size=27):
    da=base_icono(size,COLORES_AMENAZA["inundaciones"])
    for x,y,r in [(.38,.60,.09),(.51,.64,.13),(.64,.59,.09)]: da.add_artist(Circle((size*x,size*y),size*r,facecolor="white",edgecolor="none"))
    da.add_artist(Rectangle((size*.33,size*.51),size*.38,size*.10,facecolor="white",edgecolor="none"))
    for x in [.40,.52,.64]: da.add_artist(segmento(size*x,size*.43,size*(x-.035),size*.28,size*.04))
    return da

def icono_arbovirosis(size=27):
    da=base_icono(size,COLORES_AMENAZA["arbovirosis"])
    da.add_artist(Ellipse((size*.50,size*.47),size*.07,size*.23,facecolor="white",edgecolor="none"))
    da.add_artist(Circle((size*.50,size*.63),size*.035,facecolor="white",edgecolor="none"))
    for x,ang in [(.40,28),(.60,-28)]: da.add_artist(Ellipse((size*x,size*.54),size*.18,size*.075,angle=ang,fill=False,edgecolor="white",linewidth=.8))
    for x1,y1,x2,y2 in [(.47,.54,.29,.68),(.47,.48,.27,.48),(.47,.41,.30,.29),(.53,.54,.71,.68),(.53,.48,.73,.48),(.53,.41,.70,.29)]: da.add_artist(segmento(size*x1,size*y1,size*x2,size*y2,size*.025))
    da.add_artist(segmento(size*.50,size*.66,size*.50,size*.77,size*.025))
    return da

def icono_alimentos(size=27):
    da=base_icono(size,COLORES_AMENAZA["alimentos"])
    da.add_artist(segmento(size*.50,size*.19,size*.50,size*.75,size*.04))
    for yy,lado in [(.34,-1),(.42,1),(.50,-1),(.58,1),(.66,-1)]:
        xf=.50+lado*.12
        da.add_artist(segmento(size*.50,size*yy,size*xf,size*(yy+.055),size*.025))
        da.add_artist(Ellipse((size*xf,size*(yy+.055)),size*.08,size*.04,angle=35*lado,facecolor="white",edgecolor="none"))
    return da

def icono_respiratorio(size=27):
    da=base_icono(size,COLORES_AMENAZA["respiratorio"])
    da.add_artist(segmento(size*.50,size*.73,size*.50,size*.51,size*.055))
    da.add_artist(segmento(size*.50,size*.54,size*.42,size*.46,size*.045)); da.add_artist(segmento(size*.50,size*.54,size*.58,size*.46,size*.045))
    da.add_artist(Ellipse((size*.39,size*.37),size*.20,size*.34,angle=-8,facecolor="white",edgecolor="none")); da.add_artist(Ellipse((size*.61,size*.37),size*.20,size*.34,angle=8,facecolor="white",edgecolor="none"))
    return da

def icono_servicios(size=27):
    da=base_icono(size,COLORES_AMENAZA["servicios"])
    da.add_artist(Rectangle((size*.44,size*.25),size*.12,size*.50,facecolor="white",edgecolor="none")); da.add_artist(Rectangle((size*.25,size*.44),size*.50,size*.12,facecolor="white",edgecolor="none"))
    return da

ICONOS={"agua":icono_agua,"inundaciones":icono_inundaciones,"incendios":icono_incendios,"alimentos":icono_alimentos,"arbovirosis":icono_arbovirosis,"respiratorio":icono_respiratorio,"servicios":icono_servicios}

def poner_iconos(ax,x,y,amenazas,size=27):
    if not amenazas: return
    grupo=HPacker(children=[ICONOS[a](size) for a in amenazas],align="center",pad=0,sep=5)
    ax.add_artist(AnnotationBbox(grupo,(x,y),xycoords="data",frameon=False,box_alignment=(0,.5),zorder=25))

# ============================================================
# LOGO
# ============================================================
def recortar_logo(ruta):
    img=Image.open(ruta).convert("RGBA")
    bbox=img.getchannel("A").getbbox()
    if bbox: img=img.crop(bbox)
    fondo=Image.new("RGBA",img.size,(255,255,255,255))
    bbox=ImageChops.difference(img,fondo).convert("L").getbbox()
    return img.crop(bbox) if bbox else img

# ============================================================
# MAPA
# ============================================================
def main():
    seleccion, df, sitrep_id = cargar_sitrep()
    if not RUTA_GPKG.exists(): raise FileNotFoundError(f"No se encontró el GeoPackage: {RUTA_GPKG}")
    try: mundo=gpd.read_file(RUTA_GPKG,engine="pyogrio")
    except Exception: mundo=gpd.read_file(RUTA_GPKG)
    for c in ["ISO_CC","CONTINENT"]:
        if c not in mundo.columns: raise ValueError(f"El GeoPackage no contiene {c}")
    if mundo.crs is None: raise ValueError("El GeoPackage no tiene CRS definido")
    mundo=mundo.to_crs("EPSG:4326")
    americas=mundo[(mundo["CONTINENT"].isin(["North America","South America"])) | (mundo["ISO_CC"].isin(df["iso"]))].copy()

    prioridad_por_iso=df.set_index("iso")["prioridad"].to_dict(); amenazas_por_iso=df.set_index("iso")["amenazas"].to_dict()
    americas["prioridad"]=americas["ISO_CC"].map(prioridad_por_iso)
    faltan=set(df["iso"])-set(americas["ISO_CC"].dropna().astype(str))
    if faltan: print("⚠️ ISO no encontrados en el GeoPackage:",sorted(faltan))

    fecha=seleccion["fecha_corte"].max().strftime("%Y-%m-%d"); n=int(seleccion["sitrep_numero"].max())
    salida_pdf=SALIDA_DIR/f"Mapa_prioridades_amenazas_salud_El_Nino_OPS_SitRep{n:02d}_{fecha}.pdf"
    salida_png=SALIDA_DIR/f"Mapa_prioridades_amenazas_salud_El_Nino_OPS_SitRep{n:02d}_{fecha}.png"

    fig=plt.figure(figsize=(13,8.5),facecolor="white")
    fig.add_artist(Rectangle((.020,0),.620,1.0,transform=fig.transFigure,facecolor=AZUL_MAR,edgecolor="none",zorder=-10,clip_on=False))
    ax=fig.add_axes([.020,0,.620,1.0]); ax_leg=fig.add_axes([.655,.225,.310,.715]); ax_logo=fig.add_axes([.650,.005,.340,.220])
    ax.set_facecolor(AZUL_MAR); ax.set_xlim(-121.5,-31); ax.set_ylim(-58,37.5); ax.set_aspect("equal",adjustable="box")
    ax.add_patch(Rectangle((-121.5,-58),90.5,95.5,facecolor=AZUL_MAR,edgecolor="none",zorder=0))
    americas.plot(ax=ax,color=GRIS_BASE,edgecolor=BLANCO,linewidth=.46,zorder=1)
    for prioridad,color in COLORES_PRIORIDAD.items():
        sub=americas[americas["prioridad"]==prioridad]
        if not sub.empty: sub.plot(ax=ax,color=color,edgecolor=BLANCO,linewidth=.88,zorder=3)

    for iso,(x,y,nombre) in LABELS.items():
        ax.text(x,y,nombre,fontsize=8.6,fontweight="bold",color=TEXTO,ha="left",va="center",zorder=30)
        poner_iconos(ax,x+.15+DESPLAZAMIENTO_ICONOS_X.get(iso,0),y+DESPLAZAMIENTO_ICONOS_Y,amenazas_por_iso.get(iso,[]),size=TAMANOS_ICONOS.get(iso,26))
        ruta=ROUTES[iso]
        ax.plot([p[0] for p in ruta],[p[1] for p in ruta],color=AZUL_LINEA,linewidth=.70,solid_capstyle="round",solid_joinstyle="round",zorder=10)
        tx,ty=TARGET[iso]; ax.scatter([tx],[ty],s=10,color=AZUL_LINEA,zorder=11)

    ax.text(-110,-32.8,"O c é a n o\nP a c í f i c o",fontsize=8,fontstyle="italic",color=AZUL_OCEANO,ha="center")
    ax.text(-42,12,"O c é a n o\nA t l á n t i c o",fontsize=8,fontstyle="italic",color=AZUL_OCEANO,ha="center")
    ax.set_axis_off()

    ax_leg.set_xlim(0,1); ax_leg.set_ylim(0,1); ax_leg.axis("off")
    ax_leg.add_patch(FancyBboxPatch((.045,.025),.910,.950,boxstyle="round,pad=.012,rounding_size=.035",transform=ax_leg.transAxes,facecolor="#F8FCFE",edgecolor=BORDE_PANEL,linewidth=1))
    ax_leg.text(.105,.925,"Nivel de prioridad",fontsize=13.5,fontweight="bold",color=AZUL_OPS,transform=ax_leg.transAxes)
    prioridades=[("#D71920","Alta"),("#FF8618","Media"),("#F6C344","Baja"),(GRIS_LEYENDA,"Sin priorización")]
    for i,(color,texto) in enumerate(prioridades):
        yy=.840-i*.060
        ax_leg.scatter([.160],[yy],s=290,color=color,edgecolor="white",linewidth=.6,transform=ax_leg.transAxes,zorder=5)
        ax_leg.text(.255,yy,texto,fontsize=10,color=TEXTO,va="center",transform=ax_leg.transAxes)
    ax_leg.plot([.1,.9],[.585,.585],color=BORDE_PANEL,linewidth=.8,transform=ax_leg.transAxes)
    ax_leg.text(.105,.545,"Amenaza / impacto sanitario",fontsize=11.6,fontweight="bold",color=AZUL_OPS,transform=ax_leg.transAxes)
    orden=["agua","inundaciones","incendios","alimentos","arbovirosis","respiratorio","servicios"]
    for i,a in enumerate(orden):
        yy=.475-i*.061
        ax_leg.add_artist(AnnotationBbox(ICONOS[a](27),(.160,yy),xycoords=ax_leg.transAxes,frameon=False,box_alignment=(.5,.5)))
        ax_leg.text(.255,yy,ETIQUETAS_AMENAZA[a],fontsize=10,color=TEXTO,va="center",transform=ax_leg.transAxes)

    ax_logo.axis("off")
    if RUTA_LOGO:
        logo=np.asarray(recortar_logo(RUTA_LOGO))
        ax_logo.add_artist(AnnotationBbox(OffsetImage(logo,zoom=.50),(.5,.48),xycoords=ax_logo.transAxes,frameon=False,box_alignment=(.5,.5)))

    # Forzar el render final antes de exportar ambos formatos.
    fig.canvas.draw()

    # PNG: reemplazar explícitamente el archivo previo y validar el nuevo.
    salida_png.unlink(missing_ok=True)
    fig.savefig(salida_png, format="png", dpi=350, facecolor="white", bbox_inches="tight", pad_inches=0)
    with Image.open(salida_png) as im_png:
        im_png.verify()
    png_sha = hashlib.sha256(salida_png.read_bytes()).hexdigest()

    # Copia única por ejecución para evitar confundir una previsualización cacheada de GitHub.
    for viejo in SALIDA_DIR.glob(f"{salida_png.stem}_rev*.png"):
        viejo.unlink(missing_ok=True)
    revision = os.environ.get("GITHUB_RUN_NUMBER", "local")
    salida_png_revision = SALIDA_DIR / f"{salida_png.stem}_rev{revision}.png"
    salida_png_revision.write_bytes(salida_png.read_bytes())

    # PDF desde exactamente la misma figura y extensión.
    salida_pdf.unlink(missing_ok=True)
    fig.savefig(salida_pdf, format="pdf", facecolor="white", bbox_inches="tight", pad_inches=0)

    print(f"Extensión final: X={ax.get_xlim()} Y={ax.get_ylim()}")
    print(f"PNG SHA256: {png_sha}")
    print(f"PNG revisión: {salida_png_revision.resolve()}")
    plt.close(fig)

    print(f"SitRep: {sitrep_id}")
    print(f"Fecha de corte: {fecha}")
    print(f"Países/territorios: {len(df)}")
    print(f"PNG: {salida_png.resolve()}")
    print(f"PDF: {salida_pdf.resolve()}")

if __name__ == "__main__":
    main()
