from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
import sys
from tkinter import messagebox

from ui.theme import tema
from ui.widgets import (
    HeaderPanel,
    RoutePanel,
    GeneratorRoutePanel,
    ProgressPanel,
    LogPanel,
)
from core.converter import MassConverter
from core.generator import MassGenerator
from core.models import BatchResult, GenerationBatchResult


def _assets_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "assets"
    return Path(__file__).parent.parent / "assets"


# ── Constantes de modo ────────────────────────────────────────
_MODO_CONVERTIR = "convertir"
_MODO_GENERAR   = "generar"


class App(tk.Tk):
    TITULO = "Docusol — Generador & Conversor"
    ANCHO  = 720
    ALTO   = 760

    def __init__(self):
        super().__init__()
        self.title(self.TITULO)
        self.configure(bg=tema.get("FONDO"))
        self.resizable(False, False)

        self._evento_cancelar = threading.Event()
        self._en_proceso      = False
        self._worker_thread: threading.Thread | None = None
        self._modo_activo     = _MODO_CONVERTIR          # modo inicial

        self._aplicar_icono()
        self._construir_ui()
        self._centrar(self.ANCHO, self.ALTO)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Registrar como observer del ThemeManager
        tema.register(self._aplicar_tema)

    # ── Icono y geometría ─────────────────────────────────────

    def _aplicar_icono(self) -> None:
        # Asegurar que Windows use este icono en la barra de tareas 
        # en lugar del icono genérico de Python/Tkinter
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("covisol.docusol.v2")
        except Exception:
            pass

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

    # ── Construcción de UI ────────────────────────────────────

    def _construir_ui(self) -> None:
        # ── Header ───────────────────────────────────────────
        self._header = HeaderPanel(
            self,
            assets_dir=_assets_dir(),
            on_toggle_tema=self._toggle_tema,
        )
        self._header.pack(fill="x")

        # ── Cuerpo ───────────────────────────────────────────
        self._cuerpo = tk.Frame(self, bg=tema.get("FONDO"), padx=24, pady=0)
        self._cuerpo.pack(fill="x")

        # ── Selector de modo (tabs) ───────────────────────────
        self._frame_tabs = tk.Frame(self._cuerpo, bg=tema.get("FONDO"))
        self._frame_tabs.pack(fill="x", pady=(16, 0))

        self._btn_modo_convertir = tk.Button(
            self._frame_tabs,
            text="⚡  Modo 1: Convertir a PDF",
            command=lambda: self._cambiar_modo(_MODO_CONVERTIR),
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=8,
        )
        self._btn_modo_convertir.pack(side="left", fill="x", expand=True)

        self._btn_modo_generar = tk.Button(
            self._frame_tabs,
            text="📄  Modo 2: Generar DOCX",
            command=lambda: self._cambiar_modo(_MODO_GENERAR),
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=8,
        )
        self._btn_modo_generar.pack(side="left", fill="x", expand=True)

        self._actualizar_tabs()   # aplica colores iniciales

        # ── Paneles de rutas (mutuamente excluyentes) ─────────
        self._rutas = RoutePanel(
            self._cuerpo,
            on_entrada=self._auto_proponer_salida,
            on_salida=lambda _: None,
        )
        self._rutas.pack(fill="x", pady=(14, 0))

        self._panel_generador = GeneratorRoutePanel(self._cuerpo)
        # Empieza oculto: el modo inicial es "convertir"
        self._panel_generador.pack_forget()

        # ── Panel de progreso ─────────────────────────────────
        self._progreso = ProgressPanel(
            self._cuerpo,
            on_iniciar=self._iniciar_segun_modo,
            on_cancelar=self._cancelar,
        )
        self._progreso.pack(fill="x", pady=(12, 0))

        # ── Panel de log ──────────────────────────────────────
        self._log = LogPanel(self._cuerpo, bg=tema.get("FONDO"))
        self._log.pack(fill="x", pady=(12, 0))

        # ── Footer ────────────────────────────────────────────
        self._lbl_footer = tk.Label(
            self._cuerpo,
            text="Requiere Microsoft Word instalado  ·  Motor COM — ExportAsFixedFormat",
            font=("Segoe UI", 8),
            fg=tema.get("BORDE"),
            bg=tema.get("FONDO"),
        )
        self._lbl_footer.pack(pady=10)

    # ── Selector de modo ──────────────────────────────────────

    def _cambiar_modo(self, nuevo_modo: str) -> None:
        """Alterna entre modo conversor y modo generador."""
        if nuevo_modo == self._modo_activo:
            return

        self._modo_activo = nuevo_modo

        # Intercambiar paneles de rutas
        if nuevo_modo == _MODO_GENERAR:
            self._rutas.pack_forget()
            self._panel_generador.pack(fill="x", pady=(14, 0),
                                       before=self._progreso)
        else:
            self._panel_generador.pack_forget()
            self._rutas.pack(fill="x", pady=(14, 0),
                             before=self._progreso)

        # Actualizar etiqueta del botón de acción según el modo
        self._actualizar_btn_iniciar()
        self._actualizar_tabs()

    def _actualizar_tabs(self) -> None:
        """Pinta el tab activo con el color de acento y el inactivo con BORDE."""
        es_conv = (self._modo_activo == _MODO_CONVERTIR)

        activo_bg   = tema.get("ACENTO")
        activo_fg   = tema.get("BTN_PRI_FG")
        inactivo_bg = tema.get("BORDE")
        inactivo_fg = tema.get("TEXTO_SEC")

        self._btn_modo_convertir.config(
            bg=activo_bg   if es_conv else inactivo_bg,
            fg=activo_fg   if es_conv else inactivo_fg,
            activebackground=tema.get("ACENTO_HOVER"),
            activeforeground=tema.get("BTN_PRI_FG"),
        )
        self._btn_modo_generar.config(
            bg=activo_bg   if not es_conv else inactivo_bg,
            fg=activo_fg   if not es_conv else inactivo_fg,
            activebackground=tema.get("ACENTO_HOVER"),
            activeforeground=tema.get("BTN_PRI_FG"),
        )

    def _actualizar_btn_iniciar(self) -> None:
        """Cambia el texto del botón de inicio según el modo activo."""
        if self._modo_activo == _MODO_GENERAR:
            self._progreso.btn_iniciar.config(text="▶  INICIAR GENERACIÓN")
        else:
            self._progreso.btn_iniciar.config(text="▶  INICIAR CONVERSIÓN")

    # ── Tema ──────────────────────────────────────────────────

    def _toggle_tema(self) -> None:
        """Alterna entre modo oscuro y claro."""
        tema.toggle()

    def _aplicar_tema(self) -> None:
        """Refresca TODOS los widgets con los colores del tema activo.

        Se invoca automáticamente por el ThemeManager (observer).
        """
        self.configure(bg=tema.get("FONDO"))
        self._cuerpo.config(bg=tema.get("FONDO"))
        self._frame_tabs.config(bg=tema.get("FONDO"))
        self._lbl_footer.config(fg=tema.get("BORDE"), bg=tema.get("FONDO"))

        # Re-pintar tabs con colores del nuevo tema
        self._actualizar_tabs()

        # Cascada a cada panel
        self._header.actualizar_tema()
        self._rutas.actualizar_tema()
        self._panel_generador.actualizar_tema()   # ← nuevo
        self._progreso.actualizar_tema()
        self._log.actualizar_tema()

    # ── Despachador de acción principal ───────────────────────

    def _iniciar_segun_modo(self) -> None:
        """Delega al método correcto según el modo activo."""
        if self._modo_activo == _MODO_GENERAR:
            self._iniciar_generacion()
        else:
            self._iniciar()

    # ── Lógica: Modo Conversor ────────────────────────────────

    def _auto_proponer_salida(self, ruta_entrada: str) -> None:
        if not self._rutas.var_salida.get():
            self._rutas.var_salida.set(str(Path(ruta_entrada) / "PDFs_generados"))

    def _iniciar(self) -> None:
        if self._en_proceso:
            return

        entrada = self._rutas.var_entrada.get().strip()
        salida  = self._rutas.var_salida.get().strip()

        if not entrada:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de entrada.")
            return
        if not salida:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de salida.")
            return
        if not Path(entrada).exists():
            messagebox.showerror(
                "Ruta inválida", f"La carpeta de entrada no existe:\n{entrada}"
            )
            return

        self._evento_cancelar.clear()
        self._en_proceso = True
        self._log.limpiar()
        self._progreso.set_en_proceso(True)
        self._progreso.set_progreso(0)

        converter = MassConverter(
            log=self._safe_log,
            progreso=self._safe_progreso,
            al_terminar=self._on_fin_conversion,
            cancelar=self._evento_cancelar,
        )

        self._worker_thread = threading.Thread(
            target=converter.ejecutar,
            args=(entrada, salida),
            daemon=True,
        )
        self._worker_thread.start()

    # ── Lógica: Modo Generador ────────────────────────────────

    def _iniciar_generacion(self) -> None:
        """Valida los campos del GeneratorRoutePanel y lanza MassGenerator."""
        if self._en_proceso:
            return

        excel     = self._panel_generador.var_excel.get().strip()
        plantilla = self._panel_generador.var_plantilla.get().strip()
        imagenes  = self._panel_generador.var_imagenes.get().strip()
        salida    = self._panel_generador.var_salida.get().strip()

        if not excel:
            messagebox.showwarning("Campo vacío", "Selecciona el archivo Excel (.xlsx).")
            return
        if not plantilla:
            messagebox.showwarning("Campo vacío", "Selecciona la plantilla Word (.docx).")
            return
        if not imagenes:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de imágenes.")
            return
        if not salida:
            messagebox.showwarning("Campo vacío", "Selecciona la carpeta de salida.")
            return
        if not Path(excel).is_file():
            messagebox.showerror(
                "Ruta inválida", f"El archivo Excel no existe:\n{excel}"
            )
            return
        if not Path(plantilla).is_file():
            messagebox.showerror(
                "Ruta inválida", f"La plantilla Word no existe:\n{plantilla}"
            )
            return
        if not Path(imagenes).exists():
            messagebox.showerror(
                "Ruta inválida", f"La carpeta de imágenes no existe:\n{imagenes}"
            )
            return

        self._evento_cancelar.clear()
        self._en_proceso = True
        self._log.limpiar()
        self._progreso.set_en_proceso(True)
        self._progreso.set_progreso(0)
        self._progreso.lbl_estado.config(text="Generando…", fg=tema.get("ACENTO"))

        # Callbacks encapsulados en self.after(0, …) — thread-safe
        def _log_safe(mensaje: str, tipo: str = "normal") -> None:
            self.after(0, lambda: self._log.agregar(mensaje, tipo))

        def _progreso_safe(fraccion: float) -> None:
            self.after(0, lambda: self._progreso.set_progreso(fraccion))

        def _al_terminar_safe(resultado: GenerationBatchResult) -> None:
            self.after(0, lambda: self._on_fin_generacion(resultado))

        grupo = self._panel_generador.var_grupo.get().strip() or None

        generador = MassGenerator(
            log=_log_safe,
            progreso=_progreso_safe,
            al_terminar=_al_terminar_safe,
            cancelar=self._evento_cancelar,
        )

        self._worker_thread = threading.Thread(
            target=generador.ejecutar,
            args=(excel, imagenes, salida, plantilla),
            kwargs={"filtro_grupo": grupo},
            daemon=True,
        )
        self._worker_thread.start()


    # ── Cancelación ───────────────────────────────────────────

    def _cancelar(self) -> None:
        if self._en_proceso:
            self._evento_cancelar.set()
            self._progreso.set_estado("Cancelando…", tema.get("ADVERTENCIA"))
            self._progreso.btn_cancelar.config(state="disabled")

    # ── Callbacks thread-safe (modo conversor) ────────────────

    def _safe_log(self, mensaje: str, tipo: str = "normal") -> None:
        self.after(0, lambda: self._log.agregar(mensaje, tipo))

    def _safe_progreso(self, fraccion: float) -> None:
        self.after(0, lambda: self._progreso.set_progreso(fraccion))

    # ── Fin de proceso: Modo Conversor ────────────────────────

    def _on_fin_conversion(self, resultado: BatchResult) -> None:
        self._en_proceso = False

        def _actualizar() -> None:
            self._progreso.set_en_proceso(False)
            if resultado.cancelled:
                self._progreso.set_estado(
                    "⚠  Proceso cancelado.", tema.get("ADVERTENCIA")
                )
            elif resultado.failure_count == 0 and resultado.success_count > 0:
                self._progreso.set_estado(
                    "✅  Conversión completada.", tema.get("EXITO")
                )
            elif resultado.success_count > 0:
                self._progreso.set_estado(
                    "⚠  Proceso finalizado con errores.", tema.get("ADVERTENCIA")
                )
            else:
                self._progreso.set_estado(
                    "❌  No se pudo completar la conversión.", tema.get("ERROR_COLOR")
                )

        self.after(0, _actualizar)

    # ── Fin de proceso: Modo Generador ────────────────────────

    def _on_fin_generacion(self, resultado: GenerationBatchResult) -> None:
        """Actualiza la UI al terminar la generación masiva (ya en hilo principal)."""
        self._en_proceso = False
        self._progreso.set_en_proceso(False)

        if resultado.cancelado:
            self._progreso.set_estado(
                "⚠  Generación cancelada.", tema.get("ADVERTENCIA")
            )
        elif resultado.cantidad_fallidos == 0 and resultado.cantidad_exitosos > 0:
            self._progreso.set_estado(
                f"✅  {resultado.cantidad_exitosos} documento(s) generado(s).",
                tema.get("EXITO"),
            )
        elif resultado.cantidad_exitosos > 0:
            self._progreso.set_estado(
                f"⚠  Finalizado con {resultado.cantidad_fallidos} error(es).",
                tema.get("ADVERTENCIA"),
            )
        else:
            self._progreso.set_estado(
                "❌  No se pudo generar ningún documento.",
                tema.get("ERROR_COLOR"),
            )

    # ── Destrucción ───────────────────────────────────────────

    def destroy(self) -> None:
        if self._en_proceso:
            if not messagebox.askyesno(
                "Salir",
                "Hay un proceso en curso. ¿Deseas salir de todas formas?",
            ):
                return
            self._evento_cancelar.set()
        # Des-registrar observer antes de destruir
        tema.unregister(self._aplicar_tema)
        super().destroy()