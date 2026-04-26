from pathlib import Path
 
 
class FileScanner:
    """Escanea una carpeta en busca de archivos .docx."""
 
    EXTENSION = "*.docx"
 
    def listar_docx(self, carpeta: Path) -> list[Path]:
        """Retorna lista ordenada de .docx encontrados en la carpeta."""
        if not carpeta.exists():
            raise FileNotFoundError(f"La carpeta no existe: {carpeta}")
        if not carpeta.is_dir():
            raise NotADirectoryError(f"La ruta no es una carpeta: {carpeta}")
        return sorted(carpeta.glob(self.EXTENSION))
 
    def validar_salida(self, carpeta: Path) -> None:
        """Crea la carpeta de salida si no existe."""
        carpeta.mkdir(parents=True, exist_ok=True)