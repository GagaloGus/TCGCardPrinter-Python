import os
import requests
from PIL import Image
from datetime import datetime

os.system("cls")

# --- CONFIGURACIÓN ---
# Carpeta base con fecha y hora
fecha_hora = datetime.now().strftime("%H-%M_%d-%m-%Y")
IMAGES_DIR = os.path.join("cartas", fecha_hora)
os.makedirs(IMAGES_DIR, exist_ok=True)

def descargar_carta(nombre):
    
    # Busca la carta en la API usando nombre en inglés o español
    # Devuelve la URL de la imagen principal

    try:
        r = requests.get(f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={nombre}")
        r.raise_for_status()
        data = r.json()["data"][0]
        # Tomamos la imagen original
        img_url = data["card_images"][0]["image_url"]
        # Nombre en español si existe
        nombre_es = data.get("name", nombre)
        return img_url, nombre_es
    except Exception as e:
        print(f"No se encontró la carta '{nombre}': {e}")
        return None, None

def guardar_imagen(url, nombre, copia_num):
    fname = os.path.join(IMAGES_DIR, f"{nombre}_{copia_num}.jpg")
    if not os.path.exists(fname):
        img_data = requests.get(url).content
        with open(fname, "wb") as f:
            f.write(img_data)

# --- BUCLE PRINCIPAL ---
cartas = {}
while True:
    nombre = input("Nombre de la carta (Enter para terminar): ").strip()
    if not nombre:
        break

    while True:
        try:
            copias = int(input(f"Cuántas copias de '{nombre}' quieres?: "))
            if copias > 0:
                break
        except:
            pass
        print("Número inválido, intenta de nuevo.")

    img_url, nombre_es = descargar_carta(nombre)
    if not img_url:
        continue

    for i in range(1, copias + 1):
        guardar_imagen(img_url, nombre_es, i)

    print(f"{copias} copias de '{nombre_es}' descargadas.\n")
