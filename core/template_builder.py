"""
core/template_builder.py
========================
Constructor de contexto Jinja2 para la plantilla .docx de infracciones.

Responsabilidades
-----------------
* Abrir la plantilla ``.docx`` con ``docxtpl.DocxTemplate``.
* Construir el diccionario de contexto Jinja2:
    - ``url_evidencia`` → RichText con hipervínculo (vía ``build_url_id``).
    - ``img_cam``       → InlineImage con ancho de 140 mm.
    - ``img_fuga``      → InlineImage con ancho de 140 mm.
    - ``img_sunarp``    → InlineImage con ancho de 140 mm.
    - Resto de campos del Excel como cadenas de texto.
* Renderizar el template contra el contexto y guardar el archivo ``.docx``
  resultante en la ruta de destino indicada.

Ruta del hipervínculo (modo usado: PRIMARIO)
--------------------------------------------
Se usa el mecanismo nativo de docxtpl ``DocxTemplate.build_url_id``,
disponible desde la versión 0.16.0.  Confirmado presente en 0.20.2.

    url_id = tpl.build_url_id(url_evidencia)
    rt = RichText()
    rt.add(url_evidencia, url_id=url_id)
    contexto["url_evidencia"] = rt

Si en algún entorno faltara ``build_url_id``, existe un camino alternativo
(fallback) documentado pero no activado aquí: renderizar el docx normalmente
con docxtpl y luego reabrir con python-docx para inyectar el hipervínculo
manipulando ``document.xml.rels`` directamente.

Prohibiciones
-------------
* No importar nada de ``ui/``.
* No usar ``win32com`` ni ``WordEngine``.
* No escribir archivos fuera de la ruta de destino indicada.
"""

from __future__ import annotations

import logging
import io
from pathlib import Path
from typing import Any
from PIL import Image

from docxtpl import DocxTemplate, InlineImage, RichText

from core.image_handler import ALTOS_ESTANDAR

logger = logging.getLogger(__name__)


class TemplateBuilder:
    """
    Abre la plantilla ``.docx``, construye el contexto Jinja2 y genera
    el documento de salida.

    Uso típico
    ----------
    >>> builder = TemplateBuilder(Path("plantilla.docx"))
    >>> builder.generar(
    ...     datos_fila=fila,          # dict[str, Any] del ExcelParser
    ...     rutas_imagenes=rutas,     # dict[str, Path] del AssetLocator
    ...     ruta_destino=Path("salida/001_A1B123.docx"),
    ... )

    Notas
    -----
    * La instancia es reutilizable: se puede llamar a ``generar()`` múltiples
      veces con distintos datos; cada llamada recarga la plantilla internamente
      para evitar contaminación de estado entre documentos.
    * Las claves del contexto coinciden exactamente con los placeholders de la
      plantilla: ``{{ correlativo }}``, ``{{ placa }}``, ``{{ url_evidencia }}``,
      ``{{ img_cam }}``, ``{{ img_fuga }}``, ``{{ img_sunarp }}``, etc.
    """

    def __init__(self, ruta_plantilla: Path) -> None:
        """
        Parámetros
        ----------
        ruta_plantilla : Path
            Ruta al archivo ``.docx`` que actúa como plantilla Jinja2.
            Debe existir y ser un archivo regular.

        Lanza
        -----
        FileNotFoundError
            Si la plantilla no existe.
        """
        self._ruta_plantilla = Path(ruta_plantilla).resolve()
        if not self._ruta_plantilla.is_file():
            raise FileNotFoundError(
                f"Plantilla no encontrada: '{self._ruta_plantilla}'"
            )
        logger.debug("TemplateBuilder inicializado con plantilla: '%s'", self._ruta_plantilla)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def generar(
        self,
        datos_fila: dict[str, Any],
        rutas_imagenes: dict[str, Path],
        ruta_destino: Path,
    ) -> Path:
        """
        Genera el documento ``.docx`` final a partir de la plantilla.

        Parámetros
        ----------
        datos_fila : dict[str, Any]
            Diccionario normalizado devuelto por ``ExcelParser.leer()``.
            Se espera que contenga al menos las claves:
            ``correlativo``, ``placa``, ``fecha_fuga_texto``,
            ``categoria``, ``estacion_peaje``, ``ubicacion``,
            ``distrito``, ``sentido``, ``provincia``, ``url_evidencia``.
        rutas_imagenes : dict[str, Path]
            Diccionario devuelto por ``AssetLocator.localizar_imagenes()``.
            Debe contener las claves ``img_cam``, ``img_fuga``, ``img_sunarp``.
        ruta_destino : Path
            Ruta completa (incluyendo nombre de archivo) donde se guardará
            el ``.docx`` generado.  El directorio padre debe existir.

        Devuelve
        --------
        Path
            La misma ``ruta_destino`` resuelta a ruta absoluta.

        Lanza
        -----
        KeyError
            Si falta alguna clave de imagen requerida en ``rutas_imagenes``.
        Exception
            Si docxtpl no puede renderizar o guardar el documento.
        """
        ruta_destino = Path(ruta_destino).resolve()

        # Cada llamada recarga la plantilla para evitar contaminación entre docs
        tpl = DocxTemplate(str(self._ruta_plantilla))

        contexto = self._construir_contexto(tpl, datos_fila, rutas_imagenes)

        logger.debug(
            "Renderizando plantilla para correlativo='%s', destino='%s'",
            datos_fila.get("correlativo", "?"),
            ruta_destino,
        )

        tpl.render(contexto)
        tpl.save(str(ruta_destino))

        logger.info(
            "Documento generado: '%s'",
            ruta_destino.name,
        )
        return ruta_destino

    # ------------------------------------------------------------------
    # Construcción del contexto
    # ------------------------------------------------------------------

    def _construir_contexto(
        self,
        tpl: DocxTemplate,
        datos_fila: dict[str, Any],
        rutas_imagenes: dict[str, Path],
    ) -> dict[str, Any]:
        """
        Ensambla el diccionario de contexto Jinja2.

        Hipervínculo (camino PRIMARIO — build_url_id disponible en 0.20.2)
        -------------------------------------------------------------------
        Se usa ``DocxTemplate.build_url_id`` para registrar la URL en las
        relaciones del documento y luego se crea un ``RichText`` que referencia
        ese ID. Este es el mecanismo recomendado y nativo de docxtpl.

        Imágenes
        --------
        Se inyectan tres objetos ``InlineImage`` con ancho fijo de 140 mm.
        """
        contexto: dict[str, Any] = {}

        # --- Campos de texto simples (del Excel) ---
        campos_texto = [
            "correlativo",
            "placa",
            "fecha_fuga_texto",
            "categoria",
            "estacion_peaje",
            "ubicacion",
            "distrito",
            "sentido",
            "provincia",
            "tarifa",
        ]
        for campo in campos_texto:
            valor = datos_fila.get(campo, "")
            contexto[campo] = str(valor) if valor is not None else ""

        # --- Hipervínculo (CAMINO PRIMARIO: build_url_id) ---
        url_evidencia: str = str(datos_fila.get("url_evidencia", "") or "")
        contexto["url_evidencia"] = self._construir_hyperlink(tpl, url_evidencia)

        # --- Imágenes incrustadas (escalado proporcional por altura) ---
        # Intercambiados a pedido del usuario: img_cam recibe la foto de fuga y viceversa
        rutas_intercambiadas = {
            "img_cam": rutas_imagenes["img_fuga"],
            "img_fuga": rutas_imagenes["img_cam"],
            "img_sunarp": rutas_imagenes["img_sunarp"],
        }
        for clave, ruta in rutas_intercambiadas.items():
            contexto[clave] = self._cargar_imagen_segura(
                tpl, ruta, ALTOS_ESTANDAR[clave]
            )

        logger.debug(
            "Contexto construido: campos_texto=%s, url_evidencia='%s'",
            campos_texto,
            url_evidencia,
        )
        return contexto

    # ------------------------------------------------------------------
    # Hipervínculo — implementación primaria y fallback documentado
    # ------------------------------------------------------------------

    def _construir_hyperlink(self, tpl: DocxTemplate, url: str) -> RichText:
        """
        Crea un objeto ``RichText`` con hipervínculo usando ``build_url_id``.

        Camino PRIMARIO (activo)
        ------------------------
        Registra la URL como relación del documento con ``tpl.build_url_id(url)``
        y agrega el texto con el ID devuelto mediante ``rt.add(url, url_id=url_id)``.
        Disponible desde docxtpl ≥ 0.16.0; confirmado en 0.20.2.

        Camino FALLBACK (documentado, no activo)
        ----------------------------------------
        Si ``build_url_id`` no estuviera disponible, el procedimiento sería:
        1. Renderizar el .docx con docxtpl normalmente (dejar el campo como
           cadena de texto plana).
        2. Reabrir el .docx con ``python-docx``:
               doc = docx.Document(ruta_destino)
        3. Localizar el párrafo que contiene el placeholder y reemplazar el
           run por uno con hipervínculo manipulando ``document.xml.rels``.
        Este fallback requeriría modificar el flujo de ``generar()`` para
        recibir la ruta del archivo ya guardado y reescribirlo.

        Informe
        -------
        **Camino usado: PRIMARIO (build_url_id de docxtpl 0.20.2).**
        """
        
    def _construir_hyperlink(self, tpl: DocxTemplate, url: str) -> RichText | str:
        """
        Construye un hipervínculo clickeable usando ``build_url_id`` de docxtpl.

        ``build_url_id`` registra la URL como relación XML del documento;
        lxml se encarga internamente de escapar caracteres especiales como '&'.
        """
        if not url:
            return ""

        try:
            # Registrar la URL como relación del documento
            url_id = tpl.build_url_id(url)

            # Crear RichText con hipervínculo referenciando esa relación
            rt = RichText()
            rt.add(url, url_id=url_id)
            return rt
        except Exception as exc:
            logger.warning(
                "No se pudo crear hipervínculo nativo para la URL '%s': %s",
                url, exc
            )
            return url

    def _cargar_imagen_segura(
        self, tpl: DocxTemplate, ruta: Path, alto_cm
    ) -> InlineImage:
        """
        Carga la imagen con Pillow y la convierte a un JPEG estándar en memoria.
        Esto previene `UnrecognizedImageError` de docx cuando las imágenes son
        WebP o tienen extensiones falsas (ej. un .webp guardado como .jpg).

        Se escala únicamente por altura (``height``), dejando que el ancho
        se calcule automáticamente según el aspect ratio original,
        garantizando proporción sin distorsión.
        """
        img_buffer = io.BytesIO()
        try:
            with Image.open(ruta) as img:
                # Convertir a RGB (elimina transparencias o problemas de perfil)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # Guardar siempre como JPEG estándar al buffer
                img.save(img_buffer, format="JPEG", quality=90)
                img_buffer.seek(0)

            return InlineImage(tpl, img_buffer, height=alto_cm)
        except Exception as exc:
            logger.error("Error al procesar imagen segura %s: %s", ruta, exc)
            # Fallback: intentar pasar la ruta directa
            return InlineImage(tpl, str(ruta), height=alto_cm)
