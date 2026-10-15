# Componentes Compartilhados de Interface (QRZ)

import streamlit as st
import plotly.graph_objects as go

def criar_gauge(valor, titulo, max_val=100, cor_hex="#4CAF50"):
    """Gera um gráfico de Gauge circular usando Plotly."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={'text': titulo, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [None, max_val], 'tickwidth': 1},
            'bar': {'color': cor_hex},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "#333",
            'steps': [{'range': [0, max_val], 'color': '#262730'}],
        }
    ))
    fig.update_layout(
        height=220, 
        margin=dict(l=20, r=20, t=50, b=20), 
        paper_bgcolor="rgba(0,0,0,0)", 
        font={'color': "white"}
    )
    return fig

def injetar_css_ocultacao(nav_only: bool = False):
    """Injeta estilo CSS para ocultar elementos de navegação do Streamlit."""
    import config
    style = config.STYLE_HIDE_NAV_ONLY if nav_only else config.STYLE_HIDE_SIDEBAR
    st.markdown(style, unsafe_allow_html=True)

def definir_aviso(mensagem: str, tipo: str = "success"):
    """Guarda uma mensagem para ser exibida após o próximo st.rerun()."""
    st.session_state["_aviso_pendente"] = (tipo, mensagem)

def exibir_aviso():
    """Exibe (uma única vez) a mensagem guardada por definir_aviso()."""
    aviso = st.session_state.pop("_aviso_pendente", None)
    if aviso:
        tipo, mensagem = aviso
        getattr(st, tipo, st.info)(mensagem)

# ==========================================
# FILTROS GLOBAIS (barra lateral; valem para Dashboard e Lançamento)
# ==========================================
FILTROS_GLOBAIS = [
    ("pessoa_responsavel", "Responsável", "filtro_responsavel"),
    ("status", "Status", "filtro_status"),
]

def renderizar_filtros_globais(df):
    """Desenha os filtros na barra lateral; a escolha fica na sessão e persiste entre páginas."""
    st.sidebar.markdown("**🔎 Filtros Globais**")
    for coluna, rotulo, chave in FILTROS_GLOBAIS:
        if coluna not in df.columns:
            continue
        opcoes = ["Todos"] + sorted(df[coluna].dropna().unique().tolist())
        atual = st.session_state.get(chave, "Todos")
        if atual not in opcoes:
            atual = "Todos"
        st.session_state[chave] = st.sidebar.selectbox(rotulo, opcoes, index=opcoes.index(atual))
    if any(st.session_state.get(chave, "Todos") != "Todos" for _, _, chave in FILTROS_GLOBAIS):
        if st.sidebar.button("Limpar filtros", use_container_width=True):
            for _, _, chave in FILTROS_GLOBAIS:
                st.session_state[chave] = "Todos"
            st.rerun()

def aplicar_filtros_globais(df):
    """Retorna o DataFrame filtrado pelos filtros globais escolhidos na barra lateral."""
    for coluna, _, chave in FILTROS_GLOBAIS:
        valor = st.session_state.get(chave, "Todos")
        if valor != "Todos" and coluna in df.columns:
            df = df[df[coluna] == valor]
    return df

def descrever_filtros_ativos():
    """Texto curto com os filtros ativos (ou vazio)."""
    ativos = [f"{rotulo}: {st.session_state[chave]}" for _, rotulo, chave in FILTROS_GLOBAIS
              if st.session_state.get(chave, "Todos") != "Todos"]
    return " · ".join(ativos)
