# Willow — Assistente Virtual Inteligente por Voz

> Assistente de IA que escuta sua voz, entende linguagem natural e automatiza tarefas no seu computador Windows.

## Visao Geral

Willow e uma assistente virtual controlada por voz, construida em Python, capaz de:
- **Ouvir** comandos de voz em portugues via microfone.
- **Entender** linguagem natural usando modelos de IA (Google Gemini / OpenAI).
- **Executar** tarefas no Windows (abrir programas, pesquisar na web, diagnosticar problemas no terminal).
- **Seguranca** embutida com guardrails para bloquear acoes destrutivas e conteudo ilicito.

## Estrutura do Projeto

```
willow/
├── agents/                    # Perfis dos agentes de IA da equipe
│   ├── ada.md                 # Backend, Python, IA e Automação
│   ├── zane.md                # Frontend, UI/UX e Design
│   ├── turing.md              # QA, Debugging e DevOps
│   └── cipher.md              # Cibersegurança e Guardrails
├── guardrails/                # Regras de segurança (dados)
│   ├── blocked_commands.yaml  # Comandos de terminal proibidos
│   └── blocked_urls.yaml      # Sites e domínios bloqueados
├── src/                       # Código-fonte Python
│   ├── core/                  # Módulos principais
│   │   ├── audio_engine.py    # Captura de áudio e Text-to-Speech
│   │   ├── brain.py           # Conexão com LLMs (Gemini/Claude)
│   │   └── router.py          # Roteador de intenções
│   └── actions/               # Ações que a Willow pode executar
│       ├── system.py          # Abrir apps, volume, terminal
│       └── browser.py         # Abrir sites, pesquisar na web
├── tests/                     # Testes automatizados
├── main.py                    # Ponto de entrada principal
├── requirements.txt           # Dependências Python
├── .env.example               # Modelo de variáveis de ambiente
├── REGRAS.md                  # Regras de operação da equipe de IA
└── README.md                  # Este arquivo
```

## Instalacao

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/willow.git

# 2. Entre na pasta
cd willow

# 3. Crie um ambiente virtual
python -m venv venv
venv\Scripts\activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure as variáveis de ambiente
copy .env.example .env
# Edite o arquivo .env com suas chaves de API
```

## Como Usar

```bash
python main.py
```

Willow vai cumprimentar você e começar a escutar. Fale normalmente!

## Seguranca

Willow possui um sistema de guardrails que:
- Bloqueia comandos destrutivos no terminal (format, del /s, etc.)
- Impede acesso a sites adultos, de pirataria ou inseguros
- Permite comandos de diagnostico (ping, ipconfig, dir, etc.)
- Valida intencoes antes de executar qualquer acao

## Equipe de Desenvolvimento

| Agente   | Especialidade                      |
|----------|------------------------------------|
| **Ada**    | Backend, Python, IA, Automação   |
| **Zane**   | Frontend, UI/UX, Design         |
| **Turing** | QA, Debugging, DevOps           |
| **Cipher** | Cibersegurança, Guardrails      |

## Licenca

Este projeto é licenciado sob a [Licença MIT](LICENSE).

---

> Criado por **Maurício** com apoio da equipe de agentes de IA.
