import os
import sys
import time
import argparse
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("conversion_log.txt", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constante de Word: wdExportFormatPDF = 17
# Usar el valor literal evita importar módulos de constantes que pueden fallar
# ---------------------------------------------------------------------------
WD_EXPORT_FORMAT_PDF = 17


def convertir_docx_a_pdf(word_app, ruta_docx: Path, ruta_pdf: Path) -> bool:
    """
    Abre un .docx con la instancia de Word ya iniciada y lo exporta como PDF.
    Retorna True si tuvo éxito, False en caso de error.
    """
    doc = None
    try:
        # Abrir sin mostrar en pantalla; ReadOnly=True evita diálogos de edición
        doc = word_app.Documents.Open(
            str(ruta_docx.resolve()),
            ReadOnly=True,
            Visible=False,
            AddToRecentFiles=False,
        )

        # ExportAsFixedFormat es el equivalente exacto de "Guardar como PDF" en la UI
        doc.ExportAsFixedFormat(
            OutputFileName=str(ruta_pdf.resolve()),
            ExportFormat=WD_EXPORT_FORMAT_PDF,
            OpenAfterExport=False,
            OptimizeFor=0,       # 0 = wdExportOptimizeForPrint (máxima calidad)
            Range=0,             # 0 = wdExportAllDocument
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=1,   # 1 = wdExportCreateWordBookmarks
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False, # False = PDF normal; True = PDF/A (más restrictivo)
        )
        return True

    except Exception as exc:
        log.error("  ERROR al convertir '%s': %s", ruta_docx.name, exc)
        return False

    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=False)
            except Exception:
                pass


def procesar_carpeta(carpeta_entrada: Path, carpeta_salida: Path, visible: bool = False):
    """
    Recorre todos los .docx en carpeta_entrada y los convierte a PDF en carpeta_salida.
    Reutiliza una sola instancia de Word para mayor velocidad.
    """
    # Recopilar archivos
    archivos = sorted(carpeta_entrada.glob("*.docx"))
    if not archivos:
        log.warning("No se encontraron archivos .docx en: %s", carpeta_entrada)
        return

    carpeta_salida.mkdir(parents=True, exist_ok=True)
    log.info("Archivos encontrados: %d", len(archivos))
    log.info("Carpeta de salida   : %s", carpeta_salida)

    # Importar win32com aquí para dar un mensaje claro si no está instalado
    try:
        import win32com.client as win32
    except ImportError:
        log.critical(
            "pywin32 no está instalado. Ejecuta:  pip install pywin32  y vuelve a intentar."
        )
        sys.exit(1)

    # Iniciar Word una sola vez (mucho más rápido que abrir/cerrar por archivo)
    log.info("Iniciando Microsoft Word...")
    word = win32.Dispatch("Word.Application")
    word.Visible = visible          # False = proceso en segundo plano
    word.DisplayAlerts = False      # Suprimir todos los diálogos

    exitosos = 0
    fallidos = []

    try:
        for idx, ruta_docx in enumerate(archivos, start=1):
            nombre_pdf = ruta_docx.stem + ".pdf"
            ruta_pdf = carpeta_salida / nombre_pdf

            log.info("[%d/%d] Convirtiendo: %s", idx, len(archivos), ruta_docx.name)

            ok = convertir_docx_a_pdf(word, ruta_docx, ruta_pdf)

            if ok:
                exitosos += 1
                log.info("       ✓  Guardado en: %s", ruta_pdf.name)
            else:
                fallidos.append(ruta_docx.name)

            # Pausa breve para evitar que Word se sature en lotes grandes
            time.sleep(0.3)

    finally:
        # Cerrar Word aunque haya errores
        try:
            word.Quit()
        except Exception:
            pass
        log.info("Microsoft Word cerrado.")

    # Resumen final
    log.info("=" * 55)
    log.info("RESUMEN: %d exitosos / %d fallidos / %d total",
             exitosos, len(fallidos), len(archivos))
    if fallidos:
        log.warning("Archivos con error:")
        for nombre in fallidos:
            log.warning("  - %s", nombre)
    log.info("=" * 55)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convierte .docx a PDF usando el motor nativo de Microsoft Word."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Carpeta con los archivos .docx a convertir.",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Carpeta donde se guardarán los PDF generados.",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        default=False,
        help="Mostrar la ventana de Word durante la conversión (útil para depuración).",
    )

    args = parser.parse_args()

    carpeta_entrada = Path(args.input)
    carpeta_salida = Path(args.output)

    if not carpeta_entrada.exists():
        log.critical("La carpeta de entrada no existe: %s", carpeta_entrada)
        sys.exit(1)

    procesar_carpeta(carpeta_entrada, carpeta_salida, visible=args.visible)


if __name__ == "__main__":
    main()