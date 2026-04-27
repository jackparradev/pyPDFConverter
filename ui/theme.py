from __future__ import annotations

from typing import Callable

# ──────────────────────────────────────────────────────────────
# 🎨 SISTEMA DE COLORES (ALINEADO A COVISOL)
# ──────────────────────────────────────────────────────────────

DARK: dict[str, str] = {
    # ── Base ───────────────────────────────────────────────
    "FONDO":          "#0F1117",
    "FONDO_PANEL":    "#1A1D27",
    "FONDO_ENTRADA":  "#252836",
    "FONDO_LOG":      "#0D0F18",
    "BORDE":          "#2E3250",

    # ── Marca (Primario) ───────────────────────────────────
    "ACENTO":         "#E53935",   # rojo corporativo
    "ACENTO_HOVER":   "#FF5A4F",

    # ── Marca (Secundarios) ────────────────────────────────
    "ACENTO_SEC":     "#F39C12",   # naranja
    "ACENTO_SOFT":    "#FFB74D",   # amarillo suave

    # ── Estados ────────────────────────────────────────────
    "EXITO":          "#2ECC71",
    "ERROR_COLOR":    "#E53935",
    "ADVERTENCIA":    "#F39C12",

    # ── UX (Interacción) ───────────────────────────────────
    "FOCUS":          "#FF7043",   # borde activo input

    # ── Texto ──────────────────────────────────────────────
    "TEXTO":          "#EDEFF7",
    "TEXTO_SEC":      "#9AA4C7",
    "TEXTO_CAMPO":    "#D6DBF5",

    # ── Botones ────────────────────────────────────────────
    "BTN_PRI_FG":     "#FFFFFF",
}

LIGHT: dict[str, str] = {
    # ── Base ───────────────────────────────────────────────
    "FONDO":          "#F4F6F9",
    "FONDO_PANEL":    "#FFFFFF",
    "FONDO_ENTRADA":  "#EEF1F6",
    "FONDO_LOG":      "#F7F8FA",
    "BORDE":          "#D0D5DD",

    # ── Marca (Primario) ───────────────────────────────────
    "ACENTO":         "#E53935",
    "ACENTO_HOVER":   "#C62828",

    # ── Marca (Secundarios) ────────────────────────────────
    "ACENTO_SEC":     "#E67E22",
    "ACENTO_SOFT":    "#FFB74D",

    # ── Estados ────────────────────────────────────────────
    "EXITO":          "#27AE60",
    "ERROR_COLOR":    "#C62828",
    "ADVERTENCIA":    "#E67E22",

    # ── UX (Interacción) ───────────────────────────────────
    "FOCUS":          "#FF7043",

    # ── Texto ──────────────────────────────────────────────
    "TEXTO":          "#1A1D27",
    "TEXTO_SEC":      "#5A6278",
    "TEXTO_CAMPO":    "#2C3041",

    # ── Botones ────────────────────────────────────────────
    "BTN_PRI_FG":     "#FFFFFF",
}

# ──────────────────────────────────────────────────────────────
# 🅰️ TIPOGRAFÍA
# ──────────────────────────────────────────────────────────────

FUENTE_TITULO  = ("Segoe UI", 18, "bold")
FUENTE_SUBTIT  = ("Segoe UI", 10)
FUENTE_LABEL   = ("Segoe UI", 10, "bold")
FUENTE_NORMAL  = ("Segoe UI", 10)
FUENTE_MONO    = ("Consolas", 9)
FUENTE_BTN     = ("Segoe UI", 10, "bold")
FUENTE_BTN_PRI = ("Segoe UI", 12, "bold")

# ──────────────────────────────────────────────────────────────
# 🧠 THEME MANAGER (SIN CAMBIOS ESTRUCTURALES)
# ──────────────────────────────────────────────────────────────

_ObserverCallback = Callable[[], None]


class ThemeManager:
    """Gestiona el tema activo y notifica observers cuando cambia."""

    _TEMAS: dict[str, dict[str, str]] = {
        "dark":  DARK,
        "light": LIGHT,
    }

    def __init__(self, tema_inicial: str = "dark") -> None:
        if tema_inicial not in self._TEMAS:
            raise ValueError(f"Tema desconocido: {tema_inicial!r}")
        self._actual: str = tema_inicial
        self._observers: list[_ObserverCallback] = []

    # ── Lectura ──────────────────────────────────────────────

    @property
    def current(self) -> str:
        return self._actual

    @property
    def is_dark(self) -> bool:
        return self._actual == "dark"

    def get(self, key: str) -> str:
        return self._TEMAS[self._actual][key]

    # ── Escritura ────────────────────────────────────────────

    def set_theme(self, nombre: str) -> None:
        if nombre not in self._TEMAS:
            raise ValueError(f"Tema desconocido: {nombre!r}")
        if nombre == self._actual:
            return
        self._actual = nombre
        self._notificar()

    def toggle(self) -> None:
        nuevo = "light" if self._actual == "dark" else "dark"
        self.set_theme(nuevo)

    # ── Observer ─────────────────────────────────────────────

    def register(self, callback: _ObserverCallback) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister(self, callback: _ObserverCallback) -> None:
        try:
            self._observers.remove(callback)
        except ValueError:
            pass

    def _notificar(self) -> None:
        for cb in self._observers:
            cb()

    def __repr__(self) -> str:
        return f"ThemeManager(current={self._actual!r})"


# ──────────────────────────────────────────────────────────────
# 🌐 INSTANCIA GLOBAL
# ──────────────────────────────────────────────────────────────

tema = ThemeManager()

# ──────────────────────────────────────────────────────────────
# 🧩 UTILIDADES UI
# ──────────────────────────────────────────────────────────────

def aplicar_hover(widget, color_on: str, color_off: str) -> None:
    """Aplica efecto hover moderno (suave y consistente)."""
    widget.bind("<Enter>", lambda _: widget.config(bg=color_on))
    widget.bind("<Leave>", lambda _: widget.config(bg=color_off))


def aplicar_focus(entry, color_focus: str, color_normal: str) -> None:
    """Aplica efecto focus para inputs (UX profesional)."""
    entry.bind("<FocusIn>", lambda _: entry.config(highlightbackground=color_focus))
    entry.bind("<FocusOut>", lambda _: entry.config(highlightbackground=color_normal))