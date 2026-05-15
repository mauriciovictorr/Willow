"""
Willow -- Audio Engine
======================
Modulo responsavel por captura de voz (Speech-to-Text)
e sintese de fala (Text-to-Speech).

Dependencias:
    - SpeechRecognition (captura e transcricao)
    - pyttsx3 (sintese de voz offline via SAPI5 do Windows)
    - sounddevice (listagem de dispositivos de audio)
"""

import logging
import logging
import os
import sys
import tempfile
import asyncio
import time
import ctypes
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import edge_tts

logger = logging.getLogger("willow.audio")


class AudioEngine:
    """Motor de audio da Willow.

    Responsavel por:
        - Escutar o microfone e transcrever fala em texto.
        - Falar respostas em voz alta usando TTS do Windows.
        - Listar dispositivos de audio disponiveis.
    """

    def __init__(
        self,
        mic_index: int = -1,
        language: str = "pt-BR",
        voice_rate: int = 180,
        listen_timeout: int = 5,
        phrase_time_limit: int = 10,
    ) -> None:
        """Inicializa o motor de audio.

        Args:
            mic_index: Indice do microfone (-1 para autodetectar).
            language: Idioma para reconhecimento de voz.
            voice_rate: Velocidade da fala TTS (palavras por minuto).
            listen_timeout: Segundos esperando o usuario comecar a falar.
            phrase_time_limit: Segundos maximos de captura por frase.
        """
        self.language = language
        self.listen_timeout = listen_timeout
        self.phrase_time_limit = phrase_time_limit

        # --- Speech-to-Text (STT) ---
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True

        # Selecionar microfone
        if mic_index == -1:
            self.microphone = sr.Microphone()
            logger.info("Microfone: autodetectado (padrao do sistema)")
        else:
            self.microphone = sr.Microphone(device_index=mic_index)
            logger.info("Microfone: indice %d", mic_index)

        # Calibrar ruido ambiente
        self._calibrate()

        # --- Text-to-Speech (TTS) ---
        self.tts_voice = "pt-BR-AntonioNeural"
        self.tts_rate = "+0%"
        self.is_speaking = False
        self.barge_in_threshold = 3.5  # Sensibilidade da interrupcao (ajuste se necessario)

        logger.info("AudioEngine inicializado com sucesso (Voz: %s)", self.tts_voice)

    def _calibrate(self) -> None:
        """Calibra o reconhecedor para o ruido ambiente atual."""
        try:
            with self.microphone as source:
                logger.info("Calibrando ruido ambiente (1 segundo)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info(
                    "Calibracao concluida (energy_threshold=%.1f)",
                    self.recognizer.energy_threshold,
                )
        except OSError as e:
            logger.error("Falha ao acessar microfone para calibracao: %s", e)

    async def _async_speak(self, text: str) -> str:
        """Gera e salva o audio do Edge TTS assincronamente em formato MP3."""
        communicate = edge_tts.Communicate(text, self.tts_voice, rate=self.tts_rate)
        
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "willow_speech.mp3")
        
        await communicate.save(temp_file)
        return temp_file

    def listen(self) -> str | None:
        """Escuta o microfone e retorna o texto transcrito.
        Se a Willow estiver falando, monitora interrupcoes.
        """
        # --- Lógica de Interrupção (Barge-in) ---
        if self.is_speaking:
            logger.info("Monitorando interrupcao de fala...")
            interrupted = False
            
            def audio_callback(indata, frames, time_info, status):
                nonlocal interrupted
                volume_norm = np.linalg.norm(indata) * 10
                if volume_norm > self.barge_in_threshold:
                    logger.warning("Interrupcao detectada! (Vol: %.1f)", volume_norm)
                    # Corta o audio usando MCI
                    ctypes.windll.winmm.mciSendStringW("stop willow_voice", None, 0, None)
                    ctypes.windll.winmm.mciSendStringW("close willow_voice", None, 0, None)
                    interrupted = True
                    raise sd.CallbackStop()

            try:
                with sd.InputStream(callback=audio_callback):
                    while self.is_speaking and not interrupted:
                        time.sleep(0.1)
            except Exception as e:
                logger.debug("Erro no stream de interrupcao: %s", e)
            
            self.is_speaking = False
            if interrupted:
                logger.info("Willow silenciada. Escutando novo comando...")
                # Pequena pausa pra não pegar o proprio fim do grito
                time.sleep(0.3)

        # --- Lógica Padrão de Escuta (Google STT) ---
        try:
            with self.microphone as source:
                logger.info("Escutando...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )

            logger.info("Processando audio...")
            text = self.recognizer.recognize_google(audio, language=self.language)
            logger.info("Transcricao: '%s'", text)
            return text

        except sr.WaitTimeoutError:
            logger.debug("Timeout: nenhuma fala detectada em %ds", self.listen_timeout)
            return None

        except sr.UnknownValueError:
            logger.debug("Audio capturado mas nao foi possivel transcrever")
            return None

        except sr.RequestError as e:
            logger.error("Erro na API de reconhecimento de voz: %s", e)
            return None

        except OSError as e:
            logger.error("Erro de hardware no microfone: %s", e)
            return None

    def speak(self, text: str) -> None:
        """Fala o texto de forma assincrona (nao bloqueante) usando MCI."""
        if not text:
            return

        logger.info("Falando: '%s'", text)
        try:
            # Roda o gerador de audio assincrono
            temp_audio_file = asyncio.run(self._async_speak(text))
            
            # Fecha se ja tiver um tocando
            ctypes.windll.winmm.mciSendStringW("close willow_voice", None, 0, None)
            
            # Toca assincronamente pelo Windows MCI (Media Control Interface)
            open_cmd = f'open "{temp_audio_file}" type mpegvideo alias willow_voice'
            ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, None)
            ctypes.windll.winmm.mciSendStringW("play willow_voice", None, 0, None)
            
            self.is_speaking = True
            
        except Exception as e:
            logger.error("Erro no Edge TTS/MCI: %s", e)
            self.is_speaking = False

    @staticmethod
    def list_microphones() -> list[dict]:
        """Lista todos os microfones disponiveis no sistema.

        Returns:
            Lista de dicts com indice e nome de cada microfone.
        """
        mics = []
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            mics.append({"index": i, "name": name})
        return mics

    @staticmethod
    def list_audio_devices() -> None:
        """Imprime todos os dispositivos de audio (entrada e saida)."""
        print(sd.query_devices())
