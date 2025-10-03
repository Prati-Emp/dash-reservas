import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

st.set_page_config(page_title="Leads - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads")

# Remove previous single tooltip near title
# Add tooltips next to each metric label

# col1, col2, col3, col4, col5 = st.columns(5)

# col1.metric(f"Leads {tooltip_icon(tooltip_texts['Leads'])}", etapa_counts[0], unsafe_allow_html=True)
# col2.metric(f"Em atendimento {tooltip_icon(tooltip_texts['Em atendimento'])}", etapa_counts[1], unsafe_allow_html=True)
# col3.metric(f"Visita Realizada {tooltip_icon(tooltip_texts['Visita Realizada'])}", etapa_counts[2], unsafe_allow_html=True)
# col4.metric(f"Com reserva {tooltip_icon(tooltip_texts['Com reserva'])}", etapa_counts[3], unsafe_allow_html=True)
# col5.metric(f"Venda realizada {tooltip_icon(tooltip_texts['Venda realizada'])}", etapa_counts[4], unsafe_allow_html=True)

# Carregar token do MotherDuck de forma segura
MOTHERDUCK_TOKEN = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN", ""))
if not MOTHERDUCK_TOKEN:
    st.error("Token do MotherDuck não configurado. Defina MOTHERDUCK_TOKEN em st.secrets ou variável de ambiente.")
    st.stop()

# Load all data with broad date range for filtering
def get_all_leads_duckdb():
    con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    query = """
    SELECT Idlead as idlead,
           Data_cad as data_cad,
           Referencia_data as referencia_data,
           Situacao as situacao_nome,
           Imobiliaria as imobiliaria,
           nome_situacao_anterior_lead,
           gestor,
           empreendimento_ultimo
    FROM cv_leads
    ORDER BY data_cad DESC
    """
    df = con.execute(query).df()
    con.close()
    return df

@st.cache_data
def load_data():
    return get_all_leads_duckdb()

leads_df = load_data()

if leads_df.empty:
    st.warning("Nenhum dado retornado do Mother Duck.")
    st.stop()

# Sidebar for filters
st.sidebar.header("Filtros")

# Date filters stacked vertically (using data_cad)
data_inicio = st.sidebar.date_input("Data Inicial", value=datetime(2022, 4, 13).date())
data_fim = st.sidebar.date_input("Data Final", value=datetime.now().date())

# Imobiliaria filter
imobiliarias = sorted(leads_df['imobiliaria'].dropna().unique())
selected_imobiliaria = st.sidebar.selectbox("Imobiliária", ["Todas"] + list(imobiliarias))

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Apply filters using data_cad
filtered_df = leads_df[
    (leads_df['data_cad'].dt.date >= data_inicio) &
    (leads_df['data_cad'].dt.date <= data_fim)
].copy()

if selected_imobiliaria != "Todas":
    filtered_df = filtered_df[filtered_df['imobiliaria'] == selected_imobiliaria]

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Mapeamento do funil baseado na tabela "de" (situação atual) -> "para" (etapa), com especial para "descartado" usando anterior
mapa_funil = {
    "aguardando atendimento": "Leads",
    "qualificação": "Leads",
    "descoberta": "Leads",
    "em atendimento": "Em atendimento",
    "atendimento futuro": "Em atendimento",
    "visita agendada": "Em atendimento",
    "visita realizada": "Visita realizada",
    "atendimento pos visita": "Visita realizada",
    "atendimento pós visita": "Visita realizada",
    "pre cadastro": "Com reserva",
    "pre cadastro pos visita": "Com reserva",
    "em pré-cadastro": "Com reserva",
    "com reserva": "Com reserva",
    "venda realizada": "Venda realizada"
}

def get_funil_etapa(prev_situacao, curr_situacao):
    # Normalizar entradas
    if pd.isna(curr_situacao):
        curr_key = None
    else:
        curr_key = str(curr_situacao).strip().lower()
    
    # Caso especial: "descartado" sempre usa etapa da situação anterior
    if curr_key == "descartado":
        if pd.isna(prev_situacao):
            return "Leads"
        prev_key = str(prev_situacao).strip().lower()
        return mapa_funil.get(prev_key, "Leads")
    
    # Para outras situações, usa mapeamento da atual
    if curr_key is None:
        return "Leads"
    return mapa_funil.get(curr_key, "Leads")

filtered_df["funil_etapa"] = filtered_df.apply(lambda row: get_funil_etapa(row['nome_situacao_anterior_lead'], row['situacao_nome']), axis=1)

funil_etapas = [
    "Leads",
    "Em atendimento",
    "Visita realizada",
    "Com reserva",
    "Venda realizada"
]

# Calcular as contagens iniciais para cada etapa
initial_etapa_counts = {etapa: filtered_df[filtered_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas}

etapa_counts = []
total_leads_remaining = filtered_df.shape[0]

for i, etapa in enumerate(funil_etapas):
    current_stage_count = initial_etapa_counts.get(etapa, 0)
    
    if i == 0: # Leads totais
        etapa_counts.append(total_leads_remaining)
    elif etapa == "Em atendimento":
        cumulative_em_atendimento = initial_etapa_counts.get("Em atendimento", 0) + \
                                    initial_etapa_counts.get("Visita realizada", 0) + \
                                    initial_etapa_counts.get("Com reserva", 0) + \
                                    initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_em_atendimento)
    elif etapa == "Visita realizada":
        cumulative_visita_realizada = initial_etapa_counts.get("Visita realizada", 0) + \
                                      initial_etapa_counts.get("Com reserva", 0) + \
                                      initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_visita_realizada)
    elif etapa == "Com reserva":
        cumulative_com_reserva = initial_etapa_counts.get("Com reserva", 0) + \
                                 initial_etapa_counts.get("Venda realizada", 0)
        etapa_counts.append(cumulative_com_reserva)
    else:
        etapa_counts.append(current_stage_count)

fig = go.Figure(go.Funnel(
    y=funil_etapas,
    x=etapa_counts,
    textinfo="value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)

tooltip_texts = {
    "Leads": "Total de leads em todas as situações.",
    "Em atendimento": "Leads nas situações relacionadas a atendimento.",
    "Visita Realizada": "Leads que realizaram visita.",
    "Com reserva": "Leads com reserva confirmada.",
    "Venda realizada": "Leads que resultaram em venda."
}

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(label="Leads", value=etapa_counts[0], help=tooltip_texts['Leads'])
col2.metric(label="Em atendimento", value=etapa_counts[1], help=tooltip_texts['Em atendimento'])
col3.metric(label="Visita Realizada", value=etapa_counts[2], help=tooltip_texts['Visita Realizada'])
col4.metric(label="Com reserva", value=etapa_counts[3], help=tooltip_texts['Com reserva'])
col5.metric(label="Venda realizada", value=etapa_counts[4], help=tooltip_texts['Venda realizada'])

st.markdown("---")
st.subheader("Leads detalhados")
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_cad"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_cad", ascending=False),
    use_container_width=True
)
