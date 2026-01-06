@echo off
echo Actualizando python
echo.
cls
python.exe -m pip install --upgrade pip
cls
echo --------- Importando paquetes de python ---------
echo.
pip install bs4
echo.
pip install requests
echo.
pip install pillow
echo.
pip install reportlab
echo.
pip install auto-py-to-exe
echo.
pip install cloudscraper
echo.
pip install pikepdf
echo.
pip install rich
echo.
pip install customtkinter
echo.
pip install httpx
echo.
pip install aiometer
echo.
echo Fin
pause