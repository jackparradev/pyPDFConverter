from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ImageTk
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False

from ui.theme import (
    tema,
    aplicar_hover,
    FUENTE_TITULO,
    FUENTE_SUBTIT,
    FUENTE_LABEL,
    FUENTE_NORMAL,
    FUENTE_MONO,
    FUENTE_BTN,
    FUENTE_BTN_PRI,
)


# ══════════════════════════════════════════════════════════════
#  HeaderPanel
# ══════════════════════════════════════════════════════════════

class HeaderPanel(tk.Frame):
    LOGO_NAMES = ("logotipo.png", "logo.gif", "logo.pgm", "logo.ppm")
    LOGO_MAX_H = 52
    VERSION_TEXT = "v1.0"

    def __init__(self, master, assets_dir: Path, on_toggle_tema: Callable | None = None, **kwargs):
        super().__init__(master, bg=tema.get("FONDO_PANEL"), **kwargs)
        self._logo_img = self._cargar_logo(assets_dir)
        self._on_toggle_tema = on_toggle_tema
        self._construir()

    def _construir(self):
        self._barra_acento = tk.Frame(self, bg=tema.get("ACENTO"), height=3)
        self._barra_acento.pack(fill="x")

        self._contenido = tk.Frame(self, bg=tema.get("FONDO_PANEL"), padx=28, pady=18)
        self._contenido.pack(fill="x")

        if self._logo_img:
            self._lbl_logo = tk.Label(
                self._contenido, image=self._logo_img, bg=tema.get("FONDO_PANEL")
            )
            self._lbl_logo.pack(side="left", padx=(0, 18))
        else:
            self._lbl_logo = None

        self._textos = tk.Frame(self._contenido, bg=tema.get("FONDO_PANEL"))
        self._textos.pack(side="left", fill="x", expand=True)

        self._lbl_titulo = tk.Label(
            self._textos,
            text="Docusol",
            font=FUENTE_TITULO,
            fg=tema.get("TEXTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        self._lbl_titulo.pack(anchor="w")

        self._lbl_subtitulo = tk.Label(
            self._textos,
            text="DOCX  →  PDF  ·  Motor Microsoft Word  ·  Preserva hipervínculos",
            font=FUENTE_SUBTIT,
            fg=tema.get("TEXTO_SEC"),
            bg=tema.get("FONDO_PANEL"),
        )
        self._lbl_subtitulo.pack(anchor="w")

        # Frame derecho: contiene versión y toggle de tema
        self._frame_derecho = tk.Frame(self._contenido, bg=tema.get("FONDO_PANEL"))
        self._frame_derecho.pack(side="right", anchor="ne")

        self._lbl_version = tk.Label(
            self._frame_derecho,
            text=self.VERSION_TEXT,
            font=("Segoe UI", 8, "bold"),
            fg=tema.get("ACENTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        self._lbl_version.pack(anchor="e")

        # Botón toggle de tema
        icono = "☀️" if tema.is_dark else "🌙"
        self._btn_tema = tk.Button(
            self._frame_derecho,
            text=icono,
            command=self._toggle_tema,
            font=("Segoe UI", 14),
            bg=tema.get("FONDO_PANEL"),
            fg=tema.get("TEXTO_SEC"),
            activebackground=tema.get("FONDO_PANEL"),
            activeforeground=tema.get("TEXTO"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=4,
            pady=0,
        )
        self._btn_tema.pack(anchor="e", pady=(4, 0))

    def _toggle_tema(self):
        if self._on_toggle_tema:
            self._on_toggle_tema()

    def actualizar_tema(self) -> None:
        """Actualiza todos los colores del HeaderPanel al tema activo."""
        fp = tema.get("FONDO_PANEL")
        self.config(bg=fp)
        self._barra_acento.config(bg=tema.get("ACENTO"))
        self._contenido.config(bg=fp)
        self._textos.config(bg=fp)
        self._frame_derecho.config(bg=fp)

        if self._lbl_logo:
            self._lbl_logo.config(bg=fp)

        self._lbl_titulo.config(fg=tema.get("TEXTO"), bg=fp)
        self._lbl_subtitulo.config(fg=tema.get("TEXTO_SEC"), bg=fp)
        self._lbl_version.config(fg=tema.get("ACENTO"), bg=fp)

        # Actualizar ícono del toggle
        icono = "☀️" if tema.is_dark else "🌙"
        self._btn_tema.config(
            text=icono,
            bg=fp,
            fg=tema.get("TEXTO_SEC"),
            activebackground=fp,
            activeforeground=tema.get("TEXTO"),
        )

    def _cargar_logo(self, assets_dir: Path):
        for nombre in self.LOGO_NAMES:
            ruta = assets_dir / nombre
            if ruta.exists():
                try:
                    if PIL_DISPONIBLE:
                        img = Image.open(str(ruta))
                        if img.height > self.LOGO_MAX_H:
                            ratio = self.LOGO_MAX_H / img.height
                            img = img.resize(
                                (int(img.width * ratio), self.LOGO_MAX_H),
                                Image.LANCZOS,
                            )
                        return ImageTk.PhotoImage(img)
                    return tk.PhotoImage(file=str(ruta))
                except Exception:
                    pass
        return None


# ══════════════════════════════════════════════════════════════
#  RoutePanel
# ══════════════════════════════════════════════════════════════

class RoutePanel(tk.Frame):
    def __init__(
        self,
        master,
        on_entrada: Callable[[str], None],
        on_salida: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(
            master,
            bg=tema.get("FONDO_PANEL"),
            highlightbackground=tema.get("BORDE"),
            highlightthickness=1,
            **kwargs,
        )
        self._on_entrada = on_entrada
        self._on_salida = on_salida
        self.var_entrada = tk.StringVar()
        self.var_salida = tk.StringVar()

        # Listas para rastrear sub-widgets dinámicos
        self._labels: list[tk.Label] = []
        self._entries: list[tk.Entry] = []
        self._botones: list[tk.Button] = []
        self._frames: list[tk.Frame] = []
        self._separadores: list[tk.Frame] = []

        self._construir()

    def _construir(self):
        self._interior = tk.Frame(self, bg=tema.get("FONDO_PANEL"), padx=20, pady=18)
        self._interior.pack(fill="x")

        self._lbl_seccion = tk.Label(
            self._interior,
            text="CONFIGURACIÓN DE RUTAS",
            font=("Segoe UI", 8, "bold"),
            fg=tema.get("ACENTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        self._lbl_seccion.pack(anchor="w")

        self._sep_titulo = tk.Frame(
            self._interior, bg=tema.get("BORDE"), height=1
        )
        self._sep_titulo.pack(fill="x", pady=(4, 14))

        self._fila_ruta(
            self._interior,
            "📂  Carpeta de entrada  (archivos .docx)",
            self.var_entrada,
            self._seleccionar_entrada,
        )

        self._sep_medio = tk.Frame(
            self._interior, bg=tema.get("FONDO"), height=10
        )
        self._sep_medio.pack()

        self._fila_ruta(
            self._interior,
            "📁  Carpeta de salida  (PDFs generados)",
            self.var_salida,
            self._seleccionar_salida,
        )

    def _fila_ruta(self, padre, etiqueta: str, variable: tk.StringVar, comando: Callable):
        lbl = tk.Label(
            padre,
            text=etiqueta,
            font=FUENTE_LABEL,
            fg=tema.get("TEXTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        lbl.pack(anchor="w")
        self._labels.append(lbl)

        fila = tk.Frame(padre, bg=tema.get("FONDO_PANEL"))
        fila.pack(fill="x", pady=(4, 0))
        self._frames.append(fila)

        entry = tk.Entry(
            fila,
            textvariable=variable,
            font=FUENTE_MONO,
            bg=tema.get("FONDO_ENTRADA"),
            fg=tema.get("TEXTO_CAMPO"),
            insertbackground=tema.get("TEXTO"),
            relief="flat",
            highlightthickness=1,
            highlightcolor=tema.get("ACENTO"),
            highlightbackground=tema.get("BORDE"),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=6)
        self._entries.append(entry)

        btn = tk.Button(
            fila,
            text="Examinar…",
            command=comando,
            font=FUENTE_BTN,
            bg=tema.get("BORDE"),
            fg=tema.get("TEXTO"),
            activebackground=tema.get("ACENTO"),
            activeforeground=tema.get("TEXTO"),
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=6,
        )
        btn.pack(side="left", padx=(8, 0))
        aplicar_hover(btn, tema.get("ACENTO"), tema.get("BORDE"))
        self._botones.append(btn)

    def actualizar_tema(self) -> None:
        """Actualiza todos los colores del RoutePanel al tema activo."""
        fp = tema.get("FONDO_PANEL")
        self.config(bg=fp, highlightbackground=tema.get("BORDE"))
        self._interior.config(bg=fp)
        self._lbl_seccion.config(fg=tema.get("ACENTO"), bg=fp)
        self._sep_titulo.config(bg=tema.get("BORDE"))
        self._sep_medio.config(bg=tema.get("FONDO"))

        for lbl in self._labels:
            lbl.config(fg=tema.get("TEXTO"), bg=fp)

        for frame in self._frames:
            frame.config(bg=fp)

        for entry in self._entries:
            entry.config(
                bg=tema.get("FONDO_ENTRADA"),
                fg=tema.get("TEXTO_CAMPO"),
                insertbackground=tema.get("TEXTO"),
                highlightcolor=tema.get("ACENTO"),
                highlightbackground=tema.get("BORDE"),
            )

        for btn in self._botones:
            btn.config(
                bg=tema.get("BORDE"),
                fg=tema.get("TEXTO"),
                activebackground=tema.get("ACENTO"),
                activeforeground=tema.get("TEXTO"),
            )
            # Re-bind hover con colores actualizados
            aplicar_hover(btn, tema.get("ACENTO"), tema.get("BORDE"))

    def _seleccionar_entrada(self):
        from tkinter import filedialog

        ruta = filedialog.askdirectory(title="Selecciona la carpeta con los archivos DOCX")
        if ruta:
            self.var_entrada.set(ruta)
            self._on_entrada(ruta)

    def _seleccionar_salida(self):
        from tkinter import filedialog

        ruta = filedialog.askdirectory(title="Selecciona la carpeta de destino para los PDFs")
        if ruta:
            self.var_salida.set(ruta)
            self._on_salida(ruta)


# ══════════════════════════════════════════════════════════════
#  ProgressPanel
# ══════════════════════════════════════════════════════════════

class ProgressPanel(tk.Frame):
    def __init__(
        self,
        master,
        on_iniciar: Callable,
        on_cancelar: Callable,
        **kwargs,
    ):
        super().__init__(
            master,
            bg=tema.get("FONDO_PANEL"),
            highlightbackground=tema.get("BORDE"),
            highlightthickness=1,
            **kwargs,
        )
        self._on_iniciar = on_iniciar
        self._on_cancelar = on_cancelar
        self._construir()

    def _construir(self):
        self._interior = tk.Frame(
            self, bg=tema.get("FONDO_PANEL"), padx=20, pady=14
        )
        self._interior.pack(fill="x")

        self._fila_estado = tk.Frame(self._interior, bg=tema.get("FONDO_PANEL"))
        self._fila_estado.pack(fill="x", pady=(0, 8))

        self.lbl_estado = tk.Label(
            self._fila_estado,
            text="En espera…",
            font=FUENTE_NORMAL,
            fg=tema.get("TEXTO_SEC"),
            bg=tema.get("FONDO_PANEL"),
        )
        self.lbl_estado.pack(side="left")

        self.lbl_pct = tk.Label(
            self._fila_estado,
            text="0 %",
            font=("Segoe UI", 10, "bold"),
            fg=tema.get("ACENTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        self.lbl_pct.pack(side="right")

        self.canvas = tk.Canvas(
            self._interior,
            height=10,
            bg=tema.get("FONDO_ENTRADA"),
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill="x")
        self._barra = self.canvas.create_rectangle(
            0, 0, 0, 10, fill=tema.get("ACENTO"), outline=""
        )

        self._fila_btn = tk.Frame(self._interior, bg=tema.get("FONDO_PANEL"))
        self._fila_btn.pack(fill="x", pady=(14, 0))

        self.btn_iniciar = tk.Button(
            self._fila_btn,
            text="▶  INICIAR CONVERSIÓN",
            command=self._on_iniciar,
            font=FUENTE_BTN_PRI,
            bg=tema.get("ACENTO"),
            fg=tema.get("BTN_PRI_FG"),
            activebackground=tema.get("ACENTO_HOVER"),
            activeforeground=tema.get("BTN_PRI_FG"),
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=10,
        )
        self.btn_iniciar.pack(side="left", fill="x", expand=True)

        self._sep_btn = tk.Frame(
            self._fila_btn, bg=tema.get("FONDO_PANEL"), width=10
        )
        self._sep_btn.pack(side="left")

        self.btn_cancelar = tk.Button(
            self._fila_btn,
            text="⏹  Cancelar",
            command=self._on_cancelar,
            font=FUENTE_BTN,
            bg=tema.get("FONDO_ENTRADA"),
            fg=tema.get("TEXTO_SEC"),
            activebackground=tema.get("ERROR_COLOR"),
            activeforeground=tema.get("BTN_PRI_FG"),
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=10,
            state="disabled",
        )
        self.btn_cancelar.pack(side="left")

    def set_progreso(self, fraccion: float) -> None:
        fraccion = max(0.0, min(1.0, fraccion))
        pct = int(fraccion * 100)
        self.lbl_pct.config(text=f"{pct} %")

        self.canvas.update_idletasks()
        ancho = max(self.canvas.winfo_width(), 1)
        self.canvas.coords(self._barra, 0, 0, ancho * fraccion, 10)
        self.canvas.itemconfig(
            self._barra,
            fill=tema.get("EXITO") if fraccion >= 1 else tema.get("ACENTO"),
        )

    def set_en_proceso(self, activo: bool) -> None:
        if activo:
            self.btn_iniciar.config(state="disabled", bg=tema.get("BORDE"))
            self.btn_cancelar.config(state="normal")
            self.lbl_estado.config(text="Convirtiendo…", fg=tema.get("ACENTO"))
        else:
            self.btn_iniciar.config(state="normal", bg=tema.get("ACENTO"))
            self.btn_cancelar.config(state="disabled")

    def set_estado(self, texto: str, color: str) -> None:
        self.lbl_estado.config(text=texto, fg=color)

    def actualizar_tema(self) -> None:
        """Actualiza todos los colores del ProgressPanel al tema activo."""
        fp = tema.get("FONDO_PANEL")
        self.config(bg=fp, highlightbackground=tema.get("BORDE"))
        self._interior.config(bg=fp)
        self._fila_estado.config(bg=fp)
        self._fila_btn.config(bg=fp)
        self._sep_btn.config(bg=fp)

        self.lbl_estado.config(bg=fp)
        self.lbl_pct.config(fg=tema.get("ACENTO"), bg=fp)
        self.canvas.config(bg=tema.get("FONDO_ENTRADA"))

        # Actualizar la barra: mantener color según progreso actual
        self.canvas.itemconfig(self._barra, fill=tema.get("ACENTO"))

        # Botón iniciar: respetar estado actual (disabled usa color BORDE)
        if str(self.btn_iniciar.cget("state")) == "disabled":
            self.btn_iniciar.config(
                bg=tema.get("BORDE"),
                fg=tema.get("BTN_PRI_FG"),
                activebackground=tema.get("ACENTO_HOVER"),
                activeforeground=tema.get("BTN_PRI_FG"),
            )
        else:
            self.btn_iniciar.config(
                bg=tema.get("ACENTO"),
                fg=tema.get("BTN_PRI_FG"),
                activebackground=tema.get("ACENTO_HOVER"),
                activeforeground=tema.get("BTN_PRI_FG"),
            )

        self.btn_cancelar.config(
            bg=tema.get("FONDO_ENTRADA"),
            fg=tema.get("TEXTO_SEC"),
            activebackground=tema.get("ERROR_COLOR"),
            activeforeground=tema.get("BTN_PRI_FG"),
        )


# ══════════════════════════════════════════════════════════════
#  LogPanel
# ══════════════════════════════════════════════════════════════

class LogPanel(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._construir()

    @property
    def _tag_colors(self) -> dict[str, str]:
        """Devuelve colores de tags según el tema activo."""
        return {
            "info":   tema.get("TEXTO_SEC"),
            "normal": tema.get("TEXTO"),
            "ok":     tema.get("EXITO"),
            "error":  tema.get("ERROR_COLOR"),
            "warn":   tema.get("ADVERTENCIA"),
            "sep":    tema.get("BORDE"),
        }

    def _construir(self):
        self._cab = tk.Frame(
            self,
            bg=tema.get("FONDO_PANEL"),
            highlightbackground=tema.get("BORDE"),
            highlightthickness=1,
        )
        self._cab.pack(fill="x")

        self._cab_int = tk.Frame(
            self._cab, bg=tema.get("FONDO_PANEL"), padx=20, pady=10
        )
        self._cab_int.pack(fill="x")

        self._lbl_titulo = tk.Label(
            self._cab_int,
            text="REGISTRO DE ACTIVIDAD",
            font=("Segoe UI", 8, "bold"),
            fg=tema.get("ACENTO"),
            bg=tema.get("FONDO_PANEL"),
        )
        self._lbl_titulo.pack(side="left")

        self._btn_limpiar = tk.Button(
            self._cab_int,
            text="Limpiar",
            command=self.limpiar,
            font=("Segoe UI", 8),
            bg=tema.get("BORDE"),
            fg=tema.get("TEXTO_SEC"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2,
        )
        self._btn_limpiar.pack(side="right")

        self._frame_txt = tk.Frame(
            self,
            bg=tema.get("FONDO_PANEL"),
            highlightbackground=tema.get("BORDE"),
            highlightthickness=1,
        )
        self._frame_txt.pack(fill="both")

        self._scrollbar = tk.Scrollbar(
            self._frame_txt, bg=tema.get("FONDO_PANEL")
        )
        self._scrollbar.pack(side="right", fill="y")

        self._txt = tk.Text(
            self._frame_txt,
            height=10,
            font=FUENTE_MONO,
            bg=tema.get("FONDO_LOG"),
            fg=tema.get("TEXTO_SEC"),
            insertbackground=tema.get("TEXTO"),
            relief="flat",
            wrap="word",
            state="disabled",
            yscrollcommand=self._scrollbar.set,
            padx=14,
            pady=10,
        )
        self._txt.pack(fill="both", expand=True)
        self._scrollbar.config(command=self._txt.yview)

        # Configurar tags con colores del tema
        for tag, color in self._tag_colors.items():
            self._txt.tag_config(tag, foreground=color)

    def actualizar_tema(self) -> None:
        """Actualiza todos los colores del LogPanel al tema activo."""
        fp = tema.get("FONDO_PANEL")
        self.config(bg=tema.get("FONDO"))
        self._cab.config(bg=fp, highlightbackground=tema.get("BORDE"))
        self._cab_int.config(bg=fp)
        self._lbl_titulo.config(fg=tema.get("ACENTO"), bg=fp)
        self._btn_limpiar.config(
            bg=tema.get("BORDE"), fg=tema.get("TEXTO_SEC")
        )

        self._frame_txt.config(
            bg=fp, highlightbackground=tema.get("BORDE")
        )
        self._scrollbar.config(bg=fp)
        self._txt.config(
            bg=tema.get("FONDO_LOG"),
            fg=tema.get("TEXTO_SEC"),
            insertbackground=tema.get("TEXTO"),
        )

        # Re-configurar colores de tags
        for tag, color in self._tag_colors.items():
            self._txt.tag_config(tag, foreground=color)

    def agregar(self, mensaje: str, tipo: str = "normal") -> None:
        self._txt.config(state="normal")
        self._txt.insert("end", mensaje + "\n", tipo if tipo in self._tag_colors else "normal")
        self._txt.see("end")
        self._txt.config(state="disabled")

    def limpiar(self) -> None:
        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.config(state="disabled")