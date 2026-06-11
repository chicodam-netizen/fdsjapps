import streamlit as st

# Configuração da página sem barra lateral (sidebar colapsada e sem conteúdo)
st.set_page_config(
    page_title="Sistema QRZ - Acesso",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Remove a barra lateral completamente (opcional, mas com 'collapsed' ela some)
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True
)

# Logo na tela principal (centralizada)
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("*(Logo não encontrada)*")

# Título e descrição
st.title("🏭 Sistema Integrado QRZ")
st.markdown("Selecione o módulo desejado:")

# Botões de navegação (sem duplicação de ícones)
col1, col2, col3 = st.columns(3)

with col1:
    st.page_link(
        "pages/usuarios.py",
        label="Administrador",
        icon="👥",
        use_container_width=True
    )

with col2:
    st.page_link(
        "pages/analise.py",
        label="Visualização",
        icon="📊",
        use_container_width=True
    )

with col3:
    st.page_link(
        "pages/entrada.py",
        label="Entrada",
        icon="📝",
        use_container_width=True
    )

st.markdown("---")
st.caption("Sistema de Gestão QRZ - v1.0")