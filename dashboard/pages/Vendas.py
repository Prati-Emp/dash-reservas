import streamlit as st
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import display_navigation
import pandas as pd
from datetime import datetime
import plotly.express as px
import locale
import duckdb
from dotenv import load_dotenv
import os

# Metas de vendas por mês
meta_vendas = {
    "Data": [
        "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01",
        "2025-05-01", "2025-06-01", "2025-07-01", "2025-08-01",
        "2025-09-01", "2025-10-01", "2025-11-01", "2025-12-01"
    ],
    "Meta de vendas": [
        1941000.0, 1941000.0, 2961000.0, 12481000.0,
        12195000.0, 10836000.0, 10279000.0, 8828000.0,
        11622000.0, 11500000.0, 10155000.0, 5385000.0
    ]
}

# Configuração da página
st.set_page_config(page_title="Análise de Vendas", layout="wide")

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = "pages/Vendas.py"

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
            return f"R$ {value/1_000_000:.1f}Mi"
        elif value >= 1_000:  # Se for 1 mil ou mais
            return f"R$ {value/1_000:.1f}Mil"
        else:
            return f"R$ {value:.1f}"
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
      # Buscar todas as reservas com tipo de venda
    reservas_df = conn.sql("""
        SELECT 
            r.*,
            COALESCE(r.tipovenda, 'Outros') as tipo_venda,
            CASE 
                WHEN r.situacao = 'Vendida' THEN r.data_ultima_alteracao_situacao
                ELSE NULL 
            END as data_venda
        FROM reservas.main.reservas_abril r
    """).df()
    
    # Converter colunas de data
    reservas_df['data_cad'] = pd.to_datetime(reservas_df['data_cad'])
    reservas_df['data_ultima_alteracao_situacao'] = pd.to_datetime(reservas_df['data_ultima_alteracao_situacao'])
    reservas_df['data_venda'] = pd.to_datetime(reservas_df['data_venda'])
    
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

# Filtro de data - usar data_venda para vendas
vendas_datas = reservas_df[reservas_df['situacao'] == 'Vendida']['data_venda'].dropna()
data_inicio = st.sidebar.date_input(
    "Data Inicial",
    value=pd.Timestamp('2025-01-01'),
    min_value=min(vendas_datas.dt.date),
    max_value=max(vendas_datas.dt.date)
)
data_fim = st.sidebar.date_input(
    "Data Final",
    value=max(vendas_datas.dt.date),
    min_value=min(vendas_datas.dt.date),
    max_value=max(vendas_datas.dt.date)
)

# Filtro de empreendimento
empreendimentos = sorted(reservas_df['empreendimento'].unique())
empreendimento_selecionado = st.sidebar.selectbox("Empreendimento", ["Todos"] + list(empreendimentos))

# Filtro de tipo de venda
tipos_venda = sorted(reservas_df['tipo_venda'].unique())
tipo_venda_selecionado = st.sidebar.selectbox("Tipo de Venda", ["Todos"] + list(tipos_venda))

# Aplicar filtros básicos (não relacionados à data)
df_filtrado = reservas_df.copy()

# Aplicar filtro de empreendimento se selecionado
if empreendimento_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['empreendimento'] == empreendimento_selecionado]

# Aplicar filtro de tipo de venda se selecionado
if tipo_venda_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['tipo_venda'] == tipo_venda_selecionado]

# Para vendas, usar data_venda no filtro
vendas_filtradas = df_filtrado[
    (df_filtrado['situacao'] == 'Vendida') & 
    (df_filtrado['data_venda'].dt.date >= data_inicio) & 
    (df_filtrado['data_venda'].dt.date <= data_fim)
]

# Para outras situações, manter o filtro por data_cad
outras_situacoes = df_filtrado[
    (df_filtrado['situacao'] != 'Vendida') & 
    (df_filtrado['data_cad'].dt.date >= data_inicio) & 
    (df_filtrado['data_cad'].dt.date <= data_fim)
]

# Combinar os dataframes
df_filtrado = pd.concat([vendas_filtradas, outras_situacoes])

# Calcular dados do mês anterior
data_inicio_mes_anterior = pd.Timestamp(data_inicio) - pd.DateOffset(months=1)
data_fim_mes_anterior = pd.Timestamp(data_inicio) - pd.DateOffset(days=1)

# Filtrar vendas do mês anterior usando data_venda
vendas_mes_anterior = reservas_df[
    (reservas_df['situacao'] == 'Vendida') & 
    (reservas_df['data_venda'].dt.date >= data_inicio_mes_anterior.date()) & 
    (reservas_df['data_venda'].dt.date <= data_fim_mes_anterior.date())
]

# Filtrar outras situações do mês anterior usando data_cad
outras_situacoes_mes_anterior = reservas_df[
    (reservas_df['situacao'] != 'Vendida') & 
    (reservas_df['data_cad'].dt.date >= data_inicio_mes_anterior.date()) & 
    (reservas_df['data_cad'].dt.date <= data_fim_mes_anterior.date())
]

# Combinar os dataframes do mês anterior
df_mes_anterior = pd.concat([vendas_mes_anterior, outras_situacoes_mes_anterior])

# Aplicar os mesmos filtros do mês atual ao mês anterior
if empreendimento_selecionado != "Todos":
    df_mes_anterior = df_mes_anterior[df_mes_anterior['empreendimento'] == empreendimento_selecionado]
if tipo_venda_selecionado != "Todos":
    df_mes_anterior = df_mes_anterior[df_mes_anterior['tipo_venda'] == tipo_venda_selecionado]

# Métricas principais em uma linha
col1, col2, col3, col4, col5 = st.columns([3, 3, 3, 3, 3])

with col1:
    # Total de vendas no período usando data_venda
    total_vendas = len(df_filtrado[
        (df_filtrado['situacao'] == 'Vendida') & 
        (df_filtrado['data_venda'].dt.date >= data_inicio) & 
        (df_filtrado['data_venda'].dt.date <= data_fim)
    ])
    st.metric("Total de Vendas", f"{total_vendas:,}")

with col2:
    # Valor total atual usando data_venda
    vendas_periodo = df_filtrado[
        (df_filtrado['situacao'] == 'Vendida') & 
        (df_filtrado['data_venda'].dt.date >= data_inicio) & 
        (df_filtrado['data_venda'].dt.date <= data_fim)
    ]
    valor_total = vendas_periodo['valor_contrato'].sum()
    st.metric(
        "Valor Total em Vendas",
        format_currency(valor_total)
    )

with col3:
    # Calcular meta para o período selecionado
    meta_df = pd.DataFrame(meta_vendas)
    meta_df['Data'] = pd.to_datetime(meta_df['Data'])
    meta_periodo = meta_df[
        (meta_df['Data'].dt.date >= data_inicio) & 
        (meta_df['Data'].dt.date <= data_fim)
    ]
    valor_meta = meta_periodo['Meta de vendas'].sum()
      # Calcular atingimento da meta
    atingimento = (valor_total / valor_meta * 100) if valor_meta > 0 else 0
    
    st.metric(
        "Meta do Período",
        format_currency(valor_meta),
        f"{atingimento:.1f}% atingido",
        delta_color="inverse" if atingimento < 100 else "normal"
    )

with col4:
    # Taxa house atual (usando data_venda)
    vendas_periodo = df_filtrado[
        (df_filtrado['situacao'] == 'Vendida') & 
        (df_filtrado['data_venda'].dt.date >= data_inicio) & 
        (df_filtrado['data_venda'].dt.date <= data_fim)
    ]
    vendas_internas = len(vendas_periodo[vendas_periodo['tipo_venda_origem'] == 'Venda Interna (Prati)'])
    total_vendas_periodo = len(vendas_periodo)
    taxa_house = (vendas_internas / total_vendas_periodo * 100) if total_vendas_periodo > 0 else 0
    
    # Taxa house mês anterior (usando data_venda)
    vendas_anterior = df_mes_anterior[
        (df_mes_anterior['situacao'] == 'Vendida') & 
        (df_mes_anterior['data_venda'].dt.date >= data_inicio_mes_anterior.date()) & 
        (df_mes_anterior['data_venda'].dt.date <= data_fim_mes_anterior.date())
    ]
    vendas_internas_anterior = len(vendas_anterior[vendas_anterior['tipo_venda_origem'] == 'Venda Interna (Prati)'])
    total_vendas_anterior = len(vendas_anterior)
    taxa_house_anterior = (vendas_internas_anterior / total_vendas_anterior * 100) if total_vendas_anterior > 0 else 0
      # Calcular variação em pontos percentuais
    variacao_taxa = taxa_house - taxa_house_anterior
    st.metric(
        "Taxa House",
        f"{taxa_house:.1f}%",
        f"{variacao_taxa:+.1f}% vs mês anterior"
    )

with col5:
    # Tempo médio apenas das vendas do período
    vendas_periodo = df_filtrado[
        (df_filtrado['situacao'] == 'Vendida') & 
        (df_filtrado['data_venda'].dt.date >= data_inicio) & 
        (df_filtrado['data_venda'].dt.date <= data_fim)
    ]
    tempo_medio_geral = int(vendas_periodo['tempo_ate_venda'].mean().round(0))
    st.metric("Tempo Médio até a Venda", f"{tempo_medio_geral} dias")

st.divider()

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

st.divider()

# Análise estratificada por empreendimento e tipo de venda
st.subheader("Filtro por Tipo de Venda")

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

st.divider()

# Análise de conversão de reservas em vendas
st.subheader("Taxa de Conversão de Reservas em Vendas")

# Calcular taxas de conversão para vendas internas e externas
def calcular_taxa_conversao(df, df_reservas, tipo_venda, data_inicio, data_fim):
    # Total de reservas no período
    reservas_periodo = df_reservas[
        (df_reservas['tipo_venda_origem'] == tipo_venda) &
        (df_reservas['data_cad'].dt.date >= data_inicio) &
        (df_reservas['data_cad'].dt.date <= data_fim)
    ]
    total_reservas = len(reservas_periodo)
    
    # Total de vendas no período (usando data_venda)
    vendas_periodo = df[
        (df['tipo_venda_origem'] == tipo_venda) &
        (df['situacao'] == 'Vendida') &
        (df['data_venda'].dt.date >= data_inicio) &
        (df['data_venda'].dt.date <= data_fim)
    ]
    total_vendas = len(vendas_periodo)
    
    taxa = (total_vendas / total_reservas * 100) if total_reservas > 0 else 0
    return pd.Series({
        'Total Reservas': total_reservas,
        'Total Vendas': total_vendas,
        'Taxa de Conversão': taxa
    })

# Criar DataFrame de conversão usando data_venda para o período
conversao_interna = calcular_taxa_conversao(df_filtrado, reservas_df, 'Venda Interna (Prati)', data_inicio, data_fim)
conversao_externa = calcular_taxa_conversao(df_filtrado, reservas_df, 'Venda Externa (Imobiliárias)', data_inicio, data_fim)

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
