# 04 — Auditoria, Tempo e Métricas

> Documento funcional da LPS para registrar o que realmente aconteceu durante uma atividade, medir tempo de espera e execução, reconstruir a linha do tempo, identificar gargalos e criar a base de dados necessária para aprendizado futuro.

---

# 1. Objetivo deste documento

Este documento define como a LPS deve registrar e medir o trabalho.

Ele existe para responder perguntas como:

- quando a atividade foi criada;
- quanto tempo levou para alguém dar o primeiro passo;
- quanto tempo cada tarefa demorou;
- quanto tempo a demanda ficou em cada setor;
- quanto tempo ficou em fila;
- quanto tempo houve de trabalho efetivo;
- quanto tempo ficou parada;
- quantas vezes voltou;
- quanto tempo cada devolução acrescentou;
- quantas pessoas trabalharam;
- quantas horas-homem foram consumidas;
- quanto tempo total a atividade levou;
- onde o processo perdeu mais tempo;
- qual etapa foi mais rápida;
- qual etapa foi mais lenta;
- quais atividades semelhantes apresentam comportamento diferente;
- qual foi o planejado;
- qual foi o realizado;
- quem alterou cada informação;
- quando cada alteração ocorreu;
- qual era o valor anterior;
- qual passou a ser o novo valor.

Este documento define a lógica funcional.

A estrutura técnica final será traduzida posteriormente para o banco de dados.

---

# 2. Princípio central

A LPS deve registrar fatos operacionais suficientes para reconstruir a história de uma atividade sem depender da memória das pessoas.

A lógica é:

```text
EVENTOS
↓
TIMELINE
↓
TEMPOS
↓
MÉTRICAS
↓
GARGALOS
↓
APRENDIZADO
```

O sistema não deve pedir ao usuário para informar manualmente números que podem ser derivados dos eventos.

Exemplo:

Não perguntar:

```text
Quanto tempo esta tarefa ficou no Comercial?
```

Se a LPS já sabe:

```text
Entrada no Comercial:
08:00

Saída do Comercial:
13:20
```

ela deve calcular:

```text
5h20
```

---

# 3. Auditoria como pilar da LPS

A auditoria não deve ser tratada apenas como requisito de segurança.

Ela é parte do produto.

A LPS precisa saber:

> Quem fez o quê, quando, em qual atividade, em qual tarefa e qual era o estado anterior.

Isso permite:

- responsabilização;
- transparência;
- investigação;
- comparação;
- medição;
- melhoria contínua;
- aprendizado futuro.

---

# 4. Evento como unidade básica da auditoria

Toda alteração relevante deve gerar um evento.

Exemplos:

```text
atividade criada
```

```text
dono definido
```

```text
tarefa criada
```

```text
tarefa entrou na fila
```

```text
posição alterada
```

```text
executor atribuído
```

```text
tarefa iniciada
```

```text
tarefa pausada
```

```text
tarefa retomada
```

```text
tarefa devolvida
```

```text
prazo proposto
```

```text
prazo aceito
```

```text
prazo recusado
```

```text
tarefa concluída
```

```text
atividade concluída
```

Quando uma atividade utiliza processo, eventos adicionais precisam existir.

Exemplos:

```text
processo aplicado
```

```text
versão do processo registrada
```

```text
input preenchido
```

```text
input alterado
```

```text
critério de aceite atendido
```

```text
critério de aceite reaberto
```

```text
evidência de output registrada
```

```text
fluxo padrão desviado
```

O evento precisa guardar `processo_id` e `processo_versao_id` quando existirem.

---

# 5. Evento precisa possuir contexto

Um evento não deve registrar apenas:

```text
alterado
```

Precisa possuir contexto suficiente.

Exemplo:

```text
Evento:
Prazo comprometido alterado

Atividade:
Solicitação de compra 184

Tarefa:
Pagamento

Usuário:
Carla

Data/hora:
12/09/2026 14:22

Valor anterior:
15/09/2026 12:00

Novo valor:
16/09/2026 09:00
```

---

# 6. Histórico não pode depender de texto livre

Texto livre pode complementar.

Mas informações importantes devem ser estruturadas.

Exemplo ruim:

```text
"Paulo mudou alguma coisa no prazo."
```

Exemplo adequado:

```text
tipo_evento:
prazo_alterado

usuario:
Paulo

valor_anterior:
15/09 12:00

valor_novo:
16/09 09:00
```

---

# 7. Timeline da atividade

Toda atividade deve possuir uma linha do tempo consolidada.

Exemplo:

```text
08:00 — atividade criada
08:05 — tarefa "Gerar lista" criada
10:17 — primeira ação relevante
10:17 — Ryan iniciou tarefa
11:32 — tarefa concluída
11:33 — tarefa enviada para Compras
11:33 — entrou na fila de Compras em 8 de 14
15:40 — posição mudou para 5 de 12
Dia seguinte 09:10 — Compras iniciou
10:30 — devolvida para Engenharia
10:30 — motivo: especificação incompleta
11:50 — Engenharia corrigiu
11:55 — reenviada para Compras
13:20 — Compras concluiu
...
```

---

# 8. Timeline da tarefa

Além da timeline geral, cada tarefa precisa possuir sua própria linha do tempo.

Exemplo:

```text
Tarefa:
Realizar cotação
```

Timeline:

```text
08:10 — criada
08:12 — entrou na fila de Compras
10:45 — passou de 7 de 18 para 4 de 16
13:00 — executora Jennifer atribuída
13:05 — execução iniciada
13:47 — pausada
14:12 — retomada
15:05 — devolvida
15:05 — motivo: especificação incompleta
```

---

# 9. Timeline da atividade x timeline da tarefa

A timeline da atividade responde:

> O que aconteceu com o resultado como um todo?

A timeline da tarefa responde:

> O que aconteceu com esta parte específica do trabalho?

As duas visões devem coexistir.

---

# 9.1 Métricas específicas de processo

Para atividades vinculadas a processo, a LPS deve conseguir medir futuramente:

- percentual de inputs obrigatórios recebidos na criação;
- tempo aguardando inputs obrigatórios;
- tempo entre inputs completos e primeira ação;
- quantidade de critérios de aceite reabertos;
- tempo entre última tarefa e aceite final;
- desvios do fluxo padrão;
- diferenças entre versões do mesmo processo.

Essas métricas devem nascer de eventos e estados estruturados, não de perguntas manuais ao usuário.

---

# 10. Data de criação

Toda atividade precisa registrar automaticamente:

- data;
- hora;
- usuário que criou;
- organização;
- empresa;
- dono inicial.

O usuário não deve digitar a data de criação manualmente.

---

# 11. Data de criação é um marco

A criação marca o início da existência da demanda na LPS.

A partir dela, podemos medir:

```text
tempo até primeira ação
```

```text
tempo total da atividade
```

```text
tempo até conclusão
```

---

# 12. Criado por x dono

A pessoa que cria pode ser diferente do dono.

Exemplo:

```text
Criado por:
Jennifer

Dono:
Paulo
```

A auditoria precisa preservar os dois.

---

# 13. Primeira ação

Um dos indicadores centrais da LPS é:

> Quanto tempo demorou para alguém realmente começar a agir?

A diferença é:

```text
Primeira ação relevante
-
Data de criação
```

---

# 14. Tempo até primeira ação

Fórmula conceitual:

```text
tempo_ate_primeira_acao
=
timestamp_primeira_acao
-
timestamp_criacao
```

Exemplo:

```text
Atividade criada:
08:00

Primeira ação:
10:17

Tempo até primeira ação:
2h17
```

---

# 15. Abrir a tela não deve contar como primeira ação

Visualizar a atividade não representa necessariamente avanço.

A primeira ação deve ser um evento operacional relevante.

Possíveis exemplos:

- assumir tarefa;
- atribuir executor;
- iniciar execução;
- definir prazo comprometido;
- realizar movimentação;
- registrar uma decisão formal;
- executar uma ação configurada como avanço.

---

# 16. Definição exata de primeira ação

A definição final precisa ser estruturada no produto.

O importante é não confundir:

```text
atividade visualizada
```

com:

```text
atividade começou a ser tratada
```

---

# 17. Primeira ação por atividade

A atividade pode ter uma métrica global:

```text
criação
↓
primeira ação relevante em qualquer tarefa
```

---

# 18. Primeira ação por tarefa

Cada tarefa também pode possuir:

```text
criação da tarefa
↓
primeira ação relevante da tarefa
```

Isso ajuda a identificar onde o trabalho fica parado antes de começar.

---

# 19. Tempo total da atividade

A duração total da atividade é:

```text
conclusão da atividade
-
criação da atividade
```

Exemplo:

```text
Criada:
10/09 08:00

Concluída:
18/09 11:00

Tempo total:
8 dias e 3 horas
```

---

# 20. Tempo total não é tempo trabalhado

Essa distinção é obrigatória.

Exemplo:

```text
Tempo total:
8 dias e 3 horas

Tempo efetivamente trabalhado:
11h40

Restante:
fila, espera, bloqueio, fornecedor, intervalos e outros tempos
```

---

# 21. Duração cronológica

Duração cronológica representa o tempo de relógio entre dois eventos.

Exemplo:

```text
Entrada no Financeiro:
segunda-feira 09:00

Saída:
terça-feira 15:00

Duração cronológica:
30 horas
```

Essa duração pode ou não considerar calendário útil em relatórios específicos.

---

# 22. Tempo útil x tempo corrido

A LPS precisa reconhecer que existem duas formas de analisar duração.

## Tempo corrido

Conta o relógio completo.

Exemplo:

```text
sexta 17h
até
segunda 09h
```

inclui o fim de semana.

## Tempo útil

Pode considerar apenas o calendário de trabalho configurado.

Essas duas métricas não devem ser confundidas.

---

# 23. D0 e calendário útil

No D0, a prioridade é registrar timestamps corretos.

O cálculo sofisticado de calendários pode evoluir depois.

Mas a arquitetura não deve impedir no futuro:

- expediente;
- feriados;
- dias úteis;
- turnos;
- calendários por empresa.

---

# 24. Tempo em tarefa

Cada tarefa precisa possuir duração cronológica.

Exemplo:

```text
Tarefa criada:
08:00

Concluída:
16:00

Duração total:
8h
```

Mas isso não significa:

```text
8h de trabalho
```

---

# 25. Tempo efetivamente trabalhado

O tempo trabalhado é a soma das sessões de execução registradas pelos executores.

Exemplo:

```text
Ryan:
08:00–09:30 = 1h30

Jennifer:
08:30–10:00 = 1h30
```

Horas-homem:

```text
3h
```

---

# 26. Sessão de trabalho

Uma sessão representa um período em que uma pessoa trabalhou efetivamente em determinada tarefa.

Estrutura conceitual:

```text
Executor
Tarefa
Início
Fim
Duração
```

---

# 27. Início

Ao iniciar uma tarefa, a LPS registra automaticamente:

- usuário;
- tarefa;
- atividade;
- setor;
- data;
- hora.

---

# 28. Pausa

Ao pausar, a sessão atual termina.

A pausa deve permitir separar:

```text
tempo trabalhado
```

de:

```text
tempo não trabalhado
```

---

# 29. Retomada

Ao retomar:

```text
nova sessão de trabalho
```

é criada.

---

# 30. Exemplo de múltiplas sessões

```text
08:00–09:00 = 1h
11:00–12:30 = 1h30
15:20–16:00 = 40min
```

Tempo efetivamente trabalhado:

```text
3h10
```

---

# 31. Vários executores

Uma tarefa pode possuir vários executores trabalhando simultaneamente.

Exemplo:

```text
Ryan:
08:00–10:00 = 2h

Jennifer:
08:30–09:30 = 1h
```

Tempo cronológico da janela:

```text
2h
```

Horas-homem:

```text
3h
```

---

# 32. Horas-homem

Horas-homem representam a soma do tempo de trabalho de todas as pessoas.

Fórmula conceitual:

```text
horas_homem
=
Σ duração das sessões de todos os executores
```

---

# 33. Por que horas-homem importam

Uma atividade pode parecer rápida no calendário e consumir muito recurso.

Exemplo:

```text
Duração:
2 horas

Pessoas:
5

Cada pessoa:
2 horas
```

Horas-homem:

```text
10 horas
```

Sem essa métrica, o custo operacional fica invisível.

---

# 34. Quantidade de pessoas envolvidas

A LPS deve conseguir calcular:

- pessoas distintas por tarefa;
- pessoas distintas por atividade;
- setores distintos;
- gestores envolvidos;
- participantes que executaram trabalho.

---

# 35. Pessoas envolvidas não é igual a pessoas que visualizaram

A métrica de esforço deve considerar participantes operacionais reais.

Visualização não deve inflar o número.

---

# 36. Tempo em fila

Tempo em fila é o período entre:

```text
entrada na fila
```

e:

```text
primeiro início de execução daquela passagem
```

Exemplo:

```text
Entrou na fila de Compras:
segunda 14:00

Iniciou:
terça 09:30

Tempo em fila:
19h30 corridas
```

---

# 37. Uma tarefa pode entrar na mesma fila mais de uma vez

Exemplo:

```text
Compras
↓ devolução
Engenharia
↓ correção
Compras novamente
```

A LPS precisa registrar duas passagens distintas pela fila de Compras.

---

# 38. Tempo total em fila por setor

Exemplo:

```text
Primeira passagem em Compras:
18h40

Segunda passagem:
4h20

Total em fila de Compras:
23h
```

---

# 39. Tempo de execução por setor

A LPS também deve conseguir somar o tempo efetivo de trabalho realizado por pessoas de um setor.

Exemplo:

```text
Compras

Jennifer:
1h30

Rian:
0h45

Total:
2h15
```

---

# 40. Tempo de permanência no setor

Esse conceito é diferente.

Pode significar:

```text
entrada da tarefa no setor
↓
saída da tarefa do setor
```

Inclui:

- fila;
- execução;
- espera;
- bloqueio;
- devolução interna.

Exemplo:

```text
Permanência no setor:
22h

Trabalho efetivo:
2h15
```

---

# 41. Três tempos importantes por setor

A LPS deve separar, sempre que possível:

```text
tempo de permanência
```

```text
tempo em fila
```

```text
tempo efetivamente trabalhado
```

Isso muda completamente a análise de gargalo.

---

# 42. Exemplo de análise correta

```text
Compras:
22h de permanência

Fila:
18h40

Execução:
2h10

Outras esperas:
1h10
```

A conclusão não é:

> Compras trabalhou 22 horas.

A conclusão é:

> A tarefa permaneceu 22 horas em Compras, mas somente 2h10 foram de trabalho registrado.

---

# 43. Tempo entre tarefas

A LPS deve medir lacunas entre tarefas.

Exemplo:

```text
Tarefa A concluída:
10:00

Tarefa B iniciada:
15:30

Tempo entre tarefas:
5h30
```

Essa lacuna pode representar:

- fila;
- espera;
- dependência;
- falta de atribuição;
- transferência;
- intervalo operacional.

---

# 44. Tempo de transição

Quando uma tarefa termina e a próxima ainda não começou, existe um tempo de transição.

Esse tempo pode ser um gargalo invisível.

---

# 45. Tempo parado

“Tempo parado” precisa ser tratado com cuidado.

Nem toda ausência de sessão significa problema.

Pode significar:

- fila;
- aguardando cliente;
- aguardando fornecedor;
- aguardando decisão;
- fora do expediente;
- dependência;
- bloqueio.

A LPS deve buscar classificar o motivo quando possível.

---

# 46. Bloqueio

Quando uma tarefa é explicitamente bloqueada, registrar:

- início;
- fim;
- motivo;
- usuário;
- setor;
- observação quando aplicável.

---

# 47. Tempo bloqueado

Fórmula conceitual:

```text
tempo_bloqueado
=
Σ períodos de bloqueio
```

---

# 48. Motivos de bloqueio

Exemplos:

```text
Aguardando cliente
```

```text
Aguardando fornecedor
```

```text
Aguardando aprovação
```

```text
Aguardando documento
```

```text
Aguardando decisão
```

```text
Aguardando recurso
```

A lista pode ser configurável.

---

# 49. Espera externa

Aguardar fornecedor é diferente de fila interna.

Exemplo:

```text
Fornecedor:
7 dias
```

Esse tempo precisa aparecer separado para evitar atribuir o atraso ao setor interno.

---

# 50. Espera por cliente

Da mesma forma:

```text
Aguardando cliente:
3 dias
```

não deve ser tratado como 3 dias de execução interna.

---

# 51. Tempo não classificado

No início, haverá situações em que o sistema conhece a diferença temporal, mas não o motivo.

Exemplo:

```text
Tarefa ficou 9h sem execução e sem bloqueio registrado.
```

A LPS pode classificar temporariamente como:

```text
tempo não classificado
```

Isso é melhor do que inventar uma causa.

---

# 52. Redução de tempo não classificado

Com maturidade, a LPS deve buscar reduzir tempo sem explicação.

Quanto mais contexto real:

- fila;
- bloqueio;
- terceiro;
- execução;
- transição;

melhor a análise.

---

# 53. Devolução

Toda devolução deve gerar evento.

Registrar:

- tarefa;
- atividade;
- setor de origem;
- setor de destino;
- usuário;
- data;
- hora;
- motivo;
- observação;
- posição no fluxo.

---

# 54. Quantidade de devoluções

A LPS deve calcular:

```text
quantidade_de_devolucoes
```

por:

- tarefa;
- atividade;
- tipo de atividade;
- setor;
- período;
- motivo.

---

# 55. Tempo de devolução

Precisamos medir quanto tempo um retorno acrescenta ao processo.

Exemplo:

```text
Compras devolveu:
segunda 14:00

Engenharia corrigiu e reenviou:
terça 10:00

Tempo de correção:
20h
```

---

# 56. Ciclo de devolução

Pode ser medido de:

```text
momento da devolução
```

até:

```text
momento em que a tarefa retorna ao ponto de origem
```

ou até outro marco definido.

A definição técnica precisa ser consistente.

---

# 57. Tempo perdido por retrabalho

Nem toda devolução é necessariamente erro.

Mas, quando classificada como retrabalho, podemos medir:

- duração adicional;
- horas-homem adicionais;
- atraso causado;
- etapas repetidas.

---

# 58. Motivos recorrentes

Exemplo:

```text
Devoluções de Compras para Engenharia

31% — especificação incompleta
22% — quantidade divergente
14% — projeto ausente
...
```

Esse é um dos principais dados de aprendizado futuro.

---

# 59. Planejado x realizado

A LPS precisa preservar o que foi planejado e comparar com o que ocorreu.

Exemplos:

```text
Prazo planejado:
2 dias

Realizado:
3,4 dias
```

---

# 60. Planejado de atividade

Pode incluir:

- prazo final;
- tarefas previstas;
- setores previstos;
- sequência;
- prazo das tarefas;
- responsáveis previstos quando definidos.

---

# 61. Realizado da atividade

Inclui:

- duração real;
- tarefas realmente executadas;
- setores realmente percorridos;
- devoluções;
- novos participantes;
- mudanças;
- atrasos.

---

# 62. Planejado x realizado de fluxo

Exemplo:

Planejado:

```text
Engenharia
↓
Compras
↓
Financeiro
```

Real:

```text
Engenharia
↓
Compras
↓
Engenharia
↓
Compras
↓
Diretoria
↓
Financeiro
```

A diferença é dado de processo.

---

# 63. Planejado x realizado de prazo

Exemplo:

```text
Prazo solicitado:
10/09

Prazo comprometido:
12/09

Concluído:
14/09
```

A LPS deve preservar os três.

---

# 64. Desvio do prazo solicitado

Fórmula conceitual:

```text
desvio_solicitado
=
data_conclusao
-
prazo_solicitado
```

---

# 65. Desvio do prazo comprometido

Fórmula conceitual:

```text
desvio_comprometido
=
data_conclusao
-
prazo_comprometido
```

Esse indicador é importante para medir confiabilidade do compromisso.

---

# 66. Prazo renegociado

Se houve vários prazos comprometidos, o histórico deve permitir:

- prazo original;
- cada nova proposta;
- aceite;
- versão final;
- conclusão.

---

# 67. Quantidade de renegociações

Pode ser uma métrica.

Exemplo:

```text
Atividade:
3 renegociações de prazo
```

Processos com muita renegociação podem indicar baixa previsibilidade.

---

# 68. Atividades mais rápidas

A LPS poderá ordenar atividades semelhantes por duração.

Exemplo:

```text
Tipo:
Solicitação de compra

Mais rápida:
1,8 dia
```

---

# 69. Atividades mais lentas

Exemplo:

```text
Mais lenta:
14,2 dias
```

A comparação precisa ser contextual.

---

# 70. Não comparar coisas diferentes cegamente

Uma solicitação simples e uma compra importada podem pertencer a contextos diferentes.

Por isso, comparações futuras devem considerar:

- tipo;
- complexidade;
- fluxo;
- quantidade;
- fornecedor;
- setor;
- outras características relevantes.

---

# 71. Mediana

Para tempos operacionais, a mediana pode ser útil.

Exemplo:

```text
Durações:
1, 2, 2, 3, 15 dias
```

Média:

```text
4,6 dias
```

Mediana:

```text
2 dias
```

O valor extremo distorce a média.

A LPS poderá usar ambas futuramente.

---

# 72. Média

A média continua útil para:

- esforço;
- capacidade;
- custo;
- planejamento.

Não deve ser usada isoladamente.

---

# 73. Percentis

Em uma fase mais madura, a LPS poderá utilizar percentis.

Exemplo:

```text
P50:
2 dias

P80:
4 dias

P95:
8 dias
```

Isso ajuda a responder:

> Em quanto tempo 80% das atividades semelhantes terminam?

Não é necessário no D0.

---

# 74. Atividade mais rápida não significa melhor

Pode haver:

- erro;
- falta de qualidade;
- escopo menor;
- contexto diferente.

A métrica precisa ser interpretada.

---

# 75. Atividade mais lenta não significa pior

Pode envolver:

- maior complexidade;
- fornecedor;
- decisão;
- dependência externa;
- mais qualidade necessária.

O sistema deve evitar julgamento automático.

---

# 76. Gargalo

Gargalo é um ponto que limita o fluxo.

A LPS deve permitir identificar candidatos a gargalo com base em dados.

---

# 77. Possíveis sinais de gargalo

- fila crescente;
- tempo de espera elevado;
- baixa vazão;
- muitas devoluções;
- alto tempo de permanência;
- alta concentração em poucas pessoas;
- muitas renegociações;
- muitos escalonamentos;
- tarefas bloqueadoras;
- grande diferença entre entrada e saída.

---

# 78. Gargalo de fila

Exemplo:

```text
Tempo de execução:
30 min

Tempo em fila:
3 dias
```

O problema principal não é execução.

É espera.

---

# 79. Gargalo de execução

Exemplo:

```text
Fila:
20 min

Execução:
9h
```

O problema está no trabalho em si, complexidade, recurso ou processo.

---

# 80. Gargalo de retrabalho

Exemplo:

```text
Execução inicial:
2h

Correções:
5h

3 devoluções
```

O processo perde mais tempo corrigindo que executando inicialmente.

---

# 81. Gargalo externo

Exemplo:

```text
Processo interno:
1,5 dia

Fornecedor:
8 dias
```

A gestão precisa saber que o maior limitador é externo.

---

# 82. Gargalo de decisão

Exemplo:

```text
Aguardando aprovação:
4 dias
```

Esse tempo pode ser maior que toda a execução.

---

# 83. Gargalo de capacidade

Exemplo:

```text
Entrada:
30 tarefas/dia

Saída:
20 tarefas/dia
```

O backlog tende a crescer.

Esse tipo de análise será possível futuramente.

---

# 84. Gargalo por pessoa

Uma única pessoa pode concentrar várias tarefas críticas.

A LPS pode identificar:

- volume;
- horas;
- fila;
- dependências.

Mas não deve concluir automaticamente que a pessoa é o problema.

---

# 85. Gargalo por conhecimento

Exemplo:

Jennifer executa determinada tarefa muito mais rápido que outros.

Isso pode indicar:

- domínio técnico;
- falta de padrão;
- oportunidade de treinamento.

A LPS poderá sugerir investigação.

---

# 86. Métricas de atividade

Possíveis métricas:

- tempo total;
- tempo até primeira ação;
- quantidade de tarefas;
- tarefas concluídas;
- tarefas devolvidas;
- quantidade de devoluções;
- pessoas distintas;
- setores distintos;
- horas-homem;
- tempo em fila acumulado;
- tempo de execução acumulado;
- tempo bloqueado;
- tempo externo;
- renegociações;
- escalonamentos.

---

# 87. Métricas de tarefa

Possíveis métricas:

- tempo total;
- tempo até primeira ação;
- tempo em fila;
- tempo trabalhado;
- horas-homem;
- executores;
- pausas;
- devoluções;
- tempo bloqueado;
- prazo solicitado;
- prazo comprometido;
- desvio;
- posição inicial;
- alterações de posição.

---

# 88. Métricas de setor

Possíveis métricas:

- entrada de tarefas;
- saída de tarefas;
- backlog;
- tamanho médio da fila;
- tempo médio em fila;
- tempo mediano em fila;
- tempo de execução;
- permanência;
- devoluções recebidas;
- devoluções realizadas;
- renegociações;
- escalonamentos;
- cumprimento de prazo.

---

# 89. Métricas de pessoa

Possíveis métricas:

- tarefas executadas;
- horas trabalhadas;
- tempo por tipo;
- quantidade de atividades;
- participação em retrabalho;
- tempo de resposta.

Essas métricas precisam ser usadas com contexto.

---

# 90. Métrica não é avaliação de desempenho automática

A LPS não deve transformar:

```text
tempo maior
```

automaticamente em:

```text
desempenho pior
```

Antes é necessário considerar contexto.

---

# 91. Contexto necessário para métricas de pessoa

Pode incluir:

- dificuldade;
- volume;
- tipo;
- qualidade;
- dependência;
- retrabalho originado por terceiros;
- experiência;
- interrupções.

---

# 92. Objetivo principal das métricas

O objetivo inicial é melhorar o sistema de trabalho.

Perguntas:

- Onde estamos esperando?
- Onde estamos repetindo?
- Onde falta capacidade?
- Onde falta treinamento?
- Onde o prazo não é realista?
- Onde existe excesso de aprovação?
- Onde existe concentração de conhecimento?

---

# 93. Tempo de ciclo

Conceitualmente, tempo de ciclo pode representar:

```text
início real da execução
↓
conclusão
```

A definição precisa ser padronizada por métrica.

---

# 94. Lead time

Lead time pode representar:

```text
criação da demanda
↓
conclusão
```

A LPS pode usar termos em português na interface.

Não é obrigatório expor terminologia técnica.

---

# 95. Throughput

Throughput representa quantas unidades de trabalho são concluídas em determinado período.

Exemplo:

```text
Compras:
24 tarefas concluídas/dia
```

Pode ser útil futuramente para capacidade.

---

# 96. Work in Progress

WIP significa **Work in Progress**, ou trabalho em andamento.

Exemplo:

```text
12 tarefas em execução simultânea
```

Monitorar WIP pode ajudar a identificar excesso de multitarefa.

Não precisa ser um conceito obrigatório na interface inicial.

---

# 97. Backlog

Backlog representa trabalho ainda não concluído.

Pode incluir:

- tarefas aguardando;
- tarefas em execução;
- tarefas bloqueadas.

A definição operacional precisa ser consistente.

---

# 98. Aging

Aging representa há quanto tempo um item está aberto ou parado.

Exemplo:

```text
Esta tarefa está na fila há 4 dias.
```

Esse indicador pode ser muito útil.

---

# 99. Métrica de envelhecimento da fila

Exemplo:

```text
Tarefa mais antiga:
9 dias

Mediana:
1,7 dia
```

Pode indicar item esquecido.

---

# 100. Tempo até primeira resposta x primeira ação

Podem ser conceitos diferentes.

Resposta:

```text
“Recebi sua solicitação.”
```

Ação:

```text
começou a executar
```

No D0, priorizar primeira ação operacional.

Se resposta formal se tornar relevante, criar métrica separada.

---

# 101. Tempo entre setores

Exemplo:

```text
Compras concluiu:
10:00

Financeiro recebeu:
10:02

Financeiro iniciou:
16:00
```

Temos:

```text
transição:
2min

fila no Financeiro:
5h58
```

A LPS deve evitar misturar os dois.

---

# 102. Entrada no setor

O momento de entrada deve ser registrado automaticamente quando o fluxo movimenta a tarefa.

---

# 103. Saída do setor

O momento de saída deve ser registrado quando a tarefa é encaminhada, concluída ou devolvida.

---

# 104. Permanência por passagem

Se a mesma tarefa entra duas vezes no mesmo setor, cada passagem precisa ser separada.

Exemplo:

```text
Compras — passagem 1
Compras — passagem 2
```

Depois, consolidar se necessário.

---

# 105. Tempo por passagem

Isso permite identificar:

```text
Primeira passagem:
20h

Segunda:
5h
```

---

# 106. Tempo de correção

Quando existe devolução, pode ser medido o tempo entre:

```text
devolução
```

e:

```text
correção concluída
```

---

# 107. Tempo de reentrada

Também pode ser medido:

```text
correção concluída
↓
reentrada na etapa original
```

---

# 108. Qualidade da auditoria

Uma boa auditoria precisa ser:

- automática sempre que possível;
- consistente;
- imutável como histórico;
- vinculada ao usuário autenticado;
- vinculada ao objeto correto;
- ordenável por tempo.

---

# 109. Usuário autenticado

Toda ação deve, quando aplicável, registrar quem estava autenticado.

Evitar campos manuais como:

```text
Nome de quem alterou:
________
```

---

# 110. Timestamp do servidor

Sempre que possível, timestamps críticos devem ser registrados pelo servidor.

Isso reduz manipulação de horário.

---

# 111. Fuso horário

A LPS atende organizações potencialmente em locais diferentes.

A arquitetura deve armazenar tempo de forma consistente e exibir no fuso adequado.

A implementação técnica será definida no banco.

---

# 112. Alteração retroativa de tempo

Pode existir necessidade de apropriação posterior.

Exemplo:

A pessoa trabalhou sem iniciar o timer e precisa lançar depois.

Isso deve ser permitido conforme autorização.

Mas precisa ficar auditado como:

```text
lançamento manual posterior
```

---

# 113. Tempo automático x tempo manual

O sistema deve distinguir:

```text
tempo capturado pelo timer
```

de:

```text
tempo lançado manualmente
```

Isso ajuda a avaliar confiabilidade.

---

# 114. Correção de tempo

Se alguém corrigir uma sessão:

Registrar:

- valor anterior;
- novo valor;
- quem corrigiu;
- quando;
- motivo quando exigido.

---

# 115. Sessões sobrepostas da mesma pessoa

A LPS deve evitar que a mesma pessoa registre trabalho ativo simultaneamente em duas tarefas, salvo decisão explícita futura.

A regra conceitual discutida anteriormente é:

> iniciar uma nova atividade/tarefa de trabalho pausa a anterior.

Isso evita dupla contagem de tempo.

---

# 116. Trabalho simultâneo entre pessoas

É permitido.

A restrição é por pessoa, não por tarefa.

---

# 117. Pausas curtas

Pausas como:

- banheiro;
- café;
- almoço;

não devem necessariamente ser tratadas como gargalo da tarefa.

A política exata precisa ser definida em documento posterior.

---

# 118. Apropriação posterior

A pessoa pode concluir a atividade e deixar tempo pendente de apropriação, caso esse comportamento seja mantido no produto.

Se utilizado, precisa existir indicador:

```text
tempo pendente de apropriação
```

---

# 119. Qualidade do tempo

A LPS pode futuramente mostrar a origem dos dados:

```text
92% automático
8% manual
```

Isso ajuda a interpretar métricas.

---

# 120. Auditoria de dono

Toda mudança de dono precisa registrar:

- dono anterior;
- dono novo;
- usuário que alterou;
- data/hora.

---

# 121. Auditoria de executor

Registrar:

- atribuição;
- inclusão;
- remoção;
- transferência.

Nunca apagar participação histórica.

---

# 122. Auditoria de setor

Toda mudança de setor precisa registrar:

- origem;
- destino;
- usuário;
- motivo quando necessário;
- momento.

---

# 123. Auditoria de status

Toda mudança de status precisa registrar:

- anterior;
- novo;
- usuário;
- data/hora.

---

# 124. Auditoria de prazo

Registrar:

- prazo original;
- novo prazo;
- tipo de prazo;
- proposta;
- aceite;
- rejeição;
- usuário.

---

# 125. Auditoria de posição

Registrar:

- posição anterior;
- posição nova;
- total anterior;
- total novo;
- mudança automática ou manual;
- usuário quando manual.

---

# 126. Auditoria de conteúdo

Alterações em:

- título;
- descrição;
- observação;
- campos relevantes;

podem precisar de histórico.

A LPS não precisa versionar cada caractere no D0.

Mas mudanças críticas devem ser rastreáveis.

---

# 127. Auditoria de exclusão

Registros operacionais com histórico não devem desaparecer.

Preferir:

- cancelamento;
- inativação;
- arquivamento.

Se exclusão for permitida, ela precisa ser altamente restrita e registrada.

---

# 128. Auditoria de conclusão

Registrar:

- quem concluiu;
- quando;
- qual resultado;
- eventuais observações.

---

# 129. Auditoria de reabertura

Registrar:

- quem reabriu;
- quando;
- motivo;
- estado anterior.

---

# 130. Auditabilidade de inteligência futura

Quando a IA passar a sugerir algo, registrar:

- recomendação;
- modelo/versão quando aplicável;
- dados utilizados;
- usuário que aceitou ou rejeitou;
- resultado.

A recomendação nunca deve se misturar com fato.

---

# 131. Métricas de fluxo

Algumas métricas importantes:

```text
tempo total
```

```text
tempo até primeira ação
```

```text
tempo em fila
```

```text
tempo em execução
```

```text
tempo bloqueado
```

```text
tempo externo
```

```text
horas-homem
```

```text
quantidade de devoluções
```

```text
quantidade de pessoas
```

---

# 132. Soma dos tempos e sobreposição

É importante não somar categorias de forma incorreta.

Exemplo:

Se duas pessoas trabalham simultaneamente, horas-homem somam.

Mas tempo cronológico não deve duplicar o intervalo.

---

# 133. Tempo cronológico da atividade

Representa a linha do tempo real.

Não pode somar tarefas paralelas como se fossem sequenciais.

---

# 134. Exemplo de paralelismo

```text
Tarefa A:
08:00–10:00

Tarefa B:
08:30–11:00
```

Soma das durações:

```text
4h30
```

Janela cronológica:

```text
3h
```

Esses números representam coisas diferentes.

---

# 135. Duração de atividade com tarefas paralelas

A duração total continua:

```text
conclusão final
-
criação
```

Não é soma simples das durações das tarefas.

---

# 136. Horas-homem da atividade

Pode ser soma das sessões de todos os executores de todas as tarefas.

---

# 137. Tempo de espera acumulado

Pode somar períodos de espera de tarefas.

Mas, em fluxos paralelos, o valor acumulado não deve ser confundido com atraso cronológico da atividade.

---

# 138. Métricas agregadas precisam de nome claro

Evitar rótulos genéricos como:

```text
Tempo
```

Preferir:

```text
Tempo total da atividade
Tempo trabalhado
Horas-homem
Tempo em fila
Tempo bloqueado
```

---

# 139. Data e hora de conclusão

Devem ser automáticas no evento de conclusão.

Se houver correção posterior, registrar a correção.

---

# 140. Tempo até conclusão

Pode ser calculado desde:

```text
criação
```

até:

```text
conclusão
```

---

# 141. Atividades abertas

Para atividades ainda abertas, calcular:

```text
idade atual
=
agora
-
criação
```

Isso ajuda a identificar demandas antigas.

---

# 142. Tarefas abertas

Mesma lógica:

```text
idade da tarefa
```

---

# 143. Tarefa parada há muito tempo

Pode gerar indicador:

```text
sem ação há X horas/dias
```

Futuramente, pode gerar alerta.

---

# 144. Última ação relevante

A LPS deve conseguir registrar:

```text
última_acao_em
```

Isso é útil para detectar esquecimento.

---

# 145. Tempo desde última ação

Fórmula:

```text
agora
-
ultima_acao_relevante
```

---

# 146. Inatividade

Inatividade prolongada pode indicar:

- esquecimento;
- bloqueio não registrado;
- fila;
- dependência;
- baixa prioridade.

A LPS não deve presumir a causa.

---

# 147. Métricas de devolução

Exemplos:

- devoluções por atividade;
- devoluções por tarefa;
- devoluções por setor;
- devoluções por motivo;
- tempo médio de correção;
- horas-homem de retrabalho.

---

# 148. Métricas de fluxo planejado x real

Exemplos:

- etapas adicionadas;
- etapas removidas;
- retornos;
- desvios;
- quantidade de mudanças.

---

# 149. Métricas de prazo

Exemplos:

- solicitado x comprometido;
- comprometido x concluído;
- quantidade de renegociações;
- percentual no prazo;
- atraso médio;
- antecipação média.

---

# 150. Cumprimento do prazo

Exemplo conceitual:

```text
cumpriu_prazo_comprometido
=
conclusao <= prazo_comprometido
```

---

# 151. Concluído antes do prazo

Também é dado.

Mas concluir muito antes não significa automaticamente alta performance.

Pode existir prazo excessivamente folgado.

---

# 152. Acurácia do prazo

Com histórico, a LPS poderá medir:

> Quão próximo o prazo comprometido costuma ficar do realizado?

Essa métrica ajuda a avaliar capacidade de previsão.

---

# 153. Métricas de fila

Exemplos:

- posição de entrada;
- posição máxima;
- posição mínima;
- quantidade de mudanças;
- tempo em cada posição;
- tempo total em fila;
- total da fila ao entrar.

---

# 154. Posição e tempo

Estar em 4 de 17 durante dez minutos é diferente de estar em 4 de 17 durante dois dias.

A LPS deve registrar timestamps das mudanças.

---

# 155. Reordenação manual

Pode ser métrica:

```text
quantidade de reordenações manuais
```

Muitas reordenações podem indicar instabilidade de prioridade.

---

# 156. Furação de fila

Futuramente, a LPS pode identificar:

- quantas tarefas entraram na frente;
- quantas vezes;
- em quais setores;
- por quais motivos.

Isso pode revelar cultura de urgência constante.

---

# 157. Métricas de setor por período

Exemplo:

```text
Setor:
Compras

Período:
Setembro

Entraram:
180 tarefas

Concluídas:
150

Backlog:
+30
```

Isso indica crescimento de fila.

---

# 158. Taxa de entrada e saída

Conceitualmente:

```text
entrada > saída
→ backlog cresce
```

```text
saída > entrada
→ backlog reduz
```

---

# 159. Gargalo por tendência

Não basta olhar uma fotografia.

A tendência importa.

Exemplo:

```text
Fila:
20 → 28 → 35 → 47
```

O setor está acumulando demanda.

---

# 160. Comparação por período

Exemplos:

- esta semana x semana passada;
- este mês x mês anterior;
- antes x depois de mudança de processo.

---

# 161. Medir efeito de melhoria

Exemplo:

Antes do novo checklist:

```text
devoluções:
28%
```

Depois:

```text
devoluções:
12%
```

A LPS pode demonstrar resultado da melhoria.

---

# 162. Medir efeito de treinamento

Exemplo:

Antes:

```text
Ryan:
3h por levantamento
```

Depois do treinamento:

```text
1h45
```

Isso ajuda a validar ganho real.

---

# 163. Medir capital intelectual

Diferenças consistentes entre executores podem indicar conhecimento concentrado.

A LPS pode ajudar a descobrir oportunidades de:

- treinamento;
- padronização;
- documentação;
- mentoria.

---

# 164. Métrica não deve incentivar manipulação

Se pessoas forem avaliadas apenas por velocidade, podem:

- concluir cedo demais;
- reduzir qualidade;
- evitar tarefas complexas.

Por isso, métricas precisam ser combinadas com contexto e resultado.

---

# 165. Auditoria protege a confiabilidade das métricas

Se tempos e status podem ser alterados sem rastro, indicadores perdem valor.

Por isso, correções precisam ser auditadas.

---

# 166. Fonte do dado

Futuramente, pode ser útil identificar:

```text
automático
manual
importado
integração
IA sugeriu
```

Isso aumenta rastreabilidade.

---

# 167. Eventos automáticos

Exemplos:

- criação;
- entrada em fila;
- mudança de posição automática;
- mudança de setor;
- conclusão.

---

# 168. Eventos manuais

Exemplos:

- motivo de devolução;
- ajuste de prazo;
- ajuste de tempo;
- mudança de dono;
- escalonamento manual.

---

# 169. Eventos de integração

Futuramente:

```text
Pagamento confirmado pelo ERP
```

Pode gerar evento automaticamente.

O histórico precisa identificar a origem.

---

# 170. Auditoria de integrações

Registrar:

- sistema origem;
- identificador externo;
- data/hora;
- resultado;
- usuário técnico quando aplicável.

---

# 171. Auditoria e segurança

Alguns registros de auditoria devem ser protegidos contra alteração por usuários comuns.

A implementação técnica será tratada no banco.

---

# 172. Retenção do histórico

A LPS depende do histórico para aprender.

Logo, dados de auditoria operacional não devem ser descartados prematuramente.

A política legal e técnica será definida futuramente.

---

# 173. Privacidade

Auditoria não significa que todos podem ver tudo.

A visualização do histórico deve respeitar:

- organização;
- empresa;
- setor;
- papel;
- autorização;
- escopo.

---

# 174. Auditoria interna x visualização do usuário

O sistema pode armazenar mais detalhes do que mostra ao usuário final.

Exemplo:

Solicitante vê:

```text
Posição alterada
```

Gestor autorizado pode ver:

```text
Alterada de 4 para 16 por Igor às 14:07.
```

---

# 175. Métricas e anonimização

Futuramente, comparações entre empresas devem considerar anonimização e autorização.

No D0, o aprendizado deve priorizar a própria organização.

---

# 176. Indicadores do dono da atividade

O dono pode acompanhar:

- tempo total;
- posição atual;
- prazo;
- tarefas abertas;
- tarefas devolvidas;
- última ação;
- tempo sem movimentação.

---

# 177. Indicadores do executor

O executor pode acompanhar:

- tarefas atuais;
- tempo trabalhado;
- fila;
- prazos;
- sessões;
- pendências.

---

# 178. Indicadores do gestor

O gestor pode acompanhar:

- backlog;
- aging;
- tempo em fila;
- execução;
- gargalos;
- devoluções;
- carga;
- atrasos;
- conflitos;
- escalonamentos.

---

# 179. Indicadores não devem aumentar burocracia

O colaborador não deve preencher um relatório manual diário para gerar métricas que a própria LPS consegue calcular.

---

# 180. Princípio de captura automática

> Quanto mais informação puder ser inferida de ações reais do sistema, menos campos manuais devem existir.

---

# 181. Exemplo completo de atividade

```text
Atividade:
Material disponível na obra

Criada:
10/09 08:00

Primeira ação:
10/09 10:17

Tempo até primeira ação:
2h17
```

---

# 182. Exemplo de Engenharia

```text
Entrada:
10/09 10:17

Trabalho:
1h20

Saída:
10/09 11:37
```

---

# 183. Exemplo de fila de Compras

```text
Entrada na fila:
10/09 11:37

Início:
11/09 06:17

Tempo em fila:
18h40
```

---

# 184. Exemplo de execução de Compras

```text
Execução:
2h10
```

---

# 185. Exemplo de Financeiro

```text
Permanência:
4h30
```

---

# 186. Exemplo de fornecedor

```text
Espera externa:
7 dias
```

---

# 187. Exemplo consolidado

```text
Atividade criada          10/09 08:00

Primeira ação             10/09 10:17
Tempo até agir            2h17

Engenharia                1h20 trabalho
Fila Compras              18h40 espera
Compras                   2h10 trabalho
Financeiro                4h30 permanência
Fornecedor                7 dias espera externa

Tempo total               8d 03h
```

---

# 188. Interpretação do exemplo

Sem separação:

```text
Atividade levou 8 dias.
```

Com LPS:

```text
A maior parcela do tempo ocorreu no fornecedor.
```

Isso muda completamente a decisão gerencial.

---

# 189. Outro exemplo: orçamento

```text
Atividade:
Entregar orçamento
```

Dados:

```text
Criação:
segunda 08:00

Primeira ação:
segunda 08:15

Quantitativo:
6h de trabalho
3 executores

Cotação:
1d8h de fila
2h de trabalho

Revisão:
4h de espera
1h de trabalho

Aprovação:
10h de espera
20min de análise
```

A atividade pode estar perdendo mais tempo esperando aprovação do que sendo produzida.

---

# 190. Outro exemplo: retrabalho

```text
Tarefa:
Cotação

Execução inicial:
1h30

Devolução:
especificação incompleta

Correção:
2h

Nova execução:
45min
```

Esforço total:

```text
4h15
```

Sem auditoria, talvez a empresa enxergasse apenas os 45 minutos finais.

---

# 191. Métrica de retrabalho

Futuramente:

```text
retrabalho_horas
```

pode ser calculado quando etapas são classificadas como correção.

---

# 192. Percentual de retrabalho

Conceitualmente:

```text
horas_retrabalho
/
horas_totais
```

Essa métrica precisa de classificação confiável.

Não deve ser implementada de forma precipitada.

---

# 193. Tempo perdido x tempo necessário

A LPS não deve chamar toda espera de “desperdício”.

Algumas esperas são inerentes.

Exemplo:

```text
cura do concreto
```

ou:

```text
prazo logístico do fornecedor
```

O sistema registra.

A gestão decide se há oportunidade de melhoria.

---

# 194. Métrica de gargalo precisa de contexto

Não criar automaticamente uma lista:

```text
Pior setor: Financeiro
```

apenas porque a permanência foi alta.

Pode ter ocorrido:

- dependência;
- bloqueio;
- espera externa;
- falta de informação.

---

# 195. Indicadores explicáveis

Sempre que possível, um indicador deve permitir navegar até os eventos que o compõem.

Exemplo:

```text
Tempo em Compras:
22h
```

Ao abrir:

```text
18h40 fila
2h10 execução
1h10 espera classificada
```

---

# 196. Métricas auditáveis

O usuário deve poder entender de onde o número veio.

Isso aumenta confiança.

---

# 197. Resumo automático futuro

A LPS poderá gerar resumo como:

> A atividade levou 8 dias e 3 horas. O maior tempo ocorreu aguardando fornecedor, com 7 dias. Houve uma devolução de Compras para Engenharia por especificação incompleta, adicionando 20 horas ao ciclo.

Esse resumo deve ser derivado dos dados reais.

---

# 198. Resumo não substitui dados

O resumo é uma camada de leitura.

Os eventos continuam sendo a fonte.

---

# 199. Base para previsão

Para prever prazo no futuro, a LPS precisará de histórico de:

- duração;
- fila;
- execução;
- bloqueio;
- terceiros;
- devoluções;
- tipo de atividade;
- fluxo.

Por isso, este documento é central para a retroalimentação.

---

# 200. Base para recomendação

Para recomendar melhoria, a LPS precisará saber:

- onde perdeu tempo;
- onde voltou;
- onde acumulou;
- quais motivos se repetem;
- quais pessoas dominam determinados trabalhos.

---

# 201. Base para treinamento

Exemplo:

```text
Jennifer:
mediana 1h10

Ryan:
mediana 2h50
```

Em atividades comparáveis.

Isso pode gerar recomendação futura:

> Avaliar compartilhamento de método entre executores.

Não uma punição automática.

---

# 202. Base para padronização

Se uma sequência gera menos devoluções, a LPS pode futuramente sugerir sua adoção como padrão.

---

# 203. Base para dimensionamento

Com dados de volume e tempo, a gestão pode estimar:

- capacidade;
- necessidade de pessoas;
- carga;
- gargalos;
- cenários.

---

# 204. Dados necessários desde o D0

Para não perder capacidade futura, o D0 precisa registrar corretamente:

- timestamps;
- eventos;
- usuários;
- setores;
- tarefas;
- atividades;
- sessões;
- posição;
- prazos;
- devoluções;
- motivos;
- mudanças.

---

# 205. O que não precisamos calcular no D0

Não é necessário no D0:

- previsão por IA;
- percentis avançados;
- benchmarking externo;
- ranking de pessoas;
- modelos preditivos;
- custo por minuto automatizado;
- score complexo de produtividade.

---

# 206. O que precisa funcionar no D0

O D0 precisa conseguir responder:

```text
Quando foi criada?
```

```text
Quando aconteceu a primeira ação?
```

```text
Quanto tempo ficou na fila?
```

```text
Quanto tempo foi trabalhado?
```

```text
Quantas pessoas trabalharam?
```

```text
Por quais setores passou?
```

```text
Quanto tempo ficou em cada setor?
```

```text
Quantas vezes voltou?
```

```text
Por que voltou?
```

```text
Quanto tempo total levou?
```

---

# 207. Regras de cálculo devem ser centralizadas

Evitar cada relatório calcular de um jeito.

A definição de:

```text
tempo em fila
```

precisa ser única.

Da mesma forma:

- tempo total;
- horas-homem;
- primeira ação;
- atraso;
- devolução.

---

# 208. Dicionário de métricas

A LPS deve futuramente manter um dicionário oficial com:

- nome;
- definição;
- fórmula;
- unidade;
- fonte;
- exceções.

Isso evita divergência entre relatórios.

---

# 209. Exemplo de dicionário

```text
Métrica:
Tempo até primeira ação

Definição:
Intervalo entre criação da atividade e primeira ação operacional relevante.

Unidade:
tempo

Fonte:
eventos de auditoria
```

---

# 210. Unidades de tempo

A LPS pode exibir conforme escala:

```text
35 min
```

```text
2h15
```

```text
3d 4h
```

Internamente, precisa manter precisão consistente.

---

# 211. Arredondamento

Relatórios podem arredondar.

Mas o dado bruto deve preservar precisão suficiente.

---

# 212. Eventos simultâneos

Podem ocorrer eventos no mesmo segundo.

A ordenação precisa ser consistente tecnicamente.

---

# 213. Integridade temporal

Evitar estados impossíveis como:

```text
conclusão anterior à criação
```

ou:

```text
fim de sessão anterior ao início
```

O banco e aplicação devem validar.

---

# 214. Alterações retroativas

Quando permitidas, precisam ser claramente marcadas.

Exemplo:

```text
Sessão lançada em 15/09 referente a trabalho de 12/09.
```

---

# 215. Auditoria de correção

Nunca substituir silenciosamente.

Exemplo:

```text
Valor original:
2h

Corrigido para:
1h30

Por:
Paulo

Motivo:
Timer permaneceu ativo após término.
```

---

# 216. Métricas provisórias

Enquanto uma atividade está aberta, algumas métricas são parciais.

Exemplo:

```text
Tempo total até agora:
4d 6h
```

A interface precisa diferenciar dado final de dado em andamento.

---

# 217. Atividade aberta sem primeira ação

Indicador:

```text
Tempo aguardando primeira ação:
6h20
```

Pode ser relevante para gestão.

---

# 218. Tarefa sem executor

A LPS pode medir:

```text
tempo sem responsável
```

se isso for relevante.

Exemplo:

```text
Criada:
08:00

Executor atribuído:
13:00

Tempo sem executor:
5h
```

---

# 219. Tempo para assumir

Pode ser outra métrica futura.

Não precisa ser destaque no D0.

---

# 220. Tempo entre atribuição e início

Exemplo:

```text
Executor atribuído:
10:00

Início:
15:00

Tempo:
5h
```

Pode indicar fila pessoal ou capacidade.

---

# 221. Multitarefa

Se uma pessoa alterna constantemente entre tarefas, a LPS poderá observar:

- quantidade de trocas;
- sessões curtas;
- fragmentação.

Isso pode revelar desperdício por multitarefa.

---

# 222. Não medir multitarefa como produtividade automaticamente

Trocas podem ser necessárias.

A LPS apenas registra padrão.

---

# 223. Interrupções

Futuramente, interrupções podem ser classificadas quando fizer sentido.

No D0, evitar excesso de campos.

---

# 224. Eficiência de fluxo

Uma métrica futura pode comparar:

```text
tempo trabalhado
/
tempo total
```

Isso mostra quanto do ciclo foi execução versus espera.

Mas precisa ser interpretado com cuidado.

---

# 225. Exemplo de eficiência de fluxo

```text
Tempo total:
100h

Tempo trabalhado:
10h

Razão:
10%
```

Isso não significa automaticamente ineficiência.

Pode existir espera externa inevitável.

---

# 226. Tempo controlável x não controlável

Futuramente, a LPS pode classificar:

```text
interno controlável
```

```text
externo
```

```text
necessário
```

```text
não classificado
```

Isso ajuda a priorizar melhorias.

---

# 227. Cuidado com excesso de classificação

No D0, categorias demais aumentam esforço de uso.

Priorizar:

- fila;
- execução;
- bloqueio;
- externo;
- devolução.

---

# 228. Qualidade antes de quantidade de métricas

É melhor ter cinco métricas confiáveis que cinquenta métricas inconsistentes.

---

# 229. Métricas iniciais prioritárias

Sugestão para o D0:

1. tempo total;
2. tempo até primeira ação;
3. tempo em fila;
4. horas-homem;
5. tempo por setor;
6. devoluções;
7. prazo solicitado x comprometido x realizado;
8. quantidade de pessoas.

---

# 230. Métricas secundárias

Depois:

- aging;
- throughput;
- retrabalho;
- taxa de renegociação;
- concentração por executor;
- capacidade;
- previsão.

---

# 231. Auditoria precisa nascer antes dos dashboards

Não faz sentido construir dashboard sofisticado sem histórico confiável.

---

# 232. Dashboard é consequência

A ordem correta é:

```text
eventos
↓
dados confiáveis
↓
métricas
↓
dashboard
```

---

# 233. Não criar indicador só porque é bonito

Todo indicador deve responder a uma decisão.

Pergunta:

> O que o gestor fará diferente ao ver esse número?

Se não houver resposta, a métrica pode não ser necessária.

---

# 234. Exemplo de métrica útil

```text
Tempo médio em fila:
3,2 dias
```

Decisão possível:

- aumentar capacidade;
- mudar prioridade;
- redesenhar fluxo.

---

# 235. Exemplo de métrica pouco útil isoladamente

```text
2.437 cliques realizados
```

Sem relação clara com gestão do trabalho.

---

# 236. Indicadores do processo, não vaidade

A LPS deve priorizar métricas que expliquem:

- fluxo;
- capacidade;
- espera;
- qualidade;
- prazo;
- resultado.

---

# 237. Auditoria de mensagens

Mensagens podem possuir:

- autor;
- timestamp;
- edição;
- exclusão controlada.

Mas o conteúdo da conversa não substitui o histórico operacional.

---

# 238. Mensagem editada

Se mensagens forem editáveis, pode ser necessário registrar edição.

A regra detalhada pertence ao documento de comunicação.

---

# 239. Eventos gerados por conversa

Futuramente, uma mensagem pode gerar sugestão:

```text
Possível alteração de prazo detectada.
```

Somente após confirmação vira evento operacional.

---

# 240. Auditoria de notificações

Pode ser útil saber:

- notificação gerada;
- entregue;
- lida.

Não é prioridade central do D0.

---

# 241. Ciência do gestor

Quando regra exigir ciência, pode ser registrado:

```text
gestor notificado
```

e, se necessário:

```text
gestor confirmou ciência
```

São eventos diferentes.

---

# 242. Escalonamento

A auditoria deve registrar:

- abertura;
- motivo;
- destinatários;
- decisão;
- fechamento;
- tempo até decisão.

---

# 243. Tempo de escalonamento

Exemplo:

```text
Escalado:
10:00

Decisão:
14:30

Tempo:
4h30
```

Isso permite descobrir se a gestão também é gargalo.

---

# 244. Tempo de aprovação

Quando houver aprovação:

```text
solicitada
↓
decidida
```

Pode ser medido separadamente.

---

# 245. Aprovações lentas

Podem ser gargalos tão relevantes quanto execução.

---

# 246. Métrica de decisão

Futuramente:

```text
tempo médio para decisão
```

por tipo de aprovação ou gestor.

Precisa ser interpretada com contexto.

---

# 247. Atividade encerrada com pendência

Idealmente não deve acontecer sem regra clara.

Se houver exceção, registrar.

---

# 248. Cancelamento

Ao cancelar:

- data;
- usuário;
- motivo;
- estágio;
- horas consumidas.

Isso permite medir trabalho perdido.

---

# 249. Trabalho cancelado

Uma atividade cancelada também possui valor analítico.

Exemplo:

```text
12h de esforço consumidas antes do cancelamento.
```

---

# 250. Desperdício

A LPS pode futuramente identificar categorias de desperdício:

- espera;
- retrabalho;
- superprocessamento;
- multitarefa;
- interrupção;
- falta de padrão;
- comunicação;
- priorização.

Mas não precisa classificar tudo automaticamente no D0.

---

# 251. Base para desperdício

A auditoria precisa registrar fatos que permitam inferência futura.

Exemplo:

```text
3 devoluções
+
8h de correção
```

pode indicar retrabalho.

---

# 252. Métricas por cliente

Futuramente:

- duração;
- devoluções;
- espera;
- renegociações.

Isso pode revelar clientes que geram maior retrabalho.

Precisa respeitar contexto.

---

# 253. Métricas por obra

Futuramente:

- volume;
- horas;
- gargalos;
- setores;
- prazos.

---

# 254. Métricas por tipo de atividade

Muito importante para aprendizado.

Exemplo:

```text
Tipo:
Orçamento

Mediana:
4,2 dias
```

---

# 255. Métricas por fluxo

Comparar versões diferentes de um mesmo processo pode demonstrar melhoria.

---

# 256. Métricas por período

A LPS deve permitir corte temporal.

Exemplo:

```text
últimos 7 dias
```

```text
últimos 30 dias
```

```text
trimestre
```

---

# 257. Métricas em tempo real x fechadas

Algumas métricas são atuais.

Exemplo:

```text
fila agora
```

Outras são históricas.

Exemplo:

```text
tempo médio das últimas 100 atividades
```

Não misturar.

---

# 258. Dados incompletos

Se uma tarefa não possui registros suficientes, a LPS deve indicar:

```text
dados insuficientes
```

em vez de fabricar estimativa.

---

# 259. Confiabilidade

Futuramente, a LPS pode calcular qualidade dos dados.

Exemplo:

```text
85% das tarefas possuem timer completo.
```

Não é prioridade do D0.

---

# 260. Dados faltantes como insight

Se um setor frequentemente não inicia/pausa corretamente, isso pode indicar dificuldade de adoção.

A própria qualidade dos dados pode apontar melhoria de UX.

---

# 261. Dado corrigido não deve contaminar silenciosamente histórico

A correção deve ser válida para os cálculos atuais, mas o histórico da mudança deve permanecer.

---

# 262. Snapshot x evento

A LPS terá estados atuais, como:

```text
status atual
```

e eventos históricos, como:

```text
mudou de A para B às 10:15
```

Os dois são necessários.

---

# 263. Estado atual facilita uso

A interface precisa saber rapidamente:

- status;
- responsável;
- posição;
- prazo atual.

---

# 264. Eventos permitem reconstrução

A auditoria explica como chegou ao estado atual.

---

# 265. Evento não deve ser apagado ao editar estado

Essa separação é crítica.

---

# 266. Métricas derivadas devem ser recalculáveis

Sempre que possível, uma métrica importante deve poder ser reconstruída a partir dos dados básicos.

Exemplo:

```text
tempo total
```

a partir de:

```text
criação + conclusão
```

---

# 267. Evitar armazenar números derivados sem necessidade

Guardar:

```text
tempo_total = 8h
```

pode gerar inconsistência se timestamps forem corrigidos.

A decisão técnica será feita no banco.

---

# 268. Cache de métricas

Futuramente, por performance, métricas podem ser pré-calculadas.

Mas a fonte de verdade deve continuar clara.

---

# 269. Auditoria como fonte de verdade histórica

O histórico precisa ser confiável o suficiente para sustentar:

- relatórios;
- análise;
- IA;
- decisões.

---

# 270. Perguntas que a auditoria precisa responder

- Quem criou?
- Quando criou?
- Quem era o dono?
- O dono mudou?
- Quem criou cada tarefa?
- Quando entrou em cada setor?
- Quanto ficou?
- Quem trabalhou?
- Quanto trabalhou?
- Quando pausou?
- Quando voltou?
- Quando foi devolvida?
- Por quê?
- Quem mudou o prazo?
- Quem reordenou a fila?
- Quem concluiu?
- Quando concluiu?

---

# 271. Perguntas que as métricas precisam responder

- Quanto tempo levou?
- Quanto tempo esperou?
- Quanto tempo trabalhou?
- Onde ficou mais?
- Qual foi a etapa mais rápida?
- Qual foi a mais lenta?
- Quantas pessoas participaram?
- Quantas horas-homem foram consumidas?
- Quantas vezes voltou?
- Qual foi o maior motivo de retorno?
- O prazo foi cumprido?
- Houve renegociação?
- Houve escalonamento?

---

# 272. Perguntas que o gestor deverá responder com a LPS

- Onde está o gargalo?
- Ele é fila ou execução?
- É interno ou externo?
- É recorrente?
- O processo precisa mudar?
- Falta gente?
- Falta treinamento?
- Falta padrão?
- Falta informação?
- O prazo está sendo mal estimado?
- Existe concentração de conhecimento?

---

# 273. Dados para retroalimentação

Este documento gera a base para o `07_INTELIGENCIA_E_RETROALIMENTACAO.md`.

Sem:

- eventos;
- timestamps;
- tempos;
- motivos;
- fluxos;
- prazos;

não existe aprendizado confiável.

---

# 274. Evolução esperada

```text
D0
Registrar eventos confiáveis
↓
D1
Exibir métricas e gargalos
↓
D2
Identificar padrões
↓
D3
Prever
↓
D4
Recomendar
```

Os nomes de fases podem ser ajustados no roadmap.

---

# 275. O que pertence ao D0

O D0 precisa possuir:

- data de criação;
- usuário criador;
- dono;
- timestamps principais;
- primeira ação;
- início;
- pausa;
- retomada;
- conclusão;
- sessões por executor;
- entrada e saída de setor;
- entrada em fila;
- início de execução;
- devolução;
- motivo;
- prazo;
- alterações relevantes;
- histórico de posição;
- auditoria de mudanças.

---

# 276. O que pode ficar depois do D0

Pode ficar para evolução:

- calendário útil sofisticado;
- percentis;
- previsão automática;
- score de gargalo;
- ranking;
- cálculo avançado de capacidade;
- análise estatística;
- IA;
- classificação automática de desperdício;
- benchmarking entre empresas;
- custo completo por atividade.

---

# 277. Métricas mínimas do D0

A primeira versão deve ser capaz de calcular pelo menos:

1. tempo total da atividade;
2. tempo até primeira ação;
3. tempo por tarefa;
4. tempo por setor;
5. tempo em fila;
6. tempo efetivamente trabalhado;
7. horas-homem;
8. quantidade de pessoas envolvidas;
9. quantidade de devoluções;
10. planejado x realizado básico.

---

# 278. Métricas recomendadas para D1

Depois:

- aging;
- throughput;
- cumprimento de prazo;
- renegociação;
- tempo de bloqueio;
- tempo externo;
- retrabalho;
- tempo de decisão;
- tendência de backlog.

---

# 279. Decisões consolidadas neste documento

## Auditoria

- toda ação relevante precisa deixar rastro;
- histórico não deve desaparecer;
- alterações importantes guardam valor anterior e novo;
- usuário e timestamp devem ser registrados automaticamente;
- estado atual e histórico são conceitos diferentes.

## Tempo

- tempo total é diferente de tempo trabalhado;
- tempo em fila é diferente de execução;
- horas-homem somam esforço de várias pessoas;
- tarefas paralelas não devem inflar duração cronológica;
- múltiplas sessões precisam ser suportadas;
- lançamentos manuais devem ser distinguíveis dos automáticos.

## Setor

- medir entrada e saída;
- medir permanência;
- medir fila;
- medir trabalho;
- permitir múltiplas passagens pelo mesmo setor.

## Devolução

- toda devolução possui evento;
- motivo é obrigatório;
- quantidade deve ser mensurável;
- tempo de correção deve poder ser analisado.

## Métricas

- devem ser derivadas dos fatos sempre que possível;
- não devem gerar julgamento automático de pessoas;
- precisam de contexto;
- devem apoiar decisão;
- precisam ser explicáveis.

## Gargalos

- podem estar em fila, execução, retrabalho, decisão ou terceiros;
- não devem ser atribuídos automaticamente a um setor apenas pela duração;
- precisam ser identificados com evidência.

## Inteligência

- o D0 coleta;
- depois a LPS mede;
- depois compara;
- depois identifica padrões;
- somente então prevê e recomenda.

---

# 280. Decisões ainda pendentes

Precisam ser detalhadas posteriormente:

- definição formal de primeira ação;
- calendário útil no D0 ou D1;
- comportamento exato de pausas curtas;
- regra de lançamento retroativo;
- necessidade de aprovação de correção de tempo;
- classificação completa de bloqueios;
- definição de retrabalho;
- granularidade de auditoria de textos;
- retenção de histórico;
- política de exclusão;
- métricas oficiais por perfil;
- fórmulas estatísticas de previsão.

---

# 281. Relação com outros documentos

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Define os objetos cuja história será auditada.

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Define eventos de fila, prazo e escalonamento que alimentam métricas.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Define quem pode visualizar, alterar e corrigir dados auditados.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Usa eventos para gerar notificações e contexto.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Usa os dados gerados por este documento para aprender.

## `08_BANCO_DE_DADOS.md`

Traduzirá:

- eventos;
- sessões;
- históricos;
- timestamps;
- métricas deriváveis;

para estrutura técnica.

---

# 282. Exemplo de leitura gerencial completa

Sem LPS:

> Essa compra levou oito dias.

Com LPS:

```text
Tempo total:
8d 03h

Primeira ação:
2h17 após criação

Engenharia:
1h20 de trabalho

Fila de Compras:
18h40

Compras:
2h10 de trabalho

Financeiro:
4h30 de permanência

Fornecedor:
7 dias de espera externa

Devoluções:
1

Motivo:
especificação incompleta

Horas-homem:
5h50
```

Agora existe informação suficiente para gerir.

---

# 283. Regra de ouro da auditoria

> **Se algo relevante aconteceu, a LPS precisa conseguir provar quando aconteceu e quem realizou a ação.**

---

# 284. Regra de ouro do tempo

> **Tempo total, tempo de espera e tempo de trabalho são coisas diferentes e nunca devem ser tratados como a mesma métrica.**

---

# 285. Regra de ouro das métricas

> **Métrica existe para melhorar decisão, não para decorar dashboard.**

---

# 286. Regra de ouro dos gargalos

> **A LPS deve mostrar onde o tempo foi consumido antes de dizer onde está o problema.**

---

# 287. Regra de ouro do aprendizado

> **A qualidade da inteligência futura nunca será maior que a qualidade dos dados operacionais registrados hoje.**

---

# 288. Resumo funcional

A lógica completa pode ser representada assim:

```text
ATIVIDADE É CRIADA
↓
TIMESTAMP REGISTRADO
↓
PRIMEIRA AÇÃO
↓
TEMPO ATÉ PRIMEIRA AÇÃO
↓
TAREFA ENTRA EM SETOR
↓
TEMPO DE FILA
↓
EXECUTOR INICIA
↓
SESSÕES DE TRABALHO
↓
HORAS-HOMEM
↓
PAUSAS / ESPERAS / BLOQUEIOS
↓
MOVIMENTAÇÕES
↓
DEVOLUÇÕES
↓
NOVAS PASSAGENS
↓
CONCLUSÃO DAS TAREFAS
↓
CONCLUSÃO DA ATIVIDADE
↓
TEMPO TOTAL
↓
PLANEJADO X REALIZADO
↓
MÉTRICAS
↓
GARGALOS
↓
APRENDIZADO
```

---

# 289. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação das regras de auditoria, tempo e métricas da LPS |

---

# 290. Encerramento

A auditoria e o tempo são parte central da proposta da LPS.

O valor não está apenas em saber que uma tarefa foi concluída.

Está em conseguir explicar:

> quanto tempo levou;

> quanto tempo realmente foi trabalhado;

> quanto tempo ficou esperando;

> por quais setores passou;

> quantas pessoas participaram;

> quantas vezes voltou;

> por que voltou;

> onde ficou mais tempo;

> qual prazo havia sido planejado;

> o que realmente aconteceu.

Quando esses dados forem registrados de forma consistente, a LPS deixará de ser apenas uma ferramenta de acompanhamento e passará a formar uma memória operacional da empresa.

Essa memória é a base para identificar gargalos, melhorar processos, dimensionar capacidade e, posteriormente, permitir que a própria LPS aprenda com o histórico.
