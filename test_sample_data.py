import duckdb
import pandas as pd


def test_sample_data():
    try:
        con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
        
        # Unique Imobiliaria
        imobiliaria_query = "SELECT DISTINCT Imobiliaria FROM cv_leads"
        imobiliarias = con.execute(imobiliaria_query).df()
        print("Imobiliárias únicas:")
        print(imobiliarias['Imobiliaria'].tolist())
        
        # Sample gestor values
        gestor_query = "SELECT gestor, COUNT(*) as count FROM cv_leads GROUP BY gestor ORDER BY count DESC LIMIT 10"
        gestores = con.execute(gestor_query).df()
        print("\nAmostra de gestores (top 10 por contagem):")
        print(gestores.to_dict('records'))
        
        # Sample full row with date filter
        sample_query = """
        SELECT * FROM cv_leads 
        WHERE Data_cad >= '2025-01-01' AND Data_cad <= CURRENT_DATE 
        LIMIT 5
        """
        sample = con.execute(sample_query).df()
        print("\nAmostra de linhas com filtro de data (primeiras 5):")
        print(sample.to_dict('records'))
        
        con.close()
    except Exception as e:
        print("Erro:", e)

if __name__ == "__main__":
    test_sample_data()
