import streamlit as st
import pandas as pd
import plotly.express as px
import db_client
import auth
import config
import ui_components
from datetime import datetime

# Lançamento de Tarefas (login, menu e filtros ficam em main.py)

STATUS_LISTA = ["Em Andamento", "Atrasada", "Concluida"]

# ==========================================
# 2. FUNÇÕES COMPARTILHADAS (MATRIZ E STATUS)
# ==========================================
def calcular_metricas(r, e, i, g, u, t):
    m_rei = r * e * i
    m_gut = g * u * t
    return m_rei, m_gut, (m_rei + m_gut)

def cor_status(val):
    if val == "Atrasada":
        color = "#ff4b4b"
    elif val == "Em Andamento":
        color = "#faca2b"
    elif val == "Concluida":
        color = "#00c853"
    else:
        color = "#333333"
    return f'background-color: {color}; color: white; font-weight: bold'

def texto_campo(dados, coluna):
    """Valor de texto para o formulário; o rótulo 'Não Atribuído' é só visual e vira vazio."""
    valor = dados.get(coluna, '')
    if pd.isna(valor) or str(valor).strip() in ('', config.TEXTO_NAO_ATRIBUIDO, 'nan', 'None'):
        return ''
    return str(valor)

def nota_campo(dados, coluna):
    """Nota GUT/REI válida (1 a 5) para o slider; valores vazios/zerados usam 3."""
    valor = dados.get(coluna)
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        return 3
    return valor if 1 <= valor <= 5 else 3

def data_campo(dados, coluna):
    """Converte a data do DataFrame em date (ou None)."""
    valor = dados.get(coluna)
    if valor is None or pd.isna(valor):
        return None
    return valor.date() if hasattr(valor, 'date') else valor

def gravou_com_sucesso(mensagem):
    """Após gravar: descarta o cache, guarda a mensagem e recarrega a tela."""
    db_client.limpar_cache_backlog()
    ui_components.definir_aviso(mensagem)
    st.session_state['tabela_versao'] = st.session_state.get('tabela_versao', 0) + 1
    st.session_state['_ultima_selecao'] = None
    st.session_state.pop('tarefa_em_edicao', None)
    st.rerun()

def fechar_edicao():
    """Chamado quando o usuário fecha a janela de edição pelo X (ou Esc)."""
    st.session_state.pop('tarefa_em_edicao', None)

@st.dialog("✏️ Editar tarefa", width="large", on_dismiss=fechar_edicao)
def dialog_editar_tarefa(conn, df, id_selecionado):
    """Janela de edição (e exclusão) de uma tarefa, aberta a partir da tabela."""
    dados_atuais = df[df['id_registro'] == id_selecionado].iloc[0]
    data_previsao = data_campo(dados_atuais, 'data_previsao_conclusao')
    data_conclusao = data_campo(dados_atuais, 'data_conclusao')
    tarefa_ja_concluida = data_conclusao is not None
    status_atual = dados_atuais.get('status', 'Em Andamento')
    if status_atual == "Finalizada":
        status_atual = "Concluida"
    st.markdown(f"#### #{id_selecionado} — {dados_atuais.get('tarefa_product_backlog', '')}")
    if 'criado_por' in dados_atuais:
        st.caption(f"📝 Criado por: {dados_atuais['criado_por']}")

    # Chaves com o ID garantem que os campos recarreguem ao trocar de tarefa
    k = f"_{id_selecionado}"
    with st.form(f"form_edicao{k}"):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            novo_titulo = st.text_input("Tarefa", value=texto_campo(dados_atuais, 'tarefa_product_backlog'), key=f"edit_titulo{k}")
            novo_setor = st.text_input("Setor (Grooming Detalhamento)", value=texto_campo(dados_atuais, 'setor_grooming_detalhamento'), key=f"edit_setor{k}")
            novo_resp = st.text_input("Responsável", value=texto_campo(dados_atuais, 'pessoa_responsavel'), key=f"edit_resp{k}")
            idx_status = STATUS_LISTA.index(status_atual) if status_atual in STATUS_LISTA else 0
            novo_status = st.selectbox("Status", STATUS_LISTA, index=idx_status, key=f"edit_status{k}",
                                       help="Para reabrir uma tarefa concluída, mude o status para 'Em Andamento'")
        with col_e2:
            nova_origem = st.text_input("Origem (Não Conformidade)", value=texto_campo(dados_atuais, 'origem_nao_conformidade'), key=f"edit_origem{k}")
            novas_acoes = st.text_area("Ações", value=texto_campo(dados_atuais, 'detalhamento_acoes'), key=f"edit_acoes{k}")
        st.divider()
        st.write("### 🧮 Prioridade (Editar REI e GUT)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**REI**")
            novo_r = st.slider("Resultado", 1, 5, nota_campo(dados_atuais, 'resultado_rei'), key=f"edit_r{k}")
            novo_e = st.slider("Execução", 1, 5, nota_campo(dados_atuais, 'execucao_rei'), key=f"edit_e{k}")
            novo_i = st.slider("Investimento", 1, 5, nota_campo(dados_atuais, 'investimento_rei'), key=f"edit_i{k}")
        with c2:
            st.markdown("**GUT**")
            novo_g = st.slider("Gravidade", 1, 5, nota_campo(dados_atuais, 'gravidade_gut'), key=f"edit_g{k}")
            novo_u = st.slider("Urgência", 1, 5, nota_campo(dados_atuais, 'urgencia_gut'), key=f"edit_u{k}")
            novo_t = st.slider("Tendência", 1, 5, nota_campo(dados_atuais, 'tendencia_gut'), key=f"edit_t{k}")
        st.divider()
        st.write("### 📅 Datas")
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            nova_data_previsao = st.date_input("Data Previsão de Conclusão", value=data_previsao, format="DD/MM/YYYY", key=f"edit_prev{k}")
        with col_data2:
            if tarefa_ja_concluida:
                st.info(f"📅 Tarefa concluída em: {data_conclusao.strftime('%d/%m/%Y')}\n\nPara reabrir, mude o status para 'Em Andamento' ou 'Atrasada'.")
                nova_data_conclusao = data_conclusao
            else:
                nova_data_conclusao = st.date_input("Data de Conclusão", value=None, format="DD/MM/YYYY", key=f"edit_conc{k}",
                                                    help="Selecione uma data para concluir a tarefa ou deixe em branco")
        if st.form_submit_button("💾 Atualizar Dados"):
            m_rei, m_gut, soma = calcular_metricas(novo_r, novo_e, novo_i, novo_g, novo_u, novo_t)
            reaberta = False
            if tarefa_ja_concluida and novo_status != "Concluida":
                # Reabertura: remove a data de conclusão
                nova_data_conclusao = None
                reaberta = True
            elif not tarefa_ja_concluida:
                if nova_data_conclusao:
                    novo_status = "Concluida"
                elif novo_status == "Concluida" and status_atual != "Concluida":
                    nova_data_conclusao = datetime.now().date()
            update_payload = {
                "tarefa_product_backlog": novo_titulo.strip(), "setor_grooming_detalhamento": novo_setor.strip(),
                "pessoa_responsavel": novo_resp.strip(), "origem_nao_conformidade": nova_origem.strip(),
                "status": novo_status, "detalhamento_acoes": novas_acoes.strip(),
                "resultado_rei": novo_r, "execucao_rei": novo_e, "investimento_rei": novo_i,
                "gravidade_gut": novo_g, "urgencia_gut": novo_u, "tendencia_gut": novo_t,
                "matriz_rei": m_rei, "matriz_gut": m_gut, "soma_gut_rei": soma,
                "data_previsao_conclusao": nova_data_previsao.isoformat() if nova_data_previsao else None,
                "data_conclusao": nova_data_conclusao.isoformat() if nova_data_conclusao else None,
                "ultimo_usuario_edicao": st.session_state.user_nome,
                "data_ultima_edicao": db_client.agora_utc().isoformat()
            }
            if 'user_id' in dados_atuais and pd.notna(dados_atuais['user_id']):
                update_payload["user_id"] = int(dados_atuais['user_id'])
            else:
                update_payload["user_id"] = st.session_state.user_id
            if not novo_titulo.strip():
                st.error("O campo Tarefa é obrigatório")
            else:
                try:
                    conn.table("tarefasqrz").update(update_payload).eq("id_registro", id_selecionado).execute()
                    msg = f"✅ Tarefa #{id_selecionado} atualizada com sucesso!"
                    if reaberta:
                        msg += " A tarefa foi reaberta e a data de conclusão removida."
                    gravou_com_sucesso(msg)
                except Exception as err:
                    st.error(f"Erro ao atualizar: {err}")

    st.divider()
    with st.expander("🗑️ Excluir esta tarefa"):
        confirmado = st.checkbox(f"Confirmo que desejo excluir definitivamente a tarefa #{id_selecionado}", key=f"excluir_confirma_{id_selecionado}")
        if st.button("Remover Definitivamente", type="primary", key=f"excluir_btn_{id_selecionado}", disabled=not confirmado):
            try:
                conn.table("tarefasqrz").delete().eq("id_registro", int(id_selecionado)).execute()
                gravou_com_sucesso(f"🗑️ Tarefa #{id_selecionado} removida com sucesso!")
            except Exception as err:
                st.error(f"Erro ao remover: {err}")

# ==========================================
# 3. FLUXO PRINCIPAL
# ==========================================
def main():
    conn = db_client.obter_conexao()
    auth.exigir_login()

    st.title("📝 Lançamento de Tarefas")
    ui_components.exibir_aviso()
    df = db_client.carregar_dados_backlog(1)
    # Filtros globais escolhidos na barra lateral
    df = ui_components.aplicar_filtros_globais(df)
    filtros = ui_components.descrever_filtros_ativos()
    if filtros:
        st.caption(f"🔎 Filtros ativos: {filtros} — limpe-os na barra lateral para ver todas as tarefas.")

    if not df.empty:
        if 'user_id' in df.columns:
            try:
                usuarios_response = conn.table("usuarios").select("id, nome_completo, email").execute()
                usuarios_dict = {u['id']: u['nome_completo'] for u in usuarios_response.data}
                df['criado_por'] = df['user_id'].map(usuarios_dict).fillna('Sistema')
            except:
                df['criado_por'] = 'Não Atribuído'

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Tarefas", len(df))
        with col2:
            st.metric("Concluídas", len(df[df['status'] == 'Concluida']))
        with col3:
            st.metric("Em Andamento", len(df[df['status'] == 'Em Andamento']))
        with col4:
            st.metric("Atrasadas", len(df[df['status'] == 'Atrasada']))
        st.divider()

    aba1, aba2 = st.tabs(["🔍 Consulta e Edição", "➕ Novo Registro"])

    with aba1:
        if not df.empty:
            with st.expander("📊 Distribuição de Tarefas por Responsável e Status"):
                df_agrupado = df.groupby(['pessoa_responsavel', 'status']).size().reset_index(name='quantidade')
                ordem = df.groupby('pessoa_responsavel').size().sort_values(ascending=False).index
                df_agrupado['pessoa_responsavel'] = pd.Categorical(df_agrupado['pessoa_responsavel'], categories=ordem, ordered=True)
                df_agrupado = df_agrupado.sort_values('pessoa_responsavel')
                fig = px.bar(
                    df_agrupado, x='pessoa_responsavel', y='quantidade', color='status',
                    title="Tarefas por Responsável e Status",
                    labels={'pessoa_responsavel': 'Responsável', 'quantidade': 'Número de Tarefas', 'status': 'Status'},
                    color_discrete_map={'Concluida': '#00c853', 'Em Andamento': '#faca2b', 'Atrasada': '#ff4b4b'},
                    barmode='group', text='quantidade'
                )
                fig.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    legend_title="Status",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="",
                    margin=dict(t=50, b=100)
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            termo = st.text_input("🔍 Localizar tarefa (ID, Nome, Responsável, Setor ou Origem)")
            df_filtrado = df[df.apply(lambda row: termo.lower() in row.astype(str).str.lower().values, axis=1)] if termo else df
            st.subheader(f"Registros Encontrados: {len(df_filtrado)}")
            st.caption("✏️ Clique na caixa à esquerda de uma tarefa para abri-la para edição.")
            colunas_exibir = ['id_registro', 'tarefa_product_backlog', 'pessoa_responsavel', 'status', 'criado_por', 'data_previsao_conclusao']
            colunas_disponiveis = [col for col in colunas_exibir if col in df_filtrado.columns]
            df_tabela = df_filtrado[colunas_disponiveis].reset_index(drop=True)
            selecao = st.dataframe(
                df_tabela.style.map(cor_status, subset=['status']), use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
                key=f"tabela_tarefas_{st.session_state.get('tabela_versao', 0)}"
            )

            linhas = selecao.selection.rows if selecao else []
            if linhas:
                id_linha = int(df_tabela.iloc[linhas[0]]['id_registro'])
                # Abre automaticamente ao selecionar; o botão permite reabrir após fechar a janela
                if st.session_state.get('_ultima_selecao') != id_linha:
                    st.session_state['_ultima_selecao'] = id_linha
                    st.session_state['tarefa_em_edicao'] = id_linha
                if st.button(f"✏️ Abrir tarefa #{id_linha} para edição", type="primary"):
                    st.session_state['tarefa_em_edicao'] = id_linha
            else:
                st.session_state['_ultima_selecao'] = None

            if df_filtrado.empty:
                st.info("Nenhum registro encontrado. Ajuste a busca acima.")

            id_edicao = st.session_state.get('tarefa_em_edicao')
            if id_edicao is not None and id_edicao in set(df['id_registro']):
                dialog_editar_tarefa(conn, df, id_edicao)
        else:
            st.info("Nenhuma tarefa encontrada no banco de dados.")

    with aba2:
        st.subheader("➕ Cadastrar Nova Tarefa")
        with st.form("form_novo", clear_on_submit=True):
            col_inf1, col_inf2 = st.columns(2)
            with col_inf1:
                t_backlog = st.text_input("Tarefa Product Backlog")
                setor = st.text_input("Setor (Grooming Detalhamento)")
                resp = st.text_input("Pessoa Responsável")
            with col_inf2:
                origem = st.text_input("Origem (Não Conformidade)")
                status_cad = st.selectbox("Status Inicial", STATUS_LISTA)
                acoes_init = st.text_area("Detalhamento de Ações")
            st.divider()
            st.write("### 📅 Datas")
            col_data_n1, col_data_n2 = st.columns(2)
            with col_data_n1:
                data_previsao_nova = st.date_input("Data Previsão de Conclusão", value=None, format="DD/MM/YYYY")
            with col_data_n2:
                data_conclusao_nova = st.date_input("Data de Conclusão", value=None, format="DD/MM/YYYY", help="Preencha apenas se a tarefa já estiver concluída")
            st.divider()
            st.write("### 🧮 Definição de Prioridade (1 a 5)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**REI**")
                r = st.slider("Resultado", 1, 5, 3, key="r_new")
                e = st.slider("Execução", 1, 5, 3, key="e_new")
                i = st.slider("Investimento", 1, 5, 3, key="i_new")
            with c2:
                st.markdown("**GUT**")
                g = st.slider("Gravidade", 1, 5, 3, key="g_new")
                u = st.slider("Urgência", 1, 5, 3, key="u_new")
                t = st.slider("Tendência", 1, 5, 3, key="t_new")
            if st.form_submit_button("🚀 Salvar no Supabase"):
                if not t_backlog.strip():
                    st.error("O campo Tarefa é obrigatório")
                else:
                    m_rei, m_gut, soma = calcular_metricas(r, e, i, g, u, t)
                    if status_cad == "Concluida" and not data_conclusao_nova:
                        data_conclusao_nova = datetime.now().date()
                    if data_conclusao_nova:
                        status_cad = "Concluida"
                    payload = {
                        "tarefa_product_backlog": t_backlog.strip(), "setor_grooming_detalhamento": setor.strip() if setor else '',
                        "pessoa_responsavel": resp.strip() if resp else '', "origem_nao_conformidade": origem.strip() if origem else '',
                        "status": status_cad, "detalhamento_acoes": acoes_init.strip() if acoes_init else '',
                        "resultado_rei": r, "execucao_rei": e, "investimento_rei": i,
                        "gravidade_gut": g, "urgencia_gut": u, "tendencia_gut": t,
                        "matriz_rei": m_rei, "matriz_gut": m_gut, "soma_gut_rei": soma,
                        "data_previsao_conclusao": data_previsao_nova.isoformat() if data_previsao_nova else None,
                        "data_conclusao": data_conclusao_nova.isoformat() if data_conclusao_nova else None,
                        "user_id": st.session_state.user_id,
                        "ultimo_usuario_edicao": st.session_state.user_nome,
                        "data_ultima_edicao": db_client.agora_utc().isoformat()
                    }
                    try:
                        conn.table("tarefasqrz").insert(payload).execute()
                        gravou_com_sucesso(f"✅ Tarefa cadastrada com sucesso! Prioridade Total: {soma}")
                    except Exception as err:
                        st.error(f"Erro ao salvar: {err}")

main()
