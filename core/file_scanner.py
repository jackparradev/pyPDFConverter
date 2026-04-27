from pathlib import Path


class FileScanner:
    """Escanea carpetas y valida rutas de entrada/salida."""

    def listar_docx(self, carpeta: Path) -> list[Path]:
        if not carpeta.exists():
            raise FileNotFoundError(f"La carpeta no existe: {carpeta}")
        if not carpeta.is_dir():
            raise NotADirectoryError(f"La ruta no es una carpeta: {carpeta}")

        archivos: list[Path] = []
        for item in carpeta.iterdir():
            if not item.is_file():
                continue
            if item.name.startswith("~$"):
                continue
            if item.suffix.lower() == ".docx":
                archivos.append(item)

        return sorted(archivos, key=lambda p: p.name.lower())

    def validar_salida(self, carpeta: Path) -> None:
        carpeta.mkdir(parents=True, exist_ok=True)