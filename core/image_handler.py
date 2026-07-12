from pathlib import Path
from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage

ALTOS_ESTANDAR: dict[str, Cm] = {
    "img_cam": Cm(6.5),
    "img_fuga": Cm(7.0),
    "img_sunarp": Cm(6.0),
}

class ImageHandler:
    """Encapsula el escalado proporcional de imágenes para inserción en .docx."""

    @staticmethod
    def preparar_imagen(tpl: DocxTemplate, ruta_imagen: Path, alto_cm: Cm) -> InlineImage:
        """
        Prepara una imagen individual para ser insertada, escalándola por altura.
        """
        if not ruta_imagen.exists():
            raise FileNotFoundError(f"No se encontró la imagen para procesar: {ruta_imagen}")
        return InlineImage(tpl, str(ruta_imagen), height=alto_cm)

    @classmethod
    def preparar_lote(cls, tpl: DocxTemplate, rutas: dict[str, Path]) -> dict[str, InlineImage]:
        """
        Prepara un lote de imágenes aplicando los altos estándar correspondientes.
        """
        return {
            clave: cls.preparar_imagen(tpl, ruta, ALTOS_ESTANDAR[clave])
            for clave, ruta in rutas.items()
        }
