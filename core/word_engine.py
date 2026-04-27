from __future__ import annotations

from pathlib import Path

WD_EXPORT_FORMAT_PDF = 17


class WordEngine:
    """Abre, convierte y cierra documentos Word usando COM."""

    def __init__(self) -> None:
        self._word = None
        self._com_iniciado = False

    def iniciar(self) -> None:
        """Lanza una instancia aislada de Microsoft Word."""
        try:
            import pythoncom
            import win32com.client as win32
        except ImportError as exc:
            raise RuntimeError(
                "Faltan dependencias. Instala pywin32 con: pip install pywin32"
            ) from exc

        pythoncom.CoInitialize()
        self._com_iniciado = True

        try:
            self._word = win32.DispatchEx("Word.Application")
            self._word.Visible = False
            self._word.DisplayAlerts = 0
        except Exception:
            self.cerrar()
            raise

    def cerrar(self) -> None:
        """Cierra Microsoft Word y libera COM."""
        if self._word is not None:
            try:
                self._word.Quit()
            except Exception:
                pass
            self._word = None

        if self._com_iniciado:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
            self._com_iniciado = False

    def convertir(self, origen: Path, destino: Path) -> None:
        """
        Convierte un archivo DOCX a PDF.
        Lanza excepción si algo falla.
        """
        if self._word is None:
            raise RuntimeError("WordEngine no iniciado. Usa 'with WordEngine() as engine'.")

        if not origen.exists():
            raise FileNotFoundError(f"No existe el archivo de origen: {origen}")

        destino.parent.mkdir(parents=True, exist_ok=True)

        if destino.exists():
            try:
                destino.unlink()
            except Exception as exc:
                raise RuntimeError(
                    f"No se pudo reemplazar el archivo destino: {destino}"
                ) from exc

        doc = None
        try:
            doc = self._word.Documents.Open(
                FileName=str(origen.resolve()),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                PasswordDocument="",
                PasswordTemplate="",
                Revert=True,
                WritePasswordDocument="",
                WritePasswordTemplate="",
                Format=0,
            )

            doc.ExportAsFixedFormat(
                OutputFileName=str(destino.resolve()),
                ExportFormat=WD_EXPORT_FORMAT_PDF,
                OpenAfterExport=False,
                OptimizeFor=0,
                Range=0,
                From=0,
                To=0,
                Item=0,
                IncludeDocProps=True,
                KeepIRM=True,
                CreateBookmarks=1,
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Error al convertir '{origen.name}': {exc}") from exc
        finally:
            if doc is not None:
                try:
                    doc.Close(False)
                except Exception:
                    pass

    def __enter__(self) -> "WordEngine":
        self.iniciar()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cerrar()