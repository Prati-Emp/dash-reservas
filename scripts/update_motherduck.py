import os
import pandas as pd
import duckdb
from datetime import datetime
from dotenv import load_dotenv

def get_motherduck_connection():
    """Create a connection to MotherDuck"""
    token = os.environ.get('MOTHERDUCK_TOKEN', '').strip()
    print("\nDebug - Verificando token do MotherDuck:")
    print(f"Token encontrado: {'Sim' if token else 'Não'}")
    
    if not token:
        print("Variáveis de ambiente disponíveis:", list(os.environ.keys()))
        raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
    
    # Remover qualquer caractere especial ou espaço do token
    token = token.strip().strip('"').strip("'")
    
    # Configurar a conexão DuckDB primeiro
    duckdb.sql("INSTALL motherduck")
    duckdb.sql("LOAD motherduck")
    
    try:
        # Configurar o token antes de conectar
        os.environ['motherduck_token'] = token
        
        # Tentar conexão
        conn = duckdb.connect('md:reservas')
        print("Conexão estabelecida com sucesso!")
        return conn
    except Exception as e:
        print(f"\nErro na conexão com MotherDuck:")
        print(f"- Erro original: {str(e)}")
        print("- Verifique se o token está correto")
        raise
    
    try:
        return duckdb.connect(connection_string)
    except Exception as e:
        print(f"\nErro na conexão com MotherDuck:")
        print(f"- Erro original: {str(e)}")
        print("- Verifique se o token está correto no arquivo .env")
        print("- Certifique-se que o token não tem espaços extras ou caracteres inválidos")
        raise

def clean_currency(value):
    """Remove R$ e converte para número"""
    if isinstance(value, str):
        return float(value.replace('R$ ', '').replace('.', '').replace(',', '.'))
    return value

def validate_dataframe(df, name):
    """Validate DataFrame content"""
    if df.empty:
        raise ValueError(f"DataFrame {name} está vazio")
    print(f"\nValidando DataFrame {name}:")
    print(f"- Número de linhas: {len(df)}")
    print(f"- Colunas: {', '.join(df.columns)}")
    print(f"- Primeiras linhas:\n{df.head()}\n")

def update_motherduck():
    try:
        print("Iniciando atualização do MotherDuck...")
        
        # Verificar carregamento do .env
        print("\nVerificando configuração do ambiente:")
        load_dotenv(verbose=True)  # Adiciona mais informações sobre o carregamento do .env
        print("\nObtendo dados das APIs...")
        import reservas
        import workflow
        
        # Obter dados diretamente das APIs
        dados_reservas = reservas.obter_todos_dados()
        dados_workflow = workflow.obter_todos_dados()
        
        # Converter para DataFrames
        reservas_df = pd.DataFrame(dados_reservas)
        workflow_df = pd.DataFrame(dados_workflow)
        
        if reservas_df.empty or workflow_df.empty:
            raise ValueError("Não foram encontrados dados para atualizar")
        
        # Validar os DataFrames
        validate_dataframe(reservas_df, "reservas")
        validate_dataframe(workflow_df, "workflow")
        
        # Limpar os valores monetários
        if 'valor_contrato' in reservas_df.columns:
            print("\nProcessando valores monetários...")
            reservas_df['valor_contrato'] = reservas_df['valor_contrato'].apply(clean_currency)
        
        # Conectar ao MotherDuck e atualizar as tabelas
        print("\nConectando ao MotherDuck...")
        conn = get_motherduck_connection()
        
        # Criar schema se não existir
        print("\nVerificando/criando schema...")
        conn.sql("CREATE SCHEMA IF NOT EXISTS reservas.main")
          # Atualizar tabelas com validação
        print("\nAtualizando tabelas no MotherDuck...")
        
        try:
            print("- Removendo tabelas antigas...")
            conn.sql("DROP TABLE IF EXISTS reservas.main.reservas_abril")
            conn.sql("DROP TABLE IF EXISTS reservas.main.workflow_abril")
            
            print("- Criando novas tabelas...")
            conn.execute("CREATE TABLE reservas.main.reservas_abril AS SELECT * FROM reservas_df")
            conn.execute("CREATE TABLE reservas.main.workflow_abril AS SELECT * FROM workflow_df")
            
            # Validar se as tabelas foram criadas corretamente
            print("\nValidando tabelas criadas...")
            reservas_count = conn.sql("SELECT COUNT(*) as count FROM reservas.main.reservas_abril").fetchone()[0]
            workflow_count = conn.sql("SELECT COUNT(*) as count FROM reservas.main.workflow_abril").fetchone()[0]
            
            print(f"- Registros em reservas_abril: {reservas_count}")
            print(f"- Registros em workflow_abril: {workflow_count}")
            
            if reservas_count == 0 or workflow_count == 0:
                raise ValueError("Uma ou mais tabelas foram criadas vazias!")
            
            print("\nDados atualizados com sucesso no MotherDuck!")
            
        except Exception as e:
            print(f"\nErro ao atualizar tabelas: {str(e)}")
            print("Tentando reverter alterações...")
            try:
                conn.sql("DROP TABLE IF EXISTS reservas.main.reservas_abril")
                conn.sql("DROP TABLE IF EXISTS reservas.main.workflow_abril")
            except:
                pass
            raise e
            
    except Exception as e:
        print(f"\nErro durante a atualização: {str(e)}")
        raise e
    finally:
        try:
            conn.close()
            print("\nConexão com MotherDuck fechada.")
        except:
            pass

if __name__ == "__main__":
    update_motherduck()
