import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Configuração da página
st.set_page_config(page_title="Motivo Fora do Prazo", layout="wide")

# Título do aplicativo
st.title("📅 Análise de Reservas Fora do Prazo")

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

# Carregando os dados
@st.cache_data
def load_data():
    csv_path = r'C:\Users\Djonathan__Souza\OneDrive - Prati Empreendimentos ltda\backup\Desenvolvimento\double_try'
    reservas_df = pd.read_csv(f'{csv_path}/reservas_abril.csv')
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    
    return reservas_df

reservas_df = load_data()

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
df_filtrado = reservas_df[mask].copy()

if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]
if situacao_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['situacao'] == situacao_selecionada]

# Remover reservas canceladas e vendidas
df_sem_canceladas_vendidas = df_filtrado[~df_filtrado['situacao'].isin(['Cancelada', 'Vendida'])]

# Verificar reservas fora do prazo
df_sem_canceladas_vendidas['fora_do_prazo'] = df_sem_canceladas_vendidas.apply(check_time_limit, axis=1)
df_sem_canceladas_vendidas['dias_na_situacao'] = (datetime.now() - df_sem_canceladas_vendidas['data_ultima_alteracao_situacao']).dt.days

# Métricas principais
col1, col2, col3 = st.columns(3)
with col1:
    total_fora_prazo = df_sem_canceladas_vendidas['fora_do_prazo'].sum()
    st.metric(label="Total Fora do Prazo", value=int(total_fora_prazo))
with col2:
    percentual_fora_prazo = (total_fora_prazo / len(df_sem_canceladas_vendidas)) * 100
    st.metric(label="Percentual Fora do Prazo", value=f"{percentual_fora_prazo:.1f}%")
with col3:
    valor_total_fora_prazo = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']]['valor_contrato'].sum()
    st.metric(label="Valor Total Fora do Prazo", value=f"R$ {valor_total_fora_prazo:,.2f}")

# Análise por situação
st.subheader("Análise por Situação")
analise_situacao = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']].groupby('situacao').agg({
    'idreserva': 'count',
    'dias_na_situacao': 'mean',
    'valor_contrato': 'sum'
}).reset_index()

analise_situacao.columns = ['Situação', 'Quantidade', 'Média de Dias', 'Valor Total']
analise_situacao['Média de Dias'] = analise_situacao['Média de Dias'].round(1)
analise_situacao['Valor Total'] = analise_situacao['Valor Total'].map('R$ {:,.2f}'.format)

st.table(analise_situacao)

# Lista detalhada de reservas fora do prazo em formato de cards
st.subheader("Cards de Reservas Fora do Prazo")
df_fora_prazo = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']]

# Criar colunas para os cards (3 cards por linha)
cols = st.columns(3)
for idx, row in df_fora_prazo.iterrows():
    with cols[idx % 3]:
        with st.container():
            st.markdown(f"""
                <div style="padding: 1rem; border-radius: 8px; border: 1px solid #e5e7eb; margin-bottom: 1rem; background-color: white; color: black;">
                    <h4 style="color: black;">Reserva #{int(row['idreserva'])}</h4>
                    <p style="color: black;"><strong style="color: black;">Cliente:</strong> {row['cliente']}</p>
                    <p style="color: black;"><strong style="color: black;">Empreendimento:</strong> {row['empreendimento']}</p>
                    <p style="color: black;"><strong style="color: black;">Situação:</strong> {row['situacao']}</p>
                    <p style="color: black;"><strong style="color: black;">Dias na Situação:</strong> {row['dias_na_situacao']}</p>
                    <p style="color: black;"><strong style="color: black;">Valor:</strong> R$ {row['valor_contrato']:,.2f}</p>
                    <p style="color: black;"><strong style="color: black;">Imobiliária:</strong> {row['imobiliaria']}</p>
                </div>
            """, unsafe_allow_html=True)

# Gráfico de distribuição
st.subheader("Distribuição por Dias na Situação")
fig_data = df_fora_prazo.groupby('situacao')['dias_na_situacao'].mean().reset_index()
st.bar_chart(data=fig_data, x='situacao', y='dias_na_situacao')