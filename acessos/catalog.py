"""Catálogo de ações da LPS (Regras 05 §13, doc 08 §19).

Uma ação existe porque a aplicação possui comportamento correspondente. A
organização combina estas ações em perfis, mas não inventa ações novas — caso
contrário a autorização existiria no banco sem proteger nada real (doc 05 §14).

Este arquivo é a única fonte da verdade do catálogo: o comando
`seed_acoes` o materializa no banco, e o código referencia as constantes.
"""

# Demandas (na interface a "Atividade" passou a se chamar "Demanda"; o nome das constantes
# em Python continua ATIVIDADE_*, e as chaves gravadas no banco foram renomeadas por
# acessos/migrations/0003 sem perder nenhuma concessão)
ATIVIDADE_VISUALIZAR = "demanda.visualizar"
ATIVIDADE_VISUALIZAR_TODAS = "demanda.visualizar_todas"
ATIVIDADE_CRIAR = "demanda.criar"
ATIVIDADE_EDITAR = "demanda.editar"
ATIVIDADE_ALTERAR_DONO = "demanda.alterar_dono"
ATIVIDADE_ASSUMIR = "demanda.assumir"
ATIVIDADE_CONCLUIR = "demanda.concluir"
ATIVIDADE_CANCELAR = "demanda.cancelar"
ATIVIDADE_REABRIR = "demanda.reabrir"
ATIVIDADE_MARCAR_PENDENTE = "demanda.marcar_pendente"
ATIVIDADE_APROVAR_PENDENCIA = "demanda.aprovar_pendencia"
ATIVIDADE_MOVER_ESTAGIO = "demanda.mover_estagio"
ATIVIDADE_DEFINIR_ETAPA = "demanda.definir_etapa"
ATIVIDADE_DEFINIR_CONDICAO = "demanda.definir_condicao"

# Tarefas
TAREFA_VISUALIZAR = "tarefa.visualizar"
TAREFA_CRIAR = "tarefa.criar"
TAREFA_EDITAR = "tarefa.editar"
TAREFA_ATRIBUIR = "tarefa.atribuir"
TAREFA_ALTERAR_RESPONSAVEL = "tarefa.alterar_responsavel"
TAREFA_ASSUMIR = "tarefa.assumir"
TAREFA_ACEITAR = "tarefa.aceitar"
TAREFA_RECUSAR = "tarefa.recusar"
TAREFA_INICIAR = "tarefa.iniciar"
TAREFA_PAUSAR = "tarefa.pausar"
TAREFA_RETOMAR = "tarefa.retomar"
TAREFA_DEVOLVER = "tarefa.devolver"
TAREFA_CONCLUIR = "tarefa.concluir"
TAREFA_CANCELAR = "tarefa.cancelar"
TAREFA_REABRIR = "tarefa.reabrir"
TAREFA_BLOQUEAR = "tarefa.bloquear"
TAREFA_MOVER_SETOR = "tarefa.mover_setor"
TAREFA_MOVER_ESTAGIO = "tarefa.mover_estagio"
TAREFA_DEFINIR_ETAPA = "tarefa.definir_etapa"
TAREFA_DEFINIR_CONDICAO = "tarefa.definir_condicao"
TEMPO_LANCAR_MANUAL = "tempo.lancar_manual"

# Filas
FILA_VISUALIZAR_POSICAO_PROPRIA = "fila.visualizar_posicao_propria"
FILA_VISUALIZAR_COMPLETA = "fila.visualizar_completa"
FILA_REORDENAR = "fila.reordenar"

# Prazos
PRAZO_PROPOR = "prazo.propor"
PRAZO_ACEITAR = "prazo.aceitar"
PRAZO_RECUSAR = "prazo.recusar"
PRAZO_ALTERAR_SOLICITADO = "prazo.alterar_solicitado"
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
CLIENTE_GERIR = "cliente.gerir"
MOTIVO_DEVOLUCAO_GERIR = "motivo_devolucao.gerir"
ESTAGIO_TAREFA_GERIR = "estagio_tarefa.gerir"
ETAPA_GERIR = "etapa.gerir"
CONDICAO_GERIR = "condicao.gerir"
TAG_GERIR = "tag.gerir"
COR_STATUS_GERIR = "cor_status.gerir"
COR_PRIORIDADE_GERIR = "cor_prioridade.gerir"

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

# Caixa de entrada (solicitações que ainda não viraram atividade)
ENTRADA_VISUALIZAR = "entrada.visualizar"
ENTRADA_REGISTRAR = "entrada.registrar"
ENTRADA_TRIAR = "entrada.triar"


# (chave, nome, descrição, sensível)
GROUPS = [
    (
        "demandas",
        "Demandas",
        [
            (ATIVIDADE_VISUALIZAR, "Visualizar demandas", "Permite abrir demandas dentro do escopo autorizado.", False),
            (ATIVIDADE_VISUALIZAR_TODAS, "Visualizar todas as demandas", "Permite ver demandas de que a pessoa não é dona nem executora.", False),
            (ATIVIDADE_CRIAR, "Criar demanda", "Permite registrar um novo resultado a ser alcançado.", False),
            (ATIVIDADE_EDITAR, "Editar demanda", "Permite alterar título, descrição, prazo e contexto da demanda.", False),
            (ATIVIDADE_ALTERAR_DONO, "Alterar dono da demanda", "Permite transferir a responsabilidade pelo resultado para outra pessoa.", True),
            (ATIVIDADE_ASSUMIR, "Assumir demanda do grupo", "Permite se tornar dono de uma demanda endereçada ao setor da pessoa, direto na fila do grupo.", False),
            (ATIVIDADE_CONCLUIR, "Concluir demanda", "Permite encerrar a demanda quando o resultado foi alcançado.", False),
            (ATIVIDADE_CANCELAR, "Cancelar demanda", "Permite cancelar a demanda registrando o motivo.", True),
            (ATIVIDADE_REABRIR, "Reabrir demanda", "Permite reabrir uma demanda já concluída.", True),
            (ATIVIDADE_MARCAR_PENDENTE, "Marcar demanda como pendente", "Permite pausar a demanda registrando o motivo da pendência, com comentário obrigatório.", False),
            (ATIVIDADE_APROVAR_PENDENCIA, "Aprovar pendência da demanda", "Permite decidir uma pendência que aguarda aprovação do gestor, devolvendo a demanda para quem a designou.", True),
            (ATIVIDADE_MOVER_ESTAGIO, "Mover estágio da demanda", "Permite alterar o estágio visual de uma demanda no Kanban.", False),
            (ATIVIDADE_DEFINIR_ETAPA, "Definir etapa da demanda", "Permite selecionar a etapa visual da demanda dentro do seu setor.", False),
            (ATIVIDADE_DEFINIR_CONDICAO, "Definir condição da demanda", "Permite selecionar a condição manual da demanda dentro do seu setor.", False),
        ],
    ),
    (
        "tarefas",
        "Tarefas",
        [
            (TAREFA_VISUALIZAR, "Visualizar tarefas", "Permite abrir tarefas dentro do escopo autorizado.", False),
            (TAREFA_CRIAR, "Criar tarefa", "Permite adicionar tarefas a uma demanda.", False),
            (TAREFA_EDITAR, "Editar tarefa", "Permite alterar título, descrição, ordem e dependência.", False),
            (TAREFA_ATRIBUIR, "Atribuir participante", "Permite incluir ou remover participantes de uma tarefa.", False),
            (TAREFA_ALTERAR_RESPONSAVEL, "Alterar responsável da tarefa", "Permite transferir a responsabilidade pela conclusão da tarefa para outra pessoa.", True),
            (TAREFA_ASSUMIR, "Assumir tarefa", "Permite que a pessoa se torne participante de uma tarefa disponível.", False),
            (TAREFA_ACEITAR, "Aceitar atribuição", "Permite aceitar uma tarefa que outra pessoa atribuiu, tornando-se participante.", False),
            (TAREFA_RECUSAR, "Recusar atribuição", "Permite recusar uma tarefa atribuída por outra pessoa, com motivo obrigatório.", False),
            (TAREFA_INICIAR, "Iniciar tarefa", "Permite iniciar a execução e o registro de tempo.", False),
            (TAREFA_PAUSAR, "Pausar tarefa", "Permite pausar a própria sessão de trabalho.", False),
            (TAREFA_RETOMAR, "Retomar tarefa", "Permite retomar a execução de uma tarefa pausada.", False),
            (TAREFA_DEVOLVER, "Devolver tarefa", "Permite devolver a tarefa a um setor anterior, com motivo obrigatório.", False),
            (TAREFA_CONCLUIR, "Concluir tarefa", "Permite concluir a execução da tarefa.", False),
            (TAREFA_CANCELAR, "Cancelar tarefa", "Permite cancelar uma tarefa registrando o motivo.", True),
            (TAREFA_REABRIR, "Reabrir tarefa", "Permite reabrir uma tarefa concluída: ela volta ao fim da fila do setor, com motivo obrigatório e registro no histórico.", True),
            (TAREFA_BLOQUEAR, "Bloquear e desbloquear tarefa", "Permite registrar e resolver impedimentos.", False),
            (TAREFA_MOVER_SETOR, "Enviar tarefa para outro setor", "Permite movimentar a tarefa no fluxo entre setores.", False),
            (TAREFA_MOVER_ESTAGIO, "Mover estágio da tarefa", "Permite alterar o estágio visual de uma tarefa no Kanban.", False),
            (TAREFA_DEFINIR_ETAPA, "Definir etapa da tarefa", "Permite selecionar a etapa visual da tarefa dentro do seu setor.", False),
            (TAREFA_DEFINIR_CONDICAO, "Definir condição da tarefa", "Permite selecionar a condição manual da tarefa dentro do seu setor.", False),
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
            (PRAZO_ALTERAR_SOLICITADO, "Alterar prazo solicitado", "Permite corrigir ou renegociar o prazo solicitado da tarefa.", False),
            (ESCALONAMENTO_RESOLVER, "Resolver conflito de prazo", "Permite encerrar um conflito registrando a decisão tomada.", True),
        ],
    ),
    (
        "comunicacao",
        "Comunicação",
        [
            (COMUNICACAO_PARTICIPAR, "Participar da conversa", "Permite escrever mensagens no contexto de demandas e tarefas.", False),
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
            (CLIENTE_GERIR, "Gerir clientes", "Permite criar, editar e inativar clientes da organização.", False),
            (MOTIVO_DEVOLUCAO_GERIR, "Gerir motivos de devolução", "Permite manter a lista de motivos usada nas devoluções.", False),
            (ESTAGIO_TAREFA_GERIR, "Gerir estágios de tarefa", "Permite criar, editar, reordenar e inativar os estágios (colunas do Kanban) de tarefa da organização.", False),
            (ETAPA_GERIR, "Gerir etapas", "Permite criar, editar, reordenar e inativar etapas de demandas e tarefas por setor.", False),
            (CONDICAO_GERIR, "Gerir condições", "Permite criar, editar, reordenar e inativar condições manuais por setor.", False),
            (TAG_GERIR, "Gerir marcadores", "Permite criar, editar e inativar os marcadores (tags) usados em demandas e tarefas da organização.", False),
            (COR_STATUS_GERIR, "Gerir cores de status", "Permite customizar a cor visual dos status de demanda e de tarefa da organização.", False),
            (COR_PRIORIDADE_GERIR, "Gerir cores de prioridade", "Permite customizar a cor visual das prioridades (urgência) das demandas da organização.", False),
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
            (PROCESSO_CRIAR_VERSAO, "Criar nova versão de processo", "Permite abrir uma nova versão a partir da publicada, sem alterar demandas já em andamento.", False),
            (PROCESSO_INATIVAR, "Inativar processo", "Permite impedir novas aplicações do processo, preservando o histórico.", True),
            (PROCESSO_APLICAR, "Aplicar processo em demanda", "Permite aplicar a versão publicada de um processo a uma demanda: ela recebe as entradas, os critérios de aceite e as tarefas do fluxo, em todos os setores do processo.", False),
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
    (
        "entrada",
        "Caixa de entrada",
        [
            (ENTRADA_VISUALIZAR, "Ver a Caixa de Entrada", "Permite consultar as solicitações recebidas que ainda aguardam triagem, dentro do escopo autorizado.", False),
            (ENTRADA_REGISTRAR, "Registrar solicitação", "Permite colocar na Caixa de Entrada um pedido recebido por e-mail, Teams ou conversa.", False),
            (ENTRADA_TRIAR, "Triar solicitações", "Permite corrigir as sugestões, criar a demanda a partir da solicitação, ignorá-la ou restaurá-la.", False),
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
        TAREFA_ACEITAR,
        TAREFA_RECUSAR,
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
        CLIENTE_GERIR,
        ATIVIDADE_ASSUMIR,
        ATIVIDADE_MARCAR_PENDENTE,
        ATIVIDADE_MOVER_ESTAGIO,
        ATIVIDADE_DEFINIR_ETAPA,
        ATIVIDADE_DEFINIR_CONDICAO,
        ENTRADA_REGISTRAR,
    ],
    "Gestor de Setor": [
        ATIVIDADE_VISUALIZAR,
        ATIVIDADE_VISUALIZAR_TODAS,
        ATIVIDADE_CRIAR,
        ATIVIDADE_EDITAR,
        ATIVIDADE_ASSUMIR,
        ATIVIDADE_MARCAR_PENDENTE,
        ATIVIDADE_APROVAR_PENDENCIA,
        TAREFA_VISUALIZAR,
        TAREFA_CRIAR,
        TAREFA_EDITAR,
        TAREFA_ATRIBUIR,
        TAREFA_ASSUMIR,
        TAREFA_ACEITAR,
        TAREFA_RECUSAR,
        TAREFA_INICIAR,
        TAREFA_PAUSAR,
        TAREFA_RETOMAR,
        TAREFA_CONCLUIR,
        TAREFA_DEVOLVER,
        TAREFA_BLOQUEAR,
        TAREFA_MOVER_SETOR,
        TAREFA_MOVER_ESTAGIO,
        TAREFA_DEFINIR_ETAPA,
        TAREFA_DEFINIR_CONDICAO,
        TAREFA_REABRIR,
        TEMPO_LANCAR_MANUAL,
        FILA_VISUALIZAR_POSICAO_PROPRIA,
        FILA_VISUALIZAR_COMPLETA,
        FILA_REORDENAR,
        PRAZO_PROPOR,
        PRAZO_ALTERAR_SOLICITADO,
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
        CLIENTE_GERIR,
        ESTAGIO_TAREFA_GERIR,
        ETAPA_GERIR,
        CONDICAO_GERIR,
        TAG_GERIR,
        COR_STATUS_GERIR,
        COR_PRIORIDADE_GERIR,
        ENTRADA_VISUALIZAR,
        ENTRADA_REGISTRAR,
        ENTRADA_TRIAR,
    ],
    "Administrador": [key for _, _, actions in GROUPS for key, _, _, _ in actions],
}
