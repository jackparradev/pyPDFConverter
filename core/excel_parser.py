"""
core/excel_parser.py
====================
Parser del archivo Excel de infracciones de tráfico para Docusol.

Responsabilidades
-----------------
* Leer un archivo ``.xlsx`` usando ``openpyxl`` (modo sólo-lectura,
  optimizado para memoria).
* Mapear **exactamente** las 10 cabeceras acordadas a llaves normalizadas.
* Ignorar cualquier columna adicional que el archivo pudiera contener.
* Devolver una lista de ``dict[str, Any]`` lista para ser consumida por
  el motor de generación de documentos.
* Lanzar excepciones descriptivas en español ante cualquier problema de
  lectura o estructura del archivo.

Prohibiciones
-------------
* Este módulo **no** debe importar nada de la carpeta ``ui/``.
* No debe escribir archivos en disco ni conectarse a servicios externos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeo canónico: cabecera del Excel → llave normalizada del diccionario
# ---------------------------------------------------------------------------
MAPA_CABECERAS: dict[str, str] = {
    "Correlativo":              "correlativo",
    "Placa":                    "placa",
    "Fecha_y_Hora_de_Fuga_Texto": "fecha_fuga_texto",
    "Categoría":                "categoria",
    "Estación_de_Peaje":        "estacion_peaje",
    "Ubicación":                "ubicacion",
    "Distrito":                 "distrito",
    "Sentido":                  "sentido",
    "Provincia":                "provincia",
    "URL_EVIDENCIA":            "url_evidencia",
    "Tarifa (S/. incl. IGV)":   "tarifa",
}

# Columnas opcionales: se leen si existen, se ignoran silenciosamente si no.
MAPO_CABECERAS_OPCIONALES: dict[str, str] = {
    "Grupo": "grupo",
    "VIA":   "via",
}


class ExcelParser:
    """
    Lee el archivo ``.xlsx`` de infracciones y extrae los datos de cada fila
    como un diccionario normalizado.

    Uso típico
    ----------
    >>> parser = ExcelParser()
    >>> filas = parser.leer(Path("infracciones.xlsx"))
    >>> for fila in filas:
    ...     print(fila["correlativo"], fila["placa"])

    Notas
    -----
    * El parser usa el modo ``read_only=True`` de ``openpyxl`` para
      minimizar el consumo de memoria con archivos grandes.
    * La primera fila del Excel **siempre** se trata como cabecera.
    * Las filas completamente vacías se omiten con una advertencia en el log.
    * Si una cabecera requerida no se encuentra en el archivo, se lanza
      ``ValueError`` con la lista de columnas faltantes.
    """

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def leer(self, ruta_archivo: Path) -> list[dict[str, Any]]:
        """
        Lee el archivo Excel y devuelve una lista de diccionarios normalizados.

        Parámetros
        ----------
        ruta_archivo : Path
            Ruta absoluta o relativa al archivo ``.xlsx``.

        Devuelve
        --------
        list[dict[str, Any]]
            Lista con un diccionario por cada fila de datos válida.
            Las llaves son siempre las 10 llaves normalizadas definidas en
            ``MAPA_CABECERAS``.

        Lanza
        -----
        FileNotFoundError
            Si la ruta no existe o no apunta a un archivo regular.
        ValueError
            Si el archivo no tiene extensión ``.xlsx``, está vacío,
            le faltan cabeceras requeridas, o no contiene filas de datos.
        RuntimeError
            Si ``openpyxl`` no puede abrir el archivo (corrupto,
            protegido con contraseña, etc.).
        """
        ruta = Path(ruta_archivo)
        self._validar_ruta(ruta)

        logger.info("Abriendo archivo Excel: %s", ruta)
        libro = self._abrir_libro(ruta)

        try:
            hoja = self._obtener_hoja_activa(libro, ruta)
            indices_columnas = self._extraer_indices_cabecera(hoja, ruta)
            filas = self._extraer_filas(hoja, indices_columnas, ruta)
        finally:
            # En Windows, openpyxl (read_only) mantiene el ZipFile abierto
            # hasta que se llama a close() explícitamente.
            libro.close()

        logger.info(
            "Lectura completada: %d filas válidas extraídas de '%s'.",
            len(filas),
            ruta.name,
        )
        return filas

    # ------------------------------------------------------------------
    # Métodos privados de validación y lectura
    # ------------------------------------------------------------------

    def _validar_ruta(self, ruta: Path) -> None:
        """Verifica existencia y extensión del archivo."""
        if not ruta.exists():
            raise FileNotFoundError(
                f"El archivo no existe: '{ruta}'"
            )
        if not ruta.is_file():
            raise FileNotFoundError(
                f"La ruta no apunta a un archivo regular: '{ruta}'"
            )
        if ruta.suffix.lower() != ".xlsx":
            raise ValueError(
                f"El archivo debe tener extensión '.xlsx'. "
                f"Se recibió: '{ruta.suffix}' (archivo: '{ruta.name}')"
            )

    def _abrir_libro(self, ruta: Path) -> openpyxl.Workbook:
        """
        Abre el libro de Excel en modo sólo-lectura.

        Lanza ``RuntimeError`` con mensaje en español si ``openpyxl``
        no puede procesar el archivo.
        """
        try:
            return openpyxl.load_workbook(
                filename=str(ruta),
                read_only=True,
                data_only=True,   # lee valores calculados, no fórmulas
            )
        except InvalidFileException as exc:
            raise RuntimeError(
                f"El archivo '{ruta.name}' está dañado o no es un Excel válido. "
                f"Detalle técnico: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"No se pudo abrir el archivo '{ruta.name}'. "
                f"Verifique que no esté abierto en otra aplicación y que no "
                f"requiera contraseña. Detalle técnico: {exc}"
            ) from exc

    def _obtener_hoja_activa(
        self, libro: openpyxl.Workbook, ruta: Path
    ) -> Any:
        """
        Retorna la primera hoja del libro.

        Lanza ``ValueError`` si el libro no contiene ninguna hoja con datos.
        """
        hoja = libro.active
        if hoja is None:
            raise ValueError(
                f"El archivo '{ruta.name}' no contiene ninguna hoja activa. "
                "Verifique que el archivo no esté vacío."
            )
        logger.debug("Hoja activa seleccionada: '%s'", hoja.title)
        return hoja

    def _extraer_indices_cabecera(
        self, hoja: Any, ruta: Path
    ) -> dict[str, int]:
        """
        Lee la primera fila y construye un mapa ``llave_normalizada → índice``.

        Lanza ``ValueError`` si la hoja está vacía o si alguna cabecera
        requerida no se encuentra.
        """
        filas_iter = iter(hoja.iter_rows(values_only=True))
        try:
            fila_cabecera: tuple[Any, ...] | None = next(filas_iter)
        except StopIteration:
            raise ValueError(
                f"El archivo '{ruta.name}' está completamente vacío "
                "(no tiene ninguna fila, ni siquiera cabecera)."
            )

        if fila_cabecera is None or all(c is None for c in fila_cabecera):
            raise ValueError(
                f"La primera fila del archivo '{ruta.name}' está vacía. "
                "Se esperaba una fila de cabeceras."
            )

        # Construir mapa: cabecera_excel → índice de columna (0-based)
        cabeceras_presentes: dict[str, int] = {}
        for idx, valor in enumerate(fila_cabecera):
            if valor is not None:
                cabeceras_presentes[str(valor).strip()] = idx

        logger.debug(
            "Cabeceras encontradas en el archivo: %s",
            list(cabeceras_presentes.keys()),
        )

        # Verificar que todas las cabeceras requeridas estén presentes
        cabeceras_faltantes = [
            cab for cab in MAPA_CABECERAS if cab not in cabeceras_presentes
        ]
        if cabeceras_faltantes:
            raise ValueError(
                f"El archivo '{ruta.name}' no contiene las siguientes "
                f"columnas requeridas: {cabeceras_faltantes}. "
                "Verifique que el Excel corresponde a la plantilla de "
                "infracciones de Docusol."
            )

        # Retornar los índices de columnas requeridas
        indices: dict[str, int] = {
            llave_normalizada: cabeceras_presentes[cabecera_excel]
            for cabecera_excel, llave_normalizada in MAPA_CABECERAS.items()
        }

        # Agregar columnas opcionales si están presentes en el archivo
        for cabecera_excel, llave_normalizada in MAPO_CABECERAS_OPCIONALES.items():
            if cabecera_excel in cabeceras_presentes:
                indices[llave_normalizada] = cabeceras_presentes[cabecera_excel]
                logger.debug("Columna opcional '%s' encontrada.", cabecera_excel)
            else:
                logger.debug("Columna opcional '%s' no presente, se omite.", cabecera_excel)

        logger.debug("Índices de columnas mapeados: %s", indices)
        return indices

    def _extraer_filas(
        self,
        hoja: Any,
        indices_columnas: dict[str, int],
        ruta: Path,
    ) -> list[dict[str, Any]]:
        """
        Itera las filas de datos (saltando la cabecera) y construye los
        diccionarios normalizados.

        Las filas completamente vacías se omiten con advertencia en el log.
        """
        filas_resultado: list[dict[str, Any]] = []
        numero_fila_datos = 0  # contador relativo a datos (sin cabecera)

        for numero_fila_excel, fila in enumerate(
            hoja.iter_rows(min_row=2, values_only=True), start=2
        ):
            # Saltar filas totalmente vacías
            if fila is None or all(celda is None for celda in fila):
                logger.warning(
                    "Fila %d de '%s' completamente vacía, se omite.",
                    numero_fila_excel,
                    ruta.name,
                )
                continue

            numero_fila_datos += 1
            registro: dict[str, Any] = {}

            for llave_normalizada, idx_columna in indices_columnas.items():
                valor_crudo = (
                    fila[idx_columna] if idx_columna < len(fila) else None
                )
                registro[llave_normalizada] = self._limpiar_valor(valor_crudo)

            filas_resultado.append(registro)
            logger.debug(
                "Fila %d procesada → correlativo='%s'",
                numero_fila_excel,
                registro.get("correlativo"),
            )

        if not filas_resultado:
            raise ValueError(
                f"El archivo '{ruta.name}' no contiene filas de datos. "
                "Sólo se encontró la fila de cabeceras (o filas vacías)."
            )

        return filas_resultado

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def _limpiar_valor(valor: Any) -> Any:
        """
        Normaliza el valor de una celda:

        * Las cadenas de texto se eliminan espacios al inicio/fin.
        * ``None`` se devuelve tal cual para que el consumidor decida.
        * Los tipos numéricos, fechas y booleanos se devuelven sin cambio.
        """
        if isinstance(valor, str):
            return valor.strip()
        return valor
