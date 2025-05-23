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
    """Format currency value to Brazilian Real format with MI (millions) or MIL (thousands)"""
    try:
        if value >= 1_000_000:  # Se for 1 milhão ou mais
            return f"R$ {value/1_000_000:.1f}Mi".replace(".", ",")
        elif value >= 1_000:  # Se for 1 mil ou mais
            return f"R$ {value/1_000:.1f}Mil".replace(".", ",")
        else:
            return f"R$ {value:.1f}".replace(".", ",")
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
    
    # Buscar todas as reservas
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
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

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

# Aplicar filtros
df_filtrado = reservas_df[
    (reservas_df['data_cad'].dt.date >= data_inicio) & 
    (reservas_df['data_cad'].dt.date <= data_fim)
].copy()

# Aplicar filtro de empreendimento se selecionado
if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_vendas = len(df_filtrado[df_filtrado['situacao'] == 'Vendida'])
    st.metric("Total de Vendas", f"{total_vendas:,}")

with col2:
    valor_total = df_filtrado[df_filtrado['situacao'] == 'Vendida']['valor_contrato'].sum()
    st.metric("Valor Total em Vendas", format_currency(valor_total))

with col3:
    # Calcular taxa house (% de vendas internas)
    vendas_internas = len(df_filtrado[(df_filtrado['situacao'] == 'Vendida') & (df_filtrado['tipo_venda_origem'] == 'Venda Interna (Prati)')])
    taxa_house = (vendas_internas / total_vendas * 100) if total_vendas > 0 else 0
    st.metric("Taxa House", f"{taxa_house:.1f}%")

with col4:
    tempo_medio_geral = int(df_filtrado['tempo_ate_venda'].mean().round(0))
    st.metric("Tempo Médio até Venda", f"{tempo_medio_geral} dias")

# Análise por tipo de venda (Interna vs Externa)
st.subheader("Análise por Origem da Venda")

# Filtrar apenas vendas efetivas
df_vendas = df_filtrado[df_filtrado['situacao'] == 'Vendida']

analise_origem = df_vendas.groupby('tipo_venda_origem').agg({
    'idreserva': 'count',
    'valor_contrato': 'sum',
    'tempo_ate_venda': 'mean'
}).reset_index()

analise_origem.columns = ['Origem', 'Quantidade', 'Valor Total', 'Tempo Médio (dias)']
analise_origem['Valor Total'] = analise_origem['Valor Total'].apply(format_currency)
analise_origem['Tempo Médio (dias)'] = analise_origem['Tempo Médio (dias)'].round(0).astype(int)

st.table(analise_origem)

# Análise estratificada por empreendimento e tipo de venda
st.subheader("Estratificação por Tipo de Venda")

# Criar DataFrames separados para cada métrica
# Usar apenas vendas efetivas
df_vendas = df_filtrado[df_filtrado['situacao'] == 'Vendida']

quantidade = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='idreserva',
    aggfunc='count',
    fill_value=0
).reset_index()

valor = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='valor_contrato',
    aggfunc='sum',
    fill_value=0
).reset_index()

tempo = df_vendas.pivot_table(
    index='empreendimento',
    columns='tipo_venda_origem',
    values='tempo_ate_venda',
    aggfunc='mean',
    fill_value=0
).reset_index()

# Criar DataFrame final
estratificacao = pd.DataFrame()
estratificacao['Empreendimento'] = quantidade['empreendimento']
estratificacao['Quantidade (Interna)'] = quantidade['Venda Interna (Prati)']
estratificacao['Quantidade (Externa)'] = quantidade['Venda Externa (Imobiliárias)']
estratificacao['Valor Total (Interna)'] = valor['Venda Interna (Prati)']
estratificacao['Valor Total (Externa)'] = valor['Venda Externa (Imobiliárias)']
estratificacao['Tempo Médio (Interna)'] = tempo['Venda Interna (Prati)']
estratificacao['Tempo Médio (Externa)'] = tempo['Venda Externa (Imobiliárias)']

# Formatar valores
estratificacao['Valor Total (Interna)'] = estratificacao['Valor Total (Interna)'].apply(format_currency)
estratificacao['Valor Total (Externa)'] = estratificacao['Valor Total (Externa)'].apply(format_currency)
estratificacao['Tempo Médio (Interna)'] = estratificacao['Tempo Médio (Interna)'].round(0).astype(int)
estratificacao['Tempo Médio (Externa)'] = estratificacao['Tempo Médio (Externa)'].round(0).astype(int)

# Calcular e adicionar linha de totais
totais = pd.DataFrame([{
    'Empreendimento': 'Total',
    'Quantidade (Interna)': df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Interna (Prati)']['idreserva'].count(),
    'Quantidade (Externa)': df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']['idreserva'].count(),
    'Valor Total (Interna)': format_currency(df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Interna (Prati)']['valor_contrato'].sum()),
    'Valor Total (Externa)': format_currency(df_vendas[df_vendas['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']['valor_contrato'].sum()),'Tempo Médio (Interna)': int(df_filtrado[df_filtrado['tipo_venda_origem'] == 'Venda Interna (Prati)']['tempo_ate_venda'].mean().round(0)),
    'Tempo Médio (Externa)': int(df_filtrado[df_filtrado['tipo_venda_origem'] == 'Venda Externa (Imobiliárias)']['tempo_ate_venda'].mean().round(0))
}])

estratificacao = pd.concat([estratificacao, totais], ignore_index=True)

# Remover a ordenação para manter a ordem original dos empreendimentos
estratificacao = estratificacao.copy()

st.table(estratificacao)

# Análise de conversão de reservas em vendas
st.subheader("Taxa de Conversão de Reservas em Vendas")

# Calcular taxas de conversão para vendas internas e externas
def calcular_taxa_conversao(df, tipo_venda):
    total_reservas = len(df[df['tipo_venda_origem'] == tipo_venda])
    total_vendas = len(df[(df['tipo_venda_origem'] == tipo_venda) & (df['situacao'] == 'Vendida')])
    taxa = (total_vendas / total_reservas * 100) if total_reservas > 0 else 0
    return pd.Series({
        'Total Reservas': total_reservas,
        'Total Vendas': total_vendas,
        'Taxa de Conversão': taxa
    })

# Criar DataFrame de conversão
conversao_interna = calcular_taxa_conversao(df_filtrado, 'Venda Interna (Prati)')
conversao_externa = calcular_taxa_conversao(df_filtrado, 'Venda Externa (Imobiliárias)')

conversao_df = pd.DataFrame({
    'Métricas': ['Total Reservas', 'Total Vendas', 'Taxa de Conversão'],
    'Venda Interna': [
        f"{conversao_interna['Total Reservas']:,}",
        f"{conversao_interna['Total Vendas']:,}",
        f"{conversao_interna['Taxa de Conversão']:.1f}%"
    ],
    'Venda Externa': [
        f"{conversao_externa['Total Reservas']:,}",
        f"{conversao_externa['Total Vendas']:,}",
        f"{conversao_externa['Taxa de Conversão']:.1f}%"
    ]
})

st.table(conversao_df)


