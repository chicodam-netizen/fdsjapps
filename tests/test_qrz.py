# Testes automatizados do Sistema QRZ (banco falso em memória; não acessa o Supabase)
# Executar na pasta QRZ:  python -m pytest -q tests

import copy
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import db_client  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402


# ------------------------------------------------------------------
# Banco falso compatível com a API usada (table/select/eq/insert/update/delete/execute)
# ------------------------------------------------------------------
class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, tabela):
        self.db, self.tabela = db, tabela
        self.filtros, self.op, self.payload = [], "select", None

    def select(self, *_):
        self.op = "select"
        return self

    def eq(self, col, val):
        self.filtros.append((col, val))
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _casa(self, row):
        return all(row.get(c) == v for c, v in self.filtros)

    def execute(self):
        linhas = self.db.tabelas.setdefault(self.tabela, [])
        self.db.log.append((self.tabela, self.op, copy.deepcopy(self.payload), list(self.filtros)))
        if self.op == "select":
            return _Resp([copy.deepcopy(r) for r in linhas if self._casa(r)])
        if self.op == "insert":
            chave = "id_registro" if self.tabela == "tarefasqrz" else "id"
            novo = dict(self.payload)
            novo[chave] = max([r[chave] for r in linhas] or [0]) + 1
            linhas.append(novo)
            return _Resp([novo])
        if self.op == "update":
            for r in linhas:
                if self._casa(r):
                    r.update(self.payload)
            return _Resp([])
        if self.op == "delete":
            self.db.tabelas[self.tabela] = [r for r in linhas if not self._casa(r)]
            return _Resp([])


class FakeConn:
    def __init__(self):
        self.tabelas, self.log = {}, []

    def table(self, nome):
        return _Query(self, nome)


def _usuario(id_, email, senha, admin=False):
    h, s = db_client.hash_senha(senha)
    return {"id": id_, "email": email, "senha_hash": h, "salt": s, "nome_completo": f"Usuário {id_}",
            "is_admin": admin, "reset_code": None, "reset_expires": None}


def _tarefa(id_, titulo, **extra):
    base = {"id_registro": id_, "tarefa_product_backlog": titulo, "setor_grooming_detalhamento": "Qualidade",
            "pessoa_responsavel": "Ana", "origem_nao_conformidade": "Auditoria", "status": "Em Andamento",
            "detalhamento_acoes": "Ações", "resultado_rei": 3, "execucao_rei": 3, "investimento_rei": 3,
            "matriz_rei": 27, "gravidade_gut": 3, "urgencia_gut": 3, "tendencia_gut": 3, "matriz_gut": 27,
            "soma_gut_rei": 54, "data_previsao_conclusao": "2099-12-31", "data_conclusao": None, "user_id": 1}
    base.update(extra)
    return base


@pytest.fixture
def banco(monkeypatch):
    conn = FakeConn()
    conn.tabelas["usuarios"] = [_usuario(1, "ana@qrz.com", "senha123"), _usuario(2, "admin@qrz.com", "admin123", True)]
    conn.tabelas["tarefasqrz"] = [
        _tarefa(10, "Calibrar balança"),
        _tarefa(11, "Revisar POP", status="Concluida", data_conclusao="2026-01-10"),
        _tarefa(12, "Tarefa sem notas", setor_grooming_detalhamento=None, resultado_rei=None, gravidade_gut=None),
    ]
    monkeypatch.setattr(db_client, "obter_conexao", lambda: conn)
    enviados = []
    monkeypatch.setattr(db_client, "enviar_email", lambda dest, assunto, corpo: (enviados.append((dest, corpo)) or (True, "")))
    conn.enviados = enviados
    db_client.limpar_cache_backlog()
    yield conn
    db_client.limpar_cache_backlog()


def _app_logado(pagina="pages/entrada.py"):
    at = AppTest.from_file(pagina, default_timeout=30)
    at.session_state["authenticated"] = True
    at.session_state["user_email"] = "ana@qrz.com"
    at.session_state["user_id"] = 1
    at.session_state["user_nome"] = "Ana"
    return at


def _tarefa_db(conn, id_):
    return next(r for r in conn.tabelas["tarefasqrz"] if r["id_registro"] == id_)


# ------------------------------------------------------------------
# Fase 0 — funções de segurança
# ------------------------------------------------------------------
def test_verificar_senha():
    h, s = db_client.hash_senha("abc123")
    assert db_client.verificar_senha("abc123", h, s)
    assert not db_client.verificar_senha("errada", h, s)
    assert not db_client.verificar_senha("abc123", h, "")


def test_converter_para_utc_aceita_formatos_do_banco():
    a = db_client.converter_para_utc("2026-10-14T12:00:00+00:00")
    b = db_client.converter_para_utc("2026-10-14T12:00:00Z")
    c = db_client.converter_para_utc("2026-10-14T09:00:00-03:00")
    d = db_client.converter_para_utc("2026-10-14T12:00:00")  # sem fuso => UTC
    assert a == b == c == d
    assert a.tzinfo is not None


def test_busca_email_ignora_maiusculas(banco):
    assert db_client.buscar_usuario_por_email(banco, "  ANA@QRZ.com ")["id"] == 1
    assert db_client.buscar_usuario_por_email(banco, "naoexiste@qrz.com") is None


def test_reset_envia_codigo_por_email_e_nao_o_devolve(banco):
    ok, msg = db_client.solicitar_reset_senha_generico(banco, "Ana@qrz.com")
    codigo = next(u for u in banco.tabelas["usuarios"] if u["id"] == 1)["reset_code"]
    assert ok and msg == db_client.MSG_RESET_GENERICA
    assert codigo not in msg
    assert banco.enviados and banco.enviados[0][0] == "ana@qrz.com" and codigo in banco.enviados[0][1]


def test_reset_email_inexistente_tem_mesma_resposta(banco):
    ok, msg = db_client.solicitar_reset_senha_generico(banco, "ninguem@qrz.com")
    assert ok and msg == db_client.MSG_RESET_GENERICA
    assert banco.enviados == []


def test_reset_admin_nao_envia_para_usuario_comum(banco):
    ok, msg = db_client.solicitar_reset_senha_generico(banco, "ana@qrz.com", apenas_admin=True)
    assert ok and msg == db_client.MSG_RESET_GENERICA and banco.enviados == []


def test_reset_falha_de_smtp_informa_sem_mostrar_codigo(banco, monkeypatch):
    monkeypatch.setattr(db_client, "enviar_email", lambda *a: (False, "smtp off"))
    ok, msg = db_client.solicitar_reset_senha_generico(banco, "ana@qrz.com")
    codigo = next(u for u in banco.tabelas["usuarios"] if u["id"] == 1)["reset_code"]
    assert not ok and codigo not in msg


def test_redefinir_com_codigo_valido_timestamptz(banco):
    db_client.solicitar_reset_senha_generico(banco, "ana@qrz.com")
    u = next(u for u in banco.tabelas["usuarios"] if u["id"] == 1)
    # Simula o formato devolvido pelo Postgres (timestamptz com fuso)
    u["reset_expires"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    ok, msg = db_client.redefinir_senha_com_codigo(banco, "ANA@qrz.com", u["reset_code"], "novaSenha1")
    assert ok, msg
    assert db_client.verificar_senha("novaSenha1", u["senha_hash"], u["salt"])
    assert u["reset_code"] is None


def test_redefinir_codigo_expirado_e_invalido(banco):
    db_client.solicitar_reset_senha_generico(banco, "ana@qrz.com")
    u = next(u for u in banco.tabelas["usuarios"] if u["id"] == 1)
    ok, _ = db_client.redefinir_senha_com_codigo(banco, "ana@qrz.com", "000000" if u["reset_code"] != "000000" else "111111", "novaSenha1")
    assert not ok
    u["reset_expires"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    ok, msg = db_client.redefinir_senha_com_codigo(banco, "ana@qrz.com", u["reset_code"], "novaSenha1")
    assert not ok and "expirado" in msg


def test_admin_inicial_nao_usa_senha_fixa(banco):
    banco.tabelas["usuarios"] = [u for u in banco.tabelas["usuarios"] if not u["is_admin"]]
    db_client.criar_admin_se_nao_existir(banco)  # sem [admin_inicial] nos secrets de teste
    assert not any(u["is_admin"] for u in banco.tabelas["usuarios"])


# ------------------------------------------------------------------
# Fase 0 — tela de login
# ------------------------------------------------------------------
def _login_form(at, email, senha=""):
    at.text_input[0].input(email)
    at.text_input[1].input(senha)


def test_login_mensagem_generica(banco):
    at = AppTest.from_file("pages/entrada.py", default_timeout=30).run()
    _login_form(at, "naoexiste@qrz.com", "x")
    at.button[0].click().run()
    assert any("E-mail ou senha inválidos" in e.value for e in at.error)
    _login_form(at, "ana@qrz.com", "errada")
    at.button[0].click().run()
    assert any("E-mail ou senha inválidos" in e.value for e in at.error)


def test_login_com_maiusculas(banco):
    at = AppTest.from_file("pages/entrada.py", default_timeout=30).run()
    _login_form(at, "ANA@QRZ.COM", "senha123")
    at.button[0].click().run()
    assert at.session_state["authenticated"] is True
    assert not at.exception


def test_esqueci_senha_nao_mostra_codigo(banco):
    at = AppTest.from_file("pages/entrada.py", default_timeout=30).run()
    _login_form(at, "ana@qrz.com")
    at.button[1].click().run()
    codigo = next(u for u in banco.tabelas["usuarios"] if u["id"] == 1)["reset_code"]
    textos = " ".join(str(el.value) for el in list(at.info) + list(at.success) + list(at.markdown) + list(at.warning))
    assert codigo and codigo not in textos
    assert at.session_state["reset_step"] == "verify"
    assert any("Se o e-mail estiver cadastrado" in i.value for i in at.info)


def test_bloqueio_apos_5_codigos_errados(banco):
    at = AppTest.from_file("pages/entrada.py", default_timeout=30).run()
    _login_form(at, "ana@qrz.com")
    at.button[1].click().run()
    for _ in range(5):
        at.text_input[1].input("999999" if banco.tabelas["usuarios"][0]["reset_code"] != "999999" else "888888")
        at.text_input[2].input("novaSenha1")
        at.text_input[3].input("novaSenha1")
        at.button[0].click().run()
    assert at.session_state["reset_step"] is None
    assert banco.tabelas["usuarios"][0]["reset_code"] is None


# ------------------------------------------------------------------
# Fase 1 — atualização de tarefas
# ------------------------------------------------------------------
def _ultimo(widgets, label):
    """Último widget com o rótulo: após st.rerun() o AppTest mantém também os elementos da execução interrompida."""
    return [w for w in widgets if w.label == label][-1]


def _selecionar_tarefa(at, id_):
    sel = _ultimo(at.selectbox, "Selecione a tarefa para editar")
    sel.set_value(id_).run()
    return sel


def test_lista_de_edicao_mostra_titulo(banco):
    at = _app_logado().run()
    assert not at.exception
    sel = next(s for s in at.selectbox if s.label == "Selecione a tarefa para editar")
    assert any("#10 — Calibrar balança" in o for o in sel.options)


def test_tarefa_sem_notas_abre_sem_erro_e_nao_grava_nao_atribuido(banco):
    at = _app_logado().run()
    _selecionar_tarefa(at, 12)
    assert not at.exception
    assert at.slider(key="edit_r_12").value == 3
    assert at.text_input(key="edit_setor_12").value == ""
    next(b for b in at.button if b.label == "💾 Atualizar Dados").click().run()
    assert not at.exception
    t = _tarefa_db(banco, 12)
    assert t["setor_grooming_detalhamento"] == ""


def test_atualizacao_reflete_na_hora_e_mostra_mensagem(banco):
    at = _app_logado().run()
    _selecionar_tarefa(at, 10)
    at.text_input(key="edit_titulo_10").input("Calibrar balança v2")
    next(b for b in at.button if b.label == "💾 Atualizar Dados").click().run()
    assert _tarefa_db(banco, 10)["tarefa_product_backlog"] == "Calibrar balança v2"
    assert any("#10 atualizada" in s.value for s in at.success)
    # Sem cache velho: o cache (compartilhado entre sessões) já reflete o valor novo
    at2 = _app_logado().run()
    _selecionar_tarefa(at2, 10)
    assert at2.text_input(key="edit_titulo_10").value == "Calibrar balança v2"


def test_reabrir_tarefa_concluida_remove_data(banco):
    at = _app_logado().run()
    _selecionar_tarefa(at, 11)
    at.selectbox(key="edit_status_11").set_value("Em Andamento")
    next(b for b in at.button if b.label == "💾 Atualizar Dados").click().run()
    t = _tarefa_db(banco, 11)
    assert t["status"] == "Em Andamento" and t["data_conclusao"] is None
    assert any("reaberta" in s.value for s in at.success)


def test_concluir_pelo_status_preenche_data(banco):
    at = _app_logado().run()
    _selecionar_tarefa(at, 10)
    at.selectbox(key="edit_status_10").set_value("Concluida")
    next(b for b in at.button if b.label == "💾 Atualizar Dados").click().run()
    t = _tarefa_db(banco, 10)
    assert t["status"] == "Concluida" and t["data_conclusao"] == datetime.now().date().isoformat()


def test_trocar_de_tarefa_recarrega_sliders(banco):
    banco.tabelas["tarefasqrz"][0]["gravidade_gut"] = 5
    banco.tabelas["tarefasqrz"][1]["gravidade_gut"] = 1
    at = _app_logado().run()
    _selecionar_tarefa(at, 10)
    assert at.slider(key="edit_g_10").value == 5
    _selecionar_tarefa(at, 11)
    assert at.slider(key="edit_g_11").value == 1


def test_exclusao_exige_confirmacao(banco):
    at = _app_logado().run()
    sel = next(s for s in at.selectbox if s.key == "excluir_select")
    sel.set_value(12).run()
    btn = next(b for b in at.button if b.key == "excluir_btn")
    assert btn.disabled
    at.checkbox(key="excluir_confirma_12").check().run()
    next(b for b in at.button if b.key == "excluir_btn").click().run()
    assert all(r["id_registro"] != 12 for r in banco.tabelas["tarefasqrz"])
    assert any("#12 removida" in s.value for s in at.success)


def test_novo_registro_aparece_imediatamente(banco):
    at = _app_logado().run()
    next(t for t in at.text_input if t.label == "Tarefa Product Backlog").input("Nova tarefa teste")
    next(b for b in at.button if b.label == "🚀 Salvar no Supabase").click().run()
    assert any(r["tarefa_product_backlog"] == "Nova tarefa teste" for r in banco.tabelas["tarefasqrz"])
    sel = _ultimo(at.selectbox, "Selecione a tarefa para editar")
    assert any("Nova tarefa teste" in o for o in sel.options)
