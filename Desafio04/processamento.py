import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

PERIODO_INICIO = datetime(2025, 4, 15).date()
PERIODO_FIM = datetime(2025, 5, 15).date()

class ProcessadorVR:
    """
    Classe responsável por processar os dados e gerar o relatório de VR.
    """

    def __init__(self, dados: dict):
        """
        Inicializa o processador com os dados das planilhas.
        """
        self.dados = dados
        self.base = None

    def estado_from_sindicato(self, sindicato: str) -> Optional[str]:
        """
        Extrai o estado a partir do nome do sindicato.
        """
        if not isinstance(sindicato, str):
            return None
        s_up = sindicato.upper()
        mapping = {"SP": "São Paulo", "RJ": "Rio de Janeiro", "RS": "Rio Grande do Sul", "PR": "Paraná"}
        toks = s_up.replace(".", " ").replace("-", " ").split()
        for p in reversed(toks):
            if p in mapping:
                return mapping[p]
        if "SÃO PAULO" in s_up: return "São Paulo"
        if "RIO DE JANEIRO" in s_up: return "Rio de Janeiro"
        if "RIO GRANDE DO SUL" in s_up: return "Rio Grande do Sul"
        if "PARANÁ" in s_up: return "Paraná"
        return None

    def chave_sindicato(self, sindicato: str) -> Optional[str]:
        """
        Gera uma chave simplificada para o sindicato.
        """
        if not isinstance(sindicato, str): return None
        s = sindicato.upper()
        toks = s.split()
        if len(toks) >= 2:
            return f"{toks[0]} {toks[1]}"
        return toks[0] if toks else None

    def normalizar_dados(self):
        """
        Realiza todas as normalizações necessárias nos dados.
        """
        # Normalizações de tipos
        for col in ["MATRICULA"]:
            for key in ["ativos", "admis", "ferias", "afast", "apr", "estag"]:
                df = self.dados[key]
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        ext = self.dados["ext"]
        if "Cadastro" in ext.columns:
            ext["Cadastro"] = pd.to_numeric(ext["Cadastro"], errors="coerce").astype("Int64")
        admis = self.dados["admis"]
        if "Admissão" in admis.columns:
            admis["Admissão"] = pd.to_datetime(admis["Admissão"], errors="coerce").dt.date
        ferias = self.dados["ferias"]
        if "DIAS DE FÉRIAS" in ferias.columns:
            ferias["DIAS DE FÉRIAS"] = pd.to_numeric(ferias["DIAS DE FÉRIAS"], errors="coerce").fillna(0)
        dias = self.dados["dias"]
        dias["DIAS_UTEIS"] = pd.to_numeric(dias["DIAS_UTEIS"], errors="coerce")
        sxv = self.dados["sxv"]
        sxv["VALOR"] = pd.to_numeric(sxv["VALOR"], errors="coerce")

        # Estado e chave de sindicato
        ativos = self.dados["ativos"]
        dias = self.dados["dias"]
        ativos["ESTADO"] = ativos["Sindicato"].astype(str).apply(self.estado_from_sindicato)
        ativos["SIND_KEY"] = ativos["Sindicato"].astype(str).apply(self.chave_sindicato)
        dias["SIND_KEY"] = dias["SINDICATO"].astype(str).str.upper().apply(self.chave_sindicato)

        # Merge dias úteis
        self.base = ativos.merge(dias[["SIND_KEY", "DIAS_UTEIS"]], on="SIND_KEY", how="left")

    def aplicar_regras_negocio(self):
        """
        Aplica as regras de negócio para exclusões e cálculos.
        """
        apr = self.dados["apr"]
        estag = self.dados["estag"]
        afast = self.dados["afast"]
        ext = self.dados["ext"]
        ativos = self.dados["ativos"]

        # Exclusões
        excluir = set()
        if "MATRICULA" in apr.columns: excluir |= set(apr["MATRICULA"].dropna())
        if "MATRICULA" in estag.columns: excluir |= set(estag["MATRICULA"].dropna())
        if "MATRICULA" in afast.columns: excluir |= set(afast["MATRICULA"].dropna())
        if "Cadastro" in ext.columns: excluir |= set(ext["Cadastro"].dropna())

        mask_dir = ativos["TITULO DO CARGO"].astype(str).str.upper().str.contains("DIRETOR")
        self.base = self.base[~self.base["MATRICULA"].isin(excluir)]
        self.base = self.base[~mask_dir.reindex(self.base.index, fill_value=False)]

        # Férias
        ferias = self.dados["ferias"]
        ferias_sum = ferias.groupby("MATRICULA", as_index=False)["DIAS DE FÉRIAS"].sum()
        self.base = self.base.merge(ferias_sum, on="MATRICULA", how="left")
        self.base["DIAS DE FÉRIAS"] = self.base["DIAS DE FÉRIAS"].fillna(0)
        self.base["DIAS_COMPRAR_INICIAL"] = self.base["DIAS_UTEIS"].fillna(0) - self.base["DIAS DE FÉRIAS"]
        self.base.loc[self.base["DIAS_COMPRAR_INICIAL"] < 0, "DIAS_COMPRAR_INICIAL"] = 0

        # Admissões no período
        admis = self.dados["admis"]
        admis_period = admis[(admis["Admissão"] >= PERIODO_INICIO) & (admis["Admissão"] <= PERIODO_FIM)]
        self.base = self.base.merge(admis_period[["MATRICULA", "Admissão"]], on="MATRICULA", how="left")

        # Proporcionalidade por admissão (usando business days do período)
        total_period_bd = np.busday_count(PERIODO_INICIO, PERIODO_FIM)
        self.base["DIAS_ADMISSAO"] = 0
        mask_adm = self.base["Admissão"].notna()
        if mask_adm.any():
            self.base.loc[mask_adm, "DIAS_ADMISSAO"] = [
                np.busday_count(max(a, PERIODO_INICIO), PERIODO_FIM) for a in self.base.loc[mask_adm, "Admissão"]
            ]
        self.base["DIAS_APOS_ADMISSAO_PROP"] = np.where(
            mask_adm,
            (self.base["DIAS_COMPRAR_INICIAL"] * (self.base["DIAS_ADMISSAO"] / max(1, total_period_bd))).round().astype("Int64"),
            self.base["DIAS_COMPRAR_INICIAL"]
        )

        # Desligamentos
        deslig = self.dados["deslig"]
        deslig = deslig.rename(columns={c: c.strip() for c in deslig.columns})
        deslig["MATRICULA"] = pd.to_numeric(deslig["MATRICULA"], errors="coerce").astype("Int64")
        self.base = self.base.merge(deslig[["MATRICULA", "DATA DEMISSÃO", "COMUNICADO DE DESLIGAMENTO"]], on="MATRICULA", how="left")

        def dias_pos_deslig(row):
            d = row["DATA DEMISSÃO"]
            if pd.isna(d):
                return int(row["DIAS_APOS_ADMISSAO_PROP"])
            d_date = pd.to_datetime(d).date()
            # Regra: se comunicado OK e demissão até 15/05, zera
            if str(row["COMUNICADO DE DESLIGAMENTO"]).upper() == "OK" and d_date <= PERIODO_FIM:
                return 0
            # Caso contrário, proporcional até a demissão
            start = PERIODO_INICIO
            end = min(d_date, PERIODO_FIM)
            dias_u = np.busday_count(start, end)
            prop = int(round(row["DIAS_APOS_ADMISSAO_PROP"] * (dias_u / max(1, total_period_bd))))
            return min(prop, int(row["DIAS_APOS_ADMISSAO_PROP"]))

        self.base["DIAS_FINAIS"] = self.base.apply(dias_pos_deslig, axis=1).astype(int)
        self.base.loc[self.base["DIAS_FINAIS"] < 0, "DIAS_FINAIS"] = 0

    def calcular_valores(self):
        """
        Realiza os cálculos finais de valores de VR.
        """
        sxv = self.dados["sxv"]
        self.base = self.base.merge(sxv, on="ESTADO", how="left").rename(columns={"VALOR": "VALOR_DIA"})
        self.base["VALOR_DIA"] = self.base["VALOR_DIA"].fillna(0.0)
        self.base["VALOR_VR"] = (self.base["DIAS_FINAIS"] * self.base["VALOR_DIA"]).round(2)
        self.base["EMPRESA_R$"] = (self.base["VALOR_VR"] * 0.80).round(2)
        self.base["COLAB_R$"] = (self.base["VALOR_VR"] * 0.20).round(2)

    def processar(self, caminho_saida: str) -> str:
        """
        Executa todo o processamento e gera o arquivo de saída.
        """
        self.normalizar_dados()
        self.aplicar_regras_negocio()
        self.calcular_valores()
        # Saída
        out_cols = [
            "MATRICULA", "EMPRESA", "TITULO DO CARGO", "Sindicato", "ESTADO",
            "DIAS_UTEIS", "DIAS DE FÉRIAS", "Admissão", "DATA DEMISSÃO", "COMUNICADO DE DESLIGAMENTO",
            "DIAS_FINAIS", "VALOR_DIA", "VALOR_VR", "EMPRESA_R$", "COLAB_R$"
        ]
        saida = self.base[out_cols].copy()
        saida.to_excel(caminho_saida, index=False)
        return caminho_saida