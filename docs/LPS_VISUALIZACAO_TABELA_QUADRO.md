# LPS — Especificação da Visualização por Tabela (Quadro)

## 1. Objetivo

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

- Relação com outro quadro;
- Obra;
- Cliente;
- Setor;
- Centro de custo;
- Demanda vinculada;
- Tarefa vinculada.

### Avançadas

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

A interface deve responder antes da confirmação do servidor.

Exemplo:

1. usuário altera `Em andamento` para `Em execução`;
2. a tela muda imediatamente;
3. a LPS envia a alteração;
4. se sucesso: nenhuma interrupção;
5. se erro: desfazer e mostrar mensagem.

---

# 8. Mover colunas

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

Desktop é a experiência principal.

Em telas menores:

- permitir scroll horizontal;
- preservar a primeira coluna quando útil;
- menus devem caber no viewport;
- drawer pode ocupar tela inteira no mobile;
- evitar comprimir colunas a ponto de ficarem ilegíveis.

---

# 28. Acessibilidade

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

- [ ] o usuário pode criar coluna pelo `+`;
- [ ] pode escolher o tipo;
- [ ] pode renomear sem sair da tela;
- [ ] pode editar células inline;
- [ ] pode mover colunas;
- [ ] pode redimensionar colunas;
- [ ] pode ocultar colunas;
- [ ] pode ordenar qualquer tipo compatível;
- [ ] pode filtrar por múltiplas condições;
- [ ] pode agrupar por coluna compatível;
- [ ] pode editar etiquetas de Status na própria tela;
- [ ] pode mudar a cor das etiquetas sem sair da tela;
- [ ] mudanças são refletidas no Kanban automaticamente;
- [ ] Data pode opcionalmente receber horário;
- [ ] pequenas alterações usam autosave;
- [ ] o usuário recebe feedback de erro sem perder o contexto;
- [ ] permissões são verificadas no servidor;
- [ ] o tenant da organização é respeitado;
- [ ] alterações relevantes possuem histórico.

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
