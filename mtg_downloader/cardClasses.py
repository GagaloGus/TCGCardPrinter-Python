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
    ARTIFACT = 0
    BATTLE = 1
    CONSPIRACY = 2
    CREATURE = 3
    DUNGEON = 4
    EMBLEM = 5
    ENCHANTMENT = 6
    HERO = 7
    INSTANT = 8
    KINDRED = 9
    LAND = 10
    PHENOMENON = 11
    PLANE = 12
    PLANESWALKER = 13
    SCHEME = 14
    SORCERY = 15
    TOKEN = 16
    VANGUARD = 17
    OTHER = 99
    
    def __str__(self, lang:str = "orig") -> str:
        if lang not in ["orig", "en"]:
            dic = {}
            if lang == "es":
                dic = {
                    CardType.ARTIFACT: "Artefacto",
                    CardType.BATTLE: "Batalla",
                    CardType.CONSPIRACY: "Conspiración",
                    CardType.CREATURE: "Criatura",
                    CardType.DUNGEON: "Mazmorra",
                    CardType.EMBLEM: "Emblema",
                    CardType.ENCHANTMENT: "Encantamiento",
                    CardType.HERO: "Héroe",
                    CardType.INSTANT: "Instantánea",
                    CardType.KINDRED: "Afín",
                    CardType.LAND: "Tierra",
                    CardType.PHENOMENON: "Fenómeno",
                    CardType.PLANE: "Plano",
                    CardType.PLANESWALKER: "Planeswalker",
                    CardType.SCHEME: "Intriga",
                    CardType.SORCERY: "Conjuro",
                    CardType.TOKEN: "Ficha",
                    CardType.VANGUARD: "Vanguardia",
                    CardType.OTHER: "Otro",
                }
            #Si pusieron otro idioma no reconocido, pone el original
            else:
                return self.name.capitalize()
            
            # Fallback al "Other", si ese falla tambien, lo imprime en el idioma original
            return dic.get(self, dic.get(CardType.OTHER, "Other"))
        
        #Si no sale ninguno, devuelve en ingles
        return self.name.capitalize()  

class CardClass:
    def __init__(self, quantity:int, scryfall_url:str, lang:str = "orig"):       
        self.quantity = quantity
        self.scryfall_url = scryfall_url
        self.lang = lang
        self.oracle_id = ""
        self.cardMainName = ""
        self.cardNames = []
        self.cardTypeText = []
        self.img_urls = []
        
        #0 = arte unico / 1 = mismo arte por ambas caras / 2 = 2 cartas diferentes
        self.jsonData, self.layout, self.oracle_id = self._fetch_base_json()
        
        if self.lang != "orig":
            self.jsonData, self.altLang, self.layout = self._fetch_altLang_json()    
             
        self._parse_card_data()
        
        #Le da el tipo con un Enum
        self.cardTypes = self.set_cardType()
           
        if "image_uris" in self.jsonData:
            self.img_urls.append(self.jsonData["image_uris"]["border_crop"])
        elif "card_faces" in self.jsonData:
            for card_face in self.jsonData["card_faces"]:
                self.img_urls.append(card_face["image_uris"]["border_crop"])
        else:
            raise ValueError(f"No hay imagen para {self.cardMainName} / {self.scryfall_url}") 
        
        print(f"\033[33m[+]\033[0m Datos cargados: ", end="")
        if len(self.cardNames) == 1:
            print(f"{self.cardNames[0]} \033[33m({self.cardTypes[0].__str__(self.lang)})\033[0m")
        else:
            for i in range(len(self.cardNames)):
                print(f"{self.cardNames[i]} \033[33m({self.cardTypes[i].__str__(self.lang)})\033[0m", end="")
                if(i < len(self.cardNames) - 1):
                    print(" // ", end="")
            print("")
            
    def _parse_card_data(self):
        # Carta con otra carta por atras
        if self.layout != "single":
            name1 = str(self.jsonData["card_faces"][0]["printed_name" if self.altLang else "name"])
            #misma carta por ambas caras, diferente arte
            if self.layout == "reversible":
                self.cardMainName = name1
                self.cardTypeText.append(self.jsonData["card_faces"][0]["type_line"])
            
            # dos cartas diferentes
            else:
                name2 = str(self.jsonData["card_faces"][1]["printed_name" if self.altLang else "name"])
                self.cardMainName = f"{name1} // {name2}"
                self.cardTypeText += self.jsonData["type_line"].split("//") 
        
                # Cartas unicas
        else:
            self.cardTypeText.append(self.jsonData["type_line"])
            self.cardMainName = self.jsonData["printed_name" if self.altLang else "name"]
            
        # Divide el nombre de la carta si contiene un "//"
        self.cardMainName = str(self.cardMainName).strip()
        self.cardNames = [n.strip() for n in self.cardMainName.split("//")] #Limpia los espacios del principio y fin de cada elemento de la lista
    
    def _fetch_base_json(self):
        data = requests.get(self.scryfall_url).json()
        
        layout = self._get_card_layout(data)
        
        if layout == "reversible":
            oracle_id = data["card_faces"][0]["oracle_id"]
        else:
            oracle_id = data["oracle_id"]
        
        return data, layout, oracle_id
    
    def _fetch_altLang_json(self):         
        # -1- Busca en el idioma pedido en el mismo set
        data = requests.get(f"{self.scryfall_url}/{self.lang}").json()
        if data["object"] != "error":
            return data, True, self._get_card_layout(data)
            
        # -2- La busca en otro set en el idioma pedido usando su Oracle_ID
        url = f"https://api.scryfall.com/cards/search?q=oracleid:{self.oracle_id}+lang:{self.lang}"
        data = requests.get(url).json()
        
        if data["object"] == "list" and data["total_cards"] >= 1:
            return data["data"][0], True, self._get_card_layout(data["data"][0])
            
        # -3- Si no hay ninguna version en el idioma pedido, la devuelve en el idioma original
        return self.jsonData, False, self.layout
    
    def _get_card_layout(self, data):            
        # Carta con otra carta por atras
        if "card_faces" in data:
            name1 = str(data["card_faces"][0]["name"])
            name2 = str(data["card_faces"][1]["name"])
            #misma carta por ambas caras, diferente arte
            if name1 == name2:
                return "reversible"
            # dos cartas diferentes
            else:
                return "double"
        # Cartas unicas
        else:
            return "single"       
        
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
        preference = [CardType.TOKEN, CardType.CREATURE]
        for ty in CardType:
            if ty not in preference:
                preference.append(ty)   
        
        for t in self.cardTypeText:
            text_type = t.lower()
            found_type = False
            for ty in preference:
                card_type = ty.name.lower()
                if card_type in text_type:
                    allTypes.append(ty)
                    found_type = True
                    break
            
            if not found_type:
                allTypes.append(CardType.OTHER)
        
        return allTypes    
        
    def __str__(self):
        return f"{self.cardMainName} ({self.quantity}) -> {self.scryfall_url}"
