"""
core/asset_locator.py
=====================
Localizador determinista de imágenes en disco para Docusol.

Responsabilidades
-----------------
* Parsear una fecha en formato ``DD/MM/YYYY HH:MM`` y derivar los formatos
  necesarios para identificar la subcarpeta y los nombres de archivo.
* Encontrar de forma no ambigua la subcarpeta correspondiente a un registro
  dentro de una carpeta general de evidencias.
* Localizar las tres imágenes obligatorias de cada registro (cámara de placa,
  fuga e informe SUNARP) y devolver sus rutas absolutas.

Prohibiciones
-------------
* Este módulo **no** debe importar nada de la carpeta ``ui/``.
* No debe escribir archivos en disco ni conectarse a servicios externos.
* Solo se permite ``pathlib.Path`` de la librería estándar para rutas.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones personalizadas
# ---------------------------------------------------------------------------

class FechaInvalidaError(Exception):
    """
    Se lanza cuando ``fecha_texto`` no puede ser parseada como
    ``DD/MM/YYYY HH:MM``.

    Atributos
    ---------
    placa : str
        Placa del vehículo involucrado en la búsqueda.
    valor_original : str
        El texto de fecha tal como llegó al método, sin modificaciones.
    """

    def __init__(self, placa: str, valor_original: str) -> None:
        self.placa = placa
        self.valor_original = valor_original
        super().__init__(
            f"La fecha '{valor_original}' para la placa '{placa}' no tiene el "
            "formato esperado DD/MM/YYYY HH:MM (24 h). "
            "Verifique el valor en el Excel."
        )


class CarpetaAmbiguaError(Exception):
    """
    Se lanza cuando se encuentran dos o más subcarpetas que coinciden con
    la placa y la fecha indicadas; el sistema no puede elegir automáticamente.

    Atributos
    ---------
    placa : str
        Placa del vehículo involucrado en la búsqueda.
    carpetas_candidatas : list[Path]
        Lista de rutas que satisfacen los criterios de búsqueda.
    """

    def __init__(self, placa: str, carpetas_candidatas: list[Path]) -> None:
        self.placa = placa
        self.carpetas_candidatas = carpetas_candidatas
        nombres = [str(c) for c in carpetas_candidatas]
        super().__init__(
            f"Se encontraron {len(carpetas_candidatas)} carpetas para la placa "
            f"'{placa}'. El sistema no puede determinar cuál usar automáticamente. "
            f"Carpetas encontradas: {nombres}. "
            "Corrija la ambigüedad renombrando o eliminando duplicados."
        )


class ArchivosFaltantesError(Exception):
    """
    Se lanza cuando no se encuentra la carpeta del registro o cuando faltan
    una o más de las imágenes obligatorias dentro de dicha carpeta.

    Atributos
    ---------
    placa : str
        Placa del vehículo involucrado en la búsqueda.
    archivos_faltantes : list[str]
        Nombres base (sin extensión) de los archivos o recursos ausentes.
    """

    def __init__(self, placa: str, archivos_faltantes: list[str]) -> None:
        self.placa = placa
        self.archivos_faltantes = archivos_faltantes
        detalle = ", ".join(f"'{a}'" for a in archivos_faltantes)
        super().__init__(
            f"No se encontraron los siguientes recursos para la placa '{placa}': "
            f"{detalle}. Verifique que los archivos existen en la carpeta correcta "
            "y que sus nombres respetan el esquema acordado."
        )


# ---------------------------------------------------------------------------
# Extensiones de imagen aceptadas (minúsculas para comparación insensible)
# ---------------------------------------------------------------------------
_EXTENSIONES_IMAGEN: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})


# ---------------------------------------------------------------------------
# Localizador principal
# ---------------------------------------------------------------------------

class AssetLocator:
    """
    Localiza de forma determinista las tres imágenes obligatorias de un
    registro de infracción dentro de una jerarquía de carpetas en disco.

    Uso típico
    ----------
    >>> locator = AssetLocator()
    >>> rutas = locator.localizar_imagenes(
    ...     carpeta_general=Path("D:/Evidencias"),
    ...     placa="A1B-123",
    ...     fecha_texto="11/06/2026 14:30",
    ... )
    >>> print(rutas["img_cam"])
    D:/Evidencias/A1B-123 VIA 100 11-06-2026/IMG_CAM_PLACA_A1B123_20260611.jpg

    Notas
    -----
    * El método nunca retorna ``None``: si algo falla, siempre lanza una de las
      tres excepciones personalizadas definidas en este módulo.
    * La búsqueda de imágenes es insensible a mayúsculas/minúsculas en la
      extensión (``.jpg``, ``.JPG``, ``.Jpg``, etc. se aceptan por igual).
    * La identificación de la subcarpeta requiere que el nombre de la carpeta
      contenga **tanto** la placa original (con guion) **como** la fecha en
      formato ``DD-MM-YYYY``.
    """

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def localizar_imagenes(
        self,
        carpeta_general: Path,
        placa: str,
        fecha_texto: str,
        via: str = "",
    ) -> dict[str, Path]:
        """
        Localiza las tres imágenes de un registro y devuelve sus rutas absolutas.

        Parámetros
        ----------
        carpeta_general : Path
            Directorio raíz que contiene las subcarpetas de cada registro.
            Puede ser relativa o absoluta; se resolverá a ruta absoluta.
        placa : str
            Placa del vehículo tal como aparece en el Excel, por ejemplo
            ``'A1B-123'``.  Puede contener guion y/o espacios.
        fecha_texto : str
            Fecha y hora de la infracción en formato ``DD/MM/YYYY HH:MM``
            (reloj de 24 horas), por ejemplo ``'11/06/2026 14:30'``.
        via : str
            Número o identificador de vía tal como aparece en el Excel
            (columna ``VIA``), por ejemplo ``'102'`` o ``'VIA 102'``.
            Se usa como desempate cuando hay varias carpetas con la misma
            placa y fecha (ej. ``BAY-402 VIA 102 26-06-2026`` vs
            ``BAY-402 VIA 111 26-06-2026``).  Si está vacío se ignora.

        Devuelve
        --------
        dict[str, Path]
            Diccionario con tres claves:

            * ``'img_cam'``   → ruta a ``IMG_CAM_PLACA_{placa_limpia}_{fecha_archivo}.*``
            * ``'img_fuga'``  → ruta a ``IMG_FUGA_{placa_limpia}_{fecha_archivo}.*``
            * ``'img_sunarp'``→ ruta a ``CONSULTA SUNARP PLACA {placa_original}.*``

            Todas las rutas son absolutas.

        Lanza
        -----
        FechaInvalidaError
            Si ``fecha_texto`` no puede parsearse como ``DD/MM/YYYY HH:MM``.
        CarpetaAmbiguaError
            Si se encuentran dos o más subcarpetas candidatas y el campo ``via``
            no logra desempatar entre ellas.
        ArchivosFaltantesError
            Si no existe ninguna subcarpeta candidata, o si falta al menos una
            de las tres imágenes obligatorias dentro de la subcarpeta encontrada.
        """
        # Paso 1 — Parseo de fecha y derivación de formatos
        fecha_dt = self._parsear_fecha(placa, fecha_texto)
        fecha_archivo = fecha_dt.strftime("%Y%m%d")   # ej. 20260611
        fecha_carpeta = fecha_dt.strftime("%d-%m-%Y")  # ej. 11-06-2026

        logger.debug(
            "Placa='%s' | fecha_archivo='%s' | fecha_carpeta='%s'",
            placa, fecha_archivo, fecha_carpeta,
        )

        # Paso 2 — Limpieza de placa
        placa_original = placa                              # conserva guion
        placa_limpia = placa.replace("-", "").replace(" ", "")  # A1B123

        logger.debug(
            "placa_original='%s' | placa_limpia='%s'",
            placa_original, placa_limpia,
        )

        # Paso 3 — Identificación de subcarpeta
        carpeta_registro = self._identificar_subcarpeta(
            carpeta_general=Path(carpeta_general).resolve(),
            placa_original=placa_original,
            placa=placa,
            fecha_carpeta=fecha_carpeta,
            via=str(via).strip() if via else "",
        )

        # Paso 4 — Búsqueda de las 3 imágenes
        rutas = self._buscar_imagenes(
            carpeta_registro=carpeta_registro,
            placa_original=placa_original,
            placa_limpia=placa_limpia,
            fecha_archivo=fecha_archivo,
        )

        logger.info(
            "Imágenes localizadas para placa '%s': %s",
            placa_original,
            {k: str(v) for k, v in rutas.items()},
        )
        return rutas

    # ------------------------------------------------------------------
    # Métodos privados — cada paso del algoritmo
    # ------------------------------------------------------------------

    def _parsear_fecha(self, placa: str, fecha_texto: str) -> datetime:
        """
        Parsea ``fecha_texto`` con el formato ``DD/MM/YYYY HH:MM``.

        Lanza :exc:`FechaInvalidaError` si el formato es incorrecto.
        """
        try:
            return datetime.strptime(fecha_texto, "%d/%m/%Y %H:%M")
        except ValueError as exc:
            logger.error(
                "Fecha inválida para placa '%s': '%s'. Detalle: %s",
                placa, fecha_texto, exc,
            )
            raise FechaInvalidaError(placa, fecha_texto) from exc

    def _identificar_subcarpeta(
        self,
        carpeta_general: Path,
        placa_original: str,
        placa: str,
        fecha_carpeta: str,
        via: str = "",
    ) -> Path:
        """
        Busca dentro de ``carpeta_general`` un directorio cuyo nombre contenga
        **tanto** ``placa_original`` **como** ``fecha_carpeta``.

        La búsqueda es insensible a mayúsculas y se limita al nombre de la
        carpeta (``entry.name``), no a su ruta completa, para evitar falsos
        positivos cuando subcarpetas internas heredan el nombre del padre
        en la ruta.  Se busca en todos los niveles pero comparando solo el
        nombre del directorio en cada nivel.

        Reglas
        ------
        * 0 candidatas → :exc:`ArchivosFaltantesError`
        * 2 o más candidatas → :exc:`CarpetaAmbiguaError`
        * Exactamente 1 → devuelve esa carpeta

        Parámetros
        ----------
        carpeta_general : Path
            Directorio raíz resuelto a ruta absoluta.
        placa_original : str
            Placa con guion, tal como aparece en el nombre de carpeta.
        placa : str
            Placa original recibida por el llamador (para mensajes de error).
        fecha_carpeta : str
            Fecha en formato ``DD-MM-YYYY``.
        """
        placa_lower = placa_original.lower()
        fecha_lower = fecha_carpeta.lower()

        candidatas: list[Path] = [
            entrada
            for entrada in carpeta_general.rglob("*")
            if entrada.is_dir()
            and placa_lower in entrada.name.lower()
            and fecha_lower in entrada.name.lower()
        ]

        # Eliminar subcarpetas redundantes: si una carpeta candidata es
        # ancestro de otra candidata, conservar solo la más superficial.
        # Esto evita que subcarpetas internas de una carpeta válida
        # provoquen un falso CarpetaAmbiguaError.
        candidatas_filtradas: list[Path] = []
        for c in candidatas:
            es_subcarpeta_de_otra = any(
                c != otra and c.is_relative_to(otra)
                for otra in candidatas
            )
            if not es_subcarpeta_de_otra:
                candidatas_filtradas.append(c)

        logger.debug(
            "Subcarpetas candidatas para placa='%s', fecha='%s': %s",
            placa_original, fecha_carpeta, [str(c) for c in candidatas_filtradas],
        )

        if len(candidatas_filtradas) == 0:
            raise ArchivosFaltantesError(placa, ["carpeta del registro"])

        if len(candidatas_filtradas) >= 2:
            # Intentar desempatar con el número de VIA del Excel
            if via:
                via_lower = via.lower()
                por_via = [
                    c for c in candidatas_filtradas
                    if via_lower in c.name.lower()
                ]
                logger.debug(
                    "Desempate por VIA='%s': %d candidata(s) restantes: %s",
                    via, len(por_via), [str(c) for c in por_via],
                )
                if len(por_via) == 1:
                    logger.info(
                        "Carpeta desempatada por VIA '%s': '%s'",
                        via, por_via[0],
                    )
                    candidatas_filtradas = por_via
                elif len(por_via) == 0:
                    # El VIA no coincidió con ninguna — lanzar con las originales
                    raise CarpetaAmbiguaError(placa, candidatas_filtradas)
                else:
                    # El VIA sigue siendo ambiguo
                    raise CarpetaAmbiguaError(placa, por_via)
            else:
                raise CarpetaAmbiguaError(placa, candidatas_filtradas)

        # Exactamente 1 candidata
        carpeta_registro = candidatas_filtradas[0]
        logger.debug("Subcarpeta seleccionada: '%s'", carpeta_registro)
        return carpeta_registro

    def _buscar_imagenes(
        self,
        carpeta_registro: Path,
        placa_original: str,
        placa_limpia: str,
        fecha_archivo: str,
    ) -> dict[str, Path]:
        """
        Busca las tres imágenes obligatorias dentro de ``carpeta_registro``.

        La búsqueda es flexible e insensible a mayúsculas.
        Si falta alguna imagen, lanza :exc:`ArchivosFaltantesError`.

        Criterios de búsqueda
        ---------------------
        * ``img_cam``    : contiene "img_cam" y la placa
        * ``img_fuga``   : contiene "img_fuga" y la placa
        * ``img_sunarp`` : contiene "sunarp" y la placa

        Devuelve
        --------
        dict[str, Path]
            ``{'img_cam': Path, 'img_fuga': Path, 'img_sunarp': Path}``
        """
        # Filtros dinámicos: si el nombre de archivo (en minúsculas) cumple la función, es el correcto
        filtros = {
            "img_cam":    lambda n: "img_cam" in n and placa_limpia.lower() in n,
            "img_fuga":   lambda n: "img_fuga" in n and placa_limpia.lower() in n,
            "img_sunarp": lambda n: "sunarp" in n and (placa_limpia.lower() in n or placa_original.lower() in n),
        }

        # base en minúsculas → ruta absoluta  (para búsqueda case-insensitive)
        # Obtener todos los archivos de imagen en la carpeta y en cualquier subcarpeta interna
        archivos_en_carpeta: list[Path] = [
            archivo.resolve()
            for archivo in carpeta_registro.rglob("*")
            if archivo.is_file() and archivo.suffix.lower() in _EXTENSIONES_IMAGEN
        ]

        logger.debug(
            "Archivos de imagen encontrados en '%s': %s",
            carpeta_registro,
            [a.name for a in archivos_en_carpeta],
        )

        rutas_encontradas: dict[str, Path] = {}
        
        for clave, func_filtro in filtros.items():
            for archivo in archivos_en_carpeta:
                if func_filtro(archivo.name.lower()):
                    rutas_encontradas[clave] = archivo
                    break  # Tomamos la primera coincidencia

        # Verificar si faltó alguna
        faltantes = [clave for clave in filtros if clave not in rutas_encontradas]
        
        if faltantes:
            # Construir nombres descriptivos para el mensaje de error
            nombres_amigables = {
                "img_cam":    f"IMG_CAM...{placa_limpia}...",
                "img_fuga":   f"IMG_FUGA...{placa_limpia}...",
                "img_sunarp": f"SUNARP...{placa_original}",
            }
            desc_faltantes = [nombres_amigables[f] for f in faltantes]
            
            logger.warning(
                "Imágenes faltantes para '%s': %s",
                placa_original, desc_faltantes
            )
            raise ArchivosFaltantesError(placa_original, desc_faltantes)

        return rutas_encontradas
