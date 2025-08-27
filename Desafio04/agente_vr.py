import os
from langchain.agents import Tool, initialize_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from tools_vr import (
    tool_listar_arquivos,
    tool_validar_dados,
    tool_rodar_calculo,
)

load_dotenv()

SYSTEM_PROMPT = """Você é um agente especializado em folha de pagamento de VR/VA.
Seu trabalho é:
1) Listar os arquivos disponíveis na pasta indicada;
2) Validar se ATIVOS.xlsx contém colunas mínimas;
3) Rodar o cálculo e gerar a planilha final Excel.

Sempre explique de forma curta o que está fazendo antes de chamar cada ferramenta.
Se o usuário pedir explicações adicionais (por ex., por que um colaborador ficou com 0 dias), responda
em linguagem simples, usando o resultado calculado.
"""

class AgenteVR:
    """Agente especializado em processamento de VR/VA."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Inicializa o agente VR.
        
        Args:
            model_name: Nome do modelo OpenAI a ser utilizado
        """
        self.model_name = model_name
        self.agent = self._build_agente()
    
    def _build_agente(self):
        """Constrói e retorna o agente LangChain."""
        llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        tools = [
            Tool(
                name="ListarArquivos",
                func=tool_listar_arquivos,
                description="Lista os arquivos .xlsx/.xls existentes na pasta de entrada. Input = caminho da pasta",
            ),
            Tool(
                name="ValidarDados",
                func=tool_validar_dados,
                description="Valida se ATIVOS.xlsx contém as colunas mínimas. Input = caminho da pasta",
            ),
            Tool(
                name="CalcularVR",
                func=tool_rodar_calculo,
                description="Gera a planilha final VR. Input = 'BASE_DIR|OUT_PATH(opcional)'",
            ),
        ]
        
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent="zero-shot-react-description",
            verbose=True,
            system_message=SYSTEM_PROMPT,
        )
        return agent
    
    def listar_arquivos(self, base_dir: str) -> str:
        """Lista arquivos na pasta especificada."""
        return self.agent.run(f'Liste os arquivos usando a ferramenta ListarArquivos com a pasta "{base_dir}".')
    
    def validar_dados(self, base_dir: str) -> str:
        """Valida os dados da planilha ATIVOS."""
        return self.agent.run(f'Valide os dados usando a ferramenta ValidarDados com a pasta "{base_dir}".')
    
    def calcular_vr(self, base_dir: str, out_path: str = None) -> str:
        """Executa o cálculo de VR e gera a planilha final."""
        if out_path:
            return self.agent.run(f'Gere a planilha final com a ferramenta CalcularVR usando "{base_dir}|{out_path}"')
        else:
            return self.agent.run(f'Gere a planilha final com a ferramenta CalcularVR usando "{base_dir}"')
    
    def executar_fluxo_completo(self, base_dir: str, out_path: str = None) -> dict:
        """
        Executa o fluxo completo de processamento de VR.
        
        Returns:
            Dict com os resultados de cada etapa
        """
        resultados = {}
        
        resultados['listagem'] = self.listar_arquivos(base_dir)
        resultados['validacao'] = self.validar_dados(base_dir)
        resultados['calculo'] = self.calcular_vr(base_dir, out_path)
        
        return resultados