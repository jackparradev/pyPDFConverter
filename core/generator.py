"""
core/generator.py
=================
Motor de generación masiva de documentos .docx a partir de un archivo Excel
y un conjunto de imágenes localizadas en disco.

Responsabilidades
-----------------
* Implementar ``MassGenerator``, replicando exactamente el patrón de
  inyección de callbacks de ``MassConverter.__init__``.
* Leer todas las filas del Excel con ``ExcelParser``.
* Filtrar opcionalmente las filas por el campo ``grupo`` antes de procesar.
* Por cada fila: localizar las imágenes con ``AssetLocator``, construir el
  documento con ``TemplateBuilder`` y guardarlo en la carpeta de salida.
* Registrar cada resultado (éxito o fallo) en un ``GenerationBatchResult``
  y notificar a la UI mediante los callbacks tipados.
* Respetar la señal de cancelación cooperativa (``threading.Event``).

Prohibiciones
-------------
* No usar ``win32com`` ni ``WordEngine``.
* No importar nada de ``ui/``.
* No detener el lote ante el error de una fila individual; solo registrar
  y continuar.
"""

from __future__ import annotations

import threading
import logging
from pathlib import Path
from typing import Callable, Any

from core.models import GenerationResult, GenerationBatchResult
from core.excel_parser import ExcelParser
from core.asset_locator import (
    AssetLocator,
    ArchivosFaltantesError,
    CarpetaAmbiguaError,
    FechaInvalidaError,
)
from core.template_builder import TemplateBuilder

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aliases de callbacks (mismo contrato que MassConverter)
# ---------------------------------------------------------------------------
LogCallback      = Callable[[str, str], None]   # (mensaje, tipo)
ProgressCallback = Callable[[float], None]      # 0.0 a 1.0
DoneCallback     = Callable[[GenerationBatchResult], None]


class MassGenerator:
    """
    Genera masivamente documentos ``.docx`` a partir de un Excel de
    infracciones y una carpeta de evidencias en disco.

    El diseño replica fielmente el patrón de ``MassConverter``:
    inyección de callbacks en ``__init__`` + método ``ejecutar()`` pensado
    para correr en un hilo daemon.

    Uso típico
    ----------
    >>> gen = MassGenerator(
    ...     log=mi_log,
    ...     progreso=mi_progreso,
    ...     al_terminar=mi_al_terminar,
    ...     cancelar=mi_evento,
    ... )
    >>> hilo = threading.Thread(
    ...     target=gen.ejecutar,
    ...     args=(ruta_excel, carpeta_imagenes, carpeta_salida, ruta_plantilla),
    ...     kwargs={"filtro_grupo": "GRUPO_A"},
    ...     daemon=True,
    ... )
    >>> hilo.start()

    Contratos de callbacks
    ----------------------
    * ``log(mensaje: str, tipo: str)`` — tipos válidos:
      ``"info"``, ``"normal"``, ``"ok"``, ``"error"``, ``"warn"``, ``"sep"``
    * ``progreso(fraccion: float)`` — rango ``[0.0, 1.0]``
    * ``al_terminar(GenerationBatchResult)`` — llamado siempre al finalizar,
      incluso si hubo errores o cancelación.
    """

    def __init__(
        self,
        log: LogCallback,
        progreso: ProgressCallback,
        al_terminar: DoneCallback,
        cancelar: threading.Event,
    ) -> None:
        self._log         = log
        self._progreso    = progreso
        self._al_terminar = al_terminar
        self._cancelar    = cancelar

        self._parser   = ExcelParser()
        self._locator  = AssetLocator()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def ejecutar(
        self,
        ruta_excel: str | Path,
        carpeta_imagenes: str | Path,
        carpeta_salida: str | Path,
        ruta_plantilla: str | Path,
        filtro_grupo: str | None = None,
    ) -> None:
        """
        Orquesta el flujo completo de generación masiva.

        Parámetros
        ----------
        ruta_excel : str | Path
            Ruta al archivo ``.xlsx`` con los datos de infracciones.
        carpeta_imagenes : str | Path
            Carpeta raíz que contiene las subcarpetas de evidencia.
        carpeta_salida : str | Path
            Carpeta donde se guardarán los ``.docx`` generados.
            Se crea automáticamente si no existe.
        ruta_plantilla : str | Path
            Ruta al archivo ``.docx`` que actúa como plantilla Jinja2.
        filtro_grupo : str | None
            Si se indica, solo se procesan las filas cuyo campo ``grupo``
            coincida exactamente (case-insensitive) con este valor.
            ``None`` o cadena vacía = procesar todas las filas.
        """
        ruta_excel       = Path(ruta_excel)
        carpeta_imagenes = Path(carpeta_imagenes)
        carpeta_salida   = Path(carpeta_salida)
        ruta_plantilla   = Path(ruta_plantilla)

        resultado = GenerationBatchResult()

        # --- Leer Excel ---
        try:
            filas = self._parser.leer(ruta_excel)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            self._log(f"❌  Error al leer el Excel: {exc}", "error")
            self._al_terminar(resultado)
            return

        resultado.total = len(filas)

        # --- Filtrar por grupo (si se especificó) ---
        grupo_normalizado = filtro_grupo.strip() if filtro_grupo else ""
        if grupo_normalizado:
            def _grupo_str(valor: Any) -> str:
                """Convierte el valor de celda a string normalizado.
                Enteros y floats enteros (ej. 26.0) se convierten a '26'.
                """
                if isinstance(valor, float) and valor.is_integer():
                    return str(int(valor))
                return str(valor).strip() if valor is not None else ""

            filas_filtradas = [
                f for f in filas
                if _grupo_str(f.get("grupo")).lower() == grupo_normalizado.lower()
            ]
            self._log(
                f"🔍  Filtro de grupo: '{grupo_normalizado}' — "
                f"{len(filas_filtradas)} de {len(filas)} fila(s) seleccionadas.",
                "info",
            )
            if not filas_filtradas:
                self._log(
                    f"⚠  Ninguna fila coincide con el grupo '{grupo_normalizado}'. "
                    "Verifique el valor exacto en la columna 'Grupo' del Excel.",
                    "warn",
                )
                self._al_terminar(resultado)
                return
            filas = filas_filtradas

        # --- Validar plantilla ---
        try:
            builder = TemplateBuilder(ruta_plantilla)
        except FileNotFoundError as exc:
            self._log(f"❌  {exc}", "error")
            self._al_terminar(resultado)
            return

        # --- Crear carpeta de salida ---
        carpeta_salida.mkdir(parents=True, exist_ok=True)

        self._log(f"📂  Excel       : {ruta_excel}", "info")
        self._log(f"🖼️   Imágenes    : {carpeta_imagenes}", "info")
        self._log(f"📁  Salida      : {carpeta_salida}", "info")
        if grupo_normalizado:
            self._log(f"🔍  Grupo       : {grupo_normalizado}", "info")
        self._log(f"📄  Registros   : {len(filas)}\n", "info")

        # --- Procesar lote ---
        self._procesar_lote(
            filas=filas,
            carpeta_imagenes=carpeta_imagenes,
            carpeta_salida=carpeta_salida,
            builder=builder,
            resultado=resultado,
        )

        resultado.cancelado = self._cancelar.is_set()
        self._mostrar_resumen(resultado)
        self._al_terminar(resultado)

    # ------------------------------------------------------------------
    # Procesamiento del lote
    # ------------------------------------------------------------------

    def _procesar_lote(
        self,
        filas: list[dict[str, Any]],
        carpeta_imagenes: Path,
        carpeta_salida: Path,
        builder: TemplateBuilder,
        resultado: GenerationBatchResult,
    ) -> None:
        """
        Itera las filas del Excel y genera un documento por cada una.

        Por cada fila:
        1. Verifica cancelación cooperativa.
        2. Llama a ``AssetLocator`` — captura las 3 excepciones por separado.
        3. Si el localizador tiene éxito, genera el ``.docx`` con
           ``TemplateBuilder``.
        4. Registra el resultado (éxito o fallo) en ``GenerationBatchResult``
           y continúa con la siguiente fila.
        """
        total = len(filas)

        for idx, fila in enumerate(filas, start=1):

            # --- Cancelación cooperativa ---
            if self._cancelar.is_set():
                self._log("\n🛑  Generación cancelada por el usuario.", "warn")
                break

            placa       = str(fila.get("placa", "") or "")
            correlativo = str(fila.get("correlativo", "") or "")
            fecha_texto = str(fila.get("fecha_fuga_texto", "") or "")

            self._log(f"[{idx}/{total}]  {correlativo} — {placa}", "normal")

            # --- Localizar imágenes ---
            gen_result = self._procesar_fila(
                fila=fila,
                placa=placa,
                correlativo=correlativo,
                fecha_texto=fecha_texto,
                carpeta_imagenes=carpeta_imagenes,
                carpeta_salida=carpeta_salida,
                builder=builder,
                idx_fila=idx,
            )

            # --- Registrar resultado ---
            if gen_result.exitoso:
                resultado.exitosos.append(gen_result)
                self._log(
                    f"         ✓  {gen_result.ruta_destino.name}",  # type: ignore[union-attr]
                    "ok",
                )
            else:
                resultado.fallidos.append(gen_result)
                self._log(
                    f"         ✗  {gen_result.motivo_error}",
                    "error",
                )

            self._progreso(idx / total)

    def _procesar_fila(
        self,
        fila: dict[str, Any],
        placa: str,
        correlativo: str,
        fecha_texto: str,
        carpeta_imagenes: Path,
        carpeta_salida: Path,
        builder: TemplateBuilder,
        idx_fila: int,
    ) -> GenerationResult:
        """
        Intenta localizar imágenes y generar el documento para una sola fila.

        Devuelve siempre un ``GenerationResult``; nunca propaga excepciones.
        """
        # --- Paso 1: localizar imágenes ---
        try:
            rutas_imagenes = self._locator.localizar_imagenes(
                carpeta_general=carpeta_imagenes,
                placa=placa,
                fecha_texto=fecha_texto,
            )
        except ArchivosFaltantesError as exc:
            archivos_faltantes = exc.archivos_faltantes
            self._log(
                f"⚠  Faltan imágenes para el registro {placa}: {archivos_faltantes}",
                "warn",
            )
            return GenerationResult(
                correlativo=correlativo,
                fila_excel=idx_fila,
                exitoso=False,
                motivo_error=str(exc),
                datos_fila=dict(fila),
            )

        except CarpetaAmbiguaError as exc:
            self._log(
                f"⚠  ALERTA: Múltiples carpetas coinciden para la placa {placa} "
                "— registro omitido, requiere revisión manual",
                "warn",
            )
            return GenerationResult(
                correlativo=correlativo,
                fila_excel=idx_fila,
                exitoso=False,
                motivo_error=str(exc),
                datos_fila=dict(fila),
            )

        except FechaInvalidaError as exc:
            valor_original = exc.valor_original
            self._log(
                f"⚠  Error: formato de fecha inválido en registro {placa} "
                f"— valor recibido: '{valor_original}'",
                "warn",
            )
            return GenerationResult(
                correlativo=correlativo,
                fila_excel=idx_fila,
                exitoso=False,
                motivo_error=str(exc),
                datos_fila=dict(fila),
            )

        # --- Paso 2: generar el .docx ---
        nombre_archivo = f"{correlativo}_{placa}.docx"
        ruta_destino   = carpeta_salida / nombre_archivo

        try:
            ruta_final = builder.generar(
                datos_fila=fila,
                rutas_imagenes=rutas_imagenes,
                ruta_destino=ruta_destino,
            )
        except Exception as exc:  # noqa: BLE001
            motivo = f"Error al generar el documento: {exc}"
            logger.error(
                "Error generando '%s': %s",
                nombre_archivo, exc, exc_info=True,
            )
            return GenerationResult(
                correlativo=correlativo,
                fila_excel=idx_fila,
                exitoso=False,
                motivo_error=motivo,
                datos_fila=dict(fila),
            )

        return GenerationResult(
            correlativo=correlativo,
            fila_excel=idx_fila,
            exitoso=True,
            ruta_destino=ruta_final,
            datos_fila=dict(fila),
        )

    # ------------------------------------------------------------------
    # Resumen final
    # ------------------------------------------------------------------

    def _mostrar_resumen(self, resultado: GenerationBatchResult) -> None:
        """Emite el bloque de resumen al log al finalizar el lote."""
        self._log("\n" + "─" * 45, "sep")
        self._log(f"✅  Exitosos  : {resultado.cantidad_exitosos}", "ok")

        if resultado.fallidos:
            self._log(f"❌  Fallidos  : {resultado.cantidad_fallidos}", "error")
            for identificador, motivo in resultado.resumen_fallidos:
                self._log(f"    · {identificador}: {motivo}", "error")
        else:
            self._log("   Sin errores.", "ok")

        if resultado.cancelado:
            self._log("⚠  El proceso fue cancelado antes de finalizar.", "warn")

        self._log("─" * 45, "sep")
