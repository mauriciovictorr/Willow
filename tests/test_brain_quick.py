"""Teste rapido: verifica a conexao com o Cerebro (Ollama) e envia uma pergunta."""

from src.core.brain import Brain

def main():
    print("=== Teste do Cerebro ===")
    brain = Brain(model="phi3")
    
    pergunta = "Qual e a capital do Brasil? Responda em uma frase curta."
    print(f"\n[Usuario]: {pergunta}")
    
    resposta = brain.think(pergunta)
    
    print(f"\n[Willow]: {resposta}")

if __name__ == "__main__":
    main()
