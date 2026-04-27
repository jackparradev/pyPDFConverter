import os
import subprocess
import sys

print("Instalando dependencias...")
subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

print("Compilando con Nuitka...")
subprocess.run([
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--windows-console-mode=disable",
    "--enable-plugin=tk-inter",
    "--include-data-dir=assets=assets",
    "--windows-icon-from-ico=assets/logo.ico",
    "--follow-imports",
    "main.py"
])

print("Listo ✔")