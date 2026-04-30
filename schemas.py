from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field

from models import (
    CoincideEnum,
    ConfianzaEnum,
    EstadoCapsulaEnum,
    EstadoPlantaEnum,
    EtapaFotoEnum,
    FecundacionEnum,
    FormaPetaloEnum,
    GeneracionEnum,
    OrientacionFlorEnum,
    PapilioEnum,
    PloidyEnum,
    PrioridadEnum,
    TipoPatronEnum,
    TipoTareaEnum,
    ViabilidadSemillaEnum,
)


class PlantaBase(BaseModel):
    nombre_cultivar: str | None = None
    especie: str | None = None
    generacion: GeneracionEnum
    id_madre: int | None = None
    id_padre: int | None = None
    id_cruce_origen: int | None = None
    fecha_semilla: dt.date | None = None
    fecha_primera_floracion: dt.date | None = None
    ubicacion: str | None = None
    tamano_bulbo_cm: float | None = None
    num_bulbillos: int | None = None
    estado: EstadoPlantaEnum = EstadoPlantaEnum.Bueno
    bulbillos_separados: bool = False
    ploidy_sospecha: PloidyEnum = PloidyEnum.Desconocido
    ploidy_confirmado: bool = False
    num_ejemplares_fisicos: int = 1
    es_clon_de: int | None = None
    notas: str | None = None


class PlantaCreate(PlantaBase):
    pass


class PlantaUpdate(PlantaBase):
    pass


class PlantaOut(PlantaBase):
    id: int
    codigo: str
    fecha_creacion: dt.datetime
    fecha_actualizacion: dt.datetime

    class Config:
        from_attributes = True


class FenotipoBase(BaseModel):
    color_base: str | None = None
    color_secundario: str | None = None
    color_ojo: str | None = None
    color_reverso: str | None = None
    intensidad_color: int | None = Field(default=None, ge=1, le=5)
    cambia_con_edad: bool = False
    tipo_patron: TipoPatronEnum | None = None
    descripcion_patron: str | None = None
    patron_papilio: PapilioEnum | None = None
    num_petalos: int | None = None
    flor_doble: bool = False
    forma_petalo: FormaPetaloEnum | None = None
    longitud_flor_cm: float | None = None
    diametro_flor_cm: float | None = None
    num_flores_tallo: int | None = None
    orientacion_flor: OrientacionFlorEnum | None = None
    altura_vara_floral_cm: float | None = None
    longitud_tallo_cm: float | None = None
    num_tallos_temporada: int | None = None
    ancho_hojas_cm: float | None = None
    color_hojas: str | None = None
    hojas_variegadas: bool = False
    epoca_floracion: str | None = None
    evergreen: bool = False
    notas: str | None = None


class FenotipoCreate(FenotipoBase):
    planta_id: int


class FenotipoOut(FenotipoBase):
    id: int
    planta_id: int

    class Config:
        from_attributes = True


class GenotipoBase(BaseModel):
    gen_R: str | None = None
    gen_Y: str | None = None
    gen_W: str | None = None
    gen_P: str | None = None
    gen_D: str | None = None
    gen_HpMYB1: str | None = None
    ploidy_inferida: PloidyEnum = PloidyEnum.Desconocido
    confianza: ConfianzaEnum = ConfianzaEnum.Desconocido
    fuente_inferencia: str | None = None
    fecha_actualizacion: dt.date | None = None
    notas: str | None = None


class GenotipoCreate(GenotipoBase):
    planta_id: int


class GenotipoOut(GenotipoBase):
    id: int
    planta_id: int

    class Config:
        from_attributes = True


class CruceBase(BaseModel):
    planta_madre_id: int
    planta_padre_id: int
    fecha_polinizacion: dt.date
    num_flores_polinizadas: int | None = None
    fecundacion_confirmada: FecundacionEnum = FecundacionEnum.Pendiente
    fecha_confirmacion: dt.date | None = None
    num_capsulas: int = 0
    num_semillas_totales: int = 0
    num_semillas_sembradas: int = 0
    fecha_siembra: dt.date | None = None
    num_germinadas: int = 0
    tasa_germinacion: float | None = None
    resultado_esperado: str | None = None
    resultado_observado: str | None = None
    notas: str | None = None


class CruceCreate(CruceBase):
    pass


class CruceOut(CruceBase):
    id: int
    codigo: str
    fecha_creacion: dt.datetime

    class Config:
        from_attributes = True


class CapsulaBase(BaseModel):
    cruce_id: int
    numero_capsula: int
    fecha_fecundacion_estimada: dt.date
    fecha_recoleccion: dt.date | None = None
    estado: EstadoCapsulaEnum = EstadoCapsulaEnum.Desarrollando
    num_semillas_total: int | None = None
    num_semillas_viables: int | None = None
    num_semillas_inviables: int | None = None
    notas: str | None = None


class CapsulaCreate(CapsulaBase):
    pass


class CapsulaOut(CapsulaBase):
    id: int

    class Config:
        from_attributes = True


class TareaBase(BaseModel):
    tipo: TipoTareaEnum
    planta_id: int | None = None
    cruce_id: int | None = None
    fecha_vencimiento: dt.date
    completada: bool = False
    fecha_completada: dt.date | None = None
    descripcion: str | None = None
    prioridad: PrioridadEnum = PrioridadEnum.Media


class TareaCreate(TareaBase):
    pass


class TareaOut(TareaBase):
    id: int

    class Config:
        from_attributes = True


class FotoCreate(BaseModel):
    planta_id: int | None = None
    cruce_id: int | None = None
    capsula_id: int | None = None
    etapa: EtapaFotoEnum = EtapaFotoEnum.General
    es_foto_principal: bool = False
    fecha_foto: dt.date | None = None
    descripcion: str | None = None
    notas: str | None = None


class FotoOut(FotoCreate):
    id: int
    filename: str
    thumbnail_filename: str | None = None

    class Config:
        from_attributes = True
