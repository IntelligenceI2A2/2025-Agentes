from processamento import ProcessadorVR
from carregamento import CarregadorDados
import os
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

class AgenteVR:
    def __init__(self, model_path: str):
        """
        Implementação LLMChain + Structured Output
        """
        self.model_path = model_path
        self.llm = self._setup_llm()
        self.output_parser = self._setup_output_parser()
        self.prompt = self._setup_prompt()
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def _setup_llm(self):
        """Configura o modelo LLaMA"""
        return LlamaCpp(
            model_path=self.model_path,
            temperature=0.1,
            n_ctx=4096,
            max_tokens=256,
            n_gpu_layers=40,
            n_batch=128,
            verbose=False,
        )
    
    def _setup_output_parser(self):
        """Configura o parser de saída estruturada"""
        response_schemas = [
            ResponseSchema(name="thought", description="Breve pensamento do assistente"),
            ResponseSchema(name="action", description="Ação a ser executada: ListarArquivos, ValidarDados, ProcessarVR"),
            ResponseSchema(name="action_input", description="Input para a ação, sempre entre aspas")
        ]
        return StructuredOutputParser.from_response_schemas(response_schemas)
    
    def _setup_prompt(self):
        """Configura o prompt template"""
        template = """Você é um assistente especializado em processamento de VR. 

        Ferramentas disponíveis:
        - ListarArquivos: Lista arquivos Excel. Input: "caminho_da_pasta"
        - ValidarDados: Valida dados de VR. Input: "caminho_da_pasta"  
        - ProcessarVR: Processa dados e gera planilha. Input: "caminho_pasta|caminho_saida"

        Siga EXATAMENTE este formato:
        {format_instructions}

        Exemplos:
        Pergunta: Liste os arquivos em dados/
        Resposta: {{"thought": "Preciso listar arquivos", "action": "ListarArquivos", "action_input": "dados/"}}

        Pergunta: Processe os dados de dados/ e salve em saida/saida.xlsx
        Resposta: {{"thought": "Preciso processar VR", "action": "ProcessarVR", "action_input": "dados/|saida/saida.xlsx"}}

        Pergunta: {input}
        Resposta:"""

        return PromptTemplate(
            template=template,
            input_variables=["input"],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
    
    def _tool_listar_arquivos(self, caminho_pasta: str) -> str:
        """Lista arquivos Excel"""
        caminho_pasta = caminho_pasta.strip('"\'')
        if not os.path.exists(caminho_pasta):
            return f"Erro: Pasta '{caminho_pasta}' não existe"
        
        arquivos = [f for f in os.listdir(caminho_pasta) if f.lower().endswith(('.xlsx', '.xls'))]
        return f"Arquivos encontrados: {', '.join(arquivos)}"
    
    def _tool_validar_dados(self, caminho_pasta: str) -> str:
        """Valida dados de VR"""
        caminho_pasta = caminho_pasta.strip('"\'')
        if not os.path.exists(caminho_pasta):
            return f"Erro: Pasta '{caminho_pasta}' não existe"
        
        arquivos = [f for f in os.listdir(caminho_pasta) if f.lower().endswith(('.xlsx', '.xls'))]
        return f"Pasta válida com {len(arquivos)} arquivos Excel"
    
    def _tool_processar_vr(self, input_str: str) -> str:
        """Processa dados de VR"""
        try:
            if '|' in input_str:
                base_dir, output_path = input_str.split('|', 1)
                base_dir = base_dir.strip('"\'')
                output_path = output_path.strip('"\'')
            else:
                base_dir = input_str.strip('"\'')
                output_path = os.path.join(base_dir, "VR_CALCULADO.xlsx")
            
            if not os.path.exists(base_dir):
                return f"Erro: Pasta '{base_dir}' não existe"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            carregador = CarregadorDados(base_dir)
            dados = carregador.carregar_todas_planilhas()
            dados["dias"] = carregador.limpar_dias_uteis(dados["dias"])
            dados["deslig"] = carregador.limpar_desligados(dados["deslig_raw"])
            dados["ext"] = carregador.limpar_exterior(dados["ext_raw"])
            dados["sxv"] = carregador.limpar_sindicato_valor(dados["sxv"])
            
            processador = ProcessadorVR(dados)
            caminho_saida = processador.processar(output_path)
            
            return f"Processamento concluído! Arquivo: {caminho_saida}"
            
        except Exception as e:
            return f"Erro: {str(e)}"
    
    def executar_comando(self, comando: str) -> str:
        """Executa um comando e retorna a resposta da tool"""
        try:
            resposta = self.chain.run(input=comando)
            parsed = self.output_parser.parse(resposta)
            
            action = parsed["action"]
            action_input = parsed["action_input"]
            
            print(f"Agente:  {parsed['thought']}")
            print(f"Executando: {action} com input: {action_input}")
            
            # Executa a tool correspondente
            if action == "ListarArquivos":
                return self._tool_listar_arquivos(action_input)
            elif action == "ValidarDados":
                return self._tool_validar_dados(action_input)
            elif action == "ProcessarVR":
                return self._tool_processar_vr(action_input)
            else:
                return f"Ação desconhecida: {action}"
                
        except Exception as e:
            return f"Erro: {str(e)}"