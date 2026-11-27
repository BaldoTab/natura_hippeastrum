from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import crud
from database import SessionLocal, engine, get_db
from image_utils import save_image_and_thumbnail
from migration_utils import run_migrations
from models import (
    CoincideEnum,
    ConfianzaEnum,
    ConfianzaGenotipoEnum,
    EstadoCapsulaEnum,
    EstadoCuracionEnum,
    EstadoPlantaEnum,
    EtapaFotoEnum,
    FecundacionEnum,
    GeneracionEnum,
    MetodoInferenciaEnum,
    PapilioEnum,
    PloidyEnum,
    PrioridadEnum,
    TipoAfirmacionEnum,
    TipoEntidadLocusEnum,
    TipoPatronEnum,
)
from models import Capsula, Cruce, Foto, Planta, Tarea
from reference_service import load_reference_catalog, sync_reference_catalog


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
PHOTOS_DIR = STATIC_DIR / "photos"
THUMBS_DIR = STATIC_DIR / "thumbnails"
REFERENCE_CATALOG_PATH = APP_DIR / "data" / "reference_catalog.json"

logging.basicConfig(
    filename=str(APP_DIR / "app.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("hippeastrum")

app = FastAPI(title="Hippeastrum App", debug=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@app.on_event("startup")
def on_startup() -> None:
    run_migrations(engine)
    session = SessionLocal()
    try:
        sync_reference_catalog(session, load_reference_catalog(REFERENCE_CATALOG_PATH))
        _seed_demo(session)
    finally:
        session.close()


def _seed_demo(session: Session) -> None:
    count = session.execute(select(func.count(Planta.id))).scalar_one()
    if count and count > 0:
        return

    def add_planta(**kwargs):
        return crud.create_planta(session, kwargs)

    hp1 = add_planta(
        nombre_cultivar="H. x johnsonii",
        especie="H. x johnsonii",
        generacion=GeneracionEnum.F0,
        ubicacion="",
        tamano_bulbo_cm=None,
        num_bulbillos=None,
        estado=EstadoPlantaEnum.Excelente,
        ploidy_sospecha=PloidyEnum.Desconocido,
        notas="rojo uniforme estrella blanca-verdosa",
    )
    crud.upsert_fenotipo(session, hp1.id, {"color_base": "Rojo", "tipo_patron": TipoPatronEnum.Uniforme})

    hp2 = add_planta(
        nombre_cultivar="H. papilio",
        especie="H. papilio",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Excelente,
        notas="crema-verdoso venas rojas",
    )
    crud.upsert_fenotipo(session, hp2.id, {"color_base": "Crema-verdoso", "tipo_patron": TipoPatronEnum.Papilio, "patron_papilio": PapilioEnum.Si})

    hp3 = add_planta(
        nombre_cultivar="Hippeastrum híbrido",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="rojo carmesí oscuro sin estrella",
    )

    hp4 = add_planta(
        nombre_cultivar="Picotee",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="blanco con borde coral",
    )

    hp5 = add_planta(
        nombre_cultivar="Amazing Belle",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="rosa doble",
    )

    hp6 = add_planta(
        nombre_cultivar="White Glory",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="blanco doble",
    )

    hp7 = add_planta(
        nombre_cultivar="Red Cream Queen",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="rojo oscuro puro",
    )

    # CR-001: HP-003 ♀ × HP-002 ♂ — abril 2026 — confirmada — 2 cápsulas
    cr = crud.create_cruce(
        session,
        {
            "planta_madre_id": hp3.id,
            "planta_padre_id": hp2.id,
            "fecha_polinizacion": dt.date(2026, 4, 10),
            "fecundacion_confirmada": FecundacionEnum.Si,
            "fecha_confirmacion": dt.date(2026, 4, 20),
            "num_capsulas": 2,
            "notas": "Seed demo",
        },
    )

    crud.create_capsula(
        session,
        {
            "cruce_id": cr.id,
            "numero_capsula": 1,
            "fecha_fecundacion_estimada": dt.date(2026, 4, 20),
            "estado": EstadoCapsulaEnum.Desarrollando,
            "num_semillas_total": None,
            "num_semillas_viables": None,
            "num_semillas_inviables": None,
            "notas": None,
        },
    )
    crud.create_capsula(
        session,
        {
            "cruce_id": cr.id,
            "numero_capsula": 2,
            "fecha_fecundacion_estimada": dt.date(2026, 4, 20),
            "estado": EstadoCapsulaEnum.Desarrollando,
            "num_semillas_total": None,
            "num_semillas_viables": None,
            "num_semillas_inviables": None,
            "notas": None,
        },
    )

    crud.create_tarea(
        session,
        {
            "tipo": "Revisar_capsula",
            "cruce_id": cr.id,
            "fecha_vencimiento": dt.date(2026, 6, 10),
            "descripcion": "Revisar maduración cápsula CR-001",
            "prioridad": PrioridadEnum.Alta,
        },
    )


def _breadcrumbs(parts: list[tuple[str, str | None]]) -> str:
    crumbs = []
    for label, href in parts:
        if href:
            crumbs.append(f'<a class="text-primary" href="{href}">{label}</a>')
        else:
            crumbs.append(f"<span>{label}</span>")
    return " / ".join(crumbs)


async def _parse_genotipos_form(request: Request, db: Session, existing: dict[int, object]) -> list[dict]:
    form = await request.form()
    loci = {locus.id: locus for locus in crud.list_loci_referencia(db)}
    locus_ids: set[int] = set()
    for key in form:
        if not key.startswith("gl_"):
            continue
        try:
            locus_ids.add(int(key.split("_")[1]))
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Campo de genotipo inválido") from None

    entries: list[dict] = []
    for locus_id in sorted(locus_ids):
        if locus_id not in loci:
            raise HTTPException(status_code=400, detail=f"Locus desconocido: {locus_id}")
        prefix = f"gl_{locus_id}_"

        def allele(field: str, optional: bool = False) -> str | None:
            value = str(form.get(prefix + field, "") or "").strip()
            if not value:
                return None if optional else "?"
            if len(value) > 50 or "/" in value:
                raise HTTPException(status_code=400, detail=f"Alelo inválido para {loci[locus_id].codigo}")
            return value

        try:
            confianza = ConfianzaGenotipoEnum(form.get(prefix + "confianza", ConfianzaGenotipoEnum.Desconocido.value))
            metodo = MetodoInferenciaEnum(form.get(prefix + "metodo", MetodoInferenciaEnum.Desconocido.value))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Confianza o método inválido para {loci[locus_id].codigo}") from None

        data = {
            "alelo_1": allele("alelo_1"),
            "alelo_2": allele("alelo_2"),
            "alelo_3": allele("alelo_3", optional=True),
            "alelo_4": allele("alelo_4", optional=True),
            "confianza": confianza,
            "metodo_inferencia": metodo,
            "fuente_evidencia": str(form.get(prefix + "fuente", "") or "").strip() or None,
        }
        known_allele = any(value not in {None, "?"} for value in (data["alelo_1"], data["alelo_2"], data["alelo_3"], data["alelo_4"]))
        active = (
            known_allele
            or bool(data["fuente_evidencia"])
            or confianza != ConfianzaGenotipoEnum.Desconocido
            or metodo != MetodoInferenciaEnum.Desconocido
        )
        if not active:
            if locus_id in existing:
                entries.append({"locus_id": locus_id, "datos": None})
            continue
        if confianza == ConfianzaGenotipoEnum.Confirmado_lab and not data["fuente_evidencia"]:
            raise HTTPException(status_code=400, detail=f"Una confirmación de laboratorio necesita fuente para {loci[locus_id].codigo}")
        entries.append({"locus_id": locus_id, "datos": data if active else None})
    return entries


def _resolve_genealogy(
    db: Session,
    planta_id: int | None,
    id_madre: int | None,
    id_padre: int | None,
    id_cruce_origen: int | None,
    es_clon_de: int | None,
) -> dict:
    if es_clon_de:
        id_madre = None
        id_padre = None
        id_cruce_origen = None
    elif id_cruce_origen:
        cruce = db.get(Cruce, id_cruce_origen)
        if cruce is None:
            raise HTTPException(status_code=400, detail="El cruce de origen seleccionado no existe.")
        if planta_id in {cruce.planta_madre_id, cruce.planta_padre_id}:
            raise HTTPException(status_code=400, detail="Una planta no puede ser descendiente de un cruce del que forma parte como progenitor.")
        id_madre = cruce.planta_madre_id
        id_padre = cruce.planta_padre_id

    for label, parent_id in (("madre", id_madre), ("padre", id_padre), ("planta de origen del clon", es_clon_de)):
        if parent_id is not None and db.get(Planta, parent_id) is None:
            raise HTTPException(status_code=400, detail=f"La {label} seleccionada no existe.")

    if planta_id is not None:
        if planta_id in {id_madre, id_padre, es_clon_de}:
            raise HTTPException(status_code=400, detail="Una planta no puede ser su propio progenitor o su propio origen de clonación.")
        reachable = crud.genealogy_reachable_plants(db, "p", planta_id)
        targets = {parent_id for parent_id in (id_madre, id_padre, es_clon_de) if parent_id is not None}
        if targets & reachable:
            raise HTTPException(status_code=400, detail="La relación propuesta crea un ciclo en el árbol genealógico.")

    return {
        "id_madre": id_madre,
        "id_padre": id_padre,
        "id_cruce_origen": id_cruce_origen,
        "es_clon_de": es_clon_de,
    }


def _validate_cruce_parents(db: Session, cruce_id: int | None, planta_madre_id: int, planta_padre_id: int) -> None:
    if db.get(Planta, planta_madre_id) is None or db.get(Planta, planta_padre_id) is None:
        raise HTTPException(status_code=400, detail="Los parentales del cruce deben ser plantas existentes.")
    if cruce_id is not None:
        reachable = crud.genealogy_reachable_plants(db, "c", cruce_id)
        if planta_madre_id in reachable or planta_padre_id in reachable:
            raise HTTPException(status_code=400, detail="Los parentales propuestos crean un ciclo genealógico con la descendencia del cruce.")


def _plant_thumb(session: Session, planta_id: int) -> str | None:
    f = session.execute(
        select(Foto).where(Foto.planta_id == planta_id).order_by(Foto.es_foto_principal.desc(), Foto.id.desc()).limit(1)
    ).scalar_one_or_none()
    if not f:
        return None
    if f.thumbnail_filename:
        return f"/static/thumbnails/{f.thumbnail_filename}"
    return f"/static/photos/{f.filename}"


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        gen_counts = {
            g.value: db.execute(select(func.count(Planta.id)).where(Planta.generacion == g)).scalar_one()
            for g in GeneracionEnum
        }

        today = dt.date.today()
        tareas = crud.list_tareas(db, from_date=today, to_date=today + dt.timedelta(days=30), include_completed=False)

        cruces_activos = db.execute(
            select(Cruce)
            .where(Cruce.fecundacion_confirmada.in_([FecundacionEnum.Si, FecundacionEnum.Pendiente]))
            .order_by(Cruce.fecha_polinizacion.desc())
            .limit(6)
        ).scalars().all()

        plantas_recientes = db.execute(select(Planta).order_by(Planta.fecha_creacion.desc()).limit(8)).scalars().all()
        for p in plantas_recientes:
            setattr(p, "foto_principal_thumb", _plant_thumb(db, p.id))

        gen_labels = [g.value for g in GeneracionEnum]
        gen_values = [gen_counts.get(g, 0) for g in gen_labels]

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "request": request,
                "breadcrumbs": None,
                "gen_counts": gen_counts,
                "tareas": tareas,
                "cruces_activos": cruces_activos,
                "plantas_recientes": plantas_recientes,
                "gen_labels": gen_labels,
                "gen_values": gen_values,
            },
        )
    except Exception:
        logger.exception("Error rendering dashboard")
        raise


@app.get("/cultivo", response_class=HTMLResponse)
def cultivo(request: Request):
    return templates.TemplateResponse(
        request,
        "cultivo/index.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Cultivo", None)])},
    )


@app.get("/plantas", response_class=HTMLResponse)
def plantas_list(
    request: Request,
    q: str | None = None,
    generacion: str | None = None,
    estado: str | None = None,
    ploidy: str | None = None,
    db: Session = Depends(get_db),
):
    plantas = crud.list_plantas(db, generacion=generacion, estado=estado, ploidy=ploidy, q=q)
    for p in plantas:
        setattr(p, "foto_principal_thumb", _plant_thumb(db, p.id))

    return templates.TemplateResponse(
        request,
        "plantas/list.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Plantas", None)]),
            "plantas": plantas,
            "q": q,
            "generacion": generacion,
            "estado": estado,
            "ploidy": ploidy,
            "generaciones": [g.value for g in GeneracionEnum],
            "estados": [e.value for e in EstadoPlantaEnum],
            "ploidies": [p.value for p in PloidyEnum],
        },
    )


@app.get("/plantas/new", response_class=HTMLResponse)
def plantas_new(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "plantas/form.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Plantas", "/plantas"), ("Nueva", None)]),
            "planta": None,
            "action": "/plantas/new",
            "form": {"generacion": GeneracionEnum.F0.value, "estado": EstadoPlantaEnum.Bueno.value, "ploidy_sospecha": PloidyEnum.Desconocido.value, "num_ejemplares_fisicos": 1},
            "fen": {},
            "loci": crud.list_loci_referencia(db),
            "gen_by_locus": {},
            "plantas": crud.list_plantas(db),
            "cruces": crud.list_cruces(db),
            "generaciones": [g.value for g in GeneracionEnum],
            "estados": [e.value for e in EstadoPlantaEnum],
            "ploidies": [p.value for p in PloidyEnum],
            "tipo_patrones": [tp.value for tp in TipoPatronEnum],
            "papilio_opts": [pp.value for pp in PapilioEnum],
            "confianzas": [c.value for c in ConfianzaGenotipoEnum],
            "metodos": [m.value for m in MetodoInferenciaEnum],
            "labels": _plant_labels(),
        },
    )


@app.post("/plantas/new")
async def plantas_new_post(
    request: Request,
    nombre_cultivar: str | None = Form(default=None),
    especie: str | None = Form(default=None),
    generacion: str = Form(...),
    ubicacion: str | None = Form(default=None),
    tamano_bulbo_cm: float | None = Form(default=None),
    num_bulbillos: int | None = Form(default=None),
    estado: str = Form(default=EstadoPlantaEnum.Bueno.value),
    ploidy_sospecha: str = Form(default=PloidyEnum.Desconocido.value),
    ploidy_confirmado: bool = Form(default=False),
    fecha_semilla: str | None = Form(default=None),
    fecha_primera_floracion: str | None = Form(default=None),
    num_ejemplares_fisicos: int = Form(default=1),
    notas: str | None = Form(default=None),
    id_madre: int | None = Form(default=None),
    id_padre: int | None = Form(default=None),
    id_cruce_origen: int | None = Form(default=None),
    es_clon_de: int | None = Form(default=None),
    fen_color_base: str | None = Form(default=None),
    fen_tipo_patron: str | None = Form(default=None),
    fen_color_ojo: str | None = Form(default=None),
    fen_color_secundario: str | None = Form(default=None),
    fen_patron_papilio: str | None = Form(default=None),
    fen_altura_vara_floral_cm: float | None = Form(default=None),
    fen_longitud_flor_cm: float | None = Form(default=None),
    fen_diametro_flor_cm: float | None = Form(default=None),
    fen_flor_doble: bool = Form(default=False),
    fen_color_hojas: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    fen_patron_papilio = (
        fen_patron_papilio
        if fen_tipo_patron == TipoPatronEnum.Papilio.value
        and fen_patron_papilio in {PapilioEnum.Si.value, PapilioEnum.Parcial.value}
        else None
    )
    genotipos = await _parse_genotipos_form(request, db, {})
    genealogia = _resolve_genealogy(db, None, id_madre, id_padre, id_cruce_origen, es_clon_de)
    planta = crud.create_planta(
        db,
        {
            "nombre_cultivar": nombre_cultivar,
            "especie": especie,
            "generacion": generacion,
            "ubicacion": ubicacion,
            "tamano_bulbo_cm": tamano_bulbo_cm,
            "num_bulbillos": num_bulbillos,
            "estado": estado,
            "ploidy_sospecha": ploidy_sospecha,
            "ploidy_confirmado": ploidy_confirmado,
            "fecha_semilla": _parse_date(fecha_semilla),
            "fecha_primera_floracion": _parse_date(fecha_primera_floracion),
            "num_ejemplares_fisicos": num_ejemplares_fisicos,
            "notas": notas,
            **genealogia,
        },
    )

    if any([
        fen_color_base,
        fen_tipo_patron,
        fen_color_ojo,
        fen_color_secundario,
        fen_patron_papilio,
        fen_altura_vara_floral_cm,
        fen_longitud_flor_cm,
        fen_diametro_flor_cm,
        fen_flor_doble,
        fen_color_hojas,
    ]):
        crud.upsert_fenotipo(
            db,
            planta.id,
            {
                "color_base": fen_color_base,
                "tipo_patron": fen_tipo_patron or None,
                "color_ojo": fen_color_ojo,
                "color_secundario": fen_color_secundario,
                "patron_papilio": fen_patron_papilio or None,
                "altura_vara_floral_cm": fen_altura_vara_floral_cm,
                "longitud_flor_cm": fen_longitud_flor_cm,
                "diametro_flor_cm": fen_diametro_flor_cm,
                "flor_doble": fen_flor_doble,
                "color_hojas": fen_color_hojas,
            },
        )

    crud.sync_genotipos_planta(db, planta.id, genotipos)
    return RedirectResponse(url=f"/plantas/{planta.id}", status_code=303)


@app.get("/plantas/{planta_id}", response_class=HTMLResponse)
def plantas_detail(planta_id: int, request: Request, db: Session = Depends(get_db)):
    planta = crud.get_planta(db, planta_id)
    if not planta:
        return RedirectResponse(url="/plantas", status_code=303)

    fotos = db.execute(select(Foto).where(Foto.planta_id == planta_id).order_by(Foto.es_foto_principal.desc(), Foto.id.desc())).scalars().all()
    foto_principal = next((f for f in fotos if f.es_foto_principal), fotos[0] if fotos else None)

    fenotipo = planta.fenotipo
    loci = crud.list_loci_referencia(db)
    genotipos = crud.list_genotipos_planta(db, planta_id)
    gen_by_locus = {g.locus_id: g for g in genotipos}

    return templates.TemplateResponse(
        request,
        "plantas/detail.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Plantas", "/plantas"), (planta.codigo, None)]),
            "planta": planta,
            "familia": crud.get_planta_familia(db, planta_id),
            "fenotipo": fenotipo,
            "loci": loci,
            "genotipos": genotipos,
            "gen_by_locus": gen_by_locus,
            "fotos": fotos,
            "foto_principal": foto_principal,
            "etapas": [e.value for e in EtapaFotoEnum],
            "labels": _plant_labels(),
        },
    )


@app.get("/plantas/{planta_id}/edit", response_class=HTMLResponse)
def plantas_edit(planta_id: int, request: Request, db: Session = Depends(get_db)):
    planta = crud.get_planta(db, planta_id)
    if not planta:
        return RedirectResponse(url="/plantas", status_code=303)

    fen = planta.fenotipo or {}
    loci = crud.list_loci_referencia(db)
    genotipos = crud.list_genotipos_planta(db, planta_id)
    gen_by_locus = {g.locus_id: g for g in genotipos}

    return templates.TemplateResponse(
        request,
        "plantas/form.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Plantas", "/plantas"), (planta.codigo, f"/plantas/{planta.id}"), ("Editar", None)]),
            "planta": planta,
            "action": f"/plantas/{planta.id}/edit",
            "form": planta,
            "fen": fen,
            "loci": loci,
            "gen_by_locus": gen_by_locus,
            "plantas": [p for p in crud.list_plantas(db) if p.id != planta_id],
            "cruces": [c for c in crud.list_cruces(db) if planta_id not in {c.planta_madre_id, c.planta_padre_id}],
            "generaciones": [g.value for g in GeneracionEnum],
            "estados": [e.value for e in EstadoPlantaEnum],
            "ploidies": [p.value for p in PloidyEnum],
            "tipo_patrones": [tp.value for tp in TipoPatronEnum],
            "papilio_opts": [pp.value for pp in PapilioEnum],
            "confianzas": [c.value for c in ConfianzaGenotipoEnum],
            "metodos": [m.value for m in MetodoInferenciaEnum],
            "labels": _plant_labels(),
        },
    )


@app.post("/plantas/{planta_id}/edit")
async def plantas_edit_post(
    planta_id: int,
    request: Request,
    nombre_cultivar: str | None = Form(default=None),
    especie: str | None = Form(default=None),
    generacion: str = Form(...),
    ubicacion: str | None = Form(default=None),
    tamano_bulbo_cm: float | None = Form(default=None),
    num_bulbillos: int | None = Form(default=None),
    estado: str = Form(default=EstadoPlantaEnum.Bueno.value),
    ploidy_sospecha: str = Form(default=PloidyEnum.Desconocido.value),
    ploidy_confirmado: bool = Form(default=False),
    fecha_semilla: str | None = Form(default=None),
    fecha_primera_floracion: str | None = Form(default=None),
    num_ejemplares_fisicos: int = Form(default=1),
    notas: str | None = Form(default=None),
    id_madre: int | None = Form(default=None),
    id_padre: int | None = Form(default=None),
    id_cruce_origen: int | None = Form(default=None),
    es_clon_de: int | None = Form(default=None),
    fen_color_base: str | None = Form(default=None),
    fen_tipo_patron: str | None = Form(default=None),
    fen_color_ojo: str | None = Form(default=None),
    fen_color_secundario: str | None = Form(default=None),
    fen_patron_papilio: str | None = Form(default=None),
    fen_altura_vara_floral_cm: float | None = Form(default=None),
    fen_longitud_flor_cm: float | None = Form(default=None),
    fen_diametro_flor_cm: float | None = Form(default=None),
    fen_flor_doble: bool = Form(default=False),
    fen_color_hojas: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    planta = crud.get_planta(db, planta_id)
    if not planta:
        return RedirectResponse(url="/plantas", status_code=303)

    fen_patron_papilio = (
        fen_patron_papilio
        if fen_tipo_patron == TipoPatronEnum.Papilio.value
        and fen_patron_papilio in {PapilioEnum.Si.value, PapilioEnum.Parcial.value}
        else None
    )
    existing = {row.locus_id: row for row in crud.list_genotipos_planta(db, planta_id)}
    genotipos = await _parse_genotipos_form(request, db, existing)
    genealogia = _resolve_genealogy(db, planta_id, id_madre, id_padre, id_cruce_origen, es_clon_de)
    crud.update_planta(
        db,
        planta,
        {
            "nombre_cultivar": nombre_cultivar,
            "especie": especie,
            "generacion": generacion,
            "ubicacion": ubicacion,
            "tamano_bulbo_cm": tamano_bulbo_cm,
            "num_bulbillos": num_bulbillos,
            "estado": estado,
            "ploidy_sospecha": ploidy_sospecha,
            "ploidy_confirmado": ploidy_confirmado,
            "fecha_semilla": _parse_date(fecha_semilla),
            "fecha_primera_floracion": _parse_date(fecha_primera_floracion),
            "num_ejemplares_fisicos": num_ejemplares_fisicos,
            "notas": notas,
            **genealogia,
        },
    )

    if any([
        fen_color_base,
        fen_tipo_patron,
        fen_color_ojo,
        fen_color_secundario,
        fen_patron_papilio,
        fen_altura_vara_floral_cm,
        fen_longitud_flor_cm,
        fen_diametro_flor_cm,
        fen_flor_doble,
        fen_color_hojas,
    ]):
        crud.upsert_fenotipo(
            db,
            planta_id,
            {
                "color_base": fen_color_base,
                "tipo_patron": fen_tipo_patron or None,
                "color_ojo": fen_color_ojo,
                "color_secundario": fen_color_secundario,
                "patron_papilio": fen_patron_papilio or None,
                "altura_vara_floral_cm": fen_altura_vara_floral_cm,
                "longitud_flor_cm": fen_longitud_flor_cm,
                "diametro_flor_cm": fen_diametro_flor_cm,
                "flor_doble": fen_flor_doble,
                "color_hojas": fen_color_hojas,
            },
        )

    crud.sync_genotipos_planta(db, planta_id, genotipos)
    return RedirectResponse(url=f"/plantas/{planta_id}", status_code=303)


@app.post("/photos/upload")
def photo_upload(
    planta_id: int | None = Form(default=None),
    cruce_id: int | None = Form(default=None),
    capsula_id: int | None = Form(default=None),
    etapa: str = Form(default=EtapaFotoEnum.General.value),
    es_foto_principal: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    filename, thumb_filename, exif_date = save_image_and_thumbnail(content, file.filename or "upload.jpg", PHOTOS_DIR, THUMBS_DIR)

    foto = crud.create_foto(
        db,
        {
            "planta_id": planta_id,
            "cruce_id": cruce_id,
            "capsula_id": capsula_id,
            "filename": filename,
            "thumbnail_filename": thumb_filename,
            "etapa": etapa,
            "es_foto_principal": es_foto_principal,
            "fecha_foto": exif_date,
            "descripcion": None,
            "notas": None,
        },
    )

    if planta_id and es_foto_principal:
        crud.set_planta_foto_principal(db, planta_id, foto.id)

    if planta_id:
        return RedirectResponse(url=f"/plantas/{planta_id}", status_code=303)
    if cruce_id:
        return RedirectResponse(url=f"/cruces/{cruce_id}", status_code=303)
    return RedirectResponse(url="/galeria", status_code=303)


@app.post("/plantas/{planta_id}/foto_principal/{foto_id}")
def set_foto_principal(planta_id: int, foto_id: int, db: Session = Depends(get_db)):
    crud.set_planta_foto_principal(db, planta_id, foto_id)
    return RedirectResponse(url=f"/plantas/{planta_id}", status_code=303)


@app.get("/cruces", response_class=HTMLResponse)
def cruces_list(request: Request, db: Session = Depends(get_db)):
    cruces = crud.list_cruces(db)
    return templates.TemplateResponse(
        request,
        "cruces/list.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Cruces", None)]),
            "cruces": cruces,
        },
    )


@app.get("/cruces/new", response_class=HTMLResponse)
def cruces_new(request: Request, db: Session = Depends(get_db)):
    plantas = crud.list_plantas(db)
    return templates.TemplateResponse(
        request,
        "cruces/form.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Cruces", "/cruces"), ("Nuevo", None)]),
            "cruce": None,
            "action": "/cruces/new",
            "form": {"fecha_polinizacion": dt.date.today().isoformat(), "fecundacion_confirmada": FecundacionEnum.Pendiente.value},
            "plantas": plantas,
            "fecundacion_opts": [f.value for f in FecundacionEnum],
        },
    )


@app.post("/cruces/new")
def cruces_new_post(
    planta_madre_id: int = Form(...),
    planta_padre_id: int = Form(...),
    fecha_polinizacion: str = Form(...),
    num_flores_polinizadas: int | None = Form(default=None),
    fecundacion_confirmada: str = Form(default=FecundacionEnum.Pendiente.value),
    fecha_confirmacion: str | None = Form(default=None),
    fecha_siembra: str | None = Form(default=None),
    num_capsulas: int = Form(default=0),
    num_semillas_sembradas: int = Form(default=0),
    num_germinadas: int = Form(default=0),
    notas: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    _validate_cruce_parents(db, None, planta_madre_id, planta_padre_id)
    cruce = crud.create_cruce(
        db,
        {
            "planta_madre_id": planta_madre_id,
            "planta_padre_id": planta_padre_id,
            "fecha_polinizacion": _parse_date(fecha_polinizacion) or dt.date.today(),
            "num_flores_polinizadas": num_flores_polinizadas,
            "fecundacion_confirmada": fecundacion_confirmada,
            "fecha_confirmacion": _parse_date(fecha_confirmacion),
            "fecha_siembra": _parse_date(fecha_siembra),
            "num_capsulas": num_capsulas,
            "num_semillas_sembradas": num_semillas_sembradas,
            "num_germinadas": num_germinadas,
            "notas": notas,
        },
    )
    return RedirectResponse(url=f"/cruces/{cruce.id}", status_code=303)


@app.get("/cruces/{cruce_id}", response_class=HTMLResponse)
def cruces_detail(cruce_id: int, request: Request, db: Session = Depends(get_db)):
    cruce = crud.get_cruce(db, cruce_id)
    if not cruce:
        return RedirectResponse(url="/cruces", status_code=303)

    capsulas = db.execute(select(Capsula).where(Capsula.cruce_id == cruce_id).order_by(Capsula.numero_capsula.asc())).scalars().all()
    plantas_descendientes = db.execute(
        select(Planta).where(Planta.id_cruce_origen == cruce_id).order_by(Planta.codigo.asc())
    ).scalars().all()
    return templates.TemplateResponse(
        request,
        "cruces/detail.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Cruces", "/cruces"), (cruce.codigo, None)]),
            "cruce": cruce,
            "capsulas": capsulas,
            "plantas_descendientes": plantas_descendientes,
            "estados_capsula": [e.value for e in EstadoCapsulaEnum],
        },
    )


@app.get("/cruces/{cruce_id}/edit", response_class=HTMLResponse)
def cruces_edit(cruce_id: int, request: Request, db: Session = Depends(get_db)):
    cruce = crud.get_cruce(db, cruce_id)
    if not cruce:
        return RedirectResponse(url="/cruces", status_code=303)
    plantas = crud.list_plantas(db)
    return templates.TemplateResponse(
        request,
        "cruces/form.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Cruces", "/cruces"), (cruce.codigo, f"/cruces/{cruce.id}"), ("Editar", None)]),
            "cruce": cruce,
            "action": f"/cruces/{cruce.id}/edit",
            "form": cruce,
            "plantas": plantas,
            "fecundacion_opts": [f.value for f in FecundacionEnum],
        },
    )


@app.post("/cruces/{cruce_id}/edit")
def cruces_edit_post(
    cruce_id: int,
    planta_madre_id: int = Form(...),
    planta_padre_id: int = Form(...),
    fecha_polinizacion: str = Form(...),
    num_flores_polinizadas: int | None = Form(default=None),
    fecundacion_confirmada: str = Form(default=FecundacionEnum.Pendiente.value),
    fecha_confirmacion: str | None = Form(default=None),
    fecha_siembra: str | None = Form(default=None),
    num_capsulas: int = Form(default=0),
    num_semillas_sembradas: int = Form(default=0),
    num_germinadas: int = Form(default=0),
    notas: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    cruce = crud.get_cruce(db, cruce_id)
    if not cruce:
        return RedirectResponse(url="/cruces", status_code=303)

    _validate_cruce_parents(db, cruce_id, planta_madre_id, planta_padre_id)
    crud.update_cruce(
        db,
        cruce,
        {
            "planta_madre_id": planta_madre_id,
            "planta_padre_id": planta_padre_id,
            "fecha_polinizacion": _parse_date(fecha_polinizacion) or dt.date.today(),
            "num_flores_polinizadas": num_flores_polinizadas,
            "fecundacion_confirmada": fecundacion_confirmada,
            "fecha_confirmacion": _parse_date(fecha_confirmacion),
            "fecha_siembra": _parse_date(fecha_siembra),
            "num_capsulas": num_capsulas,
            "num_semillas_sembradas": num_semillas_sembradas,
            "num_germinadas": num_germinadas,
            "notas": notas,
        },
    )

    return RedirectResponse(url=f"/cruces/{cruce_id}", status_code=303)


@app.post("/cruces/{cruce_id}/capsulas")
def cruces_add_capsula(
    cruce_id: int,
    numero_capsula: int = Form(...),
    fecha_fecundacion_estimada: str = Form(...),
    estado: str = Form(default=EstadoCapsulaEnum.Desarrollando.value),
    fecha_recoleccion: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    crud.create_capsula(
        db,
        {
            "cruce_id": cruce_id,
            "numero_capsula": numero_capsula,
            "fecha_fecundacion_estimada": _parse_date(fecha_fecundacion_estimada) or dt.date.today(),
            "estado": estado,
            "fecha_recoleccion": _parse_date(fecha_recoleccion),
            "num_semillas_total": None,
            "num_semillas_viables": None,
            "num_semillas_inviables": None,
            "notas": None,
        },
    )
    return RedirectResponse(url=f"/cruces/{cruce_id}", status_code=303)


@app.get("/tareas", response_class=HTMLResponse)
def tareas_list(request: Request, db: Session = Depends(get_db)):
    tareas = crud.list_tareas(db)
    return templates.TemplateResponse(
        request,
        "tareas/list.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Tareas", None)]), "tareas": tareas},
    )


@app.post("/tareas/{tarea_id}/toggle")
def tarea_toggle(tarea_id: int, request: Request, db: Session = Depends(get_db)):
    tarea = db.get(Tarea, tarea_id)
    if not tarea:
        return RedirectResponse(url="/tareas", status_code=303)
    crud.set_tarea_completada(db, tarea, True)
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or "/tareas", status_code=303)


@app.get("/galeria", response_class=HTMLResponse)
def galeria(request: Request, db: Session = Depends(get_db)):
    fotos = db.execute(select(Foto).order_by(Foto.id.desc()).limit(60)).scalars().all()
    return templates.TemplateResponse(
        request,
        "galeria/list.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Galería", None)]), "fotos": fotos},
    )


@app.get("/arbol", response_class=HTMLResponse)
def arbol(request: Request, planta_id: int | None = None, db: Session = Depends(get_db)):
    plantas = crud.list_plantas(db)
    selected = db.get(Planta, planta_id) if planta_id is not None else None
    if selected is None and plantas:
        related_ids = {
            entity_id
            for cruce in crud.list_cruces(db)
            for entity_id in (cruce.planta_madre_id, cruce.planta_padre_id)
        }
        related_ids.update(
            planta.id
            for planta in plantas
            if planta.id_cruce_origen or planta.id_madre or planta.id_padre or planta.es_clon_de
        )
        selected = next((planta for planta in plantas if planta.id in related_ids), plantas[0])
    graph = crud.get_genealogy_graph(db, selected.id) if selected else {"nodes": [], "links": [], "selected": ""}
    return templates.TemplateResponse(
        request,
        "arbol/index.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Árbol", None)]),
            "plantas": plantas,
            "selected": selected,
            "graph": graph,
        },
    )


@app.get("/predictor", response_class=HTMLResponse)
def predictor(request: Request):
    return templates.TemplateResponse(
        request,
        "predictor/index.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Predictor", None)])},
    )


def _plant_labels() -> dict:
    return {
        "confianzas": {
            ConfianzaGenotipoEnum.Confirmado_lab.value: "Confirmado en laboratorio",
            ConfianzaGenotipoEnum.Alta_observacion.value: "Alta por observación",
            ConfianzaGenotipoEnum.Media_inferido.value: "Media por inferencia",
            ConfianzaGenotipoEnum.Baja_visual.value: "Baja por observación visual",
            ConfianzaGenotipoEnum.Desconocido.value: "Desconocida",
        },
        "metodos": {
            MetodoInferenciaEnum.Citometria_flujo.value: "Citometría de flujo",
            MetodoInferenciaEnum.Observacion_fenotipo.value: "Observación del fenotipo",
            MetodoInferenciaEnum.Resultado_cruce_F1.value: "Resultado de cruce F1",
            MetodoInferenciaEnum.Segregacion_F2.value: "Segregación F2",
            MetodoInferenciaEnum.Chi_cuadrado.value: "Chi-cuadrado",
            MetodoInferenciaEnum.Comparacion_parental.value: "Comparación parental",
            MetodoInferenciaEnum.Desconocido.value: "Desconocido",
        },
        "papilio": {
            PapilioEnum.Si.value: "Sí",
            PapilioEnum.No.value: "No",
            PapilioEnum.Parcial.value: "Parcial",
        },
    }


def _reference_labels() -> dict:
    return {
        "estados": {state.value: state.value.replace("_", " ") for state in EstadoCuracionEnum},
        "entidades": {
            TipoEntidadLocusEnum.Locus_clasico.value: "Locus clásico",
            TipoEntidadLocusEnum.Gen_molecular.value: "Gen molecular",
            TipoEntidadLocusEnum.Marcador.value: "Marcador",
        },
        "afirmaciones": {
            TipoAfirmacionEnum.Identidad.value: "Identidad",
            TipoAfirmacionEnum.Funcion.value: "Función",
            TipoAfirmacionEnum.Efecto_alelo.value: "Efecto alélico",
            TipoAfirmacionEnum.Herencia.value: "Herencia",
            TipoAfirmacionEnum.Epistasis.value: "Epistasis",
            TipoAfirmacionEnum.Expresion.value: "Expresión",
            TipoAfirmacionEnum.Ruta_bioquimica.value: "Ruta bioquímica",
            TipoAfirmacionEnum.Asociacion_fenotipica.value: "Asociación fenotípica",
            TipoAfirmacionEnum.Limitacion.value: "Limitación",
        },
        "metodos": {
            "Experimento_directo": "Experimento directo",
            "Segregacion": "Segregación",
            "Asociacion_molecular": "Asociación molecular",
            "Homologia": "Homología",
            "Inferencia": "Inferencia",
            "Observacion_local": "Observación local",
            "Revision": "Revisión",
        },
        "relaciones": {"Apoya": "Apoya", "Contradice": "Contradice", "Contexto": "Contexto"},
    }


@app.get("/referencia", response_class=HTMLResponse)
def referencia(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    categoria: str | None = None,
    estado: str | None = None,
    tipo_entidad: str | None = None,
):
    loci = crud.list_referencia_loci(
        db,
        q=q,
        categoria=categoria,
        estado=estado,
        tipo_entidad=tipo_entidad,
    )
    items = []
    for locus in loci:
        evidences = [evidence for claim in locus.afirmaciones for evidence in claim.evidencias]
        items.append(
            {
                "locus": locus,
                "claims": len(locus.afirmaciones),
                "evidences": len(evidences),
                "sources": len({evidence.fuente_id for evidence in evidences}),
                "reviewed": sum(
                    claim.estado in {EstadoCuracionEnum.Revisado, EstadoCuracionEnum.Aceptado}
                    for claim in locus.afirmaciones
                ),
            }
        )
    labels = _reference_labels()
    all_loci = crud.list_referencia_loci(db)
    categories = sorted({locus.categoria.value for locus in all_loci})
    sources_count = len(
        {
            evidence.fuente_id
            for locus in all_loci
            for claim in locus.afirmaciones
            for evidence in claim.evidencias
        }
    )
    return templates.TemplateResponse(
        request,
        "referencia/index.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Referencia", None)]),
            "items": items,
            "labels": labels,
            "categories": categories,
            "entities": labels["entidades"],
            "states": labels["estados"],
            "filters": {"q": q or "", "categoria": categoria or "", "estado": estado or "", "tipo_entidad": tipo_entidad or ""},
            "summary": {
                "loci": len(all_loci),
                "reviewed": sum(locus.estado_curacion in {EstadoCuracionEnum.Revisado, EstadoCuracionEnum.Aceptado} for locus in all_loci),
                "disputed": sum(locus.estado_curacion == EstadoCuracionEnum.Disputado for locus in all_loci),
                "sources": sources_count,
            },
        },
    )


@app.get("/referencia/bases", response_class=HTMLResponse)
def referencia_bases(request: Request):
    return templates.TemplateResponse(
        request,
        "referencia/bases.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Referencia", "/referencia"), ("Bases sobre genética", None)]),
        },
    )


@app.get("/referencia/{locus_id}", response_class=HTMLResponse)
def referencia_locus(locus_id: int, request: Request, db: Session = Depends(get_db)):
    locus = crud.get_locus_referencia(db, locus_id)
    if locus is None:
        raise HTTPException(status_code=404, detail="Locus no encontrado")
    sources = {
        evidence.fuente_id: evidence.fuente
        for claim in locus.afirmaciones
        for evidence in claim.evidencias
    }
    return templates.TemplateResponse(
        request,
        "referencia/locus.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Referencia", "/referencia"), (locus.codigo, None)]),
            "locus": locus,
            "claims": sorted(locus.afirmaciones, key=lambda claim: (claim.version == 1, claim.codigo_estable)),
            "aliases": json.loads(locus.nombres_alternativos) if locus.nombres_alternativos else [],
            "labels": _reference_labels(),
            "sources": [sources[key] for key in sorted(sources)],
        },
    )


def _parse_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s).strip())
    except Exception:
        return None
