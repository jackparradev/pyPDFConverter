import tkinter as tk
from pathlib import Path
from typing import Callable
 
try:
    from PIL import Image, ImageTk
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False
 
import ui.theme as T
 
 
# ═══════════════════════════════════════════════════════════════════════════
# PANEL DE CABECERA
# ═══════════════════════════════════════════════════════════════════════════
class HeaderPanel(tk.Frame):
    """Franja superior con logo, título y badge de versión."""
 
    LOGO_NAMES   = ("logo.png", "logo.gif", "logo.pgm", "logo.ppm")
    LOGO_MAX_H   = 52
    VERSION_TEXT = "v1.0"
 
    def __init__(self, master, assets_dir: Path, **kwargs):
        super().__init__(master, bg=T.FONDO_PANEL, **kwargs)
        self._logo_img = self._cargar_logo(assets_dir)
        self._construir()
 
    def _construir(self):
        tk.Frame(self, bg=T.ACENTO, height=3).pack(fill="x")
 
        contenido = tk.Frame(self, bg=T.FONDO_PANEL, padx=28, pady=18)
        contenido.pack(fill="x")
 
        if self._logo_img:
            tk.Label(contenido, image=self._logo_img,
                     bg=T.FONDO_PANEL).pack(side="left", padx=(0, 18))
 
        textos = tk.Frame(contenido, bg=T.FONDO_PANEL)
        textos.pack(side="left", fill="x", expand=True)
        tk.Label(textos, text="Docusol",
                 font=T.FUENTE_TITULO, fg=T.TEXTO, bg=T.FONDO_PANEL).pack(anchor="w")
        tk.Label(textos,
                 text="DOCX  →  PDF  ·  Motor Microsoft Word  ·  Preserva hipervínculos",
                 font=T.FUENTE_SUBTIT, fg=T.TEXTO_SEC, bg=T.FONDO_PANEL).pack(anchor="w")
 
        tk.Label(contenido, text=self.VERSION_TEXT,
                 font=("Segoe UI", 8, "bold"), fg=T.ACENTO,
                 bg=T.FONDO_PANEL).pack(side="right", anchor="ne")
 
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
 
 
# ═══════════════════════════════════════════════════════════════════════════
# PANEL DE RUTAS
# ═══════════════════════════════════════════════════════════════════════════
class RoutePanel(tk.Frame):
    """Campos de entrada/salida con botones de exploración."""
 
    def __init__(self, master,
                 on_entrada: Callable[[str], None],
                 on_salida:  Callable[[str], None],
                 **kwargs):
        super().__init__(master, bg=T.FONDO_PANEL,
                         highlightbackground=T.BORDE, highlightthickness=1,
                         **kwargs)
        self._on_entrada = on_entrada
        self._on_salida  = on_salida
        self.var_entrada = tk.StringVar()
        self.var_salida  = tk.StringVar()
        self._construir()
 
    def _construir(self):
        interior = tk.Frame(self, bg=T.FONDO_PANEL, padx=20, pady=18)
        interior.pack(fill="x")
 
        tk.Label(interior, text="CONFIGURACIÓN DE RUTAS",
                 font=("Segoe UI", 8, "bold"), fg=T.ACENTO,
                 bg=T.FONDO_PANEL).pack(anchor="w")
        tk.Frame(interior, bg=T.BORDE, height=1).pack(fill="x", pady=(4, 14))
 
        self._fila_ruta(interior,
                        "📂  Carpeta de entrada  (archivos .docx)",
                        self.var_entrada,
                        self._seleccionar_entrada)
        tk.Frame(interior, bg=T.FONDO, height=10).pack()
        self._fila_ruta(interior,
                        "📁  Carpeta de salida  (PDFs generados)",
                        self.var_salida,
                        self._seleccionar_salida)
 
    def _fila_ruta(self, padre, etiqueta: str,
                   variable: tk.StringVar, comando: Callable):
        from tkinter import filedialog
        tk.Label(padre, text=etiqueta,
                 font=T.FUENTE_LABEL, fg=T.TEXTO,
                 bg=T.FONDO_PANEL).pack(anchor="w")
 
        fila = tk.Frame(padre, bg=T.FONDO_PANEL)
        fila.pack(fill="x", pady=(4, 0))
 
        tk.Entry(fila, textvariable=variable,
                 font=T.FUENTE_MONO, bg=T.FONDO_ENTRADA, fg=T.TEXTO_CAMPO,
                 insertbackground=T.TEXTO, relief="flat",
                 highlightthickness=1, highlightcolor=T.ACENTO,
                 highlightbackground=T.BORDE
                 ).pack(side="left", fill="x", expand=True, ipady=8, ipadx=6)
 
        btn = tk.Button(fila, text="Examinar…", command=comando,
                        font=T.FUENTE_BTN, bg=T.BORDE, fg=T.TEXTO,
                        activebackground=T.ACENTO, activeforeground=T.TEXTO,
                        relief="flat", cursor="hand2", padx=14, pady=6)
        btn.pack(side="left", padx=(8, 0))
        T.aplicar_hover(btn, T.ACENTO, T.BORDE)
 
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
 
 
# ═══════════════════════════════════════════════════════════════════════════
# PANEL DE PROGRESO Y BOTONES
# ═══════════════════════════════════════════════════════════════════════════
class ProgressPanel(tk.Frame):
    """Barra de progreso con botones Iniciar / Cancelar."""
 
    def __init__(self, master,
                 on_iniciar:  Callable,
                 on_cancelar: Callable,
                 **kwargs):
        super().__init__(master, bg=T.FONDO_PANEL,
                         highlightbackground=T.BORDE, highlightthickness=1,
                         **kwargs)
        self._on_iniciar  = on_iniciar
        self._on_cancelar = on_cancelar
        self._construir()
 
    def _construir(self):
        interior = tk.Frame(self, bg=T.FONDO_PANEL, padx=20, pady=14)
        interior.pack(fill="x")
 
        # Estado + porcentaje
        fila = tk.Frame(interior, bg=T.FONDO_PANEL)
        fila.pack(fill="x", pady=(0, 8))
        self.lbl_estado = tk.Label(fila, text="En espera…",
                                   font=T.FUENTE_NORMAL, fg=T.TEXTO_SEC,
                                   bg=T.FONDO_PANEL)
        self.lbl_estado.pack(side="left")
        self.lbl_pct = tk.Label(fila, text="0 %",
                                font=("Segoe UI", 10, "bold"), fg=T.ACENTO,
                                bg=T.FONDO_PANEL)
        self.lbl_pct.pack(side="right")
 
        # Barra canvas
        self.canvas = tk.Canvas(interior, height=10, bg=T.FONDO_ENTRADA,
                                bd=0, highlightthickness=0)
        self.canvas.pack(fill="x")
        self._barra = self.canvas.create_rectangle(0, 0, 0, 10,
                                                    fill=T.ACENTO, outline="")
 
        # Botones
        fila_btn = tk.Frame(interior, bg=T.FONDO_PANEL)
        fila_btn.pack(fill="x", pady=(14, 0))
 
        self.btn_iniciar = tk.Button(
            fila_btn, text="▶  INICIAR CONVERSIÓN",
            command=self._on_iniciar,
            font=T.FUENTE_BTN_PRI, bg=T.ACENTO, fg="#FFFFFF",
            activebackground=T.ACENTO_HOVER, activeforeground="#FFFFFF",
            relief="flat", cursor="hand2", padx=20, pady=10,
        )
        self.btn_iniciar.pack(side="left", fill="x", expand=True)
 
        tk.Frame(fila_btn, bg=T.FONDO_PANEL, width=10).pack(side="left")
 
        self.btn_cancelar = tk.Button(
            fila_btn, text="⏹  Cancelar",
            command=self._on_cancelar,
            font=T.FUENTE_BTN, bg=T.FONDO_ENTRADA, fg=T.TEXTO_SEC,
            activebackground=T.ERROR_COLOR, activeforeground="#FFFFFF",
            relief="flat", cursor="hand2", padx=16, pady=10,
            state="disabled",
        )
        self.btn_cancelar.pack(side="left")
 
    # ── API pública ────────────────────────────────────────────────────────
 
    def set_progreso(self, fraccion: float) -> None:
        pct   = int(fraccion * 100)
        ancho = self.canvas.winfo_width()
        color = T.EXITO if fraccion >= 1 else T.ACENTO
        self.lbl_pct.config(text=f"{pct} %")
        self.canvas.coords(self._barra, 0, 0, ancho * fraccion, 10)
        self.canvas.itemconfig(self._barra, fill=color)
 
    def set_en_proceso(self, activo: bool) -> None:
        if activo:
            self.btn_iniciar.config(state="disabled", bg=T.BORDE)
            self.btn_cancelar.config(state="normal")
            self.lbl_estado.config(text="Convirtiendo…", fg=T.ACENTO)
        else:
            self.btn_iniciar.config(state="normal", bg=T.ACENTO)
            self.btn_cancelar.config(state="disabled")
 
    def set_estado(self, texto: str, color: str) -> None:
        self.lbl_estado.config(text=texto, fg=color)
 
 
# ═══════════════════════════════════════════════════════════════════════════
# PANEL DE LOG
# ═══════════════════════════════════════════════════════════════════════════
class LogPanel(tk.Frame):
    """Área de texto con colores por tipo de mensaje y botón de limpieza."""
 
    TAGS = {
        "info":   T.TEXTO_SEC,
        "normal": T.TEXTO,
        "ok":     T.EXITO,
        "error":  T.ERROR_COLOR,
        "warn":   T.ADVERTENCIA,
        "sep":    T.BORDE,
    }
 
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._construir()
 
    def _construir(self):
        # Encabezado
        cab = tk.Frame(self, bg=T.FONDO_PANEL,
                       highlightbackground=T.BORDE, highlightthickness=1)
        cab.pack(fill="x")
        cab_int = tk.Frame(cab, bg=T.FONDO_PANEL, padx=20, pady=10)
        cab_int.pack(fill="x")
 
        tk.Label(cab_int, text="REGISTRO DE ACTIVIDAD",
                 font=("Segoe UI", 8, "bold"), fg=T.ACENTO,
                 bg=T.FONDO_PANEL).pack(side="left")
        tk.Button(cab_int, text="Limpiar", command=self.limpiar,
                  font=("Segoe UI", 8), bg=T.BORDE, fg=T.TEXTO_SEC,
                  relief="flat", cursor="hand2", padx=8, pady=2
                  ).pack(side="right")
 
        # Text + scrollbar
        frame_txt = tk.Frame(self, bg=T.FONDO_PANEL,
                             highlightbackground=T.BORDE, highlightthickness=1)
        frame_txt.pack(fill="both")
 
        scrollbar = tk.Scrollbar(frame_txt, bg=T.FONDO_PANEL)
        scrollbar.pack(side="right", fill="y")
 
        self._txt = tk.Text(
            frame_txt, height=10,
            font=T.FUENTE_MONO, bg="#0D0F18", fg=T.TEXTO_SEC,
            insertbackground=T.TEXTO, relief="flat",
            wrap="word", state="disabled",
            yscrollcommand=scrollbar.set,
            padx=14, pady=10,
        )
        self._txt.pack(fill="both", expand=True)
        scrollbar.config(command=self._txt.yview)
 
        for tag, color in self.TAGS.items():
            self._txt.tag_config(tag, foreground=color)
 
    # ── API pública ────────────────────────────────────────────────────────
 
    def agregar(self, mensaje: str, tipo: str = "normal") -> None:
        self._txt.config(state="normal")
        self._txt.insert("end", mensaje + "\n", tipo)
        self._txt.see("end")
        self._txt.config(state="disabled")
 
    def limpiar(self) -> None:
        self._txt.config(state="normal")
        self._txt.delete("1.0", "end")
        self._txt.config(state="disabled")