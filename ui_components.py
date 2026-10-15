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

# ==========================================
# TELA DE LOGIN (estilo restrito à página de login)
# ==========================================
def _logo_base64(caminho="logo.png", lado=96):
    """Logo reduzido em base64 (evita enviar a imagem original de 600 px)."""
    import base64, io
    from PIL import Image
    try:
        img = Image.open(caminho).convert("RGB")
        img.thumbnail((lado, lado))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""

def injetar_estilo_login():
    """Fundo escuro, marca no canto superior esquerdo e cartão de login com moldura."""
    logo = _logo_base64()
    marca_img = f'<img src="data:image/png;base64,{logo}" alt="QRZ">' if logo else ""
    st.markdown(f"""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}
    [data-testid="stAppViewContainer"] {{
        background: radial-gradient(circle at 50% 35%, #0d2150 0%, #061233 45%, #020a21 100%);
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    .block-container {{ padding-top: 5.5rem; }}

    .qrz-marca {{
        position: fixed; top: 14px; left: 20px; z-index: 1000;
        display: flex; align-items: center; gap: 10px;
    }}
    .qrz-marca img {{
        width: 52px; height: 52px; border-radius: 50%;
        box-shadow: 0 0 0 2px rgba(70, 140, 255, .55), 0 4px 14px rgba(0, 0, 0, .45);
    }}
    .qrz-marca .nome {{ color: #ffffff; font-weight: 700; font-size: 1.15rem; line-height: 1.1; }}
    .qrz-marca .sub {{ color: #9db4dc; font-size: .78rem; }}

    [data-testid="stForm"] {{
        background: rgba(13, 24, 48, .92);
        border: 1px solid rgba(120, 160, 230, .22);
        border-radius: 14px;
        padding: 1.8rem 1.6rem 1.2rem;
        box-shadow: 0 18px 45px rgba(0, 0, 0, .45);
    }}
    [data-testid="stForm"] h3 {{ color: #ffffff; text-align: center; margin-bottom: 0; font-size: 1.45rem; padding-top: 0; }}
    [data-testid="stForm"] h3 a, [data-testid="stForm"] [data-testid="stHeaderActionElements"] {{ display: none !important; }}
    [data-testid="stForm"] [data-baseweb="input"] button {{ background: #0a1530 !important; }}
    [data-testid="stForm"] [data-testid="stElementContainer"]:has(button[kind="tertiaryFormSubmit"]),
    [data-testid="stForm"] [data-testid="stElementContainer"]:has(button[kind="tertiaryFormSubmit"]) > div {{
        width: 100% !important; display: flex; justify-content: center;
    }}
    [data-testid="stForm"] p, [data-testid="stForm"] label {{ color: #c9d6ee !important; }}
    [data-testid="stForm"] .qrz-sub {{ text-align: center; color: #8ea3c7 !important; font-size: .9rem; margin-bottom: .6rem; }}
    [data-testid="stForm"] .qrz-versao {{ text-align: center; color: #6c7fa3 !important; font-size: .72rem; letter-spacing: .04em; }}
    [data-testid="stForm"] input {{
        background: #0a1530 !important; color: #ffffff !important;
        border: 1px solid rgba(120, 160, 230, .28) !important; border-radius: 8px !important;
    }}
    [data-testid="stForm"] [data-baseweb="input"], [data-testid="stForm"] [data-baseweb="base-input"] {{
        background: #0a1530 !important; border-radius: 8px !important;
    }}
    [data-testid="stForm"] button[kind="primaryFormSubmit"] {{
        background: #1f6fe5; border: 1px solid #1f6fe5; color: #ffffff; font-weight: 600;
    }}
    [data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {{ background: #3a86f7; border-color: #3a86f7; }}
    [data-testid="stForm"] button[kind="tertiaryFormSubmit"] {{
        color: #8fb8ff !important; text-decoration: underline; margin: 0 auto; display: block;
    }}
    [data-testid="stMarkdownContainer"] a {{ color: #8fb8ff; }}
</style>
<div class="qrz-marca">{marca_img}<div><div class="nome">QRZ</div><div class="sub">Consultorias Industriais</div></div></div>
""", unsafe_allow_html=True)
