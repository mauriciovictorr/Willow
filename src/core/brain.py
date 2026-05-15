"""
Willow -- Cerebro (LLM)
========================
Modulo responsavel pela inteligencia da assistente.
Conecta-se ao Ollama (IA Local) para processamento de linguagem natural.

Dependencias:
    - requests
"""

import logging
import requests

logger = logging.getLogger("willow.brain")


class Brain:
    """Cerebro da Willow.

    Responsavel por:
        - Receber texto do usuario.
        - Enviar para o modelo de IA local (Ollama).
        - Manter historico da conversa para contexto.
        - Retornar a resposta gerada.
    """

    # Limite de mensagens no historico para evitar tokens excessivos
    MAX_HISTORY_LENGTH = 20

    def __init__(
        self,
        model: str = "phi3",
        base_url: str = "http://localhost:11434",
        system_prompt: str = "",
    ) -> None:
        """Inicializa o cerebro conectado ao Ollama.

        Args:
            model: Nome do modelo instalado no Ollama (ex: phi3, llama3).
            base_url: URL base do servidor Ollama (sem endpoint).
            system_prompt: Instrucoes de como a IA deve se comportar.
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.chat_url = f"{self.base_url}/api/chat"

        self.system_prompt = system_prompt or (
            "Voce e a Willow, uma assistente virtual inteligente e prestativa. "
            "Responda sempre em portugues do Brasil, de forma clara, "
            "direta e sem usar emojis. Suas respostas serao faladas em voz alta, "
            "entao evite formatacoes complexas como tabelas ou codigos longos."
        )

        # Historico de conversa (mantido entre chamadas)
        self.history: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Testa a conexao com o Ollama ao iniciar
        self._check_connection()

    def _check_connection(self) -> None:
        """Verifica se o servidor Ollama esta rodando e respondendo."""
        try:
            response = requests.get(self.base_url, timeout=2)
            if response.status_code == 200:
                logger.info("Cerebro conectado ao Ollama local com sucesso!")
            else:
                logger.warning("Ollama respondeu com status: %d", response.status_code)
        except requests.ConnectionError:
            logger.error(
                "Falha ao conectar no Ollama. Verifique se o programa esta aberto "
                "e rodando em %s", self.base_url
            )
        except requests.Timeout:
            logger.error("Timeout ao tentar conectar no Ollama local.")

    def _trim_history(self) -> None:
        """Remove mensagens antigas para manter o historico dentro do limite.

        Preserva sempre a mensagem de sistema (indice 0) e remove as
        mensagens mais antigas apos o limite.
        """
        if len(self.history) > self.MAX_HISTORY_LENGTH:
            # Manter system prompt + ultimas mensagens
            self.history = [self.history[0]] + self.history[-(self.MAX_HISTORY_LENGTH - 1):]
            logger.debug("Historico aparado para %d mensagens", len(self.history))

    def think(self, user_text: str) -> str | None:
        """Processa a fala do usuario e gera uma resposta com contexto.

        Mantém historico da conversa para que a Willow lembre do que
        foi dito anteriormente na mesma sessao.

        Args:
            user_text: O que o usuario falou.

        Returns:
            A resposta em texto gerada pela IA, ou None se falhar.
        """
        if not user_text:
            return None

        logger.info("Willow pensando sobre: '%s'", user_text)

        # Adicionar mensagem do usuario ao historico
        self.history.append({"role": "user", "content": user_text})

        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": False,
            "options": {
                "temperature": 0.7,
            }
        }

        try:
            response = requests.post(self.chat_url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})
            answer = message.get("content", "").strip()

            # Adicionar resposta da IA ao historico
            self.history.append({"role": "assistant", "content": answer})
            self._trim_history()

            logger.info("Willow respondeu (tamanho: %d chars)", len(answer))
            return answer

        except requests.ConnectionError:
            logger.error("Erro de conexao com o Ollama.")
            # Remover a mensagem do usuario que falhou
            self.history.pop()
            return "Desculpe, meu servidor mental esta desligado. Por favor, abra o Ollama."

        except requests.Timeout:
            logger.error("Ollama demorou muito para responder (Timeout).")
            self.history.pop()
            return "Desculpe, demorei muito para pensar. Pode repetir?"

        except Exception as e:
            logger.error("Erro inesperado no Cerebro: %s", e)
            self.history.pop()
            return "Ocorreu um erro na minha rede neural."

    def clear_history(self) -> None:
        """Limpa o historico da conversa, mantendo apenas o system prompt."""
        self.history = [self.history[0]]
        logger.info("Historico de conversa limpo.")

    def set_system_prompt(self, new_prompt: str) -> None:
        """Atualiza a personalidade / comportamento da IA.

        Args:
            new_prompt: Novo texto de instrucoes para o modelo.
        """
        self.system_prompt = new_prompt
        self.history[0] = {"role": "system", "content": new_prompt}
        logger.info("System prompt atualizado.")
