"""
Willow -- Audio Engine
======================
Modulo responsavel por captura de voz (Speech-to-Text)
e sintese de fala (Text-to-Speech).

Dependencias:
    - SpeechRecognition (captura e transcricao)
    - edge-tts (sintese de voz neural da Microsoft)
    - sounddevice (monitoramento de audio para barge-in)
    - numpy (processamento de sinal de audio)
    - ctypes/winmm (playback via MCI do Windows)
"""

import atexit
import asyncio
import ctypes
import logging
import os
import tempfile
import time
import uuid

import edge_tts
import numpy as np
import sounddevice as sd
import speech_recognition as sr

logger = logging.getLogger("willow.audio")


class AudioEngine:
    """Motor de audio da Willow.

    Responsavel por:
        - Escutar o microfone e transcrever fala em texto.
        - Falar respostas em voz alta usando Edge TTS + MCI.
        - Monitorar interrupcao por voz (barge-in) durante a fala.
        - Listar dispositivos de audio disponiveis.
    """

    # Alias do recurso MCI usado para playback
    _MCI_ALIAS = "willow_voice"

    def __init__(
        self,
        mic_index: int = -1,
        language: str = "pt-BR",
        listen_timeout: int = 5,
        phrase_time_limit: int = 10,
        barge_in_threshold: float = 3.5,
    ) -> None:
        """Inicializa o motor de audio.

        Args:
            mic_index: Indice do microfone (-1 para autodetectar).
            language: Idioma para reconhecimento de voz.
            listen_timeout: Segundos esperando o usuario comecar a falar.
            phrase_time_limit: Segundos maximos de captura por frase.
            barge_in_threshold: Sensibilidade do detector de interrupcao.
        """
        self.language = language
        self.listen_timeout = listen_timeout
        self.phrase_time_limit = phrase_time_limit
        self.barge_in_threshold = barge_in_threshold

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
        self._last_temp_file: str | None = None

        # Registrar cleanup automatico ao encerrar o programa
        atexit.register(self._cleanup)

        logger.info("AudioEngine inicializado com sucesso (Voz: %s)", self.tts_voice)

    # ------------------------------------------------------------------
    # Metodos privados
    # ------------------------------------------------------------------

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

    def _mci_send(self, command: str) -> int:
        """Envia um comando MCI ao Windows e retorna o codigo de resultado.

        Args:
            command: String de comando MCI (ex: 'play willow_voice').

        Returns:
            Codigo de retorno da API mciSendStringW (0 = sucesso).
        """
        result = ctypes.windll.winmm.mciSendStringW(command, None, 0, None)
        if result != 0:
            logger.debug("MCI comando '%s' retornou codigo %d", command, result)
        return result

    def _is_mci_playing(self) -> bool:
        """Consulta o MCI para saber se o audio ainda esta tocando.

        Returns:
            True se o audio esta tocando, False caso contrario.
        """
        buf = ctypes.create_unicode_buffer(128)
        ctypes.windll.winmm.mciSendStringW(
            f"status {self._MCI_ALIAS} mode", buf, 128, None
        )
        return buf.value == "playing"

    def _stop_mci(self) -> None:
        """Para e fecha o recurso MCI atual."""
        self._mci_send(f"stop {self._MCI_ALIAS}")
        self._mci_send(f"close {self._MCI_ALIAS}")

    def _cleanup_temp_file(self) -> None:
        """Remove o arquivo temporario de audio anterior, se existir."""
        if self._last_temp_file and os.path.exists(self._last_temp_file):
            try:
                os.remove(self._last_temp_file)
                logger.debug("Temp file removido: %s", self._last_temp_file)
            except OSError as e:
                logger.debug("Nao foi possivel remover temp file: %s", e)
            self._last_temp_file = None

    def _cleanup(self) -> None:
        """Cleanup geral: para o MCI e remove arquivos temporarios.
        Chamado automaticamente via atexit ao encerrar o programa.
        """
        self._stop_mci()
        self._cleanup_temp_file()
        logger.info("AudioEngine cleanup concluido.")

    async def _async_speak(self, text: str) -> str:
        """Gera e salva o audio do Edge TTS assincronamente em formato MP3.

        Args:
            text: Texto a ser convertido em audio.

        Returns:
            Caminho absoluto do arquivo MP3 gerado.
        """
        communicate = edge_tts.Communicate(text, self.tts_voice, rate=self.tts_rate)

        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"willow_speech_{uuid.uuid4().hex[:8]}.mp3")

        await communicate.save(temp_file)
        return temp_file

    # ------------------------------------------------------------------
    # Barge-in (interrupcao por voz)
    # ------------------------------------------------------------------

    def _monitor_barge_in(self) -> bool:
        """Monitora o microfone durante a fala e detecta interrupcao.

        Escuta o microfone em background enquanto o MCI estiver tocando.
        Se detectar volume acima do threshold, para o audio imediatamente.

        Returns:
            True se houve interrupcao, False se o audio terminou naturalmente.
        """
        interrupted = False

        def audio_callback(indata, frames, time_info, status):
            nonlocal interrupted
            volume_norm = np.linalg.norm(indata) * 10
            if volume_norm > self.barge_in_threshold:
                logger.warning("Interrupcao detectada! (Vol: %.1f)", volume_norm)
                self._stop_mci()
                interrupted = True
                raise sd.CallbackStop()

        try:
            with sd.InputStream(callback=audio_callback):
                while self._is_mci_playing() and not interrupted:
                    time.sleep(0.1)
        except Exception as e:
            logger.debug("Erro no stream de interrupcao: %s", e)

        if interrupted:
            logger.info("Willow silenciada por interrupcao do usuario.")
            # Pequena pausa para nao capturar o proprio som da interrupcao
            time.sleep(0.3)

        return interrupted

    # ------------------------------------------------------------------
    # Metodos publicos
    # ------------------------------------------------------------------

    def listen(self) -> str | None:
        """Escuta o microfone e retorna o texto transcrito.

        Se o MCI estiver tocando audio, monitora interrupcoes primeiro.

        Returns:
            Texto transcrito da fala do usuario, ou None se nada foi detectado.
        """
        # Se estiver falando, monitorar interrupcao antes de escutar
        if self._is_mci_playing():
            self._monitor_barge_in()

        # --- Logica Padrao de Escuta (Google STT) ---
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
        """Fala o texto de forma assincrona (nao bloqueante) usando Edge TTS + MCI.

        O audio e gerado pelo Edge TTS, salvo como MP3 temporario,
        e tocado assincronamente pelo Windows MCI (Media Control Interface).

        Args:
            text: Texto a ser falado.
        """
        if not text:
            return

        logger.info("Falando: '%s'", text)
        try:
            # Para qualquer audio anterior e limpa o temp file
            self._stop_mci()
            self._cleanup_temp_file()

            # Gera novo audio via Edge TTS
            temp_audio_file = asyncio.run(self._async_speak(text))
            self._last_temp_file = temp_audio_file

            # Toca assincronamente pelo Windows MCI
            open_cmd = f'open "{temp_audio_file}" type mpegvideo alias {self._MCI_ALIAS}'
            self._mci_send(open_cmd)
            self._mci_send(f"play {self._MCI_ALIAS}")

        except Exception as e:
            logger.error("Erro no Edge TTS/MCI: %s", e)

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
