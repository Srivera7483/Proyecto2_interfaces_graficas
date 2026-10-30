@echo off
title Simulador Sensor - PMS7003ST
cd /d "%~dp0serial_sim"
echo ========================================================
echo   Iniciando Simulador hacia COM1 (9600-8N1, 0.1s)
echo ========================================================
python simu_trama.py COM1 0.1
pause

