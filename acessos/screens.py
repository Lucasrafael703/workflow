"""Telas do sistema e o que cada nível de acesso libera.

A LPS autoriza por **ações** (catalog.py) — é o que protege de verdade cada
operação. Só que ninguém pensa em "tarefa.alterar_responsavel" quando vai dar
acesso a alguém da equipe: pensa em "esta pessoa pode abrir a tela de Tarefas
e trabalhar nela". Este módulo é a tradução entre as duas coisas.

Cada tela tem três níveis:

    SEM ACESSO  -> a tela some do menu
    VER         -> abre a tela e acompanha, sem alterar nada
    EDITAR      -> usa a tela por completo (inclui tudo do VER)

Um grupo (Perfil de acesso) guarda ações; o nível de cada tela é **derivado**
dessas ações. Salvar níveis numa tela nunca apaga ações de outra, e uma tela
cujo nível não mudou fica exatamente como estava — por isso ajustes finos
feitos na matriz detalhada de ações continuam valendo.
"""

from dataclasses import dataclass, field

from . import catalog as c

SEM_ACESSO = 0
VER = 1
EDITAR = 2

LEVEL_LABELS = {SEM_ACESSO: "Sem acesso", VER: "Ver", EDITAR: "Editar"}


@dataclass(frozen=True)
class Screen:
    key: str
    name: str
    description: str
    view_actions: tuple = ()
    edit_actions: tuple = ()
    # Rótulo do nível mais alto quando a tela não tem "só ver" (cadastros).
    edit_label: str = "Editar"
    # Explica, no formulário, o que o "Editar" libera a mais.
    edit_hint: str = ""

    @property
    def has_view_level(self):
        return bool(self.view_actions)

    @property
    def all_actions(self):
        return tuple(self.view_actions) + tuple(self.edit_actions)

    def actions_for(self, level):
        if level >= EDITAR:
            return set(self.all_actions)
        if level >= VER:
            return set(self.view_actions)
        return set()

    def level_from(self, keys):
        """Nível que um conjunto de ações concede nesta tela."""
        keys = set(keys)
        if self.all_actions and set(self.all_actions) <= keys:
            return EDITAR
        if self.view_actions and set(self.view_actions) <= keys:
            return VER
        return SEM_ACESSO

    def is_partial(self, keys):
        """Tem parte das ações, mas não o suficiente para o próximo nível.

        Acontece com grupos ajustados na matriz detalhada. A tela avisa
        ("personalizado") em vez de fingir que não há nada ali.
        """
        mine = set(self.all_actions) & set(keys)
        return bool(mine) and mine != self.actions_for(self.level_from(keys))

    def visible_with(self, keys):
        """Aparece no menu? Basta qualquer ação da tela."""
        return bool(set(self.all_actions) & set(keys))


@dataclass(frozen=True)
class Section:
    name: str
    screens: tuple = field(default_factory=tuple)


SECTIONS = (
    Section(
        "Dia a dia",
        (
            Screen(
                "atividades",
                "Atividades",
                "Listas de atividades, detalhes e conversas.",
                view_actions=(c.ATIVIDADE_VISUALIZAR, c.COMUNICACAO_PARTICIPAR),
                edit_actions=(
                    c.ATIVIDADE_CRIAR,
                    c.ATIVIDADE_EDITAR,
                    c.ATIVIDADE_ASSUMIR,
                    c.ATIVIDADE_CONCLUIR,
                    c.ATIVIDADE_MARCAR_PENDENTE,
                ),
                edit_hint="Criar, editar, assumir, concluir e marcar pendência.",
            ),
            Screen(
                "tarefas",
                "Tarefas",
                "Lista, kanban e calendário de tarefas.",
                view_actions=(c.TAREFA_VISUALIZAR,),
                edit_actions=(
                    c.TAREFA_CRIAR,
                    c.TAREFA_EDITAR,
                    c.TAREFA_ATRIBUIR,
                    c.TAREFA_ASSUMIR,
                    c.TAREFA_ACEITAR,
                    c.TAREFA_RECUSAR,
                    c.TAREFA_INICIAR,
                    c.TAREFA_PAUSAR,
                    c.TAREFA_RETOMAR,
                    c.TAREFA_DEVOLVER,
                    c.TAREFA_CONCLUIR,
                    c.TAREFA_BLOQUEAR,
                    c.PRAZO_PROPOR,
                    c.PRAZO_ACEITAR,
                    c.PRAZO_RECUSAR,
                ),
                edit_hint="Criar, executar, devolver, concluir e negociar prazos.",
            ),
            Screen(
                "fila",
                "Fila",
                "Fila de trabalho do setor.",
                view_actions=(c.FILA_VISUALIZAR_POSICAO_PROPRIA, c.FILA_VISUALIZAR_COMPLETA),
                edit_actions=(c.FILA_REORDENAR,),
                edit_hint="Reordenar a fila.",
            ),
        ),
    ),
    Section(
        "Gestão",
        (
            Screen(
                "gestao",
                "Visão do gestor",
                "Indicadores, equipe, gargalos e histórico.",
                view_actions=(c.METRICAS_VISUALIZAR, c.ATIVIDADE_VISUALIZAR_TODAS, c.AUDITORIA_VISUALIZAR),
                edit_actions=(
                    c.ATIVIDADE_APROVAR_PENDENCIA,
                    c.ATIVIDADE_ALTERAR_DONO,
                    c.ATIVIDADE_CANCELAR,
                    c.ATIVIDADE_REABRIR,
                    c.TAREFA_ALTERAR_RESPONSAVEL,
                    c.TAREFA_MOVER_SETOR,
                    c.TAREFA_CANCELAR,
                    c.TEMPO_LANCAR_MANUAL,
                    c.ESCALONAMENTO_RESOLVER,
                ),
                edit_hint="Aprovar pendências, trocar dono/responsável, cancelar, reabrir e lançar tempo.",
            ),
            Screen(
                "processos",
                "Processos",
                "Modelos de processo da organização.",
                view_actions=(c.PROCESSO_VISUALIZAR, c.PROCESSO_APLICAR),
                edit_actions=(
                    c.PROCESSO_CRIAR,
                    c.PROCESSO_EDITAR_RASCUNHO,
                    c.PROCESSO_PUBLICAR,
                    c.PROCESSO_CRIAR_VERSAO,
                    c.PROCESSO_INATIVAR,
                ),
                edit_hint="Criar, editar, publicar e inativar processos.",
            ),
        ),
    ),
    Section(
        "Cadastros",
        (
            Screen("empresas", "Empresas", "Cadastro de empresas.", edit_actions=(c.EMPRESA_GERIR,), edit_label="Gerenciar"),
            Screen(
                "setores",
                "Setores (equipes)",
                "Cadastro de setores.",
                edit_actions=(c.SETOR_CRIAR, c.SETOR_EDITAR, c.SETOR_INATIVAR),
                edit_label="Gerenciar",
            ),
            Screen("clientes", "Clientes", "Cadastro de clientes.", edit_actions=(c.CLIENTE_GERIR,), edit_label="Gerenciar"),
            Screen("obras", "Obras", "Cadastro de obras.", edit_actions=(c.OBRA_GERIR,), edit_label="Gerenciar"),
            Screen(
                "centros_custo",
                "Centros de custo",
                "Cadastro de centros de custo.",
                edit_actions=(c.CENTRO_CUSTO_GERIR,),
                edit_label="Gerenciar",
            ),
        ),
    ),
    Section(
        "Administração",
        (
            Screen(
                "usuarios",
                "Usuários",
                "Pessoas que acessam o sistema.",
                view_actions=(c.USUARIO_VISUALIZAR,),
                edit_actions=(c.USUARIO_CRIAR, c.USUARIO_EDITAR, c.USUARIO_INATIVAR),
                edit_hint="Cadastrar, editar e inativar pessoas.",
            ),
            Screen(
                "grupos",
                "Grupos de acesso",
                "Definir as telas de cada grupo e de cada pessoa.",
                edit_actions=(c.SEGURANCA_GERIR_PERFIS, c.SEGURANCA_GERIR_AUTORIZACOES),
                edit_label="Gerenciar",
            ),
            Screen(
                "configuracoes",
                "Configurações",
                "Etapas, status, prioridades, motivos e marcadores.",
                edit_actions=(
                    c.MOTIVO_DEVOLUCAO_GERIR,
                    c.ESTAGIO_TAREFA_GERIR,
                    c.TAG_GERIR,
                    c.COR_STATUS_GERIR,
                    c.COR_PRIORIDADE_GERIR,
                ),
                edit_label="Gerenciar",
            ),
        ),
    ),
)

SCREENS = tuple(screen for section in SECTIONS for screen in section.screens)
SCREENS_BY_KEY = {screen.key: screen for screen in SCREENS}


def levels_from_actions(keys):
    """{tela: nível} para um conjunto de chaves de ação."""
    keys = set(keys)
    return {screen.key: screen.level_from(keys) for screen in SCREENS}


def actions_for_levels(levels):
    """Chaves de ação que um dicionário {tela: nível} libera."""
    keys = set()
    for screen in SCREENS:
        keys |= screen.actions_for(int(levels.get(screen.key, SEM_ACESSO) or 0))
    return keys


def merge_levels(current_keys, new_levels):
    """Aplica níveis novos sem estragar o que não mudou.

    Para cada tela: se o nível pedido é o mesmo que as ações atuais já dão,
    as ações da tela ficam como estão (inclusive ajustes finos). Se mudou, as
    ações da tela passam a ser exatamente as do novo nível.
    """
    current_keys = set(current_keys)
    result = set(current_keys)
    for screen in SCREENS:
        if screen.key not in new_levels:
            continue
        wanted = int(new_levels[screen.key] or 0)
        if wanted == screen.level_from(current_keys):
            continue
        result -= set(screen.all_actions)
        result |= screen.actions_for(wanted)
    return result


def visible_screens(keys):
    """Telas que aparecem no menu para quem tem estas ações."""
    keys = set(keys)
    return {screen.key: screen.visible_with(keys) for screen in SCREENS}


def count_screens(levels):
    return sum(1 for value in levels.values() if value > SEM_ACESSO)


def all_screen_actions():
    return {key for screen in SCREENS for key in screen.all_actions}


# Modelos para começar um grupo novo. Só um ponto de partida: depois de criado,
# o grupo é da organização e pode ser mudado à vontade.
TEMPLATES = {
    "colaborador": {
        "name": "Colaborador",
        "description": "Executa atividades e tarefas da própria equipe.",
        "levels": {"atividades": EDITAR, "tarefas": EDITAR, "fila": VER, "processos": VER},
    },
    "gestor": {
        "name": "Gestor de setor",
        "description": "Organiza a fila, acompanha a equipe e os indicadores.",
        "levels": {
            "atividades": EDITAR,
            "tarefas": EDITAR,
            "fila": EDITAR,
            "gestao": EDITAR,
            "processos": EDITAR,
            "clientes": EDITAR,
            "obras": EDITAR,
            "usuarios": VER,
        },
    },
    "consulta": {
        "name": "Somente consulta",
        "description": "Acompanha o andamento sem alterar nada.",
        "levels": {"atividades": VER, "tarefas": VER, "fila": VER, "gestao": VER, "processos": VER},
    },
    "administrador": {
        "name": "Administrador",
        "description": "Acesso total. Use só para quem administra o sistema.",
        "levels": {screen.key: EDITAR for screen in SCREENS},
    },
}
