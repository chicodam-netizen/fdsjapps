import streamlit as st
import pandas as pd
import db_client
import auth
import ui_components

# ==========================================
# 1. CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(
    page_title="Admin - Gestão de Usuários",
    page_icon="👥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Oculta a navegação padrão do Streamlit na barra lateral
ui_components.injetar_css_ocultacao(nav_only=True)

# ==========================================
# 2. PAINEL ADMINISTRATIVO (APÓS LOGIN)
# ==========================================
def painel_admin(conn):
    st.title(f"👋 Olá, {st.session_state.admin_user['nome']}!")
    
    st.sidebar.write(f"**Admin:** {st.session_state.admin_user['email']}")

    tab_criar, tab_listar, tab_minha_senha, tab_sair = st.tabs([
        "Criar novo usuário", 
        "Listar / Alterar senha de usuários", 
        "Alterar minha senha", 
        "Sair"
    ])

    with tab_criar:
        st.header("➕ Criar novo usuário")
        with st.form("criar_usuario"):
            nome = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password", help="Mínimo 6 caracteres")
            if st.form_submit_button("Criar usuário"):
                sucesso, msg = db_client.criar_usuario(conn, email, nome, senha)
                if sucesso:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)

    with tab_listar:
        st.header("📋 Gerenciar usuários")
        df_usuarios = db_client.listar_usuarios(conn)
        if df_usuarios.empty:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            # Exibe tabela com todos os usuários
            st.dataframe(df_usuarios[['id', 'email', 'nome_completo']], use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("🔧 Alterar senha de um usuário")
            # Selectbox com nomes
            usuario_opcoes = {f"{row['nome_completo']} ({row['email']})": row['id'] for _, row in df_usuarios.iterrows()}
            escolha = st.selectbox("Selecione o usuário", list(usuario_opcoes.keys()))
            user_id = usuario_opcoes[escolha]
            nova_senha = st.text_input("Nova senha", type="password", key="nova_senha_admin")
            if st.button("Alterar senha"):
                if nova_senha:
                    sucesso, msg = db_client.alterar_senha_usuario(conn, user_id, nova_senha)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Digite a nova senha")

    with tab_minha_senha:
        st.header("🔑 Alterar sua própria senha")
        with st.form("alterar_minha_senha"):
            atual = st.text_input("Senha atual", type="password")
            nova = st.text_input("Nova senha", type="password", help="Mínimo 6 caracteres")
            confirmar = st.text_input("Confirmar nova senha", type="password")
            if st.form_submit_button("Alterar"):
                if nova == confirmar:
                    if nova:
                        sucesso, msg = db_client.alterar_propria_senha(
                            conn,
                            st.session_state.admin_user['id'],
                            atual,
                            nova
                        )
                        if sucesso:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Digite a nova senha")
                else:
                    st.error("As senhas não coincidem")

    with tab_sair:
        st.header("🚪 Sair do painel")
        st.write("Tem certeza que deseja sair do painel administrativo?")
        if st.button("Confirmar Saída", use_container_width=True):
            auth.fazer_logout(apenas_admin=True)
            st.rerun()

# ==========================================
# 3. FLUXO PRINCIPAL
# ==========================================
def main():
    conn = db_client.obter_conexao()
    db_client.criar_admin_se_nao_existir(conn)
    auth.inicializar_sessao()

    if not st.session_state.admin_authenticated:
        auth.renderizar_tela_login(conn, apenas_admin=True)
    else:
        painel_admin(conn)

    # Voltar ao menu principal no rodapé da sidebar
    st.sidebar.divider()
    if st.sidebar.button("← Voltar ao menu principal", use_container_width=True):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()