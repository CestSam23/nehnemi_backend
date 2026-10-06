from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from shapely.geometry import Point
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/nehnemi")

RUTAS = {
    "ageb": DATA / "AGEB Urbanas" / "poligono_ageb_urbanas_cdmx.shp",
    "viviendas": DATA / "Características de las viviendas" / "c_viviendas_ageb.shp",
    "ids": DATA / "Indice de desarrollo social a nivel AGEB" / "IDSAGEB.csv",
    "cfe": DATA / "Electrolineras.csv",
    "ventas_ev": DATA / "VentaDeEVPorEntidadFederativa.xlsx",
}

ALCALDIAS = {
    "002": "Azcapotzalco", "003": "Coyoacán", "004": "Cuajimalpa de Morelos",
    "005": "Gustavo A. Madero", "006": "Iztacalco", "007": "Iztapalapa",
    "008": "La Magdalena Contreras", "009": "Milpa Alta", "010": "Álvaro Obregón",
    "011": "Tláhuac", "012": "Tlalpan", "013": "Xochimilco", "014": "Benito Juárez",
    "015": "Cuauhtémoc", "016": "Miguel Hidalgo", "017": "Venustiano Carranza",
}


def normalizar(s: object) -> str:
    s = "" if pd.isna(s) else str(s).strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def leer_csv_robusto(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"No fue posible determinar la codificación de {path}")


def exigir_columnas(df: pd.DataFrame, columnas: set[str], fuente: str) -> None:
    faltantes = columnas - set(df.columns)
    if faltantes:
        raise ValueError(f"{fuente}: faltan columnas requeridas: {sorted(faltantes)}")


def percentil_estricto(s: pd.Series) -> pd.Series:
    """Porcentaje de valores válidos estrictamente menores. Los ceros empatados quedan en 0."""
    validos = s.dropna()
    if validos.empty:
        return pd.Series(np.nan, index=s.index)
    frecuencias = validos.value_counts().sort_index()
    menores = frecuencias.cumsum().shift(fill_value=0)
    mapa = (menores / len(validos) * 100).to_dict()
    return s.map(mapa)


def nivel(score: float | None) -> str | None:
    if score is None or pd.isna(score): return None
    if score < 25: return "MUY_BAJA"
    if score < 50: return "BAJA"
    if score < 75: return "MEDIA"
    return "ALTA"


def parse_numero(v):
    if pd.isna(v): return None
    s = str(v).strip().replace(",", ".")
    if normalizar(s) in {"", "sin dato", "-", "nan", "none"}: return None
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def cargar_fuentes() -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for nombre, ruta in RUTAS.items():
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró {nombre}: {ruta}")

    print("[1/6] Leyendo AGEB y viviendas...")
    ageb = gpd.read_file(RUTAS["ageb"]).to_crs(4326)
    viviendas = gpd.read_file(RUTAS["viviendas"]).to_crs(4326)
    exigir_columnas(ageb, {"CVEGEO", "CVE_MUN", "geometry"}, "AGEB")
    exigir_columnas(viviendas, {"ageb", "vvpr_hb", "vph_atm"}, "Viviendas")
    ageb["CVEGEO"] = ageb["CVEGEO"].astype(str).str.strip()
    viviendas["ageb"] = viviendas["ageb"].astype(str).str.strip()
    print(f"      ✓ {len(ageb):,} AGEB")

    print("[2/6] Leyendo IDS...")
    ids = leer_csv_robusto(RUTAS["ids"])
    if "folio_ageb" not in ids.columns:
        raise ValueError("IDSAGEB.csv no es el archivo por AGEB. Debe contener la columna 'folio_ageb'.")
    exigir_columnas(ids, {"folio_ageb", "idsm", "e_idsm"}, "IDS AGEB")
    ids["folio_ageb"] = ids["folio_ageb"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(13)
    ids = ids[ids["folio_ageb"] != "0000000000000"].copy()
    print(f"      ✓ {ids['folio_ageb'].nunique():,} claves AGEB con registro IDS")

    print("[3/6] Leyendo CFE...")
    cfe = leer_csv_robusto(RUTAS["cfe"])
    exigir_columnas(cfe, {"cons","nombre_estacion","direccion","latitude","longitude"}, "CFE")
    print(f"      ✓ {len(cfe):,} registros nacionales")

    print("[4/6] Leyendo ventas EV...")
    raw = pd.read_excel(RUTAS["ventas_ev"], header=None)
    fila_header = None
    for i, row in raw.iterrows():
        vals = [normalizar(x) for x in row.tolist()]
        if "ano" in vals and "mes" in vals and any("entidad federativa" in x for x in vals):
            fila_header = i; break
    if fila_header is None:
        raise ValueError("No se encontró la cabecera de ventas EV en el Excel de INEGI.")
    ventas = pd.read_excel(RUTAS["ventas_ev"], header=fila_header)
    ventas = ventas.iloc[:, :4].copy()
    ventas.columns = ["anio", "mes", "entidad", "unidades"]
    ventas["unidades"] = pd.to_numeric(ventas["unidades"], errors="coerce")
    ventas = ventas[ventas["anio"].notna() & ventas["mes"].notna() & ventas["entidad"].notna()].copy()
    ventas = ventas[ventas["entidad"].map(normalizar) == "ciudad de mexico"].copy()
    print(f"      ✓ {ventas['unidades'].notna().sum()} meses CDMX con valor numérico")
    return ageb, viviendas, ids, cfe, ventas


def transformar(ageb, viviendas, ids, cfe):
    print("[5/6] Cruzando y calculando métricas...")
    base = ageb.merge(viviendas[["ageb","vvpr_hb","vph_atm"]], left_on="CVEGEO", right_on="ageb", how="left")
    base = base.merge(ids[["folio_ageb","idsm","e_idsm"]], left_on="CVEGEO", right_on="folio_ageb", how="left")
    base["tenencia_auto"] = np.where(base["vvpr_hb"] > 0, base["vph_atm"] / base["vvpr_hb"], np.nan)

    lon = pd.to_numeric(cfe["longitude"], errors="coerce")
    lat = pd.to_numeric(cfe["latitude"], errors="coerce")
    estaciones = cfe[lon.notna() & lat.notna()].copy()
    estaciones["longitude"] = lon[lon.notna() & lat.notna()]
    estaciones["latitude"] = lat[lon.notna() & lat.notna()]
    estaciones = gpd.GeoDataFrame(estaciones, geometry=gpd.points_from_xy(estaciones.longitude, estaciones.latitude), crs=4326)
    estaciones = gpd.sjoin(estaciones, ageb[["CVEGEO","geometry"]], how="inner", predicate="within").drop(columns=["index_right"])

    grupos = []
    for idx, r in estaciones.iterrows():
        for n in range(1,6):
            cant = parse_numero(r.get(f"cargadores_{n:02d}"))
            if cant and cant > 0:
                grupos.append({"idx":idx,"numero_grupo":n,"cantidad":int(cant),
                    "tipo_conector":None if normalizar(r.get(f"tipo_{n:02d}")) in {"","sin dato"} else str(r.get(f"tipo_{n:02d}")).strip(),
                    "potencia_kw":parse_numero(r.get(f"potencia_{n:02d}"))})
    conectores = pd.DataFrame(grupos)
    if conectores.empty:
        conectores = pd.DataFrame(columns=["idx","numero_grupo","cantidad","tipo_conector","potencia_kw"])

    # Agregados por AGEB.
    estaciones["estaciones_carga"] = 1
    est_agg = estaciones.groupby("CVEGEO").agg(estaciones_carga=("estaciones_carga","sum")).reset_index()
    if not conectores.empty:
        tmp = conectores.merge(estaciones[["CVEGEO"]], left_on="idx", right_index=True, how="left")
        tmp["potencia_aportada"] = tmp["cantidad"] * tmp["potencia_kw"].fillna(0)
        con_agg = tmp.groupby("CVEGEO").agg(cargadores=("cantidad","sum"),potencia_total_kw=("potencia_aportada","sum")).reset_index()
    else:
        con_agg = pd.DataFrame(columns=["CVEGEO","cargadores","potencia_total_kw"])
    base = base.merge(est_agg,on="CVEGEO",how="left").merge(con_agg,on="CVEGEO",how="left")
    for c in ["estaciones_carga","cargadores","potencia_total_kw"]: base[c]=base[c].fillna(0)
    base["conectores_por_1000_viv_auto"] = np.where(base["vph_atm"]>0, base["cargadores"] / base["vph_atm"] * 1000, np.nan)

    # Distancia euclidiana en UTM 14N; aproximación territorial, no distancia vial.
    base_m = base.to_crs(32614)
    est_m = estaciones.to_crs(32614)
    cent = gpd.GeoDataFrame(base[["CVEGEO"]].copy(), geometry=base_m.geometry.centroid, crs=32614)
    if len(est_m):
        near = gpd.sjoin_nearest(cent, est_m[["geometry"]], how="left", distance_col="distancia_estacion_m")
        dist = near.groupby("CVEGEO")["distancia_estacion_m"].min()
        base["distancia_estacion_m"] = base["CVEGEO"].map(dist)
    else:
        base["distancia_estacion_m"] = np.nan

    base["cobertura_score"] = 100 - percentil_estricto(base["distancia_estacion_m"])
    base["capacidad_score"] = percentil_estricto(base["conectores_por_1000_viv_auto"])
    base["infraestructura_score"] = (base["cobertura_score"] + base["capacidad_score"]) / 2
    base["infraestructura_nivel"] = base["infraestructura_score"].map(nivel)

    base["ids_score"] = percentil_estricto(base["idsm"])
    base["tenencia_score"] = percentil_estricto(base["tenencia_auto"])
    base["accesibilidad_score"] = (base["ids_score"] + base["tenencia_score"]) / 2
    base["accesibilidad_nivel"] = base["accesibilidad_score"].map(nivel)

    print(f"      ✓ {len(estaciones):,} estaciones ubicadas espacialmente dentro de AGEB CDMX")
    print(f"      ✓ {base['accesibilidad_score'].notna().sum():,} AGEB con Accesibilidad calculable")
    print(f"      ✓ {base['infraestructura_score'].notna().sum():,} AGEB con Infraestructura calculable")
    return base, estaciones, conectores


def guardar_bd(base, estaciones, conectores, ventas, reiniciar=False):
    engine = create_engine(DATABASE_URL, future=True)
    with engine.begin() as cn:
        # Comprobar esquema.
        cn.execute(text("SELECT 1 FROM zonas LIMIT 1"))
        if reiniciar:
            cn.execute(text("TRUNCATE recomendaciones, evaluaciones_indicadores, interacciones, solicitudes_infraestructura, perfiles_ciudadanos, conectores_carga, estaciones_carga, observaciones, fuentes_datos, zonas RESTART IDENTITY CASCADE"))

        fuentes = [
            ("INEGI_CENSO_VIVIENDAS_AGEB_2020","INEGI Censo 2020 - características de viviendas por AGEB","OFICIAL","2020-01-01"),
            ("EVALUA_IDS_AGEB_2020","EVALÚA CDMX - Índice de Desarrollo Social por AGEB 2020","OFICIAL","2020-01-01"),
            ("CFE_ELECTROLINERAS","CFE - Electrolineras públicas en México","OFICIAL",None),
            ("INEGI_RAIAVL_EV","INEGI RAIAVL - ventas de vehículos eléctricos","OFICIAL",None),
            ("NEHNEMI_DERIVADO_V1","Nehnemi - métricas derivadas v1","DERIVADO",None),
        ]
        for clave,nombre,tipo,fecha in fuentes:
            cn.execute(text("""INSERT INTO fuentes_datos(clave,nombre,tipo_procedencia,fecha_referencia)
                VALUES(:c,:n,CAST(:t AS tipo_procedencia),:f)
                ON CONFLICT(clave) DO UPDATE SET nombre=EXCLUDED.nombre,tipo_procedencia=EXCLUDED.tipo_procedencia,fecha_referencia=EXCLUDED.fecha_referencia"""),{"c":clave,"n":nombre,"t":tipo,"f":fecha})
        fids=dict(cn.execute(text("SELECT clave,id FROM fuentes_datos")).all())

        # CDMX y alcaldías derivadas de la geometría AGEB.
        geom_cdmx = base.geometry.union_all()
        cn.execute(text("""INSERT INTO zonas(clave,tipo,nombre,geometria) VALUES('09','CDMX','Ciudad de México',ST_Multi(ST_GeomFromText(:wkt,4326)))
            ON CONFLICT(clave) DO UPDATE SET nombre=EXCLUDED.nombre, geometria=EXCLUDED.geometria, actualizado_en=now()"""),{"wkt":geom_cdmx.wkt})
        cdmx_id=cn.execute(text("SELECT id FROM zonas WHERE clave='09'")).scalar_one()
        for mun,nombre in ALCALDIAS.items():
            sub=base[base["CVE_MUN"].astype(str).str.zfill(3)==mun]
            if sub.empty: continue
            clave="09"+mun
            cn.execute(text("""INSERT INTO zonas(clave,tipo,nombre,zona_padre_id,geometria) VALUES(:c,'ALCALDIA',:n,:p,ST_Multi(ST_GeomFromText(:wkt,4326)))
                ON CONFLICT(clave) DO UPDATE SET nombre=EXCLUDED.nombre,zona_padre_id=EXCLUDED.zona_padre_id,geometria=EXCLUDED.geometria,actualizado_en=now()"""),{"c":clave,"n":nombre,"p":cdmx_id,"wkt":sub.geometry.union_all().wkt})

        alcaldia_ids=dict(cn.execute(text("SELECT clave,id FROM zonas WHERE tipo='ALCALDIA'")).all())
        for _,r in base.iterrows():
            mun=str(r["CVE_MUN"]).zfill(3); padre=alcaldia_ids.get("09"+mun)
            cn.execute(text("""INSERT INTO zonas(clave,tipo,nombre,zona_padre_id,geometria) VALUES(:c,'AGEB',:n,:p,ST_Multi(ST_GeomFromText(:wkt,4326)))
                ON CONFLICT(clave) DO UPDATE SET nombre=EXCLUDED.nombre,zona_padre_id=EXCLUDED.zona_padre_id,geometria=EXCLUDED.geometria,actualizado_en=now()"""),
                {"c":r.CVEGEO,"n":f"AGEB {r.CVE_AGEB}","p":padre,"wkt":r.geometry.wkt})
        zona_ids=dict(cn.execute(text("SELECT clave,id FROM zonas")).all())

        # Reemplazamos sólo los datos derivados/importados por este ETL, no datos ciudadanos.
        cn.execute(text("DELETE FROM evaluaciones_indicadores WHERE version_formula IN ('INFRAESTRUCTURA_V1','ACCESIBILIDAD_V1')"))
        cn.execute(text("DELETE FROM observaciones WHERE fuente_id IN (:fv,:fi,:fe)"),{"fv":fids["INEGI_CENSO_VIVIENDAS_AGEB_2020"],"fi":fids["EVALUA_IDS_AGEB_2020"],"fe":fids["INEGI_RAIAVL_EV"]})
        cn.execute(text("DELETE FROM estaciones_carga WHERE fuente_id=:f"),{"f":fids["CFE_ELECTROLINERAS"]})

        obs=[]; evals=[]
        for _,r in base.iterrows():
            zid=zona_ids[r.CVEGEO]
            for clave,val,unidad,fid in [
                ("VIVIENDAS_HABITADAS",r.vvpr_hb,"viviendas",fids["INEGI_CENSO_VIVIENDAS_AGEB_2020"]),
                ("VIVIENDAS_CON_AUTOMOVIL",r.vph_atm,"viviendas",fids["INEGI_CENSO_VIVIENDAS_AGEB_2020"]),
                ("IDS",r.idsm,"indice",fids["EVALUA_IDS_AGEB_2020"]),
            ]:
                if pd.notna(val): obs.append({"z":zid,"c":clave,"v":float(val),"u":unidad,"p":"2020","f":fid})
            if pd.notna(r.infraestructura_score):
                comp={"distancia_estacion_m":round(float(r.distancia_estacion_m),2),"cobertura_score":round(float(r.cobertura_score),2),"estaciones_en_zona":int(r.estaciones_carga),"conectores_en_zona":int(r.cargadores),"potencia_total_kw":round(float(r.potencia_total_kw),2),"conectores_por_1000_viviendas_auto":None if pd.isna(r.conectores_por_1000_viv_auto) else round(float(r.conectores_por_1000_viv_auto),4),"capacidad_score":round(float(r.capacidad_score),2)}
                evals.append({"z":zid,"d":"INFRAESTRUCTURA","s":round(float(r.infraestructura_score),2),"n":r.infraestructura_nivel,"v":"INFRAESTRUCTURA_V1","j":json.dumps(comp,ensure_ascii=False),"e":"Cobertura geográfica y capacidad pública de carga comparadas entre AGEB de CDMX."})
            if pd.notna(r.accesibilidad_score):
                comp={"ids":round(float(r.idsm),4),"ids_score":round(float(r.ids_score),2),"viviendas_habitadas":int(r.vvpr_hb),"viviendas_con_automovil":int(r.vph_atm),"tenencia_automovil":round(float(r.tenencia_auto),6),"tenencia_score":round(float(r.tenencia_score),2),"estrato_ids_oficial":None if pd.isna(r.e_idsm) else str(r.e_idsm)}
                evals.append({"z":zid,"d":"ACCESIBILIDAD","s":round(float(r.accesibilidad_score),2),"n":r.accesibilidad_nivel,"v":"ACCESIBILIDAD_V1","j":json.dumps(comp,ensure_ascii=False),"e":"Condiciones territoriales comparativas de accesibilidad económica; no representa capacidad individual de compra."})
        if obs:
            cn.execute(text("INSERT INTO observaciones(zona_id,clave_metrica,valor_numerico,unidad,periodo,fuente_id) VALUES(:z,:c,:v,:u,:p,:f)"),obs)
        if evals:
            cn.execute(text("""INSERT INTO evaluaciones_indicadores(zona_id,dimension,puntuacion,nivel,confianza,tamano_muestra,version_formula,componentes,explicacion)
                VALUES(:z,CAST(:d AS dimension_indicador),:s,CAST(:n AS nivel_indicador),'ALTA',NULL,:v,CAST(:j AS jsonb),:e)"""),evals)

        # Ventas EV: observaciones a nivel CDMX. Los '-' quedan como NULL y no se insertan.
        meses={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
        for _,r in ventas.dropna(subset=["unidades"]).iterrows():
            try: anio=int(float(r.anio))
            except: continue
            mes=meses.get(normalizar(r.mes));
            if not mes: continue
            periodo=f"{anio:04d}-{mes:02d}"
            cn.execute(text("""INSERT INTO observaciones(zona_id,clave_metrica,valor_numerico,unidad,periodo,fuente_id)
                VALUES(:z,'VENTAS_EV',:v,'vehiculos',:p,:f) ON CONFLICT(zona_id,clave_metrica,periodo,fuente_id) DO UPDATE SET valor_numerico=EXCLUDED.valor_numerico"""),{"z":cdmx_id,"v":float(r.unidades),"p":periodo,"f":fids["INEGI_RAIAVL_EV"]})

        # Estaciones y grupos de conectores.
        for idx,r in estaciones.iterrows():
            zid=zona_ids.get(r.CVEGEO)
            ident=str(r.get("cons",idx))
            eid=cn.execute(text("""INSERT INTO estaciones_carga(identificador_fuente,nombre,direccion,ubicacion,zona_id,fuente_id)
                VALUES(:i,:n,:d,ST_SetSRID(ST_MakePoint(:lon,:lat),4326),:z,:f) RETURNING id"""),
                {"i":ident,"n":str(r.nombre_estacion),"d":None if pd.isna(r.direccion) else str(r.direccion),"lon":float(r.longitude),"lat":float(r.latitude),"z":zid,"f":fids["CFE_ELECTROLINERAS"]}).scalar_one()
            if not conectores.empty and idx in set(conectores["idx"]):
                for _,c in conectores[conectores["idx"]==idx].iterrows():
                    cn.execute(text("""INSERT INTO conectores_carga(estacion_id,numero_grupo,cantidad,tipo_conector,potencia_kw,procedencia_estado)
                        VALUES(:e,:g,:q,:t,:p,'OFICIAL')"""),{"e":eid,"g":int(c.numero_grupo),"q":int(c.cantidad),"t":c.tipo_conector,"p":None if pd.isna(c.potencia_kw) else float(c.potencia_kw)})

    print("[6/6] ✓ PostgreSQL/PostGIS actualizado")


def main():
    ap=argparse.ArgumentParser(description="ETL de datos públicos para Nehnemi")
    ap.add_argument("--validar",action="store_true",help="Procesa y valida sin escribir en PostgreSQL")
    ap.add_argument("--reiniciar",action="store_true",help="Vacía las tablas Nehnemi antes de cargar (incluye datos ciudadanos)")
    args=ap.parse_args()
    try:
        ageb,viviendas,ids,cfe,ventas=cargar_fuentes()
        base,estaciones,conectores=transformar(ageb,viviendas,ids,cfe)
        if args.validar:
            print("\nVALIDACIÓN COMPLETADA. No se modificó PostgreSQL.")
            return
        guardar_bd(base,estaciones,conectores,ventas,args.reiniciar)
        print("\nETL COMPLETADO CORRECTAMENTE.")
    except Exception as e:
        print(f"\nERROR: {e}",file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
