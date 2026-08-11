#!/usr/bin/env bash
# RD 405/2023: actualizacion de los titulos DAM y DAW. Correr en tu maquina (boe.es no es alcanzable desde el sandbox).
set -e
cd "$(dirname "$0")/../corpus/normativa"
wget -O RD-405-2023-actualizacion-DAW.pdf "https://www.boe.es/boe/dias/2023/06/03/pdfs/BOE-A-2023-13221.pdf"
echo "Descargado. Anadelo al manifiesto con:"
echo "  python3 ../../scripts/anadir_al_manifiesto.py corpus/normativa/RD-405-2023-actualizacion-DAW.pdf 'BOE (boe.es)' 'dominio publico (art. 13 LPI)' completa false"
