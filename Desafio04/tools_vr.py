import os
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime

PERIOD_START = datetime(2025, 4, 15).date()
PERIOD_END   = datetime(2025, 5, 15).date()

def _estado_from_sind(s: str) -> Optional[str]:
    if not isinstance(s, str):
        return None
    s_up = s.upper()
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

def _sindicato_key(s: str) -> Optional[str]:
    if not isinstance(s, str): 
        return None
    s = s.upper()
    toks = s.split()
    if len(toks) >= 2:
        return f"{toks[0]} {toks[1]}"
    return toks[0] if toks else None

def carregar_bases(base_dir: str) -> Dict[str, pd.DataFrame]:
    """Carrega todas as bases esperadas no desafio."""
    dfs: Dict[str, pd.DataFrame] = {}

    dfs["ativos"] = pd.read_excel(os.path.join(base_dir, "ATIVOS.xlsx"))
    dfs["admis"] = pd.read_excel(os.path.join(base_dir, "ADMISSÃO ABRIL.xlsx"))
    dfs["ferias"] = pd.read_excel(os.path.join(base_dir, "FÉRIAS.xlsx"))

    deslig_raw = pd.read_excel(os.path.join(base_dir, "DESLIGADOS.xlsx"), header=None)
    deslig_raw.columns = deslig_raw.iloc[0]
    dfs["deslig"] = deslig_raw.iloc[1:].copy()

    dfs["afast"] = pd.read_excel(os.path.join(base_dir, "AFASTAMENTOS.xlsx"))
    dfs["apr"]   = pd.read_excel(os.path.join(base_dir, "APRENDIZ.xlsx"))
    dfs["estag"] = pd.read_excel(os.path.join(base_dir, "ESTÁGIO.xlsx"))

    ext_raw = pd.read_excel(os.path.join(base_dir, "EXTERIOR.xlsx"), header=None)
    ext_raw.columns = ext_raw.iloc[0]
    dfs["ext"] = ext_raw.iloc[1:].copy()

    dias = pd.read_excel(os.path.join(base_dir, "Base dias uteis.xlsx"), header=None)
    dias.columns = ["SINDICATO", "DIAS_UTEIS"]
    dfs["dias"] = dias.iloc[2:].copy()

    sxv = pd.read_excel(os.path.join(base_dir, "Base sindicato x valor.xlsx"), header=None)
    sxv.columns = ["ESTADO", "VALOR"]
    dfs["sxv"] = sxv.iloc[1:5].copy()

    return dfs

def validar_ativos_colunas(base_dir: str) -> str:
    req = {"MATRICULA", "EMPRESA", "TITULO DO CARGO", "Sindicato"}
    df = pd.read_excel(os.path.join(base_dir, "ATIVOS.xlsx"))
    ok = req.issubset(set(df.columns))
    faltando = list(req - set(df.columns))
    return f"ATIVOS tem colunas mínimas? {ok}. Faltando: {faltando}"

def calcular_vr(base_dir: str, out_path: Optional[str] = None) -> str:
    dfs = carregar_bases(base_dir)

    ativos = dfs["ativos"].copy()
    admis  = dfs["admis"].copy()
    ferias = dfs["ferias"].copy()
    deslig = dfs["deslig"].copy()
    afast  = dfs["afast"].copy()
    apr    = dfs["apr"].copy()
    estag  = dfs["estag"].copy()
    ext    = dfs["ext"].copy()
    dias   = dfs["dias"].copy()
    sxv    = dfs["sxv"].copy()

    # Normalizações básicas
    for col in ["MATRICULA"]:
        for df in [ativos, admis, ferias, afast, apr, estag]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    if "Cadastro" in ext.columns:
        ext["Cadastro"] = pd.to_numeric(ext["Cadastro"], errors="coerce").astype("Int64")

    if "Admissão" in admis.columns:
        admis["Admissão"] = pd.to_datetime(admis["Admissão"], errors="coerce").dt.date
    if "DIAS DE FÉRIAS" in ferias.columns:
        ferias["DIAS DE FÉRIAS"] = pd.to_numeric(ferias["DIAS DE FÉRIAS"], errors="coerce").fillna(0)

    dias["DIAS_UTEIS"] = pd.to_numeric(dias["DIAS_UTEIS"], errors="coerce")
    sxv["VALOR"] = pd.to_numeric(sxv["VALOR"], errors="coerce")

    # Chaves de junção
    ativos["ESTADO"] = ativos["Sindicato"].astype(str).apply(_estado_from_sind)
    ativos["SIND_KEY"] = ativos["Sindicato"].astype(str).apply(_sindicato_key)
    dias["SIND_KEY"] = dias["SINDICATO"].astype(str).str.upper().apply(_sindicato_key)

    base = ativos.merge(dias[["SIND_KEY", "DIAS_UTEIS"]], on="SIND_KEY", how="left")

    # Exclusões
    excluir = set()
    if "MATRICULA" in apr.columns:   excluir |= set(apr["MATRICULA"].dropna())
    if "MATRICULA" in estag.columns: excluir |= set(estag["MATRICULA"].dropna())
    if "MATRICULA" in afast.columns: excluir |= set(afast["MATRICULA"].dropna())
    if "Cadastro" in ext.columns:    excluir |= set(ext["Cadastro"].dropna())

    mask_dir = ativos["TITULO DO CARGO"].astype(str).str.upper().str.contains("DIRETOR", na=False)
    base = base[~base["MATRICULA"].isin(excluir)]
    base = base[~mask_dir.reindex(base.index, fill_value=False)]

    # Férias
    ferias_sum = ferias.groupby("MATRICULA", as_index=False)["DIAS DE FÉRIAS"].sum()
    base = base.merge(ferias_sum, on="MATRICULA", how="left")
    base["DIAS DE FÉRIAS"] = base["DIAS DE FÉRIAS"].fillna(0)
    base["DIAS_COMPRAR_INICIAL"] = base["DIAS_UTEIS"].fillna(0) - base["DIAS DE FÉRIAS"]
    base.loc[base["DIAS_COMPRAR_INICIAL"] < 0, "DIAS_COMPRAR_INICIAL"] = 0

    # Admissão proporcional dentro do período
    admis["Admissão"] = pd.to_datetime(admis["Admissão"], errors="coerce").dt.date
    admis_period = admis[(admis["Admissão"] >= PERIOD_START) & (admis["Admissão"] <= PERIOD_END)]
    base = base.merge(admis_period[["MATRICULA", "Admissão"]], on="MATRICULA", how="left")

    total_period_bd = np.busday_count(PERIOD_START, PERIOD_END)
    base["DIAS_ADMISSAO"] = 0
    mask_adm = base["Admissão"].notna()
    if mask_adm.any():
        base.loc[mask_adm, "DIAS_ADMISSAO"] = [
            np.busday_count(max(a, PERIOD_START), PERIOD_END) for a in base.loc[mask_adm, "Admissão"]
        ]
    base["DIAS_APOS_ADMISSAO_PROP"] = np.where(
        mask_adm,
        (base["DIAS_COMPRAR_INICIAL"] * (base["DIAS_ADMISSAO"] / max(1, total_period_bd))).round().astype("Int64"),
        base["DIAS_COMPRAR_INICIAL"]
    )

    deslig = deslig.rename(columns={c: c.strip() for c in deslig.columns})
    deslig["MATRICULA"] = pd.to_numeric(deslig["MATRICULA"], errors="coerce").astype("Int64")
    if "DATA DEMISSÃO" in deslig.columns:
        base = base.merge(
            deslig[["MATRICULA", "DATA DEMISSÃO", "COMUNICADO DE DESLIGAMENTO"]],
            on="MATRICULA", how="left"
        )

    def _dias_pos_deslig(row):
        d = row.get("DATA DEMISSÃO", pd.NA)
        if pd.isna(d):
            return int(row["DIAS_APOS_ADMISSAO_PROP"])
        d_date = pd.to_datetime(d).date()
        if str(row.get("COMUNICADO DE DESLIGAMENTO", "")).upper() == "OK" and d_date <= PERIOD_END:
            return 0
        start = PERIOD_START
        end = min(d_date, PERIOD_END)
        dias_u = np.busday_count(start, end)
        prop = int(round(row["DIAS_APOS_ADMISSAO_PROP"] * (dias_u / max(1, total_period_bd))))
        return min(prop, int(row["DIAS_APOS_ADMISSAO_PROP"]))

    if "DATA DEMISSÃO" in base.columns:
        base["DIAS_FINAIS"] = base.apply(_dias_pos_deslig, axis=1).astype(int)
    else:
        base["DIAS_FINAIS"] = base["DIAS_APOS_ADMISSAO_PROP"].fillna(0).astype(int)

    base.loc[base["DIAS_FINAIS"] < 0, "DIAS_FINAIS"] = 0
    base = base.merge(sxv, on="ESTADO", how="left").rename(columns={"VALOR": "VALOR_DIA"})
    base["VALOR_DIA"] = base["VALOR_DIA"].fillna(0.0)
    base["VALOR_VR"] = (base["DIAS_FINAIS"] * base["VALOR_DIA"]).round(2)
    base["EMPRESA_R$"] = (base["VALOR_VR"] * 0.80).round(2)
    base["COLAB_R$"]   = (base["VALOR_VR"] * 0.20).round(2)

    out_cols = [
        "MATRICULA","EMPRESA","TITULO DO CARGO","Sindicato","ESTADO",
        "DIAS_UTEIS","DIAS DE FÉRIAS","Admissão","DATA DEMISSÃO","COMUNICADO DE DESLIGAMENTO",
        "DIAS_FINAIS","VALOR_DIA","VALOR_VR","EMPRESA_R$","COLAB_R$"
    ]
    saida = base[out_cols].copy()

    # Caminho de saída
    if out_path is None:
        out_path = os.path.join(base_dir, "VR_MENSAL_CALCULADO.xlsx")

    saida.to_excel(out_path, index=False)
    return out_path

def tool_listar_arquivos(base_dir: str) -> str:
    files = [f for f in os.listdir(base_dir) if f.lower().endswith((".xlsx", ".xls"))]
    return f"Arquivos .xlsx/.xls encontrados ({len(files)}): {files}"

def tool_validar_dados(base_dir: str) -> str:
    return validar_ativos_colunas(base_dir)

def tool_rodar_calculo(args: str) -> str:
    """
    args: "BASE_DIR|OUT_PATH"  (OUT_PATH é opcional)
    """
    parts = [p.strip() for p in str(args).split("|")]
    base_dir = parts[0]
    out_path = parts[1] if len(parts) > 1 and parts[1] else None
    res = calcular_vr(base_dir, out_path)
    return f"Planilha gerada em: {res}"
