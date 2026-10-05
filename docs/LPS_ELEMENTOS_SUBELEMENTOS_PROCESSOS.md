# LPS — Elementos, Subelementos e Integração com Processos

## Status de implementação (03/10/2026)

Este documento é uma **especificação**; o código (HEAD `add5acd`) implementa só parte dela, e de forma diferente da proposta.
Na interface, Atividade virou **Demanda** (o código segue `Activity`), "Situação" virou **Etapa** e "Condição" virou **Status**; "Etapa" neste
documento continua significando a **etapa do Processo** (`ProcessStep`), que não é a Etapa de fluxo da Demanda. Em vez de Elemento/Subelemento
num mesmo Quadro, cada Demanda ganhou o **seu próprio Quadro** (`Board` com `kind=DEMAND`, `Activity.task_board`, criado em branco ou copiado de um
modelo `kind=TEMPLATE`), e as tarefas são **itens planos** (`BoardItem`) desse quadro, sem `parent`. O app `processes` está **desativado**: desde 02/10/2026
`/processos/*` e `/demandas/<pk>/processo/aplicar/` respondem 410, e a `Task` antiga ficou só como histórico (`/tarefas/<pk>/…` também responde 410). Os modelos e o
serviço de aplicação de processo continuam no código, sem tela. Legenda: **Implementado**, **Parcial**, **Não implementado**, **Divergente**.

| Requisito / bloco | Status | Onde está no código |
|---|---|---|
| Demanda como Elemento (§3, §6.1) | Implementado | `activities.Activity`; lista em `/demandas/` sobre `boards.DomainBoard` (`domain=DEMAND`) com campos próprios (`DomainBoardField`, `DomainCustomValue`) |
| Esquema de colunas próprio por nível (§3.2, §4.3, §5) | Divergente | Cada Demanda tem um Quadro com colunas próprias (`BoardColumn`, 8 tipos ativos: Texto, Número, Moeda, Data, Pessoa, Status, Lista suspensa, Sinal de confirmação); o esquema da lista de Demandas é outro (`DomainBoardField`) |
| Tarefa como Subelemento ligado ao pai (§4, §8, §40, §193) | Divergente | Tarefa = `BoardItem` do Quadro da Demanda (`boards/models.py`); não há relação pai × filho entre itens nem `Task` por item; o vínculo é Quadro ↔ `Activity` (`OneToOneField`) |
| Profundidade de um nível (§7) | Parcial | Ocorre por construção (Demanda → itens do seu quadro); itens não têm filhos |
| Exclusão do pai e mover filho (§8.1, §8.2) | Parcial | Excluir a Demanda remove o Quadro (`on_delete=CASCADE`); mover item só entre grupos do mesmo quadro (`ItemMoveView`) |
| Tabela com Subelementos expansíveis, cabeçalhos próprios do filho (§9–§12, §170–§172) | Não implementado | Existe a Tabela do quadro de cada Demanda (`boards/board_detail.html`, `boards.js`) e a prévia de até 5 tarefas na ficha (`boards/demand_preview.py`) |
| Kanban de Demandas com filhos expansíveis (§13–§17) | Não implementado | Há Kanban da lista de Demandas (`work-board.js`) e Kanban dentro do Quadro de cada Demanda (`board_kanban.html`), mas separados e sem expandir filhos |
| Calendário de Demandas e de Tarefas (§19) | Parcial | Calendário mensal por quadro (`board_calendar.html`); `/demandas/calendario/` é uma lista por prazo; `/tarefas/calendario/` é semanal (`boards/task_center.py`) |
| Status independentes e Status do filho não move o pai (§5.2, §16) | Implementado | Demanda: Etapa + Status do setor (`workflow-picker.js`); tarefa: coluna Status do quadro; nenhuma regra automática move o pai |
| Painel Gestão × Operação (§18, §165–§167) | Parcial | `/demandas/` (gestão) e `/tarefas/` (o que está nos quadros em que a pessoa é responsável: `boards/task_center.py`, `task_center_views.py`) |
| Processo como blueprint versionado: `Process`, `ProcessVersion`, `ProcessInput`, `ProcessCriterion`, `ProcessStep` (§20–§23, §31–§33) | Implementado (desativado) | `processes/models.py`; versão publicada imutável (testes em `processes/tests.py`); telas `process_*.html` inacessíveis (410) |
| Aplicar Processo à Demanda, gravar `process_version`, fixar versão (§28, §69, §71, §193 itens 5–6) | Implementado (desativado) | `activities/process_application.py` (`ProcessApplicationService.apply`), `Activity.process_version`; rota `activity-process-apply` responde 410 |
| Gerar Subelementos a partir das etapas (§41–§52, Fase 3) | Divergente | O serviço cria objetos `Task` (com `process_step`, `depends_on` e fila), não itens do quadro; congelado |
| Dependências e disponibilidade (§47–§50) | Parcial | Uma dependência por tarefa (`Task.depends_on`, `TaskService.pending_dependency`); só no modelo legado |
| Inputs e critérios de aceite do Processo (§35–§39, §58–§59, Fase 4) | Implementado (desativado) | `processes.ActivityInputValue`, `ActivityCriterionCheck`; `ActivityProcessService.update_input/set_criterion`; sem tela |
| Output e evidência (§56–§57) | Parcial | Campos de output/evidência na versão do Processo (`ProcessVersion`); sem tela ativa |
| Trocar ou remover Processo (§72, §73) | Não implementado | Não há serviço nem rota |
| Subelemento manual e origem manual × processo (§52–§55) | Parcial | Itens manuais são o caso normal do quadro; a origem não é registrada |
| Template de Elemento e de Subelemento (§76–§77) | Divergente | Substituído por **modelos de quadro** (`Board.kind=TEMPLATE`, `boards/starter_templates.py`, `BoardInstantiationService` em `boards/demand_services.py`, escolha no passo 3 do Nova demanda; trocar o quadro apaga as tarefas, com confirmação) |
| Progresso e conclusão da Demanda a partir dos filhos (§60–§65, Fase 5) | Parcial | Ficha: total/concluídas, "pronta para concluir" lidos do quadro (`ActivityDetailView`, `DemandBoardPreviewQuery`); sem rollup, fórmula ou coluna Relação (tipos reservados) |
| Rollups, Fórmula, indicadores, Dashboard (§66–§68, §136–§138, §162) | Não implementado | Tipos `FORMULA`, `RELATION`, `AI_EXTRACT` existem só como reservados em `BoardColumn.Type` |
| Permissões (§86–§89, §180–§182) | Parcial | Ações `quadro.*` em `acessos/catalog.py`; `DemandBoardAccess` decide quem gere a estrutura e os itens de cada Quadro de Demanda |
| Auditoria e histórico (§90–§92) | Implementado | `audit.AuditLog` com `BOARD_*` (itens, células, colunas, visões); histórico do quadro em `board_history.html` |
| Multi-organização (§94) | Implementado | Todo `Board`/`DomainBoard` tem `organization`; testes de isolamento em `boards/test_views.py` |
| Aprendizado do Processo, Processo condicional e com caminhos, automações (§132–§135, §155–§159, Fase 6) | Não implementado | — |
| Linguagem da interface (§197) | Parcial | Interface e URLs dizem Demanda/Etapa/Status (`/demandas/`); o código mantém `Activity`, `Task` |

> **Divergência:** este documento propõe Subelementos **dentro** do Quadro do pai. A implementação atual separa os níveis: a Demanda é uma linha de
> `/demandas/` e o Quadro dela contém as tarefas como itens planos. Qualquer requisito de expansão, rollup ou herança de contexto
> (§9–§17, §66, §96, §141–§147) continua válido como proposta, mas precisa de decisão de produto antes de ser construído.

## 1. Objetivo

Este documento define o conceito oficial de:

- **Elemento**;
- **Subelemento**;
- relação pai × filho;
- comportamento nas visualizações;
- relação com Demandas e Tarefas;
- integração com o motor de Processos da LPS;
- regras de criação automática e manual;
- versionamento;
- inputs, etapas, outputs e critérios de aceite;
- permissões;
- auditoria;
- agregações;
- critérios de aceite.

O objetivo é permitir que a LPS seja flexível como um Quadro dinâmico, sem perder o conceito de **processo padronizado**.

---

# 2. Estado atual da LPS

## 2.1 Atividade (hoje Demanda) e Tarefa

Na arquitetura atual:

```text
Activity
└── Task
```

Uma `Activity` pode possuir várias `Task`.

Na experiência futura da LPS:

```text
Activity = Demanda
Task     = Tarefa
```

Portanto, no Quadro de Demandas:

```text
Elemento    = Demanda
Subelemento = Tarefa
```

> **Divergência (03/10/2026):** a interface já usa Demanda, mas a Tarefa deixou de ser a `Task` filha da `Activity`: as tarefas viram itens
> (`BoardItem`) do Quadro de cada Demanda e a `Task` ficou como histórico (rotas `/tarefas/<pk>/…` respondem 410).

---

## 2.2 Processo atual

A LPS já possui o app `processes`.

Hoje um Processo é um modelo reutilizável e versionado de **como fazer um tipo de atividade**.

A estrutura existente contempla:

```text
Process
└── ProcessVersion
    ├── ProcessInput
    ├── ProcessCriterion
    └── ProcessStep
```

Uma versão de Processo possui:

- inputs;
- output esperado;
- tipo de evidência;
- critérios de aceite;
- etapas ordenadas;
- setor responsável por cada etapa;
- dependência da etapa anterior.

---

## 2.3 Lacuna registrada na época (histórico)

A documentação atual registra uma lacuna importante:

> Processos podem ser criados, versionados e publicados, mas ainda não são aplicados às Atividades.

Atualmente existem estruturas como:

```text
Activity.process_version
ActivityInputValue
ActivityCriterionCheck
```

porém o sistema ainda não:

- aplica automaticamente uma versão de Processo à Activity;
- gera Tarefas a partir das etapas;
- preenche inputs do Processo na Activity;
- registra os critérios de aceite durante a execução.

Portanto, a integração descrita neste documento é uma **evolução arquitetural proposta**, não um comportamento já implementado.

> **Divergência (03/10/2026):** a lacuna acima foi fechada no backend e depois desativada. `ProcessApplicationService.apply` aplica uma versão,
> gera tarefas e registra inputs e critérios (`activities/process_application.py`), mas as rotas e telas de Processo respondem 410 desde 02/10/2026
> e o fluxo novo de tarefas passa pelos Quadros por Demanda.

---

# 3. Conceito de Elemento

## 3.1 Definição

Um **Elemento** é o registro principal de um Quadro.

Exemplos:

```text
Quadro: Demandas
Elemento: Arena Center Norte — Elaborar orçamento
```

```text
Quadro: Contratos
Elemento: Contrato OB-077 — Alfalog
```

```text
Quadro: Compras
Elemento: Pedido de compra 00382
```

---

## 3.2 O Elemento possui seu próprio esquema de colunas

Exemplo de Demanda:

```text
Título
Cliente
Obra
Solicitante
Responsável
Setor
Status
Prioridade
Prazo
Valor
```

O conjunto de colunas pertence ao esquema do **Elemento** daquele Quadro.

---

## 3.3 Elemento é a unidade principal de gestão

O Elemento deve representar algo que faça sentido acompanhar sozinho.

Exemplo:

```text
Demanda
```

A pergunta gerencial deve ser:

> O que precisa ser entregue?

e não:

> Quais pequenos passos estão sendo executados?

Os pequenos passos pertencem ao nível inferior.

---

# 4. Conceito de Subelemento

## 4.1 Definição

Um **Subelemento** é um registro filho vinculado diretamente a um Elemento.

Exemplo:

```text
Demanda: Elaborar orçamento Arena Center Norte

Tarefas:
├── Conferir projetos
├── Levantar quantitativos
├── Solicitar cotações
└── Revisar proposta
```

---

## 4.2 Subelemento não é apenas uma linha visual menor

Ele é um registro real.

Possui:

- ID próprio;
- título;
- valores próprios;
- status próprio;
- responsável próprio;
- prazo próprio;
- histórico próprio;
- permissões;
- auditoria;
- possibilidade de conclusão.

---

## 4.3 Subelemento possui esquema próprio de colunas

Esse é um requisito central.

O Subelemento **não herda automaticamente todas as colunas do Elemento**.

Exemplo:

### Elemento — Demanda

```text
Cliente
Obra
Solicitante
Responsável
Status comercial
Prazo
Valor
```

### Subelemento — Tarefa

```text
Responsável
Setor
Status da tarefa
Prioridade
Prazo solicitado
Prazo comprometido
Checklist
```

Os dois níveis usam o mesmo motor de tipos de coluna, mas seus esquemas são independentes.

---

# 5. Mesmo motor, schemas diferentes

A arquitetura deve ser:

```text
Board
├── ElementSchema
│   └── Columns
│
└── SubitemSchema
    └── Columns
```

Não:

```text
BoardColumn
└── copiar automaticamente para subelementos
```

---

## 5.1 Reutilização de tipos

Os mesmos componentes de coluna devem ser reutilizados.

Exemplo:

```text
PeopleColumn
StatusColumn
DateColumn
MoneyColumn
FormulaColumn
RelationColumn
```

Eles podem existir no Elemento e no Subelemento com configurações diferentes.

---

## 5.2 Status independentes

Exemplo:

### Status da Demanda

```text
Entrada
Levantamento
Cotação
Revisão
Enviado
Declinado
```

### Status da Tarefa

```text
A fazer
Em execução
Bloqueada
Concluída
```

Mesmo tipo técnico:

```text
Status
```

mas duas colunas e duas configurações independentes.

---

# 6. Elemento e Subelemento na LPS

## 6.1 Demandas

Para o primeiro caso principal:

```text
Elemento = Demanda
Subelemento = Tarefa
```

Isso conversa diretamente com a estrutura atual:

```text
Activity
└── Task
```

---

## 6.2 Motor genérico

Apesar disso, a arquitetura não deve chamar todo Subelemento de Tarefa internamente.

Porque outros Quadros podem usar:

```text
Contrato
└── Aditivos
```

```text
Pedido de compra
└── Itens
```

```text
Obra
└── Entregáveis
```

```text
Inspeção
└── Não conformidades
```

Portanto:

> **Tarefa é um caso de uso de Subelemento.**

---

# 7. Profundidade

Na primeira versão, permitir apenas:

```text
Elemento
└── Subelemento
```

Não permitir:

```text
Elemento
└── Subelemento
    └── Sub-sub-elemento
        └── ...
```

---

## 7.1 Motivo

Profundidade ilimitada gera:

- navegação complexa;
- Kanban difícil;
- filtros ambíguos;
- permissões confusas;
- fórmulas recursivas;
- relatórios difíceis de interpretar.

Se um terceiro nível surgir como necessidade real, deve ser tratado como outro domínio ou relação explícita.

---

# 8. Relação pai × filho

Todo Subelemento deve possuir:

```text
parent_item_id
```

ou equivalente.

Regra:

> Subelemento não existe solto.

Ele pertence a exatamente um Elemento pai.

---

## 8.1 Exclusão do pai

Não excluir filhos silenciosamente.

Ao excluir/inativar um Elemento:

- verificar Subelementos;
- manter histórico;
- usar exclusão lógica quando houver dados operacionais.

---

## 8.2 Mover Subelemento para outro pai

Não deve ser uma edição trivial.

Mover uma Tarefa de uma Demanda para outra altera contexto de negócio.

Deve exigir:

- permissão;
- confirmação;
- auditoria;
- validação de compatibilidade.

---

# 9. Apresentação na Tabela

Na Tabela, o Elemento aparece como linha principal.

Exemplo:

```text
▼ Arena Center Norte | Ryan | Em andamento | 15/10 | R$ 2,5 mi
```

Ao expandir:

```text
    Tarefa                    Responsável   Status       Prazo
    Conferir projetos         Jennifer      Concluída    05/10
    Levantar quantitativos    Ryan          Em execução  08/10
    Solicitar cotações        Luan          A fazer      10/10

    + Adicionar tarefa
```

---

# 10. Cabeçalhos próprios do Subelemento

Ao expandir um Elemento, o bloco filho deve possuir seus próprios cabeçalhos.

Exemplo:

```text
Tarefa | Responsável | Status | Prazo | Prioridade | +
```

Esses cabeçalhos não precisam coincidir com os cabeçalhos da linha pai.

---

# 11. Configurar colunas do Subelemento

Dentro do cabeçalho dos Subelementos:

```text
+
```

abre o mesmo seletor de tipos:

```text
Status
Texto
Pessoas
Data
Número
Moeda
Lista
Prioridade
Fórmula
...
```

A nova coluna é adicionada somente ao schema do Subelemento.

---

# 12. Redimensionamento e movimentação

As colunas do Subelemento devem poder:

- ser movidas;
- redimensionadas;
- renomeadas;
- filtradas;
- ordenadas;
- ocultadas.

Independentemente das colunas do Elemento.

---

# 13. Apresentação no Kanban

No Kanban de Elementos, o card principal representa o Elemento.

Exemplo:

```text
Em andamento

┌─────────────────────────────┐
│ Arena Center Norte          │
│ Ryan                        │
│ 15/10/2026                  │
│ Comercial                   │
│                         3 ▣ │
└─────────────────────────────┘
```

O indicador:

```text
3 ▣
```

mostra a quantidade de Subelementos.

---

# 14. Expandir Subelementos no Kanban

Ao clicar no indicador:

```text
┌─────────────────────────────┐
│ Arena Center Norte          │
│ ...                         │
└─────────────────────────────┘

   ┌─────────────────────────┐
   │ Conferir projetos       │
   └─────────────────────────┘

   ┌─────────────────────────┐
   │ Levantar quantitativos  │
   └─────────────────────────┘

   + Adicionar tarefa
```

Os filhos aparecem abaixo do card pai.

---

# 15. Coluna do Kanban do pai

Regra fundamental:

> No Kanban de Elementos, a coluna é determinada pelo campo do Elemento.

Exemplo:

```text
Agrupar por: Status da Demanda
```

A Demanda está em:

```text
Em andamento
```

Todas as Tarefas expandidas permanecem visualmente sob essa Demanda.

---

# 16. Status do Subelemento não move o pai

Se:

```text
Demanda = Em andamento
```

e:

```text
Tarefa A = Concluída
Tarefa B = Em execução
```

a Demanda continua na coluna:

```text
Em andamento
```

Não mover a Demanda automaticamente.

---

# 17. Kanban próprio dos Subelementos

Para operar Tarefas:

```text
Kanban de Tarefas
```

Agrupar por:

```text
Status da Tarefa
```

Resultado:

```text
A fazer | Em execução | Bloqueada | Concluída
```

Cada Tarefa passa a ser card principal.

---

# 18. Duas perspectivas complementares

## Gestão

```text
Kanban de Demandas
```

Responde:

- onde estão as Demandas;
- quais estão travadas;
- quais têm muitas Tarefas;
- quais possuem risco.

## Operação

```text
Kanban de Tarefas
```

Responde:

- o que precisa ser feito;
- quem é responsável;
- o que está bloqueado;
- o que vence.

---

# 19. Apresentação no Calendário

Elemento e Subelemento podem possuir calendários diferentes.

Exemplo:

### Calendário de Demandas

```text
Data = prazo da Demanda
```

### Calendário de Tarefas

```text
Data = prazo comprometido da Tarefa
```

Não misturar os dois níveis automaticamente.

---

# 20. O que é Processo

Processo não é Elemento.

Processo não é Subelemento.

Processo é:

> **um modelo versionado de como um tipo de trabalho deve ser executado.**

Analogia:

```text
Processo     = receita
Elemento     = pedido que será produzido
Subelemento  = etapas concretas de execução daquele pedido
```

---

# 21. Processo como blueprint

Blueprint significa um modelo estruturado usado para criar instâncias reais.

Exemplo:

```text
Processo:
Elaboração de orçamento
```

Define:

```text
Inputs
Etapas
Output
Critérios de aceite
Responsabilidades
```

Quando aplicado:

```text
Demanda:
Orçamento Arena Center Norte
```

gera a execução concreta.

---

# 22. Processo não deve armazenar trabalho operacional

O Processo não deve conter:

```text
Ryan está executando
prazo atual 15/10
comentário do cliente
arquivo recebido hoje
```

Isso pertence ao Elemento e aos Subelementos reais.

O Processo guarda:

```text
como deve funcionar
```

e não:

```text
o que está acontecendo agora
```

---

# 23. Estrutura conceitual

```text
PROCESSO
│
├── Inputs necessários
├── Etapas
├── Output esperado
└── Critérios de aceite

            ↓ aplicar

ELEMENTO
│
├── Dados reais
├── Valores dos inputs
├── Resultado
├── Critérios verificados
│
└── SUBELEMENTOS
     ├── Etapa/Tarefa A
     ├── Etapa/Tarefa B
     └── Etapa/Tarefa C
```

---

# 24. Processo × Quadro

O Quadro define:

```text
quais dados podem existir
```

O Processo define:

```text
como um determinado tipo de trabalho usa esses dados e deve ser executado
```

---

# 25. Board Schema não deve ser recriado pelo Processo

Evitar:

```text
cada Processo cria uma nova coluna duplicada chamada Prazo
```

O Processo deve referenciar colunas existentes por ID.

Exemplo:

```text
ProcessInput:
"Projeto recebido"
→ board_column_id = 84
```

---

# 26. Vantagem

Renomear:

```text
Projeto recebido
```

para:

```text
Projetos recebidos
```

não quebra o Processo.

A referência continua pelo ID.

---

# 27. Tipos de Processo por Quadro

Um Quadro pode possuir vários Processos.

Exemplo:

```text
Quadro: Demandas

Processos:
- Elaborar orçamento
- Revisar orçamento
- Visita técnica
- Solicitação interna
- Aprovação de documento
```

Todos geram Demandas dentro do mesmo motor, mas com fluxos diferentes.

---

# 28. Escolha do Processo

Ao criar uma Demanda:

```text
Criar demanda

Tipo/processo:
[ Elaborar orçamento v ]
```

Ou:

```text
Sem processo
```

A organização pode decidir se Processo é obrigatório para determinados Quadros.

---

# 29. Elemento sem Processo

A LPS deve permitir, em Quadros autorizados:

```text
Elemento sem Processo
```

Isso atende trabalhos:

- ad hoc;
- exceções;
- atividades administrativas;
- registros simples.

Ad hoc significa algo criado para uma necessidade específica, fora de um fluxo padronizado.

---

# 30. Processo obrigatório

Para processos críticos, a organização pode configurar:

```text
Exigir Processo: Sim
```

Exemplo:

```text
Pedido de compra
```

pode exigir um Processo publicado.

---

# 31. Versão do Processo

Ao aplicar um Processo, o Elemento deve guardar:

```text
process_version_id
```

e não apenas:

```text
process_id
```

---

# 32. Motivo

Processos evoluem.

Exemplo:

```text
Elaborar orçamento v3
```

é aplicado em 01/10.

Em 15/10 é publicada:

```text
v4
```

A Demanda iniciada em v3 continua sabendo exatamente quais regras recebeu.

---

# 33. Imutabilidade da versão publicada

Uma versão publicada não deve ser alterada retroativamente.

Fluxo:

```text
v3 PUBLICADA
→ criar v4 RASCUNHO
→ editar
→ publicar v4
→ v3 SUBSTITUÍDA
```

Elementos existentes em v3 permanecem vinculados à v3.

---

# 34. Atualização de Elemento em andamento

Não migrar automaticamente:

```text
v3 → v4
```

Isso pode mudar tarefas e critérios durante a execução.

Se houver necessidade de migração:

```text
Atualizar para v4
```

deve ser uma ação explícita e auditada.

---

# 35. Inputs do Processo

Input é uma informação necessária para executar o trabalho.

Exemplos:

```text
Projeto
Memorial
Prazo solicitado
Escopo
Contato do cliente
```

---

# 36. Input deve mapear para Coluna quando possível

Exemplo:

```text
ProcessInput:
Prazo solicitado
```

mapeado para:

```text
ElementoColumn:
Prazo
```

Não armazenar o mesmo valor em dois lugares sem necessidade.

---

# 37. Inputs especiais

Alguns inputs podem não ser colunas normais.

Exemplo:

```text
Confirmação de recebimento
```

Ainda assim, a preferência é usar o motor de colunas sempre que possível.

---

# 38. Input obrigatório

Um Processo pode declarar:

```text
Projeto = obrigatório
Prazo = obrigatório
Cliente = obrigatório
```

A Demanda não avança para execução sem os inputs necessários.

---

# 39. Origem do Input

A estrutura atual contempla fontes como:

```text
Solicitante
Executor
Terceiro
```

A interface deve deixar isso claro.

Exemplo:

```text
Projeto
Responsável por fornecer: Solicitante
```

---

# 40. Processo e Subelementos

As etapas do Processo devem poder gerar Subelementos.

Exemplo:

```text
Processo: Elaborar orçamento

Etapa 1: Conferir documentação
Etapa 2: Levantar quantitativos
Etapa 3: Solicitar cotações
Etapa 4: Revisar proposta
Etapa 5: Enviar proposta
```

Ao aplicar:

```text
Demanda: Arena Center Norte
```

pode gerar:

```text
Tarefas:
- Conferir documentação
- Levantar quantitativos
- Solicitar cotações
- Revisar proposta
- Enviar proposta
```

---

# 41. ProcessStep como template

`ProcessStep` é definição.

A Tarefa é instância.

```text
ProcessStep
"Solicitar cotações"
```

gera:

```text
Task
"Solicitar cotações"
```

---

# 42. Não usar a própria etapa como Tarefa

Porque a etapa pertence à versão do Processo e é reutilizada por muitas Demandas.

Exemplo:

```text
ProcessStep #17
```

pode gerar centenas de Tarefas ao longo do tempo.

---

# 43. Campos padrão por etapa

Uma etapa pode definir valores sugeridos para o Subelemento.

Exemplo:

```text
Nome: Solicitar cotações
Setor padrão: Suprimentos
Prioridade padrão: Média
Prazo relativo: D+2
```

---

# 44. Responsável padrão

Uma etapa pode definir:

```text
Setor responsável
```

mas evitar fixar pessoa específica como regra principal.

Preferir:

```text
Setor = Suprimentos
```

e aplicar regra de atribuição.

---

# 45. Atribuição de pessoa

Possibilidades:

```text
Manual
Gestor do setor
Usuário padrão
Balanceamento futuro
Quem criou
Responsável do Elemento
```

Essa política deve ser configurável.

---

# 46. Prazo relativo

O Processo pode possuir regras como:

```text
D+1
D+2
3 dias úteis
```

D significa o dia de referência.

Exemplo:

```text
Data da Demanda = 05/10
Etapa = D+2
→ prazo sugerido 07/10
```

Calendário útil/feriados exigem um motor específico.

---

# 47. Dependências

Uma etapa pode depender de outra.

Exemplo:

```text
Conferir projetos
    ↓
Levantar quantitativos
    ↓
Solicitar cotações
```

---

# 48. Dependência não precisa impedir criação

As Tarefas podem ser criadas todas de uma vez, mas com dependências.

Exemplo:

```text
Tarefa B.depends_on = Tarefa A
```

---

# 49. Disponibilidade da Tarefa

Regra configurável:

```text
Criar todas
```

mas:

```text
Tarefa B = aguardando dependência
```

até A ser concluída.

---

# 50. Etapas paralelas

O Processo precisa permitir futuramente:

```text
         ┌─ Cotação elétrica
Entrada ─┼─ Cotação hidráulica
         └─ Cotação mecânica
```

A estrutura atual é essencialmente linear.

Paralelismo é uma evolução.

---

# 51. Etapa não é obrigatoriamente uma Tarefa única

Em alguns casos:

```text
ProcessStep
Cotação
```

pode gerar:

```text
Cotação fornecedor A
Cotação fornecedor B
Cotação fornecedor C
```

Portanto, arquiteturalmente, manter relação:

```text
ProcessStep 1 → N Subelementos
```

quando necessário.

---

# 52. Subelemento manual em Processo

Mesmo que o Processo gere Tarefas, o usuário autorizado pode precisar criar:

```text
Tarefa adicional
```

Exemplo:

```text
Revisar incompatibilidade encontrada
```

---

# 53. Origem do Subelemento

Guardar:

```text
origin = PROCESS | MANUAL | AUTOMATION
```

e, se houver:

```text
process_step_id
```

---

# 54. Vantagem

Permite distinguir:

```text
Tarefa prevista pelo Processo
```

de:

```text
Tarefa criada durante execução
```

Isso gera informação valiosa sobre retrabalho e exceções.

---

# 55. Não transformar origem em avaliação de pessoa

Tarefas extras podem indicar:

- projeto incompleto;
- mudança do cliente;
- risco;
- oportunidade;
- falha de processo.

Não concluir automaticamente que houve improdutividade.

---

# 56. Output do Processo

O Processo deve definir:

```text
qual resultado final é esperado
```

Exemplo:

```text
Proposta comercial validada e enviada ao cliente.
```

---

# 57. Evidência

O Processo atual já prevê tipo de evidência como:

```text
Arquivo
Link
Checklist
Confirmação
```

A execução deve vincular a evidência ao Elemento.

---

# 58. Critérios de aceite

Critérios definem:

```text
como saber que a entrega está aceitável
```

Exemplo:

```text
Escopo revisado
Valores conferidos
Inclusões/exclusões revisadas
Condição de pagamento validada
Arquivo salvo no local correto
```

---

# 59. Critérios pertencem ao Elemento

A definição está no Processo.

O cumprimento pertence à execução.

```text
ProcessCriterion
→ ActivityCriterionCheck
```

---

# 60. Conclusão do Elemento

Um Elemento vinculado a Processo pode exigir:

```text
todos os critérios obrigatórios atendidos
```

antes de conclusão.

---

# 61. Subelementos pendentes

Regra configurável:

```text
Não permitir concluir Elemento com Subelementos obrigatórios abertos.
```

---

# 62. Subelementos opcionais

Alguns podem ser:

```text
opcionais
```

Sua ausência não bloqueia conclusão.

---

# 63. Regra de conclusão

Exemplo:

```text
Pode concluir Demanda se:

- inputs obrigatórios recebidos;
- tarefas obrigatórias concluídas;
- critérios obrigatórios atendidos;
- output/evidência registrado.
```

---

# 64. Progresso

O Elemento pode exibir progresso derivado dos Subelementos.

Exemplo:

```text
7 de 10 concluídas
70%
```

---

# 65. Progresso não deve alterar Status automaticamente sem regra

Ter:

```text
100% tarefas concluídas
```

não significa necessariamente:

```text
Demanda concluída
```

Pode faltar:

- aceite;
- envio;
- evidência;
- aprovação.

---

# 66. Rollup

Rollup significa agregação de dados dos registros filhos.

A LPS deve prever agregações.

Exemplos:

```text
CONTAR(Tarefas)
CONTAR_CONCLUÍDAS(Tarefas)
MÍNIMO(Tarefas.Prazo)
MÁXIMO(Tarefas.Prazo)
SOMA(Tarefas.Horas)
```

---

# 67. Exemplos gerenciais

No Elemento:

```text
Tarefas abertas: 4
Tarefas atrasadas: 2
Próximo prazo: 08/10
Última conclusão: 05/10
```

---

# 68. Fórmula × Rollup

Fórmula trabalha com campos do próprio registro.

Exemplo:

```text
Margem = (Venda - Custo) / Venda
```

Rollup trabalha com registros relacionados.

Exemplo:

```text
Tarefas abertas = COUNT(Subitems where Status != Concluída)
```

São conceitos diferentes.

---

# 69. Fluxo completo de aplicação de Processo

Exemplo:

```text
1. Usuário cria Demanda
2. Escolhe Processo "Elaborar orçamento"
3. Sistema fixa ProcessVersion publicada
4. Inputs obrigatórios são apresentados
5. Usuário preenche contexto
6. Sistema cria Elemento
7. Etapas geram Subelementos/Tarefas
8. Tarefas recebem setor/prazo/regras padrão
9. Execução acontece
10. Inputs adicionais chegam
11. Critérios são verificados
12. Evidência/output é registrado
13. Elemento é concluído
```

---

# 70. Criação rápida

O usuário pode criar rapidamente:

```text
Título
```

e escolher o Processo depois, se a regra do Quadro permitir.

---

# 71. Aplicar Processo depois

Ação:

```text
Aplicar processo
```

Só permitida se:

- Elemento não possuir outro Processo incompatível;
- usuário possuir permissão;
- versão estiver publicada;
- conflitos de colunas forem validados.

---

# 72. Trocar Processo

Troca de Processo durante execução é operação de alto impacto.

Não tratar como dropdown comum.

Exigir:

- revisão;
- impacto nas Tarefas;
- critérios;
- inputs;
- histórico;
- confirmação.

---

# 73. Remover Processo

Não remover Processo de Elemento em execução silenciosamente.

Se permitido:

- manter histórico da versão utilizada;
- não apagar Tarefas;
- auditar motivo.

---

# 74. Processo e schema de Subelemento

O Processo pode dizer quais colunas do schema de Subelemento são relevantes.

Exemplo:

```text
Etapa "Cotação"

Campos principais:
- Responsável
- Prazo
- Fornecedor
- Status
```

Mas não criar um schema novo para cada execução.

---

# 75. Campos específicos de Processo

Se um Processo realmente precisar de um campo inexistente:

```text
+ Adicionar coluna ao Quadro
```

Essa mudança é estrutural no Quadro.

Deve ser explícita.

---

# 76. Template de Elemento

O Processo pode definir:

```text
campos recomendados
valores padrão
campos obrigatórios
```

sem duplicar os tipos de coluna.

---

# 77. Template de Subelemento

Cada ProcessStep pode definir:

```text
Título sugerido
Setor
Prioridade
Prazo relativo
Campos obrigatórios
Dependência
Critério de conclusão
```

---

# 78. Processo não controla layout global

O Processo não deve decidir:

```text
largura da coluna
posição da coluna
cor da view
zoom
```

Isso pertence à Visualização/Quadro.

---

# 79. Processo pode sugerir visualização

Futuro:

```text
Ao aplicar este Processo:
sugerir Kanban "Fluxo de orçamento"
```

Mas não é requisito do núcleo.

---

# 80. Grupo

Grupo é organização visual dentro do Quadro.

Não confundir:

```text
Grupo
```

com:

```text
Processo
```

Grupo pode representar:

```text
Em aberto
Outubro
Cliente A
Obra X
```

Processo define método.

---

# 81. Status

Não confundir:

```text
Status do Elemento
Status do Subelemento
Etapa do Processo
```

São conceitos relacionados, mas diferentes.

---

# 82. Etapa do Processo × Status da Tarefa

ProcessStep:

```text
o que deve ser feito
```

Status da Tarefa:

```text
qual o estado daquela execução
```

Exemplo:

```text
ProcessStep = Solicitar cotações
Task.status = Em execução
```

---

# 83. Processo × Kanban

O Kanban não precisa refletir literalmente ProcessStep.

Pode agrupar por:

```text
Status
Setor
Responsável
Prioridade
```

Processo é estrutura de execução.

Kanban é visualização.

---

# 84. Processo × Calendário

O Calendário pode usar:

```text
prazo dos Subelementos
```

gerados pelo Processo.

Não criar calendário próprio do Processo.

---

# 85. Processo × Tabela

Na Tabela, expandir o Elemento mostra os Subelementos derivados ou manuais.

Pode haver indicador:

```text
4/7 tarefas
```

---

# 86. Permissões

A autorização deve respeitar o motor atual:

```text
SUJEITO + AÇÃO + ESCOPO + ORIGEM
```

---

# 87. Ver Elemento não significa editar Subelemento

Permissões podem diferir.

Exemplo:

```text
Gestor:
ver Demanda
editar Demanda
ver Tarefas

Executor:
ver Demanda
editar apenas Tarefas do seu escopo
```

---

# 88. Criar Subelemento

Exigir ação correspondente.

Exemplo:

```text
tarefa.criar
```

no caso de Tarefas.

---

# 89. Processo

Aplicar Processo deve possuir ação própria.

A documentação atual já prevê:

```text
processo.aplicar
```

mas a implementação ainda precisa ser conectada.

---

# 90. Auditoria

Registrar:

- Processo aplicado;
- versão;
- Tarefas geradas;
- Subelemento manual criado;
- mudança de pai;
- alteração de campos;
- conclusão;
- critérios;
- evidências;
- migração de versão.

---

# 91. Histórico do Elemento

O drawer do Elemento deve mostrar uma linha do tempo integrada.

Exemplo:

```text
02/10 Demanda criada
02/10 Processo "Elaborar orçamento v3" aplicado
02/10 5 tarefas geradas
03/10 Projeto recebido
04/10 Tarefa "Conferir projetos" concluída
...
```

---

# 92. Histórico do Subelemento

Cada filho mantém histórico próprio.

Exemplo:

```text
Responsável alterado
Prazo negociado
Bloqueado
Desbloqueado
Concluído
```

---

# 93. Notificações

Notificar com base em eventos de negócio.

Exemplo:

- Tarefa atribuída;
- prazo alterado;
- bloqueio;
- conclusão;
- aprovação necessária.

Não notificar porque o card foi expandido.

---

# 94. Multi-organização

Processo, Elemento e Subelemento precisam pertencer à mesma organização.

Não permitir:

```text
Processo de Organização A
→ Elemento da Organização B
```

---

# 95. Relações de escopo

O Subelemento herda parte do contexto do pai.

Exemplo:

```text
Organização
Cliente
Obra
Centro de custo
```

mas pode possuir:

```text
Setor operacional próprio
Responsável próprio
```

---

# 96. Herança de contexto

Diferenciar:

```text
contexto herdado
```

de:

```text
valor copiado
```

Preferir referência ao contexto do pai quando o dado é estrutural.

---

# 97. Cliente e Obra

Uma Tarefa vinculada à Demanda não precisa duplicar Cliente e Obra se essas informações puderem ser obtidas do pai.

Isso reduz inconsistência.

---

# 98. Campos sobrescrevíveis

Se houver necessidade real:

```text
Tarefa possui Obra diferente do pai
```

a regra deve ser explícita.

Não permitir divergência silenciosa.

---

# 99. Item principal e resultado

Elemento deve representar um resultado relevante.

Exemplo bom:

```text
Elaborar orçamento Arena Center Norte
```

Exemplo ruim:

```text
Abrir e-mail
```

O segundo é melhor como Tarefa.

---

# 100. Critério para decidir Elemento ou Subelemento

Pergunta:

> Isso precisa ser acompanhado independentemente como entrega principal?

Se sim:

```text
Elemento
```

Se é uma parte da entrega:

```text
Subelemento
```

---

# 101. Outra pergunta

> Esse registro continua fazendo sentido sem o pai?

Se não:

```text
Subelemento
```

---

# 102. Não transformar tudo em Tarefa

Evitar decomposição excessiva.

Exemplo:

```text
Abrir arquivo
Ler página
Enviar mensagem
```

Isso aumenta microgerenciamento.

---

# 103. Subelemento deve representar unidade real de trabalho

Exemplo:

```text
Levantar quantitativos
Solicitar cotação
Revisar orçamento
```

São entregas operacionais verificáveis.

---

# 104. Processo deve reduzir necessidade de cobrança

Se o Processo gera as Tarefas corretas, responsáveis e prazos ficam visíveis.

O gestor não precisa perguntar:

```text
"Em que pé está?"
```

---

# 105. Foco em macrogestão

Elemento:

```text
visão gerencial
```

Subelementos:

```text
execução operacional
```

Processo:

```text
padronização
```

Essa divisão ajuda a evitar microgerenciamento.

---

# 106. Exemplo — Orçamento

```text
PROCESSO
Elaborar orçamento
```

Inputs:

```text
Projetos
Escopo
Prazo do cliente
Cliente
Obra
```

Etapas:

```text
1. Conferir documentação
2. Levantar quantitativos
3. Solicitar cotações
4. Compor orçamento
5. Revisar
6. Enviar
```

Output:

```text
Proposta comercial enviada
```

Critérios:

```text
Escopo revisado
Premissas registradas
Valores validados
Exclusões registradas
```

---

# 107. Execução — Orçamento

```text
ELEMENTO
Arena Center Norte — Orçamento
```

Colunas:

```text
Cliente: Center Norte
Obra: Arena Center Norte
Responsável: Ryan
Prazo: 15/10
Status: Em andamento
Valor: R$ 2.500.000
```

---

# 108. Subelementos — Orçamento

```text
TAREFAS

Conferir projetos
Responsável: Jennifer
Status: Concluída

Levantar quantitativos
Responsável: Ryan
Status: Em execução

Solicitar cotações
Responsável: Luan
Status: A fazer

Revisar proposta
Responsável: Paulo
Status: A fazer
```

---

# 109. Exemplo — Compra

Processo:

```text
Realizar compra
```

Elemento:

```text
Pedido de compra — Cabos Arena
```

Subelementos:

```text
Validar especificação
Solicitar três cotações
Comparar propostas
Aprovar compra
Emitir pedido
Acompanhar entrega
```

---

# 110. Exemplo — Contrato

Elemento:

```text
Contrato GEHAKA
```

Subelementos podem ser:

```text
Aditivo 01
Aditivo 02
Aditivo 03
```

Neste caso, os filhos não precisam ser Tarefas.

Isso reforça que o motor deve ser genérico.

---

# 111. Exemplo — Obra

Elemento:

```text
Entrega de documentação elétrica
```

Subelementos:

```text
As built
ART
Laudo
Manual
Certificados
```

ART significa **Anotação de Responsabilidade Técnica**.

---

# 112. Modelagem proposta

Conceitualmente:

```text
Board
├── element_schema
├── subitem_schema
└── views

BoardItem
├── board
├── parent = null
└── values

BoardSubitem
├── board
├── parent_item
├── origin
├── process_step
└── values
```

---

# 113. Alternativa de modelagem

Também é possível usar uma única tabela:

```text
BoardItem
├── parent_id nullable
├── level
└── values
```

---

# 114. Recomendação

Preferir modelo que preserve explicitamente:

- Elemento;
- Subelemento;
- schema de cada nível.

Mesmo que use uma única tabela física.

A regra de domínio deve permanecer clara.

---

# 115. Processo proposto

```text
Process
└── ProcessVersion
    ├── Inputs
    ├── Steps
    ├── Output
    └── Criteria
```

---

# 116. Ligação proposta

```text
ProcessVersion
      │
      ▼
BoardItem (Elemento)
      │
      ├── ProcessInputValues
      ├── CriterionChecks
      │
      └── BoardSubitems
           └── source_step
```

---

# 117. Compatibilidade com models atuais

Durante migração:

```text
BoardItem(Demanda)
↔ Activity
```

```text
BoardSubitem(Tarefa)
↔ Task
```

Não criar dados duplicados sem estratégia de sincronização.

---

# 118. Estratégia de transição

Fase inicial:

```text
Activity continua fonte de verdade da Demanda
Task continua fonte de verdade da Tarefa
```

A camada de Boards fornece:

- schemas;
- visualizações;
- colunas customizadas.

---

# 119. Aplicação de Processo

A primeira integração real deve fazer:

```text
Activity.process_version = versão publicada
```

e gerar Tarefas reais via:

```text
TaskService.create_task
```

Não inserir diretamente no banco ignorando Service.

---

# 120. Services

Manter arquitetura:

```text
URL
→ View fina
→ Service
→ Model
```

A aplicação de Processo deve ser um Service transacional.

---

# 121. Transação

Aplicar Processo deve ser atômico.

Atômico significa:

> ou todas as alterações são concluídas, ou nenhuma é gravada.

Se falhar ao gerar a Tarefa 4:

```text
não deixar apenas 3 de 5 criadas
```

sem tratamento explícito.

---

# 122. Idempotência

Aplicar a mesma versão duas vezes por acidente não pode duplicar todas as Tarefas.

Idempotência significa que repetir a mesma operação não gera efeito duplicado indevido.

---

# 123. Identificação de geração

Guardar vínculo:

```text
process_application_id
```

ou chave equivalente.

---

# 124. Processo republicado

Nova versão afeta somente novas aplicações por padrão.

---

# 125. Mudança estrutural do Quadro

Se uma nova versão exige uma coluna que não existe:

```text
Processo requer "Fornecedor homologado"
```

a publicação deve alertar:

```text
Coluna necessária não existe no Quadro.
```

---

# 126. Validação na publicação

Antes de publicar ProcessVersion:

- output definido;
- ao menos uma etapa;
- referências de coluna válidas;
- setores válidos;
- campos obrigatórios existentes;
- dependências sem ciclos;
- templates de Subelemento válidos.

---

# 127. Ciclo em etapas

Bloquear:

```text
A depende de B
B depende de A
```

---

# 128. Alteração de coluna usada em Processo

Se uma coluna é usada por versão publicada:

- renomear é permitido;
- excluir exige análise;
- alterar tipo pode ser bloqueado.

---

# 129. Renomear coluna

Seguro porque Processo referencia ID.

---

# 130. Alterar tipo

Exemplo:

```text
Prazo: Data
```

não pode virar:

```text
Arquivo
```

se versões publicadas dependem do tipo Data.

---

# 131. Processo como padrão, não prisão

Permitir execução real lidar com exceções.

Exemplo:

```text
Cliente pediu revisão adicional.
```

Criar Tarefa manual.

O histórico registra a exceção.

---

# 132. Aprendizado do Processo

Depois, a LPS pode mostrar:

```text
Em 68% das execuções deste Processo,
foi criada manualmente uma tarefa "Revisar projeto".
```

Isso pode indicar que ela deveria virar etapa padrão.

---

# 133. Inteligência futura

Exemplo:

```text
Sugestão:
Adicionar "Revisar projeto" ao Processo v5?
```

Essa é uma aplicação de Inteligência Artificial baseada em histórico.

---

# 134. Processo e melhoria contínua

Fluxo:

```text
Executar
→ observar exceções
→ aprender
→ atualizar Processo
→ publicar nova versão
```

---

# 135. Processo e capital intelectual

Quando uma boa sequência de trabalho é incorporada ao Processo, o conhecimento deixa de depender apenas de uma pessoa.

Exemplo:

```text
Jennifer executa uma atividade de forma eficiente
→ método é entendido
→ Processo é melhorado
→ próximas Demandas recebem o padrão
```

Sem transformar desempenho individual em ranking automático.

---

# 136. Indicadores úteis

Por Processo:

- quantidade de Elementos executados;
- prazo médio;
- taxa de conclusão;
- etapas que mais atrasam;
- etapas extras manuais;
- bloqueios recorrentes;
- setores com fila;
- critérios frequentemente não atendidos.

---

# 137. Indicadores de Elemento

- Subelementos totais;
- concluídos;
- atrasados;
- bloqueados;
- próximo prazo;
- percentual de critérios atendidos.

---

# 138. Evitar métrica enganosa

Não usar:

```text
quantidade de Tarefas concluídas
```

isoladamente para dizer quem é mais produtivo.

Uma Tarefa pode levar 5 minutos ou 5 dias.

---

# 139. Visualização por Processo

Futuro:

```text
Filtrar:
Processo = Elaborar orçamento v4
```

Isso permite comparar execuções do mesmo método.

---

# 140. Visualização dos Subelementos

Filtros devem permitir:

```text
Mostrar Tarefas de Demandas
onde Cliente = X
```

sem duplicar Cliente na Tarefa.

---

# 141. Contexto do pai em filtros

O motor deve compreender campos herdados.

Exemplo:

```text
Tarefa
→ parent.Cliente
```

---

# 142. Busca

Buscar:

```text
Arena Center Norte
```

pode encontrar:

- Elemento;
- Subelementos;
- contexto relacionado.

A UI deve indicar o nível do resultado.

---

# 143. Drawer do Elemento

Deve possuir seção:

```text
Tarefas  4/7
```

com:

- lista;
- adicionar;
- abrir;
- filtrar.

---

# 144. Drawer do Subelemento

Deve possuir:

```text
Demanda vinculada
Arena Center Norte
```

clicável.

---

# 145. Colunas do pai no card filho

Por padrão, não repetir.

Mas uma visualização de Tarefas pode mostrar:

```text
Demanda vinculada
Cliente
Obra
```

como campos derivados do pai.

---

# 146. Campos derivados

Marcar como:

```text
Somente leitura
```

se vierem do pai.

---

# 147. Agrupamento de Subelementos

Pode agrupar Tarefas por:

```text
Status
Responsável
Setor
Prioridade
Demanda pai
Cliente do pai
Obra do pai
```

---

# 148. Processo e Grupo visual

Um Processo pode gerar Tarefas em diferentes setores.

O Kanban pode agrupar por:

```text
Setor
```

independentemente da ordem do Processo.

---

# 149. Ordem do Processo

Guardar ordem da etapa separadamente da ordem visual.

---

# 150. Reordenar Kanban não muda Processo

Se o usuário muda a ordem visual das colunas:

```text
A fazer | Bloqueada | Em execução | Concluída
```

não altera a sequência do Processo.

---

# 151. Concluir Subelemento

Conclusão deve obedecer regra da Tarefa e, se derivada de Processo, validar critério específico da etapa quando houver.

---

# 152. Reabrir Subelemento

Se permitido:

- auditar;
- recalcular progresso do pai;
- atualizar agregações.

---

# 153. Cancelar Subelemento

Não considerar automaticamente como concluído.

O Processo precisa decidir se uma etapa cancelada satisfaz a execução.

---

# 154. Etapa dispensada

É diferente de cancelada.

Futuro status de execução:

```text
Dispensada
```

com motivo.

---

# 155. Processo condicional

Futuro:

```text
Se Valor > R$ 1.000.000
→ adicionar etapa Aprovação da Diretoria
```

Não faz parte da primeira integração obrigatória.

---

# 156. Processo com caminhos

Futuro:

```text
Se projeto completo
→ Levantamento

Se incompleto
→ Solicitar complementação
```

Exige motor de condições.

---

# 157. Primeira versão do Processo integrado

Manter simples:

```text
fluxo linear
etapas
setor
ordem
dependência
criação de Tarefas
inputs
output
critérios
```

---

# 158. O que não fazer agora

Não implementar simultaneamente:

- BPMN completo;
- fluxos recursivos;
- decisões complexas;
- dezenas de gatilhos;
- subprocessos ilimitados;
- múltiplos níveis de Subelementos.

BPMN significa **Business Process Model and Notation**, uma notação formal para modelagem de processos.

---

# 159. Processo × Automação

Processo:

```text
define método
```

Automação:

```text
reage a evento
```

Exemplo:

Processo:

```text
Etapa = Revisar proposta
```

Automação:

```text
Quando tarefa "Revisar proposta" concluir
→ notificar responsável da Demanda
```

---

# 160. Processo × Fórmula

Fórmula:

```text
calcula
```

Processo:

```text
organiza execução
```

---

# 161. Processo × Rollup

Rollup permite ao Elemento enxergar execução dos Subelementos.

Exemplo:

```text
Tarefas atrasadas = 2
```

---

# 162. Processo × Dashboard

Dashboard pode consumir:

- Elementos;
- Subelementos;
- Processos;
- agregações.

Não é responsabilidade do Processo desenhar o Dashboard.

---

# 163. Regra central de produto

> O Processo define o padrão; o Elemento representa a entrega; o Subelemento representa a execução.

---

# 164. Outra forma de enxergar

```text
PROCESSO
Como fazemos?

ELEMENTO
O que precisamos entregar?

SUBELEMENTO
O que precisa ser feito para entregar?
```

---

# 165. Papel gerencial

Gestor olha principalmente:

```text
Elementos
```

e exceções dos Subelementos.

---

# 166. Papel operacional

Executor trabalha principalmente:

```text
Subelementos
```

com contexto do Elemento pai.

---

# 167. Gestão por exceção

Em vez de acompanhar toda Tarefa:

```text
mostrar ao gestor:
- atrasadas;
- bloqueadas;
- sem responsável;
- risco de prazo;
- excesso de carga.
```

---

# 168. Processo como prevenção de microgerenciamento

Um Processo bem definido reduz a necessidade de perguntar:

```text
Você já fez?
Quem está fazendo?
Qual é o próximo passo?
Onde está o arquivo?
```

Essas respostas ficam no fluxo.

---

# 169. Regra para card pai

Card de Elemento deve mostrar indicador de filhos.

Exemplo:

```text
3 tarefas
```

---

# 170. Estado expandido

Ao expandir:

- não sair do Kanban;
- filhos aparecem abaixo;
- edição contextual;
- `+ Adicionar tarefa`.

---

# 171. Persistência da expansão

Pode ser sessão/local.

Não precisa ser propriedade de negócio do Elemento.

---

# 172. Muitos Subelementos no card

Não renderizar 50 filhos indiscriminadamente.

Exemplo:

```text
Mostrar 5
+ 17 tarefas
```

ou usar scroll interno controlado.

---

# 173. Performance

Carregar filhos sob demanda quando o card for expandido.

Evitar carregar todos os Subelementos de todas as Demandas no primeiro render.

---

# 174. Contador

O contador deve refletir quantidade de filhos visíveis conforme permissão.

Não revelar:

```text
10 tarefas
```

se o usuário só pode acessar 2 e a quantidade total for sensível.

---

# 175. Criação contextual no Kanban

Clicar:

```text
+ Adicionar tarefa
```

já preenche:

```text
parent = Demanda atual
```

---

# 176. Criação contextual na Tabela

Mesma regra.

---

# 177. Criação no drawer

Dentro da Demanda:

```text
+ Nova tarefa
```

cria vinculada.

---

# 178. Processo e criação manual

Se uma Tarefa manual é criada:

```text
origin = MANUAL
```

Não tentar vinculá-la artificialmente a uma ProcessStep.

---

# 179. Vincular manual a etapa

Pode existir ação futura:

```text
Vincular à etapa
```

mas deve ser explícita.

---

# 180. Segurança na aplicação do Processo

Antes de gerar filhos, verificar:

- organização;
- permissão de aplicar Processo;
- permissão para criar Subelementos nos setores envolvidos;
- validade da versão.

---

# 181. Falha de permissão em uma etapa

Não gerar Processo parcialmente sem explicação.

Exemplo:

```text
Você não possui permissão para criar Tarefa no setor Suprimentos.
```

---

# 182. Aplicação por gestor

Um perfil autorizado pode aplicar Processo com etapas em vários setores.

A autorização deve ser desenhada deliberadamente.

---

# 183. Critérios de aceite — Elemento

## ELS-001

Elemento possui ID próprio.

## ELS-002

Elemento utiliza schema próprio de colunas.

## ELS-003

Pode existir sem filhos.

## ELS-004

Pode ser visualizado em Tabela, Kanban e Calendário.

## ELS-005

Mudanças refletem nas demais visualizações.

---

# 184. Critérios de aceite — Subelemento

## SUB-001

Subelemento possui ID próprio.

## SUB-002

Pertence exatamente a um pai.

## SUB-003

Possui schema de colunas independente do pai.

## SUB-004

Pode ter Status, Pessoa, Data e demais campos próprios.

## SUB-005

Pode ser criado sem sair da visualização atual.

## SUB-006

Pode ser expandido dentro da Tabela.

## SUB-007

Pode ser expandido abaixo do card pai no Kanban.

---

# 185. Critérios de aceite — Kanban

## KSB-001

Card do pai mostra contador de Subelementos.

## KSB-002

Clicar expande filhos sem mudar de tela.

## KSB-003

Status do filho não move o card pai.

## KSB-004

Kanban próprio de Subelementos pode usar Status do filho.

## KSB-005

Adicionar Subelemento contextualiza o pai automaticamente.

---

# 186. Critérios de aceite — Processo

## PRO-001

Apenas versão publicada pode ser aplicada.

## PRO-002

Elemento guarda versão aplicada.

## PRO-003

Nova versão não altera Elementos em execução automaticamente.

## PRO-004

Etapas podem gerar Subelementos.

## PRO-005

Subelementos gerados mantêm referência à etapa de origem.

## PRO-006

Aplicação não pode duplicar filhos ao ser repetida acidentalmente.

## PRO-007

Aplicação deve ser atômica.

---

# 187. Critérios de aceite — Inputs

## INP-001

Inputs obrigatórios são identificados.

## INP-002

Quando possível, Input referencia coluna existente.

## INP-003

Renomear a coluna não quebra o Processo.

## INP-004

Excluir coluna usada por versão publicada exige tratamento.

---

# 188. Critérios de aceite — Output

## OUT-001

Processo possui descrição do resultado esperado.

## OUT-002

Execução pode registrar evidência.

## OUT-003

Conclusão pode exigir evidência quando configurado.

---

# 189. Critérios de aceite — Critérios

## CRT-001

Critério pertence à versão do Processo.

## CRT-002

Verificação pertence ao Elemento real.

## CRT-003

Critério obrigatório pode bloquear conclusão.

## CRT-004

Nova versão não reescreve checks históricos.

---

# 190. Critérios de aceite — Auditoria

## AUD-001

Aplicação de Processo é auditada.

## AUD-002

Versão aplicada é registrada.

## AUD-003

Criação automática de filhos é rastreável.

## AUD-004

Filho manual possui origem identificável.

## AUD-005

Migração de Processo exige histórico.

---

# 191. Critérios de aceite — Gestão

## GST-001

Elemento mostra quantidade de filhos.

## GST-002

Pode exibir progresso agregado.

## GST-003

Pode exibir quantidade de atrasados/bloqueados.

## GST-004

Indicadores não alteram Status automaticamente sem regra.

---

# 192. Implementação em fases

## Fase 1 — Relação Elemento/Subelemento

- schema de Elemento;
- schema de Subelemento;
- expandir/recolher;
- criação contextual;
- contador;
- colunas independentes.

---

## Fase 2 — Kanban

- filhos expansíveis;
- card configurável do filho;
- Kanban próprio de Subelementos.

---

## Fase 3 — Processo aplicado

- selecionar versão;
- gravar `process_version`;
- gerar Tarefas;
- vínculo Task ↔ ProcessStep;
- origem manual/processo.

---

## Fase 4 — Inputs e critérios

- mapear inputs;
- registrar valores;
- critérios de aceite;
- validação de conclusão.

---

## Fase 5 — Rollups

- total;
- concluídas;
- atrasadas;
- bloqueadas;
- próximo prazo.

---

## Fase 6 — Aprendizado

- exceções recorrentes;
- sugestões de melhoria do Processo;
- indicadores por versão.

---

# 193. Decisões arquiteturais obrigatórias

1. Elemento e Subelemento são registros diferentes.
2. Subelemento possui schema independente.
3. Um nível de filhos na primeira versão.
4. Processo é blueprint, não execução.
5. Processo aplicado deve fixar uma versão.
6. ProcessStep é template; Subelemento é instância.
7. Um Step pode gerar um ou mais filhos quando necessário.
8. Filhos manuais continuam permitidos.
9. Origem do filho deve ser registrada.
10. Processo não deve duplicar os dados do Quadro.
11. Inputs devem mapear para colunas por ID sempre que possível.
12. Mudança de versão não altera execução antiga automaticamente.
13. Kanban do pai e Kanban dos filhos são visualizações distintas.
14. Status do pai e do filho são independentes.
15. Processo deve reduzir microgerenciamento, não aumentar.

---

# 194. Diagrama final

```text
ORGANIZAÇÃO
│
└── QUADRO
    │
    ├── Schema do Elemento
    │
    ├── Schema do Subelemento
    │
    ├── Visualizações
    │   ├── Tabela
    │   ├── Kanban
    │   └── Calendário
    │
    └── ELEMENTO
        │
        ├── Colunas / valores
        ├── Processo aplicado
        │   └── ProcessVersion
        │       ├── Inputs
        │       ├── Steps
        │       ├── Output
        │       └── Critérios
        │
        └── SUBELEMENTOS
            ├── Subelemento A ← ProcessStep
            ├── Subelemento B ← ProcessStep
            └── Subelemento C ← Manual
```

---

# 195. Aplicação específica em Demandas

```text
QUADRO
Demandas
```

```text
ELEMENTO
Demanda
```

```text
SUBELEMENTO
Tarefa
```

```text
PROCESSO
Como aquela Demanda deve ser executada
```

---

# 196. Exemplo resumido

```text
Processo:
Elaborar orçamento v4
```

gera execução:

```text
Demanda:
Arena Center Norte
```

com filhos:

```text
Conferir documentação
Levantar quantitativos
Solicitar cotações
Revisar proposta
Enviar proposta
```

Cada filho possui:

```text
Responsável
Setor
Status
Prazo
Prioridade
```

A Demanda possui:

```text
Cliente
Obra
Solicitante
Responsável
Status
Prazo
Valor
```

---

# 197. Regra de linguagem da interface

O motor interno pode utilizar:

```text
Elemento
Subelemento
```

Mas a interface deve usar a linguagem do domínio.

Exemplo:

```text
Demandas / Tarefas
```

e não:

```text
Elementos / Subelementos
```

se isso for mais natural para o usuário.

Outro Quadro pode usar:

```text
Pedido / Itens
```

---

# 198. Definição final — Elemento

> Elemento é a unidade principal de trabalho ou registro dentro de um Quadro, com identidade, colunas e ciclo de vida próprios.

---

# 199. Definição final — Subelemento

> Subelemento é uma unidade filha pertencente a um Elemento, com identidade e esquema próprios, usada para decompor a entrega principal em partes operacionais ou componentes relacionados.

---

# 200. Definição final — Processo

> Processo é um modelo versionado que define como um determinado tipo de Elemento deve ser executado, incluindo inputs, etapas, output e critérios de aceite.

---

# 201. Relação final

```text
PROCESSO = padrão
ELEMENTO = entrega
SUBELEMENTO = execução
```

Essa divisão deve ser uma das bases centrais da arquitetura da LPS.

Ela permite:

- flexibilidade de Quadro;
- padronização de Processo;
- execução operacional;
- visão gerencial;
- rastreabilidade;
- evolução contínua;
- gestão por exceção;
- menor dependência de microgerenciamento.
