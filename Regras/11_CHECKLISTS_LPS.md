# 11 — Checklists da LPS

> Documento funcional para definir o que é um checklist na LPS, como ele se relaciona com tarefas, como deve ser reutilizado e quais dados precisam ser registrados para medição e aprendizado futuro.

---

# 1. Objetivo

O checklist da LPS é uma lista padronizada de pontos que precisam ser conferidos ou executados dentro de uma tarefa.

Ele existe para:

- evitar esquecimento;
- padronizar a execução;
- reaproveitar conhecimento;
- reduzir retrabalho;
- registrar como a tarefa foi executada;
- permitir medição;
- formar histórico;
- alimentar melhorias futuras.

O checklist não substitui a tarefa.

---

# 2. Atividade, tarefa e checklist

A estrutura da LPS é:

```text
ATIVIDADE
↓
TAREFAS
↓
CHECKLIST
```

## Atividade

Representa o resultado completo a ser alcançado.

Exemplo:

```text
Material disponível na obra.
```

## Tarefa

Representa uma parte do trabalho.

Exemplo:

```text
Revisar orçamento.
```

## Checklist

Representa os pontos que precisam ser verificados dentro daquela tarefa.

Exemplo:

```text
[ ] Conferir escopo
[ ] Conferir fórmulas
[ ] Conferir quantitativos
[ ] Conferir inclusões
[ ] Conferir exclusões
[ ] Conferir condições de pagamento
[ ] Confirmar arquivo salvo
```

---

# 3. Checklist pertence à tarefa

Decisão da LPS:

> **O checklist pertence à tarefa, e não à atividade.**

Motivo:

Uma atividade pode envolver vários setores.

Exemplo:

```text
Atividade:
Material disponível na obra
```

Pode possuir:

```text
Tarefa 1 — Engenharia
Tarefa 2 — Compras
Tarefa 3 — Financeiro
Tarefa 4 — Almoxarifado
```

Cada setor pode precisar de verificações completamente diferentes.

Por isso, um checklist geral na atividade misturaria responsabilidades e dificultaria a leitura.

A tarefa é o contexto correto.

---

# 4. Checklist é sempre plano

Dentro de uma tarefa:

> **não existem subitens de checklist.**

Estrutura permitida:

```text
[ ] Item 1
[ ] Item 2
[ ] Item 3
```

Estrutura não permitida:

```text
[ ] Item 1
    [ ] Subitem 1.1
    [ ] Subitem 1.2
```

Isso preserva simplicidade.

Se um item for complexo demais, provavelmente precisa ser:

- outro item;
- outra tarefa;
- outro processo.

---

# 5. Exemplo real

## Tarefa

```text
Revisão final do orçamento
```

## Checklist

```text
[ ] Conferir escopo
[ ] Conferir fórmulas
[ ] Conferir quantitativos
[ ] Conferir inclusões
[ ] Conferir exclusões
[ ] Conferir condições de pagamento
[ ] Confirmar arquivo salvo na rede
```

---

# 6. Checklist salvo no banco

O checklist não deve existir apenas naquela tarefa.

A LPS deve permitir salvar checklists como modelos reutilizáveis.

Exemplo:

```text
Checklist salvo:
Revisão final de orçamento
```

Na próxima tarefa semelhante, o usuário pode buscar esse checklist no banco e reutilizá-lo.

---

# 7. Fluxo de criação

Ao criar ou editar uma tarefa, deve existir uma área chamada:

```text
Checklist
```

Ações disponíveis:

```text
Buscar checklist salvo
Criar novo checklist
```

---

# 8. Buscar checklist salvo

Ao clicar em:

```text
Buscar checklist salvo
```

a LPS abre um pop-up.

Exemplo:

```text
Buscar checklist...

Revisão final de orçamento
Criado por: Paulo Confar
7 passos
Usado 42 vezes

Visita técnica
Criado por: Rian
9 passos
Usado 18 vezes

Cotação de materiais
Criado por: Jennifer
6 passos
Usado 31 vezes
```

O usuário escolhe um checklist e o aplica à tarefa.

---

# 9. Pop-up

O checklist deve abrir em um pop-up sobre a tela principal.

Objetivo:

- manter a tela limpa;
- evitar excesso de informação;
- permitir foco;
- esconder detalhes até que sejam necessários.

A tela principal mostra apenas o resumo.

Exemplo:

```text
Checklist
3 de 7 concluídos
```

Ao clicar, abre o pop-up completo.

---

# 10. Estrutura do pop-up

Exemplo:

```text
Checklist — Revisão final de orçamento

Criado por: Paulo Confar
7 passos
Utilizado 42 vezes

[ ] Conferir escopo
[ ] Conferir fórmulas
[ ] Conferir quantitativos
[ ] Conferir inclusões
[ ] Conferir exclusões
[ ] Conferir pagamento
[ ] Confirmar arquivo salvo

3 de 7 concluídos
```

---

# 11. Modelo x execução

A LPS precisa separar duas coisas:

```text
MODELO DO CHECKLIST
```

e:

```text
CHECKLIST DA TAREFA
```

---

# 12. Modelo do checklist

É o checklist salvo no banco para reutilização.

Exemplo:

```text
Revisão final de orçamento

1. Conferir escopo
2. Conferir fórmulas
3. Conferir quantitativos
4. Conferir inclusões
5. Conferir exclusões
6. Conferir pagamento
7. Confirmar arquivo salvo
```

---

# 13. Checklist da tarefa

Quando o modelo é utilizado, a LPS cria uma cópia para a tarefa.

Exemplo:

```text
Tarefa 8394
Checklist copiado do modelo:
Revisão final de orçamento
```

A partir daí, aquela execução possui histórico próprio.

---

# 14. Alterar o modelo não altera o passado

Regra essencial:

> **Alterar o checklist padrão não altera checklists que já foram aplicados em tarefas anteriores.**

Exemplo:

Hoje o modelo possui:

```text
7 passos
```

Amanhã Paulo adiciona:

```text
Conferir frete
```

O modelo passa a ter:

```text
8 passos
```

Tarefas antigas continuam com os 7 passos originais.

---

# 15. Criador do checklist

Todo checklist modelo precisa possuir:

```text
Criado por
```

Exemplo:

```text
Criado por:
Paulo Confar
```

No início da LPS:

> **somente quem criou o checklist pode alterar seu modelo.**

Outros usuários podem:

- buscar;
- visualizar;
- utilizar.

Mas não alterar o modelo original.

---

# 16. Informações mínimas do checklist modelo

Cada checklist salvo deve possuir:

- nome;
- descrição opcional;
- criador;
- data de criação;
- última alteração;
- quantidade de passos;
- quantidade de utilizações;
- ativo/inativo.

---

# 17. Informações mínimas de cada item

Cada item deve possuir:

- ordem;
- descrição;
- status;
- quem marcou;
- quando marcou.

Exemplo:

```text
Item:
Conferir escopo

Status:
Concluído

Marcado por:
Rian

Data/hora:
14/09/2026 10:42
```

---

# 18. Progresso

O progresso do checklist deve aparecer também fora do pop-up.

Exemplo:

```text
Checklist
3 de 7 concluídos
```

Pode haver representação visual discreta:

```text
3 / 7
```

ou barra de progresso.

O principal dado continua sendo:

```text
3 de 7
```

---

# 19. Checklist não bloqueia conclusão da tarefa

Decisão da LPS:

> **Uma tarefa pode ser concluída mesmo com checklist incompleto.**

Exemplo:

```text
Status da tarefa:
Concluída

Checklist:
3 de 7 concluídos
```

A LPS não altera os itens restantes.

---

# 20. Status geral e checklist são independentes

A tarefa pode estar:

```text
Concluída
```

enquanto o checklist permanece:

```text
3 de 7
```

Isso é intencional.

O sistema precisa preservar essa diferença.

---

# 21. Não completar checklist automaticamente

Ao concluir uma tarefa:

> **a LPS não deve marcar automaticamente os itens restantes.**

Se estavam:

```text
3 de 7
```

continuam:

```text
3 de 7
```

---

# 22. Por que isso é importante

Porque o checklist precisa registrar:

> como a tarefa realmente foi executada.

Não apenas como deveria ter sido executada.

---

# 23. Exemplo de medição

Depois de 100 utilizações:

```text
Checklist:
Revisão final de orçamento

Utilizações:
100

Concluídos com 100%:
82

Concluídos incompletos:
18
```

---

# 24. Medição por item

A LPS também pode descobrir:

```text
Conferir exclusões
Não concluído em 14% das utilizações.
```

Isso gera informação para melhoria do processo.

---

# 25. Checklist como dado

Tudo na LPS deve ser mensurável.

Por isso, o checklist não deve ser apenas uma lista visual.

Ele precisa gerar dados.

---

# 26. Métricas mínimas

A LPS deve conseguir medir:

- quantidade de checklists criados;
- criador;
- quantidade de passos;
- número de utilizações;
- conclusão total;
- conclusão parcial;
- taxa média de conclusão;
- itens mais concluídos;
- itens menos concluídos;
- usuários que utilizaram;
- tarefas nas quais foi utilizado.

---

# 27. Métricas futuras

Com histórico suficiente, poderá medir:

- tempo entre primeiro e último item;
- itens frequentemente ignorados;
- relação entre checklist incompleto e devolução;
- relação entre checklist incompleto e atraso;
- relação entre checklist completo e qualidade;
- checklists mais reutilizados;
- checklists obsoletos;
- processos com maior padronização.

---

# 28. Exemplo de aprendizado futuro

A LPS identifica:

```text
38% das devoluções de Cotação de Material
ocorreram quando o item "Conferir frete"
não foi concluído.
```

Então poderá sugerir:

```text
Adicionar "Conferir frete" ao checklist padrão?
```

O usuário decide.

---

# 29. Capital intelectual

O checklist também registra conhecimento organizacional.

Exemplo:

```text
Paulo criou:
Revisão final de orçamento

7 passos
42 utilizações
```

Isso permite visualizar:

- quem estruturou determinado conhecimento;
- quantas vezes ele foi reutilizado;
- qual checklist se tornou referência;
- onde existe dependência de conhecimento individual.

---

# 30. Checklist não é tarefa

Não confundir:

```text
Tarefa:
Revisar orçamento
```

com:

```text
Checklist:
Conferir escopo
Conferir fórmula
Conferir pagamento
```

Os itens do checklist:

- não possuem setor próprio;
- não possuem fila própria;
- não possuem executor independente;
- não possuem subtarefas;
- não possuem prazo individual.

Eles existem dentro da tarefa.

---

# 31. Quando criar outra tarefa

Se um item precisa de:

- outro setor;
- outro executor;
- outro prazo;
- outra fila;
- tempo próprio relevante;

ele provavelmente não deve ser checklist.

Deve ser outra tarefa.

---

# 32. Regra prática

Pergunta:

> Isso é um ponto de conferência dentro do trabalho?

Se sim:

```text
Checklist
```

Pergunta:

> Isso é um trabalho independente que alguém precisa executar?

Se sim:

```text
Tarefa
```

---

# 33. Exemplo — checklist

```text
Tarefa:
Visita técnica
```

Checklist:

```text
[ ] Confirmar endereço
[ ] Fotografar acessos
[ ] Registrar interferências
[ ] Conferir padrão de entrada
[ ] Fazer repasse
```

---

# 34. Exemplo — não deveria ser checklist

```text
Comprar transformador
```

se outra pessoa/setor precisa executar.

Isso deve ser uma tarefa.

---

# 35. Banco de dados conceitual

Modelos:

```text
configuracoes.checklists_modelo
configuracoes.checklist_itens_modelo
```

Execuções:

```text
produtividade.checklists
produtividade.checklist_itens
```

---

# 36. `configuracoes.checklists_modelo`

Campos conceituais:

```text
id
organizacao_id
nome
descricao
criado_por
criado_em
atualizado_em
quantidade_passos
quantidade_utilizacoes
ativo
```

---

# 37. `configuracoes.checklist_itens_modelo`

Campos conceituais:

```text
id
organizacao_id
checklist_modelo_id
ordem
descricao
ativo
criado_em
```

---

# 38. `produtividade.checklists`

Campos conceituais:

```text
id
organizacao_id
tarefa_id
checklist_modelo_id
nome_snapshot
criado_por
criado_em
quantidade_passos
quantidade_concluida
```

---

# 39. `produtividade.checklist_itens`

Campos conceituais:

```text
id
organizacao_id
checklist_id
ordem
descricao_snapshot
concluido
concluido_por
concluido_em
```

---

# 40. Snapshot

Ao aplicar um modelo, a LPS deve copiar:

- nome;
- itens;
- ordem.

Isso cria um snapshot daquela versão.

---

# 41. Histórico

Alterações relevantes precisam ser auditadas.

Exemplos:

```text
Checklist aplicado
Item concluído
Item desmarcado
Checklist modelo alterado
Checklist modelo inativado
```

---

# 42. Busca

A busca de checklist deve considerar:

- nome;
- criador;
- tipo de tarefa futuro;
- quantidade de usos;
- data de atualização.

---

# 43. Resultado da busca

Exemplo:

```text
Revisão final de orçamento
Paulo Confar
7 passos
42 usos

Visita técnica
Rian
9 passos
18 usos
```

---

# 44. Ordenação da busca

Inicialmente pode oferecer:

```text
Mais usados
Mais recentes
Meus checklists
```

---

# 45. Não poluir a tarefa

Na tela principal da tarefa, mostrar apenas:

```text
Checklist
3 de 7 concluídos
```

Detalhes abrem no pop-up.

---

# 46. Simplicidade

A LPS não deve transformar checklist em outro sistema de gestão.

No D0, cada item precisa ser simples.

Exemplo:

```text
[ ] Conferir escopo
```

Não:

```text
responsável
prazo
setor
anexo
dependência
subitem
aprovação
```

Se precisar disso:

> é uma tarefa.

---

# 47. D0

No D0, checklist precisa permitir:

```text
[ ] criar checklist modelo
[ ] informar nome
[ ] adicionar itens
[ ] ordenar itens
[ ] salvar
[ ] identificar criador
[ ] buscar checklist
[ ] visualizar quantidade de passos
[ ] visualizar quantidade de usos
[ ] aplicar à tarefa
[ ] marcar/desmarcar itens
[ ] mostrar progresso
[ ] concluir tarefa com checklist incompleto
[ ] preservar estado real
[ ] registrar quem marcou
[ ] registrar quando marcou
```

---

# 48. D1

Depois, a LPS poderá analisar:

- utilização;
- taxa de conclusão;
- itens ignorados;
- relação com devoluções;
- relação com retrabalho;
- relação com atraso;
- checklists mais usados.

---

# 49. D2

Com histórico suficiente, poderá:

- sugerir checklists;
- sugerir novos itens;
- identificar itens inúteis;
- sugerir padronização;
- comparar resultados;
- relacionar checklist com qualidade.

---

# 50. O que não entra no D0

- subitens;
- fluxo dentro do checklist;
- prazo por item;
- responsável por item;
- setor por item;
- IA criando itens automaticamente;
- aprovação por item;
- checklist com estrutura complexa.

---

# 51. Decisões consolidadas

1. Checklist pertence à tarefa.
2. Checklist não pertence à atividade no D0.
3. Não existem subitens.
4. Checklist abre em pop-up.
5. A tarefa mostra o progresso fora do pop-up.
6. O usuário pode buscar checklists salvos no banco.
7. Checklist modelo possui criador.
8. Inicialmente, somente o criador pode alterar o modelo.
9. Checklist modelo possui quantidade de passos.
10. Checklist modelo registra quantidade de utilizações.
11. Ao aplicar um modelo, a LPS cria uma cópia para a tarefa.
12. Alterações futuras no modelo não alteram tarefas antigas.
13. Cada item registra quem marcou e quando.
14. A tarefa pode ser concluída com checklist incompleto.
15. Checklist incompleto permanece incompleto após conclusão da tarefa.
16. A LPS deve medir o uso e o resultado dos checklists.

---

# 52. Regra de ouro

> **Checklist é conhecimento operacional reutilizável e mensurável dentro de uma tarefa.**

---

# 53. Regra de simplicidade

> **Se um item precisa virar um pequeno projeto, ele não é checklist: é tarefa.**

---

# 54. Regra de auditoria

> **A LPS deve preservar o que realmente foi conferido, e não completar artificialmente o que deveria ter sido feito.**

---

# 55. Regra de aprendizado

> **Primeiro a empresa cria e reutiliza checklists. Depois a LPS mede. Só então passa a sugerir melhorias.**

---

# 56. Encerramento

O checklist da LPS não deve ser tratado apenas como uma lista de caixas de seleção.

Ele é uma forma de:

```text
PADRONIZAR
↓
REUTILIZAR
↓
MEDIR
↓
APRENDER
```

A tarefa continua sendo a unidade de trabalho.

O checklist registra os pontos de controle utilizados para executar aquela tarefa.

Com o tempo, esse histórico permite transformar conhecimento individual em conhecimento organizacional mensurável.

---

# 57. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Definição funcional dos checklists da LPS |
