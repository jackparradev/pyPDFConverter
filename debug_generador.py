"""
debug_generador.py
==================
Ventana de diagnóstico para el Modo 2 (Generar DOCX).
Prueba cada componente por separado y muestra el error exacto.

Ejecutar con:
    python debug_generador.py
"""
from __future__ import annotations

import sys
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext

# ── Asegura que el directorio raíz esté en el path ──────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════
#  Constantes de UI
# ══════════════════════════════════════════════════════════════════
FONDO       = "#1a1a2e"
PANEL       = "#16213e"
ACENTO      = "#e94560"
TEXTO       = "#e0e0e0"
TEXTO_SEC   = "#8892a4"
VERDE       = "#4caf82"
AMARILLO    = "#f59e0b"
ROJO        = "#e94560"
BORDE       = "#2d3561"
FONDO_ENTRY = "#0f3460"
MONO        = ("Consolas", 9)
LABEL_F     = ("Segoe UI", 9)
BTN_F       = ("Segoe UI", 9, "bold")
TITULO_F    = ("Segoe UI", 13, "bold")


# ══════════════════════════════════════════════════════════════════
#  Ventana principal
# ══════════════════════════════════════════════════════════════════
class DiagnosticoWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("🔍  Docusol — Diagnóstico del Generador")
        self.configure(bg=FONDO)
        self.resizable(True, True)

        # Variables de ruta
        self.var_excel     = tk.StringVar()
        self.var_plantilla = tk.StringVar()
        self.var_imagenes  = tk.StringVar()
        self.var_salida    = tk.StringVar()
        self.var_grupo     = tk.StringVar()

        self._construir()
        self._centrar(820, 700)

    # ── Layout ────────────────────────────────────────────────────

    def _construir(self) -> None:
        # Título
        tk.Label(
            self, text="🔍  Diagnóstico del Generador DOCX",
            font=TITULO_F, fg=ACENTO, bg=FONDO,
        ).pack(pady=(18, 4))

        tk.Label(
            self,
            text="Selecciona las rutas y ejecuta cada prueba por separado para identificar el problema.",
            font=("Segoe UI", 9), fg=TEXTO_SEC, bg=FONDO,
        ).pack(pady=(0, 12))

        # Panel de rutas
        frame_rutas = tk.Frame(self, bg=PANEL, highlightbackground=BORDE, highlightthickness=1)
        frame_rutas.pack(fill="x", padx=18, pady=(0, 10))

        interior = tk.Frame(frame_rutas, bg=PANEL, padx=16, pady=12)
        interior.pack(fill="x")

        self._fila(interior, "📊  Archivo Excel (.xlsx):",    self.var_excel,     self._sel_excel)
        self._fila(interior, "📄  Plantilla Word (.docx):",   self.var_plantilla, self._sel_plantilla)
        self._fila(interior, "🖼️   Carpeta de Imágenes:",      self.var_imagenes,  self._sel_imagenes)
        self._fila(interior, "📁  Carpeta de Salida:",         self.var_salida,    self._sel_salida)
        
        # Filtro de grupo opcional (sin botón de examinar)
        tk.Label(interior, text="🔍  Filtro Grupo (opcional):", font=LABEL_F, fg=TEXTO, bg=PANEL).pack(anchor="w")
        fila_g = tk.Frame(interior, bg=PANEL)
        fila_g.pack(fill="x", pady=(2, 8))
        tk.Entry(
            fila_g, textvariable=self.var_grupo, font=MONO,
            bg=FONDO_ENTRY, fg=TEXTO, insertbackground=TEXTO,
            relief="flat", highlightthickness=1,
            highlightbackground=BORDE, highlightcolor=ACENTO,
        ).pack(side="left", fill="x", expand=True, ipady=6, ipadx=4)

        # Botones de prueba individuales
        frame_btns = tk.Frame(self, bg=FONDO)
        frame_btns.pack(fill="x", padx=18, pady=(0, 8))

        pruebas = [
            ("📊  Probar Excel",      self._probar_excel,     "#1d4ed8"),
            ("🖼️  Probar Imágenes",   self._probar_imagenes,  "#065f46"),
            ("📄  Probar Plantilla",  self._probar_plantilla, "#7c3aed"),
            ("🚀  Prueba Completa",   self._probar_todo,      ACENTO),
        ]
        for texto, cmd, color in pruebas:
            tk.Button(
                frame_btns, text=texto, command=cmd,
                font=BTN_F, bg=color, fg="white",
                activebackground=color, activeforeground="white",
                relief="flat", cursor="hand2", padx=10, pady=8,
            ).pack(side="left", fill="x", expand=True, padx=3)

        # Botón limpiar
        tk.Button(
            self, text="🗑  Limpiar log",
            command=self._limpiar,
            font=("Segoe UI", 8), bg=BORDE, fg=TEXTO_SEC,
            relief="flat", cursor="hand2", padx=8, pady=4,
        ).pack(anchor="e", padx=18)

        # Log
        self._log = scrolledtext.ScrolledText(
            self, font=MONO, bg="#0a0a1a", fg=TEXTO,
            relief="flat", state="disabled",
            wrap="word", padx=12, pady=10,
        )
        self._log.pack(fill="both", expand=True, padx=18, pady=(4, 18))

        # Configurar tags de color
        self._log.tag_config("ok",     foreground=VERDE)
        self._log.tag_config("error",  foreground=ROJO)
        self._log.tag_config("warn",   foreground=AMARILLO)
        self._log.tag_config("info",   foreground=TEXTO_SEC)
        self._log.tag_config("titulo", foreground=ACENTO,   font=("Segoe UI", 9, "bold"))
        self._log.tag_config("normal", foreground=TEXTO)
        self._log.tag_config("sep",    foreground=BORDE)

    def _fila(self, padre, etiqueta: str, var: tk.StringVar, cmd) -> None:
        tk.Label(padre, text=etiqueta, font=LABEL_F, fg=TEXTO, bg=PANEL).pack(anchor="w")
        fila = tk.Frame(padre, bg=PANEL)
        fila.pack(fill="x", pady=(2, 8))
        tk.Entry(
            fila, textvariable=var, font=MONO,
            bg=FONDO_ENTRY, fg=TEXTO, insertbackground=TEXTO,
            relief="flat", highlightthickness=1,
            highlightbackground=BORDE, highlightcolor=ACENTO,
        ).pack(side="left", fill="x", expand=True, ipady=6, ipadx=4)
        tk.Button(
            fila, text="Examinar…", command=cmd,
            font=("Segoe UI", 8), bg=BORDE, fg=TEXTO,
            activebackground=ACENTO, activeforeground="white",
            relief="flat", cursor="hand2", padx=10, pady=5,
        ).pack(side="left", padx=(6, 0))

    def _centrar(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── Selectores de archivo ─────────────────────────────────────

    def _sel_excel(self) -> None:
        r = filedialog.askopenfilename(
            title="Selecciona el archivo Excel",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
        )
        if r:
            self.var_excel.set(r)

    def _sel_plantilla(self) -> None:
        r = filedialog.askopenfilename(
            title="Selecciona la plantilla Word",
            filetypes=[("Word", "*.docx"), ("Todos", "*.*")],
        )
        if r:
            self.var_plantilla.set(r)

    def _sel_imagenes(self) -> None:
        r = filedialog.askdirectory(title="Selecciona la carpeta de imágenes")
        if r:
            self.var_imagenes.set(r)

    def _sel_salida(self) -> None:
        r = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if r:
            self.var_salida.set(r)

    # ── Log helpers ───────────────────────────────────────────────

    def _write(self, texto: str, tag: str = "normal") -> None:
        self._log.config(state="normal")
        self._log.insert("end", texto + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _sep(self) -> None:
        self._write("─" * 60, "sep")

    def _limpiar(self) -> None:
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    # ══════════════════════════════════════════════════════════════
    #  PRUEBA 1 — Excel
    # ══════════════════════════════════════════════════════════════
    def _probar_excel(self) -> None:
        self._sep()
        self._write("📊  PRUEBA: Lectura del Excel", "titulo")
        self._sep()

        ruta = self.var_excel.get().strip()
        if not ruta:
            self._write("❌  No has seleccionado ningún archivo Excel.", "error")
            return

        self._write(f"   Ruta : {ruta}", "info")

        # Existencia
        p = Path(ruta)
        if not p.exists():
            self._write("❌  El archivo NO existe en esa ruta.", "error")
            return
        self._write("   ✓  Archivo encontrado en disco.", "ok")

        # Parseo
        try:
            from core.excel_parser import ExcelParser, MAPA_CABECERAS
            parser = ExcelParser()
            filas = parser.leer(p)
            self._write(f"   ✓  Excel leído correctamente. Filas de datos: {len(filas)}", "ok")
            self._write("", "normal")
            self._write("   Columnas requeridas:", "info")
            for cab_excel, llave in MAPA_CABECERAS.items():
                self._write(f"      • {cab_excel}  →  {llave}", "info")
            self._write("", "normal")
            if filas:
                self._write("   Primera fila extraída:", "info")
                for k, v in filas[0].items():
                    self._write(f"      {k}: {v!r}", "normal")
        except Exception as exc:
            self._write(f"❌  Error al leer el Excel:\n   {exc}", "error")
            self._write("", "normal")
            self._write("   Traza completa:", "warn")
            self._write(traceback.format_exc(), "warn")

    # ══════════════════════════════════════════════════════════════
    #  PRUEBA 2 — Imágenes (primera fila del Excel)
    # ══════════════════════════════════════════════════════════════
    def _probar_imagenes(self) -> None:
        self._sep()
        self._write("🖼️   PRUEBA: Localización de Imágenes (primera fila)", "titulo")
        self._sep()

        ruta_excel    = self.var_excel.get().strip()
        ruta_imagenes = self.var_imagenes.get().strip()
        grupo_filtro  = self.var_grupo.get().strip()

        if not ruta_excel:
            self._write("❌  Selecciona primero el Excel (necesario para leer placa y fecha).", "error")
            return
        if not ruta_imagenes:
            self._write("❌  No has seleccionado la carpeta de imágenes.", "error")
            return

        carpeta = Path(ruta_imagenes)
        if not carpeta.exists():
            self._write(f"❌  La carpeta de imágenes NO existe:\n   {carpeta}", "error")
            return
        self._write(f"   Carpeta : {carpeta}", "info")

        # Listar subcarpetas para referencia
        subcarpetas = [e.name for e in carpeta.iterdir() if e.is_dir()]
        self._write(f"   Subcarpetas encontradas ({len(subcarpetas)}):", "info")
        for sc in subcarpetas[:10]:
            self._write(f"      📂 {sc}", "normal")
        if len(subcarpetas) > 10:
            self._write(f"      ... y {len(subcarpetas)-10} más", "info")

        # Leer primera fila del Excel que coincida con el grupo
        try:
            from core.excel_parser import ExcelParser
            filas = ExcelParser().leer(Path(ruta_excel))
        except Exception as exc:
            self._write(f"❌  No se pudo leer el Excel: {exc}", "error")
            return

        if not filas:
            self._write("❌  El Excel no tiene filas de datos.", "error")
            return

        fila = None
        if grupo_filtro:
            def _grupo_str(valor) -> str:
                if isinstance(valor, float) and valor.is_integer():
                    return str(int(valor))
                return str(valor).strip() if valor is not None else ""
            
            for f in filas:
                if _grupo_str(f.get("grupo")).lower() == grupo_filtro.lower():
                    fila = f
                    break
            if not fila:
                self._write(f"❌  No se encontró ninguna fila con el grupo '{grupo_filtro}'.", "error")
                return
        else:
            fila = filas[0]
        placa      = str(fila.get("placa", "") or "")
        fecha_txt  = str(fila.get("fecha_fuga_texto", "") or "")
        self._write("", "normal")
        self._write(f"   Primera fila → placa: {placa!r}  |  fecha: {fecha_txt!r}", "info")

        # AssetLocator
        try:
            from core.asset_locator import AssetLocator
            locator = AssetLocator()
            rutas = locator.localizar_imagenes(
                carpeta_general=carpeta,
                placa=placa,
                fecha_texto=fecha_txt,
            )
            self._write("", "normal")
            self._write("   ✓  Imágenes localizadas:", "ok")
            for clave, ruta in rutas.items():
                self._write(f"      {clave}: {ruta}", "ok")
        except Exception as exc:
            self._write(f"\n❌  Error localizando imágenes:\n   {exc}", "error")
            
            # --- AGREGADO PARA DIAGNÓSTICO PROFUNDO ---
            self._write("", "normal")
            self._write("   🔍  DIAGNÓSTICO PROFUNDO DEL DIRECTORIO:", "titulo")
            try:
                # Intentar adivinar la carpeta para mostrar los archivos reales
                fecha_dt = locator._parsear_fecha(placa, fecha_txt)
                fecha_carpeta = fecha_dt.strftime("%d-%m-%Y")
                placa_limpia = placa.replace("-", "").replace(" ", "")
                candidatas = [
                    d for d in carpeta.iterdir()
                    if d.is_dir() and placa.lower() in d.name.lower() 
                    and fecha_carpeta in d.name
                ]
                if candidatas:
                    c_real = candidatas[0]
                    self._write(f"   Carpeta candidata encontrada: {c_real.name}", "info")
                    self._write("   Archivos detectados adentro:", "warn")
                    archivos = list(c_real.iterdir())
                    if not archivos:
                        self._write("      (La carpeta está Vामध्येACÍA)", "error")
                    for a in archivos:
                        if a.is_file():
                            self._write(f"      📄 {a.name}  (ext: {a.suffix})", "normal")
                        else:
                            self._write(f"      📂 {a.name}  (es carpeta)", "normal")
                else:
                    self._write(f"   No se encontró ninguna subcarpeta para la placa {placa} y fecha {fecha_carpeta}", "error")
            except Exception as e_diag:
                self._write(f"   No se pudo realizar el diagnóstico: {e_diag}", "info")
            # ----------------------------------------
            self._write("", "normal")
            self._write("   ▶ El nombre de la carpeta debe contener la PLACA y la fecha en formato DD-MM-YYYY", "warn")
            self._write("   ▶ Ejemplo esperado:  A1B-123 VIA 100 11-06-2026", "warn")
            self._write("   ▶ Las imágenes deben llamarse:", "warn")
            from datetime import datetime
            try:
                dt = datetime.strptime(fecha_txt, "%d/%m/%Y %H:%M")
                fecha_arch = dt.strftime("%Y%m%d")
                placa_limpia = placa.replace("-","").replace(" ","")
                self._write(f"      IMG_CAM_PLACA_{placa_limpia}_{fecha_arch}.jpg", "warn")
                self._write(f"      IMG_FUGA_{placa_limpia}_{fecha_arch}.jpg", "warn")
                self._write(f"      CONSULTA SUNARP PLACA {placa}.jpg", "warn")
            except Exception:
                self._write("      (no se pudo calcular el nombre — revisa el formato de fecha)", "warn")

    # ══════════════════════════════════════════════════════════════
    #  PRUEBA 3 — Plantilla Word
    # ══════════════════════════════════════════════════════════════
    def _probar_plantilla(self) -> None:
        self._sep()
        self._write("📄  PRUEBA: Validación de la Plantilla Word", "titulo")
        self._sep()

        ruta = self.var_plantilla.get().strip()
        if not ruta:
            self._write("❌  No has seleccionado ninguna plantilla Word.", "error")
            return

        p = Path(ruta)
        self._write(f"   Ruta : {p}", "info")

        if not p.exists():
            self._write("❌  El archivo NO existe en esa ruta.", "error")
            return
        self._write("   ✓  Archivo encontrado en disco.", "ok")

        # Intentar abrirla con docxtpl
        try:
            from docxtpl import DocxTemplate
            tpl = DocxTemplate(str(p))
            # Extraer variables Jinja2 declaradas
            variables = tpl.get_undeclared_template_variables()
            self._write("", "normal")
            self._write(f"   ✓  Plantilla cargada correctamente con docxtpl.", "ok")
            self._write("", "normal")
            self._write(f"   Variables Jinja2 detectadas en la plantilla ({len(variables)}):", "info")
            if variables:
                for v in sorted(variables):
                    self._write(f"      • {{{{ {v} }}}}", "normal")
            else:
                self._write("      ⚠  NO se detectaron variables {{ }} en la plantilla.", "warn")
                self._write("      ¿Sigues usando la notación «Campo»? Debe cambiarse a {{ campo }}", "warn")
        except Exception as exc:
            self._write(f"❌  Error al abrir la plantilla:\n   {exc}", "error")
            self._write(traceback.format_exc(), "warn")
            return

        # Verificar variables requeridas
        requeridas = {
            "correlativo", "placa", "fecha_fuga_texto", "categoria",
            "estacion_peaje", "ubicacion", "distrito", "sentido",
            "provincia", "url_evidencia", "img_cam", "img_fuga", "img_sunarp",
        }
        presentes  = variables if isinstance(variables, set) else set(variables)
        faltantes  = requeridas - presentes
        extras     = presentes - requeridas

        self._write("", "normal")
        if faltantes:
            self._write(f"   ⚠  Variables requeridas AUSENTES en la plantilla:", "warn")
            for f in sorted(faltantes):
                self._write(f"      ✗  {{{{ {f} }}}}", "warn")
        else:
            self._write("   ✓  Todas las variables requeridas están presentes.", "ok")

        if extras:
            self._write(f"   ℹ  Variables extra en la plantilla (no son error):", "info")
            for e in sorted(extras):
                self._write(f"      +  {{{{ {e} }}}}", "info")

    # ══════════════════════════════════════════════════════════════
    #  PRUEBA 4 — Ciclo completo (primera fila)
    # ══════════════════════════════════════════════════════════════
    def _probar_todo(self) -> None:
        self._sep()
        self._write("🚀  PRUEBA COMPLETA: Generar 1 documento (primera fila)", "titulo")
        self._sep()

        excel     = self.var_excel.get().strip()
        plantilla = self.var_plantilla.get().strip()
        imagenes  = self.var_imagenes.get().strip()
        salida    = self.var_salida.get().strip()

        errores = []
        if not excel:     errores.append("Excel")
        if not plantilla: errores.append("Plantilla")
        if not imagenes:  errores.append("Carpeta de Imágenes")
        if not salida:    errores.append("Carpeta de Salida")
        if errores:
            self._write(f"❌  Faltan campos: {', '.join(errores)}", "error")
            return

        def _run():
            try:
                self.after(0, lambda: self._write("   Paso 1/4 — Leyendo Excel…", "info"))

                from core.excel_parser import ExcelParser
                filas = ExcelParser().leer(Path(excel))
                self.after(0, lambda: self._write(f"   ✓  {len(filas)} fila(s) leída(s).", "ok"))

                fila = filas[0]
                placa     = str(fila.get("placa", "") or "")
                fecha_txt = str(fila.get("fecha_fuga_texto", "") or "")
                correlat  = str(fila.get("correlativo", "PRUEBA") or "PRUEBA")
                self.after(0, lambda: self._write(
                    f"   Primera fila → correlativo={correlat!r}  placa={placa!r}  fecha={fecha_txt!r}", "normal"
                ))

                self.after(0, lambda: self._write("\n   Paso 2/4 — Localizando imágenes…", "info"))
                from core.asset_locator import AssetLocator
                rutas_img = AssetLocator().localizar_imagenes(
                    carpeta_general=Path(imagenes),
                    placa=placa,
                    fecha_texto=fecha_txt,
                )
                self.after(0, lambda: self._write("   ✓  3 imágenes localizadas.", "ok"))
                for clave, ruta in rutas_img.items():
                    self.after(0, lambda k=clave, r=ruta: self._write(f"      {k}: {r}", "normal"))

                self.after(0, lambda: self._write("\n   Paso 3/4 — Cargando plantilla…", "info"))
                from core.template_builder import TemplateBuilder
                builder = TemplateBuilder(Path(plantilla))
                self.after(0, lambda: self._write("   ✓  Plantilla cargada.", "ok"))

                self.after(0, lambda: self._write("\n   Paso 4/4 — Generando documento…", "info"))
                carpeta_salida = Path(salida)
                carpeta_salida.mkdir(parents=True, exist_ok=True)
                nombre = f"DEBUG_{correlat}_{placa}.docx"
                ruta_destino = carpeta_salida / nombre

                ruta_final = builder.generar(
                    datos_fila=fila,
                    rutas_imagenes=rutas_img,
                    ruta_destino=ruta_destino,
                )
                self.after(0, lambda: self._write(
                    f"\n   ✅  ÉXITO — Documento generado:\n   {ruta_final}", "ok"
                ))

            except Exception as exc:
                tb = traceback.format_exc()
                self.after(0, lambda: self._write(f"\n❌  FALLÓ en este paso:\n   {exc}", "error"))
                self.after(0, lambda: self._write("\n   Traza completa:", "warn"))
                self.after(0, lambda: self._write(tb, "warn"))

        threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = DiagnosticoWindow()
    app.mainloop()
