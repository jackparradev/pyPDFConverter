# ── Colores ────────────────────────────────────────────────────────────────
FONDO         = "#0F1117"
FONDO_PANEL   = "#1A1D27"
FONDO_ENTRADA = "#252836"
BORDE         = "#2E3250"
ACENTO        = "#4F6EF7"
ACENTO_HOVER  = "#6B87FF"
EXITO         = "#2ECC71"
ERROR_COLOR   = "#E74C3C"
ADVERTENCIA   = "#F39C12"
TEXTO         = "#E8EAF6"
TEXTO_SEC     = "#8892B0"
TEXTO_CAMPO   = "#CDD6F4"
 
# ── Tipografía ─────────────────────────────────────────────────────────────
FUENTE_TITULO  = ("Segoe UI", 18, "bold")
FUENTE_SUBTIT  = ("Segoe UI", 10)
FUENTE_LABEL   = ("Segoe UI", 10, "bold")
FUENTE_NORMAL  = ("Segoe UI", 10)
FUENTE_MONO    = ("Consolas", 9)
FUENTE_BTN     = ("Segoe UI", 10, "bold")
FUENTE_BTN_PRI = ("Segoe UI", 12, "bold")
 
 
def aplicar_hover(widget, color_on: str, color_off: str) -> None:
    """Vincula efecto hover a un widget Tkinter."""
    widget.bind("<Enter>", lambda _: widget.config(bg=color_on))
    widget.bind("<Leave>", lambda _: widget.config(bg=color_off))