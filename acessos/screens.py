"""Telas e níveis de acesso: a camada amigável sobre o catálogo de ações.

O motor de autorização trabalha com ~70 ações técnicas (`tarefa.alterar_responsavel`).
Quem administra pessoas pensa em **telas** ("Tarefas") e em um **nível**:

- ``none``   — Sem acesso: a tela some do menu e as ações dela não são concedidas;
- ``ver``    — Ver: abre a tela e consulta;
- ``editar`` — Editar: ver + trabalhar nela (criar, alterar, concluir…).

Este módulo é a tabela que liga cada tela e nível às ações. A tela de grupos grava
apenas as ações certas, e o menu lê o resultado. Nada aqui toca o banco: são
funções puras, fáceis de testar.

Regras de leitura (como descobrir o nível a partir das ações que existem):

- ``editar`` quando a ação-marca da tela (a primeira de ``edit``) está presente;
- ``ver`` quando existe qualquer ação de ``view`` ou de ``edit``;
- ``none`` caso contrário. ``extra`` (ações avançadas e sensíveis) nunca muda o nível:
  só é removida quando a tela vai para "Sem acesso".

Por isso um perfil antigo, montado ação a ação na matriz, continua sendo lido de forma
sensata — e só as telas que a pessoa realmente alterar na interface são reescritas.
"""

from dataclasses import dataclass

from . import catalog

NONE = "none"
VIEW = "ver"
EDIT = "editar"
LEVELS = (NONE, VIEW, EDIT)
LEVEL_LABELS = {NONE: "Sem acesso", VIEW: "Ver", EDIT: "Editar"}
_RANK = {NONE: 0, VIEW: 1, EDIT: 2}


def rank(level):
    return _RANK.get(level, 0)


@dataclass(frozen=True)
class Screen:
    key: str
    name: str
    description: str
    section: str
    view: tuple = ()
    edit: tuple = ()
    extra: tuple = ()

    @property
    def can_edit(self):
        return bool(self.edit)

    @property
    def levels(self):
        """Níveis que existem para esta tela (nem toda tela tem "Editar")."""
        return LEVELS if self.edit else (NONE, VIEW)

    @property
    def marker(self):
        return self.edit[0] if self.edit else None

    @property
    def all_actions(self):
        return frozenset(self.view) | frozenset(self.edit) | frozenset(self.extra)


# Seções do menu, na ordem em que aparecem nas telas de acesso.
SECTIONS = [
    ("dia_a_dia", "Dia a dia"),
    ("gestao", "Gestão"),
    ("processos_cadastros", "Processos e cadastros"),
    ("administracao", "Administração"),
]

C = catalog

SCREENS = [
    # --- Dia a dia -------------------------------------------------------
    Screen("inicio", "Início", "Painel pessoal com o resumo do dia", "dia_a_dia",
           view=(C.TELA_INICIO,)),
    Screen("entrada", "Entrada", "Solicitações recebidas para triar", "dia_a_dia",
           view=(C.ENTRADA_VISUALIZAR,),
           edit=(C.ENTRADA_REGISTRAR, C.ENTRADA_TRIAR)),
    Screen("demandas", "Demandas", "Minhas, do setor e concluídas", "dia_a_dia",
           view=(C.ATIVIDADE_VISUALIZAR,),
           edit=(C.ATIVIDADE_CRIAR, C.ATIVIDADE_EDITAR, C.ATIVIDADE_ASSUMIR, C.ATIVIDADE_CONCLUIR,
                 C.ATIVIDADE_MARCAR_PENDENTE, C.ATIVIDADE_MOVER_ESTAGIO, C.ATIVIDADE_DEFINIR_ETAPA,
                 C.ATIVIDADE_DEFINIR_CONDICAO),
           extra=(C.ATIVIDADE_VISUALIZAR_TODAS, C.ATIVIDADE_ALTERAR_DONO, C.ATIVIDADE_CANCELAR,
                  C.ATIVIDADE_REABRIR, C.ATIVIDADE_APROVAR_PENDENCIA)),
    Screen("tarefas", "Tarefas", "Lista, kanban e calendário", "dia_a_dia",
           view=(C.TAREFA_VISUALIZAR,),
           edit=(C.TAREFA_INICIAR, C.TAREFA_CRIAR, C.TAREFA_EDITAR, C.TAREFA_ATRIBUIR, C.TAREFA_ASSUMIR,
                 C.TAREFA_ACEITAR, C.TAREFA_RECUSAR, C.TAREFA_PAUSAR, C.TAREFA_RETOMAR, C.TAREFA_CONCLUIR,
                 C.TAREFA_DEVOLVER, C.TAREFA_BLOQUEAR, C.TAREFA_MOVER_ESTAGIO, C.TAREFA_DEFINIR_ETAPA,
                 C.TAREFA_DEFINIR_CONDICAO, C.PRAZO_PROPOR, C.PRAZO_ACEITAR, C.PRAZO_RECUSAR,
                 C.COMUNICACAO_PARTICIPAR),
           extra=(C.TAREFA_ALTERAR_RESPONSAVEL, C.TAREFA_CANCELAR, C.TAREFA_REABRIR, C.TAREFA_MOVER_SETOR,
                  C.TEMPO_LANCAR_MANUAL, C.PRAZO_ALTERAR_SOLICITADO, C.ESCALONAMENTO_RESOLVER)),
    Screen("quadros", "Quadros", "Quadros dinâmicos da organização", "dia_a_dia",
           view=(C.QUADRO_VISUALIZAR,),
           edit=(C.QUADRO_CRIAR_ITEM, C.QUADRO_EDITAR_ITEM, C.QUADRO_CRIAR, C.QUADRO_EDITAR,
                 C.QUADRO_GERIR_COLUNAS),
           extra=(C.QUADRO_EXCLUIR, C.QUADRO_EXCLUIR_ITEM)),
    Screen("fila", "Fila", "Fila de trabalho do setor", "dia_a_dia",
           view=(C.FILA_VISUALIZAR_POSICAO_PROPRIA,),
           edit=(C.FILA_REORDENAR, C.FILA_VISUALIZAR_COMPLETA)),
    Screen("notificacoes", "Notificações", "Caixa de avisos da pessoa", "dia_a_dia",
           view=(C.TELA_NOTIFICACOES,)),
    # --- Gestão ----------------------------------------------------------
    Screen("visao_gestor", "Visão do gestor", "Indicadores e histórico", "gestao",
           view=(C.METRICAS_VISUALIZAR,),
           extra=(C.AUDITORIA_VISUALIZAR,)),
    Screen("equipe", "Equipe", "Pessoas, capacidade e carga de trabalho", "gestao",
           view=(C.TELA_EQUIPE,)),
    Screen("gargalos", "Gargalos", "Filas, bloqueios e devoluções", "gestao",
           view=(C.TELA_GARGALOS,)),
    Screen("insights", "Insights e resultados", "Análises, desenvolvimento e resultados", "gestao",
           view=(C.TELA_INSIGHTS,)),
    # --- Processos e cadastros ------------------------------------------
    Screen("processos", "Processos", "Modelos e processos da organização", "processos_cadastros",
           view=(C.PROCESSO_VISUALIZAR,),
           edit=(C.PROCESSO_CRIAR, C.PROCESSO_EDITAR_RASCUNHO, C.PROCESSO_CRIAR_VERSAO, C.PROCESSO_APLICAR),
           extra=(C.PROCESSO_PUBLICAR, C.PROCESSO_INATIVAR)),
    Screen("empresas", "Empresas", "Cadastro de empresas", "processos_cadastros",
           view=(C.TELA_EMPRESAS,),
           edit=(C.EMPRESA_GERIR,)),
    Screen("setores", "Setores", "Cadastro de setores (equipes)", "processos_cadastros",
           view=(C.TELA_SETORES,),
           edit=(C.SETOR_EDITAR, C.SETOR_CRIAR),
           extra=(C.SETOR_INATIVAR,)),
    Screen("clientes", "Clientes", "Cadastro de clientes", "processos_cadastros",
           view=(C.TELA_CLIENTES,),
           edit=(C.CLIENTE_GERIR,)),
    Screen("obras", "Obras", "Cadastro de obras", "processos_cadastros",
           view=(C.TELA_OBRAS,),
           edit=(C.OBRA_GERIR,)),
    Screen("centros_custo", "Centros de custo", "Cadastro de centros de custo", "processos_cadastros",
           view=(C.TELA_CENTROS_CUSTO,),
           edit=(C.CENTRO_CUSTO_GERIR,)),
    # --- Administração ---------------------------------------------------
    Screen("usuarios", "Usuários", "Cadastrar e editar pessoas", "administracao",
           view=(C.USUARIO_VISUALIZAR,),
           edit=(C.USUARIO_EDITAR, C.USUARIO_CRIAR),
           extra=(C.USUARIO_INATIVAR,)),
    Screen("grupos", "Grupos de acesso", "Definir as telas de cada grupo", "administracao",
           view=(C.SEGURANCA_GERIR_PERFIS,),
           edit=(C.SEGURANCA_GERIR_AUTORIZACOES,)),
    Screen("configuracoes", "Configurações", "Etapas, prioridades e motivos", "administracao",
           view=(C.TELA_CONFIGURACOES,),
           edit=(C.ETAPA_GERIR, C.CONDICAO_GERIR, C.ESTAGIO_TAREFA_GERIR, C.TAG_GERIR, C.COR_STATUS_GERIR,
                 C.COR_PRIORIDADE_GERIR, C.MOTIVO_DEVOLUCAO_GERIR)),
    Screen("integracoes", "Integrações", "Conexões com outros sistemas", "administracao",
           view=(C.TELA_INTEGRACOES,)),
]

SCREEN_BY_KEY = {screen.key: screen for screen in SCREENS}

# Ações cuja verificação real acontece sobre a organização inteira (a view não passa um recurso
# de setor). Concedidas só em "as equipes da pessoa", elas não funcionam — a interface avisa.
ORG_ONLY_ACTIONS = frozenset(
    {
        C.QUADRO_VISUALIZAR, C.QUADRO_CRIAR, C.QUADRO_EDITAR, C.QUADRO_EXCLUIR, C.QUADRO_GERIR_COLUNAS,
        C.QUADRO_CRIAR_ITEM, C.QUADRO_EDITAR_ITEM, C.QUADRO_EXCLUIR_ITEM,
        C.USUARIO_VISUALIZAR, C.USUARIO_CRIAR, C.USUARIO_EDITAR, C.USUARIO_INATIVAR,
        C.SEGURANCA_GERIR_PERFIS, C.SEGURANCA_GERIR_AUTORIZACOES,
        C.EMPRESA_GERIR, C.OBRA_GERIR, C.CENTRO_CUSTO_GERIR, C.CLIENTE_GERIR, C.MOTIVO_DEVOLUCAO_GERIR,
        C.TAG_GERIR, C.COR_STATUS_GERIR, C.COR_PRIORIDADE_GERIR, C.SETOR_CRIAR, C.SETOR_INATIVAR,
    }
)


def sections():
    """[(chave, nome, [telas])] na ordem das seções, para telas e menu."""
    return [(key, name, [s for s in SCREENS if s.section == key]) for key, name in SECTIONS]


def actions_for_level(screen, level):
    """Ações que um nível concede (``extra`` nunca entra: é avançado)."""
    if level == EDIT and screen.can_edit:
        return frozenset(screen.view) | frozenset(screen.edit)
    if level in (VIEW, EDIT):
        return frozenset(screen.view)
    return frozenset()


def level_from_actions(screen, keys):
    """Nível que um conjunto de ações representa nesta tela."""
    if screen.marker and screen.marker in keys:
        return EDIT
    if keys & (frozenset(screen.view) | frozenset(screen.edit)):
        return VIEW
    return NONE


def levels_from_actions(keys):
    keys = frozenset(keys)
    return {screen.key: level_from_actions(screen, keys) for screen in SCREENS}


def full_levels():
    """Tudo no máximo — o que o super usuário e o Administrador enxergam."""
    return {screen.key: (EDIT if screen.can_edit else VIEW) for screen in SCREENS}


def screens_count(levels):
    """Quantas telas ficam liberadas (qualquer nível acima de "Sem acesso")."""
    return sum(1 for level in levels.values() if level != NONE)


def normalize_level(screen, level):
    """Nível válido para a tela: "Editar" numa tela sem edição vira "Ver"."""
    if level not in LEVELS:
        return NONE
    if level == EDIT and not screen.can_edit:
        return VIEW
    return level


def needs_organization(screen, level):
    """O nível só funciona com o acesso valendo para a organização inteira?"""
    return bool(actions_for_level(screen, level) & ORG_ONLY_ACTIONS)


def screens_payload():
    """Estrutura serializável para os scripts das telas de acesso."""
    return [
        {
            "key": screen.key,
            "name": screen.name,
            "section": screen.section,
            "canEdit": screen.can_edit,
            "needsOrg": {
                VIEW: needs_organization(screen, VIEW),
                EDIT: needs_organization(screen, EDIT),
            },
        }
        for screen in SCREENS
    ]
