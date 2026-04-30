from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class GeneracionEnum(str, enum.Enum):
    F0 = "F0"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"


class EstadoPlantaEnum(str, enum.Enum):
    Excelente = "Excelente"
    Bueno = "Bueno"
    Regular = "Regular"
    Malo = "Malo"
    Muerta = "Muerta"


class PloidyEnum(str, enum.Enum):
    n2 = "2n"
    n4 = "4n"
    n6 = "6n"
    n8 = "8n"
    n3 = "3n"
    n5 = "5n"
    Desconocido = "Desconocido"


class TipoPatronEnum(str, enum.Enum):
    Uniforme = "Uniforme"
    Venas = "Venas"
    Estrella = "Estrella"
    Borde = "Borde"
    Moteado = "Moteado"
    Bicolor = "Bicolor"
    Papilio = "Papilio"
    Otro = "Otro"


class PapilioEnum(str, enum.Enum):
    Si = "Sí"
    No = "No"
    Parcial = "Parcial"


class FormaPetaloEnum(str, enum.Enum):
    Ancho_redondeado = "Ancho_redondeado"
    Estrecho = "Estrecho"
    Ondulado = "Ondulado"
    Rizado = "Rizado"
    Cuchara = "Cuchara"
    Spider = "Spider"


class OrientacionFlorEnum(str, enum.Enum):
    Arriba = "Arriba"
    Lateral = "Lateral"
    Abajo = "Abajo"
    Variable = "Variable"


class FecundacionEnum(str, enum.Enum):
    Si = "Sí"
    No = "No"
    Pendiente = "Pendiente"


class EstadoCapsulaEnum(str, enum.Enum):
    Desarrollando = "Desarrollando"
    Madura = "Madura"
    Recolectada = "Recolectada"
    Abortada = "Abortada"


class ViabilidadSemillaEnum(str, enum.Enum):
    Viable = "Viable"
    Inviable = "Inviable"
    Pendiente = "Pendiente"


class EtapaFotoEnum(str, enum.Enum):
    Boton = "Boton"
    Flor_abierta = "Flor_abierta"
    Flor_marchita = "Flor_marchita"
    Fruto = "Fruto"
    Semilla = "Semilla"
    Bulbo = "Bulbo"
    Plantula = "Plantula"
    Roseta = "Roseta"
    General = "General"


class TipoTareaEnum(str, enum.Enum):
    Revisar_capsula = "Revisar_capsula"
    Sembrar = "Sembrar"
    Polinizar = "Polinizar"
    Abonar = "Abonar"
    Regar = "Regar"
    Fotografiar = "Fotografiar"
    Trasplantar = "Trasplantar"
    Otro = "Otro"


class PrioridadEnum(str, enum.Enum):
    Alta = "Alta"
    Media = "Media"
    Baja = "Baja"


class ConfianzaEnum(str, enum.Enum):
    Desconocido = "Desconocido"
    Baja = "Baja"
    Media = "Media"
    Alta = "Alta"


class CategoriaLocusEnum(str, enum.Enum):
    Color_estructural = "Color_estructural"
    Regulador_color = "Regulador_color"
    Patron = "Patron"
    Morfologia = "Morfologia"
    Ploidy_marker = "Ploidy_marker"


class TipoHerenciaEnum(str, enum.Enum):
    Dominante_simple = "Dominante_simple"
    Recesivo_simple = "Recesivo_simple"
    Dominante_parcial = "Dominante_parcial"
    Codominante = "Codominante"
    Epistatico_dominante = "Epistatico_dominante"
    Epistatico_recesivo = "Epistatico_recesivo"
    Cuantitativo_multigénico = "Cuantitativo_multigénico"
    Desconocido = "Desconocido"


class NivelEvidenciaEnum(str, enum.Enum):
    Alta = "Alta"
    Media = "Media"
    Baja = "Baja"
    Inferido = "Inferido"
    Experimental = "Experimental"


class PigmentoEnum(str, enum.Enum):
    Pelargonidina = "Pelargonidina"
    Cianidina = "Cianidina"
    Delfinidina = "Delfinidina"
    Peonidina = "Peonidina"
    Petunidina = "Petunidina"
    Malvidina = "Malvidina"
    Carotenoide = "Carotenoide"
    Ninguno = "Ninguno"


class ConfianzaGenotipoEnum(str, enum.Enum):
    Confirmado_lab = "Confirmado_lab"
    Alta_observacion = "Alta_observacion"
    Media_inferido = "Media_inferido"
    Baja_visual = "Baja_visual"
    Desconocido = "Desconocido"


class MetodoInferenciaEnum(str, enum.Enum):
    Citometria_flujo = "Citometria_flujo"
    Observacion_fenotipo = "Observacion_fenotipo"
    Resultado_cruce_F1 = "Resultado_cruce_F1"
    Segregacion_F2 = "Segregacion_F2"
    Chi_cuadrado = "Chi_cuadrado"
    Comparacion_parental = "Comparacion_parental"
    Desconocido = "Desconocido"


class CoincideEnum(str, enum.Enum):
    Si = "Sí"
    No = "No"
    Parcial = "Parcial"


class Planta(Base):
    __tablename__ = "plantas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_plantas_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nombre_cultivar: Mapped[str | None] = mapped_column(String(200))
    especie: Mapped[str | None] = mapped_column(Text)
    generacion: Mapped[GeneracionEnum] = mapped_column(Enum(GeneracionEnum), nullable=False)

    id_madre: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True)
    id_padre: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True)
    id_cruce_origen: Mapped[int | None] = mapped_column(ForeignKey("cruces.id"), nullable=True)

    fecha_semilla: Mapped[dt.date | None] = mapped_column(Date)
    fecha_primera_floracion: Mapped[dt.date | None] = mapped_column(Date)

    ubicacion: Mapped[str | None] = mapped_column(Text)
    tamano_bulbo_cm: Mapped[float | None] = mapped_column(Float)
    num_bulbillos: Mapped[int | None] = mapped_column(Integer)

    estado: Mapped[EstadoPlantaEnum] = mapped_column(Enum(EstadoPlantaEnum), nullable=False, default=EstadoPlantaEnum.Bueno)
    bulbillos_separados: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ploidy_sospecha: Mapped[PloidyEnum] = mapped_column(Enum(PloidyEnum), nullable=False, default=PloidyEnum.Desconocido)
    ploidy_confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    num_ejemplares_fisicos: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    es_clon_de: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True)

    notas: Mapped[str | None] = mapped_column(Text)

    fecha_creacion: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    fecha_actualizacion: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )

    madre: Mapped[Planta | None] = relationship("Planta", remote_side=[id], foreign_keys=[id_madre], post_update=True)
    padre: Mapped[Planta | None] = relationship("Planta", remote_side=[id], foreign_keys=[id_padre], post_update=True)
    clon_de: Mapped[Planta | None] = relationship("Planta", remote_side=[id], foreign_keys=[es_clon_de], post_update=True)

    fenotipo: Mapped[Fenotipo | None] = relationship("Fenotipo", back_populates="planta", uselist=False, cascade="all, delete-orphan")
    genotipos_loci: Mapped[list["GenotipoPlanta"]] = relationship("GenotipoPlanta", back_populates="planta", cascade="all, delete-orphan")
    epistasias: Mapped[list["EpistasiaObservada"]] = relationship("EpistasiaObservada", back_populates="planta", cascade="all, delete-orphan")
    fotos: Mapped[list[Foto]] = relationship("Foto", back_populates="planta")


class Fenotipo(Base):
    __tablename__ = "fenotipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), unique=True, nullable=False)

    color_base: Mapped[str | None] = mapped_column(Text)
    color_secundario: Mapped[str | None] = mapped_column(Text)
    color_ojo: Mapped[str | None] = mapped_column(Text)
    color_reverso: Mapped[str | None] = mapped_column(Text)

    intensidad_color: Mapped[int | None] = mapped_column(Integer)
    cambia_con_edad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    tipo_patron: Mapped[TipoPatronEnum | None] = mapped_column(Enum(TipoPatronEnum))
    descripcion_patron: Mapped[str | None] = mapped_column(Text)
    patron_papilio: Mapped[PapilioEnum | None] = mapped_column(Enum(PapilioEnum))

    num_petalos: Mapped[int | None] = mapped_column(Integer)
    flor_doble: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forma_petalo: Mapped[FormaPetaloEnum | None] = mapped_column(Enum(FormaPetaloEnum))

    longitud_flor_cm: Mapped[float | None] = mapped_column(Float)
    diametro_flor_cm: Mapped[float | None] = mapped_column(Float)
    num_flores_tallo: Mapped[int | None] = mapped_column(Integer)
    orientacion_flor: Mapped[OrientacionFlorEnum | None] = mapped_column(Enum(OrientacionFlorEnum))

    altura_vara_floral_cm: Mapped[float | None] = mapped_column(Float)
    longitud_tallo_cm: Mapped[float | None] = mapped_column(Float)
    num_tallos_temporada: Mapped[int | None] = mapped_column(Integer)

    ancho_hojas_cm: Mapped[float | None] = mapped_column(Float)
    color_hojas: Mapped[str | None] = mapped_column(Text)
    hojas_variegadas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    epoca_floracion: Mapped[str | None] = mapped_column(Text)
    evergreen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notas: Mapped[str | None] = mapped_column(Text)

    planta: Mapped[Planta] = relationship("Planta", back_populates="fenotipo")


class LocusReferencia(Base):
    __tablename__ = "loci_referencia"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_loci_referencia_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    nombre_completo: Mapped[str | None] = mapped_column(String(200))
    categoria: Mapped[CategoriaLocusEnum] = mapped_column(Enum(CategoriaLocusEnum), nullable=False)

    # JSON como texto (SQLite)
    alelos_posibles: Mapped[str | None] = mapped_column(Text)
    tipo_herencia: Mapped[TipoHerenciaEnum] = mapped_column(Enum(TipoHerenciaEnum), nullable=False, default=TipoHerenciaEnum.Desconocido)
    interacciona_con: Mapped[str | None] = mapped_column(Text)
    nivel_evidencia: Mapped[NivelEvidenciaEnum] = mapped_column(Enum(NivelEvidenciaEnum), nullable=False, default=NivelEvidenciaEnum.Baja)
    pigmento_producido: Mapped[PigmentoEnum | None] = mapped_column(Enum(PigmentoEnum), nullable=True)
    referencia_cientifica: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)

    genotipos_planta: Mapped[list["GenotipoPlanta"]] = relationship("GenotipoPlanta", back_populates="locus", cascade="all, delete-orphan")


class GenotipoPlanta(Base):
    __tablename__ = "genotipos_planta"
    __table_args__ = (
        UniqueConstraint("planta_id", "locus_id", name="uq_genotipos_planta_planta_locus"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), nullable=False, index=True)
    locus_id: Mapped[int] = mapped_column(ForeignKey("loci_referencia.id"), nullable=False, index=True)

    alelo_1: Mapped[str] = mapped_column(String(50), nullable=False, default="?")
    alelo_2: Mapped[str] = mapped_column(String(50), nullable=False, default="?")
    alelo_3: Mapped[str | None] = mapped_column(String(50))
    alelo_4: Mapped[str | None] = mapped_column(String(50))

    genotipo_display: Mapped[str | None] = mapped_column(String(200))
    fenotipo_esperado: Mapped[str | None] = mapped_column(Text)

    confianza: Mapped[ConfianzaGenotipoEnum] = mapped_column(Enum(ConfianzaGenotipoEnum), nullable=False, default=ConfianzaGenotipoEnum.Desconocido)
    metodo_inferencia: Mapped[MetodoInferenciaEnum] = mapped_column(Enum(MetodoInferenciaEnum), nullable=False, default=MetodoInferenciaEnum.Desconocido)
    fuente_evidencia: Mapped[str | None] = mapped_column(Text)
    fecha_inferencia: Mapped[dt.date | None] = mapped_column(Date)
    inferido_por_cruce_id: Mapped[int | None] = mapped_column(ForeignKey("cruces.id"), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text)

    planta: Mapped[Planta] = relationship("Planta", back_populates="genotipos_loci")
    locus: Mapped[LocusReferencia] = relationship("LocusReferencia", back_populates="genotipos_planta")
    inferido_por_cruce: Mapped[Cruce | None] = relationship("Cruce")


class EpistasiaObservada(Base):
    __tablename__ = "epistasia_observada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    planta_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), nullable=False, index=True)
    locus_epistatico_id: Mapped[int] = mapped_column(ForeignKey("loci_referencia.id"), nullable=False)
    locus_hipostatico_id: Mapped[int] = mapped_column(ForeignKey("loci_referencia.id"), nullable=False)

    efecto_observado: Mapped[str | None] = mapped_column(Text)
    confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cruce_confirmacion_id: Mapped[int | None] = mapped_column(ForeignKey("cruces.id"), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text)

    planta: Mapped[Planta] = relationship("Planta", back_populates="epistasias")
    locus_epistatico: Mapped[LocusReferencia] = relationship("LocusReferencia", foreign_keys=[locus_epistatico_id])
    locus_hipostatico: Mapped[LocusReferencia] = relationship("LocusReferencia", foreign_keys=[locus_hipostatico_id])
    cruce_confirmacion: Mapped[Cruce | None] = relationship("Cruce")


class Cruce(Base):
    __tablename__ = "cruces"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_cruces_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    planta_madre_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), nullable=False)
    planta_padre_id: Mapped[int] = mapped_column(ForeignKey("plantas.id"), nullable=False)

    fecha_polinizacion: Mapped[dt.date] = mapped_column(Date, nullable=False)
    num_flores_polinizadas: Mapped[int | None] = mapped_column(Integer)

    fecundacion_confirmada: Mapped[FecundacionEnum] = mapped_column(Enum(FecundacionEnum), nullable=False, default=FecundacionEnum.Pendiente)
    fecha_confirmacion: Mapped[dt.date | None] = mapped_column(Date)

    num_capsulas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_semillas_totales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_semillas_sembradas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha_siembra: Mapped[dt.date | None] = mapped_column(Date)
    num_germinadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasa_germinacion: Mapped[float | None] = mapped_column(Float)

    resultado_esperado: Mapped[str | None] = mapped_column(Text)
    resultado_observado: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)

    fecha_creacion: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    madre: Mapped[Planta] = relationship("Planta", foreign_keys=[planta_madre_id])
    padre: Mapped[Planta] = relationship("Planta", foreign_keys=[planta_padre_id])

    capsulas: Mapped[list[Capsula]] = relationship("Capsula", back_populates="cruce", cascade="all, delete-orphan")
    fotos: Mapped[list[Foto]] = relationship("Foto", back_populates="cruce")


class Capsula(Base):
    __tablename__ = "capsulas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cruce_id: Mapped[int] = mapped_column(ForeignKey("cruces.id"), nullable=False, index=True)
    numero_capsula: Mapped[int] = mapped_column(Integer, nullable=False)

    fecha_fecundacion_estimada: Mapped[dt.date] = mapped_column(Date, nullable=False)
    fecha_recoleccion: Mapped[dt.date | None] = mapped_column(Date)

    estado: Mapped[EstadoCapsulaEnum] = mapped_column(Enum(EstadoCapsulaEnum), nullable=False, default=EstadoCapsulaEnum.Desarrollando)

    num_semillas_total: Mapped[int | None] = mapped_column(Integer)
    num_semillas_viables: Mapped[int | None] = mapped_column(Integer)
    num_semillas_inviables: Mapped[int | None] = mapped_column(Integer)

    notas: Mapped[str | None] = mapped_column(Text)

    cruce: Mapped[Cruce] = relationship("Cruce", back_populates="capsulas")
    semillas: Mapped[list[Semilla]] = relationship("Semilla", back_populates="capsula", cascade="all, delete-orphan")
    fotos: Mapped[list[Foto]] = relationship("Foto", back_populates="capsula")


class Semilla(Base):
    __tablename__ = "semillas"
    __table_args__ = (
        UniqueConstraint("codigo_semilla", name="uq_semillas_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capsula_id: Mapped[int] = mapped_column(ForeignKey("capsulas.id"), nullable=False, index=True)

    codigo_semilla: Mapped[str] = mapped_column(String(20), nullable=False)
    estado_viabilidad: Mapped[ViabilidadSemillaEnum] = mapped_column(Enum(ViabilidadSemillaEnum), nullable=False, default=ViabilidadSemillaEnum.Pendiente)

    fecha_siembra: Mapped[dt.date | None] = mapped_column(Date)
    germinada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_germinacion: Mapped[dt.date | None] = mapped_column(Date)

    planta_resultante_id: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True)

    notas: Mapped[str | None] = mapped_column(Text)

    capsula: Mapped[Capsula] = relationship("Capsula", back_populates="semillas")
    planta_resultante: Mapped[Planta | None] = relationship("Planta", foreign_keys=[planta_resultante_id])


class Foto(Base):
    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    planta_id: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True, index=True)
    cruce_id: Mapped[int | None] = mapped_column(ForeignKey("cruces.id"), nullable=True, index=True)
    capsula_id: Mapped[int | None] = mapped_column(ForeignKey("capsulas.id"), nullable=True, index=True)

    filename: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_filename: Mapped[str | None] = mapped_column(Text)

    etapa: Mapped[EtapaFotoEnum] = mapped_column(Enum(EtapaFotoEnum), nullable=False, default=EtapaFotoEnum.General)
    es_foto_principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    fecha_foto: Mapped[dt.date | None] = mapped_column(Date)

    descripcion: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)

    planta: Mapped[Planta | None] = relationship("Planta", back_populates="fotos")
    cruce: Mapped[Cruce | None] = relationship("Cruce", back_populates="fotos")
    capsula: Mapped[Capsula | None] = relationship("Capsula", back_populates="fotos")


class Segregacion(Base):
    __tablename__ = "segregacion"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_segregacion_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    cruce_parental_id: Mapped[int] = mapped_column(ForeignKey("cruces.id"), nullable=False)

    caracter_analizado: Mapped[str | None] = mapped_column(Text)
    total_hijos_florecidos: Mapped[int | None] = mapped_column(Integer)
    num_dominante: Mapped[int | None] = mapped_column(Integer)
    num_recesivo: Mapped[int | None] = mapped_column(Integer)

    proporcion_observada: Mapped[str | None] = mapped_column(Text)
    proporcion_esperada: Mapped[str | None] = mapped_column(Text)

    coincide: Mapped[CoincideEnum | None] = mapped_column(Enum(CoincideEnum))

    conclusion_genotipo: Mapped[str | None] = mapped_column(Text)
    actualiza_genotipo_de: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)

    cruce_parental: Mapped[Cruce] = relationship("Cruce")


class Tarea(Base):
    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tipo: Mapped[TipoTareaEnum] = mapped_column(Enum(TipoTareaEnum), nullable=False)

    planta_id: Mapped[int | None] = mapped_column(ForeignKey("plantas.id"), nullable=True, index=True)
    cruce_id: Mapped[int | None] = mapped_column(ForeignKey("cruces.id"), nullable=True, index=True)

    fecha_vencimiento: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    completada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_completada: Mapped[dt.date | None] = mapped_column(Date)

    descripcion: Mapped[str | None] = mapped_column(Text)
    prioridad: Mapped[PrioridadEnum] = mapped_column(Enum(PrioridadEnum), nullable=False, default=PrioridadEnum.Media)

    planta: Mapped[Planta | None] = relationship("Planta")
    cruce: Mapped[Cruce | None] = relationship("Cruce")


class GenReferencia(Base):
    __tablename__ = "genes_referencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gen: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    caracter_controlado: Mapped[str | None] = mapped_column(Text)
    alelo_dominante: Mapped[str | None] = mapped_column(Text)
    alelo_recesivo: Mapped[str | None] = mapped_column(Text)
    tipo_herencia: Mapped[str | None] = mapped_column(Text)
    nivel_evidencia: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)
