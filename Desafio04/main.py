from processamento import ProcessadorVR
from carregamento import CarregadorDados
import argparse

def main():
    """
    Função principal que executa o processamento do VR.
    """
    parser = argparse.ArgumentParser(description="Processador de VR (versão Python puro, modularizado e orientado a objetos)")
    parser.add_argument("--base-dir", required=True, help="Pasta com as planilhas de entrada")
    parser.add_argument("--out", required=True, help="Caminho do arquivo .xlsx de saída")
    args = parser.parse_args()

    carregador = CarregadorDados(args.base_dir)
    dados = carregador.carregar_todas_planilhas()
    dados["dias"] = carregador.limpar_dias_uteis(dados["dias"])
    dados["deslig"] = carregador.limpar_desligados(dados["deslig_raw"])
    dados["ext"] = carregador.limpar_exterior(dados["ext_raw"])
    dados["sxv"] = carregador.limpar_sindicato_valor(dados["sxv"])
    processador = ProcessadorVR(dados)
    caminho_saida = processador.processar(args.out)
    print(f"Arquivo gerado em: {caminho_saida}")

if __name__ == "__main__":
    main()