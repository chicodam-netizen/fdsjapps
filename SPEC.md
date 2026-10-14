# Especificação Técnica – Sistema de Gestão Industrial QRZ

## 1. Visão Geral
O **Sistema Integrado QRZ** é uma aplicação web desenvolvida com Streamlit para o controle industrial e gestão de backlog de tarefas baseado em metodologias de qualidade (ISO 9001) e matrizes de decisão (GUT e REI). O sistema utiliza o Supabase como banco de dados persistente para autenticação, controle de usuários e armazenamento do backlog de tarefas, e integra um assistente de IA com a API da Groq para suporte à tomada de decisão.

---

## 2. Requisitos Funcionais

### RF01 – Autenticação e Gestão de Sessão
- O sistema deve restringir o acesso às telas internas (`analise.py` e `entrada.py`) para usuários autenticados.
- O controle de sessão deve ser mantido utilizando `st.session_state` (`authenticated`, `user_email`, `user_id`, `user_nome`).
- As senhas dos usuários devem ser armazenadas com segurança no banco de dados utilizando hash criptográfico PBKDF2 com salt de 16 bytes gerado dinamicamente.
- O sistema deve conter mecanismo de logout para limpar a sessão e redirecionar para a tela de login.

### RF02 – Gestão Administrativa de Usuários
- Apenas usuários com a flag `is_admin = True` no banco de dados podem acessar o painel administrativo (`usuarios.py`).
- O administrador deve poder cadastrar novos usuários (não admins), listar usuários cadastrados e redefinir a senha de qualquer usuário.
- O administrador deve poder alterar sua própria senha mediante confirmação da senha atual.
- O sistema deve conter fluxo para redefinição de senha esquecida via código de recuperação gerado aleatoriamente com validade de 15 minutos, enviado **exclusivamente por e-mail (SMTP)** — o código nunca é exibido na tela. As mensagens não revelam se o e-mail está cadastrado, e após 5 códigos incorretos o código é cancelado.
- O login aceita o e-mail sem diferenciar maiúsculas/minúsculas e responde com mensagem única para e-mail ou senha inválidos.
- Não há senha padrão no código: o administrador inicial, se necessário, é definido em `[admin_inicial]` nos secrets.

### RF03 – Gestão do Backlog de Tarefas (CRUD)
- O sistema deve permitir o cadastro de novas tarefas contendo:
  - Título da Tarefa
  - Setor (Grooming Detalhamento)
  - Pessoa Responsável
  - Origem da Demanda (Não Conformidade)
  - Status Inicial ("Em Andamento", "Atrasada", "Concluida")
  - Detalhamento das Ações
  - Data de Previsão de Conclusão e Data de Conclusão (caso concluída)
  - Índices de priorização (REI e GUT) de 1 a 5
- O sistema deve permitir buscar e filtrar tarefas por qualquer um dos atributos textuais.
- O sistema deve permitir editar qualquer tarefa do backlog atualizando as datas de conclusão automaticamente caso o status seja alterado para "Concluida".
- A seleção da tarefa a editar/excluir exibe ID, título, responsável e status, e respeita a busca.
- Uma tarefa concluída pode ser reaberta mudando o status; a data de conclusão é então removida.
- Após salvar, cadastrar ou excluir, a lista reflete a alteração imediatamente (o cache é descartado) e uma mensagem de confirmação é exibida.
- Campos vazios são exibidos como "Não Atribuído" apenas na visualização; esse texto nunca é gravado no banco.
- O sistema deve permitir a exclusão definitiva de registros, mediante confirmação explícita.

### RF04 – Cálculo de Priorização (Matrizes GUT e REI)
- O sistema deve calcular automaticamente os índices das matrizes após entrada do usuário:
  - **Matriz REI** (Resultado, Execução, Investimento): $REI = Resultado \times Execução \times Investimento$.
  - **Matriz GUT** (Gravidade, Urgência, Tendência): $GUT = Gravidade \times Urgência \times Tendência$.
  - **Prioridade Geral**: $Soma = REI + GUT$.
- O sistema deve sinalizar em destaque (card de atenção/alerta) qualquer tarefa com pontuação de prioridade geral superior a 80 ou que esteja com status "Atrasada".

### RF05 – Painel de Visualização e Dashboard
- Exibição de cartões de métricas gerais: Total de tarefas, Concluídas, Em Andamento e Atrasadas.
- Exibição de gráficos de gauge (Plotly) de Conclusão Geral, Progresso Médio, Média GUT e Média REI.
- Gráfico de barras horizontais indicando o percentual de progresso das 10 principais tarefas.
- Gráfico Treemap agrupando tarefas por status, responsável e tamanho ponderado pela pontuação de prioridade.
- Dispersão GUT (Gráfico de bolhas Plotly) correlacionando Gravidade, Urgência e Tendência.

### RF06 – Assistente de Inteligência Artificial (Chat)
- O sistema deve disponibilizar um chat de IA integrado à API da Groq utilizando o modelo `openai/gpt-oss-120b` (ou modelo configurado em secrets).
- O assistente de IA deve ser instruído a responder com foco em gestão industrial, normas ISO 9001, e metodologias GUT/REI com base no backlog do usuário (fornecido em formato CSV resumido).

---

## 3. Requisitos Não Funcionais

- **Segurança**: Criptografia de senhas (PBKDF2 + SHA-256 + Salt) na camada de banco de dados e proteção de rotas através do bloqueio da barra lateral de navegação padrão.
- **Desempenho**: Cache inteligente (`st.cache_data`) com tempo de expiração (TTL) de 60 segundos para as consultas ao banco do Supabase para evitar chamadas excessivas em cada ciclo de renderização do Streamlit.
- **Usabilidade**: Barra lateral minimalista sem a navegação integrada do Streamlit para evitar burlar telas de autenticação.
- **Portabilidade**: Funcionamento garantido em Windows/Linux e compatibilidade de dependências descrita em `requirements.txt`.

---

## 4. Arquitetura de Módulos (Spec-Driven)

```
d:\FD_CONSULTORIA\DESENVOLVIMENTO\QRZ/
├── config.py             # Constantes, strings CSS de ocultação de UI, nomes de tabelas.
├── db_client.py          # Lógica centralizada de acesso ao Supabase (CRUD, Hashing, Auth).
├── auth.py               # Lógica de session_state do Streamlit e telas reutilizáveis de Login.
├── ui_components.py      # Componentes compartilhados da interface (CSS customizado, Gauges).
├── main.py               # Ponto de acesso unificado de roteamento.
└── pages/
    ├── usuarios.py       # Painel do administrador (Gestão de Usuários).
    ├── analise.py        # Dashboard avançado e Chatbot IA.
    └── entrada.py        # Módulo de CRUD de Backlog (Gestão de Tarefas).
```
