from __future__ import annotations

import datetime as dt
import json
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import (
    Capsula,
    Cruce,
    Fenotipo,
    Foto,
    GenotipoPlanta,
    GenReferencia,
    LocusReferencia,
    Planta,
    Tarea,
)


def next_codigo(session: Session, prefix: str, table, column_name: str, width: int = 3) -> str:
    col = getattr(table, column_name)
    last = session.execute(
        select(col).where(col.like(f"{prefix}-%")).order_by(col.desc()).limit(1)
    ).scalar_one_or_none()
    if not last:
        return f"{prefix}-{1:0{width}d}"
    try:
        n = int(str(last).split("-")[-1])
    except Exception:
        n = 0
    return f"{prefix}-{(n + 1):0{width}d}"


def create_planta(session: Session, data: dict) -> Planta:
    codigo = next_codigo(session, "HP", Planta, "codigo")
    planta = Planta(codigo=codigo, **data)
    session.add(planta)
    session.commit()
    session.refresh(planta)
    return planta


def update_planta(session: Session, planta: Planta, data: dict) -> Planta:
    for k, v in data.items():
        setattr(planta, k, v)
    session.add(planta)
    session.commit()
    session.refresh(planta)
    return planta


def list_plantas(
    session: Session,
    generacion: str | None = None,
    estado: str | None = None,
    ploidy: str | None = None,
    q: str | None = None,
) -> list[Planta]:
    stmt = select(Planta).order_by(Planta.codigo.asc())
    if generacion:
        stmt = stmt.where(Planta.generacion == generacion)
    if estado:
        stmt = stmt.where(Planta.estado == estado)
    if ploidy:
        stmt = stmt.where(Planta.ploidy_sospecha == ploidy)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(func.lower(Planta.codigo).like(func.lower(like)) | func.lower(func.coalesce(Planta.nombre_cultivar, "")).like(func.lower(like)))
    return list(session.execute(stmt).scalars().all())


def get_planta(session: Session, planta_id: int) -> Planta | None:
    return session.get(Planta, planta_id)


def upsert_fenotipo(session: Session, planta_id: int, data: dict) -> Fenotipo:
    fen = session.execute(select(Fenotipo).where(Fenotipo.planta_id == planta_id)).scalar_one_or_none()
    if fen is None:
        fen = Fenotipo(planta_id=planta_id, **data)
    else:
        for k, v in data.items():
            setattr(fen, k, v)
    session.add(fen)
    session.commit()
    session.refresh(fen)
    return fen


def list_loci_referencia(session: Session) -> list[LocusReferencia]:
    return list(session.execute(select(LocusReferencia).order_by(LocusReferencia.codigo.asc())).scalars().all())


def get_locus_by_codigo(session: Session, codigo: str) -> LocusReferencia | None:
    return session.execute(select(LocusReferencia).where(LocusReferencia.codigo == codigo)).scalar_one_or_none()


def upsert_genotipo_locus(
    session: Session,
    planta_id: int,
    locus_id: int,
    data: dict,
) -> GenotipoPlanta:
    row = session.execute(
        select(GenotipoPlanta).where(GenotipoPlanta.planta_id == planta_id, GenotipoPlanta.locus_id == locus_id)
    ).scalar_one_or_none()
    if row is None:
        row = GenotipoPlanta(planta_id=planta_id, locus_id=locus_id, **data)
    else:
        for k, v in data.items():
            setattr(row, k, v)

    row.genotipo_display = _compute_genotipo_display(row)
    if not row.fecha_inferencia:
        row.fecha_inferencia = dt.date.today()

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_genotipos_planta(session: Session, planta_id: int) -> list[GenotipoPlanta]:
    return list(
        session.execute(
            select(GenotipoPlanta).where(GenotipoPlanta.planta_id == planta_id).order_by(GenotipoPlanta.locus_id.asc())
        ).scalars().all()
    )


def create_cruce(session: Session, data: dict) -> Cruce:
    codigo = next_codigo(session, "CR", Cruce, "codigo")
    cruce = Cruce(codigo=codigo, **data)
    cruce.tasa_germinacion = _calc_tasa(cruce.num_germinadas, cruce.num_semillas_sembradas)
    session.add(cruce)
    session.commit()
    session.refresh(cruce)
    return cruce


def update_cruce(session: Session, cruce: Cruce, data: dict) -> Cruce:
    for k, v in data.items():
        setattr(cruce, k, v)
    cruce.tasa_germinacion = _calc_tasa(cruce.num_germinadas, cruce.num_semillas_sembradas)
    session.add(cruce)
    session.commit()
    session.refresh(cruce)
    return cruce


def list_cruces(session: Session) -> list[Cruce]:
    return list(session.execute(select(Cruce).order_by(Cruce.codigo.desc())).scalars().all())


def get_cruce(session: Session, cruce_id: int) -> Cruce | None:
    return session.get(Cruce, cruce_id)


def create_capsula(session: Session, data: dict) -> Capsula:
    cap = Capsula(**data)
    session.add(cap)
    session.commit()
    session.refresh(cap)
    return cap


def create_tarea(session: Session, data: dict) -> Tarea:
    t = Tarea(**data)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def list_tareas(session: Session, from_date: dt.date | None = None, to_date: dt.date | None = None, include_completed: bool = False) -> list[Tarea]:
    stmt = select(Tarea)
    if not include_completed:
        stmt = stmt.where(Tarea.completada.is_(False))
    if from_date:
        stmt = stmt.where(Tarea.fecha_vencimiento >= from_date)
    if to_date:
        stmt = stmt.where(Tarea.fecha_vencimiento <= to_date)
    stmt = stmt.order_by(Tarea.fecha_vencimiento.asc())
    return list(session.execute(stmt).scalars().all())


def set_tarea_completada(session: Session, tarea: Tarea, completada: bool) -> Tarea:
    tarea.completada = completada
    tarea.fecha_completada = dt.date.today() if completada else None
    session.add(tarea)
    session.commit()
    session.refresh(tarea)
    return tarea


def create_foto(session: Session, data: dict) -> Foto:
    foto = Foto(**data)
    session.add(foto)
    session.commit()
    session.refresh(foto)
    return foto


def set_planta_foto_principal(session: Session, planta_id: int, foto_id: int) -> None:
    fotos = session.execute(select(Foto).where(Foto.planta_id == planta_id)).scalars().all()
    for f in fotos:
        f.es_foto_principal = (f.id == foto_id)
        session.add(f)
    session.commit()


def seed_genes_referencia(session: Session) -> None:
    count = session.execute(select(func.count(GenReferencia.id))).scalar_one()
    if count and count > 0:
        return

    rows = [
        {
            "gen": "HpMYB1",
            "caracter_controlado": "Regulador maestro antocianinas",
            "alelo_dominante": "HpMYB1+",
            "alelo_recesivo": "hpmyb1",
            "tipo_herencia": "Probablemente dominante",
            "nivel_evidencia": "Media",
            "notas": "Referencia inicial (seed).",
        },
        {"gen": "R", "caracter_controlado": "Antocianinas rojo/rosa", "alelo_dominante": "R", "alelo_recesivo": "r", "tipo_herencia": "Dominante", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "Y", "caracter_controlado": "Carotenoides amarillo", "alelo_dominante": "Y", "alelo_recesivo": "y", "tipo_herencia": "Dominante", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "W", "caracter_controlado": "Inhibidor blanco", "alelo_dominante": "W", "alelo_recesivo": "w", "tipo_herencia": "Dominante", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "P", "caracter_controlado": "Patrón distribución pigmento", "alelo_dominante": "P", "alelo_recesivo": "p", "tipo_herencia": "Variable", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "D", "caracter_controlado": "Flor doble", "alelo_dominante": "D", "alelo_recesivo": "d", "tipo_herencia": "Dominante", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "CHS/CHI/F3H/DFR/ANS", "caracter_controlado": "Ruta biosíntesis antocianinas", "alelo_dominante": None, "alelo_recesivo": None, "tipo_herencia": "Compleja", "nivel_evidencia": "Baja", "notas": "Seed."},
        {"gen": "Pigmentos", "caracter_controlado": "Pelargonidina, Cianidina, Delfinidina, Peonidina, Petunidina, Malvidina", "alelo_dominante": None, "alelo_recesivo": None, "tipo_herencia": "Bioquímica", "nivel_evidencia": "Baja", "notas": "Seed."},
    ]

    session.add_all([GenReferencia(**r) for r in rows])
    session.commit()


def seed_loci_referencia(session: Session) -> None:
    count = session.execute(select(func.count(LocusReferencia.id))).scalar_one()
    if count and count > 0:
        return

    def j(x):
        return json.dumps(x, ensure_ascii=False)

    rows = [
        {
            "codigo": "R",
            "nombre_completo": "Gen R — antocianinas",
            "categoria": "Color_estructural",
            "alelos_posibles": j(
                [
                    {"alelo": "R", "dominancia": "dominante", "efecto_fenotipico": "rojo/rosa", "color_hex_aproximado": "#C0303A"},
                    {"alelo": "r", "dominancia": "recesivo", "efecto_fenotipico": "sin antocianinas", "color_hex_aproximado": "#F5F5F5"},
                ]
            ),
            "tipo_herencia": "Dominante_simple",
            "interacciona_con": j(["W", "HpMYB1", "CHS", "CHI", "F3H", "DFR", "ANS"]),
            "nivel_evidencia": "Media",
            "pigmento_producido": "Cianidina",
            "referencia_cientifica": None,
            "notas": "Seed",
        },
        {
            "codigo": "Y",
            "nombre_completo": "Gen Y — carotenoides",
            "categoria": "Color_estructural",
            "alelos_posibles": j(
                [
                    {"alelo": "Y", "dominancia": "dominante", "efecto_fenotipico": "amarillo/naranja", "color_hex_aproximado": "#F3B300"},
                    {"alelo": "y", "dominancia": "recesivo", "efecto_fenotipico": "sin carotenoide", "color_hex_aproximado": "#F5F5F5"},
                ]
            ),
            "tipo_herencia": "Dominante_simple",
            "interacciona_con": j([]),
            "nivel_evidencia": "Baja",
            "pigmento_producido": "Carotenoide",
            "referencia_cientifica": None,
            "notas": "Seed",
        },
        {
            "codigo": "W",
            "nombre_completo": "Gen W — inhibidor blanco (epistático sobre R)",
            "categoria": "Regulador_color",
            "alelos_posibles": j(
                [
                    {"alelo": "W", "dominancia": "epistático dominante", "efecto_fenotipico": "blanco", "color_hex_aproximado": "#FFFFFF"},
                    {"alelo": "w", "dominancia": "recesivo", "efecto_fenotipico": "sin inhibición", "color_hex_aproximado": None},
                ]
            ),
            "tipo_herencia": "Epistatico_dominante",
            "interacciona_con": j(["R"]),
            "nivel_evidencia": "Media",
            "pigmento_producido": "Ninguno",
            "referencia_cientifica": None,
            "notas": "Seed",
        },
        {
            "codigo": "P",
            "nombre_completo": "Gen P — patrón de distribución",
            "categoria": "Patron",
            "alelos_posibles": j(
                [
                    {"alelo": "P_uniforme", "dominancia": "dominante", "efecto_fenotipico": "uniforme", "color_hex_aproximado": None},
                    {"alelo": "P_papilio", "dominancia": "recesivo/semidominante", "efecto_fenotipico": "venas (papilio)", "color_hex_aproximado": None},
                    {"alelo": "P_borde", "dominancia": "recesivo", "efecto_fenotipico": "borde", "color_hex_aproximado": None},
                    {"alelo": "P_estrella", "dominancia": "dominante parcial", "efecto_fenotipico": "estrella", "color_hex_aproximado": None},
                ]
            ),
            "tipo_herencia": "Desconocido",
            "interacciona_con": j([]),
            "nivel_evidencia": "Baja",
            "pigmento_producido": None,
            "referencia_cientifica": None,
            "notas": "Seed",
        },
        {
            "codigo": "D",
            "nombre_completo": "Gen D — flor doble",
            "categoria": "Morfologia",
            "alelos_posibles": j(
                [
                    {"alelo": "D", "dominancia": "dominante parcial", "efecto_fenotipico": "doble", "color_hex_aproximado": None},
                    {"alelo": "d", "dominancia": "recesivo", "efecto_fenotipico": "simple", "color_hex_aproximado": None},
                ]
            ),
            "tipo_herencia": "Dominante_parcial",
            "interacciona_con": j([]),
            "nivel_evidencia": "Alta",
            "pigmento_producido": None,
            "referencia_cientifica": None,
            "notas": "Seed",
        },
        {
            "codigo": "HpMYB1",
            "nombre_completo": "HpMYB1 — regulador maestro antocianinas",
            "categoria": "Regulador_color",
            "alelos_posibles": j([{ "alelo": "HpMYB1+", "dominancia": "dominante", "efecto_fenotipico": "activa ruta", "color_hex_aproximado": None}]),
            "tipo_herencia": "Desconocido",
            "interacciona_con": j(["HpbHLH1", "CHS", "CHI", "F3H", "DFR", "ANS"]),
            "nivel_evidencia": "Alta",
            "pigmento_producido": None,
            "referencia_cientifica": "Li et al. BMC Plant Biology 2023",
            "notas": "Seed",
        },
        {"codigo": "CHS", "nombre_completo": "CHS — chalcona sintasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Alta", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "CHI", "nombre_completo": "CHI — chalcona isomerasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Alta", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "F3H", "nombre_completo": "F3H — flavanona 3-hidroxilasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Alta", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "DFR", "nombre_completo": "DFR — dihidroflavonol reductasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Alta", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "ANS", "nombre_completo": "ANS — antocianidina sintasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Alta", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "F3pH", "nombre_completo": "F3pH — flavonoide 3-primo-hidroxilasa", "categoria": "Color_estructural", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Media", "pigmento_producido": None, "referencia_cientifica": "Homología", "notas": "Seed"},
        {"codigo": "HpbHLH1", "nombre_completo": "HpbHLH1 — cofactor regulador MYB", "categoria": "Regulador_color", "alelos_posibles": None, "tipo_herencia": "Desconocido", "interacciona_con": None, "nivel_evidencia": "Baja", "pigmento_producido": None, "referencia_cientifica": "Inferido", "notas": "Seed"},
    ]

    session.add_all([LocusReferencia(**r) for r in rows])
    session.commit()


def _calc_tasa(num_germinadas: int | None, num_semillas_sembradas: int | None) -> float | None:
    if not num_semillas_sembradas or num_semillas_sembradas <= 0:
        return None
    if not num_germinadas or num_germinadas < 0:
        return 0.0
    return float(num_germinadas) / float(num_semillas_sembradas)


def _compute_genotipo_display(row: GenotipoPlanta) -> str:
    alleles = [row.alelo_1, row.alelo_2]
    if row.alelo_3:
        alleles.append(row.alelo_3)
    if row.alelo_4:
        alleles.append(row.alelo_4)
    return "/".join([a or "?" for a in alleles])
