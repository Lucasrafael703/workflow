"""Catálogo de ações da LPS (Regras 05 §13, doc 08 §19).

Uma ação existe porque a aplicação possui comportamento correspondente. A
organização combina estas ações em perfis, mas não inventa ações novas — caso
contrário a autorização existiria no banco sem proteger nada real (doc 05 §14).

Este arquivo é a única fonte da verdade do catálogo: o comando
`seed_acoes` o materializa no banco, e o código referencia as constantes.
"""

# Atividades
ATIVIDADE_VISUALIZAR = "atividade.visualizar"
ATIVIDADE_VISUALIZAR_TODAS = "atividade.visualizar_todas"
ATIVIDADE_CRIAR = "atividade.criar"
ATIVIDADE_EDITAR = "atividade.editar"
ATIVIDADE_ALTERAR_DONO = "atividade.alterar_dono"
ATIVIDADE_CONCLUIR = "atividade.concluir"
ATIVIDADE_CANCELAR = "atividade.cancelar"
ATIVIDADE_REABRIR = "atividade.reabrir"

# Tarefas
TAREFA_VISUALIZAR = "tarefa.visualizar"
TAREFA_CRIAR = "tarefa.criar"
TAREFA_EDITAR = "tarefa.editar"
TAREFA_ATRIBUIR = "tarefa.atribuir"
TAREFA_ASSUMIR = "tarefa.assumir"
TAREFA_INICIAR = "tarefa.iniciar"
TAREFA_PAUSAR = "tarefa.pausar"
TAREFA_RETOMAR = "tarefa.retomar"
TAREFA_DEVOLVER = "tarefa.devolver"
TAREFA_CONCLUIR = "tarefa.concluir"
TAREFA_CANCELAR = "tarefa.cancelar"
TAREFA_BLOQUEAR = "tarefa.bloquear"
TAREFA_MOVER_SETOR = "tarefa.mover_setor"
TEMPO_LANCAR_MANUAL = "tempo.lancar_manual"

# Filas
FILA_VISUALIZAR_POSICAO_PROPRIA = "fila.visualizar_posicao_propria"
FILA_VISUALIZAR_COMPLETA = "fila.visualizar_completa"
FILA_REORDENAR = "fila.reordenar"

# Prazos
PRAZO_PROPOR = "prazo.propor"
PRAZO_ACEITAR = "prazo.aceitar"
PRAZO_RECUSAR = "prazo.recusar"
ESCALONAMENTO_RESOLVER = "escalonamento.resolver"

# Comunicação
COMUNICACAO_PARTICIPAR = "comunicacao.participar"

# Cadastros
SETOR_CRIAR = "setor.criar"
SETOR_EDITAR = "setor.editar"
SETOR_INATIVAR = "setor.inativar"
EMPRESA_GERIR = "empresa.gerir"
OBRA_GERIR = "obra.gerir"
CENTRO_CUSTO_GERIR = "centro_custo.gerir"
MOTIVO_DEVOLUCAO_GERIR = "motivo_devolucao.gerir"

# Processos
PROCESSO_VISUALIZAR = "processo.visualizar"
PROCESSO_CRIAR = "processo.criar"
PROCESSO_EDITAR_RASCUNHO = "processo.editar_rascunho"
PROCESSO_PUBLICAR = "processo.publicar"
PROCESSO_CRIAR_VERSAO = "processo.criar_versao"
PROCESSO_INATIVAR = "processo.inativar"
PROCESSO_APLICAR = "processo.aplicar"

# Segurança
USUARIO_VISUALIZAR = "usuario.visualizar"
USUARIO_CRIAR = "usuario.criar"
USUARIO_EDITAR = "usuario.editar"
USUARIO_INATIVAR = "usuario.inativar"
SEGURANCA_GERIR_PERFIS = "seguranca.gerir_perfis"
SEGURANCA_GERIR_AUTORIZACOES = "seguranca.gerir_autorizacoes"

# Auditoria
AUDITORIA_VISUALIZAR = "auditoria.visualizar"
METRICAS_VISUALIZAR = "metricas.visualizar"


# (chave, nome, descrição, sensível)
GROUPS = [
    (
        "atividades",
        "Atividades",
        [
            (ATIVIDADE_VISUALIZAR, "Visualizar atividades", "Permite abrir atividades dentro do escopo autorizado.", False),
            (ATIVIDADE_VISUALIZAR_TODAS, "Visualizar todas as atividades", "Permite ver atividades de que a pessoa não é dona nem executora.", False),
            (ATIVIDADE_CRIAR, "Criar atividade", "Permite registrar um novo resultado a ser alcançado.", False),
            (ATIVIDADE_EDITAR, "Editar atividade", "Permite alterar título, descrição, prazo e contexto da atividade.", False),
            (ATIVIDADE_ALTERAR_DONO, "Alterar dono da atividade", "Permite transferir a responsabilidade pelo resultado para outra pessoa.", True),
            (ATIVIDADE_CONCLUIR, "Concluir atividade", "Permite encerrar a atividade quando o resultado foi alcançado.", False),
            (ATIVIDADE_CANCELAR, "Cancelar atividade", "Permite cancelar a atividade registrando o motivo.", True),
            (ATIVIDADE_REABRIR, "Reabrir atividade", "Permite reabrir uma atividade já concluída.", True),
        ],
    ),
    (
        "tarefas",
        "Tarefas",
        [
            (TAREFA_VISUALIZAR, "Visualizar tarefas", "Permite abrir tarefas dentro do escopo autorizado.", False),
            (TAREFA_CRIAR, "Criar tarefa", "Permite adicionar tarefas a uma atividade.", False),
            (TAREFA_EDITAR, "Editar tarefa", "Permite alterar título, descrição, ordem e dependência.", False),
            (TAREFA_ATRIBUIR, "Atribuir executor", "Permite incluir ou remover executores de uma tarefa.", False),
            (TAREFA_ASSUMIR, "Assumir tarefa", "Permite que a pessoa se torne executora de uma tarefa disponível.", False),
            (TAREFA_INICIAR, "Iniciar tarefa", "Permite iniciar a execução e o registro de tempo.", False),
            (TAREFA_PAUSAR, "Pausar tarefa", "Permite pausar a própria sessão de trabalho.", False),
            (TAREFA_RETOMAR, "Retomar tarefa", "Permite retomar a execução de uma tarefa pausada.", False),
            (TAREFA_DEVOLVER, "Devolver tarefa", "Permite devolver a tarefa a um setor anterior, com motivo obrigatório.", False),
            (TAREFA_CONCLUIR, "Concluir tarefa", "Permite concluir a execução da tarefa.", False),
            (TAREFA_CANCELAR, "Cancelar tarefa", "Permite cancelar uma tarefa registrando o motivo.", True),
            (TAREFA_BLOQUEAR, "Bloquear e desbloquear tarefa", "Permite registrar e resolver impedimentos.", False),
            (TAREFA_MOVER_SETOR, "Enviar tarefa para outro setor", "Permite movimentar a tarefa no fluxo entre setores.", False),
            (TEMPO_LANCAR_MANUAL, "Lançar tempo manualmente", "Permite apropriar tempo trabalhado fora do cronômetro.", True),
        ],
    ),
    (
        "filas",
        "Filas",
        [
            (FILA_VISUALIZAR_POSICAO_PROPRIA, "Visualizar posição própria", "Permite acompanhar a posição das próprias demandas na fila, sem ver as demais.", False),
            (FILA_VISUALIZAR_COMPLETA, "Visualizar fila completa", "Permite ver todas as tarefas e detalhes da fila do setor no escopo autorizado.", False),
            (FILA_REORDENAR, "Reordenar fila", "Permite alterar a ordem de execução das tarefas do setor.", True),
        ],
    ),
    (
        "prazos",
        "Prazos",
        [
            (PRAZO_PROPOR, "Propor prazo", "Permite propor um novo prazo comprometido para a tarefa.", False),
            (PRAZO_ACEITAR, "Aceitar prazo", "Permite aceitar o prazo proposto pelo setor executor.", False),
            (PRAZO_RECUSAR, "Recusar prazo", "Permite recusar o prazo proposto, o que registra um conflito.", False),
            (ESCALONAMENTO_RESOLVER, "Resolver conflito de prazo", "Permite encerrar um conflito registrando a decisão tomada.", True),
        ],
    ),
    (
        "comunicacao",
        "Comunicação",
        [
            (COMUNICACAO_PARTICIPAR, "Participar da conversa", "Permite escrever mensagens no contexto de atividades e tarefas.", False),
        ],
    ),
    (
        "cadastros",
        "Cadastros",
        [
            (SETOR_CRIAR, "Criar setor", "Permite cadastrar novos setores na organização.", False),
            (SETOR_EDITAR, "Editar setor", "Permite alterar dados de um setor existente.", False),
            (SETOR_INATIVAR, "Inativar setor", "Permite inativar um setor, preservando o histórico.", True),
            (EMPRESA_GERIR, "Gerir empresas", "Permite criar, editar e inativar empresas da organização.", False),
            (OBRA_GERIR, "Gerir obras", "Permite criar, editar e inativar obras.", False),
            (CENTRO_CUSTO_GERIR, "Gerir centros de custo", "Permite criar, editar e inativar centros de custo.", False),
            (MOTIVO_DEVOLUCAO_GERIR, "Gerir motivos de devolução", "Permite manter a lista de motivos usada nas devoluções.", False),
        ],
    ),
    (
        "processos",
        "Processos",
        [
            (PROCESSO_VISUALIZAR, "Visualizar processos", "Permite consultar os modelos reutilizáveis cadastrados.", False),
            (PROCESSO_CRIAR, "Criar processo", "Permite cadastrar um novo processo em rascunho.", False),
            (PROCESSO_EDITAR_RASCUNHO, "Editar rascunho de processo", "Permite alterar inputs, output, critérios e fluxo antes da publicação.", False),
            (PROCESSO_PUBLICAR, "Publicar versão de processo", "Permite tornar uma versão do processo disponível para uso — depois disso ela não é mais alterada.", True),
            (PROCESSO_CRIAR_VERSAO, "Criar nova versão de processo", "Permite abrir uma nova versão a partir da publicada, sem alterar atividades já em andamento.", False),
            (PROCESSO_INATIVAR, "Inativar processo", "Permite impedir novas aplicações do processo, preservando o histórico.", True),
            (PROCESSO_APLICAR, "Aplicar processo em atividade", "Permite selecionar um processo publicado ao criar uma atividade.", False),
        ],
    ),
    (
        "seguranca",
        "Segurança",
        [
            (USUARIO_VISUALIZAR, "Visualizar usuários", "Permite consultar os usuários da organização.", False),
            (USUARIO_CRIAR, "Criar usuário", "Permite cadastrar novas pessoas na organização.", True),
            (USUARIO_EDITAR, "Editar usuário", "Permite alterar dados, setores e perfis de um usuário.", True),
            (USUARIO_INATIVAR, "Inativar usuário", "Permite encerrar o acesso de uma pessoa, preservando o histórico.", True),
            (SEGURANCA_GERIR_PERFIS, "Gerir perfis", "Permite criar e alterar perfis de acesso.", True),
            (SEGURANCA_GERIR_AUTORIZACOES, "Gerir autorizações", "Permite conceder e remover ações e escopos de usuários e perfis.", True),
        ],
    ),
    (
        "auditoria",
        "Auditoria",
        [
            (AUDITORIA_VISUALIZAR, "Visualizar auditoria", "Permite consultar o histórico de eventos do trabalho.", False),
            (METRICAS_VISUALIZAR, "Visualizar métricas", "Permite acessar a visão do gestor e os indicadores.", False),
        ],
    ),
]


# Perfis sugeridos na implantação. A organização pode renomear, alterar e criar
# outros — são um ponto de partida, não uma regra (doc 05 §11).
SUGGESTED_PROFILES = {
    "Colaborador": [
        ATIVIDADE_VISUALIZAR,
        ATIVIDADE_CRIAR,
        TAREFA_VISUALIZAR,
        TAREFA_ASSUMIR,
        TAREFA_INICIAR,
        TAREFA_PAUSAR,
        TAREFA_RETOMAR,
        TAREFA_CONCLUIR,
        TAREFA_DEVOLVER,
        TAREFA_BLOQUEAR,
        FILA_VISUALIZAR_POSICAO_PROPRIA,
        PRAZO_PROPOR,
        PRAZO_ACEITAR,
        PRAZO_RECUSAR,
        COMUNICACAO_PARTICIPAR,
        PROCESSO_VISUALIZAR,
        PROCESSO_APLICAR,
    ],
    "Gestor de Setor": [
        ATIVIDADE_VISUALIZAR,
        ATIVIDADE_VISUALIZAR_TODAS,
        ATIVIDADE_CRIAR,
        ATIVIDADE_EDITAR,
        TAREFA_VISUALIZAR,
        TAREFA_CRIAR,
        TAREFA_EDITAR,
        TAREFA_ATRIBUIR,
        TAREFA_ASSUMIR,
        TAREFA_INICIAR,
        TAREFA_PAUSAR,
        TAREFA_RETOMAR,
        TAREFA_CONCLUIR,
        TAREFA_DEVOLVER,
        TAREFA_BLOQUEAR,
        TAREFA_MOVER_SETOR,
        TEMPO_LANCAR_MANUAL,
        FILA_VISUALIZAR_POSICAO_PROPRIA,
        FILA_VISUALIZAR_COMPLETA,
        FILA_REORDENAR,
        PRAZO_PROPOR,
        PRAZO_ACEITAR,
        PRAZO_RECUSAR,
        ESCALONAMENTO_RESOLVER,
        COMUNICACAO_PARTICIPAR,
        METRICAS_VISUALIZAR,
        AUDITORIA_VISUALIZAR,
        PROCESSO_VISUALIZAR,
        PROCESSO_CRIAR,
        PROCESSO_EDITAR_RASCUNHO,
        PROCESSO_PUBLICAR,
        PROCESSO_CRIAR_VERSAO,
        PROCESSO_INATIVAR,
        PROCESSO_APLICAR,
    ],
    "Administrador": [key for _, _, actions in GROUPS for key, _, _, _ in actions],
}
