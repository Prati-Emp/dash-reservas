import duckdb
import pandas as pd


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
