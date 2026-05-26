#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para validar descarga de mazo desde Moxfield
URL esperada: https://moxfield.com/decks/0bPV5UuYzkufFWJ00KWC1g
Resultado esperado: 1 commander + 99 mainboard + 10 tokens = 110 cartas total
"""

import sys
import os
from mtg_downloader.cardClasses import CardScraper, CardType
import mtg_downloader.mtg_descargar_cartas as mtg

def test_moxfield_deck():
    url = "https://moxfield.com/decks/0bPV5UuYzkufFWJ00KWC1g"
    
    print("\033[33m" + "="*60 + "\033[0m")
    print("\033[33m TEST DE DESCARGA - MOXFIELD \033[0m")
    print("\033[33m" + "="*60 + "\033[0m\n")
    
    try:
        # 1. Detectar plataforma e ID
        print("\033[36m[1] Detectando plataforma e ID...\033[0m")
        platform, deck_id = mtg.get_platform_and_id(url)
        print(f"✓ Plataforma: {platform}")
        print(f"✓ ID del mazo: {deck_id}\n")
        
        # 2. Obtener JSON del mazo
        print("\033[36m[2] Obteniendo datos del mazo...\033[0m")
        data = mtg.get_json(platform, deck_id)
        deck_name = data.get("name", "Sin nombre")
        print(f"✓ Nombre del mazo: {deck_name}\n")
        
        # 3. Contar cartas sin procesar
        print("\033[36m[3] Contando cartas (sin procesar)...\033[0m")
        
        # Contar mainboard
        mainboard_count = 0
        if "mainboard" in data:
            mainboard_count = len(data["mainboard"])
        print(f"  - Mainboard: {mainboard_count}")
        
        # Contar commanders
        commander_count = 0
        if "commanders" in data:
            commander_count = len(data["commanders"])
        print(f"  - Commanders: {commander_count}")
        
        # Contar tokens
        token_count = 0
        if "tokens" in data:
            token_count = len([t for t in data["tokens"] if t.get("layout") in ["token", "emblem"]])
        print(f"  - Tokens/Emblemas: {token_count}\n")
        
        # 4. Obtener longitud total (con y sin tokens)
        print("\033[36m[4] Longitud total del mazo...\033[0m")
        length_with_tokens = mtg.get_download_length(platform, deck_id, True)
        length_without_tokens = mtg.get_download_length(platform, deck_id, False)
        print(f"  - Con tokens: {length_with_tokens}")
        print(f"  - Sin tokens: {length_without_tokens}\n")
        
        # 5. Cargar mazo completo
        print("\033[36m[5] Cargando todas las cartas del mazo (idioma original)...\033[0m")
        cards = mtg.load_deck(platform, deck_id, True, "orig")
        
        print(f"\n✓ Total de cartas cargadas: {len(cards)}\n")
        
        # 6. Clasificar por tipo
        print("\033[36m[6] Clasificación por tipo...\033[0m")
        
        type_count = {}
        for card in cards:
            card_type = card.cardTypes[0]
            if card_type not in type_count:
                type_count[card_type] = 0
            type_count[card_type] += 1
        
        for card_type in sorted(type_count.keys(), key=lambda x: x.value):
            print(f"  - {card_type.__str__('orig')}: {type_count[card_type]}")
        
        # 7. Validación de resultados
        print("\n" + "\033[33m" + "="*60 + "\033[0m")
        print("\033[33m VALIDACIÓN DE RESULTADOS \033[0m")
        print("\033[33m" + "="*60 + "\033[0m\n")
        
        # Contar commanders en las cartas cargadas
        commander_cards = sum(1 for c in cards if CardType.COMMANDER in c.cardTypes)
        token_cards = sum(1 for c in cards if CardType.TOKEN in c.cardTypes)
        other_cards = len(cards) - commander_cards - token_cards
        
        print(f"Commanders:  {commander_cards} (esperado: 1)")
        print(f"Mainboard:   {other_cards} (esperado: 99)")
        print(f"Tokens:      {token_cards} (esperado: 10)")
        print(f"Total:       {len(cards)} (esperado: 110)")
        
        # Validar
        success = (commander_cards == 1 and other_cards == 99 and token_cards == 10 and len(cards) == 110)
        
        if success:
            print("\n\033[32m✓ ¡PRUEBA EXITOSA! Los números coinciden.\033[0m")
        else:
            print("\n\033[31m✗ ¡PRUEBA FALLIDA! Los números no coinciden.\033[0m")
            print("  Diferencias:")
            if commander_cards != 1:
                print(f"    - Commanders: esperado 1, obtenido {commander_cards}")
            if other_cards != 99:
                print(f"    - Mainboard: esperado 99, obtenido {other_cards}")
            if token_cards != 10:
                print(f"    - Tokens: esperado 10, obtenido {token_cards}")
        
        return success
        
    except Exception as e:
        print(f"\n\033[31m✗ ERROR: {e}\033[0m")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_moxfield_deck()
    sys.exit(0 if success else 1)
