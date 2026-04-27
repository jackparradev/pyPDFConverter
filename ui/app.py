from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from ui.theme import tema
from ui.widgets import HeaderPanel, RoutePanel, ProgressPanel, LogPanel
from core.converter import MassConverter
from core.models import BatchResult


def _assets_dir() -> Path:
    return Path(__file__).parent.parent / "assets"


class App(tk.Tk):
    TITULO = "Conversor DOCX → PDF"
    ANCHO = 720
    ALTO = 660

    def __init__(self):
        super().__init__()
        self.title(self.TITULO)
        self.configure(bg=tema.get("FONDO"))
        self.resizable(False, False)

        self._evento_cancelar = threading.Event()
        self._en_proceso = False
        self._worker_thread: threading.Thread | None = None

        self._aplicar_icono()
        self._construir_ui()
        self._centrar(self.ANCHO, self.ALTO)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Registrar como observer del ThemeManager
        tema.register(self._aplicar_tema)

    def _aplicar_icono(self) -> None:
        ruta = _assets_dir() / "logo.ico"
        if ruta.exists():
            try:
                self.iconbitmap(str(ruta))
            except Exception:
                pass

    def _centrar(self, ancho: int, alto: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _construir_ui(self) -> None:
        self._header = HeaderPanel(
            self,
            assets_dir=_assets_dir(),
            on_toggle_tema=self._toggle_tema,
        )
        self._header.pack(fill="x")

        self._cuerpo = tk.Frame(self, bg=tema.get("FONDO"), padx=24, pady=0)
        self._cuerpo.pack(fill="x")

        self._rutas = RoutePanel(
            self._cuerpo,
            on_entrada=self._auto_proponer_salida,
            on_salida=lambda _: None,
        )
        self._rutas.pack(fill="x", pady=(20, 0))

        self._progreso = ProgressPanel(
            self._cuerpo,
            on_iniciar=self._iniciar,
            on_cancelar=self._cancelar,
        )
        self._progreso.pack(fill="x", pady=(12, 0))

        self._log = LogPanel(self._cuerpo, bg=tema.get("FONDO"))
        self._log.pack(fill="x", pady=(12, 0))

        self._lbl_footer = tk.Label(
            self._cuerpo,
            text="Requiere Microsoft Word instalado  ·  Motor COM — ExportAsFixedFormat",
            font=("Segoe UI", 8),
            fg=tema.get("BORDE"),
            bg=tema.get("FONDO"),
        )
        self._lbl_footer.pack(pady=10)

    # ── Tema ─────────────────────────────────────────────────

    def _toggle_tema(self) -> None:
        """Alterna entre modo oscuro y claro."""
        tema.toggle()

    def _aplicar_tema(self) -> None:
        """Refresca TODOS los widgets con los colores del tema activo.

        Se invoca automáticamente por el ThemeManager (observer).
        """
        self.configure(bg=tema.get("FONDO"))
        self._cuerpo.config(bg=tema.get("FONDO"))
        self._lbl_footer.config(fg=tema.get("BORDE"), bg=tema.get("FONDO"))

        # Cascada a cada panel
        self._header.actualizar_tema()
        self._rutas.actualizar_tema()
        self._progreso.actualizar_tema()
        self._log.actualizar_tema()

    # ── Lógica de negocio (sin cambios funcionales) ──────────

    def _auto_proponer_salida(self, ruta_entrada: str) -> None:
        if not self._rutas.var_salida.get():
            self._rutas.var_salida.set(str(Path(ruta_entrada) / "PDFs_generados"))

    def _iniciar(self) -> None:
        if self._en_proceso:
            return

        entrada = self._rutas.var_entrada.get().strip()
        salida = self._rutas.var_salida.get().strip()

        if not entrada:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de entrada.")
            return
        if not salida:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de salida.")
            return
        if not Path(entrada).exists():
            messagebox.showerror("Ruta inválida", f"La carpeta de entrada no existe:\n{entrada}")
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

        self._worker_thread = threading.Thread(
            target=converter.ejecutar,
            args=(entrada, salida),
            daemon=True,
        )
        self._worker_thread.start()

    def _cancelar(self) -> None:
        if self._en_proceso:
            self._evento_cancelar.set()
            self._progreso.set_estado("Cancelando…", tema.get("ADVERTENCIA"))
            self._progreso.btn_cancelar.config(state="disabled")

    def _safe_log(self, mensaje: str, tipo: str = "normal") -> None:
        self.after(0, lambda: self._log.agregar(mensaje, tipo))

    def _safe_progreso(self, fraccion: float) -> None:
        self.after(0, lambda: self._progreso.set_progreso(fraccion))

    def _on_fin(self, resultado: BatchResult) -> None:
        self._en_proceso = False

        def _actualizar():
            self._progreso.set_en_proceso(False)
            if resultado.cancelled:
                self._progreso.set_estado("⚠  Proceso cancelado.", tema.get("ADVERTENCIA"))
            elif resultado.failure_count == 0 and resultado.success_count > 0:
                self._progreso.set_estado("✅  Conversión completada.", tema.get("EXITO"))
            elif resultado.success_count > 0:
                self._progreso.set_estado("⚠  Proceso finalizado con errores.", tema.get("ADVERTENCIA"))
            else:
                self._progreso.set_estado("❌  No se pudo completar la conversión.", tema.get("ERROR_COLOR"))

        self.after(0, _actualizar)

    def destroy(self) -> None:
        if self._en_proceso:
            if not messagebox.askyesno(
                "Salir",
                "Hay una conversión en curso. ¿Deseas salir de todas formas?",
            ):
                return
            self._evento_cancelar.set()
        # Des-registrar observer antes de destruir
        tema.unregister(self._aplicar_tema)
        super().destroy()