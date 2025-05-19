import os
import pandas as pd
import duckdb
from datetime import datetime

def get_motherduck_connection():
    """Create a connection to MotherDuck"""
    token = os.getenv('MOTHERDUCK_TOKEN')
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
    return duckdb.connect('md:reservas?motherduck_token=' + token)

def clean_currency(value):
    """Remove R$ e converte para número"""
    if isinstance(value, str):
        return float(value.replace('R$ ', '').replace('.', '').replace(',', '.'))
    return value

def update_motherduck():
    try:
        print("Iniciando atualização do MotherDuck...")
        
        # Executar os scripts de atualização
        import reservas
        import workflow
        print("Dados atualizados dos sistemas externos")
        
        # Ler os arquivos CSV gerados
        reservas_df = pd.read_csv('reservas_abril.csv')
        workflow_df = pd.read_csv('workflow_abril.csv')
        
        # Limpar os valores monetários
        if 'valor_contrato' in reservas_df.columns:
            reservas_df['valor_contrato'] = reservas_df['valor_contrato'].apply(clean_currency)
        
        # Conectar ao MotherDuck e atualizar as tabelas
        conn = get_motherduck_connection()
        
        # Criar schema se não existir
        conn.sql("CREATE SCHEMA IF NOT EXISTS reservas.main")
        
        # Atualizar tabelas
        conn.sql("DROP TABLE IF EXISTS reservas.main.reservas_abril")
        conn.sql("DROP TABLE IF EXISTS reservas.main.workflow_abril")
        
        # Criar novas tabelas com os dados atualizados
        conn.execute("CREATE TABLE reservas.main.reservas_abril AS SELECT * FROM reservas_df")
        conn.execute("CREATE TABLE reservas.main.workflow_abril AS SELECT * FROM workflow_df")
        
        print("Dados atualizados com sucesso no MotherDuck!")
        
    except Exception as e:
        print(f"Erro durante a atualização: {str(e)}")
        raise e

if __name__ == "__main__":
    update_motherduck()
