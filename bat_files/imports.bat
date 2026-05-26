@echo off
echo Actualizando python
echo.
cls
python.exe -m pip install --upgrade pip
cls
echo --------- Importando paquetes de python ---------
echo.
pip install bs4 --no-warn-script-location
echo.
pip install requests --no-warn-script-location
echo.
pip install pillow --no-warn-script-location
echo.
pip install reportlab --no-warn-script-location
echo.
pip install auto-py-to-exe --no-warn-script-location
echo.
pip install cloudscraper --no-warn-script-location
echo.
pip install pikepdf --no-warn-script-location
echo.
pip install --upgrade rich --no-warn-script-location
echo.
pip install customtkinter --no-warn-script-location
echo.
pip install httpx --no-warn-script-location
echo.
pip install aiometer --no-warn-script-location
echo.
echo Fin
pause