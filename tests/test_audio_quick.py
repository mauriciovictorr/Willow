"""Teste rapido: verifica se o AudioEngine carrega e detecta microfones."""

from src.core.audio_engine import AudioEngine


def main():
    print("=== Teste: Listagem de Microfones ===")
    mics = AudioEngine.list_microphones()
    print(f"Microfones encontrados: {len(mics)}")
    for mic in mics:
        print(f"  [{mic['index']}] {mic['name']}")

    print("\n=== Teste: Dispositivos de Audio ===")
    AudioEngine.list_audio_devices()

    print("\n=== Teste: Inicializar AudioEngine ===")
    engine = AudioEngine()
    print("AudioEngine inicializado com sucesso!")

    print("\n=== Teste: TTS (Text-to-Speech) ===")
    engine.speak("Ola! Eu sou a Willow. Prazer em conhecer voce!")
    print("TTS concluido.")


if __name__ == "__main__":
    main()
