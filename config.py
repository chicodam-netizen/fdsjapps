# Configurações Globais do Sistema QRZ

# Nomes de Tabelas no Supabase
TABELA_TAREFAS = "tarefasqrz"
TABELA_USUARIOS = "usuarios"

# Texto exibido para campos vazios (apenas visualização; nunca deve ser gravado no banco)
TEXTO_NAO_ATRIBUIDO = "Não Atribuído"

# Estilos CSS Customizados
STYLE_HIDE_SIDEBAR = """
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
</style>
"""

STYLE_HIDE_NAV_ONLY = """
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
"""
