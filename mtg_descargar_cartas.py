import sys
from enum import Enum
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
import requests
import re
import os
import cloudscraper
import subprocess

OUTPUT_DIR = ""
DOWNLOAD_LEN = 0
N_ERROR_LOAD = 0
N_ERROR_DOWNLOADS = 0
    
class CardType(Enum):
    CREATURE = 0
    ARTIFACT = 1
    ENCHANTMENT = 2
    INSTANT = 3
    SORCERY = 4
    PLANESWALKER = 5
    LAND = 6
    TOKEN = 7
    OTHER = 99
    
    def __str__(self) -> str:
        return self.name.capitalize()
        

class CardClass:
    def __init__(self, quantity:int, scryfall_url:str):    
        #Pide el JSON de scryfall al crear la carta
        self.jsonData = requests.get(scryfall_url).json()
        
        #La carta tiene otra carta en la parte de atras
        self.doubleCard = True
        
        # Cartas unicas o con parte de atras
        if "type_line" in self.jsonData:
            self.cardTypeText = list[str](self.jsonData["type_line"].split("//"))
            self.cardMainName = self.jsonData["name"]
            if len(self.cardTypeText) == 1:
                self.doubleCard = False
            
        # Misma carta con diferente arte por las dos caras
        elif "card_faces" in self.jsonData:
            self.cardTypeText = list[str](self.jsonData["card_faces"][0]["type_line"].split("//"))
            self.cardMainName = self.jsonData["card_faces"][0]["name"]
        
        self.cardMainName = str(self.cardMainName).strip()
        self.cardNames = [n.strip() for n in self.cardMainName.split("//")] #Limpia los espacios del principio y fin de cada elemento de la lista

        self.cardTypes = self.set_cardType()
        
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        #({' '.join(map(str, self.cardType))})
        print(f"\033[33m[+]\033[0m Datos cargados: ", end="")
        if len(self.cardNames) == 1:
            print(f"{self.cardNames[0]} \033[33m({self.cardTypes[0]})\033[0m")
        else:
            for i in range(len(self.cardNames)):
                print(f"{self.cardNames[i]} \033[33m({self.cardTypes[i]})\033[0m", end="")
                if(i < len(self.cardNames) - 1):
                    print(" // ", end="")
            print("")
          
    def downloadImages(self, folder_path:str):
        global N_ERROR_DOWNLOADS
        try:   
            img_urls = []
            
            if "image_uris" in self.jsonData:
                img_urls.append(self.jsonData["image_uris"]["border_crop"])
            elif "card_faces" in self.jsonData:
                for card_face in self.jsonData["card_faces"]:
                    img_urls.append(card_face["image_uris"]["border_crop"])
            else:
                raise ValueError(f"No hay imagen para {self.cardMainName} / {self.scryfall_url}")            
            
            for i in range(len(self.cardNames)):
                url = img_urls[i]
                img = requests.get(url).content
                
                for q in range(self.quantity):
                    filepath = os.path.join(folder_path, crear_directorio_nuevo(f"{self.cardTypeText[i].lower()}_{self.cardNames[i].lower()}_{q}.jpg"))    
                    open(filepath, "wb").write(img)
                    print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")
                    
        except Exception as e:
            print(f"\033[31m[!]\033[0m Error bajando la imagen de {self.cardMainName} //  \033[0m{e}")
            N_ERROR_DOWNLOADS += 1
    
    def set_cardType(self) -> list[CardType]:
        allTypes = []
        
        for type in self.cardTypeText:
            type = type.lower()
            if "token" in type:
                allTypes.append(CardType.TOKEN)
            elif "creature" in type:
                allTypes.append(CardType.CREATURE)
            elif "artifact" in type:
                allTypes.append(CardType.ARTIFACT)
            elif "enchantment" in type:
                allTypes.append(CardType.ENCHANTMENT)
            elif "land" in type:
                allTypes.append(CardType.LAND)
            elif "instant" in type:
                allTypes.append(CardType.INSTANT)
            elif "sorcery" in type:
                allTypes.append(CardType.SORCERY)
            elif "planeswalker" in type:
                allTypes.append(CardType.PLANESWALKER)
            else:
                allTypes.append(CardType.OTHER)
        
        return allTypes    
        
    def __str__(self):
        return f"{self.cardMainName} ({self.quantity}) -> {self.scryfall_url}"

def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

 
def crear_directorio_nuevo(name: str) -> str:
    # Reemplaza caracteres no admitidos
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    return name
    
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
# Devuelve los datos de la API del mazo
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
        print("balls")
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
# Carga las cartas del mazo según la plataforma
# ------------------------------------------------------------
def load_deck(platform:str, deck_id:str, prnt_tokens:bool) -> list[CardClass]:
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
                
                multiverseID = c["card"]["multiverseid"]
                editionCode = c["card"]["edition"]["editioncode"]
                collectorNumber = c["card"]["collectorNumber"]
                cardName = c["card"]["oracleCard"]["name"]

                #Si es un token, que solo imprima 1
                quantity = c["quantity"] if "Token" not in cardTypes else 1

                url = ""                
                #https://api.scryfall.com/cards/multiverse/<multiverseID>
                if(multiverseID != 0):
                    url = f"https://api.scryfall.com/cards/multiverse/{multiverseID}"

                #https://api.scryfall.com/cards/<editionCode>/<collectorNumber>
                else:
                    url = f"https://api.scryfall.com/cards/{editionCode}/{collectorNumber}"

                p.update(task, advance=1)   
                try:             
                    card = CardClass(quantity, url)
                    cards.append(card)
                except Exception as e:
                    raise Exception(f"\033[31m[!]\033[0m Error bajando la imagen de {cardName}  //  \033[0m{e}")
                    N_ERROR_LOAD+=1

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
                    card = CardClass(quantity, f"https://api.scryfall.com/cards/{scryfallID}")    
                    cards.append(card)
                except Exception as e:
                    print(f"\033[31m[!]\033[0m Error bajando la imagen de {cardName}  //  \033[0m{e}")
                    N_ERROR_LOAD+=1     

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
        return
    
    #Muestra los datos obtenidos
    borrar_ultimas_lineas(0)
    print(f"\033[33m-- {deckName} --")
    print(f"\033[33mPlataforma: \033[0m{platform.capitalize()}")
    print(f"\033[33mID del mazo: \033[0m'{deck_id}'")
    
    #Pregunta para imprimir los tokens
    prnt_tokens = yesNo_CustomChoice("¿Quieres imprimir tambien los tokens?", "si", "no")
    borrar_ultimas_lineas(0)
    print(f"\033[33mImprimir tokens: \033[0m'{'Si' if prnt_tokens else 'No'}'")
    
    #Obtiene la longitud del mazo
    print("\nObteniendo longitud del mazo...")
    DOWNLOAD_LEN = get_download_lenght(platform, deck_id, prnt_tokens)
    borrar_ultimas_lineas(0)
    
    #Carga las cartas en una lista
    cards = load_deck(platform, deck_id, prnt_tokens)
    
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
            c.downloadImages(OUTPUT_DIR)

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


