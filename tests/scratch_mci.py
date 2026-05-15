import asyncio
import edge_tts
import time
import ctypes
import os

async def test_mci():
    print("Gerando MP3...")
    communicate = edge_tts.Communicate("Olá, este é um teste usando o Media Control Interface do Windows.", "pt-BR-AntonioNeural")
    temp_file = os.path.abspath("test_mci.mp3")
    await communicate.save(temp_file)
    
    print("Tocando MP3 via MCI...")
    # MCI commands need to handle paths correctly, quotes are important
    open_cmd = f'open "{temp_file}" type mpegvideo alias willow_voice'
    ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, None)
    ctypes.windll.winmm.mciSendStringW("play willow_voice", None, 0, None)
    
    print("Tocando... Vou cortar em 2 segundos.")
    time.sleep(2)
    
    print("Cortando!")
    ctypes.windll.winmm.mciSendStringW("stop willow_voice", None, 0, None)
    ctypes.windll.winmm.mciSendStringW("close willow_voice", None, 0, None)
    print("Audio parado.")

if __name__ == "__main__":
    asyncio.run(test_mci())
