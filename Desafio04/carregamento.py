import os
import pandas as pd

class CarregadorDados:
    """
    Classe responsável por carregar e normalizar os dados das planilhas Excel.
    """

    def __init__(self, base_dir: str):
        """
        Inicializa o carregador com o diretório base das planilhas.
        """
        self.base_dir = base_dir

    def carregar_planilha(self, nome_arquivo: str, header=0) -> pd.DataFrame:
        """
        Carrega uma planilha Excel do diretório base.
        """
        return pd.read_excel(os.path.join(self.base_dir, nome_arquivo), header=header)

    def carregar_todas_planilhas(self) -> dict:
        """
        Carrega todas as planilhas necessárias e retorna em um dicionário.
        """
        dados = {
            "ativos": self.carregar_planilha("ATIVOS.xlsx"),
            "admis": self.carregar_planilha("ADMISSÃO ABRIL.xlsx"),
            "ferias": self.carregar_planilha("FÉRIAS.xlsx"),
            "deslig_raw": self.carregar_planilha("DESLIGADOS.xlsx", header=None),
            "afast": self.carregar_planilha("AFASTAMENTOS.xlsx"),
            "apr": self.carregar_planilha("APRENDIZ.xlsx"),
            "estag": self.carregar_planilha("ESTÁGIO.xlsx"),
            "ext_raw": self.carregar_planilha("EXTERIOR.xlsx", header=None),
            "dias": self.carregar_planilha("Base dias uteis.xlsx", header=None),
            "sxv": self.carregar_planilha("Base sindicato x valor.xlsx", header=None),
        }
        return dados
    
    def limpar_desligados(self, df):
        df.columns = df.iloc[0]
        return df.iloc[1:].copy()

    def limpar_exterior(self, df):
        df.columns = df.iloc[0]
        return df.iloc[1:].copy()
    
    def limpar_dias_uteis(self, df):
        df.columns = ["SINDICATO", "DIAS_UTEIS"]
        return df.iloc[2:].copy()
    
    def limpar_sindicato_valor(self, df):
        df.columns = ["ESTADO", "VALOR"]
        return df.iloc[1:5].copy()