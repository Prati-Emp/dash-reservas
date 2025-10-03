import duckdb
import pandas as pd


def test_columns():
    try:
        con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
        # Get column names
        columns_query = "DESCRIBE cv_leads"
        columns = con.execute(columns_query).df()
        print("Colunas da tabela cv_leads:")
        print(columns['column_name'].tolist())
        
        # Sample data
        sample_query = "SELECT * FROM cv_leads LIMIT 1"
        sample = con.execute(sample_query).df()
        print("\nDados de amostra (primeira linha):")
        print(sample.to_dict('records'))
        
        con.close()
    except Exception as e:
        print("Erro:", e)

if __name__ == "__main__":
    test_columns()
