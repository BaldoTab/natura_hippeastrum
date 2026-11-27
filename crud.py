from __future__ import annotations

import datetime as dt
import json
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models import (
    AfirmacionFuente,
    AfirmacionReferencia,
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


def get_planta_familia(session: Session, planta_id: int) -> dict:
    planta = get_planta(session, planta_id)
    if planta is None:
        return {}

    madre = session.get(Planta, planta.id_madre) if planta.id_madre else None
    padre = session.get(Planta, planta.id_padre) if planta.id_padre else None
    cruce_origen = session.get(Cruce, planta.id_cruce_origen) if planta.id_cruce_origen else None
    clone_de = session.get(Planta, planta.es_clon_de) if planta.es_clon_de else None

    hijos = list(
        session.execute(
            select(Planta)
            .where(
                Planta.id != planta_id,
                or_(Planta.id_madre == planta_id, Planta.id_padre == planta_id),
            )
            .order_by(Planta.codigo.asc())
        ).scalars()
    )

    parent_ids = {parent_id for parent_id in (planta.id_madre, planta.id_padre) if parent_id}
    hermanos = []
    if parent_ids:
        hermanos = list(
            session.execute(
                select(Planta)
                .where(
                    Planta.id != planta_id,
                    or_(Planta.id_madre.in_(parent_ids), Planta.id_padre.in_(parent_ids)),
                )
                .order_by(Planta.codigo.asc())
            ).scalars()
        )

    clones = list(
        session.execute(
            select(Planta).where(Planta.es_clon_de == planta_id).order_by(Planta.codigo.asc())
        ).scalars()
    )
    cruces_progenitor = list(
        session.execute(
            select(Cruce)
            .where(or_(Cruce.planta_madre_id == planta_id, Cruce.planta_padre_id == planta_id))
            .order_by(Cruce.fecha_polinizacion.desc(), Cruce.codigo.desc())
        ).scalars()
    )

    return {
        "madre": madre,
        "padre": padre,
        "cruce_origen": cruce_origen,
        "clone_de": clone_de,
        "hijos": hijos,
        "hermanos": hermanos,
        "clones": clones,
        "cruces_progenitor": cruces_progenitor,
    }


def _genealogy_network(session: Session) -> tuple[list[dict], list[dict], dict[str, set[str]]]:
    plantas = list(session.execute(select(Planta).order_by(Planta.codigo.asc())).scalars())
    cruces = list(session.execute(select(Cruce).order_by(Cruce.codigo.asc())).scalars())
    planta_ids = {planta.id for planta in plantas}
    cruce_ids = {cruce.id for cruce in cruces}

    nodes = [
        {
            "id": f"p-{planta.id}",
            "kind": "planta",
            "label": planta.codigo,
            "name": planta.nombre_cultivar or "",
            "generation": planta.generacion.value if planta.generacion else "",
            "url": f"/plantas/{planta.id}",
        }
        for planta in plantas
    ]
    nodes.extend(
        {
            "id": f"c-{cruce.id}",
            "kind": "cruce",
            "label": cruce.codigo,
            "name": "Cruce",
            "generation": "",
            "url": f"/cruces/{cruce.id}",
        }
        for cruce in cruces
    )

    links: list[dict] = []
    for planta in plantas:
        if planta.es_clon_de in planta_ids:
            links.append({"source": f"p-{planta.es_clon_de}", "target": f"p-{planta.id}", "type": "clon"})
        elif planta.id_cruce_origen in cruce_ids:
            links.append({"source": f"c-{planta.id_cruce_origen}", "target": f"p-{planta.id}", "type": "cruce"})
        else:
            if planta.id_madre in planta_ids:
                links.append({"source": f"p-{planta.id_madre}", "target": f"p-{planta.id}", "type": "parentesco"})
            if planta.id_padre in planta_ids:
                links.append({"source": f"p-{planta.id_padre}", "target": f"p-{planta.id}", "type": "parentesco"})

    for cruce in cruces:
        if cruce.planta_madre_id in planta_ids:
            links.append({"source": f"p-{cruce.planta_madre_id}", "target": f"c-{cruce.id}", "type": "parental"})
        if cruce.planta_padre_id in planta_ids:
            links.append({"source": f"p-{cruce.planta_padre_id}", "target": f"c-{cruce.id}", "type": "parental"})

    unique_links = []
    seen_links = set()
    for link in links:
        key = (link["source"], link["target"], link["type"])
        if key not in seen_links:
            seen_links.add(key)
            unique_links.append(link)

    adjacency = {node["id"]: set() for node in nodes}
    for link in unique_links:
        adjacency.setdefault(link["source"], set()).add(link["target"])
    return nodes, unique_links, adjacency


def get_genealogy_graph(session: Session, planta_id: int) -> dict:
    nodes, links, directed = _genealogy_network(session)
    selected_id = f"p-{planta_id}"
    if selected_id not in directed:
        return {"nodes": [], "links": [], "selected": selected_id}

    undirected = {node_id: set(neighbors) for node_id, neighbors in directed.items()}
    for link in links:
        undirected.setdefault(link["source"], set()).add(link["target"])
        undirected.setdefault(link["target"], set()).add(link["source"])

    connected = set()
    pending = [selected_id]
    while pending:
        node_id = pending.pop()
        if node_id in connected:
            continue
        connected.add(node_id)
        pending.extend(undirected.get(node_id, set()) - connected)

    return {
        "nodes": [node for node in nodes if node["id"] in connected],
        "links": [link for link in links if link["source"] in connected and link["target"] in connected],
        "selected": selected_id,
    }


def genealogy_reachable_plants(session: Session, kind: str, entity_id: int) -> set[int]:
    _, _, adjacency = _genealogy_network(session)
    start_id = f"{kind}-{entity_id}"
    reachable = set()
    pending = [start_id]
    while pending:
        node_id = pending.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        pending.extend(adjacency.get(node_id, set()) - reachable)
    return {int(node_id.split("-", 1)[1]) for node_id in reachable if node_id.startswith("p-")}


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


def list_referencia_loci(
    session: Session,
    q: str | None = None,
    categoria: str | None = None,
    estado: str | None = None,
    tipo_entidad: str | None = None,
) -> list[LocusReferencia]:
    stmt = (
        select(LocusReferencia)
        .options(
            selectinload(LocusReferencia.afirmaciones)
            .selectinload(AfirmacionReferencia.evidencias)
            .selectinload(AfirmacionFuente.fuente)
        )
        .order_by(LocusReferencia.codigo.asc())
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            func.lower(LocusReferencia.codigo).like(func.lower(like))
            | func.lower(func.coalesce(LocusReferencia.nombre_completo, "")).like(func.lower(like))
            | func.lower(func.coalesce(LocusReferencia.resumen, "")).like(func.lower(like))
        )
    if categoria:
        stmt = stmt.where(LocusReferencia.categoria == categoria)
    if estado:
        stmt = stmt.where(LocusReferencia.estado_curacion == estado)
    if tipo_entidad:
        stmt = stmt.where(LocusReferencia.tipo_entidad == tipo_entidad)
    return list(session.execute(stmt).scalars().all())


def get_locus_referencia(session: Session, locus_id: int) -> LocusReferencia | None:
    stmt = (
        select(LocusReferencia)
        .where(LocusReferencia.id == locus_id)
        .options(
            selectinload(LocusReferencia.afirmaciones)
            .selectinload(AfirmacionReferencia.evidencias)
            .selectinload(AfirmacionFuente.fuente)
        )
    )
    return session.execute(stmt).scalar_one_or_none()


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


def sync_genotipos_planta(session: Session, planta_id: int, entries: list[dict]) -> None:
    existing = {
        row.locus_id: row
        for row in session.execute(select(GenotipoPlanta).where(GenotipoPlanta.planta_id == planta_id)).scalars()
    }
    for entry in entries:
        locus_id = entry["locus_id"]
        data = entry["datos"]
        row = existing.get(locus_id)
        if data is None:
            if row is not None:
                session.delete(row)
            continue
        if row is None:
            row = GenotipoPlanta(planta_id=planta_id, locus_id=locus_id, **data)
            session.add(row)
        else:
            previous_alleles = [row.alelo_1, row.alelo_2, row.alelo_3, row.alelo_4]
            for field, value in data.items():
                setattr(row, field, value)
            if previous_alleles == [row.alelo_1, row.alelo_2, row.alelo_3, row.alelo_4] and row.genotipo_display:
                continue
        row.genotipo_display = _compute_genotipo_display(row)
        if not row.fecha_inferencia:
            row.fecha_inferencia = dt.date.today()
    session.commit()


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
    descendientes = session.execute(select(Planta).where(Planta.id_cruce_origen == cruce.id)).scalars()
    for planta in descendientes:
        planta.id_madre = cruce.planta_madre_id
        planta.id_padre = cruce.planta_padre_id
        session.add(planta)
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
