import asyncio
import edge_tts
import winsound
import time
import sounddevice as sd
import numpy as np
import os

def check_interruption():
    print("Iniciando monitoramento de interrupcao...")
    threshold = 5.0  # Volume threshold
    interrupted = False
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal interrupted
        volume_norm = np.linalg.norm(indata) * 10
        if volume_norm > threshold and not interrupted:
            print(f"\n[!] Pico de som detectado (Volume: {volume_norm:.1f}). Interrompendo a fala!")
            winsound.PlaySound(None, winsound.SND_PURGE)
            interrupted = True
            raise sd.CallbackStop()

    # Inicia a escuta em background do mic padrao
    with sd.InputStream(callback=audio_callback):
        while not interrupted:
            time.sleep(0.1)

async def test_barge_in():
    text = "Olá! Eu sou a Willow. Estou falando uma frase bem longa para você tentar me interromper. Chegue perto do microfone e fale qualquer coisa em voz alta para eu calar a boca!"
    communicate = edge_tts.Communicate(text, "pt-BR-AntonioNeural", rate="+0%")
    temp_file = "test_barge_in.wav"
    await communicate.save(temp_file)
    
    print("Tocando o audio...")
    winsound.PlaySound(temp_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
    
    # Inicia a verificacao do microfone
    check_interruption()
    
    print("Teste concluido.")
    time.sleep(1)
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == "__main__":
    asyncio.run(test_barge_in())
