# LPS — Especificação Completa das Colunas Dinâmicas

## Status de implementação (03/10/2026)

**Resumo.** O motor de colunas existe no app `boards` (quadros dinâmicos: `Board`, `BoardColumn`, `BoardColumnOption`, `BoardItem`, `BoardCell`), com visões Tabela ("Quadro principal", implícita), Kanban e Calendário sobre os mesmos itens e valores. Das 13 colunas-base desta especificação, **8 estão implementadas e podem ser criadas**: Texto, Número, Moeda, Data, Pessoas (somente uma pessoa por célula), Status, Lista suspensa (seleção única) e Confirmação (tipo técnico `CHECKBOX`, rótulo "Sinal de confirmação"). **Prioridade, Arquivo, Relação, Cronograma e Fórmula não existem como colunas de quadro**: `PRIORITY`, `FILE`, `RELATION`, `TIMELINE`, `FORMULA` (além de `CONFIRMATION` e `AI_EXTRACT`) estão apenas reservados no catálogo `BoardColumn.Type` e não se criam nem se editam. As operações comuns (criar, renomear inline, mover, redimensionar, ocultar, duplicar, alterar tipo com plano de conversão, excluir logicamente, autosave por célula), a auditoria e as permissões no servidor estão implementadas. **Não existem** filtros por coluna, autoajuste de largura, linha de resumo, verificação de dependências na exclusão, restrição de visualização por coluna, cópia/cola e exportação. Em paralelo, Demandas e Tarefas usam o "quadro de domínio" (`DomainBoard*`) sobre `Activity` e `Task`, com campos de sistema fixos e campos customizados simples (`DomainCustomValue`). Estimativa: cerca de 45% da especificação está implementada (revisão do código no commit `add5acd`, de 02/10/2026).

Vocabulário atual da interface: "Atividade" virou **Demanda** (o código segue `Activity`), "Situação" virou **Etapa** (`stage`) e "Condição" virou **Status** (`condition`). No quadro dinâmico, o item aparece como "Tarefa" (`Board.item_label`, padrão "Nome da Tarefa").

| Requisito / bloco | Status | Onde está no código |
|---|---|---|
| Modelo de coluna (§5) | Divergente (nomes diferentes) | `boards/models.py` (`BoardColumn`: `is_required`, `board`, `settings`, `position` decimal, `width` 96–640) |
| Tipos-base (§4, §61, §62) | Parcial (8 de 13) | `boards/models.py` (`BoardColumn.Type`, `ACTIVE_TYPES`); `boards/presentation.py` (`TYPE_INFO`) |
| Operações comuns: criar, renomear, mover, redimensionar (§6.1–6.4) | Implementado | `boards/services.py` (`ColumnService`, `PositionService`); `boards/views.py`; `static/js/boards.js` |
| Autoajuste, filtro por coluna (§6.5, §6.7) | Não implementado | — (só busca textual e filtro por pessoa em `boards/queries.py`) |
| Ordenar, agrupar, ocultar, excluir (§6.6, §6.8, §6.12, §6.13) | Parcial | `boards/queries.py` (`sort_expression`); `boards/kanban.py`; `ColumnService.set_visible`, `soft_delete` |
| Duplicar coluna, alterar tipo (§6.9, §6.11) | Divergente | `ColumnService.duplicate`, `conversion_plan`, `change_type` |
| Autosave (§6.14) | Parcial | gravação por célula em `CellService.set_value`; diálogo "Configurações da coluna" tem botão Salvar |
| Visões: Tabela, Kanban, Calendário, gaveta de detalhes (§7, §28, §29) | Parcial | `boards/kanban.py`, `boards/calendar_view.py`, `templates/boards/*`; formulário de criação não existe |
| Colunas Texto, Número, Moeda, Data (§8–§11) | Parcial | `boards/validators.py`, `boards/services.py` (`CellService`), `templates/boards/_cell.html` |
| Coluna Pessoas (§12) | Parcial (uma pessoa) | `BoardCellUser`; `core/views.py` (`PersonSearchView`); `boards/validators.py` |
| Colunas Status e Lista suspensa (§13, §14) | Implementado (Lista só com seleção única) | `BoardColumnOption`, `OptionService`; `static/js/boards.js` (`openLabels`, `editOption`) |
| Coluna Confirmação (§16) | Implementado (como `CHECKBOX`) | `BoardCell.value_boolean`; `static/js/boards.js` |
| Prioridade, Arquivo, Relação, Cronograma, Fórmula (§15, §17–§20) | Não implementado em quadros dinâmicos | apenas valores reservados em `BoardColumn.Type`; no quadro de domínio, Prioridade e "Demanda vinculada" existem como campos de sistema |
| Campos de negócio e conjuntos iniciais (§21–§23) | Parcial | `boards/domain_defaults.py`, `boards/domain_services.py`, `boards/work_views.py`, `boards/starter_templates.py` (modelo "Orçamentos") |
| Obrigatória, valor padrão, validações (§24–§26) | Parcial | `normalize_cell_value`; `ItemService.create` (etiqueta padrão); obrigatoriedade não é checada na criação do item |
| Resumo de coluna (§27) | Parcial | só soma de Número/Moeda no cabeçalho da raia do Kanban (`boards/kanban.py`, `build_lanes`) |
| Edição contextual, popovers, gaveta (§30–§32, §58, §59) | Implementado | `static/js/boards.js` (`openCellEditor`, `editDate`, `editOption`, `editPerson`); `templates/boards/_item_drawer.html` |
| Segurança, multi-organização, auditoria (§33, §36–§38) | Implementado | `boards/services.py` (`_require`, `_audit`); `boards/views.py` (`get_*` por organização); `boards/presentation.py` |
| Restrição por coluna, notificações de coluna (§34, §35, §39, §40) | Não implementado | — |
| Valores vazios, pesquisa (§41, §45) | Parcial | `templates/boards/_cell.html`; `BoardQueryService.search_filter` |
| Cópia e cola, exportação (§43, §44) | Não implementado | — |
| Campos não editáveis, de sistema, futuros, IA (§46–§50) | Parcial (só no quadro de domínio) | `DomainBoardField.is_system`; `BoardColumn.Type.AI_EXTRACT` reservado |
| Nomes, soft delete, performance, acessibilidade (§51–§57) | Parcial | `ColumnService._unique_name`; `is_active`; `BoardQueryService.with_cells`; `static/css/boards.css` |
| Contrato por tipo e arquitetura de classes (§61, §62) | Divergente | lógica por tipo em ramos `if` (validators, services, queries, templates, JS), sem `BaseColumnType` |
| Critérios de aceite (§63–§69) | Parcial | tabelas de status em cada seção |

### Nomes na especificação × nomes no código

| Especificação | Código |
|---|---|
| `board_id`, `required` | `board` (chave estrangeira), `is_required` |
| `MONEY`, `PEOPLE`, `CONFIRMATION` | `CURRENCY`, `PERSON`, `CHECKBOX` (`CONFIRMATION` fica reservado) |
| `date_format` (configuração de Data) | `format` (`DD/MM/YYYY`, `DD/MM/YY`, `YYYY-MM-DD`) |
| opção de Status: `name`, `order`, `behavior` | `BoardColumnOption`: `label`, `position`, `is_default`, `is_done`, `is_active` |
| valor da célula | `BoardCell` tipada: `value_text`, `value_number`, `value_date`, `value_datetime`, `value_boolean`, mais `BoardCellUser` e `BoardCellOption` |

## 1. Objetivo

Este documento define o padrão oficial de **colunas dinâmicas da LPS**.

A coluna é uma das peças centrais do novo motor de Quadros.

A ideia é simples:

```text
Quadro
├── Colunas
├── Itens
└── Visualizações
```

Cada coluna define:

- qual informação existe;
- qual é o tipo da informação;
- como o usuário preenche;
- como o valor aparece;
- como o valor é validado;
- como pode ser filtrado;
- como pode ser ordenado;
- como pode ser agrupado;
- como aparece no Kanban;
- como aparece no Calendário;
- como pode participar de Fórmulas;
- quais permissões controlam sua edição e visualização.

A coluna não pertence exclusivamente à Tabela.

Ela pertence ao **Quadro**.

Tabela, Kanban e Calendário usam a mesma coluna e o mesmo valor.

---

# 2. Regra principal

> Um dado deve existir uma única vez e ser apresentado de formas diferentes pelas visualizações.

Exemplo:

```text
Coluna: Status
Valor: Em andamento
```

Na Tabela:

```text
| Em andamento |
```

No Kanban:

```text
coluna "Em andamento"
```

No Calendário:

```text
card com etiqueta "Em andamento"
```

No filtro:

```text
Status = Em andamento
```

Não criar uma versão do Status para cada tela.

> **Status (03/10/2026): Implementado nos quadros dinâmicos.** O valor existe uma única vez em `BoardCell` (por item e coluna) e as visões só o leem: a Tabela ("Quadro principal", sem registro próprio), o Kanban (`BoardView` tipo `KANBAN`, `boards/kanban.py`) e o Calendário (`BoardView` tipo `CALENDAR`, `boards/calendar_view.py`). Mover um cartão grava a mesma célula pelo mesmo serviço da Tabela (`CellService.set_value`).

---

# 3. Situação atual da LPS × nova arquitetura

Na LPS atual, `Activity` e `Task` ainda possuem vários campos definidos diretamente no código e no banco de dados.

Exemplos atuais:

```text
Activity.owner
Activity.requested_by
Activity.sector
Activity.client
Activity.site
Activity.status
Activity.urgency
Activity.requested_deadline

Task.responsavel
Task.sector
Task.status
Task.requested_deadline
Task.committed_deadline
```

Na nova arquitetura, esses conceitos passam a ser apresentados por um **motor comum de colunas**.

Exemplo:

```text
Responsável       → Pessoas
Solicitante       → Pessoas
Setor             → Relação
Cliente           → Relação
Obra              → Relação
Prazo             → Data
Valor da proposta → Moeda
Status            → Status
Prioridade        → Prioridade
Margem            → Fórmula
```

Isso permite adicionar novos campos sem criar nova tela e sem alterar o banco para cada pequena necessidade de negócio.

> **Divergência (03/10/2026):** o motor comum ainda não substituiu os campos de `Activity` e `Task`. Eles continuam no modelo e no banco (`Activity`: `client`, `site`, `cost_center`, `sector`, `stage`, `condition`, `status`, `urgency`, `owner`, `requested_by`, `requested_deadline`; `Task`: `sector`, `stage`, `condition`, `status`, `priority`, `requested_deadline`, `committed_deadline`, `responsavel`). O quadro de domínio (`DomainBoard`, `DomainBoardField`, `boards/domain_defaults.py`) apresenta um subconjunto deles como **campos de sistema** (`is_system=True`) e grava sempre pelos services de `activities` (`ActivityService`, `TaskService`), que mantêm regras e auditoria. Só os campos customizados simples (`DomainCustomValue`) usam o mecanismo novo. Termos atuais: Situação = **Etapa** (`stage`), Condição = **Status** (`condition`), Atividade = **Demanda**. O mapeamento da lista acima (Setor, Cliente e Obra como Relação; Margem como Fórmula) é **futuro**.

---

# 4. Tipos-base oficiais da LPS

A primeira arquitetura deve trabalhar com 13 tipos-base:

```text
1. Texto
2. Número
3. Moeda
4. Data
5. Pessoas
6. Status
7. Lista suspensa
8. Prioridade
9. Confirmação
10. Arquivo
11. Relação
12. Cronograma
13. Fórmula
```

Esses são os tipos fundamentais.

Colunas de negócio são construídas sobre eles.

Exemplo:

```text
"Responsável" não é um tipo.
É uma coluna do tipo Pessoas.

"Cliente" não é um tipo.
É uma coluna do tipo Relação.

"Valor da proposta" não é um tipo.
É uma coluna do tipo Moeda.
```

> **Divergência (03/10/2026):** em quadros dinâmicos estão implementados **8 dos 13 tipos**: Texto (`TEXT`), Número (`NUMBER`), Moeda (`CURRENCY`), Data (`DATE`), Pessoas (`PERSON`), Status (`STATUS`), Lista suspensa (`DROPDOWN`) e Confirmação (`CHECKBOX`, rótulo "Sinal de confirmação"). O seletor os oferece nesta ordem: Status, Lista suspensa, Texto, Data, Pessoa, Número, Moeda, Sinal de confirmação (`BoardColumn.ACTIVE_TYPES`). **Prioridade, Arquivo, Relação, Cronograma e Fórmula não foram implementados** como tipos de quadro: `PRIORITY`, `FILE`, `RELATION`, `TIMELINE`, `FORMULA`, `CONFIRMATION` e `AI_EXTRACT` existem no catálogo apenas como reserva ("fases futuras") e `ColumnService.create` os recusa ("Tipo de coluna inválido"). O quadro de domínio de Demandas e Tarefas tem um catálogo separado (`DomainBoardField.Type`: `TEXT`, `NUMBER`, `CURRENCY`, `DATETIME`, `PERSON`, `STAGE`, `SECTOR`, `PRIORITY`, `SELECT`, `BOOLEAN`, `CHECKLIST`, `RELATION`), usado para os campos de sistema.

---

# 5. Estrutura conceitual de uma coluna

Toda coluna deve possuir propriedades comuns.

Exemplo conceitual:

```text
Column

id
board_id
name
type
position
width
required
description
is_visible
is_active
settings
created_at
updated_at
```

## 5.1 `id`

Identificador interno e imutável.

O nome visível nunca deve ser usado como identidade técnica.

## 5.2 `board_id`

Quadro ao qual a coluna pertence.

## 5.3 `name`

Nome mostrado ao usuário.

Exemplos:

```text
Responsável
Prazo
Cliente
Valor
Status
```

Pode ser renomeado sem quebrar dados.

## 5.4 `type`

Define o comportamento da coluna.

Exemplos:

```text
TEXT
NUMBER
MONEY
DATE
PEOPLE
STATUS
DROPDOWN
PRIORITY
CONFIRMATION
FILE
RELATION
TIMELINE
FORMULA
```

> **Divergência:** os identificadores técnicos são `TEXT`, `NUMBER`, `CURRENCY` (e não `MONEY`), `DATE`, `PERSON` (e não `PEOPLE`), `STATUS`, `DROPDOWN` e `CHECKBOX` (a spec chama de `CONFIRMATION`, que ficou reservado). Os demais (`PRIORITY`, `FILE`, `RELATION`, `TIMELINE`, `FORMULA`) estão reservados e não são criáveis.

## 5.5 `position`

Define a ordem da coluna.

A ordem deve ser alterável por arrastar e soltar.

## 5.6 `width`

Largura visual da coluna na Tabela.

Deve ser persistida.

## 5.7 `required`

Indica se o valor é obrigatório em criação/edição.

## 5.8 `description`

Ajuda contextual da coluna.

Exemplo:

```text
Prazo comprometido de entrega ao solicitante.
```

## 5.9 `is_visible`

Controla se a coluna aparece na visualização atual.

Não significa exclusão.

> **Divergência:** `BoardColumn.is_visible` vale para o quadro inteiro (a Tabela), não por visualização. Kanban e Calendário escolhem seus campos de cartão à parte, em `BoardView.settings["card_fields"]`. Só o quadro de domínio guarda visibilidade, ordem e largura por visualização (`DomainBoardViewColumn`).

## 5.10 `is_active`

Permite desativação lógica.

## 5.11 `settings`

Guarda configurações específicas de cada tipo.

Exemplo de Data:

```json
{
  "show_time": true,
  "date_format": "DD/MM/YYYY"
}
```

Exemplo de Pessoas:

```json
{
  "multiple": false
}
```

> **Divergência:** o JSON de configuração é validado por `clean_column_settings` (`boards/validators.py`) e só aceita chaves conhecidas por tipo: Data (`show_time`, `allow_weekends`, `is_deadline`, `format`), Número (`decimal_places`, `unit`, `minimum`, `maximum`), Moeda (`currency`, `decimal_places`, `minimum`, `maximum`) e Pessoa (`multiple`, que só aceita `false`). Na Data a chave é `format` e não `date_format`. Texto, Status, Lista e Confirmação não têm configuração própria.

Mapeamento das propriedades comuns para `BoardColumn`:

| Propriedade da spec | Campo no código | Observação |
|---|---|---|
| `id` | `id` | imutável; o nome nunca é identidade |
| `board_id` | `board` | chave estrangeira para `Board` |
| `name` | `name` | até 120 caracteres |
| `type` | `type` | ver §5.4 |
| `position` | `position` | decimal (20,6), passo 1000; o cliente envia os vizinhos (`before_id`, `after_id`) e o servidor calcula a posição (`PositionService`) |
| `width` | `width` | padrão 160, mínimo 96, máximo 640 |
| `required` | `is_required` | ver §24 |
| `description` | `description` | o serviço grava até 500 caracteres |
| `is_visible` | `is_visible` | por quadro, ver §5.9 |
| `is_active` | `is_active` | exclusão lógica |
| `settings` | `settings` | ver acima |
| `created_at`, `updated_at` | `created_at`, `updated_at` | além de `created_by` |

---

# 6. Regras comuns a todas as colunas

Toda coluna deve seguir as mesmas regras de experiência, exceto onde o tipo exigir comportamento diferente.

---

## 6.1 Criar coluna

Fluxo:

```text
[ + ]

Pesquisar ou descrever sua coluna

Status
Texto
Pessoas
Lista suspensa
Data
Números
...
```

O usuário escolhe o tipo.

A coluna aparece imediatamente.

Não abrir uma página separada.

> **Status (03/10/2026): Implementado, com diferenças.** O botão "+" do cabeçalho abre um popover com a grade de tipos ("Escolha o tipo da coluna"); a coluna entra na hora, sem trocar de página (`ColumnService.create`, `static/js/boards.js`, `openTypePicker`).
>
> **Divergência:** o seletor não tem campo de pesquisa nem "descrever sua coluna", e oferece 8 tipos (ver §4). Nomes iniciais: Texto, Números, Valor, Data, Pessoa, Status, Lista suspensa, Confirmação (com sufixo "2", "3"... se já existir). Uma coluna de Status nasce com três etiquetas: "Não iniciado" (padrão), "Em andamento" e "Concluído" (conta como concluído).

---

## 6.2 Renomear

O nome deve ser editável inline.

Fluxo:

```text
Status
```

clicou:

```text
[ Status ]
```

digitou:

```text
Etapa comercial
```

Enter:

```text
Etapa comercial
```

Autosave.

> **Status (03/10/2026): Implementado.** Edição inline no cabeçalho (Enter confirma, Esc cancela) e gravação imediata (`ColumnService.rename`, endpoint `board-column-rename`). O serviço não impede nome repetido (ver §52).

---

## 6.3 Mover

A coluna deve poder ser arrastada horizontalmente.

Exemplo:

```text
Cliente | Responsável | Status | Prazo
```

vira:

```text
Cliente | Status | Responsável | Prazo
```

A ordem é salva automaticamente.

> **Status (03/10/2026): Implementado.** Arrastar o cabeçalho; a nova posição é gravada entre as vizinhas (`ColumnService.reorder`, endpoint `board-column-reorder`) e desfeita na tela se o servidor recusar.

---

## 6.4 Redimensionar

O usuário arrasta a divisória lateral do cabeçalho.

Exemplo:

```text
| Responsável                   |
```

pode virar:

```text
| Responsável |
```

A largura é persistida.

> **Status (03/10/2026): Implementado.** Arrastar a divisória do cabeçalho ou usar as setas do teclado (16 px; 48 px com Shift); limites de 96 a 640 px, padrão 160 (`ColumnService.resize`, endpoint `board-column-resize`). No quadro dinâmico a largura é da coluna e vale para todas as pessoas.

---

## 6.5 Autoajuste

Duplo clique na divisória pode ajustar automaticamente a largura conforme o conteúdo.

> **Status (03/10/2026): Não implementado.** Não há tratamento de duplo clique na divisória (`static/js/boards.js`). Continua como requisito futuro.

---

## 6.6 Ordenar

Toda coluna ordenável deve oferecer:

```text
Ordenar crescente
Ordenar decrescente
Remover ordenação
```

Cada tipo define sua lógica de comparação.

> **Status (03/10/2026): Parcial.** O menu da coluna oferece "Ordenar ascendente", "Ordenar descendente" e "Remover ordenação". A ordenação é por uma coluna de cada vez, via `?sort=<id>&dir=asc|desc` (a página recarrega) e é feita no banco (`BoardQueryService.sort_expression`), dentro de cada grupo: Texto sem diferenciar maiúsculas, Número e Moeda numericamente, Data cronologicamente (considera a hora quando `show_time` está ligado), Status e Lista pela posição das etiquetas, Pessoa pelo nome, Confirmação pelo valor; vazios por último. O Kanban tem ordenação própria (ordem do quadro, título, criação ou coluna), salva na visualização.

---

## 6.7 Filtrar

Toda coluna filtrável deve abrir um filtro coerente com seu tipo.

Exemplos:

Texto:

```text
contém
não contém
é igual a
está vazio
```

Número:

```text
maior que
menor que
entre
igual a
```

Data:

```text
antes de
depois de
entre
hoje
esta semana
atrasado
```

Pessoas:

```text
contém Ryan
não contém Ryan
está vazio
```

> **Status (03/10/2026): Não implementado (filtro por coluna).** Os operadores listados acima (contém, maior que, entre, atrasado, é Eu etc.) não existem. O que há: busca textual do quadro (`q`, até 120 caracteres: nome do item, textos, rótulos de etiqueta e nomes de pessoa) e um filtro por pessoa (`pessoa`), repetidos no Kanban e no Calendário (`BoardQueryService._filtered_items`). No quadro de domínio, as telas de Demandas e Tarefas usam os filtros do app `activities` (prazo, etapa, status, pessoa).

---

## 6.8 Agrupar por

Tipos categóricos podem ser usados para agrupamento.

Exemplos:

```text
Status
Prioridade
Pessoa
Setor
Cliente
Lista suspensa
```

Tipos como Texto livre não devem ser a primeira opção para agrupamento.

> **Status (03/10/2026): Parcial.** Na Tabela, o agrupamento é por **grupos manuais** do quadro (`BoardGroup`), que não são um valor de coluna. Só o Kanban agrupa por coluna, e apenas por **Status ou Lista suspensa** (`GROUPABLE_TYPES` em `boards/kanban.py`); Pessoa, Data e os demais tipos ficam para uma próxima versão. No quadro de domínio, o agrupamento aceita `stage`, `condition`, `sector`, `owner`/`responsavel` e `urgency`/`priority` (`WorkBoardViewSettingsView`).

---

## 6.9 Duplicar coluna

Duplica:

- tipo;
- configurações;
- opções;
- largura;
- validações.

Por padrão, não duplica os valores dos itens.

Uma opção futura pode permitir duplicar também valores.

> **Divergência (03/10/2026):** a duplicação copia tipo, configurações, descrição, obrigatoriedade, largura e etiquetas **e também os valores das células** (pessoas e etiquetas incluídas); a spec pede que, por padrão, os valores não sejam copiados. A cópia nasce ao lado da original com o nome "<nome> (cópia)" (`ColumnService.duplicate`).

---

## 6.10 Adicionar coluna à direita

A partir do menu:

```text
Adicionar coluna à direita
```

Abre o seletor de tipos sem mudar de tela.

> **Status (03/10/2026): Implementado.** Item "Adicionar coluna à direita" no menu da coluna; abre o seletor de tipos e cria a coluna logo após a escolhida (`after_column_id`).

---

## 6.11 Alterar tipo

Só deve ser permitido entre tipos compatíveis ou após validação de conversão.

Exemplos seguros:

```text
Número → Moeda
Texto → Número, somente se todos os valores forem válidos
Data → Data com hora
```

Exemplos perigosos:

```text
Pessoas → Número
Arquivo → Data
```

Nesses casos, bloquear ou exigir uma migração explícita.

> **Divergência (03/10/2026):** `ColumnService.conversion_plan` classifica a troca em três modos. **Segura** (nada se perde): Número↔Moeda, Status↔Lista suspensa e qualquer tipo → Texto (o valor vira o texto exibido). **Com leitura** (`parsed`): Texto → Número, Moeda ou Data; o que não converte é apagado, e a tela informa quantos valores se perdem. **Destrutiva**: qualquer outro par, com todos os valores da coluna apagados e as etiquetas desativadas. Fora do modo seguro, o servidor responde 409 e só converte com `confirm`; a tela mostra uma pré-visualização (`preview`). Diferenças em relação ao texto: Pessoas → Número **não é bloqueado**, é permitido com confirmação e perda dos valores; Texto → Número não exige que todos os valores sejam válidos; "Data → Data com hora" não é troca de tipo, é a opção `show_time`. Ao trocar, as configurações voltam ao padrão do novo tipo.

---

## 6.12 Ocultar

Ocultar não exclui a coluna.

A coluna continua existindo e pode alimentar:

- filtros;
- Fórmulas;
- Kanban;
- Calendário;
- automações.

> **Status (03/10/2026): Parcial.** "Ocultar coluna" grava `is_visible=False` para o quadro todo; a barra mostra "Colunas ocultas (N)" com o botão "Mostrar". A coluna continua existindo e pode ser usada no Kanban (agrupamento, soma, cartão) e no Calendário. Filtros por coluna, Fórmulas e automações ainda não existem.

---

## 6.13 Excluir

Exclusão deve exigir confirmação.

Se houver dados históricos, Fórmulas ou automações usando a coluna:

```text
Esta coluna é usada por:
- 2 Fórmulas
- 1 visualização
- 3 filtros salvos
```

O sistema deve impedir exclusão insegura ou solicitar tratamento das dependências.

> **Status (03/10/2026): Parcial.** A exclusão pede confirmação e é lógica (`is_active=False`, `ColumnService.soft_delete`). **Não há verificação de dependências**: as visualizações que apontavam para a coluna deixam de usá-la e recaem no padrão (`resolve_group_column`, `resolve_date_column`), sem aviso ao usuário. Fórmulas, filtros salvos e automações não existem.

---

## 6.14 Autosave

Não criar botão geral:

```text
Salvar coluna
```

Pequenas mudanças devem ser persistidas automaticamente.

> **Divergência (03/10/2026):** renomear, mover, redimensionar, ocultar, editar células e editar etiquetas gravam na hora. Já o diálogo "Configurações da coluna" (descrição, obrigatória, casas decimais, moeda, horário etc.) tem botão **Salvar**, e a ocultação recarrega a página.

---

# 7. Modo de apresentação geral

A mesma coluna possui diferentes formas de apresentação.

---

## 7.1 Tabela

Exibe uma célula por item.

Exemplo:

```text
| Status       |
| Em andamento |
| Concluído    |
```

> **Status (03/10/2026): Implementado.** A Tabela é o "Quadro principal", implícito em todo quadro (`templates/boards/board_detail.html`, `_board_workspace.html`), com grupos, colunas e uma célula por item.

---

## 7.2 Kanban

Pode:

- ser usada para agrupar;
- aparecer dentro do cartão;
- ser editada pelo próprio cartão.

> **Status (03/10/2026): Implementado.** Raias = etiquetas da coluna agrupadora (Status ou Lista); cartões com campos configuráveis e editáveis no próprio cartão; arrastar o cartão grava a etiqueta da coluna agrupadora (`boards/kanban.py`, `templates/boards/_kanban_lanes.html`).

---

## 7.3 Calendário

Colunas de Data podem posicionar o item.

Outras colunas aparecem como informações do cartão.

> **Status (03/10/2026): Implementado (escala mensal).** A coluna de Data escolhida (`date_field`) posiciona o item; arrastar o cartão para outro dia grava a data. Só existe a escala "Mês" (`PERIODS = ("month",)`); há painéis "Sem data" e "Atrasados" (este quando a coluna é prazo), cor por Status/Lista/grupo e campos de cartão configuráveis (`boards/calendar_view.py`).

---

## 7.4 Formulário de criação

O tipo determina o componente de entrada.

Exemplo:

Pessoas:

```text
Pesquisar pessoa...
```

Data:

```text
Calendário
```

Status:

```text
Lista de etiquetas
```

> **Status (03/10/2026): Não implementado como formulário completo.** O item nasce só com o nome (`ItemService.create`); o Kanban cria o cartão já dentro da raia (preenche a etiqueta) e o Calendário cria no dia clicado (preenche a data), via valores iniciais opcionais (`initial`, até 30). A criação de Demandas é um fluxo próprio, em 4 passos (fora do motor de colunas).

---

## 7.5 Drawer de detalhes

A coluna aparece como campo editável no detalhe do item.

> **Status (03/10/2026): Implementado.** A gaveta do item (`board-item-detail`, `templates/boards/_item_drawer.html`) mostra todas as colunas, editáveis no lugar, o grupo e as últimas 8 mudanças, com link para o histórico completo do quadro.

---

# 8. Coluna Texto

> **Status (03/10/2026): Implementado (parcial nos filtros e no resumo).** Valor em `BoardCell.value_text`, com limite de 5000 caracteres (`MAX_TEXT_LENGTH`), edição inline (clicar, digitar, Enter; Esc cancela), ordenação alfabética sem diferenciar maiúsculas e participação na busca do quadro. Onde: `boards/validators.py`, `templates/boards/_cell.html`.
>
> **Divergência:** o texto longo é cortado com reticências por CSS, mas a célula não mostra tooltip com o valor completo. Os filtros de §8.7 e a contagem de preenchidos de §8.9 não existem. O limite de 5000 caracteres não é configurável (a spec cita "máximo 100 caracteres" como exemplo de validação).

## 8.1 Objetivo

Guardar uma informação textual curta e livre.

Exemplos:

```text
Código externo
Número do pedido
Objeto resumido
Observação curta
Nome complementar
```

---

## 8.2 Armazenamento

String.

---

## 8.3 Edição

Diretamente na célula.

Fluxo:

```text
clicar → digitar → Enter
```

---

## 8.4 Apresentação na Tabela

Texto simples.

Se for muito longo:

```text
Instalação elétrica do ...
```

Tooltip mostra o valor completo.

---

## 8.5 Apresentação no Kanban

Pode aparecer como linha textual.

Evitar mais de duas linhas no cartão.

---

## 8.6 Apresentação no Calendário

Pode aparecer como informação secundária.

Não deve dominar o cartão.

---

## 8.7 Filtros

```text
contém
não contém
é igual a
começa com
termina com
está vazio
não está vazio
```

---

## 8.8 Ordenação

Alfabética.

---

## 8.9 Resumo

Não possui soma ou média.

Pode oferecer contagem de preenchidos.

---

## 8.10 Regra

Texto não deve ser usado para armazenar números que precisam ser calculados.

Errado:

```text
"1500000"
```

para Valor.

Correto:

```text
Moeda = 1.500.000
```

---

# 9. Coluna Número

> **Status (03/10/2026): Parcial.** Valor em `BoardCell.value_number` (decimal 24,6; valor absoluto abaixo de 10^15), edição inline que aceita o formato brasileiro ("1.234,56"), arredondamento `ROUND_HALF_UP` e ordenação numérica feita no banco. Configurações implementadas: `decimal_places` (0 a 6, padrão 2), `unit` (sufixo de até 12 caracteres, ex.: "%"), `minimum` e `maximum`.
>
> **Divergência:** não existem as configurações "Separador" e "Prefixo". Filtros (§9.6) e Fórmulas (§9.9) não existem. O único resumo é a soma opcional no cabeçalho de cada raia do Kanban (`sum_column`); soma, média, mínimo, máximo e contagem na Tabela são futuros.

## 9.1 Objetivo

Guardar valores numéricos calculáveis.

Exemplos:

```text
Quantidade
Probabilidade
Número de lotes
Horas previstas
Pontos
Percentual
```

---

## 9.2 Armazenamento

Número decimal.

---

## 9.3 Edição

Inline.

Aceitar apenas números válidos.

---

## 9.4 Configurações

```text
Casas decimais
Separador
Prefixo
Sufixo
Valor mínimo
Valor máximo
```

Exemplo:

```text
85 %
```

---

## 9.5 Apresentação na Tabela

Formatada conforme configuração.

---

## 9.6 Filtros

```text
igual
diferente
maior que
menor que
maior ou igual
menor ou igual
entre
está vazio
```

---

## 9.7 Ordenação

Numérica.

Nunca lexicográfica.

Correto:

```text
2
10
100
```

e não:

```text
10
100
2
```

---

## 9.8 Resumo

Pode oferecer:

```text
Soma
Média
Mínimo
Máximo
Contagem
```

---

## 9.9 Fórmulas

Pode ser entrada e resultado de Fórmulas.

---

# 10. Coluna Moeda

> **Status (03/10/2026): Parcial.** Tipo explícito `CURRENCY` que compartilha o motor de Número (`value_number`). Configurações: `currency` (`BRL`, `USD` ou `EUR`, com símbolos "R$", "US$" e "€"), `decimal_places`, `minimum`, `maximum`. Exibição como "R$ 1.250.000,00" (`CellService.display_value`). Soma por raia no Kanban.
>
> **Divergência:** "Exibir símbolo" e "Formato" não são configuráveis (o símbolo sempre aparece). Filtros, média, mínimo, máximo e Fórmulas não existem.

## 10.1 Objetivo

Representar valores financeiros.

Exemplos:

```text
Valor da proposta
Custo
Contrato
Saldo
Valor medido
Orçamento
```

---

## 10.2 Base técnica

Pode compartilhar motor com Número, mas deve ser um tipo explícito para o usuário.

---

## 10.3 Configurações

```text
Moeda
Casas decimais
Exibir símbolo
Formato
```

Inicial:

```text
BRL — Real brasileiro
```

BRL significa **Brazilian Real**, código internacional do Real brasileiro.

---

## 10.4 Apresentação

```text
R$ 1.250.000,00
```

---

## 10.5 Filtros

Mesmos de Número.

---

## 10.6 Resumo

```text
Soma
Média
Mínimo
Máximo
```

---

## 10.7 Fórmulas

Pode participar de:

```text
Saldo = Contrato - Medido
```

---

# 11. Coluna Data

> **Status (03/10/2026): Parcial.** Data e Data com hora são a mesma coluna: `value_date` mais `value_datetime` quando `show_time` está ligado. Configurações: `show_time`, `allow_weekends` (recusa sábado e domingo no servidor), `is_deadline` (destaca "vencido" quando a data já passou e alimenta o painel "Atrasados" do Calendário) e `format` (`DD/MM/YYYY`, `DD/MM/YY` ou `YYYY-MM-DD`). Aceita entrada ISO e `dd/mm/aaaa`. Ordenação cronológica e uso como coluna principal do Calendário estão implementados.
>
> **Divergência:** a edição usa um popover com o campo de data nativo do navegador (`date` ou `datetime-local`) e os botões "Hoje" e "Limpar"; não há ícone de relógio para adicionar horário (o horário aparece quando a coluna está configurada com `show_time`). A chave de configuração é `format`, não `date_format`. Os filtros de §11.11 e as Fórmulas de §11.13 não existem. Desligar `show_time` mantém a data (a hora deixa de ser exibida).

## 11.1 Objetivo

Guardar Data e, opcionalmente, horário.

Exemplos:

```text
Prazo
Data de envio
Visita técnica
Data de entrega
Próximo feedback
```

---

## 11.2 Regra central

Data e Data + hora são a mesma família de campo.

Não exigir uma coluna separada para Hora.

---

## 11.3 Configuração

```text
Exibir horário: Sim/Não
Formato da data
Permitir finais de semana
Definir como prazo
```

---

## 11.4 Sem horário

```text
15/10/2026
```

---

## 11.5 Com horário

```text
15/10/2026 14:00
```

---

## 11.6 Edição

Popover contextual com calendário.

O usuário não sai da tela.

---

## 11.7 Adicionar horário

Ícone de relógio.

Ao clicar:

```text
Horário opcional
```

---

## 11.8 Apresentação na Tabela

Compacta.

```text
15/10/2026
```

ou:

```text
15/10/2026 14:00
```

---

## 11.9 Kanban

Pode aparecer como chip:

```text
📅 15/10/2026
```

---

## 11.10 Calendário

Pode ser a coluna que posiciona o item no dia.

---

## 11.11 Filtros

```text
antes de
depois de
entre
hoje
amanhã
esta semana
este mês
atrasado
está vazio
```

---

## 11.12 Ordenação

Cronológica.

---

## 11.13 Fórmulas

Pode participar de cálculos de Data.

Exemplo:

```text
Dias restantes = Prazo - Hoje
```

---

# 12. Coluna Pessoas

> **Status (03/10/2026): Parcial (uma pessoa por célula).** Tipo `PERSON`; o vínculo guarda o usuário (`BoardCellUser.user`), não o nome digitado, e o servidor só aceita usuário ativo da mesma organização (`CellService.set_value`). Seleção por popover com busca (`PersonSearchView`, `/api/pessoas/`, no máximo 20 resultados); a Tabela mostra avatar com iniciais e nome.
>
> **Divergência:** a configuração `multiple` só aceita `false` ("Várias pessoas ficam para uma versão futura"), embora a tabela de vínculos já comporte várias. O filtro é um único seletor "Todas as pessoas" no topo do quadro (pessoas que aparecem em alguma célula de Pessoa), sem os operadores "é Eu", "contém", "não contém" e "está vazio". O agrupamento por Pessoa não existe no Kanban dos quadros dinâmicos (só Status e Lista); existe nos quadros de domínio (`owner`, `responsavel`). A busca não é restrita por setor, apenas por organização.

## 12.1 Objetivo

Relacionar um item a usuários reais da organização.

Não é texto livre.

---

## 12.2 Exemplos

```text
Responsável
Solicitante
Aprovador
Participantes
Supervisor
Engenheiro responsável
```

---

## 12.3 Configuração

```text
Permitir:
- uma pessoa
- várias pessoas
```

---

## 12.4 Uma pessoa

Exemplo:

```text
Responsável
[ PB Paulo Biasi ]
```

---

## 12.5 Várias pessoas

Exemplo:

```text
Participantes
[ Ryan ] [ Luan ] [ Jennifer ]
```

---

## 12.6 Seleção

Popover:

```text
Pesquisar pessoas...

Ryan
Luan
Jennifer
Guilherme
```

---

## 12.7 Regra de identidade

Salvar `user_id`, não o nome digitado.

Se Ryan mudar o nome exibido, o vínculo continua correto.

---

## 12.8 Apresentação na Tabela

Avatar + nome.

Em pouco espaço:

```text
PB
```

ou:

```text
PB Paulo
```

---

## 12.9 Kanban

Pode aparecer como:

```text
PB Paulo
```

ou apenas avatar.

---

## 12.10 Calendário

Pode aparecer de forma compacta.

---

## 12.11 Filtros

```text
é Paulo
contém Ryan
não contém Ryan
é Eu
está vazio
```

---

## 12.12 Agrupamento

Pode agrupar por Pessoa.

Exemplo:

```text
Ryan
Luan
Jennifer
```

---

## 12.13 Permissões

O seletor só deve mostrar pessoas dentro do escopo permitido.

---

## 12.14 Importante

Uma coluna Pessoas não significa automaticamente "Responsável".

O significado é definido pelo nome da coluna e pela regra de negócio.

---

# 13. Coluna Status

> **Status (03/10/2026): Implementado.** As etiquetas ficam em `BoardColumnOption` (id estável, `label`, `color`, `position`, `is_default`, `is_done`, `is_active`), de modo que renomear, recolorir ou reordenar não regrava as células. Edição por popover (lista de etiquetas, "Limpar", "Editar etiquetas"); o diálogo "Editar etiquetas" cria, renomeia, recolore (paleta de 16 cores), reordena (botões ↑ e ↓) e exclui etiquetas, e marca a padrão e a que "conta como concluído". Ordenação pela posição das etiquetas, agrupamento do Kanban e todas as visões refletem a mudança.
>
> **Divergência:** os campos `name`, `order` e `behavior` da spec são `label`, `position` e as marcas `is_default` e `is_done`. O popover da célula não tem "+ Nova etiqueta" (a criação é no diálogo de etiquetas). Etiqueta repetida na mesma coluna é recusada (sem diferenciar maiúsculas). Excluir uma etiqueta esvazia as células que a usavam, após confirmação. Os filtros de §13.9 não existem. **Cuidado arquitetural (§13.12):** o Status de quadro é configurável e independente de `Activity.condition`/`Activity.stage` e de `Task.status`; `is_done` só influencia o Calendário (ocultar concluídos e calcular atrasados) e não altera nenhum estado operacional.

## 13.1 Objetivo

Representar estado ou etapa de fluxo.

Exemplos:

```text
Não iniciado
Em andamento
Aguardando cliente
Em revisão
Concluído
```

---

## 13.2 Estrutura

Cada opção deve possuir:

```text
id
name
color
order
is_active
behavior opcional
```

---

## 13.3 Identidade estável

O ID nunca muda ao renomear.

Exemplo:

```text
id = 42
nome = Working on it
```

usuário altera:

```text
nome = Trabalhando nisso
```

continua:

```text
id = 42
```

---

## 13.4 Cor

A cor pertence à opção.

Alterar a cor deve atualizar todas as visualizações.

---

## 13.5 Edição

Clique na célula.

Popover:

```text
Trabalhando nisso
Parado
Concluído
+ Nova etiqueta
Editar etiquetas
```

---

## 13.6 Renomear

Pode ser feito sem sair da tela.

---

## 13.7 Alterar cor

Paleta visual inline.

---

## 13.8 Ordenação

Por ordem configurada das opções.

Não alfabeticamente.

---

## 13.9 Filtro

```text
é
não é
está em
não está em
está vazio
```

---

## 13.10 Agrupamento

É um dos principais tipos para agrupar Tabela e Kanban.

---

## 13.11 Kanban

Pode ser usado como coluna de agrupamento.

Mover um cartão entre grupos altera o valor da coluna Status configurada para aquele Kanban.

---

## 13.12 Cuidado arquitetural

Status visual configurável e estado de negócio crítico não devem ser confundidos sem uma regra explícita.

---

# 14. Coluna Lista suspensa

> **Status (03/10/2026): Parcial (seleção única).** Tipo `DROPDOWN`, com as mesmas etiquetas de Status (`BoardColumnOption`), edição por popover, ordenação pela posição, agrupamento no Kanban e uso para colorir o Calendário.
>
> **Divergência:** a seleção múltipla (§14.3) não existe; a célula guarda uma única etiqueta. Na Tabela a opção aparece como etiqueta colorida (pílula), a mesma de Status, e não como vários chips. Uma Lista nova nasce sem etiquetas (só Status recebe as três etiquetas iniciais). Os filtros de §14.6 não existem.

## 14.1 Objetivo

Classificar itens em opções configuráveis que não necessariamente representam fluxo.

Exemplos:

```text
Disciplina
Tipo de orçamento
Região
Categoria
Modalidade
Tipo de contrato
```

---

## 14.2 Diferença para Status

Status:

```text
Não iniciado → Em andamento → Concluído
```

Lista:

```text
Elétrica
Hidráulica
Mecânica
Civil
```

A Lista não exige uma sequência de progresso.

---

## 14.3 Configuração

Pode permitir:

```text
seleção única
seleção múltipla
```

---

## 14.4 Edição

Popover com opções.

---

## 14.5 Apresentação

Chips.

Exemplo:

```text
[ Elétrica ]
```

ou:

```text
[ Elétrica ] [ Dados ] [ SDAI ]
```

SDAI significa **Sistema de Detecção e Alarme de Incêndio**.

---

## 14.6 Filtros

```text
contém
não contém
é
não é
está vazio
```

---

## 14.7 Agrupamento

Permitido.

---

# 15. Coluna Prioridade

> **Status (03/10/2026): Não implementado como coluna de quadro dinâmico.** `PRIORITY` está reservado em `BoardColumn.Type` e não pode ser criado.
>
> **Divergência:** Prioridade existe apenas como **campo de sistema** do quadro de domínio: `urgency` na Demanda (`Activity.Urgency`) e `priority` na Tarefa (`Task.Priority`), ambos com os valores Baixa, Média e Alta (não há "Crítica"), cores configuráveis por organização (`core.colors.EnumColorResolver`), edição inline pelos services e agrupamento. Prioridade padrão, ordem semântica por coluna e filtros próprios não existem no motor de colunas.

## 15.1 Objetivo

Representar importância relativa para decisão e organização do trabalho.

---

## 15.2 Valores iniciais

```text
Alta
Média
Baixa
```

Pode existir:

```text
Crítica
```

se houver necessidade real.

Evitar dez níveis.

---

## 15.3 Apresentação

Chip com ícone e cor.

```text
🔴 Alta
🟣 Média
🔵 Baixa
```

A interface não deve depender só da cor.

---

## 15.4 Ordenação

Ordem semântica:

```text
Crítica
Alta
Média
Baixa
```

---

## 15.5 Filtros

```text
é
não é
está em
está vazio
```

---

## 15.6 Agrupamento

Permitido.

---

## 15.7 Regra

Prioridade não deve virar mecanismo de pressão indiscriminada.

Se tudo for Alta, a coluna perde valor.

---

# 16. Coluna Confirmação

> **Status (03/10/2026): Implementado (como `CHECKBOX`).** Rótulo "Sinal de confirmação"; nome inicial "Confirmação". Valor em `BoardCell.value_boolean` com três estados (sem resposta, sim, não); um clique ou a barra de espaço alterna; ordenação implementada.
>
> **Divergência:** o identificador é `CHECKBOX`, não `CONFIRMATION` (reservado). Os filtros "marcado" e "não marcado" e o uso em Fórmula não existem.

## 16.1 Objetivo

Guardar estado binário.

Exemplo:

```text
Sim / Não
Feito / Não feito
Confirmado / Não confirmado
```

---

## 16.2 Apresentação

Checkbox ou ícone.

```text
☐
☑
```

---

## 16.3 Exemplos

```text
Visita realizada
Projeto recebido
Cliente respondeu
Contrato assinado
```

---

## 16.4 Filtro

```text
marcado
não marcado
```

---

## 16.5 Ordenação

Marcados e não marcados.

---

## 16.6 Fórmula

Pode ser usada como condição booleana.

Booleana significa uma informação com dois estados lógicos: verdadeiro ou falso.

---

## 16.7 Regra

Não usar Confirmação para substituir um fluxo complexo.

Se existem cinco estados, usar Status.

---

# 17. Coluna Arquivo

> **Status (03/10/2026): Não implementado.** `FILE` está reservado em `BoardColumn.Type`, sem criação, upload, painel de anexos nem download. Todo o conteúdo abaixo é requisito futuro.

## 17.1 Objetivo

Associar documentos ao item.

---

## 17.2 Exemplos

```text
Projeto
Memorial
Proposta
Foto
Planilha
PDF
Contrato
```

---

## 17.3 Apresentação na Tabela

```text
📎 4 arquivos
```

ou chips compactos.

---

## 17.4 Ao clicar

Abrir painel contextual.

Não redirecionar para uma página genérica de arquivos.

---

## 17.5 Configuração

Pode aceitar:

```text
um arquivo
vários arquivos
tipos permitidos
tamanho máximo
```

---

## 17.6 Segurança

Download deve respeitar:

- login;
- organização;
- autorização do recurso.

Não servir arquivos por URL pública sem validação.

---

## 17.7 Filtro

Inicialmente:

```text
tem arquivo
não tem arquivo
```

---

## 17.8 Ordenação

Pode ordenar por quantidade ou presença.

---

# 18. Coluna Relação

> **Status (03/10/2026): Não implementado em quadros dinâmicos.** `RELATION` está reservado em `BoardColumn.Type`. Todo o conteúdo abaixo é requisito futuro, com uma exceção no quadro de domínio: o campo de sistema `activity` ("Demanda vinculada") do quadro de Tarefas é do tipo `RELATION`, guarda o vínculo real (`Task.activity`) e é **somente leitura**. `sector` é um campo de sistema do tipo `SECTOR`, editável pelos services. Cliente, Obra e Centro de custo existem em `Activity` (`client`, `site`, `cost_center`), mas não são campos do quadro.

## 18.1 Objetivo

Relacionar um item a outro registro real.

---

## 18.2 Exemplos

```text
Setor
Cliente
Obra
Centro de custo
Demanda vinculada
Fornecedor
Contrato
Pedido
```

---

## 18.3 Regra central

Não armazenar apenas o texto mostrado.

Armazenar o ID do objeto relacionado.

---

## 18.4 Exemplo

```text
Demanda vinculada:
Arena Center Norte
```

internamente:

```text
activity_id = 381
```

---

## 18.5 Tipos de relação

Primeira versão:

```text
1 para 1 lógico
1 para vários
vários para vários
```

A escolha depende da configuração.

---

## 18.6 Seleção

Popover com busca.

Exemplo:

```text
Pesquisar obra...

Arena Center Norte
Ascenty Sumaré
Santa Isabel
```

---

## 18.7 Apresentação

Nome do objeto relacionado.

Pode possuir ícone do tipo.

---

## 18.8 Clique

Abre o drawer do objeto relacionado.

Evitar navegação completa.

---

## 18.9 Filtro

Por objeto relacionado.

---

## 18.10 Agrupamento

Permitido para relações categóricas.

Exemplo:

```text
agrupar por Setor
```

---

## 18.11 Colunas especializadas construídas sobre Relação

```text
Setor
Cliente
Obra
Centro de custo
Demanda vinculada
Processo
```

Não criar um tipo primitivo diferente para cada uma.

---

# 19. Coluna Cronograma

> **Status (03/10/2026): Não implementado.** `TIMELINE` está reservado em `BoardColumn.Type`. O Calendário usa apenas colunas de Data (`DATE_TYPES = (DATE,)`). Todo o conteúdo abaixo é requisito futuro.

## 19.1 Objetivo

Guardar um intervalo temporal com início e fim.

---

## 19.2 Exemplo

```text
10/10/2026 → 18/10/2026
```

---

## 19.3 Diferença para Data

Data:

```text
Entrega: 18/10
```

Cronograma:

```text
Execução: 10/10 → 18/10
```

---

## 19.4 Apresentação na Tabela

Barra ou texto compacto.

```text
10/10 → 18/10
```

---

## 19.5 Linha do tempo

Pode alimentar visualização futura de Linha do tempo.

---

## 19.6 Gantt

Pode alimentar visualização futura de Gantt.

Gantt é uma visualização de planejamento em barras horizontais distribuídas ao longo do tempo.

---

## 19.7 Filtros

```text
inicia antes de
inicia depois de
termina antes de
termina depois de
sobrepõe período
```

---

## 19.8 Regra

Cronograma de processo da LPS não deve tentar substituir ferramentas completas de planejamento de obra, como Microsoft Project, sem um objetivo claro.

---

# 20. Coluna Fórmula

> **Status (03/10/2026): Não implementado.** `FORMULA` está reservado em `BoardColumn.Type`. Não há motor de cálculo, referência por id, detecção de ciclos nem tratamento de erros. O mais próximo é o campo de sistema somente leitura "Tarefas"/"Checklist" (`CHECKLIST`) do quadro de domínio, que exibe "feitas/total" com barra de progresso. Todo o conteúdo abaixo é requisito futuro.

## 20.1 Objetivo

Calcular um valor automaticamente a partir de outras colunas.

O usuário não digita o resultado.

---

## 20.2 Exemplos

Margem:

```text
(Valor - Custo) / Valor
```

Saldo:

```text
Contrato - Medido
```

Valor total:

```text
Quantidade * Preço unitário
```

Dias restantes:

```text
Prazo - Hoje
```

Percentual:

```text
Concluídas / Total
```

---

## 20.3 Regra principal

> Fórmula é somente leitura.

O usuário altera as entradas.

O resultado é recalculado.

---

## 20.4 Não é automação

Fórmula:

```text
calcula valor
```

Automação:

```text
executa ação
```

Fórmula não deve:

- criar tarefa;
- alterar Status;
- enviar notificação;
- trocar responsável;
- apagar registro.

---

## 20.5 Configuração

Exemplo:

```text
Fórmula:
[ Quantidade ] * [ Preço unitário ]

Resultado:
[ Moeda ]
```

---

## 20.6 Tipos de resultado

```text
Número
Moeda
Percentual
Texto
Data
Duração
Booleano
```

Booleano significa verdadeiro ou falso.

---

## 20.7 Apresentação na Tabela

Mesmo padrão do tipo resultante.

---

## 20.8 Kanban

Pode aparecer como informação do cartão.

---

## 20.9 Calendário

Pode aparecer no cartão, mas não deve posicionar o item se o resultado não for Data.

---

## 20.10 Filtros

Dependem do tipo resultante.

---

## 20.11 Ordenação

Depende do tipo resultante.

---

## 20.12 Agrupamento

Somente se o resultado for categórico e a operação for suportada.

---

## 20.13 Dependências

Se a Fórmula usa:

```text
Valor
Custo
```

essas colunas não podem ser excluídas silenciosamente.

---

## 20.14 Referência por ID

Internamente:

```text
column_id_41 - column_id_52
```

Não:

```text
"Valor" - "Custo"
```

Assim renomear uma coluna não quebra a Fórmula.

---

## 20.15 Ciclos

Bloquear:

```text
A = B + 1
B = A + 1
```

Isso é uma dependência circular.

---

## 20.16 Erros

Exibir erro compreensível:

```text
#DIV/0
```

pode ser apresentado ao usuário como:

```text
Não foi possível calcular: divisão por zero.
```

---

# 21. Campos de negócio da LPS

Abaixo, como os principais campos da LPS atual devem ser representados no novo motor.

| Campo de negócio | Tipo-base |
|---|---|
| Título | Texto |
| Responsável | Pessoas |
| Solicitante | Pessoas |
| Participantes | Pessoas |
| Status | Status |
| Prioridade/Urgência | Prioridade |
| Setor | Relação |
| Cliente | Relação |
| Obra | Relação |
| Centro de custo | Relação |
| Demanda vinculada | Relação |
| Prazo | Data |
| Prazo solicitado | Data |
| Prazo comprometido | Data |
| Valor | Moeda |
| Quantidade | Número |
| Probabilidade | Número |
| Disciplina | Lista suspensa |
| Tags | Lista suspensa ou tipo Tag especializado |
| Projeto recebido | Confirmação |
| Arquivos | Arquivo |
| Período de execução | Cronograma |
| Margem | Fórmula |

> **Divergência (03/10/2026):** os campos de sistema do quadro de domínio têm tipos próprios, não os tipos-base acima. Estado atual:
>
> - Título: `title` (`TEXT`).
> - Responsável: `owner` na Demanda e `responsavel` na Tarefa (`PERSON`, editável).
> - Setor: `sector` (`SECTOR`, editável).
> - Etapa: `stage` (`STAGE`); Status: `condition` (`SELECT`); ambos por setor.
> - Prioridade/Urgência: `urgency` (Demanda) e `priority` (Tarefa), ver §15.
> - Prazo solicitado: `requested_deadline`, do tipo `DATETIME` (data e hora), e não Data.
> - Demanda vinculada: `activity` (`RELATION`, somente leitura).
> - Tarefas/Checklist: `tasks` e `checklist` (`CHECKLIST`, somente leitura).
> - **Não expostos como campos do quadro:** Solicitante (`Activity.requested_by`), Participantes, Cliente, Obra, Centro de custo, Prazo comprometido (`Task.committed_deadline`), Tags, Arquivos, Período de execução e Margem.
>
> Valor, Quantidade, Probabilidade, Disciplina e Projeto recebido podem existir como **colunas de um quadro dinâmico** (por exemplo, o modelo "Orçamentos") ou como campos customizados do quadro de domínio, criados em "Novo campo" (`WorkBoardFieldCreateView`: `TEXT`, `NUMBER`, `CURRENCY`, `DATETIME`, `SELECT`, `BOOLEAN`). No quadro de domínio, o valor customizado fica em `DomainCustomValue` e é editado como texto ou data e hora; o cadastro de opções para campos `SELECT` não tem tela (`DomainBoardChoice` só aparece no admin, somente leitura).

---

# 22. Demandas — conjunto inicial sugerido

Template inicial:

```text
Título
Solicitante
Responsável
Setor
Cliente
Obra
Status
Prioridade
Prazo
```

Extras:

```text
Valor
Probabilidade
Disciplina
Visita técnica
Arquivos
```

> **Status (03/10/2026): Parcial.** O quadro de domínio de Demandas nasce (`ensure_domain_board`, sob demanda e idempotente) com: Título da demanda, Responsável, Setor, Prioridade, Prazo (`requested_deadline`), Status (`stage`), Status (`condition`) e Tarefas. Não há Solicitante, Cliente nem Obra, e os "extras" sugeridos (Valor, Probabilidade, Disciplina, Visita técnica, Arquivos) só existem se forem criados à mão ou vierem do modelo de quadro "Orçamentos" (`boards/starter_templates.py`: Cliente, Responsável, Setor, Prazo, Status com 9 etiquetas, Valor, Probabilidade de 0 a 100 %, Pendência e Visita técnica; 4 grupos e o Kanban "Kanban por Status").
>
> **Divergência:** em `boards/domain_defaults.py` o rótulo do campo `stage` ainda é "Status", o mesmo de `condition`, embora pelo vocabulário atual `stage` seja **Etapa**. Isso produz duas colunas chamadas "Status" (ver §52). A confirmar se é intencional.

---

# 23. Tarefas — conjunto inicial sugerido

Template inicial:

```text
Título
Demanda vinculada
Responsável
Setor
Status
Prioridade
Prazo solicitado
Prazo comprometido
```

Extras:

```text
Participantes
Checklist
Arquivos
Cronograma
```

Checklist pode permanecer inicialmente como recurso especializado de Tarefa e não como tipo de coluna-base.

> **Status (03/10/2026): Parcial.** O quadro de domínio de Tarefas nasce com Título da tarefa, Demanda vinculada, Responsável, Setor, Prioridade, Prazo (`requested_deadline`), Status (`stage`) e Checklist. Faltam Prazo comprometido, Participantes, Arquivos e Cronograma. O Checklist permanece como recurso especializado de Tarefa, como a spec sugere.
>
> **Divergência:** além do quadro de domínio, **cada Demanda possui o seu próprio quadro de tarefas** (`Board` com `kind="DEMAND"`, ligado a `Activity`, criado em branco ou copiado de um modelo por `BoardInstantiationService`). Em branco, ele recebe as colunas Responsável (Pessoa), Status (3 etiquetas) e Data, além das visões Kanban e Calendário. Esse quadro usa as colunas dinâmicas da §5 em diante; o acesso segue `DemandBoardAccess` (dono, criador ou participante da Demanda).

---

# 24. Coluna obrigatória

Uma coluna pode ser configurada como obrigatória.

Exemplo:

```text
Responsável: obrigatório
```

Na criação:

```text
Não é possível criar a tarefa sem Responsável.
```

Não permitir item inválido silenciosamente.

> **Divergência (03/10/2026): Parcial.** `BoardColumn.is_required` é configurável ("Valor obrigatório" nas configurações da coluna). O servidor recusa **limpar** uma célula obrigatória ("“<coluna>” é obrigatória") e a tela esconde o botão "Limpar". Mas o item é criado só com o nome (`ItemService.create`), sem checar colunas obrigatórias; portanto "Não é possível criar a tarefa sem Responsável" **não** é atendido hoje.

---

# 25. Valor padrão

Alguns tipos podem ter valor padrão.

Exemplo:

```text
Status padrão = Não iniciado
Prioridade padrão = Média
```

Não preencher valores como Responsável automaticamente sem regra explícita.

> **Status (03/10/2026): Parcial.** Só existe a etiqueta padrão (`BoardColumnOption.is_default`) de Status e Lista, aplicada automaticamente a cada item novo (`ItemService.create`); o Status inicial é "Não iniciado". Os demais tipos não têm valor padrão, e Prioridade padrão não se aplica (tipo não implementado). Nenhum valor de Pessoa é preenchido sem regra explícita.

---

# 26. Validações

Toda coluna deve aceitar regras de validação compatíveis.

Exemplos:

Número:

```text
mínimo 0
máximo 100
```

Data:

```text
não permitir data anterior a hoje
```

Texto:

```text
máximo 100 caracteres
```

Relação:

```text
somente Obras ativas
```

> **Status (03/10/2026): Parcial.** Validação sempre no servidor (`normalize_cell_value`): mínimo e máximo em Número e Moeda, casas decimais, bloqueio de fins de semana em Data, etiqueta ativa da própria coluna, pessoa da organização. Divergências: o limite de Texto é fixo (5000), "não permitir data anterior a hoje" não existe e a validação de Relação ("somente Obras ativas") é futura.

---

# 27. Resumo de coluna

A Tabela pode mostrar resumo na parte inferior.

Número:

```text
Soma: 1.250
```

Moeda:

```text
Total: R$ 4.820.000
```

Status:

```text
3 Em andamento
5 Concluídos
```

Pessoas:

```text
5 pessoas
```

Data:

```text
Mais próxima: 05/10
```

Não forçar resumo onde não fizer sentido.

> **Status (03/10/2026): Parcial.** Não há linha de resumo no rodapé da Tabela. Existem apenas: contagem de itens por grupo e por raia, e a soma de uma coluna de Número ou Moeda no cabeçalho de cada raia do Kanban (`build_lanes`, `format_total`). Distribuição de Status, "Mais próxima" em Data e demais resumos são futuros.

---

# 28. Colunas em visualizações

A configuração do Quadro define quais colunas existem.

Cada visualização define quais aparecem.

Exemplo:

Quadro:

```text
15 colunas
```

Tabela Comercial:

```text
9 visíveis
```

Kanban Gerencial:

```text
5 campos no cartão
```

Calendário:

```text
4 campos no cartão
```

Não duplicar coluna.

> **Divergência (03/10/2026):** no quadro dinâmico, a existência, a ordem, a largura e a visibilidade das colunas são do Quadro e valem para a Tabela; Kanban e Calendário escolhem seus campos de cartão por visualização (`BoardView.settings["card_fields"]`), sem duplicar coluna. Não há visões de Tabela com subconjuntos próprios (como "Tabela Comercial"). No quadro de domínio, largura, ordem e visibilidade são por visualização (`DomainBoardViewColumn`, `DomainBoardCardField`).

---

# 29. Configuração do cartão

Kanban e Calendário devem permitir:

```text
Clique ou arraste os campos que deseja mostrar.
```

Exemplo:

```text
Status
Responsável
Prazo
Valor
```

A ordem deve ser alterável por arrastar.

> **Status (03/10/2026): Implementado, com diferenças.** O diálogo "Configurar cartões" permite marcar os campos e ordená-los, com pré-visualização do cartão. Divergência: a ordem é alterada pelos botões ↑ e ↓, não por arrastar. Limites: Kanban com até 12 campos (padrão 4, `MAX_CARD_FIELDS`); Calendário com até 6 (padrão 3), além da opção "Mostrar o nome de cada campo" no Kanban. No quadro de domínio: `WorkBoardCardFieldsView`.

---

# 30. Edição contextual

Regra global:

> Se o valor puder ser editado no local em que está sendo visto, não abrir outra página.

Exemplos:

Status:

```text
clicar → escolher etiqueta
```

Pessoa:

```text
clicar → pesquisar pessoa
```

Data:

```text
clicar → calendário
```

Prioridade:

```text
clicar → escolher prioridade
```

Texto:

```text
clicar → digitar
```

> **Status (03/10/2026): Implementado.** Os 8 tipos são editados no lugar (Tabela, cartão do Kanban, cartão do Calendário e gaveta) pelo mesmo editor (`openCellEditor`); a gravação é otimista, com desfazer visual se o servidor recusar. Prioridade e Relação não se aplicam (tipos não implementados).

---

# 31. Popovers

Tipos indicados para popover:

```text
Pessoas
Status
Lista suspensa
Prioridade
Data
Relação
Confirmação
```

> **Status (03/10/2026): Parcial.** Usam popover: Pessoa, Status, Lista suspensa e Data. Confirmação alterna ao clique, sem popover. Prioridade e Relação não existem.

---

# 32. Modal ou drawer

Usar para:

- configuração avançada da coluna;
- criação completa de item;
- detalhes completos;
- arquivos;
- Fórmula complexa;
- permissões;
- histórico.

> **Status (03/10/2026): Parcial.** Existem o diálogo de configuração da coluna, o diálogo de etiquetas, a gaveta de detalhes do item e o histórico completo do quadro (`board-history`, 50 por página). Arquivos, Fórmula complexa e permissões por coluna são futuros.

---

# 33. Segurança

Colunas não podem ignorar a autorização da LPS.

Exemplo:

Se o usuário pode ver a Demanda, mas não editar:

```text
célula visível
edição bloqueada
```

> **Status (03/10/2026): Implementado.** Toda gravação passa por `_require` em `boards/services.py`, com as ações do catálogo `QUADRO_VISUALIZAR`, `QUADRO_EDITAR`, `QUADRO_EXCLUIR`, `QUADRO_GERIR_COLUNAS`, `QUADRO_CRIAR_ITEM`, `QUADRO_EDITAR_ITEM` e `QUADRO_EXCLUIR_ITEM` (negação = 403). Quem não pode editar vê a célula sem o comportamento de edição (`permissions.edit_item`), e o servidor confere de novo. Quadros de Demanda (`kind="DEMAND"`) somam a regra relacional de `DemandBoardAccess`. No quadro de domínio, a edição de cada campo exige a permissão do serviço de `activities` correspondente.

---

# 34. Restrição de visualização

Futuro:

```text
Esta coluna pode ser vista por:
- gestores
- financeiro
```

Isso exige cuidado porque filtros, Fórmulas e exportações também precisam respeitar a restrição.

Não implementar apenas escondendo no HTML.

> **Status (03/10/2026): Não implementado.** Não há restrição de visualização por coluna; é requisito futuro.

---

# 35. Restrição de edição

Exemplo:

```text
Valor final
Visualização: Comercial + Diretoria
Edição: Diretoria
```

A validação real deve ocorrer no servidor.

> **Status (03/10/2026): Não implementado.** A edição é controlada por quadro (permissões `QUADRO_*`), não por coluna.

---

# 36. Multi-organização

Pessoas, Relações, Status e opções devem sempre respeitar a organização do Quadro.

Não permitir selecionar:

- pessoa de outra empresa;
- obra de outra organização;
- cliente de outro tenant;
- status pertencente a outro tenant.

Tenant significa a organização isolada dentro de uma aplicação multiempresa.

> **Status (03/10/2026): Implementado.** Quadro, grupo, coluna, etiqueta, visão e item são carregados sempre pela organização da pessoa (`get_board`, `get_column` etc. em `boards/views.py`; outra organização = 404). A pessoa de uma célula precisa ser usuária ativa da organização do quadro; a etiqueta precisa ser ativa e da própria coluna. Relações entre organizações não se aplicam (tipo não implementado).

---

# 37. Auditoria

Mudanças relevantes em colunas de negócio devem ser auditáveis.

Exemplos:

```text
Responsável alterado
Prazo alterado
Status alterado
Prioridade alterada
Cliente alterado
Obra alterada
```

> **Status (03/10/2026): Implementado.** `_audit` grava em `AuditLog` com `metadata["board_id"]`: criação, renomeação, movimento, largura, ocultação, troca de tipo, alterações de etiqueta e cada mudança de célula (valor antigo e novo, como a tela mostra). O histórico fica em `board-history` e na gaveta do item (`BoardQueryService.history`, `item_history`).

---

# 38. Alterações visuais

Mudanças exclusivamente visuais podem possuir auditoria simplificada.

Exemplos:

```text
largura
posição
visibilidade na view
```

Não precisam gerar notificação de negócio.

> **Divergência (03/10/2026):** não há uma categoria de "auditoria simplificada": largura, posição e visibilidade de coluna também geram registros no histórico do quadro (`BOARD_COLUMN_RESIZED`, `BOARD_COLUMN_MOVED`, `BOARD_COLUMN_UPDATED`), sem notificação.

---

# 39. Notificações

Editar uma coluna não significa automaticamente notificar alguém.

Notificação é regra de negócio.

Exemplos que podem notificar:

```text
troca de Responsável
prazo alterado
Status crítico
```

Exemplos que não devem:

```text
largura aumentada
coluna movida
coluna ocultada
```

> **Status (03/10/2026): Não implementado para colunas de quadro.** `boards/services.py` não dispara notificações ao editar célula, e mudanças visuais nunca notificam (conforme a spec). No quadro de domínio, mudanças de responsável e prazo passam pelos services de `activities`, cuja notificação não foi verificada aqui.

---

# 40. Fórmulas e permissões

Uma Fórmula não deve revelar informação de uma coluna que o usuário não possui autorização para enxergar.

Esse ponto exige desenho técnico antes de habilitar restrição por coluna.

> **Status (03/10/2026): Não aplicável hoje.** Sem Fórmulas e sem restrição de visualização por coluna.

---

# 41. Valores vazios

Cada tipo precisa possuir representação visual limpa.

Exemplo:

```text
—
```

ou célula vazia.

Não usar:

```text
null
None
undefined
```

na interface.

> **Status (03/10/2026): Parcial.** Os templates nunca exibem `None`, `null` ou `undefined`. Status vazio mostra "—"; Lista, Texto, Número, Data e Moeda vazios mostram a célula em branco; Pessoa vazia mostra um avatar vazio; Confirmação sem resposta mostra a caixa vazia (`templates/boards/_cell.html`).

---

# 42. Campo vazio e filtro

Todos os tipos devem suportar:

```text
está vazio
não está vazio
```

quando fizer sentido.

> **Status (03/10/2026): Não implementado**, pois não há filtros por coluna (ver §6.7).

---

# 43. Cópia e cola

Evolução desejável para a Tabela:

```text
Ctrl+C
Ctrl+V
```

com validação por tipo.

Não permitir colar texto inválido em Número sem aviso.

> **Status (03/10/2026): Não implementado** (Ctrl+C e Ctrl+V). Existe navegação por setas, edição com Enter ou F2 e limpeza com Delete ou Backspace.

---

# 44. Exportação

Valores exportados devem manter o significado.

Exemplo:

Pessoas:

```text
Paulo Biasi
```

e não:

```text
user_id=42
```

Moeda:

```text
1250000.00
```

mais formatação conforme formato de exportação.

> **Status (03/10/2026): Não implementado.** Não há endpoint de exportação nos quadros.

---

# 45. Pesquisa global

A pesquisa pode indexar:

```text
Texto
Status
Lista
Pessoas
Relações
```

Número, Data e Fórmula podem entrar de forma específica.

> **Status (03/10/2026): Parcial.** A busca do quadro (`BoardQueryService.search_filter`) cobre o nome do item, o texto das colunas de Texto, os rótulos das etiquetas (Status e Lista) e o nome e usuário das pessoas. Número, Data e Moeda não entram na busca. Não existe pesquisa global entre quadros.

---

# 46. Campos não editáveis

Algumas colunas podem ser somente leitura.

Exemplos:

```text
Código da Demanda
Criado em
Criado por
Última atualização
Margem calculada
Dias em atraso
```

Esses campos podem usar tipos-base, mas com `editable = false`.

> **Status (03/10/2026): Parcial.** Nos quadros dinâmicos não há colunas somente leitura. No quadro de domínio, `activity` (Demanda vinculada) e `tasks`/`checklist` são somente leitura (`editable=False` em `build_cells`), e campos de sistema sem regra de gravação são recusados ("Este campo não pode ser editado diretamente").

---

# 47. Colunas de sistema

Além das 13 colunas-base, o sistema pode expor campos técnicos:

```text
ID
Código
Criado em
Criado por
Atualizado em
```

Eles não devem aparecer no seletor principal de criação como colunas comuns, salvo em uma área:

```text
Campos do sistema
```

> **Status (03/10/2026): Parcial.** `DomainBoardField.is_system` marca os campos de sistema do quadro de domínio. ID, Código, Criado em, Criado por e Atualizado em não são oferecidos como colunas, e não existe a área "Campos do sistema" no seletor.

---

# 48. Colunas futuras

Não fazem parte da primeira versão obrigatória:

```text
E-mail
Telefone
Localização
Link
Avaliação
Dependência
Progresso
Espelhamento
Documento rico
Extração por IA
```

IA significa **Inteligência Artificial**.

Esses tipos podem ser adicionados depois sem quebrar o motor central.

> **Status (03/10/2026): Nenhuma implementada**, como previsto. Só `AI_EXTRACT` está reservado em `BoardColumn.Type`.

---

# 49. Extração por IA

A opção "Extract info" vista no Monday não deve ser copiada como tipo-base agora.

Na LPS, isso deve ser uma capacidade futura:

```text
Extrair valor de documento
Extrair CNPJ
Extrair prazo
Extrair valor contratual
```

Pode preencher outras colunas.

Não deve ser confundida com Fórmula.

> **Status (03/10/2026): Não implementado.** Apenas o valor reservado `AI_EXTRACT`; sem extração de documentos.

---

# 50. Documento

A opção "monday Doc" também não é coluna-base da primeira versão da LPS.

Documento rico pode ser um recurso futuro.

> **Status (03/10/2026): Não implementado**, como previsto.

---

# 51. Regras de nomes

Evitar nomes genéricos:

```text
Campo 1
Campo 2
Info
Outro
```

Preferir:

```text
Prazo de entrega
Responsável
Valor da proposta
Setor responsável
```

> **Status (03/10/2026): Parcial.** Cada tipo nasce com um nome descritivo (§6.1), mas o sistema não valida nomes genéricos.

---

# 52. Duplicidade de nomes

O sistema pode permitir duas colunas visualmente iguais, mas isso gera confusão.

Recomendação:

```text
Status comercial
Status operacional
```

em vez de:

```text
Status
Status
```

> **Divergência (03/10/2026):** a criação e a duplicação de coluna evitam repetição ("Status 2", "<nome> (cópia)", em `ColumnService._unique_name`), mas **renomear aceita nome repetido** (`ColumnService.rename` não valida). Além disso, no quadro de domínio de Demandas os campos `stage` e `condition` têm hoje o mesmo rótulo "Status" (ver §22).

---

# 53. Dependências de exclusão

Antes de excluir uma coluna, verificar:

- Fórmulas;
- filtros;
- agrupamentos;
- automações;
- visualizações;
- relatórios;
- integrações.

> **Status (03/10/2026): Não implementado.** `ColumnService.soft_delete` não consulta Fórmulas, filtros, visualizações, relatórios ou integrações (ver §6.13).

---

# 54. Soft delete

Soft delete significa exclusão lógica, mantendo o registro técnico e histórico.

Para colunas já utilizadas, preferir:

```text
is_active = false
```

em vez de apagamento físico imediato.

> **Status (03/10/2026): Implementado.** Colunas, etiquetas, grupos, itens, visões e quadros usam `is_active=False`; `BoardCell.column` é `PROTECT`, então o banco impede apagar fisicamente uma coluna com valores.

---

# 55. Performance

A Tabela pode possuir muitas colunas.

Regras:

- carregar apenas valores necessários;
- evitar consulta por célula;
- usar pré-carregamento de Pessoas e Relações;
- calcular Fórmulas de forma eficiente;
- indexar campos de busca e filtros mais usados.

> **Status (03/10/2026): Implementado (sem Fórmulas).** Leitura sem consulta por célula (`BoardQueryService.with_cells` e `attach_cells`), ordenação em subconsulta no banco e índices em `BoardCell` por coluna e valor numérico, de data e booleano. O Calendário busca só o intervalo da grade do mês.

---

# 56. Responsividade

No desktop:

- arrastar;
- redimensionar;
- edição inline.

No mobile:

- priorizar as colunas selecionadas;
- permitir scroll horizontal;
- abrir popovers como drawers;
- evitar células minúsculas.

> **Status (03/10/2026): Parcial.** A Tabela tem rolagem horizontal e há regras `@media` para telas de até 720 e 760 px em `static/css/boards.css`; arrastar, redimensionar e editar inline funcionam no desktop. A abertura de popovers como gavetas no celular não foi verificada.

---

# 57. Acessibilidade

Nunca usar apenas cor.

Status deve mostrar:

```text
● Em andamento
```

e não apenas um quadrado azul.

Pessoas devem ter nome acessível mesmo com avatar.

> **Status (03/10/2026): Parcial.** Etiquetas sempre mostram o texto (nunca só cor); a Confirmação tem texto para leitor de tela ("Sim", "Não", "Sem resposta"); Pessoa mostra nome ao lado do avatar; cabeçalhos ordenados têm `aria-sort`; menus e diálogos têm `aria-label`. O marcador "●" na etiqueta de Status não existe (a cor vai no fundo da etiqueta).

---

# 58. Teclado

Comportamentos desejados:

```text
Enter  = editar/confirmar
Esc    = cancelar/fechar
Tab    = próxima célula
Shift+Tab = célula anterior
```

> **Status (03/10/2026): Parcial.** Enter ou F2 abrem a edição, Esc cancela e fecha, Tab confirma a edição inline, as setas movem o foco entre células, Delete e Backspace limpam, e a barra de espaço alterna a Confirmação. O avanço para a próxima célula com Tab e Shift+Tab não foi verificado (a edição inline apenas confirma). A divisória de coluna é redimensionável por teclado.

---

# 59. Regra de UX

UX significa **User Experience**, ou experiência do usuário.

A regra central da LPS:

> O usuário clica na informação que quer mudar e altera ali.

Não:

```text
clicar
abrir tela
procurar formulário
editar
salvar
voltar
```

Mas:

```text
clicar
alterar
pronto
```

> **Status (03/10/2026): Implementado** para os 8 tipos de coluna e para colunas, etiquetas e grupos.

---

# 60. Regra de produto

As colunas são blocos reutilizáveis.

Não desenvolver novamente:

```text
seletor de Pessoa para Demandas
seletor de Pessoa para Tarefas
seletor de Pessoa para Compras
```

Desenvolver:

```text
PeopleColumn
```

e reutilizar.

> **Status (03/10/2026): Parcial.** Os editores por tipo são únicos e reaproveitados entre Tabela, Kanban, Calendário e gaveta (`openCellEditor`), e a busca de pessoas (`personSearchNode`) é um só componente. Não existe uma classe `PeopleColumn`; os quadros de domínio (Demandas e Tarefas) têm editores próprios em `static/js/work-board.js`.

---

# 61. Contrato conceitual por tipo

Cada tipo de coluna deve implementar:

```text
render()
editor()
validate()
serialize()
deserialize()
sort()
filter()
summarize()
format()
```

Alguns também:

```text
group()
calculate()
```

> **Divergência (03/10/2026):** o contrato existe como comportamento, mas distribuído em ramos por tipo, não em classes: `validate` e `serialize` em `normalize_cell_value` (`boards/validators.py`); `format` em `CellService.display_value` (`boards/services.py`); `sort` em `BoardQueryService.sort_expression` (`boards/queries.py`); `render` em `templates/boards/_cell.html`; `editor` em `openCellEditor` (`static/js/boards.js`). `filter` e `summarize` existem só de forma parcial (busca global e soma no Kanban); `calculate` não existe.

---

# 62. Exemplo de arquitetura

```text
BaseColumnType
│
├── TextColumnType
├── NumberColumnType
├── MoneyColumnType
├── DateColumnType
├── PeopleColumnType
├── StatusColumnType
├── DropdownColumnType
├── PriorityColumnType
├── ConfirmationColumnType
├── FileColumnType
├── RelationColumnType
├── TimelineColumnType
└── FormulaColumnType
```

> **Divergência (03/10/2026):** a hierarquia `BaseColumnType` e suas subclasses **não foram implementadas**; a arquitetura real é um catálogo (`BoardColumn.Type`) com despacho por tipo nos módulos citados em §61. Nenhum tipo `Priority`, `File`, `Relation`, `Timeline` ou `Formula` existe.

---

# 63. Critérios de aceite gerais

> **Status (03/10/2026):**
>
> | Critério | Status | Observação |
> |---|---|---|
> | COL-GER-001 | Implementado | criar pelo "+" do cabeçalho, sem sair do quadro |
> | COL-GER-002 | Implementado | renomear inline |
> | COL-GER-003 | Implementado | arrastar o cabeçalho |
> | COL-GER-004 | Implementado | arrastar a divisória ou setas; 96 a 640 px |
> | COL-GER-005 | Implementado | posição e largura gravadas em `BoardColumn` |
> | COL-GER-006 | Parcial | células, nome, posição, largura e etiquetas gravam na hora; o diálogo de configurações tem botão Salvar |
> | COL-GER-007 | Não implementado | não há filtros por coluna |
> | COL-GER-008 | Implementado | ordenação por tipo, no banco |
> | COL-GER-009 | Implementado | ocultar só muda `is_visible` |
> | COL-GER-010 | Não implementado | a exclusão não verifica dependências |

## COL-GER-001

O usuário consegue criar uma coluna sem sair do Quadro.

## COL-GER-002

O usuário consegue renomear inline.

## COL-GER-003

O usuário consegue mover por arrastar e soltar.

## COL-GER-004

O usuário consegue redimensionar.

## COL-GER-005

A posição e largura permanecem após recarregar.

## COL-GER-006

Toda alteração simples usa autosave.

## COL-GER-007

Filtros respeitam o tipo.

## COL-GER-008

Ordenação respeita o tipo.

## COL-GER-009

Ocultar não exclui dados.

## COL-GER-010

Excluir verifica dependências.

---

# 64. Critérios de aceite — Pessoas

> **Status (03/10/2026):**
>
> | Critério | Status | Observação |
> |---|---|---|
> | COL-PES-001 | Parcial | só uma pessoa; `multiple=true` é recusado |
> | COL-PES-002 | Implementado | usuários ativos da organização |
> | COL-PES-003 | Implementado | `BoardCellUser.user` |
> | COL-PES-004 | Implementado | o vínculo é por usuário |
> | COL-PES-005 | Parcial | filtro por pessoa para o quadro todo, não por coluna |
> | COL-PES-006 | Parcial | agrupa nos quadros de domínio; no Kanban dos quadros dinâmicos, não |

## COL-PES-001

A coluna pode ser configurada para uma ou várias pessoas.

## COL-PES-002

A seleção busca apenas usuários válidos da organização.

## COL-PES-003

O banco guarda referência ao usuário, não apenas nome.

## COL-PES-004

Renomear a pessoa não quebra vínculos.

## COL-PES-005

A coluna pode ser filtrada por usuário.

## COL-PES-006

Pode ser usada para agrupamento.

---

# 65. Critérios de aceite — Status

> **Status (03/10/2026):**
>
> | Critério | Status | Observação |
> |---|---|---|
> | COL-STA-001 | Implementado | `BoardColumnOption.pk` |
> | COL-STA-002 | Implementado | renomear no diálogo de etiquetas e no cabeçalho da raia do Kanban |
> | COL-STA-003 | Implementado | paleta de cores |
> | COL-STA-004 | Implementado | Tabela, Kanban e Calendário leem a mesma etiqueta |
> | COL-STA-005 | Parcial | filtros e Kanban usam o id; automações não existem |
> | COL-STA-006 | Implementado | agrupamento do Kanban |

## COL-STA-001

As opções possuem ID estável.

## COL-STA-002

Nome pode ser alterado inline.

## COL-STA-003

Cor pode ser alterada inline.

## COL-STA-004

Todas as visualizações refletem a mudança.

## COL-STA-005

Renomear não quebra automações ou filtros.

## COL-STA-006

Pode agrupar Kanban.

---

# 66. Critérios de aceite — Data

> **Status (03/10/2026):**
>
> | Critério | Status | Observação |
> |---|---|---|
> | COL-DAT-001 | Implementado | `show_time=false` por padrão |
> | COL-DAT-002 | Implementado | opção "Mostrar horário" nas configurações |
> | COL-DAT-003 | Implementado | desligar o horário mantém `value_date` |
> | COL-DAT-004 | Implementado | `date_field` do Calendário |
> | COL-DAT-005 | Implementado | ordena por `value_date` ou `value_datetime` |

## COL-DAT-001

Data funciona sem horário.

## COL-DAT-002

Horário pode ser ativado opcionalmente.

## COL-DAT-003

Remover horário mantém a Data.

## COL-DAT-004

Pode alimentar o Calendário.

## COL-DAT-005

Ordenação é cronológica.

---

# 67. Critérios de aceite — Fórmula

> **Status (03/10/2026): COL-FOR-001 a COL-FOR-007 não implementados** (o tipo `FORMULA` está apenas reservado).

## COL-FOR-001

O valor é calculado automaticamente.

## COL-FOR-002

O resultado é somente leitura.

## COL-FOR-003

Referências usam IDs de colunas.

## COL-FOR-004

Renomear coluna referenciada não quebra a Fórmula.

## COL-FOR-005

Dependência circular é bloqueada.

## COL-FOR-006

Excluir coluna referenciada é bloqueado até corrigir a Fórmula.

## COL-FOR-007

O resultado possui tipo definido.

---

# 68. Critérios de aceite — Relação

> **Status (03/10/2026): COL-REL-001 a COL-REL-005 não implementados** em quadros dinâmicos. Apenas o campo de sistema `activity` (Demanda vinculada) do quadro de Tarefas guarda uma referência real, somente leitura.

## COL-REL-001

O valor referencia um objeto real.

## COL-REL-002

O usuário consegue pesquisar objetos.

## COL-REL-003

Objetos de outro tenant não aparecem.

## COL-REL-004

Clicar pode abrir o drawer do relacionado.

## COL-REL-005

Pode ser filtrada e agrupada.

---

# 69. Critérios de aceite — Arquivos

> **Status (03/10/2026): COL-ARQ-001 a COL-ARQ-004 não implementados** (o tipo `FILE` está apenas reservado).

## COL-ARQ-001

Upload respeita autorização.

## COL-ARQ-002

Download exige autorização.

## COL-ARQ-003

A célula mostra quantidade de anexos.

## COL-ARQ-004

Abrir anexo não exige sair do contexto principal.

---

# 70. Matriz final

| Tipo | Editável inline | Filtrar | Ordenar | Agrupar | Resumo | Kanban | Calendário | Fórmula |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Texto | Sim | Sim | Sim | Limitado | Contagem | Sim | Sim | Entrada limitada |
| Número | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| Moeda | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| Data | Sim | Sim | Sim | Sim | Sim | Sim | Principal | Sim |
| Pessoas | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Não direta |
| Status | Sim | Sim | Sim | Sim | Distribuição | Principal | Sim | Condição |
| Lista suspensa | Sim | Sim | Sim | Sim | Distribuição | Sim | Sim | Condição |
| Prioridade | Sim | Sim | Sim | Sim | Distribuição | Sim | Sim | Condição |
| Confirmação | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Sim |
| Arquivo | Via painel | Básico | Básico | Não | Contagem | Sim | Sim | Não |
| Relação | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Limitado |
| Cronograma | Sim | Sim | Sim | Não | Duração | Sim | Futuro | Sim |
| Fórmula | Não | Sim | Sim | Depende | Depende | Sim | Depende | Resultado |

**Matriz implementada em 03/10/2026 (quadros dinâmicos).** Apenas os 8 tipos criáveis; "Resumo" refere-se ao que existe de fato.

| Tipo | Editável inline | Filtrar | Ordenar | Agrupar | Resumo | Kanban | Calendário | Fórmula |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Texto | Sim | Só busca global | Sim | Não | Não | Campo do cartão | Campo do cartão | Não |
| Número | Sim | Não | Sim | Não | Soma por raia | Campo do cartão e soma | Campo do cartão | Não |
| Moeda | Sim | Não | Sim | Não | Soma por raia | Campo do cartão e soma | Campo do cartão | Não |
| Data | Sim | Não | Sim | Não | Não | Campo do cartão | Posiciona o item | Não |
| Pessoas | Sim (uma pessoa) | Filtro por pessoa do quadro | Sim | Não (só nos quadros de domínio) | Não | Campo do cartão | Campo do cartão | Não |
| Status | Sim | Só busca global | Sim | Sim (Kanban) | Contagem por raia | Agrupa e colore | Colore o cartão | Não |
| Lista suspensa | Sim | Só busca global | Sim | Sim (Kanban) | Contagem por raia | Agrupa e colore | Colore o cartão | Não |
| Confirmação | Sim | Não | Sim | Não | Não | Campo do cartão | Campo do cartão | Não |
| Prioridade, Arquivo, Relação, Cronograma, Fórmula | Não implementados em quadros dinâmicos | | | | | | | |

---

# 71. Definição final

A coluna na LPS é:

> Um componente reutilizável de dados e comportamento que define como uma informação é armazenada, editada, validada, filtrada, ordenada, agrupada, calculada e apresentada nas diferentes visualizações do sistema.

As 13 colunas-base oficiais são:

```text
Texto
Número
Moeda
Data
Pessoas
Status
Lista suspensa
Prioridade
Confirmação
Arquivo
Relação
Cronograma
Fórmula
```

Campos específicos da construção e da operação da Biasi devem nascer da composição desses tipos, e não da criação indiscriminada de novos tipos técnicos.

Essa é a base para a LPS ser dinâmica sem virar um sistema tecnicamente desorganizado.

> **Status (03/10/2026):** a definição é o alvo. Hoje o motor entrega 8 dos 13 tipos-base (Texto, Número, Moeda, Data, Pessoas, Status, Lista suspensa e Confirmação); os cinco restantes (Prioridade, Arquivo, Relação, Cronograma e Fórmula) continuam como requisito futuro.
