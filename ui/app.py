import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
 
import ui.theme as T
from ui.widgets import HeaderPanel, RoutePanel, ProgressPanel, LogPanel
from core.converter import MassConverter
from core.models import BatchResult
 
 
def _assets_dir() -> Path:
    """Localiza la carpeta assets/ relativa a este archivo."""
    return Path(__file__).parent.parent / "assets"
 
 
class App(tk.Tk):
    """Ventana raíz de la aplicación."""
 
    TITULO  = "Conversor DOCX → PDF"
    ANCHO   = 720
    ALTO    = 660
 
    def __init__(self):
        super().__init__()
        self.title(self.TITULO)
        self.configure(bg=T.FONDO)
        self.resizable(False, False)
 
        self._evento_cancelar = threading.Event()
        self._en_proceso      = False
 
        self._aplicar_icono()
        self._construir_ui()
        self._centrar(self.ANCHO, self.ALTO)
 
    # ── Inicialización ─────────────────────────────────────────────────────
 
    def _aplicar_icono(self) -> None:
        ruta = _assets_dir() / "logo.ico"
        if ruta.exists():
            try:
                self.iconbitmap(str(ruta))
            except Exception:
                pass
 
    def _centrar(self, ancho: int, alto: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - ancho) // 2
        y = (self.winfo_screenheight() - alto)  // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
 
    # ── Construcción de la UI ──────────────────────────────────────────────
 
    def _construir_ui(self) -> None:
        HeaderPanel(self, assets_dir=_assets_dir()).pack(fill="x")
 
        cuerpo = tk.Frame(self, bg=T.FONDO, padx=24, pady=0)
        cuerpo.pack(fill="x")
 
        self._rutas = RoutePanel(
            cuerpo,
            on_entrada=self._auto_proponer_salida,
            on_salida=lambda _: None,
        )
        self._rutas.pack(fill="x", pady=(20, 0))
 
        self._progreso = ProgressPanel(
            cuerpo,
            on_iniciar=self._iniciar,
            on_cancelar=self._cancelar,
        )
        self._progreso.pack(fill="x", pady=(12, 0))
 
        self._log = LogPanel(cuerpo, bg=T.FONDO)
        self._log.pack(fill="x", pady=(12, 0))
 
        tk.Label(
            cuerpo,
            text="Requiere Microsoft Word instalado  ·  Motor COM — ExportAsFixedFormat",
            font=("Segoe UI", 8), fg=T.BORDE, bg=T.FONDO,
        ).pack(pady=10)
 
    # ── Callbacks de RoutePanel ────────────────────────────────────────────
 
    def _auto_proponer_salida(self, ruta_entrada: str) -> None:
        """Si la salida está vacía, sugiere una subcarpeta automáticamente."""
        if not self._rutas.var_salida.get():
            self._rutas.var_salida.set(str(Path(ruta_entrada) / "PDFs_generados"))
 
    # ── Acciones principales ───────────────────────────────────────────────
 
    def _iniciar(self) -> None:
        entrada = self._rutas.var_entrada.get().strip()
        salida  = self._rutas.var_salida.get().strip()
 
        if not entrada:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de entrada.")
            return
        if not salida:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de salida.")
            return
        if not Path(entrada).exists():
            messagebox.showerror("Ruta inválida",
                                 f"La carpeta de entrada no existe:\n{entrada}")
            return
 
        self._evento_cancelar.clear()
        self._en_proceso = True
        self._log.limpiar()
        self._progreso.set_en_proceso(True)
        self._progreso.set_progreso(0)
 
        converter = MassConverter(
            log=self._safe_log,
            progreso=self._safe_progreso,
            al_terminar=self._on_fin,
            cancelar=self._evento_cancelar,
        )
        threading.Thread(
            target=converter.ejecutar,
            args=(entrada, salida),
            daemon=True,
        ).start()
 
    def _cancelar(self) -> None:
        if self._en_proceso:
            self._evento_cancelar.set()
            self._progreso.set_estado("Cancelando…", T.ADVERTENCIA)
            self._progreso.btn_cancelar.config(state="disabled")
 
    # ── Callbacks thread-safe ──────────────────────────────────────────────
 
    def _safe_log(self, mensaje: str, tipo: str = "normal") -> None:
        self.after(0, lambda: self._log.agregar(mensaje, tipo))
 
    def _safe_progreso(self, fraccion: float) -> None:
        self.after(0, lambda: self._progreso.set_progreso(fraccion))
 
    def _on_fin(self, resultado: BatchResult) -> None:
        self._en_proceso = False
 
        def _actualizar():
            self._progreso.set_en_proceso(False)
            if resultado.failure_count == 0 and resultado.success_count > 0:
                self._progreso.set_estado("✅  Conversión completada.", T.EXITO)
            else:
                self._progreso.set_estado("⚠  Proceso finalizado con errores.", T.ADVERTENCIA)
 
        self.after(0, _actualizar)
 
    # ── Cierre seguro ──────────────────────────────────────────────────────
 
    def destroy(self) -> None:
        if self._en_proceso:
            if not messagebox.askyesno(
                "Salir", "Hay una conversión en curso. ¿Deseas salir de todas formas?"
            ):
                return
            self._evento_cancelar.set()
        super().destroy()