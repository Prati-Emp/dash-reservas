import duckdb
import pandas as pd

MOTHERDUCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InByYXRpcHJvamV0b3NAZ21haWwuY29tIiwic2Vzc2lvbiI6InByYXRpcHJvamV0b3MuZ21haWwuY29tIiwicGF0IjoiUnA1clVla2JwRFY4OFp2d3RKNWxkOFhxdmtpSFQzRlNacWdXbXFsQ09WMCIsInVzZXJJZCI6ImFkZThmZGM0LTc1MDktNGU4Ny1hZTcwLTMwZGVkMTQ4Y2RlOSIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc0OTA2ODI4N30.TEUsvAxCKXhzNrb7WAok0jL2YmqEEtrxaEOKZZ6tuBI"

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
