import time
import threading
from pathlib import Path
from typing import Callable
 
from core.models import ConversionResult, BatchResult
from core.file_scanner import FileScanner
from core.word_engine import WordEngine
 
 
# Tipos de callback para que la UI pueda anotarlos
LogCallback      = Callable[[str, str], None]   # (mensaje, tipo)
ProgressCallback = Callable[[float], None]       # fracción 0.0–1.0
DoneCallback     = Callable[[BatchResult], None]
 
 
class MassConverter:
    """
    Ejecuta la conversión de todos los .docx de una carpeta.
    Diseñado para correr en un Thread; usa callbacks para notificar a la UI.
    """
 
    PAUSA_ENTRE_ARCHIVOS = 0.25  # segundos (evita saturar Word)
 
    def __init__(
        self,
        log: LogCallback,
        progreso: ProgressCallback,
        al_terminar: DoneCallback,
        cancelar: threading.Event,
    ):
        self._log        = log
        self._progreso   = progreso
        self._al_terminar = al_terminar
        self._cancelar   = cancelar
        self._scanner    = FileScanner()
 
    # ── Punto de entrada ───────────────────────────────────────────────────
 
    def ejecutar(self, ruta_entrada: str, ruta_salida: str) -> None:
        """Método que se pasa como target a threading.Thread."""
        entrada = Path(ruta_entrada)
        salida  = Path(ruta_salida)
        resultado = BatchResult()
 
        try:
            archivos = self._scanner.listar_docx(entrada)
        except (FileNotFoundError, NotADirectoryError) as exc:
            self._log(f"❌  {exc}", "error")
            self._al_terminar(resultado)
            return
 
        if not archivos:
            self._log("⚠  No se encontraron archivos .docx en la carpeta.", "warn")
            self._al_terminar(resultado)
            return
 
        self._scanner.validar_salida(salida)
        resultado.total = len(archivos)
 
        self._log(f"📂  Entrada : {entrada}", "info")
        self._log(f"📁  Salida  : {salida}", "info")
        self._log(f"📄  Archivos: {resultado.total}\n", "info")
        self._log("⏳  Iniciando Microsoft Word…", "info")
 
        try:
            with WordEngine() as engine:
                self._procesar_lote(engine, archivos, salida, resultado)
        except RuntimeError as exc:
            self._log(f"❌  {exc}", "error")
 
        self._mostrar_resumen(resultado)
        self._al_terminar(resultado)
 
    # ── Privados ───────────────────────────────────────────────────────────
 
    def _procesar_lote(
        self,
        engine: WordEngine,
        archivos: list[Path],
        salida: Path,
        resultado: BatchResult,
    ) -> None:
        total = len(archivos)
        for idx, docx in enumerate(archivos, start=1):
            if self._cancelar.is_set():
                self._log("\n🛑  Conversión cancelada por el usuario.", "warn")
                break
 
            destino = salida / (docx.stem + ".pdf")
            self._log(f"[{idx}/{total}]  {docx.name}", "normal")
 
            conv = self._convertir_uno(engine, docx, destino)
            if conv.success:
                resultado.successful.append(conv)
                self._log(f"         ✓  {destino.name}", "ok")
            else:
                resultado.failed.append(conv)
                self._log(f"         ✗  {conv.error}", "error")
 
            self._progreso(idx / total)
            time.sleep(self.PAUSA_ENTRE_ARCHIVOS)
 
    def _convertir_uno(
        self, engine: WordEngine, origen: Path, destino: Path
    ) -> ConversionResult:
        try:
            engine.convertir(origen, destino)
            return ConversionResult(origen, destino, success=True)
        except Exception as exc:
            return ConversionResult(origen, destino, success=False, error=str(exc))
 
    def _mostrar_resumen(self, resultado: BatchResult) -> None:
        self._log("\n" + "─" * 45, "sep")
        self._log(f"✅  Exitosos : {resultado.success_count}", "ok")
        if resultado.failed:
            self._log(f"❌  Fallidos : {resultado.failure_count}", "error")
            for conv in resultado.failed:
                self._log(f"    · {conv.filename}", "error")
        else:
            self._log("   Sin errores.", "ok")
        self._log("─" * 45, "sep")