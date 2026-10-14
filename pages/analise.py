import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
import warnings
import db_client
import auth
import ui_components

# ==========================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==========================================
warnings.filterwarnings('ignore')
st.set_page_config(
    page_title="Controle Industrial - QRZ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Oculta a navegação padrão do Streamlit na barra lateral
ui_components.injetar_css_ocultacao(nav_only=True)

# --- CONFIGURAÇÃO GROQ ---
try:
    API_KEY_GROQ = st.secrets["GROQ_API_KEY"]
except Exception:
    API_KEY_GROQ = ""
    st.error("Chave API do Groq não configurada nos segredos (secrets.toml).")

# ==========================================
# 2. FLUXO PRINCIPAL
# ==========================================
def main():
    conn = db_client.obter_conexao()
    auth.inicializar_sessao()

    # Redireciona para login se não autenticado
    if not st.session_state.authenticated:
        auth.renderizar_tela_login(conn, apenas_admin=False)
        return

    # Sidebar do Usuário Autenticado
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.title("QRZ Analytics")
    
    st.sidebar.markdown(f"### 👤 {st.session_state.user_nome}")
    st.sidebar.markdown(f"📧 {st.session_state.user_email}")
    
    menu_usuario = st.sidebar.selectbox("Menu", ["📊 Dashboard", "🔑 Alterar Senha"])
    
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        auth.fazer_logout(apenas_admin=False)
        st.rerun()
    
    st.sidebar.divider()
    
    # Rota: Alteração de Senha
    if menu_usuario == "🔑 Alterar Senha":
        st.title("🔑 Alterar Senha")
        with st.form("form_alterar_senha"):
            senha_atual = st.text_input("Senha atual", type="password")
            nova_senha = st.text_input("Nova senha", type="password", help="Mínimo 6 caracteres")
            confirmar_senha = st.text_input("Confirmar nova senha", type="password")
            
            if st.form_submit_button("Alterar Senha", use_container_width=True):
                if nova_senha == confirmar_senha:
                    if len(nova_senha) >= 6:
                        with st.spinner("Alterando senha..."):
                            sucesso, mensagem = db_client.alterar_propria_senha(conn, st.session_state.user_id, senha_atual, nova_senha)
                            if sucesso:
                                st.success(mensagem)
                                st.balloons()
                            else:
                                st.error(mensagem)
                    else:
                        st.error("A nova senha deve ter no mínimo 6 caracteres")
                else:
                    st.error("As senhas não coincidem")
        return

    # Rota: Dashboard e Análise
    st.title("📊 Dashboard de Performance GRC")
    
    st.sidebar.header("🔎 Filtros Globais")
    df = db_client.carregar_dados_backlog(1)
    if df.empty:
        st.info("Sem dados para exibir.")
        return
    
    # Filtros na sidebar
    lista_resp = ["Todos"] + sorted(df['pessoa_responsavel'].unique().tolist())
    filtro_resp = st.sidebar.selectbox("Responsável", lista_resp)
    lista_status = ["Todos"] + sorted(df['status'].unique().tolist())
    filtro_status = st.sidebar.selectbox("Status", lista_status)
    
    df_filtered = df.copy()
    if filtro_resp != "Todos":
        df_filtered = df_filtered[df_filtered['pessoa_responsavel'] == filtro_resp]
    if filtro_status != "Todos":
        df_filtered = df_filtered[df_filtered['status'] == filtro_status]
    
    # Abas do Dashboard
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Visão Geral e Métricas", "🔥 Priorização GUT", 
        "💎 Análise REI", "⚠️ Tarefas Críticas", "🤖 Chat IA"
    ])
    
    with tab1:
        st.subheader("Visão Geral Detalhada")
        df_display = df_filtered.copy()
        
        mapa_colunas = {
            'id_registro': 'ID',
            'tarefa_product_backlog': 'Tarefa',
            'pessoa_responsavel': 'Responsável',
            'percentual_ok': 'Progresso',
            'status': 'Status',
            'data_previsao_conclusao': 'Previsão'
        }
        cols_para_mostrar = [c for c in mapa_colunas.keys() if c in df_display.columns]
        df_final = df_display[cols_para_mostrar].rename(columns=mapa_colunas)
        st.dataframe(
            df_final,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d", width="small"),
                "Tarefa": st.column_config.TextColumn("Tarefa", width="large"),
                "Progresso": st.column_config.ProgressColumn("Progresso", format="%d%%", min_value=0, max_value=100),
                "Previsão": st.column_config.DateColumn("Previsão", format="YYYY-MM-DD")
            },
            use_container_width=True,
            hide_index=True
        )
        st.markdown("---")
        st.subheader("📈 Métricas de Performance")
        total = len(df_filtered)
        concluidas = len(df_filtered[(df_filtered['percentual_ok'] >= 100) | (df_filtered['status'] == 'Concluida')])
        perc_geral = (concluidas / total * 100) if total > 0 else 0
        prog_medio = df_display['percentual_ok'].mean() if total > 0 else 0
        med_gut = df_filtered['matriz_gut'].mean() if 'matriz_gut' in df_filtered.columns else 0
        med_rei = df_filtered['matriz_rei'].mean() if 'matriz_rei' in df_filtered.columns else 0
        
        g1, g2, g3, g4 = st.columns(4)
        with g1: st.plotly_chart(ui_components.criar_gauge(perc_geral, "Conclusão Geral (%)", 100, "#4CAF50"), use_container_width=True)
        with g2: st.plotly_chart(ui_components.criar_gauge(prog_medio, "Progresso Médio (%)", 100, "#2196F3"), use_container_width=True)
        with g3: st.plotly_chart(ui_components.criar_gauge(med_gut, "Média GUT", 125, "#FFC107"), use_container_width=True)
        with g4: st.plotly_chart(ui_components.criar_gauge(med_rei, "Média REI", 125, "#E91E63"), use_container_width=True)
        
        st.subheader("📊 Visualizações Avançadas")
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.markdown("**Top Tarefas por Percentual**")
            df_top = df_display.nlargest(10, 'percentual_ok').sort_values('percentual_ok', ascending=True)
            fig_bar = px.bar(df_top, x="percentual_ok", y="tarefa_product_backlog", orientation='h', 
                             text="percentual_ok", color="percentual_ok", color_continuous_scale="Viridis")
            fig_bar.update_layout(showlegend=False, yaxis={'title': ''})
            fig_bar.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.markdown("**Distribuição de Ocorrências**")
            if 'soma_gut_rei' not in df_filtered.columns: 
                df_filtered['soma_gut_rei'] = 1
            fig_tree = px.treemap(df_filtered, path=[px.Constant("Todas"), 'status', 'tarefa_product_backlog'], 
                                  values='soma_gut_rei', color='percentual_ok', color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_tree, use_container_width=True)
    
    with tab2:
        st.subheader("🎯 Priorização GUT")
        fig_gut = px.scatter(df_filtered, x="gravidade_gut", y="urgencia_gut", size="tendencia_gut", 
                             color="status", hover_data=["tarefa_product_backlog"], title="Dispersão GUT")
        st.plotly_chart(fig_gut, use_container_width=True)
        st.subheader("Top 10 Tarefas por Prioridade GUT")
        top_gut = df_filtered.nlargest(10, 'matriz_gut')[['tarefa_product_backlog', 'pessoa_responsavel', 'matriz_gut', 'status']]
        st.dataframe(top_gut, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("📊 Análise REI")
        fig_rei = px.bar(df_filtered.head(15), x="tarefa_product_backlog", y=["resultado_rei", "execucao_rei", "investimento_rei"], 
                         title="Composição REI", barmode='group')
        st.plotly_chart(fig_rei, use_container_width=True)
        st.subheader("Top 10 Tarefas por Prioridade REI")
        top_rei = df_filtered.nlargest(10, 'matriz_rei')[['tarefa_product_backlog', 'pessoa_responsavel', 'matriz_rei', 'status']]
        st.dataframe(top_rei, use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("🚨 Atenção Imediata")
        criticas = df_filtered[(df_filtered['soma_gut_rei'] > 80) | (df_filtered['status'] == 'Atrasada')]
        if not criticas.empty:
            st.warning(f"⚠️ {len(criticas)} tarefas requerem atenção imediata!")
            st.dataframe(criticas[['tarefa_product_backlog', 'pessoa_responsavel', 'status', 'soma_gut_rei']], 
                        use_container_width=True, hide_index=True)
        else:
            st.success("✅ Nenhuma tarefa crítica encontrada!")
    
    with tab5:
        st.subheader("🤖 Assistente IA - Análise de Dados")
        p = st.chat_input("Pergunte sobre os dados...")
        if p:
            st.chat_message("user").write(p)
            try:
                client = Groq(api_key=API_KEY_GROQ)
                csv_mini = df_filtered[['tarefa_product_backlog', 'status', 'percentual_ok', 'pessoa_responsavel']].head(50).to_csv(index=False)
                system_prompt = """
## INSTRUÇÕES PARA RESPOSTA
Com base nos dados acima, responda à pergunta de forma clara e objetiva.
- Use as metodologias ISO 9001, Matriz GUT e Matriz REI como referência
- Use os números exatos fornecidos
- Sugira priorizações baseadas na matriz GUT
- Considere o impacto/esforço pela matriz REI
- Seja específico nas recomendações para a certificação ISO 9001
- Se perguntar sobre outro assunto, responda: "Desculpe, somente posso responder sobre ISO 9001, Matriz GUT e REI", a não ser se pedir o diagrama de pareto ou similar.
- Se perguntar sobre quem é você, responda: "Sou a IA de apoio à gestão para Implementação da Gestão Industrial - QRZ Consultoria"
- Responder sobre o diagrama de pareto das tarefas
Seja sempre cordial!
"""
                msg = f"Dados resumidos do dashboard:\n{csv_mini}\n\nPergunta do usuário: {p}"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": msg}
                ]
                r = client.chat.completions.create(
                    messages=messages, 
                    model="openai/gpt-oss-120b",
                    temperature=0.7,
                    max_tokens=2000
                )
                st.chat_message("assistant").write(r.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro na IA: {e}")

    # Voltar ao menu principal no rodapé da sidebar
    st.sidebar.divider()
    if st.sidebar.button("← Voltar ao menu principal", use_container_width=True):
        st.switch_page("main.py")

if __name__ == "__main__":
    main()