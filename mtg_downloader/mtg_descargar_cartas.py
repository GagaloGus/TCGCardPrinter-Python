import sys
from enum import Enum
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
import requests
import re
import os
import cloudscraper
import subprocess

#Añade el directorio de arriba en el path para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))

from basicFunctions import *
from cardClasses import *

OUTPUT_DIR = ""
DOWNLOAD_LEN = 0
N_ERROR_LOAD = 0
N_ERROR_DOWNLOADS = 0

def callback():
    print("mamaguebo")

# ------------------------------------------------------------
# Detecta plataforma e ID del mazo
# ------------------------------------------------------------
def get_platform_and_id(url:str):
    if "archidekt" in url.lower():
        match = re.search(r"decks/(\d+)", url)
        if not match:
            raise ValueError("No pude sacar el ID de Archidekt.")
        return "archidekt", match.group(1)

    if "moxfield" in url.lower():
        deck_id = url.rstrip("/").split("/")[-1]
        return "moxfield", deck_id

    raise ValueError(f"\033[31m[!] Plataforma o web no soportada: \033[0m'{url}'")

# ------------------------------------------------------------
# Devuelve el JSON de la API del mazo
# ------------------------------------------------------------
def getJson_api_data(platform:str, deck_id:str):
    global DOWNLOAD_LEN
    if platform == "archidekt":
        api_url = f"https://archidekt.com/api/decks/{deck_id}/"

        resp = requests.get(api_url)

        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            raise ValueError("\033[31m[!] La API de Archidekt no devolvió JSON válido.")
        
        return resp.json()     
    elif platform == "moxfield":
        api_url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"

        #Crea un scraper de cloudflare
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(api_url)

        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            raise ValueError("\033[31m[!] La API de Moxfield no devolvió JSON válido.")

        return resp.json()
    else:
        raise ValueError(f"\033[31m[!] Plataforma no soportada: \033[0m'{platform}'")

# ------------------------------------------------------------
# Devuelve la longitud del mazo a imprimir
# ------------------------------------------------------------
def get_download_lenght(platform:str, deck_id:str, prnt_tokens:bool) -> int:
    
    count = 0
    # -------- ARCHIDEKT --------
    if platform == "archidekt":
        data = getJson_api_data(platform, deck_id)     
        
        #Skip a la maybe board y los tokens           
        skipTypes = ["Maybeboard"]
        if not prnt_tokens:
            skipTypes.append("Token")
        
        for c in data["cards"]:      
            cardTypes = list(c["categories"]) + list(c["card"]["oracleCard"]["types"])
            if any(x in cardTypes for x in skipTypes): #observa si se repite algun dato
                continue
    
            count += 1
        return count
            
    # -------- MOXFIELD --------
    elif platform == "moxfield":
        data = getJson_api_data(platform, deck_id)
    
        all_cards = {}
    
        for sec in ["mainboard", "commanders", "companions", "signatureSpells"]:
            if sec in data:
                for c in data[sec].values():
                    all_cards[c["card"]["scryfall_id"]] = c
    
        if prnt_tokens and "tokens" in data:
            for t in data["tokens"]:
                if t.get("layout") == "token":
                    all_cards[t["scryfall_id"]] = t
    
        return len(all_cards)


    else:
        raise ValueError(f"\033[31m[!] Plataforma no soportada: \033[0m'{platform}'")
 
# ------------------------------------------------------------
# Carga las cartas del mazo segun la plataforma
# ------------------------------------------------------------
def load_deck(platform:str, deck_id:str, prnt_tokens:bool, lang:str) -> list[CardClass]:
    global DOWNLOAD_LEN, N_ERROR_LOAD
    cards = []
            
    # -------- ARCHIDEKT --------
    with Progress(
        TextColumn("[bold]Obteniendo datos de cartas..."), BarColumn(), TextColumn("[bold]{task.completed} / {task.total}"), TimeRemainingColumn()
        ) as p:
        task = p.add_task("", total=DOWNLOAD_LEN)
        if platform == "archidekt":
            data = getJson_api_data(platform, deck_id)     

            #Skip a la maybe board y los tokens           
            skipTypes = ["Maybeboard"]
            if not prnt_tokens:
                skipTypes.append("Token")

            for c in data["cards"]:     
                cardTypes = list(c["categories"]) + list(c["card"]["oracleCard"]["types"])

                if any(x in cardTypes for x in skipTypes): #observa si se repite algun dato
                    continue
                
                editionCode = c["card"]["edition"]["editioncode"]
                collectorNumber = c["card"]["collectorNumber"]
                cardName = c["card"]["oracleCard"]["name"]

                #Si es un token, que solo imprima 1
                quantity = c["quantity"] if "Token" not in cardTypes else 1
            
                url = f"https://api.scryfall.com/cards/{editionCode}/{collectorNumber}"

                p.update(task, advance=1)   
                try:             
                    card = CardClass(quantity, url, lang)
                    cards.append(card)
                except Exception as e:
                    N_ERROR_LOAD+=1
                    raise ValueError(f"\033[31m[!]\033[0m Error bajando la imagen de {cardName}: {e.__str__()}")

        # -------- MOXFIELD --------
        elif platform == "moxfield":
            data = getJson_api_data(platform, deck_id)

            all_cards = {}
            i = 0

            #principales
            for sec in ["mainboard", "commanders", "companions", "signatureSpells"]:
                if sec in data:
                    for key, c in data[sec].items():
                        all_cards[i] = c
                        i += 1

            # tokens
            if prnt_tokens and "tokens" in data:
                for t in data["tokens"]:
                    if t.get("layout") == "token":
                        all_cards[i] = t
                        i+=1


            for id, value in all_cards.items():

                #Si tienen la lista "card" se usa esa, si no la lista normal
                if "card" in value:
                    card_data = value["card"]
                else:
                    card_data = value

                cardName = card_data["name"] if "name" in card_data else "NoName"
                scryfallID = card_data["scryfall_id"] 

                quantity = value["quantity"] if "quantity" in value else 1

                p.update(task, advance=1)   
                try:             
                    card = CardClass(quantity, f"https://api.scryfall.com/cards/{scryfallID}", lang)    
                    cards.append(card)
                except Exception as e:
                    N_ERROR_LOAD+=1     
                    (f"\033[31m[!]\033[0m Error bajando la imagen de {cardName}: {e.__str__()}")

        else:
            raise ValueError(f"\033[31m[!] Plataforma no soportada: \033[0m'{platform}'")
        
    return cards

# ------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------
def main():
    global OUTPUT_DIR, N_ERROR_LOAD, N_ERROR_DOWNLOADS, DOWNLOAD_LEN
    
    print(f"\033[33m======= DESCARGAR CARTAS MAGIC THE GATHERING =======")
    print(f"\033[0m- Plataformas admitidas: [ Archidekt, Moxfield ]\n")
    
    url = input("Pega la URL del mazo: \033[36m").strip()
    try:
        platform, deck_id = get_platform_and_id(url)
        deckName = getJson_api_data(platform, deck_id)["name"]
    except Exception as e:
        print(e)
        os.system("pause")
        os._exit(0)
        
    #Muestra los datos obtenidos
    borrar_ultimas_lineas(0)
    print(f"\033[33m-- {deckName} --")
    print(f"\033[33mPlataforma: \033[0m{platform.capitalize()}")
    print(f"\033[33mID del mazo: \033[0m'{deck_id}'")
    
    #Pregunta para imprimir los tokens
    prnt_tokens = yesNo_CustomChoice("¿Quieres imprimir tambien los tokens?", "si", "no")
    borrar_ultimas_lineas(0)
    print(f"\033[33mImprimir tokens: \033[0m'{'Si' if prnt_tokens else 'No'}'")
    
    #Pregunta el idioma de las cartas
    card_lang = multiple_CustomChoice(
        "Elige el idioma de las cartas:",
        ["Original", "English", "Español"]
    )
    
    if card_lang == 1:
        card_lang = "en"
    if card_lang == 2:
        card_lang = "es"
    else:
        card_lang = "orig"
        
    
    #Obtiene la longitud del mazo
    print("\nObteniendo longitud del mazo...")
    DOWNLOAD_LEN = get_download_lenght(platform, deck_id, prnt_tokens)
    borrar_ultimas_lineas(0)
    
    #Carga las cartas en una lista
    cards = load_deck(platform, deck_id, prnt_tokens, card_lang)
    
    #Ordena segun el tipo de carta
    cards.sort(key=lambda c: c.cardTypes[0].value)
    
    print(f"\nSe encontraron \033[36m{DOWNLOAD_LEN}\033[0m cartas (sin contar repetidos).")

    #Crea una carpeta donde se descargaran las cartas
    customFolderName = crear_directorio_nuevo(input("Quieres poner algun nombre a la carpeta de descarga? (Enter para no): \033[36m"))
    OUTPUT_DIR = os.path.join("cartas", customFolderName if customFolderName != "" else crear_directorio_nuevo(deckName))
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    print("\033[0m")
    
    #Descarga las cartas una por una
    with Progress(
        TextColumn("[bold]Descargando cartas..."), BarColumn(), TextColumn("[bold]{task.completed} / {task.total}"), TimeRemainingColumn()
        ) as p:
        task = p.add_task("", total=DOWNLOAD_LEN)
        for c in cards:
            p.update(task, advance=1)
            try:
                c.downloadImages(OUTPUT_DIR)
            except Exception as e:
                N_ERROR_DOWNLOADS += 1
                print(f"\033[31m[!]\033[0m Error bajando la imagen de {c.cardMainName} //  \033[0m{e}")

    print(f"\n\033[32mListo, mi rey. Todas las cartas estan en la carpeta '{OUTPUT_DIR}'\033[0m")
    
    N_ERROR_DOWNLOADS += N_ERROR_LOAD    
    if(N_ERROR_DOWNLOADS > 0):
        print(f"\033[33m[!] No se pudieron descargar {N_ERROR_DOWNLOADS} cartas, te toca descargalas manualmente :(\033[0m")
    
    #Permite directamente crear el imprimible de las imagenes
    try:
        import imprimir_cartas as modulo_imprimir
        imprimir_ahora = yesNo_CustomChoice("¿Quieres crear el PDF de las cartas?", "si", "no")
        
        if(imprimir_ahora):
            borrar_ultimas_lineas(0)
            print()
            modulo_imprimir.main(OUTPUT_DIR, "1")
            os._exit(0)
        else:
            subprocess.Popen(rf'explorer /select,"{OUTPUT_DIR}"')
            os.system("pause")
    except:
        print("\033[33m[!] El modulo de impresion no esta disponible desde este script.\033[0m")
        subprocess.Popen(rf'explorer /select,"{OUTPUT_DIR}"')
        os.system("pause")
        
if __name__ == "__main__":
    os.system("cls")
    main()


