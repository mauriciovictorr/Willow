"""
Willow -- Cérebro (LLM)
========================
Módulo responsável pela inteligência da assistente.
Conecta-se ao Ollama (IA Local) para processamento de linguagem natural.

Dependências:
    - requests
"""

import logging
import requests

logger = logging.getLogger("willow.brain")


class Brain:
    """Cérebro da Willow.

    Responsável por:
        - Receber texto do usuário.
        - Enviar para o modelo de IA local (Ollama).
        - Retornar a resposta gerada.
        - (Futuro) Manter contexto da conversa.
    """

    def __init__(
        self,
        model: str = "phi3",
        base_url: str = "http://localhost:11434/api/generate",
        system_prompt: str = "",
    ) -> None:
        """Inicializa o cérebro conectado ao Ollama.

        Args:
            model: Nome do modelo instalado no Ollama (ex: phi3, llama3).
            base_url: URL da API local do Ollama.
            system_prompt: Instruções de como a IA deve se comportar.
        """
        self.model = model
        self.base_url = base_url
        self.system_prompt = system_prompt or (
            "Você é a Willow, uma assistente virtual inteligente e prestativa. "
            "Responda sempre em português do Brasil, de forma clara, "
            "direta e sem usar emojis. Suas respostas serão faladas em voz alta, "
            "então evite formatações complexas como tabelas ou códigos longos."
        )

        # Testa a conexão com o Ollama ao iniciar
        self._check_connection()

    def _check_connection(self) -> None:
        """Verifica se o servidor Ollama está rodando e respondendo."""
        try:
            # Endpoint padrão do Ollama para checar status
            response = requests.get(self.base_url.replace("/api/generate", ""), timeout=2)
            if response.status_code == 200:
                logger.info("Cérebro conectado ao Ollama local com sucesso!")
            else:
                logger.warning("Ollama respondeu com status: %d", response.status_code)
        except requests.ConnectionError:
            logger.error(
                "Falha ao conectar no Ollama. Verifique se o programa está aberto "
                "e rodando em %s", self.base_url
            )
        except requests.Timeout:
            logger.error("Timeout ao tentar conectar no Ollama local.")

    def think(self, user_text: str) -> str | None:
        """Processa a fala do usuário e gera uma resposta.

        Args:
            user_text: O que o usuário falou.

        Returns:
            A resposta em texto gerada pela IA, ou None se falhar.
        """
        if not user_text:
            return None

        logger.info("Willow pensando sobre: '%s'", user_text)

        payload = {
            "model": self.model,
            "prompt": user_text,
            "system": self.system_prompt,
            "stream": False,  # Resposta completa de uma vez
            "options": {
                "temperature": 0.7,  # Nível de criatividade
            }
        }

        try:
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            answer = data.get("response", "").strip()
            
            logger.info("Willow respondeu (tamanho: %d chars)", len(answer))
            return answer

        except requests.ConnectionError:
            logger.error("Erro de conexão com o Ollama.")
            return "Desculpe, meu servidor mental está desligado. Por favor, abra o Ollama."
        except requests.Timeout:
            logger.error("Ollama demorou muito para responder (Timeout).")
            return "Desculpe, demorei muito para pensar. Pode repetir?"
        except Exception as e:
            logger.error("Erro inesperado no Cérebro: %s", e)
            return "Ocorreu um erro na minha rede neural."

    def set_system_prompt(self, new_prompt: str) -> None:
        """Atualiza a personalidade / comportamento da IA."""
        self.system_prompt = new_prompt
        logger.info("System prompt atualizado.")
