import streamlit as st
import duckdb
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from utils import display_navigation

# Display navigation bar (includes logo)
display_navigation()

# Store current page in session state
st.session_state['current_page'] = __file__

st.set_page_config(page_title="Leads Ativos - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads Ativos")

MOTHERDUCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InByYXRpcHJvamV0b3NAZ21haWwuY29tIiwic2Vzc2lvbiI6InByYXRpcHJvamV0b3MuZ21haWwuY29tIiwicGF0IjoiUnA1clVla2JwRFY4OFp2d3RKNWxkOFhxdmtpSFQzRlNacWdXbXFsQ09WMCIsInVzZXJJZCI6ImFkZThmZGM0LTc1MDktNGU4Ny1hZTcwLTMwZGVkMTQ4Y2RlOSIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc0OTA2ODI4N30.TEUsvAxCKXhzNrb7WAok0jL2YmqEEtrxaEOKZZ6tuBI"

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

# Imobiliaria filter
imobiliarias = sorted(leads_df['imobiliaria'].dropna().unique())
selected_imobiliaria = st.sidebar.selectbox("Imobiliária", ["Todas"] + list(imobiliarias))

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Apply filters
filtered_df = leads_df.copy()

if selected_imobiliaria != "Todas":
    filtered_df = filtered_df[filtered_df['imobiliaria'] == selected_imobiliaria]

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Exclude converted leads: Descartado, Em Pré-Cadastro, Venda realizada
exclude_situations = ['descartado', 'em pré-cadastro', 'venda realizada']
filtered_df = filtered_df[~filtered_df['situacao_nome'].str.lower().str.strip().isin(exclude_situations)]

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
    "Com reserva"
]

etapa_counts = [filtered_df[filtered_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas]

fig = go.Figure(go.Funnel(
    y=funil_etapas,
    x=etapa_counts,
    textinfo="value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Leads", etapa_counts[0])
col2.metric("Em atendimento", etapa_counts[1])
col3.metric("Visita Realizada", etapa_counts[2])
col4.metric("Com reserva", etapa_counts[3])

st.markdown("---")
st.subheader("Leads ativos detalhados")
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_cad"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_cad", ascending=False),
    use_container_width=True
)
