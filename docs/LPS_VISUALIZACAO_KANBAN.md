# LPS — Especificação da Visualização por Kanban

## 1. Objetivo

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

Exemplos:

- soma;
- contagem;
- média.

## Densidade

Possível evolução:

- compacta;
- normal;
- detalhada.

---

# 18. Personalização do cartão

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

Ao mover um cartão:

1. UI move imediatamente;
2. requisição é enviada;
3. servidor valida;
4. se sucesso, mantém;
5. se erro, retorna e mostra mensagem.

O usuário não deve esperar uma página recarregar.

---

# 40. Performance

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

- [ ] pode ser criada a partir do mesmo quadro;
- [ ] não duplica itens;
- [ ] permite escolher a coluna de agrupamento;
- [ ] suporta Status e Lista suspensa;
- [ ] suporta outros agrupamentos aprovados pela LPS;
- [ ] reflete renomeação de etiqueta imediatamente;
- [ ] reflete mudança de cor imediatamente;
- [ ] permite selecionar Status diretamente no cartão;
- [ ] permite editar etiquetas sem sair do Kanban;
- [ ] permite arrastar cartões;
- [ ] drag executa regra de negócio correta;
- [ ] drag inválido é revertido;
- [ ] permite mostrar colunas vazias;
- [ ] possui coluna Em branco para valores vazios;
- [ ] permite ordenar cartões;
- [ ] permite filtrar;
- [ ] permite pesquisar;
- [ ] permite configurar campos do cartão;
- [ ] permite reordenar campos do cartão;
- [ ] mostra pré-visualização;
- [ ] permite múltiplos Kanbans do mesmo quadro;
- [ ] alterações leves usam autosave;
- [ ] permissões são verificadas no servidor;
- [ ] alterações de negócio são auditáveis.

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
