# LPS — Especificação da Visualização por Tabela (Quadro)

## Status de implementação (03/10/2026)

**Resumo.** A Tabela do **Quadro dinâmico** (`/quadros/<id>/`, o "Quadro principal") está implementada em cerca de 65% desta especificação: criação de colunas por `+` com 8 tipos, edição inline com autosave e interface otimista, renomear, mover (arrastando), redimensionar, ocultar, duplicar, alterar tipo e excluir colunas, etiquetas editáveis na própria tela, ordenação por coluna, busca, filtro por Pessoa, grupos, criar item, Data com horário opcional, permissões no servidor e auditoria. **Não existem ainda**: filtros por condições, agrupar por coluna, resumo de coluna, gaveta de detalhes na Tabela, tipos estruturais e avançados (Relação, Arquivos, Fórmula etc.), compartilhar/automatizar/integrar. As telas de **Demandas** (`/demandas/`) e de **Tarefas** (`/tarefas/`) não são a Tabela genérica: têm colunas fixas no HTML e seguem outro desenho (veja a tabela e as notas das seções 29 e 30). Itens ainda não implementados continuam descritos abaixo como requisito futuro.

| Requisito / bloco | Status | Onde está no código |
|---|---|---|
| Modelo Quadro, Grupo, Coluna, Etiqueta, Item e Célula tipada; isolamento por organização | Implementado | `boards/models.py` (`Board`, `BoardGroup`, `BoardColumn`, `BoardColumnOption`, `BoardItem`, `BoardCell`), `boards/views.py` (`get_board` e demais `get_*` filtram por organização) |
| Abas de visualização (Quadro principal, Kanban, Calendário, `+`) | Implementado (o Quadro principal é implícito, sem registro; Linha do tempo e Dashboard aparecem como "Em breve") | `templates/boards/_board_view_tabs.html`, `boards/models.py` (`BoardView`), `static/js/boards.js` (`openViewDialog`) |
| Cabeçalho do quadro (nome editável, histórico, excluir) | Parcial (sem descrição na tela, favorito, compartilhar, automatizar, integrar) | `templates/boards/_board_head.html`, `boards/views.py` (`BoardRenameView`, `BoardHistoryView`) |
| Barra de ações (busca, Pessoa, colunas ocultas) | Parcial (sem Filtro, Agrupar por, Ordenar global nem Configurar visualização) | `templates/boards/_board_workspace.html` |
| Criar coluna pelo `+` e escolher o tipo | Implementado (8 tipos, sem campo de pesquisa no seletor) | `boards/presentation.py` (`TYPE_INFO`, `type_catalog`), `boards/services.py` (`ColumnService.create`), `static/js/boards.js` (`openTypePicker`, `addColumn`) |
| Tipos: Status, Lista suspensa, Texto, Data, Pessoa, Número, Moeda, Sinal de confirmação | Implementado (seleção única; uma pessoa por célula) | `boards/models.py` (`BoardColumn.ACTIVE_TYPES`), `boards/validators.py` (`normalize_cell_value`) |
| Tipos estruturais e avançados (Relação, Obra, Cliente, Arquivos, Fórmula, Cronograma, Prioridade, IA) | Não implementado (os tipos existem como reservados no catálogo, sem criação nem edição) | `boards/models.py` (`BoardColumn.Type`, comentário "Reservados para fases futuras") |
| Edição inline por tipo, autosave e interface otimista com desfazer em caso de erro | Implementado | `static/js/boards.js` (`openCellEditor`, `saveCell`, `inlineEdit`), `boards/views.py` (`CellUpdateView`), `boards/services.py` (`CellService.set_value`) |
| Renomear coluna no lugar | Implementado (duplo clique no nome, ou menu "Renomear") | `static/js/boards.js` (`startColumnRename`), `boards/services.py` (`ColumnService.rename`) |
| Mover colunas arrastando o cabeçalho | Implementado (posição decimal; sem alternativa "mover para a esquerda/direita" no menu) | `static/js/boards.js` (eventos `dragstart`/`drop`), `boards/services.py` (`ColumnService.reorder`, `PositionService`) |
| Redimensionar colunas (mínimo 96 px, máximo 640 px; teclado) | Implementado (sem duplo clique para ajuste automático) | `static/js/boards.js` (`startResize`, `resizeByKey`), `boards/models.py` (`MIN_COLUMN_WIDTH`, `MAX_COLUMN_WIDTH`) |
| Menu da coluna (Configurações, Etiquetas, Ordenar, Duplicar, Adicionar à direita, Alterar tipo, Renomear, Ocultar, Excluir) | Parcial (sem Filtro, Recolher, Agrupar por nem ações de IA) | `static/js/boards.js` (`openColumnMenu`), `boards/views.py` (`Column*View`) |
| Configurações por tipo (descrição, obrigatória, horário, fins de semana, prazo, casas decimais, unidade, mínimo/máximo, moeda) | Parcial (sem validação personalizada, lembretes, restringir edição/visualização, resumo) | `static/js/boards.js` (`openSettings`), `boards/validators.py` (`clean_column_settings`) |
| Etiquetas com identificador próprio, cor, ordem, padrão e "representa conclusão" | Implementado | `boards/models.py` (`BoardColumnOption`), `boards/services.py` (`OptionService`), `static/js/boards.js` (`openLabels`) |
| Ordenação por coluna (crescente, decrescente, remover) | Implementado (por parâmetros da URL, recarrega a página; não é salva) | `boards/queries.py` (`sort_expression`, `items`), `static/js/boards.js` (`sortUrl`) |
| Filtros por condição (operadores por tipo, múltiplos filtros com E) | Não implementado | não existe no código |
| Pesquisa e filtro por Pessoa | Implementado (sem destaque dos resultados; pessoa em qualquer coluna Pessoa) | `boards/queries.py` (`search_filter`, `_filtered_items`) |
| Agrupar por coluna (Status, Setor, Responsável…) | Divergente (existem Grupos manuais do quadro, não agrupamento por coluna) | `boards/models.py` (`BoardGroup`), `boards/services.py` (`GroupService`), `templates/boards/_group.html` |
| Ocultar colunas sem apagar | Implementado (vale para o quadro todo, não por visualização; recarrega a página) | `boards/models.py` (`BoardColumn.is_visible`), `boards/services.py` (`ColumnService.set_visible`) |
| Resumo de coluna (soma, média, contagem por Status) | Não implementado na Tabela (só soma por raia no Kanban) | `boards/kanban.py` (`build_lanes`) |
| Criar item inline e menu do item | Parcial (Adicionar, Renomear, Mover para grupo, Excluir; sem Duplicar, Vincular, Arquivar, Copiar link, Ver histórico por item) | `static/js/boards.js` (`addItem`, `openItemMenu`), `boards/services.py` (`ItemService`) |
| Gaveta lateral de detalhes ao clicar no título | Não implementado na Tabela (existe no Calendário) | `boards/views.py` (`ItemDetailView`), `templates/boards/_item_drawer.html` |
| Data com horário opcional (um só tipo) | Implementado (configuração "Mostrar horário" da coluna) | `boards/validators.py` (`DEFAULT_SETTINGS`, `_normalize_date`), `boards/models.py` (`BoardCell.value_datetime`) |
| Reflexo imediato no Kanban e no Calendário (mesmo dado, mesma etiqueta) | Implementado | `boards/kanban.py`, `boards/calendar_view.py`, `static/js/boards.js` (`refreshKanban`, `refreshCalendar`) |
| Permissões no servidor e auditoria | Implementado | `boards/services.py` (`_require`, `_audit`), `boards/presentation.py` (`board_permissions`), `audit/models.py` (`BOARD_*`) |
| Performance (paginação ou carga incremental) | Parcial (atualizações por fragmento; sem paginação da tabela) | `boards/views.py` (`BoardDetailView`), `boards/queries.py` (`with_cells`, `attach_cells`) |
| Responsividade e acessibilidade | Parcial (rolagem horizontal, 1ª coluna fixa, teclado nas células; sem alternativa por menu para mover coluna) | `static/css/boards.css`, `static/js/boards.js` (`moveFocus`, `resizeByKey`) |
| Tabela de Demandas (`/demandas/`) | Divergente (colunas fixas no HTML, edição inline própria) | `boards/work_views.py` (`DemandWorkBoardView`), `templates/boards/demand_work_board.html`, `static/js/activity-inline-edit.js`, `static/js/activity-inline-options.js` |
| Tabela de Tarefas (`/tarefas/`) | Divergente (lista somente leitura sobre itens dos Quadros de Demanda) | `boards/task_center.py`, `boards/task_center_views.py`, `templates/boards/task_center.html` |

## 1. Objetivo

> **Divergência:** "Quadro" na LPS tem duas camadas. O que esta especificação descreve é o **Quadro dinâmico** (app `boards`): `Board` → `BoardGroup`/`BoardColumn` → `BoardItem` → `BoardCell`. Demandas e Tarefas **não** são mais um quadro genérico configurável: a lista de Demandas é uma tela própria sobre `Activity`, e a "Tarefa" passou a ser um **item do Quadro de cada Demanda** (`Board.kind = DEMAND`, um por Demanda). Os termos da interface são Demanda (antes Atividade), Etapa (antes Situação) e Status (antes Condição); na lista de Demandas a coluna da Etapa ainda aparece como "Estágio".

A visualização por **Tabela (Quadro)** é a visão-base dos dados na LPS.

Ela deve funcionar como uma planilha inteligente e configurável: o usuário enxerga os itens em linhas, os campos em colunas e consegue alterar praticamente tudo sem sair da tela.

A principal referência de experiência é o comportamento observado no Monday: criar colunas, editar valores, renomear, mudar cores, filtrar, ordenar, agrupar, redimensionar e mover colunas diretamente no quadro.

Na LPS, a Tabela não deve ser tratada como uma tela específica de Demandas, Tarefas, Orçamentos ou Obras. Ela deve ser uma **visualização dos mesmos dados do quadro**.

Exemplo:

```text
Quadro: Demandas

Título | Solicitante | Responsável | Setor | Prioridade | Prazo | Status
```

O mesmo conjunto de dados pode depois ser exibido como Kanban, Calendário ou outra visualização.

---

## 2. Princípio central

> **Divergência:** o princípio está implementado: a etiqueta é uma linha própria (`BoardColumnOption`) referenciada por chave estrangeira pelas células (`BoardCellOption`); renomear ou recolorir não toca nas células, e Tabela, Kanban e Calendário leem a mesma etiqueta. O que ainda **não existe** é o consumo por dashboards, relatórios e automações (não há motor de automações no código dos Quadros).

> O dado pertence ao quadro. A Tabela é apenas uma forma de enxergar e editar esse dado.

Consequências:

- não existe um "Status da Tabela" diferente do "Status do Kanban";
- uma alteração feita na Tabela precisa aparecer imediatamente em todas as outras visualizações;
- o usuário não deve preencher a mesma informação em duas telas;
- o sistema deve evitar navegação desnecessária;
- pequenas alterações devem ser salvas automaticamente.

Exemplo:

```text
Status: Working on it
```

O usuário renomeia para:

```text
Trabalhando Nisso
```

A LPS deve atualizar automaticamente:

- a célula da Tabela;
- o título da coluna correspondente no Kanban, se o Kanban estiver agrupado por esse Status;
- filtros;
- agrupamentos;
- dashboards;
- relatórios;
- automações relacionadas àquela opção.

A automação não deve depender do texto "Trabalhando Nisso". Ela deve depender do identificador interno da opção.

---

# 3. Estrutura visual do Quadro

A tela deve ser dividida em cinco áreas principais.

## 3.1 Cabeçalho do quadro

> **Divergência:** o cabeçalho mostra o link "Quadros", o **nome editável no lugar**, o indicador de salvamento, "Histórico" e "Excluir quadro" (conforme permissão). Descrição curta, favorito, Compartilhar, Automatizar, Integrar e menu de mais ações **não existem**. A descrição aparece só na lista de quadros (`/quadros/`).

Exemplo:

```text
Demandas                                      Integrar | Automatizar | Compartilhar | ...
Gestão das demandas internas e intersetoriais.
```

Elementos esperados:

- nome do quadro;
- descrição curta;
- favorito;
- ações do quadro;
- compartilhar;
- automatizar;
- integrar;
- menu de mais ações.

---

## 3.2 Abas de visualização

> **Divergência:** a aba "Quadro principal" é implícita (não tem registro e não se duplica nem se filtra); só Kanban e Calendário podem ter várias visualizações. Filtros e configurações próprias existem nas visualizações Kanban e Calendário (campo `settings` do `BoardView`); busca e Pessoa vão pela URL e não são salvos. Cada quadro nasce com um Kanban; os Quadros de Demanda nascem com Kanban e Calendário.

Exemplo:

```text
[ Quadro principal ] [ Kanban ] [ Calendário ] [ + ]
```

### Comportamento

- cada aba representa uma visualização dos mesmos itens;
- a aba ativa recebe destaque;
- `+` abre a criação de uma nova visualização;
- o usuário pode ter várias visualizações do mesmo tipo;
- cada visualização pode possuir filtros e configurações próprias.

Exemplo:

```text
Quadro principal
Minhas demandas
Demandas do Comercial
Kanban por Status
Kanban por Setor
Calendário de prazos
```

---

## 3.3 Barra de ações

> **Divergência:** a barra tem **Buscar** (campo e botão), **Pessoa**, a lista "Colunas ocultas (n)" com "Mostrar" e "Limpar busca e ordem". **Filtro, Agrupar por, Ordenar global e Configurar visualização não existem** (a ordenação é feita pelo menu de cada coluna). O botão de criar item fica no rodapé de cada grupo, como "Adicionar" + o título da coluna principal (`item_label`, padrão "Nome da Tarefa"); em Quadros de Demanda o rótulo é "Adicionar tarefa".

Abaixo das abas deve existir uma barra de ações leve e sempre acessível.

Exemplo:

```text
[Criar demanda]  Pesquisar  Pessoa  Filtro  Ordenar  Agrupar por  Ocultar  ...
```

Botões principais:

- Criar item;
- Pesquisar;
- Pessoa;
- Filtro;
- Ordenar;
- Agrupar por;
- Ocultar colunas;
- Configurar visualização;
- Mais ações.

O nome do botão principal deve respeitar o contexto:

```text
Criar demanda
Criar tarefa
Criar orçamento
Criar item
```

---

## 3.4 Cabeçalho de colunas

> **Divergência:** nome, menu `...`, arrastar e redimensionar estão implementados. A linha de cabeçalho se repete **dentro de cada grupo**, e a primeira coluna ("Nome da Tarefa" por padrão, ajustável por quadro) é fixa e não tem menu: ela é o nome do item, não uma coluna configurável.

Cada coluna deve apresentar:

- nome;
- área clicável;
- menu `...`;
- suporte a arrastar;
- suporte a redimensionar;
- feedback visual durante interação.

Exemplo:

```text
| Demanda | Responsável | Status | Prazo | Setor | + |
```

O `+` no final cria uma nova coluna.

---

## 3.5 Linhas / itens

> **Divergência:** a edição é direta: clicar na célula abre o editor do tipo; o nome do item edita-se no lugar (clique ou Enter). A primeira coluna fica fixa à esquerda na rolagem horizontal.

Cada linha representa um item.

Exemplo:

```text
Validar Go/No-Go Santa Isabel | Camila Santos | Em andamento | 20/09/2026 | Comercial
```

O comportamento deve ser de edição direta.

O usuário clica na célula, altera e continua trabalhando.

---

# 4. Criação de colunas

## 4.1 Ação principal

No final das colunas deve existir:

```text
+
```

Tooltip:

```text
Adicionar coluna
```

Ao clicar, abre um seletor de tipos.

---

## 4.2 Seletor de tipo de coluna

> **Divergência:** o seletor mostra os **8 tipos ativos**, nesta ordem: Status, Lista suspensa, Texto, Data, Pessoa, Número, Moeda e Sinal de confirmação, com descrição curta. Não há campo "Pesquise ou descreva sua coluna" nem divisão em Essenciais/Mais úteis. Nomes padrão das novas colunas: "Status", "Lista suspensa", "Texto", "Data", "Pessoa", "Números", "Valor" e "Confirmação"; nomes repetidos ganham sufixo ("Texto 2").

Referência observada:

```text
Pesquise ou descreva sua coluna

Essenciais
Status              Lista suspensa
Texto               Data
Pessoas             Números

Mais úteis
Arquivos            Extração por IA
Documento           Fórmula
Conectar quadros     Sinal de confirmação
Cronograma           Prioridade
```

Para a LPS, o catálogo inicial recomendado é:

### Essenciais

- Status;
- Texto;
- Pessoas;
- Lista suspensa;
- Data;
- Números;
- Moeda;
- Checkbox.

### Estruturais

> **Divergência:** nenhum tipo estrutural existe. Relação com outro quadro está apenas reservada no catálogo (`RELATION`, "Conectar quadros"); Obra, Cliente, Setor, Centro de custo, Demanda vinculada e Tarefa vinculada podem ser imitados com Texto ou Lista suspensa, sem vínculo real. (Nas telas de Demandas e Tarefas, Cliente, Obra e Setor são campos da própria Demanda.)

- Relação com outro quadro;
- Obra;
- Cliente;
- Setor;
- Centro de custo;
- Demanda vinculada;
- Tarefa vinculada.

### Avançadas

> **Divergência:** não implementadas. Existem como tipos reservados, que não se criam nem se editam: Arquivo, Cronograma, Prioridade, Confirmação, Conectar quadros, Fórmula e Extração por IA. "Sinal de confirmação" (checkbox) já está ativo, e "Progresso" e "Campo calculado" não têm tipo reservado.

- Arquivos;
- Fórmula;
- Cronograma;
- Progresso;
- Prioridade;
- Sinal de confirmação;
- Campo calculado;
- Extração por Inteligência Artificial.

---

## 4.3 Fluxo ideal

> **Divergência:** o fluxo `+` → tipo → coluna aparece → renomear inline está implementado: a coluna entra na hora e o campo de nome já abre para digitar.

```text
+ → escolher tipo → coluna aparece → renomear inline → usar
```

Evitar:

```text
+ → abrir página → preencher formulário → salvar → voltar
```

---

# 5. Tipos de coluna e comportamento

Cada tipo de coluna deve saber:

- como exibir;
- como editar;
- como validar;
- como ordenar;
- como filtrar;
- como agrupar;
- como resumir;
- como aparecer em um cartão Kanban;
- como ser usado em automações.

---

## 5.1 Status

> **Divergência:** implementado como `BoardColumnOption` (id próprio e imutável, rótulo, cor, posição, `is_default`, `is_done`, `is_active`), com criar, renomear, recolorir, reordenar, excluir (a etiqueta fica inativa e as células que a usavam são limpas), definir padrão (os itens novos já nascem com ela) e marcar "representa conclusão". "Campo obrigatório" existe na coluna. **Validação** não existe. Um Status novo nasce com "Não iniciado" (padrão), "Em andamento" e "Concluído" (conclusão).

Exemplo:

```text
Em andamento
Aguardando retorno
Concluído
```

Configurações:

- nome da coluna;
- criar etiqueta;
- renomear etiqueta;
- mudar cor;
- reordenar etiquetas;
- excluir/desativar etiqueta;
- definir etiqueta padrão;
- indicar quais etiquetas representam conclusão;
- validação;
- campo obrigatório.

Regra importante:

Cada etiqueta deve possuir um identificador interno imutável.

```text
ID: status_01
Nome: Trabalhando Nisso
Cor: rosa
```

Renomear o texto ou mudar a cor não pode quebrar filtros, automações ou histórico.

---

## 5.2 Lista suspensa

> **Divergência:** só **seleção única** (a célula guarda uma etiqueta, embora a tabela de apoio aceite várias); sem valor padrão próprio além da "etiqueta padrão", sem seleção múltipla, sem validação.

Permite uma ou mais opções, conforme configuração.

Configurações:

- opções;
- cores;
- seleção única ou múltipla;
- valor padrão;
- obrigatório;
- validação.

---

## 5.3 Texto

> **Divergência:** um único tipo de texto de até **5.000 caracteres**, com campo de uma linha na edição. Não há "curto/longo", tamanho máximo configurável, placeholder nem validação.

Configurações:

- texto curto ou longo;
- tamanho máximo;
- obrigatório;
- placeholder;
- validação.

Edição:

```text
clique → digite → Enter
```

---

## 5.4 Pessoas

> **Divergência:** a célula guarda **uma pessoa** da mesma organização, com busca no servidor; marcar "várias pessoas" é recusado ("Várias pessoas ficam para uma versão futura"). Restrição por setor ou papel não existe.

Permite selecionar usuários da organização.

Configurações:

- uma pessoa;
- múltiplas pessoas;
- restringir por setor;
- restringir por papel;
- obrigatório.

O seletor deve permitir pesquisa.

---

## 5.5 Data

> **Divergência:** é um só tipo de Data, com configurações: **Mostrar horário** (`show_time`), **Permitir sábado e domingo** (`allow_weekends`), **Tratar como prazo** (`is_deadline`, destaca "vencido") e formato (`DD/MM/YYYY`, `DD/MM/YY`, `YYYY-MM-DD`, aceito pelo servidor). A edição abre um seletor com "Hoje" e "Limpar". Lembretes, sincronização com calendário externo, número da semana e ícone de data não existem.

A Data é um dos melhores exemplos de configuração inline observada.

Estado simples:

```text
17/09/2026
```

O usuário pode habilitar horário clicando no relógio.

Estado completo:

```text
17/09/2026 09:00
```

A LPS não precisa criar dois tipos diferentes de campo.

Deve existir uma única coluna do tipo Data com configuração:

```text
Exibir horário: sim/não
```

Configurações possíveis:

- exibir horário;
- formato da data;
- habilitar final de semana;
- definir como prazo;
- lembretes;
- sincronização com calendário no futuro;
- mostrar número da semana;
- ícone de data.

---

## 5.6 Número

> **Divergência:** implementados casas decimais (0 a 6), **unidade** (até 12 caracteres, por exemplo "%"), mínimo e máximo. Formato e as operações de resumo (soma, média, mínimo, máximo, contagem) **não existem** na Tabela; a soma só é usada no cabeçalho das raias do Kanban.

Configurações:

- casas decimais;
- mínimo;
- máximo;
- unidade;
- formato;
- validação.

Operações de resumo:

- soma;
- média;
- mínimo;
- máximo;
- contagem.

---

## 5.7 Moeda

> **Divergência:** moedas aceitas: Real (R$), Dólar (US$) e Euro (€); casas decimais de 0 a 6; mínimo e máximo; exibição no padrão brasileiro (`R$ 1.250.000,00`). Resumo por soma/média na Tabela não existe.

Configurações:

- moeda;
- casas decimais;
- separador;
- resumo por soma/média.

Exemplo:

```text
R$ 1.250.000,00
```

---

# 6. Edição inline

A edição inline é uma regra obrigatória do produto.

## 6.1 Renomear coluna

> **Divergência:** o gesto é **duplo clique** no nome (ou "Renomear" no menu); um clique simples no nome não edita. Enter confirma e Esc cancela; se o servidor recusar, o nome anterior volta.

Fluxo:

```text
clicar no nome → editar → Enter
```

ou:

```text
... → Renomear
```

Sem abrir nova página.

---

## 6.2 Editar célula

> **Divergência:** Status e Lista abrem uma lista de etiquetas com "Limpar" e "Editar etiquetas"; Pessoa abre busca; Data abre seletor; Texto e Número abrem campo na própria célula (Enter confirma, Esc cancela, setas navegam entre células, F2 e Enter abrem, Delete limpa); a confirmação alterna ao clique ou à barra de espaço.

Exemplos:

### Status

```text
clique → opções → selecionar
```

### Pessoa

```text
clique → pesquisar pessoa → selecionar
```

### Data

```text
clique → calendário → data
```

### Texto

```text
clique → digitar → Enter
```

### Número

```text
clique → digitar → Enter
```

---

# 7. Autosave

> **Divergência:** todas as ações listadas salvam sozinhas, **com duas exceções de comportamento**: "Ocultar coluna" e "Mostrar coluna" recarregam a página, e a **ordenação** é feita por navegação (parâmetros `sort` e `dir` na URL), sem ser gravada. O texto é gravado ao confirmar (Enter ou sair do campo), sem debounce a cada tecla.

Pequenas alterações devem ser persistidas automaticamente.

Não utilizar botão genérico:

```text
Salvar quadro
```

para operações rotineiras.

Exemplos de autosave:

- renomear coluna;
- editar célula;
- mudar cor de etiqueta;
- criar etiqueta;
- redimensionar coluna;
- mover coluna;
- ocultar coluna;
- habilitar horário na Data;
- mudar ordenação.

---

## 7.1 Interface otimista

> **Divergência:** implementado: a célula muda na hora e volta ao valor anterior, com mensagem, se o servidor recusar; o servidor devolve o HTML final da célula, do cabeçalho ou da linha.

A interface deve responder antes da confirmação do servidor.

Exemplo:

1. usuário altera `Em andamento` para `Em execução`;
2. a tela muda imediatamente;
3. a LPS envia a alteração;
4. se sucesso: nenhuma interrupção;
5. se erro: desfazer e mostrar mensagem.

---

# 8. Mover colunas

> **Divergência:** a ordem (`position`, decimal com passo 1000) e a largura pertencem à **coluna do quadro**, e valem para todas as visualizações; não há ordem por visualização. Soltar mostra o lado de destino (antes/depois) e uma falha devolve a coluna ao lugar anterior. Não há alternativa por menu ("Mover coluna para a esquerda/direita").

O cabeçalho deve ser arrastável.

Exemplo:

```text
ANTES
Demanda | Pessoa | Data | Status

DEPOIS
Demanda | Status | Pessoa | Data
```

O movimento precisa:

- ser fluido;
- mostrar a posição de destino;
- preservar largura;
- persistir automaticamente;
- ser independente por visualização, se essa for a decisão do produto.

---

# 9. Redimensionar colunas

> **Divergência:** largura mínima 96 px e máxima 640 px (padrão 160 px), gravada por coluna; também funciona pelo teclado (setas, 16 px por passo, 48 px com Shift). **Duplo clique para ajuste automático não existe.**

O usuário deve poder arrastar a borda lateral do cabeçalho.

Exemplo:

```text
| Responsável                      |
```

vira:

```text
| Responsável |
```

Persistir `width` automaticamente.

Recomendado:

- largura mínima;
- largura máxima;
- duplo clique para ajuste automático;
- cursor visual de resize.

---

# 10. Menu de coluna

> **Divergência:** o menu real tem: Configurações da coluna e Editar etiquetas (Status e Lista), **Ordenar ascendente**, **Ordenar descendente**, Remover ordenação, **Duplicar coluna**, **Adicionar coluna à direita**, **Alterar tipo** (com aviso de quantos valores serão apagados), Renomear, **Ocultar coluna** e Excluir coluna. As ações de gestão só aparecem a quem tem `quadro.gerir_colunas`. Não existem "Ações assistidas por IA", Filtro, Recolher nem Agrupar por.

Cada coluna deve possuir menu `...`.

Estrutura recomendada:

```text
Configurações >
Ações assistidas por IA >
Filtro
Ordenar >
Recolher
Agrupar por
----------------------
Duplicar coluna
Adicionar coluna à direita
Alterar tipo de coluna
----------------------
Renomear
Excluir
```

Na LPS, algumas opções podem variar conforme permissão e tipo.

---

# 11. Configurações específicas da coluna

> **Divergência:** a janela "Configurações" tem **descrição** (até 500 caracteres, aparece ao passar o mouse), **valor obrigatório** e as opções do tipo (Data: horário, fins de semana, prazo; Número e Moeda: casas, unidade, moeda, mínimo e máximo; Status e Lista: botão "Editar etiquetas"). Validação personalizada, lembretes, restringir edição ou visualização e resumo da coluna **não existem**.

O submenu de Configurações precisa variar pelo tipo.

## Exemplo: Data

```text
Personalizar coluna de Data
Adicionar descrição
Definir como obrigatória
Definir validação
Definir como prazo
Adicionar/editar lembretes
Restringir edição
Restringir visualização
Exibir resumo da coluna
```

## Exemplo: Status

```text
Personalizar coluna de Status
Adicionar descrição
Definir como obrigatória
Definir validação
Restringir edição
Restringir visualização
Exibir/ocultar resumo
```

---

# 12. Ordenação

> **Divergência:** a ordenação é aplicada **dentro de cada grupo** (os grupos mantêm sua ordem), com vazios por último, e Status/Lista ordenam pela ordem das etiquetas e Pessoa pelo primeiro nome. Vale só até sair da página (não é salva).

Toda coluna compatível deve oferecer Ordenar.

Modos:

```text
Crescente
Decrescente
Remover ordenação
```

A lógica depende do tipo.

## Texto

Ordem alfabética.

## Número

Ordem numérica.

## Moeda

Ordem pelo valor numérico.

## Data

Ordem cronológica.

## Pessoas

Ordem pelo nome exibido.

## Status / Lista

Preferencialmente pela ordem configurada das etiquetas, e não pelo nome alfabético.

---

# 13. Filtros

> **Divergência:** **não implementado.** Hoje só existem a busca por texto e o filtro por Pessoa. Os operadores de 13.1 e a combinação de 13.2 continuam como requisito futuro (o Kanban também exibe "Filtros" desabilitado, "em breve").

O botão global `Filtro` deve permitir construir condições sem sair da visualização.

Exemplos:

```text
Status = Em andamento
Responsável = Paulo
Setor = Comercial
Prazo antes de 30/09/2026
Prioridade = Alta
```

---

## 13.1 Operadores

### Texto

- contém;
- não contém;
- é igual;
- está vazio;
- não está vazio.

### Número / Moeda

- igual;
- maior que;
- menor que;
- entre;
- vazio.

### Data

- hoje;
- amanhã;
- antes de;
- depois de;
- entre;
- atrasado;
- vazio.

### Pessoas

- é;
- não é;
- contém;
- vazio.

### Status / Lista

- é;
- não é;
- qualquer um entre;
- vazio.

---

## 13.2 Múltiplos filtros

Permitir combinação:

```text
Setor = Comercial
E
Status != Concluído
E
Prazo <= hoje + 7 dias
```

---

# 14. Pesquisa

> **Divergência:** a busca (até 120 caracteres) procura no nome do item, em textos de células, em rótulos de etiquetas e em nomes de pessoas. Não há destaque dos resultados nem campos "cliente", "obra" ou "código" nos Quadros genéricos.

A busca deve pesquisar rapidamente os dados visíveis do quadro.

Pode incluir:

- título;
- texto;
- pessoas;
- cliente;
- obra;
- etiquetas;
- código.

Resultados devem ser destacados sem mudar de página.

---

# 15. Filtro por pessoa

> **Divergência:** o seletor lista as pessoas que aparecem em colunas de Pessoa do quadro e filtra itens em que a pessoa aparece em **qualquer** coluna Pessoa. Não há "Eu", "Meu setor" nem escolha entre Responsável, Solicitante e Participante (nas telas de Demandas e Tarefas existem abas e filtros de escopo próprios).

O atalho `Pessoa` deve facilitar visões pessoais.

Exemplos:

```text
Eu
Paulo Bonfim
Camila Santos
Meu setor
```

Pode filtrar por campos como:

- Responsável;
- Solicitante;
- Participante.

---

# 16. Agrupar por

> **Divergência:** a Tabela dos Quadros usa **Grupos manuais** (`BoardGroup`: nome, cor, ordem), não agrupamento por uma coluna. Cada grupo tem cabeçalho com expandir/recolher (a escolha é lembrada no navegador), nome editável, contagem ("N tarefas"), cor e menu (renomear, mudar a cor, mover para cima/baixo, excluir; só exclui grupo vazio). **Agrupar por Status/Setor/Responsável não existe**, e o cabeçalho do grupo não mostra somas.

A Tabela pode ser dividida em grupos.

Exemplo por Status:

```text
Novas
  Demanda 1
  Demanda 2

Em andamento
  Demanda 3

Concluídas
  Demanda 4
```

Possíveis colunas de agrupamento:

- Status;
- Setor;
- Responsável;
- Prioridade;
- Lista suspensa;
- outras colunas categóricas compatíveis.

---

## 16.1 Cabeçalho de grupo

> **Divergência:** implementados nome, contagem, cor, menu e expandir/recolher; somas e resumos não.

Pode mostrar:

- nome;
- quantidade de itens;
- somas/resumos;
- cor;
- menu;
- expandir/recolher.

Exemplo:

```text
Em andamento  12  |  R$ 3.250.000,00
```

---

# 17. Ocultar colunas

> **Divergência:** "Ocultar coluna" está no menu da coluna e as ocultas ficam na lista "Colunas ocultas (n)", com "Mostrar". O estado (`BoardColumn.is_visible`) pertence ao **quadro**, não à visualização, e a página recarrega.

O usuário deve poder esconder colunas sem apagá-las.

Exemplo:

```text
Ocultar:
[ ] Cliente
[x] Observações internas
[ ] Prazo
```

A configuração pertence à visualização.

---

# 18. Resumo de coluna

> **Divergência:** **não implementado** na Tabela. Só há a soma de uma coluna de Número/Moeda no cabeçalho das raias do Kanban.

Dependendo do tipo, o rodapé ou cabeçalho pode mostrar resumo.

Exemplos:

### Moeda

```text
Soma: R$ 8.250.000,00
```

### Número

```text
Média: 42%
```

### Status

```text
3 Em andamento | 2 Concluídos | 1 Bloqueado
```

---

# 19. Criar item

> **Divergência:** implementado: "+ Adicionar …" no rodapé do grupo cria a linha (já com a etiqueta padrão nas colunas de Status/Lista) e abre o nome para digitar; Enter confirma e os demais campos são editados na linha. Não há formulário completo alternativo nos Quadros genéricos; em Quadros de Demanda, a exclusão de item pede o **motivo do cancelamento**.

O usuário deve poder criar item sem formulário complexo.

Exemplo:

```text
+ Adicionar demanda
```

Ao clicar:

- linha aparece;
- foco vai para Título;
- usuário digita;
- Enter confirma;
- demais campos podem ser preenchidos inline.

Formulário completo continua disponível para cadastros com contexto complexo.

---

# 20. Menu do item

> **Divergência:** o menu do item tem **Mover para o grupo**, **Renomear** e **Excluir item** (conforme permissão). Abrir detalhes, Duplicar, Vincular, Arquivar, Copiar link e Ver histórico por item **não existem** (o histórico do quadro inteiro está em `Histórico`). A linha também se move arrastando a alça, o que persiste grupo e posição.

Cada linha pode ter `...`.

Possíveis ações:

- Abrir detalhes;
- Duplicar;
- Mover para grupo;
- Vincular;
- Arquivar;
- Excluir, conforme regra;
- Copiar link;
- Ver histórico.

---

# 21. Abertura de detalhes

> **Divergência:** **não implementado na Tabela**: clicar no nome renomeia o item. A gaveta do item (campos editáveis no lugar e últimas alterações) existe no **Calendário** (`board-item-detail`). Em Demandas, o título leva à ficha da Demanda; a gaveta com resumo, tarefas, comunicação e histórico existe no Kanban legado (`activity-kanban-drawer`).

Clicar no título pode abrir um drawer lateral, mantendo o quadro no fundo.

Para Demandas, o drawer pode mostrar:

- Resumo;
- Contexto;
- Tarefas vinculadas;
- Comentários;
- Arquivos;
- Histórico.

Para Tarefas:

- Demanda vinculada;
- Responsável;
- Prioridade;
- Prazo;
- Status;
- Checklist;
- Comentários;
- Arquivos;
- Histórico.

A intenção é evitar abandonar o contexto do quadro.

---

# 22. Data + hora

> **Divergência:** implementado como **configuração da coluna** ("Mostrar horário", em "Configurações"), e não por um relógio dentro do seletor. A mesma coluna guarda data (`value_date`) e, quando exibe horário, também data e hora (`value_datetime`); a hora é opcional por célula e nunca se inventa 00:00.

Comportamento obrigatório baseado no fluxo observado:

1. coluna Data começa simples;
2. usuário abre o seletor;
3. calendário aparece;
4. existe ação de relógio / adicionar horário;
5. ao habilitar, o seletor apresenta data + hora;
6. a mesma célula passa a armazenar horário.

Exemplo:

```text
Antes: 17/09/2026
Depois: 17/09/2026 09:00
```

Não criar outra coluna só para isso.

---

# 23. Relação com Kanban

> **Divergência:** implementado: Kanban e Calendário leem as mesmas células e etiquetas, e renomear ou recolorir a etiqueta muda a raia e a cor nas três visões.

A Tabela é a melhor visão para configurar e editar os dados.

O Kanban lê esses mesmos dados.

Exemplo:

Tabela:

```text
Demanda | Status
A       | Trabalhando Nisso
B       | Done
```

Kanban agrupado por Status:

```text
Trabalhando Nisso
- A

Done
- B
```

Se o usuário renomear `Trabalhando Nisso` para `Em execução`, a coluna do Kanban precisa mudar automaticamente.

---

# 24. Permissões

> **Divergência:** ações verificadas no servidor (`quadro.visualizar`, `quadro.editar`, `quadro.gerir_colunas`, `quadro.criar_item`, `quadro.editar_item`, `quadro.excluir_item`, `quadro.excluir`, `quadro.criar`); criar, renomear, configurar e excluir visualizações pedem `quadro.editar`. "Compartilhar visualização" não existe (as visualizações são compartilhadas por todos que veem o quadro). Quadros de Demanda usam também a relação da pessoa com a Demanda (`DemandBoardAccess`).

A interface pode esconder ações, mas isso não é segurança.

O servidor precisa validar permissões para:

- visualizar quadro;
- editar item;
- editar coluna;
- criar coluna;
- excluir coluna;
- mudar configuração;
- gerenciar opções;
- criar visualização;
- compartilhar visualização.

No modelo da LPS, a autorização deve continuar seguindo o motor de ação + escopo.

---

# 25. Histórico e auditoria

> **Divergência:** registrados (`audit.AuditLog`, ações `BOARD_*`): quadro, grupo, coluna (criação, alteração, **movimento, redimensionamento**, exclusão), item (criação, alteração, movimento, exclusão), célula (valor antigo e novo) e visualização. Mudanças visuais (largura, ordem) **são auditadas** em vez de ignoradas. A tela "Histórico" do quadro é paginada.

Alterações relevantes devem ter histórico.

Recomendado auditar:

- criação/exclusão de coluna;
- mudança de tipo;
- renomeação de etiqueta;
- mudança de campo relevante;
- movimentação de item que altera um dado de negócio;
- mudança de responsável;
- mudança de prazo;
- mudança de prioridade;
- mudança de Status.

Mudanças puramente visuais podem ter nível de auditoria diferente:

- largura;
- ordem visual;
- coluna escondida.

---

# 26. Performance

> **Divergência:** as gravações atualizam só a célula, o cabeçalho ou a linha (fragmentos HTML) e o número de consultas não cresce com o número de itens (células pré-carregadas), mas a Tabela **carrega todos os itens do quadro de uma vez, sem paginação nem carga incremental**. Os metadados das colunas vão num `json_script` na própria página.

A Tabela precisa continuar fluida com muitos itens.

Regras recomendadas:

- paginação ou carregamento incremental;
- atualizações parciais;
- evitar recarregar a página inteira;
- debounce em autosave de texto;
- operações de drag com resposta local;
- cache de metadados de colunas;
- queries filtradas por organização.

---

# 27. Responsividade

> **Divergência:** há rolagem horizontal e a primeira coluna e o cabeçalho ficam fixos; o drawer em tela cheia no celular **não se aplica** (não há drawer na Tabela). Ajustes de CSS abaixo de 720 e 760 px existem.

Desktop é a experiência principal.

Em telas menores:

- permitir scroll horizontal;
- preservar a primeira coluna quando útil;
- menus devem caber no viewport;
- drawer pode ocupar tela inteira no mobile;
- evitar comprimir colunas a ponto de ficarem ilegíveis.

---

# 28. Acessibilidade

> **Divergência:** teclado: Enter e F2 editam, Esc cancela, setas navegam entre células, setas redimensionam a coluna; há rótulos ARIA e aviso de status. **Faltam** as alternativas por menu para mover coluna.

Além de arrastar com mouse, oferecer alternativas por menu.

Exemplo:

```text
Mover coluna para esquerda
Mover coluna para direita
```

Também:

- foco de teclado;
- Enter para editar;
- Escape para cancelar;
- contraste suficiente;
- tooltips;
- ícones acompanhados de rótulos nas ações críticas.

---

# 29. Regras específicas para Demandas

> **Divergência:** a lista de Demandas (`/demandas/`, modo "Lista") tem **colunas fixas no HTML**, e não colunas configuráveis: Demanda (título com código, cliente e obra), Cliente / Obra, Setor, Responsável, Tarefas (progresso "feitas de total" e percentual), Prazo, **Estágio** (Etapa) e **Status**. **Solicitante e Prioridade não aparecem como colunas.** A edição inline cobre título, responsável, prazo, setor, Estágio e Status (e Cliente / Obra abre a janela "Editar demanda" na etapa 2); quem não tem permissão vê a célula de leitura. Abas de escopo: "Sob minha responsabilidade", "Do meu setor", "Em que participo", "Concluídas" e "Todas as demandas" (conforme permissão), com filtros por busca, Setor, Etapa, Status, pessoas e atalhos "Atrasadas" e "Vencem hoje". A configuração de campos e visões do `DomainBoard` (`DomainBoardField`, `DomainBoardView`) existe, mas hoje só alimenta o cartão do Kanban de Demandas.

Colunas iniciais sugeridas:

```text
Título da demanda
Solicitante
Responsável
Setor
Prioridade
Prazo
Status
Tarefas vinculadas
Obra
Cliente
```

O administrador pode adicionar outras.

O usuário não deve ser obrigado a manter todas visíveis.

---

# 30. Regras específicas para Tarefas

> **Divergência:** a Tarefa é um **item do Quadro da Demanda** (`BoardItem`), que nasce com as colunas **Responsável** (Pessoa), **Status** (Não iniciado, Em andamento, Concluído) e **Data**; o quadro pode ganhar outras colunas e vir de um modelo. A tela `/tarefas/` é **somente leitura**: lista tarefas em que a pessoa é responsável (ou, com permissão, de outras pessoas) com Nome da Tarefa, Demanda, Cliente / Obra, Responsável, Status, Prazo e "Abrir quadro", com abas Lista, Kanban e Calendário semanal, filtros de busca, estado (A fazer, Em andamento, Concluídas) e prazo, e 50 linhas por página. Dependência, tempo estimado, tempo registrado, tags e bloqueio **não existem** nesse modelo. O modelo antigo `Task` ficou como histórico.

Colunas iniciais sugeridas:

```text
Título da tarefa
Demanda vinculada
Responsável
Setor
Prioridade
Prazo
Status
Checklist
```

Campos opcionais:

```text
Participantes
Dependência
Tempo estimado
Tempo registrado
Tags
Bloqueio
```

Tempo deve ser informação auxiliar, não o centro do gerenciamento.

---

# 31. O que não fazer

Evitar:

- formulário para toda pequena edição;
- status duplicados por visualização;
- salvar manualmente cada alteração;
- tabela rígida por módulo;
- colunas codificadas diretamente no HTML;
- usar o nome da etiqueta como chave de automação;
- recarregar a página após editar uma célula;
- criar `Data` e `Data + Hora` como tipos independentes;
- obrigar o gestor a visualizar todos os campos;
- transformar o quadro em instrumento de vigilância individual.

---

# 32. Critérios de aceite

A visualização Tabela está pronta quando:

- [x] o usuário pode criar coluna pelo `+`; (implementado)
- [x] pode escolher o tipo; (8 tipos)
- [x] pode renomear sem sair da tela; (implementado)
- [x] pode editar células inline; (implementado)
- [x] pode mover colunas; (arrastando; sem alternativa por menu)
- [x] pode redimensionar colunas; (implementado)
- [x] pode ocultar colunas; (por quadro, não por visualização)
- [x] pode ordenar qualquer tipo compatível; (por parâmetros da URL)
- [ ] pode filtrar por múltiplas condições; (não implementado; só busca e Pessoa)
- [ ] pode agrupar por coluna compatível; (não implementado; há grupos manuais)
- [x] pode editar etiquetas de Status na própria tela; (implementado)
- [x] pode mudar a cor das etiquetas sem sair da tela; (implementado)
- [x] mudanças são refletidas no Kanban automaticamente; (implementado)
- [x] Data pode opcionalmente receber horário; (configuração da coluna)
- [x] pequenas alterações usam autosave; (implementado)
- [x] o usuário recebe feedback de erro sem perder o contexto; (implementado)
- [x] permissões são verificadas no servidor; (implementado)
- [x] o tenant da organização é respeitado; (implementado)
- [x] alterações relevantes possuem histórico. (implementado)

---

# 33. Resumo da filosofia

A visualização Tabela da LPS deve transmitir esta sensação:

> Eu clico no dado que quero mudar, altero e continuo trabalhando.

Ela é o local mais completo para estruturar os dados, mas não deve parecer um cadastro burocrático.

A regra é:

```text
selecionar > editar > continuar
```

não:

```text
abrir tela > preencher formulário > salvar > voltar
```

A Tabela é a fundação do quadro. O Kanban, o Calendário e as demais visualizações são outras lentes sobre os mesmos dados.
