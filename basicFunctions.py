import re
import sys

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

def multiple_CustomChoice(text:str, options:list[str], results:list[str] = []) -> int:
    if not results:
        results = options.copy()
    
    while True:
        print(f"\033[33m{text}\033[0m")
        for i, opt in enumerate(options):
            print(f"  {i}-> {opt}")
        print("\033[36m", end="")
        __inp = input()
        
        choice = int(__inp) if __inp.isdigit() else 0

        # Verificacion
        if choice in list(range(0, len(options))):
            break
        else:
            borrar_ultimas_lineas(len(options)+1) 
            print(f"\033[31m[Error: Opción no válida: {choice}] \033[0m", end="")

            
    # Mostrar las dimensiones seleccionadas
    borrar_ultimas_lineas(0)
    print(f"\033[33m{choice}-> {results[choice]}")
    return choice