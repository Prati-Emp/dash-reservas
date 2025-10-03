import duckdb
import pandas as pd

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InByYXRpcHJvamV0b3NAZ21haWwuY29tIiwic2Vzc2lvbiI6InByYXRpcHJvamV0b3MuZ21haWwuY29tIiwicGF0IjoiUnA1clVla2JwRFY4OFp2d3RKNWxkOFhxdmtpSFQzRlNacWdXbXFsQ09WMCIsInVzZXJJZCI6ImFkZThmZGM0LTc1MDktNGU4Ny1hZTcwLTMwZGVkMTQ4Y2RlOSIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc0OTA2ODI4N30.TEUsvAxCKXhzNrb7WAok0jL2YmqEEtrxaEOKZZ6tuBI"

con = duckdb.connect(f"md:reservas?token={token}")

# Unique imobiliarias
df = con.execute("SELECT DISTINCT Imobiliaria FROM cv_leads").df()
print("Imobiliarias únicas:")
print(df)

# Count vendas por imobiliaria
df_vendas = con.execute("""
SELECT Imobiliaria, COUNT(*) as vendas
FROM cv_leads
WHERE Situacao = 'Venda Realizada'
GROUP BY Imobiliaria
""").df()
print("Vendas por imobiliaria:")
print(df_vendas)

con.close()
