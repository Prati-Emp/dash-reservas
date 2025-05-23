import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import display_logo
import pandas as pd
from datetime import datetime
import plotly.express as px
import locale
import duckdb
from dotenv import load_dotenv
import os

# Configuração da página
st.set_page_config(page_title="Análise de Vendas", layout="wide")

# Mostrar logo
display_logo()

# Carregar variáveis de ambiente
load_dotenv()

# Configurar locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR')
        except locale.Error:
            pass

def format_currency(value):
    """Format currency value to Brazilian Real format"""
    try:
        return f"R$ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {value}"

# MotherDuck connection
@st.cache_resource
def get_motherduck_connection():
    """Create a cached connection to MotherDuck"""
    try:
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
        
        # Sanitize o token
        token = token.strip().strip('"').strip("'")
        
        # Conectar diretamente ao MotherDuck com o token na URL (formato para conta free)
        connection_string = f'motherduck:reservas?motherduck_token={token}'
        
        try:
            conn = duckdb.connect(connection_string)
            return conn
        except Exception as e:
            st.error(f"Erro na conexão com MotherDuck: {str(e)}")
            raise
    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

# Carregando os dados
@st.cache_data
def load_data():
    conn = get_motherduck_connection()
    
    # Buscar apenas reservas vendidas
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
        WHERE situacao = 'Vendida'
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    
    # Calcular tempo até a venda (em dias)
    reservas_df['tempo_ate_venda'] = (reservas_df['data_ultima_alteracao_situacao'] - reservas_df['data_cad']).dt.days
    
    # Identificar vendas internas (Prati) e externas (outras imobiliárias)
    reservas_df['tipo_venda_origem'] = reservas_df['imobiliaria'].apply(
        lambda x: 'Venda Interna (Prati)' if 'PRATI' in str(x).upper() else 'Venda Externa (Imobiliárias)'
    )
    
    return reservas_df

# Título do aplicativo
st.title("📈 Análise de Vendas")

# Carregar dados
reservas_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de data
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-01-01'),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date)
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max(reservas_df['data_cad'].dt.date),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date)
)

# Aplicar filtros de data
df_filtrado = reservas_df[
    (reservas_df['data_cad'].dt.date >= data_inicio) & 
    (reservas_df['data_cad'].dt.date <= data_fim)
].copy()

# Métricas principais
col1, col2, col3 = st.columns(3)

with col1:
    total_vendas = len(df_filtrado)
    st.metric("Total de Vendas", f"{total_vendas:,}")

with col2:
    valor_total = df_filtrado['valor_contrato'].sum()
    st.metric("Valor Total em Vendas", format_currency(valor_total))

with col3:
    tempo_medio_geral = df_filtrado['tempo_ate_venda'].mean()
    st.metric("Tempo Médio até Venda", f"{tempo_medio_geral:.1f} dias")

# Análise por tipo de venda (Interna vs Externa)
st.subheader("Análise por Origem da Venda")

analise_origem = df_filtrado.groupby('tipo_venda_origem').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum',
    'tempo_ate_venda': 'mean'
}).reset_index()

analise_origem.columns = ['Origem', 'Quantidade', 'Valor Total', 'Tempo Médio (dias)']
analise_origem['Valor Total'] = analise_origem['Valor Total'].apply(format_currency)
analise_origem['Tempo Médio (dias)'] = analise_origem['Tempo Médio (dias)'].round(1)

st.table(analise_origem)

# Gráfico de distribuição de vendas
st.subheader("Distribuição de Vendas por Origem")

fig = px.pie(df_filtrado, 
             names='tipo_venda_origem', 
             values='valor_contrato',
             title='Distribuição do Valor Total de Vendas por Origem')
st.plotly_chart(fig, use_container_width=True)

# Tempo médio de vendas por tipo
st.subheader("Tempo Médio até a Venda por Origem")

fig_tempo = px.bar(analise_origem, 
                  x='Origem', 
                  y='Tempo Médio (dias)',
                  text='Tempo Médio (dias)')
fig_tempo.update_traces(texttemplate='%{text:.1f} dias', textposition='outside')
st.plotly_chart(fig_tempo, use_container_width=True)

# Análise detalhada por imobiliária
st.subheader("Análise por Imobiliária")

analise_imobiliaria = df_filtrado.groupby('imobiliaria').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum',
    'tempo_ate_venda': 'mean'
}).reset_index()

analise_imobiliaria.columns = ['Imobiliária', 'Quantidade', 'Valor Total', 'Tempo Médio (dias)']
analise_imobiliaria['Valor Total'] = analise_imobiliaria['Valor Total'].apply(format_currency)
analise_imobiliaria['Tempo Médio (dias)'] = analise_imobiliaria['Tempo Médio (dias)'].round(1)
analise_imobiliaria = analise_imobiliaria.sort_values('Quantidade', ascending=False)

st.table(analise_imobiliaria)

# Análise de desempenho mensal
st.subheader("Desempenho Mensal")

df_filtrado['mes_venda'] = df_filtrado['data_ultima_alteracao_situacao'].dt.strftime('%Y-%m')
vendas_mensais = df_filtrado.groupby('mes_venda').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum'
}).reset_index()

vendas_mensais.columns = ['Mês', 'Quantidade', 'Valor Total']
vendas_mensais['Valor Total'] = vendas_mensais['Valor Total'].apply(format_currency)

st.table(vendas_mensais)
