import sys
import requests
import re
import os
import cloudscraper
import subprocess

OUTPUT_DIR = ""
N_ERROR_DOWNLOADS = 0
NAMES_ERROR_DOWNLOADS = [str]

class CardClass:
    def __init__(self, cardID:int, quantity:int, scryfall_url:str):    
        #Pide el JSON de scryfall al crear la carta
        self.jsonData = requests.get(scryfall_url).json()
        
        self.cardMainName = self.jsonData["name"]
        self.cardNames = list[str](self.cardMainName.replace(" ", "").split("//"))
        self.cardTypes = list[str](self.jsonData["type_line"].replace(" ", "").lower().split("//"))
        self.cardID = str(cardID)
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        print(f"\033[33m[+]\033[0m Datos de carta cargados de -> {self.cardMainName}")
        
    def downloadImages(self, folder_path:str):
        global N_ERROR_DOWNLOADS, NAMES_ERROR_DOWNLOADS
        try:   
            img_urls = []
            
            if "image_uris" in self.jsonData:
                img_urls.append(self.jsonData["image_uris"]["border_crop"])
            elif "card_faces" in self.jsonData:
                for card_face in self.jsonData["card_faces"]:
                    img_urls.append(card_face["image_uris"]["border_crop"])
            else:
                raise ValueError(f"\033[31m[!]\033[0m No hay imagen para {self.cardMainName} / {self.scryfall_url}")            
            
            for i, url in enumerate(img_urls):
                img = requests.get(url).content
                for q in range(self.quantity):
                    filepath = os.path.join(folder_path, crear_directorio_nuevo(f"{self.cardTypes[i]}_{self.cardID}_{q}.jpg"))    
                    open(filepath, "wb").write(img)
                    print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")
                    
        except Exception as e:
            print(f"\033[31m[!]\033[0m Error bajando la imagen de {self.cardMainName}\n{e}")
            N_ERROR_DOWNLOADS += 1
            NAMES_ERROR_DOWNLOADS.append(self.cardMainName)
    
    def __str__(self):
        return f"{self.cardMainName} ({self.quantity}) -> {self.scryfall_url}"
 
def crear_directorio_nuevo(name: str) -> str:
    # Reemplaza caracteres no admitidos
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    return name
    
def borrar_ultimas_lineas(num_lineas:int):
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

def getJson_api_data(platform:str, deck_id:str):
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
# Carga las cartas del mazo según la plataforma
# ------------------------------------------------------------
def load_deck(platform:str, deck_id:str, prnt_tokens:bool) -> list[CardClass]:
    cards = []
    
    # -------- ARCHIDEKT --------
    if platform == "archidekt":
        data = getJson_api_data(platform, deck_id)     
        
        #Skip a la maybe board y los tokens           
        skipTypes = ["Maybeboard"]
        if not prnt_tokens:
            skipTypes.append("Tokens & Extras")
        
        for c in data["cards"]:      
            cardType = c["categories"][0]
            
            if cardType in skipTypes:
                continue
            
            cardID = c["card"]["id"]
            multiverseID = c["card"]["multiverseid"]
            editionCode = c["card"]["edition"]["editioncode"]
            collectorNumber = c["card"]["collectorNumber"]
            
            #Si es un token, que solo imprima 1
            quantity = c["quantity"] if cardType != "Tokens & Extras" else 1
            
            url = ""                
            #https://api.scryfall.com/cards/multiverse/<multiverseID>
            if(multiverseID != 0):
                url = f"https://api.scryfall.com/cards/multiverse/{multiverseID}"
            
            #https://api.scryfall.com/cards/<editionCode>/<collectorNumber>
            else:
                url = f"https://api.scryfall.com/cards/{editionCode}/{collectorNumber}"
                
            card = CardClass(cardID, quantity, url)
            cards.append(card)
        
        return cards

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
            
            cardID = card_data["uniqueCardId"] if "uniqueCardId" in card_data else 0
            scryfallID = card_data["scryfall_id"] 
            
            quantity = value["quantity"] if "quantity" in value else 1

            card = CardClass(cardID, quantity, f"https://api.scryfall.com/cards/{scryfallID}")    
            cards.append(card)
        
        return cards

    else:
        raise ValueError(f"\033[31m[!] Plataforma no soportada: \033[0m'{platform}'")

# ------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------
def main():
    global OUTPUT_DIR, ERROR_DOWNLOADS
    ERROR_DOWNLOADS = 0
    
    print(f"\033[33m======= DESCARGAR CARTAS MAGIC THE GATHERING =======")
    print(f"\033[0m- Plataformas admitidas: [ Archidekt, Moxfield ]\n")
    
    url = input("Pega la URL del mazo: \033[36m").strip()
    try:
        platform, deck_id = get_platform_and_id(url)
        deckName = getJson_api_data(platform, deck_id)["name"]
    except Exception as e:
        print(e)
        return
    
    #Muestra los datos obtenidos
    borrar_ultimas_lineas(0)
    print(f"\033[33m-- {deckName} --")
    print(f"\033[33mPlataforma: \033[0m{platform.capitalize()}")
    print(f"\033[33mID del mazo: \033[0m'{deck_id}'")
    
    #Pregunta para imprimir los tokens
    prnt_tokens = yesNo_CustomChoice("¿Quieres imprimir tambien los tokens?", "si", "no")
    borrar_ultimas_lineas(0)
    print(f"\033[33mImprimir tokens: \033[0m'{'Si' if prnt_tokens else 'No'}'\n")
    
    #Carga las cartas en una lista
    cards = load_deck(platform, deck_id, prnt_tokens)
    
    #Como cada carta puede repetirse, esto imprime la longitud apropiada
    amnt = 0
    for c in cards:
        amnt += c.quantity 
    print(f"\nSe encontraron \033[36m{amnt}\033[0m cartas.")

    #Crea una carpeta donde se descargaran las cartas
    customFolderName = crear_directorio_nuevo(input("Quieres poner algun nombre a la carpeta de descarga? (Enter para no): "))
    OUTPUT_DIR = os.path.join("cartas", customFolderName if customFolderName != "" else crear_directorio_nuevo(deckName))
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    print("")
    
    #Descarga las cartas una por una
    for c in cards:
        c.downloadImages(OUTPUT_DIR)

    print(f"\n\033[32mListo, mi rey. Todas las cartas estan en la carpeta '{OUTPUT_DIR}'\033[0m")
    if(ERROR_DOWNLOADS > 0):
        print(f"\033[33m[!] No se pudieron descargar {ERROR_DOWNLOADS} cartas, te toca descargalas manualmente :(\033[0m")
    
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


