import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Configuração da página
st.set_page_config(page_title="Relatório de Reservas", layout="wide")

# Título do aplicativo
st.title("📊 Relatório de Reservas")

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
        
    # Pega a data da última alteração diretamente da tabela de reservas
    data_ultima_alteracao = pd.to_datetime(row['data_ultima_alteracao_situacao'])
    
    # Calcula a diferença entre agora e a última alteração em dias
    dias_decorridos = (datetime.now() - data_ultima_alteracao).days
    
    # Verifica se o tempo desde a última alteração excede o limite
    return dias_decorridos >= dias_limite

# Carregando os dados
@st.cache_data
def load_data():
    csv_path = r'C:\Users\Djonathan__Souza\OneDrive - Prati Empreendimentos ltda\backup\Desenvolvimento\double_try'
    reservas_df = pd.read_csv(f'{csv_path}/reservas_abril.csv')
    workflow_df = pd.read_csv(f'{csv_path}/workflow_abril.csv')
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    workflow_df['referencia_data'] = pd.to_datetime(workflow_df['referencia_data'])
    
    return reservas_df, workflow_df

reservas_df, workflow_df = load_data()

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de data
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-04-01'),  # Data padrão definida para 01/04/2025
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

# Filtro de situação
situacoes = sorted(reservas_df['situacao'].unique())
situacao_selecionada = st.sidebar.selectbox("Situação", ["Todas"] + list(situacoes))

# Aplicar filtros
mask = (reservas_df['data_cad'].dt.date >= data_inicio) & (reservas_df['data_cad'].dt.date <= data_fim)
if empreendimento_selecionado != "Todos":
    mask = mask & (reservas_df['empreendimento'] == empreendimento_selecionado)
if situacao_selecionada != "Todas":
    mask = mask & (reservas_df['situacao'] == situacao_selecionada)

df_filtrado = reservas_df[mask]

# Métricas principais
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total de Reservas", value=len(df_sem_canceladas_vendidas))
with col2:
    valor_total = df_sem_canceladas_vendidas['valor_contrato'].sum()
    st.metric(label="Valor Total", value=f"R$ {valor_total:,.2f}")

# Reservas por Situação
st.subheader("Reservas por Situação")

# Contar reservas por situação do df_filtrado
quantidade_por_situacao = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]['situacao'].value_counts().reset_index()
quantidade_por_situacao.columns = ['Situação', 'Quantidade']

# Verificar fora do prazo diretamente na tabela de reservas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]
df_sem_canceladas_vendidas['tempo_excedido'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)

# Contar fora do prazo por situação
fora_prazo_por_situacao = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['tempo_excedido']].groupby('situacao')['tempo_excedido'].count().reset_index()
fora_prazo_por_situacao.columns = ['Situação', 'Fora do Prazo']

# Juntar as informações
reservas_por_situacao = pd.merge(quantidade_por_situacao, fora_prazo_por_situacao, on='Situação', how='left')
reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao['Fora do Prazo'].fillna(0).astype(int)

# Garantir que "Fora do Prazo" não seja maior que "Quantidade"
reservas_por_situacao['Fora do Prazo'] = reservas_por_situacao.apply(
    lambda row: min(row['Fora do Prazo'], row['Quantidade']), 
    axis=1
)

st.table(reservas_por_situacao)

# Tabela detalhada
st.subheader("Lista de Reservas")

# Calcular o tempo na situação atual
df_sem_canceladas_vendidas['tempo_na_situacao'] = (datetime.now() - pd.to_datetime(df_sem_canceladas_vendidas['data_ultima_alteracao_situacao'])).dt.days

# Verificar quais reservas estão fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)

# Função para estilizar o DataFrame
def highlight_fora_prazo(s):
    return ['color: red' if df_sem_canceladas_vendidas['fora_do_prazo'].iloc[i] else '' for i in range(len(s))]

# Preparar e exibir o DataFrame com estilo
colunas_exibir = ['idreserva', 'cliente', 'empreendimento', 'situacao', 
                  'tempo_na_situacao', 'valor_contrato', 'imobiliaria']

st.dataframe(
    df_sem_canceladas_vendidas[colunas_exibir].style.apply(highlight_fora_prazo, axis=0),
    use_container_width=True
)

# Análise de workflow
if st.checkbox("Mostrar Análise de Workflow"):
    st.subheader("Análise de Workflow")
    # Usar os dados filtrados diretamente da tabela de reservas
    workflow_agregado = df_filtrado.groupby('situacao')['idreserva'].count().reset_index()
    st.bar_chart(data=workflow_agregado, x='situacao', y='idreserva')