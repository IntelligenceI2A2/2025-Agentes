from integrador_api import IntegradorAPI
from processador_zip import LeitorNotasFiscais

def main():
    leitor = LeitorNotasFiscais("202401_NFs.zip")
    leitor.extrair_arquivos()
    leitor.carregar_dados_csv()
    leitor.montar_objetos_notas()

    integrador = IntegradorAPI(base_url="https://n8n2.tec.pet/webhook/NotasI2A2")
    integrador.enviar_notas(leitor.notas_fiscais)

if __name__ == "__main__":
    main()
