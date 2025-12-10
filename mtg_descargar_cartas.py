import requests
import re
import os
import time
import imprimir_cartas as modulo_imprimir

OUTPUT_DIR = ""

class CardClass:
    def __init__(self, cardName:str, cardID:int, cardType:str, quantity:int, scryfall_url:str):
        self.cardName = cardName
        self.cardID = str(cardID)
        self.cardType = cardType.lower().replace(" ","")
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        
    def downloadImages(self, folder_path:str):
        try:
            #Pide el JSON de scryfall
            data = requests.get(self.scryfall_url).json()
            
            img_url = ""
            if "image_uris" in data:
                img_url = data["image_uris"]["border_crop"]
            elif "card_faces" in data:
                img_url = data["card_faces"][0]["image_uris"]["border_crop"]
            else:
                print(f"[!] No hay imagen para {self.scryfall_url}")     
            
            img = requests.get(img_url).content
            for i in range(self.quantity):
                index = i
                filepath = os.path.join(folder_path, f"{self.cardType}_{self.cardID}_{index}.jpg")    
                open(filepath, "wb").write(img)
                print(f"✔ Imagen descargada: {filepath}")
        except Exception as e:
            print(f"[!] Error bajando la imagen de {self.cardName}\n{e}")
    
    def __str__(self):
        return f"{self.cardName} ({self.quantity}) -> {self.scryfall_url}"

def yesNo_CustomChoice(text:str, trueOption:str, falseOption:str) -> bool:
    value = False
    while True:
        __inp = input(f"{text} [{trueOption}/{falseOption}]: ").lower()
        if __inp in [trueOption, falseOption]:
            value = __inp == trueOption
            break
        else:
            modulo_imprimir.borrar_ultimas_lineas(0)
            print(f"[Error: Opción no válida: {__inp}] ", end="")
    return value

# ------------------------------------------------------------
# Detecta plataforma e ID del mazo
# ------------------------------------------------------------
def get_platform_and_id(url):
    if "archidekt" in url.lower():
        match = re.search(r"decks/(\d+)", url)
        if not match:
            raise ValueError("No pude sacar el ID de Archidekt.")
        return "archidekt", match.group(1)

    if "moxfield" in url.lower():
        deck_id = url.rstrip("/").split("/")[-1]
        return "moxfield", deck_id

    raise ValueError("URL no es Archidekt ni Moxfield.")


# ------------------------------------------------------------
# Carga las cartas del mazo según la plataforma
# ------------------------------------------------------------
def load_deck(platform, deck_id) -> list[CardClass]:
    cards = []
    
    if platform == "archidekt":
        api_url = f"https://archidekt.com/api/decks/{deck_id}/"
        data = requests.get(api_url).json()
        
        for c in data["cards"]:      
            cardType = c["categories"][0]
            #Skip a la maybe board y los tokens
            if cardType in ["Maybeboard", "Tokens & Extras"]:
                continue
            
            cardID = c["card"]["id"]
            quantity = c["quantity"]
            multiverseID = c["card"]["multiverseid"]
            editionCode = c["card"]["edition"]["editioncode"]
            collectorNumber = c["card"]["collectorNumber"]
            cardName = c["card"]["oracleCard"]["name"]
            
            url = ""                
            #https://api.scryfall.com/cards/multiverse/<multiverseID>
            if(multiverseID != 0):
                url = f"https://api.scryfall.com/cards/multiverse/{multiverseID}"
            
            #https://api.scryfall.com/cards/<editionCode>/<collectorNumber>
            else:
                url = f"https://api.scryfall.com/cards/{editionCode}/{collectorNumber}"
                
            cardClass = CardClass(cardName, cardID, cardType, quantity, url)
            cards.append(cardClass)
        
        return cards

    elif platform == "moxfield":
        api_url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"
        data = requests.get(api_url).json()
        cards = []

        for section in ["mainboard", "sideboard"]:
            for name, info in data[section].items():
                cards.append([name] * info["quantity"])

        return cards

    else:
        raise ValueError("Plataforma no soportada.")

# ------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------
def main():
    global OUTPUT_DIR
    
    url = input("Pega la URL del mazo (Archidekt o Moxfield): ").strip()

    platform, deck_id = get_platform_and_id(url)
    print(f"Detecté plataforma: {platform}, ID: {deck_id}")

    print("Cargando cartas del mazo...")
    cards = load_deck(platform, deck_id)
    
    #Como cada carta puede repetirse, esto imprime la longitud apropiada
    amnt = 0
    for c in cards:
        amnt += c.quantity 
    print(f"Se encontraron {amnt} cartas.")

    OUTPUT_DIR = os.path.join("cartas", input("Quieres poner algun nombre a la carpeta de descarga? (Enter para no): "))
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    
    for c in cards:
        c.downloadImages(OUTPUT_DIR)

    print(f"\nListo, mi rey. Todas las cartas estan en la carpeta '{OUTPUT_DIR}'")
    
    # Configuracion de impresion
    imprimir_ahora = yesNo_CustomChoice("¿Quieres crear el PDF de las cartas?", "si", "no")

    if(imprimir_ahora):
        modulo_imprimir.main(OUTPUT_DIR, 1)

if __name__ == "__main__":
    os.system("cls")
    main()

