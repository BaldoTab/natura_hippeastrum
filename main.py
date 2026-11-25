from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import crud
from database import Base, SessionLocal, engine, get_db
from image_utils import save_image_and_thumbnail
from migrations_auto import ensure_columns
from models import (
    CoincideEnum,
    ConfianzaEnum,
    ConfianzaGenotipoEnum,
    EstadoCapsulaEnum,
    EstadoPlantaEnum,
    EtapaFotoEnum,
    FecundacionEnum,
    GeneracionEnum,
    MetodoInferenciaEnum,
    PapilioEnum,
    PloidyEnum,
    PrioridadEnum,
    TipoPatronEnum,
)
from models import Capsula, Cruce, Foto, GenReferencia, Planta, Tarea


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
PHOTOS_DIR = STATIC_DIR / "photos"
THUMBS_DIR = STATIC_DIR / "thumbnails"

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
    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    session = SessionLocal()
    try:
        crud.seed_genes_referencia(session)
        crud.seed_loci_referencia(session)
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
    locus_r = crud.get_locus_by_codigo(session, "R")
    locus_w = crud.get_locus_by_codigo(session, "W")
    locus_d = crud.get_locus_by_codigo(session, "D")
    if locus_r:
        crud.upsert_genotipo_locus(session, hp1.id, locus_r.id, {"alelo_1": "R", "alelo_2": "R", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_w:
        crud.upsert_genotipo_locus(session, hp1.id, locus_w.id, {"alelo_1": "w", "alelo_2": "w", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_d:
        crud.upsert_genotipo_locus(session, hp1.id, locus_d.id, {"alelo_1": "d", "alelo_2": "d", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    crud.upsert_fenotipo(session, hp1.id, {"color_base": "Rojo", "tipo_patron": TipoPatronEnum.Uniforme})

    hp2 = add_planta(
        nombre_cultivar="H. papilio",
        especie="H. papilio",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Excelente,
        notas="crema-verdoso venas rojas",
    )
    locus_p = crud.get_locus_by_codigo(session, "P")
    locus_y = crud.get_locus_by_codigo(session, "Y")
    if locus_p:
        crud.upsert_genotipo_locus(session, hp2.id, locus_p.id, {"alelo_1": "P_papilio", "alelo_2": "P_papilio", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_y:
        crud.upsert_genotipo_locus(session, hp2.id, locus_y.id, {"alelo_1": "Y", "alelo_2": "y", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_w:
        crud.upsert_genotipo_locus(session, hp2.id, locus_w.id, {"alelo_1": "w", "alelo_2": "w", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_d:
        crud.upsert_genotipo_locus(session, hp2.id, locus_d.id, {"alelo_1": "d", "alelo_2": "d", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
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
    if locus_w:
        crud.upsert_genotipo_locus(session, hp4.id, locus_w.id, {"alelo_1": "W", "alelo_2": "?", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_d:
        crud.upsert_genotipo_locus(session, hp4.id, locus_d.id, {"alelo_1": "d", "alelo_2": "d", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})

    hp5 = add_planta(
        nombre_cultivar="Amazing Belle",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="rosa doble",
    )
    if locus_d:
        crud.upsert_genotipo_locus(session, hp5.id, locus_d.id, {"alelo_1": "D", "alelo_2": "d", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})

    hp6 = add_planta(
        nombre_cultivar="White Glory",
        especie="Híbrido",
        generacion=GeneracionEnum.F0,
        estado=EstadoPlantaEnum.Bueno,
        notas="blanco doble",
    )
    if locus_w:
        crud.upsert_genotipo_locus(session, hp6.id, locus_w.id, {"alelo_1": "W", "alelo_2": "W", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})
    if locus_d:
        crud.upsert_genotipo_locus(session, hp6.id, locus_d.id, {"alelo_1": "D", "alelo_2": "d", "confianza": ConfianzaGenotipoEnum.Baja_visual, "metodo_inferencia": MetodoInferenciaEnum.Observacion_fenotipo})

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


def _plant_thumb(session: Session, planta_id: int) -> str | None:
    f = session.execute(
        select(Foto).where(Foto.planta_id == planta_id).order_by(Foto.es_foto_principal.desc(), Foto.id.desc()).limit(1)
    ).scalar_one_or_none()
    if not f:
        return None
    return f.thumbnail_filename


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
            setattr(p, "_thumb", _plant_thumb(db, p.id))

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
        setattr(p, "_thumb", _plant_thumb(db, p.id))

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
def plantas_new(request: Request):
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
            "gen": {},
            "generaciones": [g.value for g in GeneracionEnum],
            "estados": [e.value for e in EstadoPlantaEnum],
            "ploidies": [p.value for p in PloidyEnum],
            "tipo_patrones": [tp.value for tp in TipoPatronEnum],
            "papilio_opts": [pp.value for pp in PapilioEnum],
            "confianzas": [c.value for c in ConfianzaGenotipoEnum],
            "metodos": [m.value for m in MetodoInferenciaEnum],
        },
    )


@app.post("/plantas/new")
def plantas_new_post(
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
            "fenotipo": fenotipo,
            "loci": loci,
            "genotipos": genotipos,
            "gen_by_locus": gen_by_locus,
            "fotos": fotos,
            "foto_principal": foto_principal,
            "etapas": [e.value for e in EtapaFotoEnum],
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
            "generaciones": [g.value for g in GeneracionEnum],
            "estados": [e.value for e in EstadoPlantaEnum],
            "ploidies": [p.value for p in PloidyEnum],
            "tipo_patrones": [tp.value for tp in TipoPatronEnum],
            "papilio_opts": [pp.value for pp in PapilioEnum],
            "confianzas": [c.value for c in ConfianzaGenotipoEnum],
            "metodos": [m.value for m in MetodoInferenciaEnum],
        },
    )


@app.post("/plantas/{planta_id}/edit")
def plantas_edit_post(
    planta_id: int,
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
    return templates.TemplateResponse(
        request,
        "cruces/detail.html",
        {
            "request": request,
            "breadcrumbs": _breadcrumbs([("Cruces", "/cruces"), (cruce.codigo, None)]),
            "cruce": cruce,
            "capsulas": capsulas,
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
def arbol(request: Request):
    return templates.TemplateResponse(
        request,
        "arbol/index.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Árbol", None)])},
    )


@app.get("/predictor", response_class=HTMLResponse)
def predictor(request: Request):
    return templates.TemplateResponse(
        request,
        "predictor/index.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Predictor", None)])},
    )


@app.get("/referencia", response_class=HTMLResponse)
def referencia(request: Request, db: Session = Depends(get_db)):
    genes = db.execute(select(GenReferencia).order_by(GenReferencia.gen.asc())).scalars().all()
    return templates.TemplateResponse(
        request,
        "referencia/index.html",
        {"request": request, "breadcrumbs": _breadcrumbs([("Referencia", None)]), "genes": genes},
    )


def _parse_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s).strip())
    except Exception:
        return None
