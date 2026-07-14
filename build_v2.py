import os
import subprocess
import sys

print("Instalando dependencias...")
subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

print("Compilando Docusol V2 con Nuitka...")
print("Esto puede tardar varios minutos. Por favor espera...")

subprocess.run([
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--windows-console-mode=disable",
    "--enable-plugin=tk-inter",
    "--include-data-dir=assets=assets",
    "--windows-icon-from-ico=assets/logo.ico",
    "--follow-imports",
    "--include-package=openpyxl",
    "--include-package=docxtpl",
    "--include-package=docx",
    "--include-package=lxml",
    "--include-package=jinja2",
    "--include-package=markupsafe",
    "--output-dir=dist/v2",
    "--output-filename=DocusolV2.exe",
    "main.py"
])

print("\n¡Compilación completada! ✔")
print("Puedes encontrar tu aplicación en la carpeta: dist/v2/main.dist/")
