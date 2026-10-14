# Guia de Implantação e DevOps – Sistema QRZ

Este documento descreve as etapas de configuração, variáveis de ambiente e procedimentos para rodar localmente ou fazer deploy em produção do **Sistema QRZ**.

---

## 1. Requisitos de Ambiente
* Python 3.9 a 3.11
* Banco de dados Supabase ativo
* API Key do Groq ativa
* Servidor SMTP (opcional para envio real de e-mails de recuperação de senha)

---

## 2. Configuração de Secrets (`.streamlit/secrets.toml`)

Crie o diretório `.streamlit/` no diretório raiz do projeto e adicione o arquivo `secrets.toml` com a estrutura abaixo:

```toml
# Conexão com o Supabase
[connections.supabase]
SUPABASE_URL = "https://<ref-do-projeto>.supabase.co"
# Use a chave SECRETA (service_role, aba Legacy, "eyJ...") - o RLS bloqueia a chave anon/publishable.
# O Streamlit roda no servidor, então esta chave nunca chega ao navegador. Nunca a exponha.
SUPABASE_KEY = "<service_role key>"

# Chave API do Groq
GROQ_API_KEY = "gsk_sua-chave-api-da-groq"

# Servidor SMTP (OBRIGATÓRIO para a recuperação de senha funcionar)
# O código de recuperação é enviado somente por e-mail; nunca aparece na tela.
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587            # 587 = STARTTLS, 465 = SSL
smtp_user = "seu-email@gmail.com"
smtp_password = "sua-senha-de-aplicativo"
# remetente = "QRZ <no-reply@seudominio.com>"   # opcional
# enabled = false                               # opcional: desliga envios reais em testes

# Administrador inicial (opcional) - usado apenas se NÃO existir nenhum admin no banco.
# Depois do primeiro login, troque a senha pelo painel e remova este bloco.
# [admin_inicial]
# email = "admin@suaempresa.com"
# senha = "uma-senha-forte-com-8-ou-mais-caracteres"
# nome = "Administrador"
```

---

## 3. Estrutura do Banco de Dados (Supabase)

Para criar o banco de uma nova instância (uma por empresa), abra o **SQL Editor** do projeto
Supabase e execute o arquivo [`sql/schema.sql`](sql/schema.sql). Ele cria as tabelas, a numeração
automática dos IDs e liga o RLS com acesso restrito ao papel `service_role`.

Resumo das colunas:

### Tabela: `usuarios`
* `id` (int8, Primary Key, Auto-increment)
* `email` (text, Unique)
* `senha_hash` (text)
* `salt` (text)
* `nome_completo` (text)
* `is_admin` (boolean, default: false)
* `last_login` (timestamp with time zone, nullable)
* `reset_code` (text, nullable)
* `reset_expires` (timestamp with time zone, nullable)

### Tabela: `tarefasqrz`
* `id_registro` (int8, Primary Key, Auto-increment)
* `tarefa_product_backlog` (text)
* `setor_grooming_detalhamento` (text)
* `pessoa_responsavel` (text)
* `origem_nao_conformidade` (text)
* `status` (text)
* `detalhamento_acoes` (text)
* `resultado_rei` (numeric)
* `execucao_rei` (numeric)
* `investimento_rei` (numeric)
* `matriz_rei` (numeric)
* `gravidade_gut` (numeric)
* `urgencia_gut` (numeric)
* `tendencia_gut` (numeric)
* `matriz_gut` (numeric)
* `soma_gut_rei` (numeric)
* `data_previsao_conclusao` (date, nullable)
* `data_conclusao` (date, nullable)
* `user_id` (int8, chave estrangeira para `usuarios.id`, nullable)
* `ultimo_usuario_edicao` (text, nullable)
* `data_ultima_edicao` (timestamp with time zone, nullable)

---

## 4. Executando o Projeto Localmente

1. Crie e ative um ambiente virtual do Python:
   ```bash
   python -m venv venv
   # No Windows:
   .\venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o aplicativo principal com o Streamlit:
   ```bash
   streamlit run main.py
   ```

---

## 5. Testes automatizados

Os testes usam um banco falso em memória (não acessam o Supabase):
```bash
pip install pytest
python -m pytest -q tests
```

## 6. Pipeline de CI/CD (GitHub Actions)

A automação do CI/CD verifica a sintaxe Python e roda os testes automatizados sempre que há commits enviados para as branches `main` ou `master`. A configuração do arquivo está em `.github/workflows/ci-cd.yml`.
