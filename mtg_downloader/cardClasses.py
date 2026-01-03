from enum import Enum
import sys
from PIL import Image
import os
import requests
from urllib.request import urlopen

#Añade el directorio de arriba en el path para usar scripts fuera de la carpeta
sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[0:-2]))
from basicFunctions import *

class CardType(Enum):
    CREATURE = 0
    ARTIFACT = 1
    ENCHANTMENT = 2
    INSTANT = 3
    SORCERY = 4
    BATTLE = 5
    PLANESWALKER = 6
    LAND = 7
    TOKEN = 8
    OTHER = 99
    
    def __str__(self) -> str:
        return self.name.capitalize()
        

class CardClass:
    def __init__(self, quantity:int, scryfall_url:str):    
        #Pide el JSON de scryfall al crear la carta
        self.jsonData = requests.get(scryfall_url).json()
        
        #La carta tiene otra carta en la parte de atras
        self.doubleCard = True
        self.cardTypeText = []
        
        # Carta con otra carta por atras
        if "card_faces" in self.jsonData:
            name1 = str(self.jsonData["card_faces"][0]["name"])
            name2 = str(self.jsonData["card_faces"][1]["name"])
            #misma carta por ambas caras, diferente arte
            if name1 == name2:
                self.cardMainName = name1
                self.cardTypeText.append(self.jsonData["card_faces"][0]["type_line"])
            
            # dos cartas diferentes
            else:
                self.cardMainName = self.jsonData["name"]
                self.cardTypeText += self.jsonData["type_line"].split("//")
        
        # Cartas unicas
        elif "type_line" in self.jsonData:
            self.cardTypeText.append(self.jsonData["type_line"])
            self.cardMainName = self.jsonData["name"]
            self.doubleCard = False
              
        # Divide el nombre de la carta si contiene un "//"
        self.cardMainName = str(self.cardMainName).strip()
        self.cardNames = [n.strip() for n in self.cardMainName.split("//")] #Limpia los espacios del principio y fin de cada elemento de la lista

        #Le da el tipo con un Enum
        self.cardTypes = self.set_cardType()
        
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.img_urls = []
        
        if "image_uris" in self.jsonData:
            self.img_urls.append(self.jsonData["image_uris"]["border_crop"])
        elif "card_faces" in self.jsonData:
            for card_face in self.jsonData["card_faces"]:
                self.img_urls.append(card_face["image_uris"]["border_crop"])
        else:
            raise ValueError(f"No hay imagen para {self.cardMainName} / {self.scryfall_url}") 
        
        print(f"\033[33m[+]\033[0m Datos cargados: ", end="")
        if len(self.cardNames) == 1:
            print(f"{self.cardNames[0]} \033[33m({self.cardTypes[0]})\033[0m")
        else:
            for i in range(len(self.cardNames)):
                print(f"{self.cardNames[i]} \033[33m({self.cardTypes[i]})\033[0m", end="")
                if(i < len(self.cardNames) - 1):
                    print(" // ", end="")
            print("")
            
    def showImage(self) -> list:
        imgs = []
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            imgs.append(Image.open(urlopen(url)))
        return imgs
            
    def downloadImages(self, folder_path:str):        
        for i in range(len(self.cardNames)):
            url = self.img_urls[i]
            img = requests.get(url).content
            
            for q in range(self.quantity):
                filepath = os.path.join(folder_path, crear_directorio_nuevo(f"{self.cardTypeText[i].lower()}_{self.cardNames[i].lower()}_{q}.jpg"))    
                open(filepath, "wb").write(img)
                print(f"\033[32m[Y]\033[0m Imagen descargada: {filepath}")
                    
    
    def set_cardType(self) -> list[CardType]:
        allTypes = []
        for t in self.cardTypeText:
            t = t.lower()
            if "token" in t:
                allTypes.append(CardType.TOKEN)
            elif "creature" in t:
                allTypes.append(CardType.CREATURE)
            elif "artifact" in t:
                allTypes.append(CardType.ARTIFACT)
            elif "enchantment" in t:
                allTypes.append(CardType.ENCHANTMENT)
            elif "land" in t:
                allTypes.append(CardType.LAND)
            elif "instant" in t:
                allTypes.append(CardType.INSTANT)
            elif "sorcery" in t:
                allTypes.append(CardType.SORCERY)
            elif "battle" in t:
                allTypes.append(CardType.BATTLE)
            elif "planeswalker" in t:
                allTypes.append(CardType.PLANESWALKER)
            else:
                allTypes.append(CardType.OTHER)
        
        return allTypes    
        
    def __str__(self):
        return f"{self.cardMainName} ({self.quantity}) -> {self.scryfall_url}"
