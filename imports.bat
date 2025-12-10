@echo off
echo Actualizando python
echo.
cls
python.exe -m pip install --upgrade pip
echo Importando paquetes de python
echo.
pip install bs4
echo.
pip install requests
echo.
pip install pillow
echo.
pip install reportlab
echo.
pip install pyinstaller
echo.
echo Fin
pause