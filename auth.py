# Módulo de Autenticação e Sessão (QRZ)

import streamlit as st
from PIL import Image
import db_client
import config
import ui_components

def inicializar_sessao():
    """Garante que todas as chaves de sessão necessárias estão inicializadas."""
    # Autenticação de usuário comum
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_nome' not in st.session_state:
        st.session_state.user_nome = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False

    # Tentativas de login e reset de senha
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = {}
    if 'reset_step' not in st.session_state:
        st.session_state.reset_step = None  # 'request', 'verify'
    if 'reset_email' not in st.session_state:
        st.session_state.reset_email = None
    if 'reset_code' not in st.session_state:
        st.session_state.reset_code = None

def fazer_logout():
    """Limpa o estado de autenticação."""
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.session_state.user_nome = None
    st.session_state.is_admin = False
    st.session_state.reset_step = None
    st.session_state.reset_email = None
    st.session_state.reset_code = None

def exigir_login():
    """Interrompe a página se não houver usuário autenticado."""
    inicializar_sessao()
    if not st.session_state.authenticated:
        st.warning("Faça login para acessar esta página.")
        st.stop()

def exigir_admin():
    """Interrompe a página se o usuário não for administrador."""
    exigir_login()
    if not st.session_state.get('is_admin', False):
        st.error("🔒 Acesso permitido apenas para administradores.")
        st.stop()

MAX_TENTATIVAS_CODIGO = 5

def _voltar_ao_login():
    st.session_state.reset_step = None
    st.session_state.reset_email = None
    st.session_state.reset_tentativas = 0

def renderizar_tela_login(conn):
    """Tela única de login (todos os perfis) com recuperação de senha, centralizada."""
    inicializar_sessao()
    _, centro, _ = st.columns([1, 1.4, 1])
    with centro:
        _conteudo_login(conn)

def _conteudo_login(conn):
    try:
        st.image(Image.open("logo.png"), use_container_width=True)
    except Exception:
        pass
    st.title("🔐 Sistema de Acesso QRZ")
    st.markdown("Faça login para acessar o sistema")

    ui_components.exibir_aviso()

    # FLUXO DE RECUPERAÇÃO DE SENHA (Etapa: Verificação do Código)
    if st.session_state.reset_step == "verify":
        st.subheader("🔑 Redefinir senha")
        st.caption("Digite o código de 6 dígitos enviado para o seu e-mail.")
        with st.form("form_reset_verify"):
            email = st.text_input("E-mail", value=st.session_state.reset_email, disabled=True)
            code = st.text_input("Código de verificação", placeholder="Digite o código recebido")
            nova_senha = st.text_input("Nova senha", type="password", placeholder="Mínimo 6 caracteres")
            confirmar = st.text_input("Confirmar nova senha", type="password")

            if st.form_submit_button("Redefinir senha", use_container_width=True):
                if code and nova_senha and confirmar:
                    if nova_senha != confirmar:
                        st.error("As senhas não coincidem")
                    elif len(nova_senha) < 6:
                        st.error("A senha deve ter no mínimo 6 caracteres")
                    else:
                        # Verifica o código e redefine a senha
                        sucesso, msg = db_client.redefinir_senha_com_codigo(
                            conn, email, code, nova_senha
                        )
                        if sucesso:
                            _voltar_ao_login()
                            ui_components.definir_aviso(msg)
                            st.rerun()
                        else:
                            st.session_state.reset_tentativas = st.session_state.get('reset_tentativas', 0) + 1
                            if st.session_state.reset_tentativas >= MAX_TENTATIVAS_CODIGO:
                                db_client.invalidar_codigo_reset(conn, email)
                                _voltar_ao_login()
                                ui_components.definir_aviso("Muitas tentativas inválidas. O código foi cancelado; solicite um novo.", "error")
                                st.rerun()
                            st.error(msg)
                else:
                    st.warning("Preencha todos os campos")

        if st.button("Voltar ao login"):
            _voltar_ao_login()
            st.rerun()
        return

    # FLUXO DE LOGIN NORMAL
    with st.form("form_login"):
        email = st.text_input("E-mail", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password", placeholder="••••••••")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_login = st.form_submit_button("Entrar", use_container_width=True)
        with col2:
            submit_reset_req = st.form_submit_button("Esqueci minha senha", use_container_width=True)

        # Tratar solicitação de recuperação de senha
        if submit_reset_req:
            if email:
                with st.spinner("Enviando código..."):
                    sucesso, resultado = db_client.solicitar_reset_senha_generico(conn, email)
                if sucesso:
                    st.session_state.reset_step = "verify"
                    st.session_state.reset_email = db_client.normalizar_email(email)
                    st.session_state.reset_tentativas = 0
                    ui_components.definir_aviso(resultado, "info")
                    st.rerun()
                else:
                    st.error(resultado)
            else:
                st.warning("Por favor, digite o e-mail no campo acima antes de clicar em Esqueci minha senha.")

        # Tratar login
        if submit_login:
            if email and senha:
                with st.spinner("Autenticando..."):
                    try:
                        usuario = db_client.buscar_usuario_por_email(conn, email)

                        # Mensagem única para e-mail inexistente ou senha errada
                        if not usuario or not db_client.verificar_senha(senha, usuario.get('senha_hash'), usuario.get('salt', '')):
                            st.error("E-mail ou senha inválidos")
                            return

                        conn.table(config.TABELA_USUARIOS).update({
                            "last_login": db_client.agora_utc().isoformat()
                        }).eq("id", usuario['id']).execute()

                        st.session_state.authenticated = True
                        st.session_state.user_email = usuario['email']
                        st.session_state.user_id = usuario['id']
                        st.session_state.user_nome = usuario.get('nome_completo', 'Usuário')
                        st.session_state.is_admin = bool(usuario.get('is_admin', False))

                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro no processo de login: {e}")
            else:
                st.warning("Preencha e-mail e senha")
