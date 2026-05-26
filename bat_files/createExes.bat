python -m PyInstaller --noconfirm --onefile --console ^
  --paths "E:\cartita\CardPrinter-Python\root" ^
  --distpath "..\dist" ^
  --hidden-import "rich._unicode_data" ^
  --hidden-import "rich._unicode_data.unicode17-0-0" ^
  "E:\cartita\CardPrinter-Python\root\mtg_downloader\mtg_descargar_cartas.py"

python -m PyInstaller --noconfirm --onefile --console ^
  --paths "E:\cartita\CardPrinter-Python\root" ^
  --distpath "..\dist" ^
  --hidden-import "rich._unicode_data" ^
  --hidden-import "rich._unicode_data.unicode17-0-0" ^
  "E:\cartita\CardPrinter-Python\root\card_printers\imprimir_cartas.py"

rmdir /s /q .\build\