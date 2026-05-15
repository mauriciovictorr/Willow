import asyncio
import edge_tts
import winsound
import time
import os

async def test_winsound():
    print("Gerando WAV...")
    voice = "pt-BR-AntonioNeural"
    text = "Olá, estou testando o áudio em formato WAV nativo do Windows para permitir interrupções."
    communicate = edge_tts.Communicate(text, voice, rate="+0%")
    
    # Needs to be a valid WAV format supported by winsound
    # Edge-TTS supports riff-24khz-16bit-mono-pcm
    output_format = "riff-24khz-16bit-mono-pcm"
    
    temp_file = "test_winsound.wav"
    await communicate.save(temp_file)
    
    print("Tocando o audio de forma assincrona (nao bloqueante)...")
    winsound.PlaySound(temp_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
    
    print("Esperando 2 segundos e depois cortando o audio (interrupcao)...")
    time.sleep(2)
    winsound.PlaySound(None, winsound.SND_PURGE) # Interrompe
    print("Audio interrompido!")
    
    time.sleep(1)
    os.remove(temp_file)

if __name__ == "__main__":
    asyncio.run(test_winsound())
