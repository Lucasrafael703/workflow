# LPS — Especificação da Visualização por Kanban

## Status de implementação (03/10/2026)

**Resumo.** O Kanban existe hoje em quatro superfícies, todas lendo os mesmos dados da fonte de verdade (nenhuma guarda cartões próprios): (1) **Kanban dos Quadros dinâmicos** (`/quadros/visoes/<id>/`), o que mais se aproxima desta especificação (cerca de 80% implementado); (2) **Kanban de Demandas** (`/demandas/kanban/`), parcial e com configuração própria; (3) **Kanban de Tarefas** (`/tarefas/kanban/`), somente leitura, com três raias por estado derivado; (4) **Kanban legado de Demandas por setor** (`/demandas/kanban-legado/`), que agrupa por Etapa do setor, tem limite de coluna e gaveta (a rota `/tarefas/kanban-legado/` existe, mas é interceptada pela regra de rotas desativadas de Tarefas e responde "410 Gone"). As seções 1 a 45 abaixo descrevem a intenção; onde o código seguiu outro caminho há uma nota **Divergência**. Itens futuros foram mantidos no texto.

| Requisito / bloco | Status | Onde está no código |
|---|---|---|
| Visualização configurável sobre o mesmo quadro (sem duplicar itens), vários Kanbans por quadro, renomear e excluir | Implementado | `boards/models.py` (`BoardView`), `boards/services.py` (`ViewService`), `boards/views.py` (`ViewCreateView`, `ViewUpdateView`, `ViewDeleteView`), `templates/boards/_board_view_tabs.html`, `static/js/boards.js` (`openViewDialog`) |
| Agrupar por Status ou Lista suspensa, com troca sem recriar a visualização | Implementado | `boards/kanban.py` (`GROUPABLE_TYPES`, `clean_kanban_settings`, `resolve_group_column`), `templates/boards/board_kanban.html` |
| Agrupar por Setor, Prioridade, Pessoa ou Etapa nos Quadros | Não implementado (só colunas de Status e Lista suspensa; Setor e Prioridade funcionam se o quadro tiver uma coluna de Lista suspensa com esse nome) | `boards/kanban.py` (comentário de `GROUPABLE_TYPES`) |
| Raias com contagem, raias vazias, raia "Em branco" (automática, sempre, nunca) e soma de Número/Moeda no cabeçalho | Implementado | `boards/kanban.py` (`build_lanes`, `format_total`), `templates/boards/_kanban_lanes.html` |
| Resumo por média, contagem configurável e densidade do cartão | Não implementado (há contagem fixa e soma opcional) | `boards/kanban.py` (`DEFAULT_SETTINGS`) |
| Renomear e recolorir etiqueta pela raia, editar etiquetas, paleta de 16 cores, definir etiqueta padrão | Implementado | `static/js/boards.js` (`renameLane`, `recolorLane`, `openLabels`), `boards/views.py` (`OptionUpdateView`), `boards/presentation.py` (`COLOR_PALETTE`) |
| Alterar o Status direto no cartão | Implementado (clique abre o editor da célula) | `templates/boards/_kanban_card.html`, `static/js/boards.js` (`openCellEditor`), `boards/views.py` (`CellUpdateView`) |
| Arrastar cartão entre raias (interface otimista, volta se o servidor recusar) | Implementado | `static/js/boards.js` (`moveCard`, evento `drop`), `boards/services.py` (`CellService.set_value`) |
| Regras ricas no arrastar (pedir motivo, destino bloqueado destacado, reordenar dentro da raia) | Não implementado | `static/js/boards.js` (`moveCard` grava só a célula agrupadora) |
| Alternativa ao arrastar ("Mover para") | Implementado nos Quadros; no Kanban de Demandas novo não verificado/ausente | `static/js/boards.js` (`openCardMenu`) |
| Configurar cartões (campos, ordem, nome do campo, pré-visualização, até 12 campos) | Implementado, com setas em vez de arrastar campos; sem capa | `static/js/boards.js` (`openKanbanConfig`), `boards/kanban.py` (`MAX_CARD_FIELDS`, `resolve_card_columns`) |
| Ordenação dos cartões (ordem do quadro, título, criação, qualquer coluna) | Implementado | `boards/kanban.py` (`sort_choice`, `sort_options`), `boards/queries.py` (`kanban_items`) |
| Pesquisa e filtro por Pessoa | Implementado | `boards/queries.py` (`search_filter`, `_filtered_items`), `templates/boards/board_kanban.html` |
| Filtros por valor de coluna (Responsável, Setor, Prazo, Status) | Não implementado (botão "Filtros" desabilitado, "em breve") | `templates/boards/board_kanban.html` |
| Criar item dentro da raia já com o agrupador preenchido | Implementado nos Quadros | `static/js/boards.js` (`addCard`), `boards/views.py` (`ItemCreateView`, parâmetro `initial`) |
| Gaveta lateral com detalhes ao clicar no cartão | Não implementado no Kanban dos Quadros (o clique no título renomeia); existe no Calendário e no Kanban legado | `static/js/boards.js` (gaveta só no bloco `cal`), `activities/kanban.py` (`ActivityKanbanDrawerView`) |
| Permissões no servidor e auditoria | Implementado | `boards/services.py` (`_require`, `_audit`, ações `QUADRO_EDITAR` e `QUADRO_EDITAR_ITEM`), `boards/presentation.py` |
| Autosave das configurações leves | Implementado nos Quadros; no Kanban de Demandas é por botão "Salvar cartões" | `static/js/boards.js` (`updateView`, debounce de 250 ms), `static/js/work-board.js` (`submitCardSettings`) |
| Kanban de Demandas | Parcial / Divergente (raias por Estágio ou Status; cartão com título, responsável, setor, prioridade, prazo e tarefas) | `boards/work_views.py` (`DemandWorkBoardView`), `boards/domain_defaults.py`, `templates/boards/_work_kanban.html`, `static/js/work-board.js` |
| Kanban de Tarefas | Divergente (três raias por estado derivado, somente leitura) | `boards/task_center.py` (`kanban_columns`), `boards/task_center_views.py`, `templates/boards/task_center.html` |
| Kanban legado de Demandas por setor (Etapas do setor, limite informativo de coluna) | Existe, fora desta especificação (a versão de Tarefas está desativada) | `activities/kanban.py`, `activities/kanban_urls.py`, `activities/urls.py` (`demandas/kanban-legado/`), `static/js/kanban.js` |
| Responsividade, performance por raia e acessibilidade | Parcial (rolagem horizontal; sem carga por raia; sem layout móvel dedicado verificado) | `static/css/boards.css`, `boards/views.py` (`kanban_context`) |

## 1. Objetivo

> **Divergência:** "Quadro" na LPS tem duas camadas. Os **Quadros dinâmicos** (app `boards`, `Board`/`BoardView`) são o que esta especificação descreve. Já Demandas e Tarefas têm telas próprias: o Kanban de Demandas lê o `DomainBoard` (configuração de lentes sobre `Activity`) e o Kanban de Tarefas lê itens dos Quadros de cada Demanda. Veja o resumo no início do documento.

A visualização **Kanban** organiza os mesmos itens do Quadro em colunas visuais, normalmente usando um campo categórico como Status, Setor, Prioridade ou Lista suspensa.

A principal referência de experiência é o comportamento observado no Monday: o Kanban não possui dados próprios. Ele lê as colunas do quadro, permite escolher por qual campo agrupar e permite configurar quais informações aparecem nos cartões.

Na LPS, o Kanban deve ser uma **visualização configurável**, e não um módulo independente.

---

## 2. Princípio central

> O Kanban não cria outro conjunto de dados. Ele reorganiza os mesmos itens do quadro.

Exemplo do Quadro:

```text
Demanda                 | Status              | Setor
Validar Go/No-Go        | Trabalhando Nisso   | Comercial
Conferir documentação   | Done                | Suprimentos
```

Kanban agrupado por `Status`:

```text
Trabalhando Nisso
- Validar Go/No-Go

Done
- Conferir documentação
```

Kanban agrupado por `Setor`:

```text
Comercial
- Validar Go/No-Go

Suprimentos
- Conferir documentação
```

Nenhum item foi duplicado.

---

# 3. Relação entre Quadro e Kanban

O Quadro controla os campos.

O Kanban decide:

- por qual campo agrupar;
- quais campos mostrar no cartão;
- em qual ordem mostrar;
- filtros;
- ordenação;
- campos visíveis;
- opções visuais próprias da visualização.

---

# 4. Criação da visualização Kanban

> **Divergência:** a janela "Adicionar visualização" (botão `+` nas abas, visível só a quem tem `quadro.editar`) lista Tabela (já existe: é o "Quadro principal"), Kanban, Calendário, Linha do tempo e Dashboard. **Linha do tempo e Dashboard aparecem desabilitados ("Em breve")**. O nome sugerido é "Kanban"; repetido, vira "Kanban 2", "Kanban 3" etc. Todo quadro já nasce com um Kanban (`ViewService.create_default_kanban`) e o modelo "Orçamentos" traz um Kanban por Status com soma do Valor.

A partir das abas:

```text
[ Quadro principal ] [ Calendário ] [ + ]
```

Ao clicar em `+`:

```text
Adicionar visualização

Tabela
Kanban
Calendário
Linha do tempo
Dashboard
```

Escolheu Kanban:

```text
Nome da visualização: Kanban Comercial
[Criar visualização]
```

---

## 4.1 Regra

Criar uma visualização não deve duplicar itens.

Deve criar apenas uma configuração de visualização vinculada ao quadro.

---

# 5. Estrutura visual

A tela Kanban deve ter:

1. cabeçalho do quadro;
2. abas de visualização;
3. barra de ações;
4. colunas do Kanban;
5. cartões;
6. configurações da visualização;
7. configuração dos cartões.

---

# 6. Barra de ações

> **Divergência:** a barra dos Quadros tem Buscar (campo de texto e botão), filtro **Pessoa**, **Agrupar por**, **Ordenar** e **Configurar cartões**. Agrupar, Ordenar e Configurar só aparecem a quem pode editar o quadro; os demais veem apenas o selo "Agrupado por …". **"Filtros" está desabilitado ("em breve")**. Não há "Mais ações" e o botão de criar fica no rodapé de cada raia ("Adicionar" + título da coluna principal do quadro), não na barra. No Kanban de Demandas a barra é a de filtros da própria tela de Demandas (abas de escopo, busca, Atrasadas, Vencem hoje, Setor, Etapa, Status e Pessoas).

Exemplo:

```text
[Criar demanda] Pesquisar Pessoa Filtro Ordenar Agrupar por: Status Configurar cartões ...
```

Botões principais:

- Criar item;
- Pesquisar;
- Pessoa;
- Filtro;
- Ordenar;
- Agrupar por;
- Configurar cartões;
- Configurações da visualização;
- Mais ações.

---

# 7. Agrupamento

> **Divergência:** nos Quadros só colunas de **Status** e **Lista suspensa** viram raias (`GROUPABLE_TYPES`); Pessoa, Prioridade e Setor como tipos próprios ficam para uma próxima versão. Se o quadro não tem nenhuma dessas colunas, a tela mostra "Escolha por qual coluna agrupar". No Kanban de Demandas o servidor aceita agrupar por `stage`, `condition`, `sector`, `owner` e `urgency` (Tarefas: `stage`, `sector`, `responsavel`, `priority`), mas o painel de configuração só oferece **Estágio** e **Status**.

O agrupamento é a regra que define as colunas do Kanban.

Exemplo:

```text
Agrupar por: Status
```

Opções compatíveis podem incluir:

- Status;
- Lista suspensa;
- Setor;
- Prioridade;
- Pessoa, em algumas visões;
- outros campos categóricos suportados.

---

## 7.1 Exemplo observado

> **Divergência:** o seletor "Agrupar por" dos Quadros lista só as colunas de Status e Lista suspensa do quadro. "Etapa" como agrupamento existe apenas no Kanban de Demandas e no Kanban legado (Etapas do setor).

O usuário escolhe:

```text
Coluna Kanban
[ Status v ]
```

E o seletor pode listar:

```text
Status
Setor
Prioridade
Etapa
```

A LPS deve seguir esse conceito.

---

# 8. Colunas do Kanban

Cada valor da coluna agrupadora se transforma em uma coluna visual.

Exemplo:

Status possui:

```text
Trabalhando Nisso
Stuck
Done
```

Kanban:

```text
[ Trabalhando Nisso ] [ Stuck ] [ Done ]
```

---

## 8.1 Coluna vazia

> **Divergência:** a opção é "Mostrar raias vazias" (`show_empty`, padrão ligado). A raia "Em branco" tem controle próprio (seção 29).

A configuração pode permitir:

```text
Mostrar colunas vazias: Sim/Não
```

Se ligado, `Stuck` aparece mesmo sem cartões.

---

## 8.2 Quantidade

O cabeçalho pode mostrar:

```text
Trabalhando Nisso  12
```

---

## 8.3 Resumo financeiro ou numérico

> **Divergência:** implementado como "Somar valor no cabeçalho da raia" (`sum_column`), aceitando colunas de **Número** ou **Moeda**, formatado como a coluna (símbolo, unidade, casas decimais). A raia sem itens não mostra total.

Se existir uma coluna de valor compatível:

```text
Comercial  8
R$ 4.850.000,00
```

Configuração:

```text
Somar valor por coluna: Sim/Não
```

---

# 9. Renomear uma coluna do Kanban

> **Divergência:** o nome da raia é, de fato, o rótulo da etiqueta (`BoardColumnOption.label`); não há outro cadastro. Renomeia-se com duplo clique no título da raia ou pelo menu da raia ("Renomear etiqueta"), e a raia é redesenhada pelo servidor (`refreshKanban`), refletindo também na tabela. No Kanban de Demandas, as raias herdam o nome da Etapa ou Status do setor (`ActivityStage`/`WorkflowStatus`), que se edita em Configurações.

No comportamento observado, a coluna do Kanban herda o nome da etiqueta do campo usado para agrupamento.

Isso é fundamental.

Se a etiqueta:

```text
Working on it
```

for renomeada inline para:

```text
Trabalhando Nisso
```

A coluna do Kanban deve mudar imediatamente.

Não deve existir outro cadastro do nome da coluna do Kanban.

---

# 10. Alterar a cor da coluna

A cor da coluna deve ser herdada da opção usada para agrupamento.

Exemplo:

```text
StatusOption
Nome: Trabalhando Nisso
Cor: rosa
```

A etiqueta na Tabela fica rosa.

O cabeçalho correspondente do Kanban também pode refletir a cor.

A mudança ocorre sem sair da tela.

---

# 11. Edição inline da etiqueta

> **Divergência:** clicar no Status dentro do cartão abre o editor padrão da célula (lista de etiquetas), com o botão "Editar etiquetas". O cartão dos Quadros tem os campos editáveis no lugar; o título do cartão também (clique ou Enter).

Ao clicar em um Status no cartão, abrir um menu rápido.

Exemplo:

```text
Trabalhando Nisso
Stuck
Done
-----------------
Editar etiquetas
```

O usuário pode selecionar outro Status imediatamente.

---

# 12. Edição de etiquetas

> **Divergência:** o painel "Editar etiquetas" permite renomear, mudar a cor, adicionar, reordenar, excluir e marcar a etiqueta padrão ("Padrão para novos itens"); também há "representa conclusão" (`is_done`), usado pelo Calendário e pela tela de Tarefas. Excluir uma etiqueta envia seus itens para a raia "Em branco".

A ação `Editar etiquetas` abre um painel compacto.

Possibilidades:

- renomear opção;
- mudar cor;
- adicionar etiqueta;
- reordenar;
- definir padrão;
- aplicar.

Exemplo:

```text
[ rosa ] Trabalhando Nisso    ...
[ vermelho ] Stuck            ...
[ verde ] Done                ...
[ cinza ] Etiqueta padrão     ...

+ Nova etiqueta
```

---

# 13. Paleta de cores

> **Divergência:** a paleta oferece 16 cores fixas (`COLOR_PALETTE`); não há seletor de cor livre. A cor é propriedade da etiqueta e vale na tabela, no Kanban e no Calendário. Não existe "filtro" que use as etiquetas ainda (filtros por valor são futuros).

O usuário deve conseguir clicar na cor de uma etiqueta e escolher uma nova em uma paleta.

A ação deve:

- atualizar imediatamente;
- refletir em Tabela;
- refletir em Kanban;
- refletir em filtros;
- refletir em outros componentes que usam a mesma opção.

A cor é propriedade da opção do campo, não do cartão.

---

# 14. Arrastar cartão

> **Divergência:** nos Quadros, arrastar grava a etiqueta da coluna agrupadora pelo mesmo endpoint da célula (`board-cell-update`), então valem as mesmas validações e a mesma auditoria da edição na tabela; soltar na raia "Em branco" limpa o valor (recusado se a coluna for obrigatória) e quem só visualiza não arrasta. **Reordenar cartões dentro da mesma raia não é persistido** (a ordem vem da ordenação escolhida). No Kanban de Demandas, soltar chama `DomainBoardMutationService.set_value`, que executa `ActivityService.set_stage` (ou `set_condition`, `change_owner` etc.) e só permite arrastar quem tem a ação correspondente (`can_move_kanban`).

Drag-and-drop é uma ação central do Kanban.

Exemplo:

```text
Trabalhando Nisso       Done
[ Demanda A ]  --->     [ Demanda A ]
```

Semântica:

Se Kanban está agrupado por `Status`:

```text
mover cartão → altera Status
```

Se agrupado por `Setor`:

```text
mover cartão → solicita/efetua alteração de Setor
```

---

## 14.1 Regra crítica

> **Divergência:** a regra "arrastar é gesto, a regra continua no serviço" vale no Kanban de Demandas e no legado. Nos Quadros não há regra de negócio além das validações da célula (obrigatória, etiqueta ativa da mesma coluna, permissão `quadro.editar_item`).

Nem todo agrupamento pode permitir alteração por drag automaticamente.

Exemplos:

### Status

Normalmente pode alterar diretamente, respeitando regras de negócio.

### Setor

Pode exigir serviço específico, autorização, notificação, atualização de fila ou confirmação.

### Responsável

Pode exigir regra de atribuição.

Portanto:

> Arrastar é gesto visual. A regra de negócio continua sendo executada pelo serviço correspondente.

---

# 15. Feedback durante drag

> **Divergência:** hoje a raia de destino recebe apenas a marcação `is-drop-target`; não há mensagem "Solte o item aqui…" nem indicação de destino bloqueado. Se o servidor recusar, o cartão volta à posição anterior e aparece uma mensagem (toast).

Ao arrastar:

- cartão deve ganhar elevação;
- destino deve ser destacado;
- coluna deve indicar que aceita o item;
- se destino não for permitido, indicar bloqueio;
- após soltar, atualizar imediatamente;
- se o servidor recusar, devolver à posição anterior.

Exemplo:

```text
Solte o item aqui
para mover para Suprimentos
```

---

# 16. Configuração da visualização

> **Divergência:** a configuração é uma **janela modal larga "Configurar cartões"**, e não um drawer. Ela reúne: mostrar raias vazias, raia "Em branco", somar valor, mostrar o nome de cada campo e a lista de campos do cartão com pré-visualização. "Agrupar por" e "Ordenar" ficam na barra.

Botão:

```text
Configurações
```

ou ícone de engrenagem.

Drawer recomendado:

```text
Configurações da visualização

Kanban
Agrupar por: Status
Mostrar colunas vazias: [on]
Ordenar cartões por: Prazo
Somar valor por coluna: [on]
```

---

# 17. Configurações recomendadas do Kanban

## Agrupar por

Seleciona a coluna responsável pelas lanes.

## Mostrar colunas vazias

Exibe opções sem itens.

## Ordenar cartões por

Exemplos:

- ordem manual;
- prazo;
- prioridade;
- data de criação;
- título;
- valor.

## Mostrar resumo por coluna

> **Divergência:** só a **soma** (e a contagem fixa no cabeçalho). Média e demais resumos não foram implementados.

Exemplos:

- soma;
- contagem;
- média.

## Densidade

> **Divergência:** não implementado (continua como evolução futura).

Possível evolução:

- compacta;
- normal;
- detalhada.

---

# 18. Personalização do cartão

> **Divergência:** o cartão aceita até **12 campos** (`MAX_CARD_FIELDS`). Sem escolha, mostra os **4 primeiros campos visíveis** do quadro (menos o agrupador). O nome do campo só aparece se "Mostrar o nome de cada campo" estiver ligado (padrão desligado). Os campos são as colunas do quadro; "Comentários", "Anexos" e "Tarefas vinculadas" não existem como campo de cartão nos Quadros.

O botão `Configurar cartões` deve abrir um painel lateral.

Exemplo:

```text
Personalizar cartão Kanban

Campos visíveis
[x] Responsável
[x] Setor
[x] Prioridade
[x] Prazo
[x] Tarefas vinculadas
[x] Comentários
[x] Anexos
[ ] Valor estimado
[ ] Obra vinculada
```

---

# 19. Arrastar campos dentro do cartão

> **Divergência:** a ordem dos campos do cartão se altera com os botões de seta (subir/descer), não arrastando; o salvamento é automático (250 ms).

O usuário deve poder reorganizar os campos.

Exemplo:

```text
ANTES
Status
Prazo
Setor
Valor

DEPOIS
Prazo
Valor
Status
Setor
```

A pré-visualização deve atualizar imediatamente.

---

# 20. Pré-visualização do cartão

> **Divergência:** a pré-visualização mostra uma cópia do primeiro cartão real da visualização (ou a mensagem "Ainda não há cartões para mostrar"). "Exibir imagem de capa" não existe.

O painel de configuração deve mostrar um cartão de exemplo.

Exemplo:

```text
Validar Go/No-Go Santa Isabel

Status: Em andamento
Prazo: 20/09/2026
Setor: Comercial
Responsável: Camila Santos
```

Configurações podem incluir:

```text
Mostrar nome da coluna
Exibir imagem de capa
```

---

# 21. Card da Demanda

> **Divergência:** o cartão do Kanban de Demandas vem de `DomainBoardField`: padrão com **Título, Responsável, Setor, Prioridade, Prazo e Tarefas** (progresso feitas/total). Solicitante, Comentários e Anexos não estão no cartão. O nome dos campos aparece por padrão (`show_field_names` = verdadeiro). A configuração é salva com o botão "Salvar cartões" e a página recarrega.

Configuração inicial recomendada para Demandas:

```text
Título
Solicitante
Responsável
Setor
Prioridade
Prazo
Tarefas vinculadas
Comentários
Anexos
```

Campos adicionais opcionais:

```text
Obra
Cliente
Valor estimado
Tags
Descrição resumida
```

---

# 22. Card da Tarefa

> **Divergência:** a Tarefa hoje é um **item do Quadro da Demanda** (`BoardItem`); a `Task` antiga ficou como histórico. O cartão do Kanban de Tarefas mostra nome, Demanda, cliente e obra, prazo, Status (etiqueta), responsável e link "Abrir quadro". Não há checklist, bloqueio nem tempo estimado nesse cartão.

Configuração inicial recomendada:

```text
Título
Demanda vinculada
Responsável
Prazo
Prioridade
Checklist
```

Campos adicionais:

```text
Setor
Participantes
Bloqueio
Comentários
Anexos
Tempo estimado
Observações
```

Tempo deve ser opcional e secundário.

---

# 23. Abrir detalhes do item

> **Divergência:** no Kanban dos Quadros clicar no título do cartão **renomeia o item**; não há gaveta (o endpoint `board-item-detail` existe e é usado pelo Calendário). No Kanban de Demandas o título é um link para a ficha da Demanda. O Kanban legado abre a gaveta (`activity-kanban-drawer`) sem sair do quadro.

Clicar no título/cartão deve abrir um drawer lateral.

Evitar abandonar o Kanban.

Para Demanda:

- resumo;
- contexto;
- tarefas;
- arquivos;
- comentários;
- histórico.

Para Tarefa:

- Demanda vinculada;
- responsável;
- prioridade;
- prazo;
- Status;
- checklist;
- comentários;
- arquivos;
- histórico.

---

# 24. Criar item na coluna

> **Divergência:** nos Quadros, "Adicionar" na raia cria o item no primeiro grupo do quadro, já com a etiqueta da raia (ou vazia, na raia "Em branco"), e põe o título em edição. No Kanban de Demandas "Adicionar demanda" abre o assistente de criação (sem pré-preencher a Etapa). O Kanban legado de Demandas cria a Demanda direto na coluna (somente o nome; setor e etapa vêm do quadro, o responsável é quem criou). Criar Tarefa direto numa coluna do Kanban de Tarefas atual é feito pelo botão "Adicionar" da raia (A fazer, Em andamento, Concluídas), que escolhe o Quadro da Demanda e já usa a etiqueta correspondente quando existe.

Cada coluna pode apresentar:

```text
+ Adicionar demanda
```

ou:

```text
+ Adicionar tarefa
```

Ao criar dentro de uma coluna, o campo agrupador já deve nascer preenchido.

Exemplo:

Criou dentro de `Em andamento`:

```text
Status = Em andamento
```

---

# 25. Filtros

> **Divergência:** só há busca por texto e filtro por Pessoa na URL (`?q=`, `?pessoa=`); eles não são salvos na visualização. Filtros por valor de coluna estão desabilitados. O Kanban de Demandas tem os filtros da tela de Demandas (abas de escopo, Setor, Etapa, Status, Atrasadas, Vencem hoje e Pessoas); o legado acrescenta cliente, obra e etiqueta.

O Kanban utiliza filtros da visualização.

Exemplos:

```text
Responsável = Camila Santos
Setor = Comercial
Prioridade = Alta
Prazo <= 7 dias
Status != Concluído
```

O filtro não altera os dados, apenas a visualização.

---

# 26. Filtro por Pessoa

> **Divergência:** nos Quadros é uma lista de pessoas que aparecem em colunas de Pessoa do quadro ("Todas as pessoas" ou uma). As opções "Eu", solicitante, participante e "pessoas do meu setor" não existem; elas existem como abas de escopo na tela de Demandas.

Atalho útil:

```text
Pessoa
```

Pode permitir:

- Eu;
- responsável específico;
- solicitante;
- participante;
- pessoas do meu setor.

---

# 27. Pesquisa

> **Divergência:** a busca dos Quadros procura em título do item, textos de células, rótulos de etiquetas e nomes de pessoas (não há campo de código, cliente ou obra nos Quadros genéricos).

Pesquisar deve filtrar cartões dinamicamente.

Campos típicos:

- título;
- código;
- cliente;
- obra;
- responsável;
- etiquetas.

---

# 28. Ordenação

> **Divergência:** opções: "Ordem do quadro", Título A→Z/Z→A, Mais recentes/antigos e qualquer coluna do quadro crescente ou decrescente (Prazo, Valor e Prioridade entram se existirem como coluna). A ordem vale dentro de cada raia e fica salva na visualização. Arrastar dentro da raia não vira prioridade manual.

A ordenação pode ser global por coluna Kanban ou por lane.

Opções:

- Manual;
- Prazo crescente;
- Prazo decrescente;
- Prioridade;
- Título;
- Data de criação;
- Valor.

Se ordenação automática estiver ativa, drag dentro da mesma coluna pode ser limitado ou tratado como prioridade manual.

---

# 29. Coluna "Em branco"

> **Divergência:** implementada com o rótulo "Em branco" e três modos (`auto`: só quando houver itens; `always`; `never`). Mover um item para ela limpa a etiqueta, exceto se a coluna agrupadora for obrigatória.

Itens sem valor no campo agrupador devem aparecer em:

```text
Em branco
```

A visualização pode permitir ocultar essa coluna.

Mover um item para `Em branco` significa limpar o valor, se a regra permitir.

---

# 30. Alterar agrupamento sem recriar o Kanban

Este é um dos pontos mais importantes.

Exemplo:

```text
Agrupar por: Status
```

muda para:

```text
Agrupar por: Setor
```

O Kanban é reorganizado imediatamente.

Não criar outra tela.

---

# 31. Múltiplos Kanbans do mesmo quadro

> **Divergência:** implementado nos Quadros (cada `BoardView` tem `settings` próprio: coluna agrupadora, soma, campos, ordenação). "Kanban por Responsável" não é possível enquanto Pessoa não for agrupável.

O mesmo quadro pode possuir:

```text
Kanban por Status
Kanban por Setor
Kanban por Responsável
```

Cada um tem configurações próprias.

Os itens continuam sendo os mesmos.

---

# 32. Uso para gestão sem microgerenciamento

O Kanban deve ajudar o gestor a enxergar:

- onde o trabalho está;
- o que está parado;
- onde existe concentração;
- quais itens estão bloqueados;
- quais prazos estão próximos;
- qual setor acumulou demandas;
- quais entregas precisam de intervenção.

Ele não deve ser desenhado para responder:

```text
Quem ficou 17 minutos sem mexer numa tarefa?
```

A LPS deve favorecer **gestão por exceção**, não vigilância.

---

# 33. Exemplos de Kanban de Demandas

> **Divergência:** no Kanban de Demandas as raias por padrão são as **Etapas** da organização (`ActivityStage`, ordenadas por `order`), mais a raia "Sem estágio" (a interface ainda mistura "Etapa" e "Estágio", e o campo padrão do quadro de domínio chama-se "Status" tanto para a Etapa quanto para o Status, em `boards/domain_defaults.py`); agrupar por Status usa os Status de Demanda. "Por Setor" e "Por Prioridade" têm suporte no servidor, mas sem controle na tela.

## Por Status

```text
Novas | Em andamento | Aguardando retorno | Concluídas
```

## Por Setor

```text
Comercial | Engenharia | Suprimentos | Financeiro | RH
```

## Por Prioridade

```text
Alta | Média | Baixa
```

---

# 34. Exemplos de Kanban de Tarefas

> **Divergência:** o Kanban de Tarefas (`/tarefas/kanban/`) tem três raias fixas derivadas da etiqueta de Status do item: **A fazer** (sem Status ou etiqueta padrão), **Em andamento** e **Concluídas** (etiqueta que "representa conclusão"). Agrupar por Setor ou Responsável não existe nessa tela. Cada raia mostra no máximo 50 cartões (`KANBAN_CAP`).

## Por Status

```text
A fazer | Em execução | Bloqueadas | Concluídas
```

## Por Setor

```text
Comercial | Suprimentos | Engenharia | Obras
```

## Por Responsável

```text
Paulo | Ryan | Luan | Jennifer
```

Essa última visão é útil para carga de trabalho, mas deve mostrar volume e compromissos, não transformar ausência de interação em julgamento de produtividade.

---

# 35. Relação com regras de negócio

> **Divergência:** o fluxo "soltar, pedir motivo, validar" **não existe** no arrastar. No Kanban legado de Demandas, a ação que pede motivo ("Cancelar demanda") abre janela pelo menu do cartão, não pelo arrastar; as ações de Tarefa do legado (bloquear, mover de setor) foram desativadas. O Kanban de Tarefas atual não permite arrastar.

A visualização não deve ignorar serviços existentes.

Exemplo conceitual:

```text
Usuário arrasta tarefa para Bloqueada
```

Se a regra exigir motivo:

1. card é solto;
2. sistema abre popup de motivo;
3. usuário informa;
4. service valida;
5. servidor persiste;
6. auditoria e notificação são geradas;
7. card permanece em Bloqueada.

O Kanban não pode contornar regras apenas porque o gesto foi drag-and-drop.

---

# 36. Permissões

> **Divergência:** nos Quadros valem `quadro.visualizar`, `quadro.editar` (criar, renomear, configurar e excluir visualizações), `quadro.gerir_colunas` (criar, editar, reordenar e excluir etiquetas), `quadro.criar_item`, `quadro.editar_item` e `quadro.excluir_item`. Quadros de Demanda usam `DemandBoardAccess`. A conferência é feita no servidor a cada requisição.

Verificar no servidor:

- visualizar item;
- editar item;
- mover Status;
- mudar Setor;
- atribuir responsável;
- gerenciar etiquetas;
- editar visualização;
- personalizar cartões;
- compartilhar.

O fato de um botão estar escondido não substitui autorização.

---

# 37. Auditoria

> **Divergência:** alterações de célula (inclusive o arrastar) geram `BOARD_CELL_UPDATED` com valor antigo e novo; criação, edição e exclusão de visualização geram `BOARD_VIEW_*`. O histórico do quadro fica em `board-history`. No Kanban de Demandas a auditoria é a dos `ActivityService`.

Movimentos que alteram dado de negócio devem ser auditáveis.

Exemplos:

- Status alterado;
- Setor alterado;
- Responsável alterado;
- Prioridade alterada;
- prazo alterado.

Movimentos puramente visuais podem ser tratados separadamente.

---

# 38. Autosave

> **Divergência:** nos Quadros todas as configurações leves (agrupamento, ordenação, raias vazias, soma, campos do cartão) salvam ao alterar, sem botão. No Kanban de Demandas o painel "Configurar cartões" exige "Salvar cartões" e recarrega a página.

Configurações leves devem salvar automaticamente:

- escolha de campos do cartão;
- ordem dos campos;
- mostrar/ocultar campo;
- agrupamento;
- mostrar colunas vazias;
- opção de resumo;
- cor de etiqueta;
- renomeação.

Botão explícito pode existir para configurações maiores, mas não deve ser necessário para cada pequena interação.

---

# 39. Interface otimista

> **Divergência:** o cartão se move na hora e volta se o servidor recusar. Depois de gravar, o navegador pede o HTML das raias de novo (`board-view-lanes`) para refletir contagens, soma e ordenação; não se atualiza só o cartão alterado.

Ao mover um cartão:

1. UI move imediatamente;
2. requisição é enviada;
3. servidor valida;
4. se sucesso, mantém;
5. se erro, retorna e mostra mensagem.

O usuário não deve esperar uma página recarregar.

---

# 40. Performance

> **Divergência:** o número de consultas do Kanban dos Quadros não cresce com o número de cartões (células pré-carregadas), mas **todas as raias e cartões são carregados de uma vez**; não há carga por raia nem renderização por viewport. A tela de Tarefas limita 50 cartões por raia e 2.000 itens lidos.

Para muitos cartões:

- carregar por lane;
- limitar renderização fora do viewport;
- atualizar somente cartão alterado;
- buscar contadores de forma eficiente;
- evitar recarregar o board completo;
- debounce nas configurações;
- manter consultas isoladas por organização.

---

# 41. Responsividade

> **Divergência:** há rolagem horizontal entre raias e ajustes de CSS abaixo de 720 px; drawer em tela cheia e gesto de swipe dedicados **não verificados**.

No desktop:

- scroll horizontal entre lanes;
- largura estável das colunas;
- cabeçalho de lane permanece legível.

No mobile:

- uma ou poucas lanes por vez;
- swipe/scroll horizontal;
- drawer ocupa tela;
- ações rápidas continuam acessíveis.

---

# 42. Acessibilidade

> **Divergência:** o menu "Mover para" (alternativa ao arrastar) existe no cartão dos Quadros e "Mover para etapa…" no legado; o Kanban de Demandas atual não tem alternativa ao arrastar. Títulos e campos do cartão são focáveis por teclado (Enter edita); etiquetas têm texto, não só cor.

Drag-and-drop deve possuir alternativa.

Menu do cartão:

```text
Mover para
  A fazer
  Em execução
  Bloqueada
  Concluída
```

Também:

- navegação por teclado;
- foco visível;
- contraste das cores;
- não depender apenas da cor para indicar estado.

---

# 43. O que não fazer

Evitar:

- criar dados exclusivos do Kanban;
- cadastrar novamente as mesmas etiquetas;
- fazer o usuário sair da tela para renomear Status;
- exigir salvar manual após mudar cor;
- transformar cada agrupamento em módulo separado;
- permitir drag que viole regra de negócio;
- esconder falha de persistência;
- usar texto da etiqueta como identificador interno;
- mostrar todos os campos no cartão por padrão;
- usar tempo como principal métrica de produtividade.

---

# 44. Critérios de aceite

A visualização Kanban está pronta quando:

- [x] pode ser criada a partir do mesmo quadro; (implementado)
- [x] não duplica itens; (implementado)
- [x] permite escolher a coluna de agrupamento; (implementado)
- [x] suporta Status e Lista suspensa; (implementado)
- [ ] suporta outros agrupamentos aprovados pela LPS; (Quadros: não; Demandas: Estágio e Status na tela, outros no servidor)
- [x] reflete renomeação de etiqueta imediatamente; (implementado)
- [x] reflete mudança de cor imediatamente; (implementado)
- [x] permite selecionar Status diretamente no cartão; (implementado nos Quadros)
- [x] permite editar etiquetas sem sair do Kanban; (implementado nos Quadros)
- [x] permite arrastar cartões; (implementado)
- [ ] drag executa regra de negócio correta; (parcial: nos Quadros só a validação da célula; Demandas usa os services)
- [x] drag inválido é revertido; (implementado)
- [x] permite mostrar colunas vazias; (implementado)
- [x] possui coluna Em branco para valores vazios; (implementado)
- [x] permite ordenar cartões; (implementado)
- [ ] permite filtrar; (parcial: só busca e Pessoa; filtros por valor em breve)
- [x] permite pesquisar; (implementado)
- [x] permite configurar campos do cartão; (implementado)
- [x] permite reordenar campos do cartão; (implementado, por setas)
- [x] mostra pré-visualização; (implementado)
- [x] permite múltiplos Kanbans do mesmo quadro; (implementado)
- [x] alterações leves usam autosave; (implementado nos Quadros; Demandas usa botão)
- [x] permissões são verificadas no servidor; (implementado)
- [x] alterações de negócio são auditáveis. (implementado)

---

# 45. Resumo da filosofia

O Kanban da LPS deve transmitir a sensação:

> Eu escolho como quero enxergar o trabalho, e os mesmos dados se reorganizam na hora.

A regra central é:

```text
Mesmo dado + outra lente = outra visualização
```

O Kanban não é um banco separado, não é uma tela rígida e não deve exigir manutenção duplicada.

Ele é uma lente visual sobre o quadro, configurável pelo usuário e sempre conectado à mesma fonte de verdade.
