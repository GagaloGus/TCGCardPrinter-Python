import requests
import webbrowser
import sys
import os


LAND_TYPES = ["Island", "Swamp", "Plains", "Mountain", "Forest"]
URLS = []

def borrar_ultimas_lineas(num_lineas:int):
    num_lineas+=1
    # ANSI escape code para mover el cursor hacia arriba
    sys.stdout.write("\033[F" * num_lineas)  # Mueve el cursor arriba
    sys.stdout.write("\033[K" * num_lineas)  # Borra las líneas
    sys.stdout.flush()
    
def yesNo_CustomChoice(text:str, trueOption:str = "si", falseOption:str = "no") -> bool:
    value = False
    while True:
        __inp = input(f"{text} [{trueOption}/{falseOption}]: \033[36m").lower()
        if __inp in [trueOption, falseOption]:
            value = __inp == trueOption
            break
        else:
            borrar_ultimas_lineas(0)
            print(f"\033[31m[Error: Opción no válida: {__inp}]\033[0m ", end="")
    print("\033[0m", end="")
    return value

def get_image_url(setID:str, cardID:int) -> str:
    data = requests.get(f"https://api.scryfall.com/cards/{setID}/{cardID}").json()

    cardName = data["name"]
    if cardName not in LAND_TYPES:
        raise ValueError(f"La carta no es una tierra! -> {cardName}")
    
    img_url = data["image_uris"]["border_crop"]
    print(f"{cardName} ({setID}/{cardID}) -> {img_url}")
    return img_url

def main_program():
    global URLS
    
    setID = input("\n\033[0m¿Cual es el set de la carta? (scryfall.com/card/\033[33mbfz\033[0m/268/mountain): \033[36m").strip()
    cardID = int(input("\033[0m¿Cual es el ID de la carta dentro del set? (scryfall.com/card/bfz/\033[33m268\033[0m/mountain): \033[36m").strip())

    try:
        data = requests.get(f"https://api.scryfall.com/cards/{setID}/{cardID}").json()
        cardName = data["name"]
        if cardName not in LAND_TYPES:
            raise ValueError(f"La carta no es una tierra! -> {cardName}")
        
        #Itera hacia arriba
        print("")
        i = cardID 
        while True:
            try:
                newUrl = get_image_url(setID, i)
                URLS.append(newUrl)
                i += 1
            except:
                break

        #Itera hacia abajo
        i = cardID - 1
        while True:
            try:
                newUrl = get_image_url(setID, i)
                URLS.append(newUrl)
                i -= 1
            except:
                break

    except Exception as e:
        print(f"\033[32m{e}\033[0m")

    print(f"\n\033[0mSe encontraron \033[36m{len(URLS)}\033[0m urls de tierras")
    abrir_navegador = yesNo_CustomChoice("¿Quieres abrirlas en el navegador?")

    if abrir_navegador:
            print("\033[33m -- ABRIENDO URLS... --")
            for url in URLS:
                if abrir_navegador:
                    webbrowser.open(url)

if __name__ == "__main__":
    os.system("cls")
    print(f"\033[33m======= OBTENER SET DE TIERRAS CUSTOM DE SCRYFALL =======")
    main_program()
    
    while True:
        print("")
        otra_vez = yesNo_CustomChoice("¿Quieres buscar mas tierras?")
        if(otra_vez):
            print(f"\n\033[33m==============================================================\\033[0m")
            main_program()
        else:
            break