from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConversionResult:
    """Resultado de convertir un único archivo DOCX a PDF."""
    source: Path
    target: Path
    success: bool
    error: str = ""

    @property
    def filename(self) -> str:
        return self.source.name


@dataclass
class BatchResult:
    """Resultado global de una conversión masiva."""
    total: int = 0
    successful: list[ConversionResult] = field(default_factory=list)
    failed: list[ConversionResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def processed_count(self) -> int:
        return self.success_count + self.failure_count


# ---------------------------------------------------------------------------
# Modelos para la generación masiva de documentos desde Excel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationResult:
    """
    Resultado inmutable de intentar generar un documento a partir de
    una única fila del Excel de infracciones.

    Atributos
    ---------
    correlativo : str
        Identificador único de la fila (columna «Correlativo»).
    fila_excel : int
        Número de fila en el Excel (base 1, sin contar cabecera).
    exitoso : bool
        ``True`` si el documento se generó sin errores.
    ruta_destino : Path | None
        Ruta absoluta al archivo generado; ``None`` si falló.
    motivo_error : str
        Descripción del error en caso de fallo; cadena vacía si fue exitoso.
    datos_fila : dict[str, Any]
        Copia de los datos normalizados que provienen del parser de Excel.
    """

    correlativo: str
    fila_excel: int
    exitoso: bool
    ruta_destino: Path | None = None
    motivo_error: str = ""
    datos_fila: dict[str, Any] = field(default_factory=dict)

    @property
    def identificador(self) -> str:
        """Etiqueta legible para logs: «fila 3 – correlativo ABC-001»."""
        return f"fila {self.fila_excel} – correlativo {self.correlativo}"


@dataclass
class GenerationBatchResult:
    """
    Resultado agregado de una corrida de generación masiva de documentos
    a partir de un archivo Excel.

    A diferencia de ``BatchResult``, esta clase *no* es frozen porque la
    UI y el motor de generación la van completando de forma incremental.

    Atributos
    ---------
    total : int
        Total de filas leídas del Excel (incluyendo omitidas).
    exitosos : list[GenerationResult]
        Filas procesadas correctamente.
    fallidos : list[GenerationResult]
        Filas que produjeron un error con su motivo detallado.
    cancelado : bool
        ``True`` si el usuario interrumpió el proceso antes de completarse.
    """

    total: int = 0
    exitosos: list[GenerationResult] = field(default_factory=list)
    fallidos: list[GenerationResult] = field(default_factory=list)
    cancelado: bool = False

    @property
    def cantidad_exitosos(self) -> int:
        """Número de documentos generados correctamente."""
        return len(self.exitosos)

    @property
    def cantidad_fallidos(self) -> int:
        """Número de filas que fallaron durante la generación."""
        return len(self.fallidos)

    @property
    def cantidad_procesados(self) -> int:
        """Total de filas intentadas (exitosas + fallidas)."""
        return self.cantidad_exitosos + self.cantidad_fallidos

    @property
    def resumen_fallidos(self) -> list[tuple[str, str]]:
        """
        Lista de tuplas ``(identificador, motivo_error)`` para todas las
        filas fallidas; útil para mostrar en la UI o en el log.
        """
        return [(r.identificador, r.motivo_error) for r in self.fallidos]