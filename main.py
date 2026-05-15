"""
Willow — Assistente Virtual Inteligente por Voz
===================================================
Ponto de entrada principal da aplicacao.

Uso:
    python main.py
"""

import logging
import os

from dotenv import load_dotenv

from src.core.audio_engine import AudioEngine
from src.core.brain import Brain

# Carregar variaveis de ambiente do .env
load_dotenv()

# Configurar logging a partir do .env (padrao: WARNING)
log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("willow.main")


def run_willow() -> None:
    """Loop principal da assistente Willow."""
    print("Iniciando a Willow...")

    # 1. Inicializar modulos
    mic_index = int(os.getenv("MICROPHONE_INDEX", "-1"))
    language = os.getenv("WILLOW_LANGUAGE", "pt-BR")

    print("-> Ligando motor de audio...")
    audio = AudioEngine(mic_index=mic_index, language=language)

    print("-> Conectando ao cerebro (Ollama/phi3)...")
    brain = Brain(model="phi3")

    print("\n[Willow esta pronta! Pode falar.]\n")
    audio.speak("Ola! Sou a Willow. Como posso te ajudar hoje?")

    # 2. Loop principal
    while True:
        try:
            print("\n(Escutando...)")
            user_text = audio.listen()

            if user_text:
                print(f"[Voce]: {user_text}")

                # Verificar comando de saida
                if user_text.lower() in ["tchau", "desligar", "encerrar", "sair"]:
                    print("\n[Willow]: Desligando. Ate logo!")
                    audio.speak("Desligando. Ate logo!")
                    break

                # Pensar e responder
                print("(Pensando...)")
                response = brain.think(user_text)

                if response:
                    print(f"[Willow]: {response}")
                    audio.speak(response)

        except KeyboardInterrupt:
            print("\n[Willow]: Desligamento forcado (Ctrl+C).")
            break
        except Exception as e:
            logger.error("Erro no loop principal: %s", e)
            print(f"\n[Erro]: {e}")

    # Cleanup e feito automaticamente pelo atexit registrado no AudioEngine


if __name__ == "__main__":
    run_willow()
