# Cliente do Banco de Dados Supabase (QRZ)

import streamlit as st
import pandas as pd
import hashlib
import hmac
import secrets
import smtplib
import re
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from st_supabase_connection import SupabaseConnection
import config

# Mensagem neutra: não revela se o e-mail existe ou não no cadastro
MSG_RESET_GENERICA = "Se o e-mail estiver cadastrado, enviamos um código de verificação (válido por 15 minutos)."

# ==========================================
# 1. CONEXÃO SUPABASE
# ==========================================
def obter_conexao():
    """Inicializa e retorna a conexão com o Supabase."""
    try:
        return st.connection("supabase", type=SupabaseConnection)
    except Exception as e:
        st.error(f"Erro de conexão com o banco de dados: {e}")
        st.stop()

# ==========================================
# 2. FUNÇÕES AUXILIARES (SENHA, E-MAIL, DATAS)
# ==========================================
def hash_senha(senha: str, salt: str = None) -> tuple:
    """Gera o hash PBKDF2 com Salt para uma senha."""
    if salt is None:
        salt = secrets.token_hex(16)
    senha_com_salt = senha + salt
    hash_obj = hashlib.pbkdf2_hmac('sha256', senha_com_salt.encode(), salt.encode(), 100000)
    return hash_obj.hex(), salt

def verificar_senha(senha: str, hash_armazenado: str, salt: str) -> bool:
    """Compara uma senha em texto claro com o hash armazenado (comparação em tempo constante)."""
    if not salt or not hash_armazenado:
        return False
    novo_hash, _ = hash_senha(senha, salt)
    return hmac.compare_digest(novo_hash, hash_armazenado)

def normalizar_email(email: str) -> str:
    """Padroniza o e-mail (sem espaços, minúsculo) para cadastro e busca."""
    return (email or "").strip().lower()

def agora_utc() -> datetime:
    """Data/hora atual com fuso UTC (o banco grava timestamptz)."""
    return datetime.now(timezone.utc)

def converter_para_utc(valor: str) -> datetime:
    """Converte um timestamp ISO vindo do banco em datetime com fuso UTC."""
    dt = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def buscar_usuario_por_email(conn, email: str, colunas: str = "*"):
    """Busca um usuário pelo e-mail, ignorando maiúsculas/minúsculas e espaços."""
    email_limpo = (email or "").strip()
    if not email_limpo:
        return None
    candidatos = [normalizar_email(email_limpo)]
    # Cadastros antigos podem ter sido gravados com maiúsculas
    if email_limpo not in candidatos:
        candidatos.append(email_limpo)
    for candidato in candidatos:
        resp = conn.table(config.TABELA_USUARIOS).select(colunas).eq("email", candidato).execute()
        if resp.data:
            return resp.data[0]
    return None

def enviar_email(destinatario: str, assunto: str, corpo: str):
    """Envia e-mail em texto simples via SMTP configurado em secrets [email]."""
    try:
        cfg = st.secrets.get("email", {})
    except Exception:
        cfg = {}
    if not cfg.get("enabled", True):
        print(f"[email desabilitado] Para: {destinatario} | Assunto: {assunto}")
        return False, "Envio de e-mail desabilitado na configuração"

    servidor = cfg.get("smtp_server")
    porta = int(cfg.get("smtp_port", 587))
    usuario = cfg.get("smtp_user")
    senha = cfg.get("smtp_password")
    if not all([servidor, usuario, senha]):
        return False, "SMTP não configurado"

    msg = EmailMessage()
    msg["From"] = cfg.get("remetente", usuario)
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.set_content(corpo)

    try:
        if porta == 465:
            with smtplib.SMTP_SSL(servidor, porta, timeout=20) as server:
                server.login(usuario, senha)
                server.send_message(msg)
        else:
            with smtplib.SMTP(servidor, porta, timeout=20) as server:
                server.starttls()
                server.login(usuario, senha)
                server.send_message(msg)
        return True, ""
    except Exception as e:
        print(f"[email] Falha ao enviar para {destinatario}: {e}")
        return False, str(e)

# ==========================================
# 3. CONTROLE E CRIAÇÃO DE USUÁRIOS
# ==========================================
def criar_admin_se_nao_existir(conn):
    """Cria o administrador inicial a partir de secrets [admin_inicial], se ainda não houver admin."""
    try:
        resp = conn.table(config.TABELA_USUARIOS).select("id").eq("is_admin", True).execute()
        if resp.data:
            return
        try:
            cfg = st.secrets.get("admin_inicial", {})
        except Exception:
            cfg = {}
        email = normalizar_email(cfg.get("email", ""))
        senha = cfg.get("senha", "")
        if not email or len(senha) < 8:
            st.warning("Nenhum administrador cadastrado. Configure [admin_inicial] (email e senha com 8+ caracteres) nos secrets.")
            return
        hash_senha_result, salt = hash_senha(senha)
        novo_admin = {
            "email": email,
            "senha_hash": hash_senha_result,
            "salt": salt,
            "nome_completo": cfg.get("nome", "Administrador"),
            "is_admin": True,
            "two_factor_enabled": False
        }
        conn.table(config.TABELA_USUARIOS).insert(novo_admin).execute()
        st.success(f"✅ Administrador inicial criado: {email}. Faça login com a senha definida nos secrets.")
    except Exception as e:
        st.warning(f"Erro ao verificar/criar administrador padrão: {e}")

def listar_usuarios(conn):
    """Lista todos os usuários comuns e administradores."""
    try:
        resp = conn.table(config.TABELA_USUARIOS).select("id, email, nome_completo, is_admin").execute()
        return pd.DataFrame(resp.data)
    except Exception as e:
        st.error(f"Erro ao obter lista de usuários: {e}")
        return pd.DataFrame()

def criar_usuario(conn, email: str, nome: str, senha: str):
    """Cria um novo usuário comum no banco de dados."""
    try:
        email = normalizar_email(email)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return False, "E-mail inválido"
        if len(senha) < 6:
            return False, "Senha deve ter no mínimo 6 caracteres"
        if len(nome.strip()) < 3:
            return False, "Nome deve ter no mínimo 3 caracteres"

        if buscar_usuario_por_email(conn, email, "id"):
            return False, "E-mail já cadastrado"

        hash_s, salt = hash_senha(senha)
        novo = {
            "email": email,
            "senha_hash": hash_s,
            "salt": salt,
            "nome_completo": nome.strip(),
            "is_admin": False,
            "two_factor_enabled": False
        }
        conn.table(config.TABELA_USUARIOS).insert(novo).execute()
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao criar usuário: {e}"

def alterar_senha_usuario(conn, user_id: int, nova_senha: str):
    """Altera a senha de qualquer usuário (usado por administrador)."""
    try:
        if len(nova_senha) < 6:
            return False, "Senha deve ter no mínimo 6 caracteres"
        novo_hash, novo_salt = hash_senha(nova_senha)
        conn.table(config.TABELA_USUARIOS).update({
            "senha_hash": novo_hash,
            "salt": novo_salt
        }).eq("id", user_id).execute()
        return True, "Senha alterada com sucesso!"
    except Exception as e:
        return False, f"Erro ao alterar senha do usuário: {e}"

def alterar_propria_senha(conn, user_id: int, senha_atual: str, nova_senha: str):
    """Altera a senha do próprio usuário logado, validando a senha atual."""
    try:
        resp = conn.table(config.TABELA_USUARIOS).select("senha_hash, salt").eq("id", user_id).execute()
        if not resp.data:
            return False, "Usuário não encontrado"
        usuario = resp.data[0]
        if not verificar_senha(senha_atual, usuario['senha_hash'], usuario.get('salt', '')):
            return False, "Senha atual incorreta"
        if len(nova_senha) < 6:
            return False, "Nova senha deve ter no mínimo 6 caracteres"
        novo_hash, novo_salt = hash_senha(nova_senha)
        conn.table(config.TABELA_USUARIOS).update({
            "senha_hash": novo_hash,
            "salt": novo_salt
        }).eq("id", user_id).execute()
        return True, "Sua senha foi alterada!"
    except Exception as e:
        return False, f"Erro ao redefinir própria senha: {e}"

# ==========================================
# 4. RECUPERAÇÃO DE SENHA (ADMIN & USUÁRIO)
# ==========================================
def solicitar_reset_senha_generico(conn, email: str, apenas_admin: bool = False):
    """Gera um código de 6 dígitos e o envia por e-mail. Nunca devolve o código para a tela."""
    try:
        usuario = buscar_usuario_por_email(conn, email, "id, email, is_admin")
        if not usuario or (apenas_admin and not usuario.get('is_admin', False)):
            return True, MSG_RESET_GENERICA

        reset_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        expires_at = agora_utc() + timedelta(minutes=15)

        conn.table(config.TABELA_USUARIOS).update({
            "reset_code": reset_code,
            "reset_expires": expires_at.isoformat()
        }).eq("id", usuario['id']).execute()

        corpo = (
            "Olá,\n\n"
            f"Seu código para redefinir a senha do Sistema QRZ é: {reset_code}\n\n"
            "O código é válido por 15 minutos. Se você não solicitou, ignore este e-mail.\n"
        )
        enviado, _ = enviar_email(usuario['email'], "Sistema QRZ - Código de recuperação de senha", corpo)
        if not enviado:
            return False, "Não foi possível enviar o e-mail agora. Tente novamente mais tarde ou procure o administrador."
        return True, MSG_RESET_GENERICA
    except Exception as e:
        return False, f"Erro: {e}"

def invalidar_codigo_reset(conn, email: str):
    """Remove o código de recuperação pendente (ex: após excesso de tentativas)."""
    try:
        usuario = buscar_usuario_por_email(conn, email, "id")
        if usuario:
            conn.table(config.TABELA_USUARIOS).update({
                "reset_code": None,
                "reset_expires": None
            }).eq("id", usuario['id']).execute()
    except Exception as e:
        print(f"[reset] Falha ao invalidar código: {e}")

def redefinir_senha_com_codigo(conn, email: str, code: str, nova_senha: str, apenas_admin: bool = False):
    """Redefine a senha utilizando o código gerado."""
    try:
        usuario = buscar_usuario_por_email(conn, email, "id, is_admin, reset_code, reset_expires")
        if not usuario or (apenas_admin and not usuario.get('is_admin', False)):
            return False, "Código inválido"

        codigo_salvo = usuario.get('reset_code') or ""
        if not codigo_salvo or not hmac.compare_digest(codigo_salvo, (code or "").strip()):
            return False, "Código inválido"
        if not usuario.get('reset_expires') or agora_utc() > converter_para_utc(usuario['reset_expires']):
            return False, "Código expirado. Solicite um novo."

        if len(nova_senha) < 6:
            return False, "Senha deve ter no mínimo 6 caracteres"

        novo_hash, novo_salt = hash_senha(nova_senha)
        conn.table(config.TABELA_USUARIOS).update({
            "senha_hash": novo_hash,
            "salt": novo_salt,
            "reset_code": None,
            "reset_expires": None
        }).eq("id", usuario['id']).execute()
        return True, "Senha redefinida com sucesso! Faça login."
    except Exception as e:
        return False, f"Erro: {e}"

# ==========================================
# 5. CARGA E TRATAMENTO DE DADOS (BACKLOG)
# ==========================================
def limpar_dados(df):
    """Padroniza e trata os dados obtidos da tabela do backlog."""
    if df.empty:
        return df

    # Tratar campos de texto
    colunas_texto = [
        'tarefa_product_backlog', 'setor_grooming_detalhamento',
        'pessoa_responsavel', 'origem_nao_conformidade',
        'status', 'detalhamento_acoes'
    ]
    for coluna in colunas_texto:
        if coluna in df.columns:
            df[coluna] = df[coluna].astype(str).str.strip()
            df[coluna] = df[coluna].str.replace('\n', ' ').str.replace('\r', ' ')
            df[coluna] = df[coluna].str.replace(r'\s+', ' ', regex=True)
            df[coluna] = df[coluna].replace(['nan', 'null', 'None', 'NaN'], '')
            df[coluna] = df[coluna].replace('', config.TEXTO_NAO_ATRIBUIDO)

    # Padronizar Status
    if 'status' in df.columns:
        df['status'] = df['status'].replace({
            'finalizada': 'Concluida', 'Finalizada': 'Concluida',
            'concluida': 'Concluida', 'concluído': 'Concluida',
            'em andamento': 'Em Andamento', 'Em andamento': 'Em Andamento',
            'atrasada': 'Atrasada', 'atrasado': 'Atrasada'
        })

    # Tratar campos numéricos
    colunas_inteiras = [
        'resultado_rei', 'execucao_rei', 'investimento_rei', 'matriz_rei',
        'gravidade_gut', 'urgencia_gut', 'tendencia_gut', 'matriz_gut',
        'soma_gut_rei', 'percentual_ok'
    ]
    for col in colunas_inteiras:
        if col in df.columns:
            # fillna(0) para fins analíticos, coerção e arredondamento
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round().astype(int)

    # Tratar datas
    colunas_data = ['data_previsao_conclusao', 'data_conclusao', 'data_criacao']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calcular Atrasos de tarefas pendentes
    hoje = pd.Timestamp(datetime.now().date())
    if 'data_previsao_conclusao' in df.columns and 'data_conclusao' in df.columns and 'status' in df.columns:
        mascara_atraso = (
            df['data_conclusao'].isna() &
            df['data_previsao_conclusao'].notna() &
            (df['data_previsao_conclusao'] < hoje) &
            (df['status'] != 'Concluida')
        )
        df.loc[mascara_atraso, 'status'] = 'Atrasada'

    return df

@st.cache_data(ttl=60)
def carregar_dados_backlog(conn_hash):
    """Carrega dados da tabela tarefasqrz utilizando cache de 60s."""
    # conn_hash é necessário para invalidar/utilizar cache do Streamlit de maneira estável
    try:
        conn = obter_conexao()
        response = conn.table(config.TABELA_TAREFAS).select("*").execute()
        df = pd.DataFrame(response.data)
        return limpar_dados(df)
    except Exception as e:
        st.error(f"Erro ao carregar dados do backlog: {e}")
        return pd.DataFrame()

def limpar_cache_backlog():
    """Descarta o cache do backlog para que a próxima leitura reflita gravações recentes."""
    carregar_dados_backlog.clear()
