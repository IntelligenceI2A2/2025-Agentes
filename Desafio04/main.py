import argparse
from agente_vr import AgenteVR

def main():
    parser = argparse.ArgumentParser(description="Agente VR com LangChain + OpenAI GPT")
    parser.add_argument("--base-dir", required=True, help="Pasta com as planilhas do Desafio04")
    parser.add_argument("--out", default=None, help="Arquivo de saída .xlsx")
    parser.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI (ex.: gpt-4o, gpt-4o-mini)")

    args = parser.parse_args()

    agent = AgenteVR(model_name=args.model)
    
    agent.executar_fluxo_completo(args.base_dir, args.out)
    
if __name__ == "__main__":
    main()