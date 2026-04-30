from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from crud import create_tarea
from models import PrioridadEnum, TipoTareaEnum


def tarea_confirmar_fecundacion(session: Session, cruce_id: int, fecha_polinizacion: dt.date) -> None:
    create_tarea(
        session,
        {
            "tipo": TipoTareaEnum.Polinizar,
            "cruce_id": cruce_id,
            "fecha_vencimiento": fecha_polinizacion + dt.timedelta(days=10),
            "descripcion": f"Confirmar fecundación cruce {cruce_id}",
            "prioridad": PrioridadEnum.Media,
        },
    )


def tarea_revisar_maduracion_capsula(session: Session, cruce_id: int, fecha_confirmacion: dt.date) -> None:
    create_tarea(
        session,
        {
            "tipo": TipoTareaEnum.Revisar_capsula,
            "cruce_id": cruce_id,
            "fecha_vencimiento": fecha_confirmacion + dt.timedelta(days=45),
            "descripcion": f"Revisar maduración cápsula cruce {cruce_id}",
            "prioridad": PrioridadEnum.Alta,
        },
    )


def tarea_revisar_germinacion(session: Session, cruce_id: int, fecha_siembra: dt.date) -> None:
    create_tarea(
        session,
        {
            "tipo": TipoTareaEnum.Sembrar,
            "cruce_id": cruce_id,
            "fecha_vencimiento": fecha_siembra + dt.timedelta(days=14),
            "descripcion": f"Revisar germinación cruce {cruce_id}",
            "prioridad": PrioridadEnum.Media,
        },
    )
