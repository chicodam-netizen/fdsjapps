import streamlit as st
import db_client
import auth

# Minha Conta: dados do usuário logado e troca da própria senha

def main():
    auth.exigir_login()
    conn = db_client.obter_conexao()

    st.title("🔑 Minha Conta")
    perfil = "Administrador" if st.session_state.get("is_admin") else "Usuário"
    st.markdown(
        f"**Nome:** {st.session_state.user_nome}  \n"
        f"**E-mail:** {st.session_state.user_email}  \n"
        f"**Perfil:** {perfil}"
    )

    st.subheader("Alterar senha")
    with st.form("form_alterar_senha", clear_on_submit=True):
        senha_atual = st.text_input("Senha atual", type="password")
        nova_senha = st.text_input("Nova senha", type="password", help="Mínimo 6 caracteres")
        confirmar_senha = st.text_input("Confirmar nova senha", type="password")
        if st.form_submit_button("Alterar Senha", use_container_width=True):
            if nova_senha != confirmar_senha:
                st.error("As senhas não coincidem")
            elif len(nova_senha) < 6:
                st.error("A nova senha deve ter no mínimo 6 caracteres")
            else:
                with st.spinner("Alterando senha..."):
                    sucesso, mensagem = db_client.alterar_propria_senha(conn, st.session_state.user_id, senha_atual, nova_senha)
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)

main()
