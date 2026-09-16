# 07 — Inteligência e Retroalimentação

> Documento funcional da LPS para definir como o sistema deve aprender com a própria operação, transformar histórico em análise, análise em previsão e previsão em recomendação, sem fingir inteligência antes de possuir dados confiáveis.

---

# 1. Objetivo deste documento

Este documento define como a LPS deve evoluir de um sistema de registro e gestão do trabalho para uma plataforma capaz de aprender com a própria operação.

Ele deve responder:

- o que significa a LPS se retroalimentar;
- quais dados precisam ser coletados desde o D0;
- como o histórico de atividades, tarefas, filas, prazos, devoluções e conversas pode gerar aprendizado;
- como identificar padrões recorrentes;
- como detectar gargalos;
- como comparar processos;
- como evoluir de análise para previsão;
- como sugerir prazos;
- como sugerir fluxos;
- como sugerir melhorias;
- como utilizar IA no futuro sem criar uma “caixa-preta”;
- como diferenciar fato, cálculo, previsão e recomendação;
- como tratar aprendizado entre empresas;
- como anonimizar dados;
- como evitar recomendações ruins;
- como preservar responsabilidade humana;
- como medir se uma recomendação realmente melhorou o processo.

Este documento não define:

- o modelo técnico final de IA;
- o fornecedor de modelo;
- arquitetura de machine learning;
- infraestrutura de treinamento;
- embeddings;
- pipelines de dados;
- escolha de LLM;
- detalhes de anonimização jurídica;
- arquitetura de data warehouse;
- dashboards finais.

Esses assuntos podem ser definidos tecnicamente em fases posteriores.

---

# 2. Princípio central

A LPS não deve começar tentando “ser inteligente”.

Ela deve começar registrando a realidade com qualidade.

A evolução correta é:

```text
REGISTRAR
↓
MEDIR
↓
COMPARAR
↓
IDENTIFICAR PADRÕES
↓
PREVER
↓
RECOMENDAR
```

Qualquer tentativa de inverter essa sequência aumenta o risco de criar uma inteligência artificial que apenas parece inteligente.

---

# 3. Filosofia de aprendizado

A LPS deve aprender com o que realmente aconteceu.

Não apenas com o que estava planejado.

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

O histórico real é mais valioso que o fluxo desenhado.

---

# 4. A LPS deve aprender com fatos

Fatos estruturados incluem:

- atividade criada;
- tarefa criada;
- dono definido;
- executor atribuído;
- setor responsável;
- entrada em fila;
- posição;
- início;
- pausa;
- retomada;
- conclusão;
- devolução;
- motivo de devolução;
- alteração de prazo;
- aceite;
- recusa;
- escalonamento;
- mudança de fluxo;
- bloqueio;
- desbloqueio;
- mensagem contextual;
- conclusão final.

---

# 5. A LPS não deve aprender apenas com opinião

Exemplo ruim:

```text
Compras é lento.
```

Exemplo útil:

```text
Tempo médio em fila:
1,8 dia

Tempo de execução:
2h10

Devoluções:
21%

Motivo mais comum:
especificação incompleta
```

A conclusão gerencial vem dos dados.

---

# 6. Retroalimentação

Retroalimentação significa que cada nova atividade melhora a capacidade futura da LPS de compreender o processo.

Exemplo:

Primeira solicitação de compra:

```text
LPS sabe pouco.
```

Após 10:

```text
LPS possui alguns padrões.
```

Após 100:

```text
LPS consegue observar duração, fila, devoluções e caminhos recorrentes.
```

Após 1.000:

```text
LPS pode começar a sugerir prazos e fluxos com mais confiança.
```

---

# 7. O aprendizado deve ser incremental

A LPS não precisa esperar milhares de atividades para gerar qualquer valor.

Pode começar com análises simples.

Exemplo:

```text
Nas últimas 12 atividades deste tipo,
8 passaram por Compras antes do Financeiro.
```

Isso já é um padrão.

---

# 8. Confiança da análise

Toda conclusão futura deve considerar quantidade e qualidade dos dados.

Exemplo:

```text
Amostra:
3 atividades
```

não deve gerar recomendação tão forte quanto:

```text
Amostra:
380 atividades
```

---

# 9. Dados insuficientes

Quando não houver histórico suficiente, a LPS deve dizer:

```text
Dados insuficientes para estimar.
```

Não inventar.

---

# 10. Níveis de maturidade da inteligência

A LPS deve evoluir em etapas.

## Nível 0 — Registro

```text
O que aconteceu?
```

## Nível 1 — Descrição

```text
Quanto tempo levou?
Onde ficou?
Quantas vezes voltou?
```

## Nível 2 — Diagnóstico

```text
Onde está o principal gargalo?
Quais motivos se repetem?
```

## Nível 3 — Previsão

```text
Quanto provavelmente vai levar?
Existe risco de atraso?
```

## Nível 4 — Recomendação

```text
Qual fluxo parece melhor?
Qual prazo parece realista?
Qual melhoria deveria ser testada?
```

---

# 11. D0 da inteligência

No D0, o objetivo é:

> **coletar dados corretamente.**

Não é:

> prever tudo.

---

# 12. O que o D0 precisa fazer

Registrar com consistência:

- atividades;
- tarefas;
- donos;
- executores;
- setores;
- fluxos;
- tempos;
- sessões;
- filas;
- posições;
- prazos;
- devoluções;
- motivos;
- escalonamentos;
- bloqueios;
- conversas;
- resultados.

---

# 13. Qualidade do dado é parte do produto

Se usuários:

- não iniciam tarefas;
- não pausam;
- não registram devolução;
- alteram prazo por chat sem formalizar;
- mantêm fila fora da LPS;

a inteligência futura ficará comprometida.

Por isso, UX simples é requisito da inteligência.

---

# 14. O usuário trabalha; o sistema registra

Regra:

> Quanto mais dados puderem ser capturados automaticamente como consequência da operação, melhor.

Exemplo:

Ao mover tarefa:

```text
Compras → Financeiro
```

a LPS registra automaticamente:

- origem;
- destino;
- data;
- hora;
- usuário;
- duração no setor anterior.

---

# 15. Evitar pedir informação que o sistema já sabe

Exemplo ruim:

```text
Quanto tempo ficou em Compras?
```

Exemplo correto:

```text
LPS calcula pela entrada e saída.
```

---

# 16. Histórico de duração

A LPS deve acumular duração por:

- atividade;
- tarefa;
- tipo de atividade;
- tipo de tarefa;
- setor;
- usuário;
- obra;
- cliente;
- fluxo;
- período;
- fornecedor quando aplicável.

---

# 17. Duração total

Exemplo:

```text
Solicitação de compra:
8d 03h
```

Esse dado isolado já é útil, mas não suficiente.

---

# 18. Decomposição da duração

A LPS deve conseguir decompor:

```text
tempo total
```

em:

```text
fila
execução
bloqueio
espera externa
retrabalho
transição
```

quando houver dados.

---

# 19. Histórico de tarefas semelhantes

Exemplo:

```text
Tipo:
Levantamento de quantitativos
```

Histórico:

```text
1h20
1h45
1h10
2h05
1h30
```

A LPS pode aprender a faixa típica.

---

# 20. Média não basta

A análise futura deve considerar:

- média;
- mediana;
- dispersão;
- valores extremos;
- tamanho da amostra.

---

# 21. Exemplo

Durações:

```text
1
2
2
3
15 dias
```

Média:

```text
4,6 dias
```

Mediana:

```text
2 dias
```

A LPS não deve depender de uma única estatística.

---

# 22. Histórico de fila

A LPS deve acumular:

- posição de entrada;
- total da fila;
- alterações;
- tempo em fila;
- quantidade de reordenações;
- posição na hora do início;
- entradas prioritárias.

---

# 23. Fila como fonte de aprendizado

Com histórico, a LPS poderá entender:

- quanto uma tarefa em posição 4 costuma esperar;
- como o tamanho da fila afeta prazo;
- quais setores reordenam mais;
- quais tipos de atividade furam fila;
- quais períodos possuem maior backlog.

---

# 24. Posição não é previsão por si só

Exemplo:

```text
4 de 17
```

pode significar:

```text
30 minutos
```

ou:

```text
2 dias
```

dependendo das três demandas anteriores.

A inteligência futura combina:

- posição;
- tipo das demandas;
- duração histórica;
- capacidade;
- executores;
- horário;
- dependências.

---

# 25. Histórico de devoluções

A LPS deve acumular:

- quantidade;
- origem;
- destino;
- motivo;
- observação;
- tempo de correção;
- tempo adicional;
- tipo de tarefa;
- setor.

---

# 26. Devolução como fonte de melhoria

Exemplo:

```text
31% das devoluções de Compras para Engenharia
ocorrem por especificação incompleta.
```

Isso pode gerar ação gerencial.

---

# 27. Motivos recorrentes

A LPS deve conseguir agrupar motivos como:

- informação incompleta;
- especificação incorreta;
- documento ausente;
- aprovação pendente;
- quantidade divergente;
- escopo incorreto.

---

# 28. Motivo recorrente pode revelar causa raiz

Exemplo:

```text
Motivo:
especificação incompleta
```

aparece em:

```text
42 de 120 devoluções
```

A recomendação futura pode ser:

> Revisar formulário de entrada ou criar checklist técnico antes de Compras.

---

# 29. A LPS não deve pular direto para a solução

Antes:

```text
detectar frequência
```

Depois:

```text
medir impacto
```

Depois:

```text
sugerir melhoria
```

---

# 30. Gargalos recorrentes

A LPS deve detectar candidatos a gargalo.

Exemplos:

- fila longa;
- espera por decisão;
- fornecedor;
- retrabalho;
- concentração em uma pessoa;
- alto tempo de execução;
- baixa capacidade;
- muitas renegociações;
- muitas devoluções.

---

# 31. Gargalo de fila

Exemplo:

```text
Execução:
35 min

Fila:
3,2 dias
```

A melhoria deve atacar fila/capacidade, não velocidade do executor.

---

# 32. Gargalo de execução

Exemplo:

```text
Fila:
15 min

Execução:
9h
```

Pode indicar:

- complexidade;
- falta de padrão;
- falta de ferramenta;
- treinamento.

---

# 33. Gargalo de decisão

Exemplo:

```text
Execução técnica:
2h

Aguardando aprovação:
4 dias
```

A etapa decisória limita o processo.

---

# 34. Gargalo externo

Exemplo:

```text
Processo interno:
1,5 dia

Fornecedor:
7 dias
```

A LPS precisa distinguir para não culpar o setor interno.

---

# 35. Gargalo de conhecimento

Exemplo:

```text
Jennifer:
1h10

Ryan:
2h50
```

em tarefas comparáveis.

Pode indicar:

- conhecimento concentrado;
- oportunidade de treinamento;
- falta de padrão.

---

# 36. Não transformar diferença em julgamento automático

A LPS deve sugerir investigação.

Não:

```text
Ryan é improdutivo.
```

Melhor:

```text
Existe diferença consistente de duração entre executores neste tipo de tarefa.
Avaliar complexidade, método e necessidade de treinamento.
```

---

# 37. Gargalo recorrente

Um único caso extremo não prova padrão.

A LPS precisa avaliar repetição.

Exemplo:

```text
1 atraso
```

é diferente de:

```text
72% das ocorrências atrasam na mesma etapa.
```

---

# 38. Análise por período

Padrões podem mudar.

Exemplo:

```text
últimos 30 dias
```

versus:

```text
últimos 12 meses
```

A LPS deve permitir contexto temporal.

---

# 39. Mudança de processo

Quando um fluxo é alterado, a LPS deve comparar antes e depois.

Exemplo:

Antes:

```text
devoluções:
28%
```

Depois:

```text
12%
```

---

# 40. Aprender se a melhoria funcionou

Esse é um ponto central da retroalimentação.

Fluxo:

```text
detectar problema
↓
sugerir mudança
↓
empresa aplica
↓
LPS mede resultado
↓
mantém ou revisa recomendação
```

---

# 41. Recomendações precisam ser testáveis

Exemplo:

> Adicionar validação técnica antes de Compras pode reduzir devoluções.

Depois medir:

```text
devolução antes
versus
devolução depois
```

---

# 42. LPS como ciclo de melhoria

```text
OBSERVAR
↓
MEDIR
↓
HIPÓTESE
↓
AÇÃO
↓
RESULTADO
↓
NOVO APRENDIZADO
```

---

# 43. Previsões futuras

Com dados suficientes, a LPS poderá prever:

- duração provável;
- risco de atraso;
- tempo em fila;
- provável data de conclusão;
- chance de devolução;
- necessidade de escalonamento;
- gargalo provável.

---

# 44. Previsão não é promessa

A interface deve apresentar:

```text
estimativa
```

ou:

```text
probabilidade
```

e nunca fingir certeza.

---

# 45. Exemplo de previsão

```text
Previsão:
3,4 dias

Faixa observada:
2,8 a 4,6 dias

Base:
86 atividades semelhantes
```

Isso é melhor que:

```text
Vai terminar em 3,4 dias.
```

---

# 46. Previsão precisa ser explicável

Exemplo:

```text
A estimativa considera:
- tipo de atividade;
- fluxo;
- fila atual;
- duração histórica;
- fornecedor;
- setor.
```

---

# 47. Previsão precisa mostrar confiança

Exemplo:

```text
Confiança:
baixa
```

quando:

- poucos dados;
- fluxo novo;
- atividade atípica.

---

# 48. Sugestão de prazo

No início:

```text
usuário informa manualmente.
```

Depois:

```text
LPS sugere.
```

---

# 49. Exemplo de sugestão de prazo

Histórico:

```text
Engenharia:
0,8 dia

Compras:
2,3 dias

Financeiro:
0,9 dia

Fornecedor:
6,8 dias
```

Nova atividade:

```text
Prazo final desejado:
10 dias
```

Sugestão:

```text
Para cumprir em 10 dias,
o pedido deveria estar liberado até aproximadamente D+3.
```

---

# 50. Prazo sugerido não deve substituir decisão humana

Usuário pode:

```text
aceitar
```

```text
ajustar
```

```text
ignorar
```

A LPS registra a decisão.

---

# 51. Aprender com aceites e rejeições

Se usuários frequentemente rejeitam determinada sugestão, isso também é dado.

A LPS pode reavaliar o modelo.

---

# 52. Sugestão de prazo por tarefa

Futuramente:

```text
Atividade:
10 dias
```

LPS pode sugerir:

```text
Engenharia:
1 dia

Compras:
2 dias

Financeiro:
1 dia

Fornecedor:
6 dias
```

---

# 53. Distribuição de prazo

Essa capacidade depende de histórico confiável.

Não pertence ao D0.

---

# 54. Sugestão de fluxo

No início:

```text
fluxo criado manualmente
```

Depois:

```text
fluxo recorrente identificado
```

---

# 55. Exemplo

Após 80 atividades do tipo:

```text
Solicitação de compra
```

a LPS observa:

```text
76% seguiram:
Engenharia → Compras → Financeiro → Almoxarifado
```

Sugestão:

```text
Deseja utilizar este fluxo como padrão?
```

---

# 56. Fluxo sugerido não deve ser imposto

A empresa pode possuir exceções legítimas.

---

# 57. Sugestão de etapa faltante

Exemplo:

A LPS percebe que:

```text
atividades com validação técnica antes de Compras
```

possuem:

```text
12% devoluções
```

enquanto:

```text
sem validação
```

possuem:

```text
31% devoluções
```

Sugestão futura:

> Avaliar inclusão de validação técnica antes de Compras.

---

# 58. Sugestão de remoção de etapa

Se uma etapa:

- quase nunca agrega ação;
- demora;
- não muda resultado;

a LPS pode sugerir análise.

Nunca remover automaticamente.

---

# 59. Sugestão de paralelismo

Exemplo:

Tarefas A e B sempre acontecem em sequência, mas não dependem entre si.

A LPS pode observar:

> Estas tarefas poderiam ser executadas em paralelo.

É uma hipótese.

---

# 60. Sugestão de treinamento

Exemplo:

```text
Jennifer:
mediana 1h15

Equipe:
mediana 2h40
```

com contexto comparável.

Sugestão:

> Avaliar compartilhamento do método de Jennifer com a equipe.

---

# 61. Sugestão de documentação

Se dúvidas e devoluções se repetem:

> Criar procedimento padrão para especificação antes de cotação.

---

# 62. Sugestão de checklist

Se motivo recorrente é:

```text
informação incompleta
```

a LPS pode sugerir:

> Criar checklist de entrada.

---

# 63. Sugestão de capacidade

Se:

```text
entrada > saída
```

por várias semanas:

> A fila está crescendo de forma consistente.

Possíveis recomendações:

- redistribuir pessoas;
- revisar prioridade;
- automatizar;
- treinar;
- aumentar capacidade.

---

# 64. Sugestão não deve escolher contratação automaticamente

A LPS deve mostrar o problema e opções.

A decisão de contratar pessoa continua humana.

---

# 65. Sugestão de responsável

Futuramente, pode existir:

> Pessoas A e B possuem experiência neste tipo de tarefa.

Mas a recomendação deve considerar:

- disponibilidade;
- fila;
- desempenho histórico;
- autorização;
- setor.

---

# 66. Risco de concentração

Se apenas uma pessoa executa determinado processo:

```text
90% das tarefas deste tipo são executadas por Jennifer.
```

A LPS pode alertar:

> Existe concentração de conhecimento.

---

# 67. Risco de dependência de pessoa

Pode sugerir:

- treinamento;
- documentação;
- backup.

---

# 68. Risco de sobrecarga

Exemplo:

```text
Paulo possui 18 tarefas abertas
enquanto média do setor é 5.
```

A LPS pode sugerir redistribuição.

Mas precisa considerar complexidade.

---

# 69. Comparação entre processos

Processo passa a ser uma dimensão explícita de comparação.

A LPS deve conseguir analisar:

- execuções do mesmo processo;
- versão A x versão B do mesmo processo;
- fluxo padrão x fluxo real;
- antes x depois de uma mudança;
- unidades ou equipes executando o mesmo processo.

Exemplo:

```text
Processo: Elaborar orçamento
Versão 2: mediana 18h
Versão 3: mediana 14h
```

Isso não prova sozinho que a versão 3 é melhor. A análise precisa considerar contexto e qualidade do resultado.

---

# 70. Não misturar versões silenciosamente

Se o processo mudou, a LPS precisa saber qual versão originou cada atividade.

Relatórios podem consolidar várias versões, mas devem permitir separar:

```text
processo_id
processo_versao_id
```

Sem isso, uma melhoria ou piora pode ser escondida pela média.

---

# 71. Segmentação

Para melhorar comparabilidade, a LPS pode usar:

- processo;
- versão do processo;
- tipo de atividade;
- empresa;
- setor;
- obra;
- cliente;
- porte;
- complexidade;
- fluxo real.

Nem todos estarão disponíveis no D0.

Para processos, também podem ser observados:

- input incompleto;
- quantidade de desvios;
- critérios de aceite reabertos;
- output aprovado na primeira tentativa.

---

# 72. Complexidade

Futuramente, pode existir classificação de complexidade.

Mas não precisa ser inventada agora.

O histórico pode ajudar a descobrir variáveis relevantes.

---

# 73. Clusterização futura

A LPS pode futuramente agrupar atividades semelhantes automaticamente.

Não é prioridade inicial.

---

# 74. Comparação com próprio histórico

A primeira comparação mais segura é:

```text
empresa consigo mesma.
```

---

# 75. Benchmark interno

Exemplos:

- setor atual x mês anterior;
- obra A x obra B;
- equipe A x equipe B;
- fluxo antigo x novo.

---

# 76. Benchmark externo

Comparar empresas diferentes é mais complexo.

Precisa considerar:

- anonimização;
- autorização;
- porte;
- processo;
- segmento;
- região;
- complexidade.

---

# 77. Uso anonimizado entre empresas

A possibilidade de aprendizado cruzado é um diferencial futuro importante.

Mas precisa ser tratada com muito cuidado.

---

# 78. Princípio de isolamento

Dados identificáveis de uma empresa não devem ser usados para expor informação a outra.

Exemplo proibido:

> A Empresa X leva 2 dias em Compras.

para um cliente que não deveria conhecer isso.

---

# 79. Aprendizado agregado

Exemplo possível:

```text
Em empresas de perfil semelhante,
processos com validação técnica antes de Compras
apresentaram menor taxa de devolução.
```

Sem identificar empresas.

---

# 80. Consentimento

O uso entre empresas deve depender de política clara e autorização apropriada.

Não assumir que todo dado pode ser compartilhado.

---

# 81. Anonimização

Pode exigir remover ou generalizar:

- nome da empresa;
- clientes;
- obras;
- pessoas;
- valores;
- locais;
- mensagens;
- documentos.

A implementação jurídica e técnica será detalhada futuramente.

---

# 82. Benchmark sem dados pessoais

Preferir métricas agregadas.

Exemplo:

```text
mediana de tempo por processo
```

em vez de:

```text
nome de funcionário.
```

---

# 83. Benefício futuro do aprendizado cruzado

Uma empresa nova pode receber boas práticas sem esperar anos de histórico próprio.

Exemplo:

> Empresas semelhantes costumam utilizar este fluxo.

---

# 84. Risco do aprendizado cruzado

O que funciona em uma empresa pode falhar em outra.

Por isso, sugestão precisa considerar contexto.

---

# 85. Nunca apresentar benchmark como regra absoluta

Melhor:

```text
Sugestão baseada em padrões agregados.
```

Não:

```text
Este é o fluxo correto.
```

---

# 86. IA futura

A IA deve ser uma camada sobre dados estruturados e contexto.

Ela pode ajudar a:

- resumir;
- classificar;
- detectar padrões;
- explicar desvios;
- sugerir prazo;
- sugerir fluxo;
- sugerir melhoria;
- identificar risco;
- encontrar atividades semelhantes.

---

# 87. IA não substitui o motor de regras

Ações oficiais continuam baseadas em:

- permissões;
- estados;
- fluxos;
- regras.

IA pode sugerir.

Não deve decidir silenciosamente.

---

# 88. IA não deve alterar prazo automaticamente

Mesmo que confiante.

---

# 89. IA não deve reordenar fila automaticamente no início

Pode sugerir:

> Tarefa X possui alto risco de atraso.

Gestor decide.

---

# 90. IA não deve alterar dono automaticamente

Pode sugerir um executor.

A atribuição continua controlada.

---

# 91. IA não deve concluir atividade

Pode detectar que todas as condições parecem satisfeitas.

Mas conclusão oficial segue regra de negócio.

---

# 92. IA e explicabilidade

Toda recomendação importante deve explicar:

- por que;
- com base em quê;
- nível de confiança;
- dados principais.

---

# 93. Exemplo

```text
Sugestão:
Antecipar emissão do pedido em 1 dia.

Motivo:
Nas últimas 54 atividades semelhantes,
o fornecedor utilizou mediana de 7,2 dias,
enquanto restam 8 dias para o prazo final.
```

---

# 94. Recomendações sem explicação geram baixa confiança

Evitar:

```text
IA recomenda: faça isso.
```

---

# 95. Fato, cálculo, previsão e recomendação

A LPS precisa separar quatro níveis.

## Fato

```text
Compras levou 2d 4h.
```

## Cálculo

```text
Mediana das últimas 50 atividades:
2d 1h.
```

## Previsão

```text
Esta tarefa provavelmente levará entre 1,8 e 2,5 dias.
```

## Recomendação

```text
Considere iniciar hoje para reduzir risco de atraso.
```

---

# 96. A interface deve diferenciar visualmente

Não é necessário no D0, mas é princípio.

---

# 97. Feedback humano

Usuário deve poder indicar:

```text
Sugestão útil
```

```text
Sugestão não útil
```

ou aceitar/rejeitar.

---

# 98. Aprender com feedback

Se recomendações são constantemente rejeitadas, a LPS precisa reavaliar.

---

# 99. Aceite não prova que estava correta

O resultado precisa ser medido.

Exemplo:

LPS sugeriu novo fluxo.

Usuário aceitou.

Depois:

```text
tempo caiu?
devoluções caíram?
```

---

# 100. Medir qualidade da recomendação

Possíveis métricas futuras:

- taxa de aceite;
- impacto após aceite;
- erro de previsão;
- confiança calibrada;
- redução de atraso.

---

# 101. Previsão de atraso

A LPS poderá combinar:

- prazo restante;
- etapas abertas;
- tempos históricos;
- fila;
- fornecedor;
- devoluções;
- bloqueios.

---

# 102. Exemplo

```text
Prazo final:
5 dias

Etapas restantes normalmente:
6,2 dias
```

Alerta:

```text
Risco alto de atraso.
```

---

# 103. Explicar risco

```text
Principal fator:
prazo histórico do fornecedor.
```

---

# 104. Previsão de devolução

Futuramente:

> Este tipo de tarefa apresenta 28% de devolução quando enviado sem validação técnica.

Pode sugerir revisão.

---

# 105. Previsão de fila

Com histórico:

```text
Posição atual:
7 de 18
```

A LPS pode estimar:

```text
Início provável:
amanhã entre 09h e 12h.
```

---

# 106. Previsão de capacidade

Exemplo:

```text
Fila atual:
47 tarefas

Capacidade histórica:
20/dia
```

Pode estimar backlog.

---

# 107. Capacidade não deve ser tratada como constante absoluta

Pode variar por:

- equipe;
- férias;
- complexidade;
- período;
- tipo de tarefa.

---

# 108. Sazonalidade

Futuramente, a LPS pode identificar:

- fechamento mensal;
- períodos de obra;
- férias;
- picos de demanda.

---

# 109. Tendência

Exemplo:

```text
Backlog aumentou por 5 semanas consecutivas.
```

Pode indicar problema estrutural.

---

# 110. Anomalias

A LPS pode detectar atividades muito fora do padrão.

Exemplo:

```text
Mediana:
2 dias

Esta atividade:
11 dias
```

Alerta:

> Atividade fora do comportamento histórico.

---

# 111. Outlier não significa erro

Pode ser caso legítimo.

A LPS deve chamar atenção, não julgar.

---

# 112. Outlier de produtividade

Exemplo:

Uma pessoa executa muito mais rápido.

Pode revelar:

- boa prática;
- erro de registro;
- tarefa simples;
- conhecimento.

Requer análise.

---

# 113. Outlier de atraso

Atividade muito mais lenta pode revelar:

- falha;
- dependência externa;
- processo novo.

---

# 114. Motivo recorrente em conversas

Futuramente, IA pode analisar textos para encontrar temas.

Exemplo:

```text
"faltou projeto"
"aguardando projeto"
"projeto incompleto"
```

podem formar tema:

```text
problemas de documentação técnica
```

---

# 115. Texto não substitui motivo estruturado

Mas ajuda a encontrar contexto adicional.

---

# 116. Resumo automático

A LPS poderá resumir:

- histórico;
- mensagens;
- prazos;
- devoluções;
- decisões;
- gargalos.

---

# 117. Exemplo

> A atividade levou 8 dias e 3 horas. O maior período foi de 7 dias aguardando fornecedor. Houve uma devolução por especificação incompleta e uma renegociação de prazo. O prazo final foi cumprido após o ajuste.

---

# 118. Resumo precisa citar fatos internos

Futuramente, o usuário pode clicar em cada afirmação e abrir o evento correspondente.

---

# 119. Resumo de atividade aberta

Pode mostrar:

- estado atual;
- última decisão;
- prazo;
- risco;
- próximos passos.

---

# 120. Resumo para gestor

Pode priorizar:

- gargalo;
- risco;
- atraso;
- devolução;
- escalonamento.

---

# 121. Resumo para executor

Pode priorizar:

- o que fazer;
- contexto;
- prazo;
- pendências.

---

# 122. Resumo personalizado por autorização

Nunca mostrar dado fora do escopo do usuário.

---

# 123. IA e segurança

A IA precisa respeitar:

- organização;
- empresa;
- setor;
- atividade;
- autorização;
- escopo.

---

# 124. IA não pode vazar informação

Exemplo:

Usuário sem acesso ao Financeiro pergunta:

> Por que esta atividade atrasou?

A resposta não pode revelar dados restritos além do permitido.

---

# 125. IA e multiempresa

O contexto enviado ao modelo precisa ser filtrado.

---

# 126. Aprendizado do próprio cliente

Por padrão, o primeiro aprendizado deve ocorrer com dados da própria organização.

---

# 127. Benchmark externo opcional

Pode ser produto pago futuro.

---

# 128. Possível diferencial comercial

Uma empresa nova poderia receber:

- modelos de fluxo;
- faixas de prazo;
- causas frequentes;
- boas práticas;

derivadas de dados agregados e autorizados.

---

# 129. Mas não depender disso para gerar valor

A LPS precisa ser valiosa mesmo sem benchmark externo.

---

# 130. Aprendizado individual da organização já é valioso

Exemplo:

> Antes você achava que Compras demorava. Agora sabe que 78% do tempo está no fornecedor.

---

# 131. Métricas como base de insight

O insight precisa surgir de relações.

Exemplo:

```text
Tempo alto
+
fila baixa
+
execução alta
=
problema provável na execução
```

---

# 132. Outro exemplo

```text
Execução baixa
+
fila alta
=
capacidade/priorização
```

---

# 133. Outro exemplo

```text
Devolução alta
+
motivo recorrente
=
problema de entrada/padrão
```

---

# 134. Outro exemplo

```text
Prazo renegociado com frequência
=
baixa previsibilidade ou capacidade insuficiente
```

---

# 135. Insight precisa ser acionável

Evitar:

> Seu processo está lento.

Melhor:

> 68% do tempo desta atividade foi gasto aguardando aprovação. Avalie reduzir ou antecipar essa etapa.

---

# 136. Recomendação precisa considerar impacto

Não vale otimizar uma etapa que representa 1% do tempo total.

---

# 137. Pareto

A LPS pode futuramente utilizar lógica de Pareto:

> quais poucos problemas respondem pela maior parte do atraso?

---

# 138. Exemplo

```text
3 motivos
respondem por
72% das devoluções
```

Esses merecem prioridade.

---

# 139. Melhoria contínua orientada a dados

Fluxo:

```text
Problema detectado
↓
Impacto medido
↓
Causa provável
↓
Ação proposta
↓
Resultado medido
```

---

# 140. Sugestão de prioridade de melhoria

Futuramente, a LPS pode priorizar melhorias por:

- frequência;
- impacto;
- tempo perdido;
- custo;
- risco.

---

# 141. Custo

Quando houver custo/hora confiável, a LPS poderá traduzir:

```text
retrabalho
```

em:

```text
custo
```

Não pertence ao D0.

---

# 142. ROI

ROI significa **Return on Investment**, ou retorno sobre investimento.

Futuramente, a LPS poderá mostrar:

```text
redução de horas
redução de atraso
redução de retrabalho
```

e estimar retorno financeiro.

---

# 143. Exemplo

Antes:

```text
100h/mês de retrabalho
```

Depois:

```text
60h/mês
```

Ganho:

```text
40h/mês
```

Isso pode ser monetizado se houver custo/hora.

---

# 144. Valor do produto

A inteligência futura pode ajudar a LPS provar:

- tempo economizado;
- capacidade liberada;
- prazo reduzido;
- retrabalho reduzido;
- menos escalonamento;
- menos espera.

---

# 145. Não vender “IA” sem resultado

O cliente paga por:

- previsibilidade;
- velocidade;
- redução de desperdício;
- transparência;
- gestão.

IA é meio.

---

# 146. Dados necessários para sugestão de prazo

No mínimo:

- tipo de atividade;
- tipo de tarefa;
- setor;
- fluxo;
- histórico de duração;
- fila;
- prazo externo;
- devoluções.

---

# 147. Dados necessários para sugestão de fluxo

- fluxos históricos;
- tarefas frequentes;
- ordem;
- retornos;
- taxa de sucesso;
- duração;
- desvios.

---

# 148. Dados necessários para sugestão de melhoria

- gargalo;
- frequência;
- impacto;
- motivo;
- comparação antes/depois;
- alternativas observadas.

---

# 149. Dados necessários para sugestão de treinamento

- tarefas comparáveis;
- duração;
- qualidade;
- devoluções;
- executor;
- volume suficiente.

---

# 150. Não usar apenas velocidade para sugerir treinamento

Pode ser injusto.

Combinar:

- tempo;
- qualidade;
- retrabalho;
- complexidade.

---

# 151. Qualidade

A LPS ainda precisa evoluir a definição de qualidade de tarefa.

Pode incluir:

- devolução;
- retrabalho;
- aprovação;
- erro posterior.

Não precisa estar totalmente resolvido no D0.

---

# 152. Resultado final

Uma atividade rápida que gera problema depois pode não ser melhor.

---

# 153. Efeito de longo prazo

Futuramente, a LPS pode relacionar:

```text
execução rápida
```

com:

```text
retrabalho posterior
```

---

# 154. Process mining

No futuro, a LPS pode utilizar conceitos de **process mining**, ou mineração de processos.

Isso significa reconstruir o processo real a partir dos eventos.

---

# 155. Exemplo de mineração de processo

Planejado:

```text
A → B → C
```

Histórico real:

```text
A → B → A → B → D → C
```

A LPS pode mapear os caminhos mais frequentes.

---

# 156. Benefício

Descobrir:

- fluxo real;
- exceções;
- retornos;
- caminhos rápidos;
- caminhos lentos.

---

# 157. Não precisamos implementar process mining completo no D0

Mas os eventos precisam ser registrados para permitir isso depois.

---

# 158. Sequência de eventos

Por isso é importante registrar:

- timestamp;
- atividade;
- tarefa;
- setor;
- usuário;
- tipo de evento.

---

# 159. Dados históricos como patrimônio

O histórico operacional acumulado tende a se tornar um dos principais ativos da LPS.

---

# 160. Quanto mais usada, mais valiosa

Se os dados forem confiáveis:

```text
uso
↓
histórico
↓
aprendizado
↓
melhor recomendação
↓
mais valor
```

Esse é o efeito de retroalimentação desejado.

---

# 161. Mas volume não corrige dados ruins

```text
1 milhão de registros ruins
```

continua sendo uma base ruim.

---

# 162. Governança de dados

Futuramente, pode existir:

- qualidade;
- completude;
- consistência;
- validação.

No D0, priorizar regras simples e uso correto.

---

# 163. Indicador de qualidade do dado

Exemplo futuro:

```text
92% das tarefas possuem sessões de tempo completas.
```

---

# 164. Dados faltantes

Se 40% das tarefas não possuem timer:

> estimativas de esforço devem indicar baixa confiança.

---

# 165. Confiança da recomendação depende da qualidade

Não apenas do volume.

---

# 166. Drift

Processos mudam com o tempo.

O padrão de 2026 pode não valer em 2028.

A LPS precisa dar mais peso ao histórico recente quando apropriado.

---

# 167. Mudança de equipe

Pode alterar desempenho.

---

# 168. Mudança de fornecedor

Pode alterar prazo.

---

# 169. Mudança de fluxo

Pode invalidar comparação antiga.

---

# 170. Modelo precisa saber o contexto temporal

Não tratar toda história como igualmente relevante.

---

# 171. Feedback explícito

Gestor pode marcar:

```text
Recomendação aplicada
```

e depois avaliar.

---

# 172. Feedback implícito

Aceitar prazo sugerido é um sinal.

Mas resultado real é mais importante.

---

# 173. Aprendizado por resultado

Exemplo:

LPS sugeriu:

```text
prazo de 5 dias
```

Real:

```text
8 dias
```

O erro deve ser registrado.

---

# 174. Erro de previsão

Futuramente:

```text
erro = realizado - previsto
```

---

# 175. Calibração

Se a LPS diz:

```text
80% de chance de atraso
```

esses alertas deveriam se confirmar aproximadamente nessa proporção ao longo do tempo.

Tema avançado, não D0.

---

# 176. Recomendações conservadoras

Em processos críticos, pode ser melhor estimar com margem.

A política precisa ser configurável no futuro.

---

# 177. Sensibilidade ao risco

Empresa A pode preferir:

```text
prazo agressivo
```

Empresa B:

```text
prazo seguro
```

A LPS pode futuramente adaptar.

---

# 178. IA não substitui gestão

Mesmo uma boa previsão precisa de decisão humana.

---

# 179. Gestão usa inteligência para decidir melhor

A função da LPS é:

```text
dar contexto
reduzir incerteza
mostrar padrão
sugerir
```

---

# 180. Não criar autoridade artificial

Evitar frases:

> A IA decidiu.

Preferir:

> A LPS sugere com base em 86 atividades semelhantes.

---

# 181. Explicação da base

Mostrar:

- amostra;
- período;
- principais fatores;
- confiança.

---

# 182. Exemplo de recomendação responsável

```text
Sugestão:
Prazo de 6 dias.

Base:
42 atividades semelhantes dos últimos 90 dias.

Mediana:
5,3 dias.

80% foram concluídas em até:
6,1 dias.
```

---

# 183. Recomendações sem histórico

Se não há dados internos:

```text
Não há histórico suficiente.
```

Se benchmark externo autorizado existir:

```text
Sugestão baseada em benchmark agregado.
```

Deixar claro.

---

# 184. Fonte da recomendação

Pode ser:

```text
histórico interno
```

```text
regra configurada
```

```text
benchmark agregado
```

```text
IA
```

---

# 185. Nunca misturar fontes silenciosamente

Usuário precisa saber.

---

# 186. Aprendizado entre setores

A mesma organização pode aproveitar conhecimento interno.

Exemplo:

Um setor possui fluxo eficiente.

Outro setor realiza processo semelhante.

A LPS pode sugerir comparação.

---

# 187. Compartilhamento interno de boas práticas

Menos sensível que entre empresas, mas ainda precisa de autorização.

---

# 188. Biblioteca futura de boas práticas

A LPS pode guardar:

- fluxos aprovados;
- checklists;
- padrões;
- recomendações validadas.

Não é prioridade do D0.

---

# 189. Recomendação validada

Uma sugestão aplicada com bons resultados pode virar padrão.

Fluxo:

```text
sugestão
↓
teste
↓
resultado positivo
↓
aprovação humana
↓
novo padrão
```

---

# 190. O sistema se retroalimenta sem se autoalterar silenciosamente

Esse é um princípio crítico.

A LPS aprende.

Mas mudanças estruturais exigem confirmação.

---

# 191. Autoaprendizado não significa autonomia irrestrita

Evitar:

```text
LPS mudou o fluxo sozinha.
```

Preferir:

```text
LPS sugeriu alteração.
Gestor aprovou.
```

---

# 192. Auditoria da inteligência

Toda recomendação relevante deve poder ser auditada.

Registrar:

- quando foi gerada;
- para quem;
- qual contexto;
- recomendação;
- confiança;
- aceita/rejeitada;
- resultado posterior quando disponível.

---

# 193. Histórico de recomendações

Isso permite avaliar a própria LPS.

---

# 194. A LPS também precisa aprender com seus erros

Se previsões falham em determinado processo:

> modelo precisa ser revisado.

---

# 195. Meta-inteligência

Futuramente, o sistema pode saber:

```text
Neste tipo de atividade minhas previsões são confiáveis.
```

ou:

```text
Neste outro tipo ainda há pouca confiança.
```

---

# 196. Não esconder incerteza

Esse é um diferencial de confiança.

---

# 197. Dados de conversa e IA

Mensagens podem ajudar a explicar:

- risco;
- impedimento;
- decisão;
- causa.

Mas devem passar por filtros de autorização.

---

# 198. Resumo de conversa

Futuramente:

```text
Principais decisões:
- manter fornecedor atual;
- prazo ajustado para 18/09;
- Engenharia corrigirá especificação.
```

---

# 199. Resumo não altera estado

Continua sendo leitura.

---

# 200. Detecção de compromisso

Mensagem:

> “Eu entrego amanhã às 14h.”

A LPS pode sugerir:

```text
Registrar compromisso de prazo?
```

---

# 201. Detecção de bloqueio

Mensagem:

> “Estou aguardando projeto.”

Sugestão:

```text
Registrar bloqueio?
```

---

# 202. Detecção de risco

Mensagem:

> “Se não pagar hoje, o fornecedor cancela a entrega.”

Sugestão:

```text
Registrar risco?
```

---

# 203. Human-in-the-loop

**Human-in-the-loop** significa manter uma pessoa no processo de confirmação.

Esse deve ser o padrão inicial da IA da LPS.

---

# 204. Confirmação humana

A IA identifica.

A pessoa confirma.

O sistema registra.

---

# 205. Automação futura seletiva

Somente depois de muita confiança e para ações de baixo risco pode existir automação maior.

---

# 206. Ações de alto impacto sempre merecem cautela

Exemplos:

- alterar prioridade;
- alterar prazo;
- trocar dono;
- cancelar;
- aprovar;
- reordenar fila crítica.

---

# 207. Sugestão de próxima melhor ação

Futuramente, a LPS pode mostrar:

```text
Próxima ação recomendada:
cobrar aprovação da diretoria.
```

Base:

```text
atividade parada há 2 dias nesta etapa.
```

---

# 208. Próxima ação não deve virar obrigação

---

# 209. Alertas de esquecimento

Exemplo:

```text
Nenhuma ação há 3 dias.
```

Pode ser simples regra antes de IA.

---

# 210. Regras + IA

A inteligência da LPS não precisa ser toda baseada em IA generativa.

Pode combinar:

- regras;
- estatística;
- histórico;
- machine learning;
- IA generativa.

---

# 211. Escolher ferramenta adequada

Exemplo:

```text
Prazo vencido
```

é regra simples.

Não precisa de IA.

---

# 212. Outro exemplo

```text
Resumir 200 mensagens
```

é um bom uso de IA generativa.

---

# 213. Outro exemplo

```text
Estimar duração
```

pode usar estatística/modelo preditivo.

---

# 214. Evitar usar LLM para tudo

Isso aumenta:

- custo;
- imprevisibilidade;
- complexidade.

---

# 215. Inteligência híbrida

A arquitetura futura pode combinar:

```text
regras determinísticas
+
métricas
+
modelos estatísticos
+
IA generativa
```

---

# 216. Regra de decisão tecnológica

Perguntar:

> Qual é a forma mais simples, confiável e explicável de resolver este problema?

---

# 217. IA como interface sobre dados

Um uso futuro poderoso:

Usuário pergunta:

> Onde estamos perdendo mais tempo no Comercial este mês?

A LPS responde usando dados autorizados.

---

# 218. Outro exemplo

> Quais são os três motivos mais comuns de devolução?

---

# 219. Outro exemplo

> Quais atividades estão com maior risco de atraso?

---

# 220. Outro exemplo

> O que mudou desde a semana passada?

---

# 221. Perguntas naturais

Essa camada pode tornar a análise acessível a gestores sem conhecimento técnico.

---

# 222. Respostas precisam apontar dados

Exemplo:

> O maior gargalo foi espera em Compras, com mediana de 1,9 dia em 64 tarefas.

---

# 223. Evitar resposta vaga

> O Comercial parece sobrecarregado.

Sem base, não serve.

---

# 224. IA e auditoria

A pergunta e resposta podem ser registradas em contextos sensíveis conforme política.

Não é prioridade do D0.

---

# 225. Privacidade de prompts

Futuramente, perguntas podem conter dados sensíveis.

Precisa de governança.

---

# 226. IA como copiloto, não autoridade

A visão deve ser:

```text
LPS observa
LPS explica
LPS sugere
gestor decide
```

---

# 227. Inteligência para colaborador

Pode ajudar com:

- próximos passos;
- resumo;
- prazo;
- dependência;
- atividades similares.

---

# 228. Inteligência para gestor

Pode ajudar com:

- gargalos;
- capacidade;
- risco;
- tendência;
- melhoria;
- treinamento.

---

# 229. Inteligência para diretoria

Pode ajudar com:

- visão agregada;
- gargalos sistêmicos;
- setores sobrecarregados;
- melhoria de processo;
- capacidade.

---

# 230. Inteligência não deve gerar vigilância excessiva

Evitar recomendações baseadas em:

- tempo online;
- quantidade de cliques;
- mensagens;
- presença.

Foco em trabalho e fluxo.

---

# 231. Inteligência orientada ao processo

Priorizar:

- espera;
- retrabalho;
- capacidade;
- qualidade;
- fluxo;
- prazo.

---

# 232. Pessoas dentro do contexto

A LPS pode analisar diferenças entre pessoas para:

- treinamento;
- padronização;
- distribuição.

Não para criar ranking simplista.

---

# 233. Fairness

Futuramente, recomendações sobre pessoas devem considerar justiça e contexto.

---

# 234. Complexidade desigual

Uma pessoa pode receber tarefas mais difíceis.

Não comparar cegamente.

---

# 235. Recomendação de treinamento responsável

Exemplo:

> Em tarefas classificadas como equivalentes, Jennifer apresenta menor tempo e menor taxa de devolução. Avaliar sessão de compartilhamento de método.

---

# 236. Não dizer

> Ryan é pior.

---

# 237. Sugestão de balanceamento

Exemplo:

```text
Fila de Ryan:
12 tarefas

Fila de Jennifer:
3 tarefas
```

A LPS pode sugerir redistribuição se regras permitirem.

---

# 238. Balanceamento não pode ignorar habilidade

---

# 239. Perfis de habilidade

Futuramente, pode existir histórico de experiência por tipo de tarefa.

Não é necessário no D0.

---

# 240. Aprendizado de habilidade implícito

A LPS pode inferir experiência pela quantidade de tarefas executadas.

Mas isso não significa competência automaticamente.

---

# 241. Avaliação humana continua importante

---

# 242. Aprendizado de fornecedores

Se fornecedor estiver relacionado à tarefa, a LPS pode medir:

- prazo;
- atraso;
- devolução;
- confiabilidade.

---

# 243. Sugestão futura

> Fornecedor A possui prazo mediano menor, mas maior variabilidade.

---

# 244. Não transformar em recomendação de compra sem contexto comercial

Preço, qualidade e contrato também importam.

---

# 245. Aprendizado de clientes

Pode observar:

- quantidade de devoluções por informação;
- tempo aguardando cliente;
- mudanças de escopo.

---

# 246. Uso cuidadoso

Não rotular cliente negativamente sem contexto.

---

# 247. Aprendizado por obra

Pode identificar obras com:

- maior retrabalho;
- maior espera;
- maior concentração de gargalo.

---

# 248. Aprendizado por setor

Pode identificar:

- evolução;
- capacidade;
- fila;
- melhoria após treinamento.

---

# 249. Aprendizado por tipo de atividade

Provavelmente uma das dimensões mais importantes.

---

# 250. Taxonomia de tipos

Para inteligência funcionar bem, tipos de atividade precisam ser usados com consistência.

---

# 251. Excesso de tipos prejudica comparação

Se cada usuário cria:

```text
Compra
Comprar material
Solicitação de compra
Aquisição
```

como tipos diferentes, histórico fragmenta.

---

# 252. Cadastros precisam ser governados

Isso se conecta ao documento de autorizações.

---

# 253. Inteligência depende de padronização mínima

Dinamismo não significa ausência de padrão.

---

# 254. Equilíbrio

```text
configurável
+
governado
=
dados comparáveis
```

---

# 255. Dados qualitativos

Além de números, podem existir:

- motivo;
- observação;
- conversa;
- decisão.

---

# 256. Dados quantitativos

- duração;
- fila;
- posição;
- prazo;
- quantidade;
- horas-homem.

---

# 257. Inteligência combina ambos

Esse pode ser um diferencial importante da LPS.

---

# 258. Exemplo

Quantitativo:

```text
3 devoluções
```

Qualitativo:

```text
todas por especificação incompleta
```

Insight:

> Há recorrência de falha de especificação antes de Compras.

---

# 259. Atividade encerrada como unidade de aprendizado

Ao concluir uma atividade, a LPS pode consolidar:

- duração;
- fluxo real;
- desvios;
- pessoas;
- devoluções;
- prazo;
- resultado.

---

# 260. Pós-análise automática futura

Após conclusão:

```text
O que aprendemos?
```

A LPS pode gerar resumo.

---

# 261. Exemplo

```text
Prazo cumprido: não
Maior espera: fornecedor
Devoluções: 1
Motivo: especificação incompleta
Fluxo fora do padrão: não
```

---

# 262. Sem formulário manual obrigatório

Idealmente, isso é calculado automaticamente.

---

# 263. Reflexão humana opcional

Pode existir campo:

```text
Lição aprendida
```

Não obrigatório no D0.

---

# 264. Lição aprendida pode alimentar inteligência

Mas texto livre precisa ser tratado como contexto.

---

# 265. Aprendizado organizacional

A LPS pode futuramente reunir:

- padrões;
- lições;
- procedimentos;
- fluxos aprovados.

---

# 266. Conhecimento não deve ficar apenas em relatório

Idealmente, o aprendizado volta para o fluxo.

Exemplo:

```text
devolução recorrente
↓
novo checklist
↓
queda de devolução
```

---

# 267. Retroalimentação real

Isso diferencia:

```text
dashboard
```

de:

```text
sistema que aprende.
```

---

# 268. Dashboard mostra

> O problema existe.

---

# 269. Retroalimentação sugere

> Aqui está uma mudança possível.

---

# 270. Depois mede

> A mudança funcionou ou não?

---

# 271. Recomendações devem ser priorizadas

Não bombardear gestor com 50 melhorias.

Preferir:

```text
Top 3 oportunidades por impacto.
```

---

# 272. Critérios possíveis

- tempo perdido;
- frequência;
- custo;
- risco;
- volume.

---

# 273. Recomendação precisa ter dono

Futuramente, uma melhoria aprovada pode virar atividade.

Mas criação deve ser explícita.

---

# 274. IA não cria atividade automaticamente no D0

Mantém decisão já consolidada.

---

# 275. Sugestão pode oferecer botão

```text
Criar atividade de melhoria
```

Usuário confirma e preenche.

Evolução futura.

---

# 276. Histórico de melhorias

A LPS pode relacionar:

```text
problema detectado
↓
ação de melhoria
↓
resultado
```

Muito valioso para gestão.

---

# 277. Exemplo

Problema:

```text
31% devoluções por especificação
```

Melhoria:

```text
checklist técnico
```

Resultado:

```text
12% após 60 dias
```

---

# 278. ROI de melhoria

Futuramente:

```text
horas economizadas
```

```text
prazo reduzido
```

```text
custo evitado
```

---

# 279. Produto pago

A camada paga pode evoluir para oferecer:

- previsões;
- recomendações;
- benchmark;
- análises automáticas;
- resumos;
- modelos de fluxo;
- alertas preditivos.

---

# 280. Mas o dado pertence à operação

A base deve existir também na versão operacional.

---

# 281. Freemium futuro

Uma hipótese possível:

```text
gratuito:
registro e gestão básica
```

```text
pago:
inteligência, recomendações, benchmark e automações
```

Essa é decisão de modelo de negócio, não fechada neste documento.

---

# 282. Inteligência como efeito de rede

Com autorização e anonimização, mais empresas podem melhorar o benchmark.

Mas esse efeito depende de confiança.

---

# 283. Confiança é ativo central

Se cliente acredita que seus dados podem vazar:

```text
não alimenta o sistema
```

e o efeito de rede desaparece.

---

# 284. Transparência sobre uso dos dados

A política precisa deixar claro:

- o que é usado;
- para quê;
- se é agregado;
- se é anonimizado;
- se existe opt-out/consentimento conforme modelo adotado.

---

# 285. Não prometer anonimização sem implementação adequada

Tema jurídico e técnico posterior.

---

# 286. IA interna da empresa

Mesmo sem benchmark externo, a LPS pode entregar muito valor.

---

# 287. Primeira inteligência recomendada

Antes de modelos complexos, priorizar análises determinísticas:

- maiores gargalos;
- tempos;
- devoluções;
- aging;
- atraso;
- fila;
- concentração.

---

# 288. Segunda camada

Estatística histórica:

- média;
- mediana;
- percentis;
- tendência.

---

# 289. Terceira camada

Previsão:

- duração;
- atraso;
- capacidade.

---

# 290. Quarta camada

IA generativa:

- resumo;
- explicação;
- perguntas em linguagem natural;
- recomendação contextual.

---

# 291. Essa ordem reduz risco

---

# 292. Exemplo de inteligência sem IA

Regra:

```text
Se prazo comprometido < agora
e tarefa não concluída
→ atrasada
```

Não precisa de modelo.

---

# 293. Exemplo estatístico

```text
Mediana das últimas 50 tarefas:
2,4 dias
```

---

# 294. Exemplo preditivo

```text
Probabilidade de atraso:
72%
```

---

# 295. Exemplo generativo

> Resuma por que existe risco de atraso.

---

# 296. IA precisa usar dados de qualidade

Se histórico estiver errado, resposta também estará.

---

# 297. Garbage in, garbage out

Princípio:

```text
dados ruins
→ inteligência ruim
```

---

# 298. Validação de recomendação

Antes de liberar recurso pago avançado, medir:

- acurácia;
- confiança;
- impacto.

---

# 299. Experimentos

Futuramente, a LPS pode apoiar testes A/B operacionais quando apropriado.

Exemplo:

Fluxo A x Fluxo B.

Não é prioridade do D0.

---

# 300. Cuidado com experimentos em processos críticos

Segurança e negócio vêm primeiro.

---

# 301. Métrica de sucesso da inteligência

A inteligência deve melhorar algo observável.

Exemplos:

- menos atraso;
- menos devolução;
- menor fila;
- menor tempo total;
- maior previsibilidade;
- menor retrabalho.

---

# 302. Não medir sucesso por quantidade de sugestões

---

# 303. Sugestão ignorada não é necessariamente fracasso

Pode ter sido correta, mas impraticável.

A coleta de feedback ajuda.

---

# 304. Decisão humana contextual

Gestor conhece fatores que o sistema ainda não sabe.

---

# 305. IA precisa aprender limites

Se determinado processo possui muitas exceções:

```text
confiança baixa
```

---

# 306. Atividade rara

Se ocorre uma vez por ano, previsão pode ser fraca.

---

# 307. Atividade repetitiva

Se ocorre 500 vezes/mês, previsão pode ser muito melhor.

---

# 308. Inteligência proporcional à repetição

Processos repetitivos são melhores candidatos iniciais.

---

# 309. Primeiro foco de IA

Recomendação:

- processos frequentes;
- dados estruturados;
- impacto claro.

---

# 310. Evitar começar por processos únicos e complexos

---

# 311. Dados de treinamento internos

Não confundir:

```text
histórico usado para cálculo local
```

com:

```text
treinar modelo global
```

São decisões distintas.

---

# 312. Modelos externos

Se a LPS usar provedores externos de IA, política de dados precisa considerar isso.

Tema técnico/jurídico posterior.

---

# 313. Mascaramento

Futuramente, dados sensíveis podem ser removidos antes de enviar ao modelo.

---

# 314. Minimização de dados

Enviar apenas o necessário.

---

# 315. IA não precisa receber banco inteiro

---

# 316. Contexto selecionado

Para resumir uma atividade:

- eventos daquela atividade;
- mensagens autorizadas;
- tarefas;
- prazos.

---

# 317. Menos contexto irrelevante melhora qualidade

---

# 318. Histórico de recomendações por organização

Pode formar memória operacional.

---

# 319. Preferências da empresa

Empresa pode aceitar mais ou menos sugestões automáticas.

---

# 320. Modo conservador

```text
somente insights
```

---

# 321. Modo assistido

```text
insights + sugestões
```

---

# 322. Automação avançada

Somente depois e de forma seletiva.

---

# 323. Não definir esses modos no D0

Apenas preservar arquitetura para evolução.

---

# 324. Alertas simples antes de IA

Exemplos:

```text
atividade sem ação há 3 dias
```

```text
fila cresceu 40% na semana
```

```text
3 devoluções na mesma tarefa
```

---

# 325. Esses alertas já geram valor

---

# 326. Insight de tendência

Exemplo:

> O tempo mediano de fila do Financeiro aumentou de 6h para 14h nas últimas quatro semanas.

---

# 327. Insight de mudança

> Após a alteração do fluxo, devoluções caíram 35%.

---

# 328. Insight de concentração

> 82% das tarefas deste tipo são executadas por uma única pessoa.

---

# 329. Insight de prazo

> 47% das solicitações deste tipo renegociam o prazo inicial.

---

# 330. Insight de capacidade

> O setor recebe em média 25 tarefas/dia e conclui 19.

---

# 331. Insight precisa mostrar período

Sem período, números podem enganar.

---

# 332. Insight precisa mostrar amostra

Exemplo:

```text
Base:
64 atividades
```

---

# 333. Insight precisa permitir detalhamento

Usuário deve poder abrir a lista de casos que compõem o número, conforme autorização.

---

# 334. Explicabilidade por drill-down

**Drill-down** significa ir do indicador agregado para os registros que o compõem.

Isso aumenta confiança.

---

# 335. Inteligência para auditoria

A IA pode ajudar a encontrar:

- alterações atípicas;
- mudanças frequentes;
- inconsistências.

Mas não substituir controles de segurança.

---

# 336. Fraude e abuso

Não é escopo atual da LPS.

Evitar projetar inteligência antifraude sem necessidade.

---

# 337. Aprendizado e governança

A empresa pode querer excluir determinados processos de benchmark externo.

Essa configuração pode existir futuramente.

---

# 338. Aprendizado e exclusão de dados

Se dados forem removidos por obrigação legal, modelos e agregações precisam respeitar política aplicável.

Tema futuro.

---

# 339. Histórico consolidado

A LPS deve preservar dados suficientes para analisar evolução ao longo do tempo.

---

# 340. Mudança de nomenclatura

Se setor “Compras” virar “Suprimentos”, histórico não pode se perder.

---

# 341. Identificador estável

A inteligência deve trabalhar com identificadores, não apenas nomes.

Decisão técnica do banco.

---

# 342. Tipos inativados

Histórico continua utilizável.

---

# 343. Fluxos versionados

Futuramente, inteligência deve saber qual versão foi usada.

---

# 344. Comparação por versão

Exemplo:

```text
Fluxo v1:
3,8 dias

Fluxo v2:
2,9 dias
```

---

# 345. Recomendar manutenção do v2

Somente se contexto e qualidade também forem melhores.

---

# 346. Qualidade e velocidade

O melhor processo não é necessariamente o mais rápido.

Pode ser o que equilibra:

- prazo;
- qualidade;
- retrabalho;
- custo.

---

# 347. Métrica composta

Futuramente, pode existir score de processo.

Mas evitar no D0.

Scores escondem nuances.

---

# 348. Preferir métricas explicáveis

---

# 349. Objetivo final

A LPS deve ajudar a empresa a responder:

> Como estamos trabalhando?

> Onde estamos perdendo tempo?

> Por que isso acontece?

> O que tende a acontecer?

> O que podemos mudar?

> A mudança funcionou?

---

# 350. Inteligência como ciclo fechado

```text
EXECUÇÃO
↓
DADOS
↓
ANÁLISE
↓
INSIGHT
↓
DECISÃO
↓
MUDANÇA
↓
NOVA EXECUÇÃO
↓
NOVOS DADOS
```

Esse é o coração da retroalimentação.

---

# 351. D0 — checklist de dados

```text
[ ] atividade possui tipo/contexto
[ ] dono registrado
[ ] tarefas registradas
[ ] setores registrados
[ ] executores registrados
[ ] timestamps confiáveis
[ ] sessões de tempo
[ ] fila e posição
[ ] prazo solicitado
[ ] prazo comprometido
[ ] devoluções
[ ] motivos
[ ] bloqueios
[ ] escalonamentos
[ ] conclusão
[ ] histórico de alterações
```

---

# 352. D1 — checklist de análise

```text
[ ] médias
[ ] medianas
[ ] tempos por setor
[ ] tempos por tarefa
[ ] gargalos
[ ] devoluções recorrentes
[ ] backlog
[ ] aging
[ ] planejado x realizado
[ ] comparação por período
```

---

# 353. D2 — checklist de previsão

```text
[ ] prazo provável
[ ] risco de atraso
[ ] tempo provável em fila
[ ] capacidade provável
[ ] anomalias
```

---

# 354. D3 — checklist de recomendação

```text
[ ] sugestão de prazo
[ ] sugestão de fluxo
[ ] sugestão de melhoria
[ ] sugestão de treinamento
[ ] sugestão de balanceamento
[ ] resumo automático
```

---

# 355. D4 — checklist de benchmark

```text
[ ] dados agregados
[ ] anonimização
[ ] consentimento
[ ] segmentação por perfil de empresa
[ ] sugestões baseadas em benchmark
```

---

# 356. O que não pertence ao D0

- IA generativa obrigatória;
- previsão automática;
- recomendação automática;
- benchmark externo;
- score de produtividade;
- ranking de pessoas;
- fluxo criado por IA;
- prazo imposto por IA;
- reordenação automática de fila;
- contratação recomendada automaticamente;
- treinamento global de modelo com dados dos clientes.

---

# 357. O que precisa nascer preparado no D0

Mesmo sem IA, o D0 precisa:

- registrar eventos;
- manter histórico;
- separar tempos;
- preservar fluxo real;
- preservar devoluções;
- preservar prazos;
- preservar contexto;
- permitir comparação futura.

---

# 358. Decisões consolidadas neste documento

## Filosofia

- a LPS deve aprender com uso real;
- inteligência começa com dados confiáveis;
- não implementar IA antes de histórico suficiente;
- fatos estruturados têm prioridade.

## Evolução

- primeiro registrar;
- depois medir;
- depois comparar;
- depois identificar padrões;
- depois prever;
- depois recomendar.

## Histórico

- duração é dado central;
- fila é dado central;
- devolução é dado central;
- motivo é dado central;
- fluxo real é mais importante que fluxo planejado para aprendizado.

## Gargalos

- podem ser fila, execução, decisão, retrabalho, capacidade ou terceiro;
- precisam ser identificados com evidência;
- não devem ser atribuídos automaticamente a pessoas.

## Previsões

- serão futuras;
- devem mostrar incerteza;
- devem ser explicáveis;
- precisam de histórico suficiente.

## Sugestões

- prazo pode ser sugerido futuramente;
- fluxo pode ser sugerido futuramente;
- melhoria pode ser sugerida futuramente;
- treinamento pode ser sugerido futuramente;
- decisão final permanece humana.

## IA

- não é o produto;
- é camada de apoio;
- não altera processo silenciosamente;
- deve respeitar permissões;
- deve distinguir fato, previsão e recomendação;
- deve ser auditável.

## Benchmark

- primeiro aprendizado é interno;
- comparação entre empresas é futura;
- exige anonimização, governança e autorização;
- dados identificáveis não devem ser expostos.

## Retroalimentação

- recomendação aplicada precisa ter resultado medido;
- a LPS deve aprender se a melhoria funcionou;
- o sistema também precisa aprender com erros de previsão e recomendações ruins.

---

# 359. Decisões ainda pendentes

Precisam ser detalhadas posteriormente:

- quantidade mínima de casos para gerar sugestões;
- fórmula de confiança;
- estatísticas oficiais;
- critérios de atividades semelhantes;
- definição de complexidade;
- política de benchmark;
- consentimento entre empresas;
- anonimização;
- fornecedor de IA;
- arquitetura de modelos;
- políticas de retenção;
- regras de feedback;
- métricas de qualidade de recomendação;
- automações futuras permitidas;
- limites de atuação autônoma;
- modelo comercial da camada de inteligência.

---

# 360. Relação com os demais documentos

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Fornece:

- atividades;
- tarefas;
- fluxos;
- retornos;
- setores;
- executores.

A inteligência aprende com esses caminhos.

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Fornece:

- posições;
- filas;
- prazos;
- conflitos;
- renegociações;
- escalonamentos.

A inteligência poderá prever capacidade e atraso.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

É a principal base deste documento.

Fornece:

- timestamps;
- duração;
- horas-homem;
- espera;
- gargalos;
- eventos.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Define quais dados a inteligência pode utilizar e exibir para cada usuário.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Fornece contexto textual e permite:

- resumo;
- identificação de risco;
- detecção de compromisso;
- análise de motivo.

## `08_BANCO_DE_DADOS.md`

Precisa preservar os dados necessários para as análises futuras sem exigir remodelagem completa.

---

# 361. Estrutura conceitual de dados para inteligência

Sem fechar tabelas definitivas, a inteligência dependerá de dados equivalentes a:

```text
atividades
tarefas
eventos
sessoes_tempo
passagens_setor
historico_fila
historico_prazos
devolucoes
motivos
bloqueios
escalonamentos
mensagens
```

---

# 362. Dados derivados

Depois podem existir estruturas de:

```text
metricas
agregacoes
insights
previsoes
recomendacoes
feedback_recomendacao
```

Essas estruturas não precisam existir completas no D0.

---

# 363. Evento bruto é mais valioso que indicador isolado

Se guardamos apenas:

```text
tempo médio = 2h
```

perdemos capacidade de recalcular.

Se guardamos eventos:

```text
início
fim
usuário
setor
```

podemos gerar novas métricas no futuro.

---

# 364. Preservar granularidade suficiente

Sem criar volume absurdo desnecessário.

Registrar eventos de negócio relevantes.

---

# 365. Não registrar cada clique

Não agrega inteligência operacional.

---

# 366. Exemplo completo — aprendizado de compra

Após 100 atividades:

```text
Engenharia:
mediana 0,8 dia

Compras:
mediana 2,3 dias

Financeiro:
mediana 0,9 dia

Fornecedor:
mediana 6,8 dias
```

Devoluções:

```text
22%
```

Principal motivo:

```text
especificação incompleta
```

---

# 367. Primeiro insight

> O fornecedor representa a maior parcela do ciclo.

---

# 368. Segundo insight

> Quase um quarto das atividades retorna por especificação incompleta.

---

# 369. Primeira sugestão

> Avaliar validação técnica antes de Compras.

---

# 370. Segunda sugestão

> Considerar emitir o pedido até aproximadamente D+3 quando o prazo final for de 10 dias.

---

# 371. Empresa aplica validação técnica

Depois de 60 novas atividades:

```text
Devoluções:
11%
```

---

# 372. LPS aprende

> A nova etapa reduziu devoluções de 22% para 11%.

---

# 373. Esse é o objetivo final

Não apenas:

```text
mostrar números
```

Mas:

```text
aprender
↓
sugerir
↓
medir resultado
```

---

# 374. Exemplo completo — treinamento

Histórico:

```text
Jennifer:
1h15 mediana
5% devolução

Ryan:
2h40 mediana
7% devolução
```

Tarefas comparáveis.

Insight:

> Existe diferença consistente de tempo sem aumento relevante de devolução.

Sugestão:

> Avaliar compartilhamento do método de Jennifer.

---

# 375. Depois do treinamento

Ryan:

```text
1h50 mediana
6% devolução
```

A LPS demonstra ganho.

---

# 376. Exemplo completo — fila

Histórico do Almoxarifado:

```text
Entrada média:
25 tarefas/dia

Saída média:
19 tarefas/dia
```

Fila:

```text
20 → 28 → 35 → 47
```

Insight:

> O backlog está crescendo de forma estrutural.

---

# 377. Sugestão

> Avaliar capacidade, priorização ou redistribuição.

---

# 378. Não sugerir automaticamente

> Contrate uma pessoa.

Sem análise adicional.

---

# 379. Exemplo completo — prazo

Solicitação de orçamento:

```text
prazo solicitado:
1 dia
```

Histórico de 120 orçamentos semelhantes:

```text
mediana:
3,8 dias

80%:
até 5,1 dias
```

Sugestão futura:

```text
Prazo de 1 dia apresenta alto risco.
```

---

# 380. Exemplo completo — fluxo

Fluxo A:

```text
Engenharia → Compras
```

Devolução:

```text
31%
```

Fluxo B:

```text
Engenharia → Validação → Compras
```

Devolução:

```text
12%
```

Insight:

> O fluxo com validação apresenta menor taxa de devolução.

---

# 381. Recomendação

> Avaliar adoção do Fluxo B como padrão.

---

# 382. Exemplo completo — fornecedor

Fornecedor A:

```text
prazo mediano:
5 dias

variabilidade:
alta
```

Fornecedor B:

```text
prazo mediano:
6 dias

variabilidade:
baixa
```

A LPS pode mostrar.

A decisão comercial considera outros fatores.

---

# 383. Exemplo completo — resumo

Pergunta:

> O que aconteceu nesta atividade?

Resposta futura:

> A atividade foi criada em 10/09 e concluída em 18/09. O maior tempo foi de 7 dias aguardando fornecedor. Houve uma devolução de Compras para Engenharia por especificação incompleta, acrescentando 20 horas ao ciclo. O prazo foi renegociado uma vez e cumprido após a renegociação.

---

# 384. Exemplo completo — risco

Atividade atual:

```text
Prazo restante:
4 dias
```

Histórico das etapas restantes:

```text
mediana:
5,7 dias
```

Alerta:

> Risco elevado de atraso.

Explicação:

> O tempo histórico das etapas restantes é superior ao prazo disponível.

---

# 385. A recomendação pode ser

> Antecipar decisão, aumentar capacidade ou renegociar prazo.

Não escolher sozinha.

---

# 386. Recomendação de foco gerencial

Futuramente:

```text
Top 3 gargalos da semana:
1. aprovação financeira
2. espera de fornecedor
3. devolução por especificação
```

---

# 387. Isso ajuda o gestor a priorizar

Em vez de analisar centenas de tarefas.

---

# 388. Gestão por exceção

A inteligência deve permitir que gestor foque no que foge do padrão.

---

# 389. Exceções

- atraso;
- fila anormal;
- devolução recorrente;
- bloqueio longo;
- prazo incompatível;
- sobrecarga;
- anomalia.

---

# 390. Operação normal não precisa de intervenção constante

---

# 391. Valor da LPS

No início:

```text
transparência
```

Depois:

```text
controle
```

Depois:

```text
aprendizado
```

Depois:

```text
previsibilidade
```

Depois:

```text
recomendação
```

---

# 392. Moat potencial

Um possível diferencial defensável da LPS está em:

- histórico real de execução;
- modelo de processos;
- dados de gargalos;
- aprendizado acumulado;
- benchmark autorizado.

Isso é mais difícil de copiar do que apenas telas.

---

# 393. Vibe coding não replica histórico

Alguém pode copiar:

- layout;
- CRUD;
- timer;
- kanban.

Mas não copia facilmente:

- anos de dados;
- modelos aprendidos;
- benchmark;
- padrões operacionais.

---

# 394. O valor aumenta com o uso

Esse é um possível efeito de retenção.

Quanto mais a empresa usa:

```text
mais histórico
↓
mais inteligência
↓
mais valor
```

---

# 395. Cuidado com lock-in abusivo

O valor deve vir da melhoria, não de impedir exportação de dados.

---

# 396. Dados do cliente

A política de propriedade e portabilidade precisa ser clara.

Tema jurídico/comercial posterior.

---

# 397. Inteligência como serviço

Pode se tornar camada premium:

- diagnósticos;
- previsões;
- recomendações;
- benchmarks;
- copiloto gerencial.

---

# 398. Mas o D0 precisa provar o dado

Sem dados reais e uso real, essa camada é apenas promessa.

---

# 399. Critério para liberar previsão

Só liberar quando:

- amostra suficiente;
- qualidade suficiente;
- erro aceitável;
- explicabilidade mínima.

---

# 400. Critério para liberar recomendação

Só liberar quando:

- existe padrão;
- impacto é mensurável;
- confiança é adequada;
- decisão continua auditável.

---

# 401. Critério para usar benchmark externo

Somente quando:

- autorizado;
- anonimizado;
- comparável;
- governado.

---

# 402. Critério para automatizar

Perguntar:

1. A ação é reversível?
2. O risco é baixo?
3. A previsão é confiável?
4. Há autorização?
5. Existe auditoria?
6. Usuário pode desfazer?

Se não, manter confirmação humana.

---

# 403. Recomendação de arquitetura de produto

Não construir IA primeiro.

Construir:

```text
eventos
histórico
métricas
```

Depois:

```text
insights
```

Depois:

```text
previsões
```

Depois:

```text
IA
```

---

# 404. O banco precisa nascer preparado

Mesmo sem tabelas de IA, precisa registrar corretamente os eventos necessários.

---

# 405. Não supermodelar o futuro

Não criar dezenas de tabelas de machine learning no D0.

---

# 406. Documento 08 deve refletir apenas o necessário agora

E preservar possibilidade de expansão.

---

# 407. Perguntas que a LPS deverá responder no futuro

## Descritivas

- Quanto tempo leva?
- Onde fica mais tempo?
- Quantas vezes volta?
- Quem participa?
- Qual o maior gargalo?

## Diagnósticas

- Por que está atrasando?
- Quais motivos se repetem?
- Onde existe retrabalho?
- Onde existe concentração?

## Preditivas

- Quando provavelmente termina?
- Qual risco de atraso?
- Quanto tempo deve ficar na fila?

## Prescritivas

- Qual prazo sugerido?
- Qual fluxo sugerido?
- O que deveria ser melhorado?
- Onde treinar?
- Onde redistribuir capacidade?

---

# 408. Regra de ouro dos dados

> **A LPS só pode aprender aquilo que consegue observar.**

---

# 409. Regra de ouro da previsão

> **Previsão deve mostrar incerteza e nunca ser apresentada como certeza.**

---

# 410. Regra de ouro da recomendação

> **A LPS sugere; a gestão decide.**

---

# 411. Regra de ouro do benchmark

> **Aprender entre empresas não pode significar expor dados entre empresas.**

---

# 412. Regra de ouro da IA

> **IA deve ampliar a capacidade de gestão, não substituir responsabilidade, auditoria ou regra de negócio.**

---

# 413. Regra de ouro da retroalimentação

> **Toda melhoria sugerida precisa poder ser medida depois para sabermos se realmente funcionou.**

---

# 414. Regra de ouro da confiança

> **Quando não souber, a LPS deve dizer que não sabe.**

---

# 415. Decisões de produto que este documento protege

Este documento impede que a equipe:

- implemente IA antes da base;
- invente prazos sem histórico;
- automatize decisões críticas silenciosamente;
- use benchmark sem governança;
- confunda correlação com causa;
- transforme métricas em julgamento de pessoas;
- esconda incerteza;
- gere recomendações sem medir resultado.

---

# 416. Checklist antes de implementar uma nova inteligência

Perguntar:

```text
[ ] Qual problema resolve?
[ ] Qual decisão melhora?
[ ] Quais dados usa?
[ ] Os dados são confiáveis?
[ ] Existe amostra suficiente?
[ ] O usuário pode entender a recomendação?
[ ] Existe nível de confiança?
[ ] A ação é reversível?
[ ] Precisa de confirmação humana?
[ ] Respeita autorização?
[ ] Podemos medir se funcionou?
```

---

# 417. Se não conseguimos responder

A inteligência ainda não deve ser implementada.

---

# 418. Roadmap conceitual

## D0 — Coletar

```text
atividade
tarefa
tempo
fila
prazo
devolução
motivo
conversa
auditoria
```

## D1 — Analisar

```text
médias
medianas
gargalos
retrabalho
aging
backlog
planejado x realizado
```

## D2 — Prever

```text
duração
risco
fila
capacidade
```

## D3 — Recomendar

```text
prazo
fluxo
melhoria
treinamento
redistribuição
```

## D4 — Aprender entre empresas

```text
benchmark anonimizado
boas práticas
modelos agregados
```

---

# 419. Encerramento

A inteligência da LPS não deve nascer de uma promessa de IA.

Ela deve nascer de uma operação bem registrada.

A primeira missão é responder com precisão:

> O que aconteceu?

Depois:

> Quanto tempo levou?

Depois:

> Onde perdemos tempo?

Depois:

> Isso se repete?

Depois:

> O que provavelmente acontecerá?

E somente então:

> O que deveríamos fazer diferente?

A LPS se torna mais valiosa quando consegue fechar esse ciclo:

```text
TRABALHO
↓
DADO
↓
APRENDIZADO
↓
DECISÃO
↓
MELHORIA
↓
NOVO TRABALHO
```

Esse ciclo é a retroalimentação.

O objetivo não é criar um sistema que “pensa sozinho”.

O objetivo é criar um sistema que acumula memória operacional suficiente para ajudar pessoas a tomar decisões cada vez melhores.

---

# 420. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação da filosofia de inteligência, aprendizado, previsão, recomendação e retroalimentação da LPS |
