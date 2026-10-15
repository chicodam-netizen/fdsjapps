import streamlit as st
import auth
import db_client
import ui_components

# Ponto de entrada único: login -> Dashboard, com menu lateral por perfil
st.set_page_config(
    page_title="Sistema QRZ",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

auth.inicializar_sessao()
conn = db_client.obter_conexao()

PAGINA_DASHBOARD = st.Page("pages/dashboard.py", title="Dashboard de Performance GRC", icon="📊", default=True)
PAGINA_LANCAMENTO = st.Page("pages/lancamento.py", title="Lançamento de Tarefas", icon="📝")
PAGINA_ADMIN = st.Page("pages/administracao.py", title="Administração", icon="👥")
PAGINA_CONTA = st.Page("pages/minha_conta.py", title="Minha Conta", icon="🔑")

# ==========================================
# 1. NÃO AUTENTICADO: apenas a tela de login
# ==========================================
if not st.session_state.authenticated:
    db_client.criar_admin_se_nao_existir(conn)
    auth.renderizar_tela_login(conn)
    st.stop()

# ==========================================
# 2. AUTENTICADO: páginas liberadas conforme o perfil
# ==========================================
eh_admin = st.session_state.get("is_admin", False)
paginas = [PAGINA_DASHBOARD, PAGINA_LANCAMENTO, PAGINA_CONTA] + ([PAGINA_ADMIN] if eh_admin else [])
pagina_atual = st.navigation(paginas, position="hidden")

with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except Exception:
        st.title("QRZ")
    st.markdown(f"**👤 {st.session_state.user_nome}**")
    st.caption(f"{st.session_state.user_email} · {'Administrador' if eh_admin else 'Usuário'}")
    st.divider()

    st.page_link(PAGINA_DASHBOARD, use_container_width=True)
    st.page_link(PAGINA_LANCAMENTO, use_container_width=True)
    if eh_admin:
        st.page_link(PAGINA_ADMIN, use_container_width=True)
    else:
        st.button("👥 Administração", disabled=True, use_container_width=True,
                  help="Disponível apenas para administradores")
    st.divider()

# Filtros globais: só nas páginas que exibem tarefas
if pagina_atual in (PAGINA_DASHBOARD, PAGINA_LANCAMENTO):
    df_filtros = db_client.carregar_dados_backlog(1)
    if not df_filtros.empty:
        ui_components.renderizar_filtros_globais(df_filtros)
        st.sidebar.divider()

with st.sidebar:
    st.page_link(PAGINA_CONTA, use_container_width=True)
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        auth.fazer_logout()
        st.rerun()
    st.caption("Sistema de Gestão QRZ")

pagina_atual.run()
