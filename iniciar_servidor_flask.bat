@echo off
title Servidor Flask - DataLogger UMA
cd /d "%~dp0serial_sim"
echo ========================================================
echo   Iniciando Servidor Flask en http://127.0.0.1:5000
echo   Dashboard: http://127.0.0.1:5000/dashboard
echo ========================================================
python server_flask.py
pause

