import time
import requests
from typing import List, Dict

class IntegradorAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def enviar_notas(self, notas_fiscais: List[Dict]) -> None:
        for nota in notas_fiscais:
            resposta = requests.post(self.base_url, json=nota)
            if resposta.status_code == 201:
                print(f"Nota {nota['chave_acesso']} enviada com sucesso.")
            elif resposta.status_code == 200:
                print(f"Nota {nota['chave_acesso']} enviada com sucesso.")
                time.sleep(120)
            else:
                print(f"Erro ao enviar nota {nota['chave_acesso']}: {resposta.status_code} - {resposta.text}")
