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
import os
import tempfile
import asyncio
import sounddevice as sd
import speech_recognition as sr
import edge_tts
from playsound import playsound

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
        # Usando a voz masculina do Azure/Edge (Antonio)
        self.tts_voice = "pt-BR-AntonioNeural"
        self.tts_rate = "+0%"  # Pode ajustar se quiser mais rapido ou devagar

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

    async def _async_speak(self, text: str) -> None:
        """Gera e salva o audio do Edge TTS assincronamente."""
        communicate = edge_tts.Communicate(text, self.tts_voice, rate=self.tts_rate)
        
        # Criar arquivo temporario para o audio
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "willow_speech.mp3")
        
        await communicate.save(temp_file)
        return temp_file

    def listen(self) -> str | None:
        """Escuta o microfone e retorna o texto transcrito.

        Returns:
            Texto transcrito ou None se nao conseguiu entender.
        """
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
        """Fala o texto usando Text-to-Speech (Edge TTS - voz masculina neural).

        Args:
            text: Texto para ser falado.
        """
        if not text:
            return

        logger.info("Falando (Edge TTS): '%s'", text)
        try:
            # Roda o gerador de audio assincrono
            temp_audio_file = asyncio.run(self._async_speak(text))
            
            # Toca o arquivo
            playsound(temp_audio_file)
            
            # Remove o temporario apos falar
            try:
                os.remove(temp_audio_file)
            except OSError:
                pass
                
        except Exception as e:
            logger.error("Erro no Edge TTS: %s", e)

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
