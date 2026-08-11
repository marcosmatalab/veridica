#!/usr/bin/env bash
# Fondo de armario: TemarioDAW entero (Comesana) para densidad PARCIAL del resto de asignaturas.
# SOLO si sobra tiempo al final de la fase 1. ~500 MB descomprimido.
set -e
cd "$(dirname "$0")/.."
git clone --depth 1 https://github.com/statickidz/TemarioDAW.git fondo-temario
echo "Clonado en fondo-temario/. Copia cada modulo a su carpeta de corpus/ y registra en el manifiesto con densidad=parcial."
