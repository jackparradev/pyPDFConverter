from pathlib import Path
 
WD_EXPORT_FORMAT_PDF = 17
 
 
class WordEngine:
    """Abre, convierte y cierra documentos Word usando el motor COM."""
 
    def __init__(self):
        self._word = None
 
    # ── Ciclo de vida ──────────────────────────────────────────────────────
 
    def iniciar(self) -> None:
        """Lanza la instancia invisible de Microsoft Word."""
        try:
            import win32com.client as win32
        except ImportError as exc:
            raise RuntimeError(
                "pywin32 no está instalado. Ejecuta:  pip install pywin32"
            ) from exc
 
        self._word = win32.Dispatch("Word.Application")
        self._word.Visible = False
        self._word.DisplayAlerts = 0
 
    def cerrar(self) -> None:
        """Cierra Microsoft Word limpiamente."""
        if self._word:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None
 
    # ── Conversión ─────────────────────────────────────────────────────────
 
    def convertir(self, origen: Path, destino: Path) -> None:
        """
        Convierte un archivo .docx a PDF preservando hipervínculos.
        Lanza una excepción si falla.
        """
        if self._word is None:
            raise RuntimeError("WordEngine no iniciado. Llama a iniciar() primero.")
 
        doc = None
        try:
            doc = self._word.Documents.Open(
                str(origen.resolve()),
                False, True, False, "", "", True, "", "", 0,
            )
            doc.ExportAsFixedFormat(
                str(destino.resolve()),
                WD_EXPORT_FORMAT_PDF,
                False, 0, 0, 0, 0,
                True, True, 1, True, True, False,
            )
        finally:
            if doc:
                try:
                    doc.Close(False)
                except Exception:
                    pass
 
    # ── Context manager ────────────────────────────────────────────────────
 
    def __enter__(self):
        self.iniciar()
        return self
 
    def __exit__(self, *_):
        self.cerrar()