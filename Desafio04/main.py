import os
import argparse
from agente_vr import AgenteVR

def main():
    parser = argparse.ArgumentParser(description="Agente de VR com Structured Output")
    parser.add_argument("--model", required=True, help="Caminho do modelo LLaMA")
    parser.add_argument("--base-dir", required=True, help="Pasta com planilhas")
    parser.add_argument("--out", required=True, help="Arquivo de saída")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"Modelo não encontrado: {args.model}")
        return
    
    if not os.path.exists(args.base_dir):
        print(f"Pasta não encontrada: {args.base_dir}")
        return

    try:
        print("Inicializando agente...")
        agente = AgenteVR(args.model)
        
        print("Listando arquivos...")
        print(agente.executar_comando(f"Liste os arquivos em {args.base_dir}"))
        
        print("Validando dados...")
        print(agente.executar_comando(f"Valide os dados em {args.base_dir}"))
        
        print("Processando VR...")
        resultado = agente.executar_comando(f"Processe os dados de {args.base_dir} e salve em {args.out}")
        print(resultado)
        
        if os.path.exists(args.out):
            print(f"Arquivo criado: {args.out}")
            
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    main()