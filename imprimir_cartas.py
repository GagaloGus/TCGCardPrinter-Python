import os
import sys
import re
import pikepdf
import subprocess
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image

INPUT_DIR = "cartas_imprimir"
OUTPUT_DIR = "pdf"
BACK_NAME = "back.png"
PDF_FRONT = ""
PDF_BACK = ""
BACK_IMAGE = ""
page_width, page_height = A4
cols = 0
rows = 0
card_w = 0
card_h = 0
card_margin = 0
x_start = 0
y_start = 0

def borrar_ultimas_lineas(num_lineas):
    num_lineas+=1
    # ANSI escape code para mover el cursor hacia arriba
    sys.stdout.write("\033[F" * num_lineas)  # Mueve el cursor arriba
    sys.stdout.write("\033[K" * num_lineas)  # Borra las líneas
    sys.stdout.flush()

def yesNo_CustomChoice(text:str, trueOption:str, falseOption:str) -> bool:
    value = False
    while True:
        __inp = input(f"{text} [{trueOption}/{falseOption}]: \033[36m").lower()
        if __inp in [trueOption, falseOption]:
            value = __inp == trueOption
            break
        else:
            print("\033[0m", end="")
            borrar_ultimas_lineas(0)
            print(f"\033[31m[Error: Opción no válida: {__inp}]\033[0m ", end="")
    return value

def comprimir_imagen(path, max_width_px=744, quality=85):
    img = Image.open(path).convert("RGB")

    # Redimensiona solo si es más grande
    if img.width > max_width_px:
        ratio = max_width_px / img.width
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    return img

def crear_directorio_nuevo(name: str) -> str:
    # Reemplaza caracteres no admitidos
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    return name

def dibujar_guias_pagina(c: canvas.Canvas,dash: bool = True, lines_between_cards:bool = True):
    global cols, rows, card_w, card_h, card_margin, x_start, y_start
    line_margin = 0.3
    # Estilo
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(line_margin)
    if dash:
        c.setDash(1, 2)  # guiones finos
    else:
        c.setDash()      # línea sólida

    y_bottom = y_start
    for row in range(rows):
        y_top = y_bottom + card_h
        c.line(0, y_top, page_width, y_top)
        c.line(0, y_bottom, page_width, y_bottom)
        y_bottom -= (card_h + card_margin)

    x_left = x_start
    for col in range(cols):
        x_right = x_left + card_w
        c.line(x_right, 0, x_right, page_height)
        c.line(x_left, 0, x_left, page_height)
        x_left += (card_w + card_margin)

    c.setDash()  # Reset dash a solido

def comprimir_pdf(input_pdf: str, output_pdf: str):
    if not os.path.exists(input_pdf):
        print(f"\033[33m[Error: No se encontró {input_pdf}]\033[0m")
        return

    try:
        print("Comprimiendo PDF...")
        pdf = pikepdf.open(input_pdf)
        pdf.save(output_pdf, compress_streams=True)
        pdf.close()
        borrar_ultimas_lineas(0)
        os.remove(input_pdf)
    except Exception as e:
        print(f"\033[31mError comprimiendo PDF {input_pdf}: {e}\033[0m")


def main(customInputDir = "", customTipoCarta = "-1"):
    global cols, rows, card_w, card_h, card_margin, x_start, y_start, INPUT_DIR
    
    print(f"\033[33m======= CREAR IMPRIMIBLE DE CARTAS =======\033[0m\n")
    
    #Se cambia el directorio de input por si se llama desde otro script
    if customInputDir != "":
        INPUT_DIR = customInputDir
    
    os.makedirs(INPUT_DIR, exist_ok=True)

    # Buscar imágenes
    images = sorted([f for f in os.listdir(INPUT_DIR)])
    if not images:
        print(f"\033[33mNo se encontraron imágenes en la carpeta '{INPUT_DIR}'\033[0m")
        os.system("pause")
        os._exit(0)
        
    print(f"\033[0mSe encontraron \033[36m{len(images)}\033[0m imágenes para imprimir.")
    
    DECK_DIR = os.path.join(OUTPUT_DIR, crear_directorio_nuevo(input("Quieres poner algun nombre a la carpeta? (Enter para no): \033[36m")))

    PDF_FRONT = os.path.join(DECK_DIR, "deck_front.pdf")
    PDF_BACK = os.path.join(DECK_DIR, "deck_back.pdf")
    BACK_IMAGE = os.path.join('cartas_imprimir', BACK_NAME)
    os.makedirs(DECK_DIR, exist_ok=True)
    
    # Configuracion del layout
    magicDim = (63, 88)
    yugiDim = (59, 86)
    pokerDim = (63.5, 88.9)
    tipo_carta = 0
    
    #Tipo de carta custom por si se llama desde otro script
    customTipoCarta = int(customTipoCarta)
    if customTipoCarta != -1 and customTipoCarta in [1, 2, 3, 4]:
        print("\n")
        tipo_carta = customTipoCarta
    else:
        while True:
            __inp = input(f"""\033[0m
Que dimensiones de carta quieres:
  1-> Magic The Gathering ({magicDim[0]}mm x {magicDim[1]}mm)
  2-> Yugioh ({yugiDim[0]}mm x {yugiDim[1]}mm)
  3-> Carta normal ({pokerDim[0]}mm x {pokerDim[1]}mm)
  4-> Otro\n\033[36m""")
            tipo_carta = int(__inp) if __inp.isdigit() else 0

            # Verificacion
            if tipo_carta in [1, 2, 3, 4]:
                break
            else:
                borrar_ultimas_lineas(5) 
                print(f"\033[33m[Error: Opción no válida: {tipo_carta}] \033[0m", end="")

            
    # Mostrar las dimensiones seleccionadas
    borrar_ultimas_lineas(0)
    print(f"\033[33m{tipo_carta}-> ",end="")
    
    if(tipo_carta == 1): #magic
        print(f"-- Magic --")
        card_w, card_h = magicDim[0]*mm, magicDim[1]*mm
    elif(tipo_carta == 2): #yugi
        print("-- YuGiOh --")
        card_w, card_h = yugiDim[0]*mm, yugiDim[1]*mm
    elif(tipo_carta == 3): #normal
        print("-- Carta normal --")
        card_w, card_h = pokerDim[0]*mm, pokerDim[1]*mm
    else: #custom
        print("-- Custom --")
        card_w = float(input("\033[33m  Anchura en milimetros: \033[36m"))*mm
        card_h = float(input("\033[33m  Altura en milimetros: \033[36m"))*mm
    
    print("\033[0m")
    
    # Configuracion del margen
    has_margin = yesNo_CustomChoice("¿Quieres que haya margen entre las cartas?", "si", "no")
    borrar_ultimas_lineas(0)
    print(f"\033[33m-- {'Con' if has_margin else 'Sin'} Margen --\033[0m")
    
    card_margin = 5*mm if has_margin else 0.3*mm       
    
    # Calcula cuantas cartas caben en horizontal y vertical
    cols = int(page_width // (card_w + card_margin))
    rows = int(page_height // (card_h + card_margin))

    # Centra horizontalmente
    total_width = cols * card_w + (cols - 1) * card_margin
    x_start = (page_width - total_width) / 2

    # Centra verticalmente
    total_height = rows * card_h + (rows - 1) * card_margin
    y_start = (page_height + total_height) / 2 - card_h

    # Crear PDF frontal
    tempPDFName = PDF_FRONT.replace(".pdf", "_temp.pdf")
    c = canvas.Canvas(tempPDFName, pagesize=A4)
    x, y = x_start, y_start
    count = 0
    dibujar_guias_pagina(c)

    print("\n\033[36mGenerando PDF", end="")
    for i in range(len(images)):
        img_name = images[i]
        # Se salta la imagen del dorso para evitar impresion innecesaria
        if(img_name == BACK_NAME):
            continue
        
        img_path = os.path.join(INPUT_DIR, img_name)
        img = comprimir_imagen(img_path)

        c.drawImage(ImageReader(img), x, y, width=card_w, height=card_h)

        count += 1
        x += card_w + card_margin
        if count % cols == 0:
            x = x_start
            y -= card_h + card_margin
        if count % (cols*rows) == 0 and i < len(images) - 1: # nueva pagina
            c.showPage()
            dibujar_guias_pagina(c)
            x, y = x_start, y_start
        print(".", end="", flush=True)

    c.save()
    print()
    comprimir_pdf(tempPDFName, PDF_FRONT)
    print(f"\033[32mPDF de cartas generado: \033[0m{PDF_FRONT}")
    
    # Crear PDF del dorso
    if os.path.exists(BACK_IMAGE):
        tempPDFName = PDF_BACK.replace(".pdf", "_temp.pdf")
        c = canvas.Canvas(tempPDFName, pagesize=A4)
        dibujar_guias_pagina(c)
        back = comprimir_imagen(BACK_IMAGE)
        x, y = x_start, y_start
        for _ in range(cols*rows):
            c.drawImage(ImageReader(back), x, y, width=card_w, height=card_h)
            x += card_w + card_margin
            if x > page_width - card_margin - card_w:
                x = x_start
                y -= card_h + card_margin
        c.showPage()
        c.save()
        comprimir_pdf(tempPDFName, PDF_BACK)
        print(f"\033[32mPDF de dorsos generado: \033[0m{PDF_BACK}")
    else:
        print(f"\033[33mNo encontré '{BACK_IMAGE}'\033[0m")
        
    subprocess.Popen(rf'explorer /select,"{PDF_FRONT}"')
    os.system("pause")
    os._exit(0)

if __name__ == "__main__": 
    os.system("cls")
    
    # Modifica si se ha llamado desde otro script con otros parametros
    if len(sys.argv) > 1:
        main(sys.argv[1], sys.argv[2])
    else:
        main()
    
    
