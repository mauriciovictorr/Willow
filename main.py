"""
Willow — Assistente Virtual Inteligente por Voz
===================================================
Ponto de entrada principal da aplicação.

Uso:
    python main.py
"""

import logging
from src.core.audio_engine import AudioEngine
from src.core.brain import Brain

# Configurar logs para não poluir o terminal
logging.basicConfig(level=logging.WARNING)

def run_willow():
    print("Iniciando a Willow...")
    
    # 1. Inicializar modulos
    print("-> Ligando motor de audio...")
    audio = AudioEngine()
    
    print("-> Conectando ao cerebro (Ollama/phi3)...")
    brain = Brain(model="phi3")
    
    print("\n[Willow está pronta! Pode falar.]\n")
    audio.speak("Olá! Sou o Willow. Como posso te ajudar hoje?")
    
    # 2. Loop principal
    while True:
        try:
            print("\n(Escutando...)")
            user_text = audio.listen()
            
            if user_text:
                print(f"[Você]: {user_text}")
                
                # Check for exit command
                if user_text.lower() in ["tchau", "desligar", "encerrar", "sair"]:
                    print("\n[Willow]: Desligando. Ate logo!")
                    audio.speak("Desligando. Até logo!")
                    break
                    
                # Think and speak
                print("(Pensando...)")
                response = brain.think(user_text)
                
                if response:
                    print(f"[Willow]: {response}")
                    audio.speak(response)
                    
        except KeyboardInterrupt:
            print("\n[Willow]: Desligamento forcado (Ctrl+C).")
            break
        except Exception as e:
            print(f"\n[Erro]: {e}")

if __name__ == "__main__":
    run_willow()
