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

st.set_page_config(page_title="Leads - Funil de Vendas", page_icon="📊", layout="wide")

st.title("📊 Funil de Leads - Prati Empreendimentos")

MOTHERDUCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InByYXRpcHJvamV0b3NAZ21haWwuY29tIiwic2Vzc2lvbiI6InByYXRpcHJvamV0b3MuZ21haWwuY29tIiwicGF0IjoiUnA1clVla2JwRFY4OFp2d3RKNWxkOFhxdmtpSFQzRlNacWdXbXFsQ09WMCIsInVzZXJJZCI6ImFkZThmZGM0LTc1MDktNGU4Ny1hZTcwLTMwZGVkMTQ4Y2RlOSIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc0OTA2ODI4N30.TEUsvAxCKXhzNrb7WAok0jL2YmqEEtrxaEOKZZ6tuBI"

# Load all data with broad date range for filtering
def get_all_leads_duckdb():
    con = duckdb.connect(f"md:reservas?token={MOTHERDUCK_TOKEN}")
    query = """
    SELECT Idlead as idlead, Data_cad as data_cad, Situacao as situacao_nome, Imobiliaria as imobiliaria, nome_situacao_anterior_lead, gestor, empreendimento_ultimo
    FROM cv_leads
    WHERE Data_cad >= '2022-04-13'
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

# Initial filter by imobiliaria
leads_df = leads_df[
    (leads_df["imobiliaria"] == "Prati Empreendimentos")
]

# Sidebar for filters
st.sidebar.header("Filtros")

# Date filters stacked vertically
data_inicio = st.sidebar.date_input("Data Inicial", value=datetime(2022, 4, 13).date())
data_fim = st.sidebar.date_input("Data Final", value=datetime.now().date())

# Empreendimento filter
empreendimentos = sorted(leads_df['empreendimento_ultimo'].dropna().unique())
selected_empreendimento = st.sidebar.selectbox("Empreendimento de Interesse", ["Todos"] + list(empreendimentos))

# Apply filters
filtered_df = leads_df[
    (leads_df['data_cad'].dt.date >= data_inicio) &
    (leads_df['data_cad'].dt.date <= data_fim)
].copy()

if selected_empreendimento != "Todos":
    filtered_df = filtered_df[filtered_df['empreendimento_ultimo'] == selected_empreendimento]

# Transições do funil baseadas na tabela "de" -> "para"
transicoes_funil = {
    ("aguardando atendimento", "qualificação"): "Leads",
    ("qualificação", "descoberta"): "Leads",
    ("descoberta", "em atendimento"): "Em atendimento",
    ("em atendimento", "atendimento futuro"): "Em atendimento",
    ("atendimento futuro", "visita agendada"): "Em atendimento",
    ("visita agendada", "visita realizada"): "Visita realizada",
    ("visita realizada", "atendimento pos visita"): "Visita realizada",
    ("atendimento pos visita", "pre cadastro pos visita"): "Com reserva",
    ("com reserva", "venda realizada"): "Venda realizada",
    ("venda realizada", "venda realizada"): "Venda realizada"
}

# Mapeamento do funil para fallback (situação atual ou anterior para "descartado")
mapa_funil = {
    "aguardando atendimento": "Leads",
    "qualificação": "Leads",
    "descoberta": "Leads",
    "em atendimento": "Em atendimento",
    "atendimento futuro": "Em atendimento",
    "visita agendada": "Em atendimento",
    "visita realizada": "Visita realizada",
    "atendimento pos visita": "Visita realizada",
    "pre cadastro": "Com reserva",
    "pre cadastro pos visita": "Com reserva",
    "com reserva": "Com reserva",
    "venda realizada": "Venda realizada",
    "descartado": "Leads"
}

def get_funil_etapa(prev_situacao, curr_situacao):
    # Normalizar entradas
    if pd.isna(prev_situacao):
        prev_key = None
    else:
        prev_key = str(prev_situacao).strip().lower()
    
    if pd.isna(curr_situacao):
        curr_key = None
    else:
        curr_key = str(curr_situacao).strip().lower()
    
    # Caso especial: "descartado" usa a etapa da situação anterior
    if curr_key == "descartado":
        if prev_key is None:
            return "Leads"
        return mapa_funil.get(prev_key, "Leads")
    
    # Verificar transição (prev, curr)
    if prev_key is not None and curr_key is not None:
        trans_key = (prev_key, curr_key)
        if trans_key in transicoes_funil:
            return transicoes_funil[trans_key]
    
    # Fallback: usar mapa da situação atual
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

etapa_counts = [filtered_df[filtered_df["funil_etapa"] == etapa].shape[0] for etapa in funil_etapas]

fig = go.Figure(go.Funnel(
    y=funil_etapas,
    x=etapa_counts,
    textinfo="value+percent initial"
))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Leads", etapa_counts[0])
col2.metric("Em atendimento", etapa_counts[1])
col3.metric("Visita Realizada", etapa_counts[2])
col4.metric("Com reserva", etapa_counts[3])
col5.metric("Venda realizada", etapa_counts[4])

st.markdown("---")
st.subheader("Leads detalhados")
display_columns = ["idlead", "situacao_nome", "nome_situacao_anterior_lead", "funil_etapa", "gestor", "imobiliaria", "empreendimento_ultimo", "data_cad"]
st.dataframe(
    filtered_df[display_columns].sort_values("data_cad", ascending=False),
    use_container_width=True
)
