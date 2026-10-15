import streamlit as st
import db_client
import auth

# Administração de usuários (somente administradores; login e menu ficam em main.py)

def main():
    auth.exigir_admin()
    conn = db_client.obter_conexao()

    st.title("👥 Administração")

    tab_criar, tab_listar = st.tabs([
        "Criar novo usuário",
        "Listar / Alterar senha de usuários",
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
            df_exibir = df_usuarios[['id', 'email', 'nome_completo']].copy()
            df_exibir['perfil'] = df_usuarios['is_admin'].map(lambda a: 'Administrador' if a else 'Usuário')
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
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

main()
