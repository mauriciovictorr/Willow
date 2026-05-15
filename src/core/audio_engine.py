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
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import edge_tts
import winsound

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
        """Gera e salva o audio do Edge TTS assincronamente em formato WAV nativo."""
        communicate = edge_tts.Communicate(text, self.tts_voice, rate=self.tts_rate)
        
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "willow_speech.wav")
        
        # Gera WAV pcm (16-bit) para compatibilidade com winsound
        with open(temp_file, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                    
        # Edge TTS raw PCM requires headers, but saving with --format does it automatically?
        # A forma mais estavel pela API Python para ter headers WAV é usar subprocess ou aiofiles, 
        # mas como estamos chamando save(), podemos apenas usar o edge_tts padrao.
        # Wait, the stream method above doesn't add wav headers.
        # Vamos usar a CLI interna ou apenas o save() padrao.
        return temp_file
        
    async def _generate_wav(self, text: str, output_file: str) -> None:
        """Usa subprocess para chamar a CLI do edge-tts e gerar um WAV garantido."""
        # Acha o executavel do edge-tts dentro do ambiente virtual atual
        python_dir = os.path.dirname(sys.executable)
        edge_tts_path = os.path.join(python_dir, "edge-tts")
        
        # A CLI gera headers RIFF corretos, a API Python as vezes falha com PCM
        cmd = f'"{edge_tts_path}" --voice "{self.tts_voice}" --text "{text}" --rate="{self.tts_rate}" --format "riff-24khz-16bit-mono-pcm" --write-media "{output_file}"'
        proc = await asyncio.create_subprocess_shell(cmd)
        await proc.communicate()

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
                    winsound.PlaySound(None, winsound.SND_PURGE) # Cala a boca
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
        """Fala o texto de forma assincrona (nao bloqueante)."""
        if not text:
            return

        logger.info("Falando: '%s'", text)
        try:
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "willow_speech.wav")
            
            # Garante que nao tem arquivo sujo
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

            # Gera o WAV usando a CLI interna do edge-tts para headers corretos
            asyncio.run(self._generate_wav(text, temp_file))
            
            # Toca assincronamente pelo Windows
            winsound.PlaySound(temp_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.is_speaking = True
            
        except Exception as e:
            logger.error("Erro no Edge TTS/Winsound: %s", e)
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
