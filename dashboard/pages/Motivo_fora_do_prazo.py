import streamlit as st

# Configuração da página
st.set_page_config(page_title="Motivo Fora do Prazo", layout="wide")

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
    try:
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            raise ValueError("MOTHERDUCK_TOKEN não encontrado nas variáveis de ambiente")
        
        # Configurar o token como variável de ambiente (necessário no Linux)
        os.environ['motherduck_token'] = token.strip()
        
        try:
            # Tentar conexão com configuração explícita
            conn = duckdb.connect(database=':memory:', config={'motherduck_token': token})
            
            # Carregar extensão motherduck
            conn.execute("INSTALL motherduck; LOAD motherduck;")
            
            # Conectar ao MotherDuck
            conn = duckdb.connect('md:reservas')
            return conn
        except Exception as e:
            st.error(f"Erro na conexão com MotherDuck: {str(e)}")
            raise
    except Exception as e:
        st.error(f"Erro ao configurar conexão: {str(e)}")
        raise

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
    conn = get_motherduck_connection()      # Usando a tabela correta do MotherDuck
    reservas_df = conn.sql("""
        SELECT *
        FROM reservas.main.reservas_abril
    """).df()
    
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
situacoes = sorted(reservas_df[~reservas_df['situacao'].isin(['Vendida', 'Distrato', 'Cancelada'])]['situacao'].unique())
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
    st.metric(label="Valor Total Fora do Prazo", value=format_currency(valor_total_fora_prazo))

# Análise por situação
st.subheader("Análise por Situação")
analise_situacao = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']].groupby('situacao').agg({
    'idreserva': 'count',
    'dias_na_situacao': 'mean',
    'valor_contrato': 'sum'
}).reset_index()

analise_situacao.columns = ['Situação', 'Quantidade', 'Média de Dias', 'Valor Total']
analise_situacao['Média de Dias'] = analise_situacao['Média de Dias'].round(1)
analise_situacao['Valor Total'] = analise_situacao['Valor Total'].apply(format_currency)

st.table(analise_situacao)

@st.cache_data
def get_reservation_messages(idreserva):
    """Busca as mensagens de uma reserva específica"""
    url = f"https://prati.cvcrm.com.br/api/v2/cv/reservas/{idreserva}/mensagens"
    headers = {
        "accept": "application/json",
        "email": "djonathan.souza@grupoprati.com",
        "token": "394f594bc6192c86d94f329355ae13ca0b78a2a9",
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        messages = response.json().get("dados", [])
        return messages
    except Exception as e:
        st.error(f"Erro ao buscar mensagens da reserva {idreserva}: {str(e)}")
        return []

# Lista detalhada de reservas fora do prazo em formato de cards
st.subheader("Cards de Reservas Fora do Prazo")
df_fora_prazo = df_sem_canceladas_vendidas[df_sem_canceladas_vendidas['fora_do_prazo']]

# Criar colunas para os cards (3 cards por linha)
for i in range(0, len(df_fora_prazo), 3):
    cols = st.columns([1, 1, 1])  # Equal width columns
    for j in range(3):
        if i + j < len(df_fora_prazo):
            row = df_fora_prazo.iloc[i + j]
            messages = get_reservation_messages(int(row['idreserva']))
            
            with cols[j]:
                st.markdown(f"""
                    <div style="
                        padding: 1.2rem;
                        border-radius: 10px;
                        border: 1px solid #e5e7eb;
                        margin: 0.5rem 0;
                        background-color: white;
                        color: black;
                        height: 100%;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
                    ">
                        <h4 style="color: #000000; margin-top: 0; margin-bottom: 1rem; font-weight: 600;">Reserva #{int(row['idreserva'])}</h4>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Cliente:</strong> {row['cliente']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Empreendimento:</strong> {row['empreendimento']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Situação:</strong> {row['situacao']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Dias na Situação:</strong> {row['dias_na_situacao']}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Valor:</strong> {format_currency(row['valor_contrato'])}</p>
                        <p style="color: #000000; margin: 0.5rem 0;"><strong style="color: #000000; font-weight: 600;">Imobiliária:</strong> {row['imobiliaria']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                if messages:
                    with st.expander("Ver Mensagens"):
                        for msg in messages:
                            st.markdown(f"""
                                <div style="
                                    padding: 0.8rem;
                                    border-radius: 8px;
                                    border: 1px solid #e5e7eb;
                                    margin: 0.5rem 0;
                                    background-color: #f9fafb;
                                    color: #000000;
                                ">
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Data:</strong> <span style="color: #000000;">{msg.get('dataCad', 'N/A')}</span></p>
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Usuário:</strong> <span style="color: #000000;">{msg.get('usuario_nome', 'N/A')}</span></p>
                                    <p style="color: #000000; margin: 0.2rem 0;"><strong style="color: #000000;">Mensagem:</strong> <span style="color: #000000;">{msg.get('mensagem', 'N/A')}</span></p>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    with st.expander("Ver Mensagens"):
                        st.info("Não há mensagens para esta reserva.")