import zipfile
import pandas as pd
from pathlib import Path
from typing import List, Dict

class LeitorNotasFiscais:
    def __init__(self, caminho_arquivo_zip: str):
        self.caminho_arquivo_zip = Path(caminho_arquivo_zip)
        self.diretorio_extracao = Path("dados_extraidos")
        self.dados_cabecalho = pd.DataFrame()
        self.dados_itens = pd.DataFrame()
        self.notas_fiscais: List[Dict] = []

    def extrair_arquivos(self) -> None:
        with zipfile.ZipFile(self.caminho_arquivo_zip, 'r') as zip_ref:
            zip_ref.extractall(self.diretorio_extracao)

    def carregar_dados_csv(self) -> None:
        self.dados_cabecalho = pd.read_csv(self.diretorio_extracao / "202401_NFs_Cabecalho.csv", sep=",", encoding="utf-8")
        self.dados_itens = pd.read_csv(self.diretorio_extracao / "202401_NFs_Itens.csv", sep=",", encoding="utf-8")
        self.dados_cabecalho.columns = [col.strip().lower().replace(' ', '_') for col in self.dados_cabecalho.columns]
        self.dados_itens.columns = [col.strip().lower().replace(' ', '_') for col in self.dados_itens.columns]

    def montar_objetos_notas(self) -> None:
        for _, linha in self.dados_cabecalho.iterrows():
            chave_acesso = linha["chave_de_acesso"]
            itens_relacionados = self.dados_itens[self.dados_itens["chave_de_acesso"] == chave_acesso]

            nota_fiscal = {
                "chave_acesso": chave_acesso,
                "cabecalho": {
                    "data_emissao": linha.get("data_emissão"),
                    "razao_social_emitente": linha.get("razão_social_emitente"),
                    "cnpj_emitente": linha.get("cpf/cnpj_emitente"),
                    "cnpj_destinatario": linha.get("cnpj_destinatário"),
                    "valor_nota_fiscal": linha.get("valor_nota_fiscal"),
                },
                "itens": [
                    {
                        "descricao": item.get("descrição_do_produto/serviço"),
                        "quantidade": item.get("quantidade"),
                        "valor_total": item.get("valor_total")
                    }
                    for _, item in itens_relacionados.iterrows()
                ]
            }
            self.notas_fiscais.append(nota_fiscal)
