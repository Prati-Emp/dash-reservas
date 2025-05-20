import streamlit as st

# Configuração da página
st.set_page_config(page_title="Imobiliária", layout="wide")

import pandas as pd
from datetime import datetime
import re
import requests
import locale
import duckdb
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

# Set locale to Brazilian Portuguese silently
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
    token = os.getenv('MOTHERDUCK_TOKEN')
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
    return duckdb.connect('md:reservas?motherduck_token=' + token)

# Carregando os dados
@st.cache_data
def load_data():
    conn = get_motherduck_connection()
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    
    return reservas_df

# Título do aplicativo
st.title("🏢 Imobiliária")

# Carregar e processar dados
reservas_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de data
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-04-01'),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date),
    key="data_inicio_filter"
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max(reservas_df['data_cad'].dt.date),
    min_value=min(reservas_df['data_cad'].dt.date),
    max_value=max(reservas_df['data_cad'].dt.date),
    key="data_fim_filter"
)

# Filtro de imobiliária
imobiliarias = sorted(reservas_df['imobiliaria'].unique())
imobiliaria_selecionada = st.sidebar.selectbox("Imobiliária", ["Todas"] + list(imobiliarias), key="imobiliaria_filter")

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos), key="empreendimento_filter")

# Aplicar todos os filtros
mask = (reservas_df['data_cad'].dt.date >= data_inicio) & (reservas_df['data_cad'].dt.date <= data_fim)
df_filtrado = reservas_df[mask].copy()

if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]
if imobiliaria_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['imobiliaria'] == imobiliaria_selecionada]

# Remover reservas canceladas e vendidas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida', 'Distrato'])]

# Métricas principais
col1, col2 = st.columns(2)

# Coluna da esquerda - Métricas totais
with col1:
    total_reservas = len(df_sem_canceladas_vendidas)
    valor_total = df_sem_canceladas_vendidas['valor_contrato'].sum()
    st.metric(label="Total de Reservas", value=int(total_reservas), help="Total de reservas ativas")
    st.metric(label="Valor Total", value=format_currency(valor_total))

# Coluna da direita - Métricas Prati
with col2:
    reservas_prati = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'].str.strip().str.upper() == 'PRATI EMPREENDIMENTOS']
    total_prati = len(reservas_prati)
    valor_prati = reservas_prati['valor_contrato'].sum()
    st.metric(label="Reservas Prati", value=int(total_prati), help="Total de reservas da Prati")
    st.metric(label="Valor Prati", value=format_currency(valor_prati))

def extract_days(situacao):
    # Extrai o número entre parênteses da situação
    match = re.search(r'\((\d+)\)', situacao)
    if match:
        return int(match.group(1))
    return 0

def check_time_limit(row):
    # Extrai o número entre parênteses da situação
    dias_limite = extract_days(row['situacao'])
    
    if dias_limite == 0:
        return False
        
    # Pega a data da última alteração
    data_ultima_alteracao = pd.to_datetime(row['data_ultima_alteracao_situacao'])
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (datetime.now() - data_ultima_alteracao).days
    
    # Verifica se o tempo desde a última alteração excede o limite
    return dias_decorridos >= dias_limite

# Verificar reservas fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
df_sem_canceladas_vendidas['dias_na_situacao'] = (datetime.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']).dt.days

# Análise por Imobiliária
st.subheader("Análise por Imobiliária")
analise_imobiliaria = df_sem_canceladas_vendidas.groupby('imobiliaria').agg({
    'idreserva': 'count',
    'fora_do_prazo': 'sum',
    'valor_contrato': 'sum',
    'dias_na_situacao': 'mean'
}).reset_index()

analise_imobiliaria.columns = ['Imobiliária', 'Total Reservas', 'Fora do Prazo', 'Valor Total', 'Média de Dias']
analise_imobiliaria['Média de Dias'] = analise_imobiliaria['Média de Dias'].round(1)
analise_imobiliaria['Valor Total'] = analise_imobiliaria['Valor Total'].apply(format_currency)

# Exibir tabela de análise por imobiliária
st.table(analise_imobiliaria)

# Análise comparativa Prati vs Outras Imobiliárias
st.subheader("Comparativo Prati vs Outras Imobiliárias")

# Separar dados Prati e outras imobiliárias
df_prati = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'] == 'PRATI EMPREENDIMENTOS']
df_outras = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['imobiliaria'] != 'PRATI EMPREENDIMENTOS']

# Análise por situação para cada grupo
analise_situacao_prati = df_prati.groupby('situacao')['idreserva'].count().reset_index()
analise_situacao_outras = df_outras.groupby('situacao')['idreserva'].count().reset_index()

# Renomear colunas
analise_situacao_prati.columns = ['Situação', 'Prati']
analise_situacao_outras.columns = ['Situação', 'Outras']

# Mesclar os dataframes
analise_comparativa = pd.merge(analise_situacao_prati, analise_situacao_outras, on='Situação', how='outer').fillna(0)
analise_comparativa = analise_comparativa.astype({'Prati': int, 'Outras': int})

# Exibir tabela comparativa
st.table(analise_comparativa)

# Gráfico de Barras - Reservas por Imobiliária
st.subheader("Distribuição de Reservas por Imobiliária")
chart_data = df_sem_canceladas_vendidas.groupby('imobiliaria')['idreserva'].count().reset_index()
chart_data.columns = ['Imobiliária', 'Quantidade']
st.bar_chart(data=chart_data, x='Imobiliária', y='Quantidade')
