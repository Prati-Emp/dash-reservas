import requests
import time
import csv
import os

import sys
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

try:
    url = 'https://prati.cvcrm.com.br/api/v1/cvdw/reservas/workflow/tempo'
    headers = {
        "accept": "application/json",
        "email": os.environ.get('CVCRM_EMAIL', '').strip(),
        "token": os.environ.get('CVCRM_TOKEN', '').strip(),
    }
except Exception as e:
    print("Erro ao configurar credenciais. Verifique as variáveis de ambiente.")
    sys.exit(1)

# Data de corte - 01/01/2024
DATA_CORTE = datetime(2024, 1, 1)

def filtrar_por_data(dados):
    """Filtra dados a partir de 01/01/2024"""
    dados_filtrados = []
    for item in dados:
        try:
            data_str = item.get('referencia_data', '').split()[0]
            data_item = datetime.strptime(data_str, "%Y-%m-%d")
            if data_item >= DATA_CORTE:
                dados_filtrados.append(item)
        except (ValueError, AttributeError):
            continue
    return dados_filtrados

def obter_todos_dados():
    """Busca todos os dados paginados da API"""
    pagina = 25
    registros_por_pagina = 500
    todos_dados = []
    
    while True:
        try:
            params = {
                "pagina": pagina,
                "registros_por_pagina": registros_por_pagina
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            dados = response.json().get("dados", [])
            print(f"Página {pagina} - {len(dados)} registros")
            
            dados_filtrados = filtrar_por_data(dados)
            todos_dados.extend(dados_filtrados)
            
            if len(dados) < registros_por_pagina:
                break
                
            pagina += 1
            time.sleep(3)
            
        except Exception as e:
            print(f"Erro na página {pagina}: {str(e)}")
            break
            
    return todos_dados

def gerar_csv(dados, nome_arquivo='workflow_abril.csv'):
    """Gera arquivo CSV com os dados filtrados"""
    if not dados:
        print("Nenhum dado para exportar")
        return
    
    campos = list(dados[0].keys())
    
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(dados)
    
    print(f"Arquivo {nome_arquivo} gerado com {len(dados)} registros")

if __name__ == "__main__":
    print("Iniciando busca de dados a partir de 01/01/2024...")
    dados = obter_todos_dados()
    print(f"Total de registros encontrados: {len(dados)}")
    if dados:
        gerar_csv(dados)
    else:
        print("Nenhum registro encontrado após a data de corte")