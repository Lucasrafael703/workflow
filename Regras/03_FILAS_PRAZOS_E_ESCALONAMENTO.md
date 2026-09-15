# 03 — Filas, Prazos e Escalonamento

> Documento funcional da LPS para gestão de capacidade, posição em fila, negociação de prazo, transparência entre setores e escalonamento de conflitos.

---

# 1. Objetivo deste documento

Este documento define como a LPS deve organizar e tornar visível o trabalho quando uma tarefa entra em um setor.

Ele deve responder:

- como uma fila funciona;
- quem enxerga a fila;
- quem pode alterar sua ordem;
- como o solicitante acompanha sua posição;
- como o setor executor informa capacidade;
- como prazo solicitado e prazo comprometido se relacionam;
- como funciona uma proposta de novo prazo;
- como o dono aceita ou rejeita;
- quando um conflito deve ser escalado;
- como notificações se relacionam com mudanças relevantes;
- quais dados precisam ser registrados para aprendizado futuro;
- como manter transparência sem expor demandas de outros usuários.

Este documento não define:

- o layout final das telas;
- a estrutura física completa do banco;
- as permissões detalhadas por perfil;
- todos os tipos de notificação;
- algoritmos de inteligência artificial;
- regras estatísticas de previsão.

Esses assuntos pertencem aos demais documentos da LPS.

---

# 2. Princípio central

A fila existe para responder:

> **Em que ordem o setor pretende executar suas demandas?**

Ela não deve existir apenas como uma lista visual.

Ela precisa permitir:

- transparência;
- controle;
- previsibilidade;
- negociação de prazo;
- rastreabilidade;
- gestão de capacidade;
- geração de dados;
- identificação de gargalos.

---

# 3. Fila por setor

Cada setor pode possuir sua própria fila.

Exemplo:

```text
Setor:
Almoxarifado
```

Fila:

```text
1. Demanda A
2. Demanda B
3. Demanda C
4. Minha demanda
5. Demanda E
...
17. Demanda Q
```

A fila representa a ordem operacional definida pelo setor.

---

# 4. Fila não é o fluxo da atividade

Os conceitos são diferentes.

## Fluxo

Responde:

> Por quais setores e tarefas a atividade precisa passar?

Exemplo:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

## Fila

Responde:

> Em qual posição esta tarefa está dentro do setor atual?

Exemplo:

```text
Compras:
7 de 23
```

Uma atividade pode mudar de setor e, a cada entrada em um novo setor, entrar em uma nova fila.

---

# 5. Fila como representação de capacidade

A fila é uma fotografia da carga de trabalho atual do setor.

Ela ajuda a responder:

- quantas demandas existem;
- qual a ordem;
- onde está cada tarefa;
- quanto trabalho está aguardando;
- qual setor está sobrecarregado;
- quais tarefas estão próximas de execução;
- quais demandas estão represadas.

A LPS deve permitir transformar essa fila em dados gerenciais.

---

# 6. Posição na fila

Cada tarefa deve possuir uma posição quando estiver aguardando execução em determinado setor.

Exemplo:

```text
4 de 17
```

Isso significa:

```text
3 demandas antes
+
13 demandas depois
+
a própria demanda
```

A posição precisa ser atualizada sempre que a ordem mudar.

---

# 7. A posição é um dado operacional

A posição não é apenas um elemento visual.

A LPS deve registrar:

- posição atual;
- posição anterior;
- data e hora da mudança;
- usuário que alterou;
- setor;
- motivo, quando necessário;
- impacto no prazo, quando aplicável.

---

# 8. Histórico da posição

Exemplo:

```text
09:00 — posição 4 de 17
10:12 — posição 6 de 18
11:40 — posição 11 de 20
13:05 — posição 16 de 21
```

A LPS deve conseguir reconstruir esse histórico.

Isso permite responder:

- quantas vezes a posição mudou;
- quanto a tarefa foi rebaixada;
- quanto a tarefa foi antecipada;
- por quem;
- em quais horários;
- em quais contextos.

---

# 9. Mudança de posição não deve ser invisível

Se uma tarefa muda significativamente na fila, o solicitante não deve descobrir apenas entrando manualmente no sistema.

A LPS precisa ser capaz de notificar mudanças relevantes.

Exemplo:

```text
Sua posição mudou:
4 de 17
↓
16 de 17
```

A definição exata de canal e preferências pertence ao documento de notificações.

---

# 10. Transparência sem exposição

O solicitante precisa entender a situação da própria demanda.

Ele não precisa enxergar os detalhes das demais tarefas.

Exemplo adequado:

```text
Setor:
Almoxarifado

Sua posição:
4 de 17

Status:
Aguardando execução

Prazo comprometido:
Hoje às 16h20
```

Exemplo desnecessário:

```text
1. Receber bobinas do cliente X
2. Separar material da obra Y
3. Carregar caminhão Z
4. Seu pedido
```

A LPS deve mostrar posição sem expor conteúdo alheio.

---

# 11. Visão do solicitante

O solicitante deve conseguir visualizar, quando autorizado:

- setor atual;
- posição na fila;
- quantidade total de demandas;
- status;
- prazo solicitado;
- prazo comprometido;
- responsável atual, quando aplicável;
- alterações relevantes;
- devoluções;
- conclusão.

O objetivo é reduzir necessidade de cobrança manual.

---

# 12. O solicitante não gerencia a fila do outro setor

Saber que está em:

```text
4 de 17
```

não dá ao solicitante o direito de reordenar a fila.

A responsabilidade pela fila pertence ao setor executor e às pessoas autorizadas.

Isso evita conflito operacional.

---

# 13. O solicitante pode questionar, não comandar

Se houver impacto relevante ou prazo incompatível, o solicitante pode:

- solicitar revisão;
- negociar prazo;
- registrar impacto;
- recusar novo prazo;
- acionar escalonamento conforme regra.

Mas não deve simplesmente mover sua tarefa para o topo da fila de outro setor.

---

# 14. Visão do executor

Quem trabalha no setor precisa de uma visão mais completa.

Deve enxergar, conforme autorização:

- fila completa;
- posição;
- prazo solicitado;
- prazo comprometido;
- impacto;
- responsável;
- dono da atividade;
- tempo em fila;
- status;
- tarefas disponíveis;
- tarefas em execução;
- tarefas devolvidas;
- tarefas bloqueadas.

---

# 15. Visão do gestor do setor

O gestor precisa enxergar ainda mais contexto.

Exemplos:

- tamanho total da fila;
- backlog;
- tarefas próximas do vencimento;
- tarefas atrasadas;
- tarefas com conflito de prazo;
- tarefas devolvidas;
- carga por executor;
- capacidade aparente;
- atividades com maior impacto;
- tarefas escaladas;
- histórico de reordenação.

---

# 16. Executor não precisa necessariamente controlar a ordem

Participar do setor não significa poder reordenar a fila.

A LPS deve separar:

```text
participar do setor
```

de:

```text
poder alterar a fila
```

A autorização deve controlar isso.

---

# 17. Quem pode alterar a fila

A regra consolidada é:

> Gestor + pessoas autorizadas.

Não precisa ser apenas o gestor.

Exemplo:

```text
Gestor do Almoxarifado
✅ pode reordenar

Auxiliar autorizado
✅ pode reordenar

Demais membros
❌ não podem reordenar
```

A permissão exata pertence ao documento de autorizações.

---

# 18. Reordenação

A fila precisa ser fácil de mexer.

A operação não pode exigir processo burocrático.

Exemplo de comportamento esperado:

```text
arrastar
↓
soltar
↓
nova ordem salva
```

ou outro mecanismo simples equivalente.

O sistema registra o histórico automaticamente.

---

# 19. Toda reordenação relevante deve ser auditada

Registrar:

- posição anterior;
- nova posição;
- usuário;
- data e hora;
- setor;
- tarefa;
- motivo, quando exigido;
- eventual impacto no prazo.

---

# 20. Motivo de reordenação

Nem toda pequena mudança precisa obrigatoriamente exigir motivo.

Mas mudanças relevantes podem exigir justificativa.

Exemplo:

```text
Posição 3
↓
Posição 15
```

Motivo:

```text
Entrada de demandas bloqueadoras
```

A necessidade de motivo pode ser configurável.

---

# 21. Reordenação não deve apagar a posição anterior

A LPS precisa preservar a sequência histórica.

Exemplo:

```text
4
↓
6
↓
3
↓
8
```

O estado atual é apenas o último valor.

O histórico precisa permanecer disponível.

---

# 22. Fila e prioridade são conceitos diferentes

Prioridade responde:

> Quão importante ou urgente essa demanda é para o setor?

Fila responde:

> Em qual ordem ela será executada agora?

Uma demanda pode ser importante, mas ainda assim não estar em primeiro lugar.

---

# 23. Criticidade não deve ser definida só pelo solicitante

O solicitante conhece o próprio problema.

O setor conhece a carga total.

Exemplo:

Para o solicitante:

```text
Preciso de um veículo hoje.
```

Para o Almoxarifado:

```text
Chegada de 50 bobinas
```

pode ser mais crítica operacionalmente.

Por isso, a LPS não deve transformar urgência declarada pelo solicitante em prioridade automática de fila.

---

# 24. Impacto

O solicitante pode informar o impacto de um atraso.

Exemplo:

```text
Se atrasar, equipe ficará parada.
```

Ou:

```text
Se atrasar, cliente não recebe proposta.
```

Impacto é informação de contexto.

Não é necessariamente a posição final da fila.

---

# 25. Prioridade operacional

A prioridade operacional é definida pelo setor executor, conforme sua realidade.

Ela pode considerar:

- impacto;
- prazo;
- disponibilidade;
- dependências;
- capacidade;
- demanda bloqueadora;
- risco;
- sequência operacional.

No D0, essa avaliação será humana.

---

# 26. Risco calculado pela LPS

Futuramente, a LPS poderá estimar risco com base em:

- histórico;
- tempo restante;
- tempo típico;
- fila atual;
- dependências;
- fornecedor;
- atrasos anteriores.

No D0, esse risco não precisa ser calculado automaticamente.

---

# 27. Prazo solicitado

Prazo solicitado é a data desejada por quem precisa da entrega.

Exemplo:

```text
Solicitado para:
Hoje às 17h
```

Representa necessidade.

Não representa garantia de capacidade.

---

# 28. Prazo comprometido

Prazo comprometido é a data que o setor executor declara que consegue cumprir.

Exemplo:

```text
Comprometido para:
Terça-feira às 15h
```

Esse prazo deve refletir:

- fila;
- capacidade;
- prioridade;
- contexto;
- dependências.

---

# 29. Prazo solicitado e comprometido devem coexistir

Nunca substituir um pelo outro como se fossem a mesma coisa.

Exemplo:

```text
Prazo solicitado:
12/09 17h

Prazo comprometido:
15/09 15h
```

Essa diferença é informação gerencial.

---

# 30. Divergência de prazo

Quando:

```text
Prazo comprometido
>
Prazo solicitado
```

existe divergência.

A LPS precisa deixar isso visível.

A divergência pode indicar:

- sobrecarga;
- conflito de prioridade;
- prazo irreal;
- falta de capacidade;
- planejamento inadequado;
- dependência externa.

---

# 31. Proposta de novo prazo

O setor executor pode propor um novo prazo.

Exemplo:

```text
Prazo solicitado:
Hoje
```

Setor responde:

```text
Consigo entregar:
Terça-feira às 15h
```

A proposta deve ser estruturada no sistema.

Não apenas enviada em mensagem.

---

# 32. Proposta não substitui prazo automaticamente

Enquanto o dono não aceitar, o sistema precisa mostrar:

```text
Prazo solicitado:
Hoje

Novo prazo proposto:
Terça-feira às 15h

Status:
Aguardando decisão
```

---

# 33. Aceite

Se o dono aceita:

```text
Novo prazo proposto
↓
Prazo comprometido
```

O sistema registra:

- quem propôs;
- quando;
- qual era o prazo anterior;
- quem aceitou;
- quando;
- novo prazo comprometido.

---

# 34. Rejeição

Se o dono rejeita:

```text
Novo prazo proposto
↓
Recusado
```

A tarefa não deve ficar indefinidamente em conflito silencioso.

A LPS deve iniciar o escalonamento conforme regra configurada.

---

# 35. Rejeição precisa de contexto

Pode ser útil registrar:

```text
Motivo da recusa:
Equipe da obra ficará parada.
```

Esse contexto pode ser importante para gestores.

A obrigatoriedade deve ser configurável.

---

# 36. Negociação de prazo

O fluxo conceitual é:

```text
Solicitante define necessidade
↓
Setor avalia capacidade
↓
Aceita o prazo
OU
propõe novo prazo
↓
Dono aceita
OU
recusa
↓
Se recusado:
escalonamento
```

---

# 37. Negociação não deve acontecer somente por chat

A conversa pode apoiar.

Mas as decisões precisam virar dados estruturados.

Exemplo:

Mensagem:

> Consigo fazer terça.

Ação estruturada:

```text
Propor novo prazo
```

---

# 38. Histórico de prazo

A LPS deve preservar todas as alterações.

Exemplo:

```text
Prazo solicitado:
12/09

Primeira proposta:
14/09

Recusado

Segunda proposta:
13/09

Aceito
```

Isso permite medir:

- quantidade de renegociações;
- frequência de conflito;
- diferença média entre solicitado e comprometido.

---

# 39. Prazo não deve ser apagado quando renegociado

O sistema deve manter:

- prazo original;
- propostas;
- rejeições;
- aceite;
- prazo atual;
- alterações posteriores.

---

# 40. Prazo de atividade e prazo de tarefa

A atividade pode possuir prazo final.

As tarefas podem possuir prazos próprios.

Exemplo:

```text
Atividade:
Material disponível até 20/09
```

Tarefas:

```text
Engenharia:
13/09

Compras:
15/09

Financeiro:
16/09

Fornecedor:
20/09
```

No início, esses prazos serão definidos manualmente.

---

# 41. Distribuição manual no D0

A LPS ainda não possui inteligência suficiente para distribuir automaticamente o prazo total.

Por isso, no D0:

> as pessoas informam os prazos.

O sistema registra.

Depois aprende.

---

# 42. Aprendizado futuro sobre prazo

Com histórico suficiente, a LPS poderá perceber:

```text
Fornecedor:
média de 7 dias
```

Se o prazo total é:

```text
10 dias
```

então poderá sugerir:

```text
Restam aproximadamente 3 dias para as etapas internas.
```

Essa capacidade pertence à evolução futura.

---

# 43. Compromisso do setor

O prazo comprometido é uma declaração operacional.

Por isso, precisa ser tratado com responsabilidade.

A LPS deve permitir medir futuramente:

- quantos prazos foram cumpridos;
- quantos foram renegociados;
- quantos foram recusados;
- quanto de atraso existe por setor;
- quais tipos de tarefa têm menor previsibilidade.

---

# 44. Fila e prazo precisam conversar

A posição deve ajudar a contextualizar o prazo.

Exemplo:

```text
Posição:
4 de 17

Prazo comprometido:
Hoje às 16h20
```

Se a tarefa cai para:

```text
16 de 17
```

talvez o prazo precise ser revisado.

A LPS deve registrar esse tipo de evento.

---

# 45. Mudança de posição pode afetar previsão

No D0, o sistema pode simplesmente:

- registrar posição;
- registrar prazo.

Futuramente, poderá detectar:

> Sua posição mudou significativamente. O prazo comprometido está em risco.

---

# 46. Notificação de mudança de posição

A decisão consolidada é:

> toda mudança de posição pode gerar notificação dentro da LPS.

Como evitar excesso será detalhado no documento de notificações.

O histórico deve existir independentemente do canal de aviso.

---

# 47. Exemplo de notificação

```text
Sua posição mudou:
4 de 17 → 5 de 17
```

Outro exemplo:

```text
Sua posição mudou:
5 de 17 → 16 de 18
```

A configuração pode decidir quais canais utilizar.

---

# 48. Notificação de conclusão

Quando uma tarefa relevante ou a atividade é concluída, o dono precisa ser informado.

Outros participantes podem ser notificados conforme configuração.

---

# 49. Conclusão da tarefa na fila

Quando a tarefa é concluída:

- ela deixa a fila ativa;
- sua posição final fica histórica;
- o evento de conclusão é registrado;
- o próximo passo do fluxo pode ser liberado.

---

# 50. Tarefa iniciada

Ao iniciar execução, ela pode:

- continuar representada na fila como “em execução”;
- ou sair da seção de aguardando.

A definição visual pertence ao documento de experiência.

Conceitualmente, a LPS precisa distinguir:

```text
aguardando execução
```

de:

```text
em execução
```

---

# 51. Tempo em fila

A LPS deve conseguir medir:

```text
entrada na fila
↓
início da execução
```

Isso gera:

```text
tempo em fila
```

Esse indicador é essencial para descobrir gargalos.

---

# 52. Tempo de execução

Também deve medir:

```text
início
↓
conclusão
```

considerando sessões reais de trabalho conforme o documento de auditoria.

---

# 53. Fila longa não significa necessariamente setor lento

Exemplo:

Um setor pode ter muitas demandas, mas alta capacidade.

Outro pode ter poucas, mas muito complexas.

Por isso, o gestor deve combinar:

- tamanho da fila;
- tempo médio;
- capacidade;
- complexidade;
- execução;
- espera.

---

# 54. Posição não deve ser usada isoladamente como previsão

Estar em:

```text
4 de 17
```

não significa necessariamente estar perto da conclusão.

As três demandas anteriores podem levar:

```text
10 minutos
```

ou:

```text
3 dias
```

No D0, a posição gera transparência.

No futuro, o histórico poderá gerar previsão.

---

# 55. Transparência é o primeiro ganho

Antes de a LPS prever prazo, ela já entrega valor ao mostrar:

```text
Sua posição é 4 de 17.
```

Isso reduz incerteza.

---

# 56. Escalonamento

Escalonamento é o mecanismo usado quando um conflito operacional precisa subir de nível.

Exemplos:

- prazo recusado;
- tarefa atrasada;
- bloqueio relevante;
- conflito de prioridade;
- ausência de resposta;
- risco de impacto maior.

---

# 57. Escalonamento não é punição

O objetivo é levar o problema para quem possui autoridade para decidir.

Exemplo:

```text
Solicitante precisa hoje
↓
Setor consegue apenas amanhã
↓
Novo prazo recusado
↓
Gestores envolvidos precisam decidir
```

---

# 58. Escalonamento configurável

A empresa deve poder definir:

- quem recebe;
- quando recebe;
- em qual nível;
- em quais tipos de tarefa;
- em quais atrasos;
- em quais conflitos;
- em quais impactos.

A LPS não deve fixar organogramas no código.

---

# 59. Exemplo de escalonamento por conflito de prazo

```text
Prazo solicitado
↓
Novo prazo proposto
↓
Recusado
↓
Gestor do setor executor
+
Gestor do dono da atividade
↓
Decisão
```

---

# 60. Exemplo de escalonamento por atraso

```text
Prazo comprometido atingido
↓
Tarefa ainda aberta
↓
Aviso ao executor
↓
Escalonamento ao gestor
```

A sequência pode variar por empresa.

---

# 61. Escalonamento por níveis

Futuramente, pode existir:

```text
Nível 1:
Executor

Nível 2:
Gestor do setor

Nível 3:
Dono + gestor

Nível 4:
Gestão superior
```

A configuração precisa ser flexível.

---

# 62. Escalonamento automático

A LPS deve suportar escalonamento automático por regra.

Exemplo:

```text
Prazo ultrapassado
↓
Regra encontrada
↓
Escalonar
```

No D0, começar com regras simples.

---

# 63. Escalonamento manual

Também pode existir ação:

```text
Escalar
```

para situações não previstas automaticamente.

Essa ação deve ser autorizada e auditada.

---

# 64. Todo escalonamento deve gerar histórico

Registrar:

- origem;
- motivo;
- data e hora;
- usuário;
- destinatários;
- nível;
- tarefa;
- situação naquele momento;
- decisão posterior.

---

# 65. Escalonamento precisa de motivo

Exemplos:

```text
Prazo recusado
```

```text
Impacto operacional elevado
```

```text
Tarefa atrasada
```

```text
Bloqueio sem solução
```

```text
Conflito de prioridade
```

---

# 66. Escalonamento precisa terminar em decisão

O sistema não deve apenas “avisar” e deixar indefinido.

Futuramente, deve ser possível registrar:

- decisão;
- novo prazo;
- mudança de prioridade;
- mudança de responsável;
- manutenção do plano;
- encerramento do escalonamento.

---

# 67. Gestor precisa estar ciente do que pode travar sua área

A empresa deve poder configurar quais situações exigem ciência do gestor.

Exemplos:

- tarefas críticas;
- tarefas bloqueadoras;
- devoluções;
- atrasos;
- conflitos de prazo;
- escalonamentos.

Essa ciência não significa necessariamente aprovação.

---

# 68. Ciência e aprovação são diferentes

Exemplo:

```text
Gestor foi notificado
```

não significa:

```text
Gestor aprovou
```

A LPS deve preservar essa diferença quando aplicável.

---

# 69. Impacto e escalonamento

Impacto pode ser usado como critério para escalonamento.

Exemplo:

```text
Se atraso parar uma equipe de obra:
escalonar imediatamente
```

Mas impacto não deve automaticamente definir a posição da fila.

---

# 70. Bloqueadores

Uma tarefa pode ser considerada bloqueadora quando impede avanço significativo de outras atividades.

Exemplo:

```text
Pagamento não realizado
↓
Fornecedor não libera material
↓
Obra para
```

Essas relações podem justificar regra especial de escalonamento.

---

# 71. Bloqueador não deve depender apenas da percepção do solicitante

A empresa pode definir critérios próprios.

No D0, começar de forma simples:

- impacto informado;
- validação do setor;
- escalonamento manual ou parametrizado.

---

# 72. Histórico de fila como dado de gestão

Depois de meses, a LPS poderá responder:

- quanto tempo uma tarefa fica em cada posição;
- quantas vezes é rebaixada;
- quantas vezes é antecipada;
- quais setores mais reordenam;
- quais tipos de tarefa frequentemente perdem posição;
- quais tarefas entram como urgência.

---

# 73. Entrada emergencial

Pode existir situação em que uma nova demanda entra no topo.

Exemplo:

```text
Falha crítica
```

Isso é permitido.

Mas deve ficar registrado.

---

# 74. Urgência recorrente é um dado

Se um setor possui muitas “urgências” que furam fila, isso pode indicar:

- planejamento ruim;
- falta de capacidade;
- processo desorganizado;
- regra inadequada.

A LPS deve permitir enxergar esse padrão.

---

# 75. Fila e gestão de capacidade

O objetivo futuro é permitir que o gestor entenda:

```text
Demanda
versus
Capacidade
```

A fila é um dos dados necessários.

---

# 76. Capacidade não é apenas quantidade de pessoas

Pode depender de:

- habilidade;
- tipo de tarefa;
- complexidade;
- disponibilidade;
- experiência;
- ferramentas;
- dependências.

A LPS não deve reduzir capacidade a:

```text
número de funcionários
```

---

# 77. Capacidade aprendida pelo histórico

Futuramente, a LPS pode observar:

```text
Setor X conclui em média 18 tarefas/dia deste tipo.
```

Isso permite melhorar previsões.

No D0, basta registrar dados corretamente.

---

# 78. Capacidade por tipo de tarefa

Um setor pode ser rápido em um tipo de demanda e lento em outro.

Exemplo:

```text
Cotação simples:
30 min

Cotação complexa:
4h
```

A inteligência futura precisa considerar o contexto.

---

# 79. Previsão de conclusão

No D0, pode ser manual.

Exemplo:

```text
Prazo comprometido:
amanhã às 14h
```

Futuramente, a LPS pode calcular previsão com base em:

- posição;
- tempo histórico;
- carga;
- capacidade;
- tipo de tarefa.

---

# 80. Posição exata foi escolhida como padrão

A decisão consolidada é:

> o solicitante deve enxergar a posição exata.

Exemplo:

```text
4 de 17
```

Não apenas:

```text
Em breve
```

ou:

```text
Aguardando
```

---

# 81. Exibir total da fila

O total ajuda a dar contexto.

```text
4 de 17
```

é mais informativo que:

```text
posição 4
```

---

# 82. Alteração da quantidade total

A fila pode mudar mesmo que a posição não mude.

Exemplo:

```text
4 de 17
↓
4 de 25
```

Esse dado também pode ser relevante.

O histórico deve registrar entradas e saídas.

---

# 83. A posição pode melhorar sem ação direta

Exemplo:

```text
4 de 17
↓
3 de 16
↓
2 de 15
```

porque demandas anteriores foram concluídas.

Essas mudanças podem ser geradas automaticamente.

---

# 84. A posição pode piorar

Exemplo:

```text
4 de 17
↓
7 de 19
```

por reordenação ou entrada prioritária.

A LPS precisa diferenciar:

- mudança automática por conclusão;
- mudança manual;
- mudança por nova entrada prioritária.

---

# 85. Motivo da mudança

Futuramente, a LPS pode exibir ao solicitante uma explicação simples.

Exemplo:

```text
Sua posição mudou de 4 para 7.
Motivo: reordenação da fila pelo setor.
```

Sem expor detalhes das outras tarefas.

---

# 86. Auditoria interna mais detalhada

Internamente, gestores podem enxergar:

- quem reordenou;
- qual tarefa passou à frente;
- motivo;
- horário;
- impacto.

O solicitante não precisa ver tudo.

---

# 87. Regras configuráveis

A LPS deve permitir configurar, por empresa:

- quem pode visualizar fila completa;
- quem vê somente própria posição;
- quem pode reordenar;
- quem pode propor prazo;
- quem pode aceitar;
- quem pode rejeitar;
- quem recebe escalonamento;
- quando escalar;
- quais eventos notificam;
- quais mudanças exigem motivo.

---

# 88. Configurabilidade não deve destruir consistência

Mesmo configurável, os conceitos permanecem:

- fila;
- posição;
- prazo solicitado;
- prazo comprometido;
- proposta;
- aceite;
- rejeição;
- escalonamento;
- histórico.

A empresa configura comportamento, não redefine o significado central.

---

# 89. Exemplo de regra de empresa A

```text
Reordenação:
Gestores e coordenadores

Novo prazo:
Pode ser proposto por qualquer executor

Aceite:
Dono da atividade

Escalonamento:
Após rejeição
```

---

# 90. Exemplo de regra de empresa B

```text
Reordenação:
Somente gestor

Novo prazo:
Somente gestor

Aceite:
Dono

Escalonamento:
Dono + gestor superior
```

A mesma LPS deve atender ambas.

---

# 91. D0 deve evitar parametrização excessiva

Ser configurável não significa construir centenas de parâmetros no primeiro dia.

No D0, priorizar regras realmente necessárias para:

- fila;
- prazo;
- reordenação;
- aceite;
- rejeição;
- escalonamento;
- notificação essencial.

---

# 92. Transparência como redução de cobrança

A LPS deve reduzir mensagens como:

> “E aí?”

> “Vai sair quando?”

> “Você viu?”

> “Onde está?”

A posição e o prazo comprometido já respondem parte dessas dúvidas.

---

# 93. Exemplo de experiência do solicitante

```text
Tarefa:
Separar material

Setor:
Almoxarifado

Posição:
4 de 17

Prazo solicitado:
Hoje às 16h

Prazo comprometido:
Hoje às 17h30

Status:
Aguardando execução
```

Isso é suficiente para acompanhar sem enxergar o restante da fila.

---

# 94. Exemplo de mudança

Depois:

```text
Posição:
16 de 18

Prazo comprometido:
Amanhã às 09h
```

A LPS deve notificar a mudança conforme regra.

---

# 95. Exemplo de conflito

Solicitante:

```text
Preciso hoje.
```

Setor:

```text
Consigo amanhã.
```

Dono:

```text
Recusa.
```

Sistema:

```text
Escalonar.
```

---

# 96. Exemplo de decisão gerencial

Gestor decide:

```text
Manter prazo do setor
```

ou:

```text
Antecipar a demanda
```

ou:

```text
Redirecionar recurso
```

ou:

```text
Aceitar impacto
```

A decisão deve ficar registrada.

---

# 97. O sistema não decide sozinho no D0

A LPS estrutura o conflito.

Pessoas autorizadas decidem.

A inteligência futura pode sugerir.

---

# 98. Aprendizado a partir dos conflitos

Depois de histórico suficiente, será possível analisar:

- quais setores mais rejeitam prazos;
- quais solicitantes mais pedem prazos inviáveis;
- quais tarefas sofrem maior renegociação;
- quais processos têm baixa previsibilidade;
- onde falta capacidade.

---

# 99. Aprendizado a partir da fila

Também será possível analisar:

- tempo médio em fila;
- posição média de entrada;
- frequência de reordenação;
- tempo até primeira ação;
- quantidade média de demandas;
- horários de pico;
- volume por período.

---

# 100. Aprendizado a partir do escalonamento

Perguntas futuras:

- quais conflitos mais escalam;
- quem resolve;
- quanto tempo leva;
- quais setores geram mais escalonamentos;
- quais motivos se repetem;
- quais regras precisam mudar.

---

# 101. Fila não deve incentivar competição tóxica

Mostrar posição não significa criar ranking de “quem merece mais”.

O objetivo é transparência.

O solicitante precisa saber:

> Onde está minha demanda?

Não:

> Por que a demanda do outro é mais importante que a minha?

---

# 102. Privacidade entre demandas

A LPS deve aplicar acesso contextual.

O solicitante vê:

```text
posição
```

mas não necessariamente:

- título das outras tarefas;
- cliente;
- valor;
- descrição;
- responsáveis;
- anexos.

---

# 103. Informação mínima necessária

Para acompanhar fila, o solicitante precisa no mínimo:

```text
posição
total
setor
status
prazo
```

Detalhes adicionais dependem de permissão.

---

# 104. Fila do próprio setor

Membros autorizados podem enxergar informações mais completas.

A política será definida por perfil e ação.

---

# 105. Mudança de fila e conversa

A reordenação não deve depender de justificar via mensagem.

Se motivo for exigido, ele deve ser estruturado.

A conversa pode complementar.

---

# 106. Mudança de prazo e conversa

Da mesma forma:

Mensagem:

> Não consigo hoje.

não substitui:

```text
Propor novo prazo
```

---

# 107. Rejeição e conversa

A recusa pode possuir comentário.

Mas o estado formal é:

```text
Proposta rejeitada
```

---

# 108. Escalonamento e conversa

A discussão pode acontecer na atividade.

A decisão precisa ser registrada formalmente.

---

# 109. Estado de conflito

Quando existe proposta recusada e decisão pendente, a tarefa pode possuir estado equivalente a:

```text
Prazo em conflito
```

O nome final será definido em outro documento.

---

# 110. Conflito não significa parar execução

Dependendo da situação, a tarefa pode continuar sendo executada enquanto o prazo é discutido.

A LPS não deve obrigar bloqueio automático salvo regra específica.

---

# 111. Mudança de posição durante execução

Uma tarefa já em execução não deve ser tratada exatamente como uma tarefa aguardando.

A fila precisa distinguir estados.

Exemplo:

```text
Aguardando
Em execução
Bloqueada
```

A interface detalhará isso.

---

# 112. Filas múltiplas por setor

No D0, preferir uma fila principal por setor.

Evitar criar dezenas de subfilas antes da necessidade.

Futuramente, pode existir segmentação por:

- tipo;
- equipe;
- prioridade;
- processo.

---

# 113. Simplicidade de fila

A fila precisa ser utilizável rapidamente.

Idealmente:

- ordenar;
- filtrar;
- localizar;
- assumir;
- abrir;
- iniciar.

Sem excesso de telas.

---

# 114. Fila deve refletir trabalho real

Se o setor mantém tarefas fora da LPS, a fila fica incompleta.

A adoção depende de o sistema ser suficientemente simples para virar fonte principal de acompanhamento.

---

# 115. Fonte de verdade operacional

O objetivo é que a LPS se torne a referência para perguntas como:

> O que está na fila do setor?

> Qual a ordem?

> Qual o prazo?

> Qual está atrasada?

---

# 116. Não criar fila paralela em planilha

Se o setor precisa continuar mantendo planilha externa para controlar ordem, a LPS não resolveu o problema.

---

# 117. Posição como compromisso de transparência

A posição precisa ser confiável.

Se o setor não atualiza a fila, o dado perde valor.

Por isso, reordenar precisa ser fácil.

---

# 118. Mudanças automáticas

A LPS deve atualizar posição automaticamente quando:

- tarefa anterior é concluída;
- tarefa é removida da fila ativa;
- nova tarefa entra;
- tarefa muda de setor;
- tarefa é cancelada.

---

# 119. Mudanças manuais

Ocorrem quando pessoa autorizada reordena.

Essas mudanças precisam ser distinguíveis no histórico.

---

# 120. Entradas prioritárias

Quando uma tarefa entra acima de outras:

```text
nova tarefa urgente
↓
posição 1
```

o histórico deve deixar claro que houve entrada prioritária.

---

# 121. Saída temporária

Uma tarefa bloqueada pode, conforme regra, sair da fila operacional ativa sem desaparecer do backlog.

A definição precisa ser tratada com cuidado posteriormente.

---

# 122. Backlog x fila ativa

Conceitualmente:

```text
Backlog:
tudo que existe para o setor
```

```text
Fila ativa:
ordem atual de execução
```

No D0, os conceitos podem ser simplificados visualmente.

---

# 123. Pendência externa

Uma tarefa aguardando fornecedor pode não ocupar posição operacional da mesma forma que uma tarefa pronta para execução.

A LPS deve, futuramente, separar:

```text
aguardando ação interna
```

de:

```text
aguardando terceiro
```

Isso evita distorção de capacidade.

---

# 124. Posição deve considerar tarefas realmente executáveis

Se uma tarefa está bloqueada, pode não fazer sentido ocupar a mesma fila de execução.

A regra exata será definida depois.

---

# 125. SLA

SLA significa **Service Level Agreement**, ou acordo de nível de serviço.

A LPS pode futuramente trabalhar com metas de atendimento.

Exemplo:

```text
Primeira resposta:
até 4h
```

```text
Conclusão:
até 2 dias
```

Mas SLA não é obrigatório no D0.

---

# 126. Prazo comprometido é mais importante no D0

Antes de construir SLA sofisticado, a LPS precisa validar:

- pedido;
- fila;
- prazo solicitado;
- prazo comprometido;
- execução;
- atraso.

---

# 127. Escalonamento baseado em percentual do prazo

Futuramente, pode existir:

```text
80% do prazo consumido
↓
alerta
```

```text
100%
↓
escalonamento
```

No D0, começar com regras simples de vencimento e rejeição.

---

# 128. Escalonamento baseado em posição

Futuramente, pode existir alerta se a tarefa:

- cai muitas posições;
- fica parada;
- não avança;
- acumula reordenações.

Não é obrigatório no D0.

---

# 129. Escalonamento baseado em impacto

Também pode existir regra:

```text
Impacto alto + prazo em risco
↓
escalar
```

Deixar para evolução após validar dados.

---

# 130. Regras devem ser explicáveis

O usuário deve conseguir entender por que houve escalonamento.

Evitar “caixa-preta”.

Exemplo:

```text
Escalonado porque:
prazo comprometido ultrapassado em 2h.
```

---

# 131. Histórico de decisão

Quando gestor resolve conflito, registrar:

- decisão;
- responsável;
- data;
- novo prazo;
- nova posição, se alterada;
- observação.

---

# 132. Decisão pode alterar fila

Exemplo:

Gestor decide:

```text
Antecipar demanda
```

Então:

```text
posição 8
↓
posição 2
```

A mudança precisa estar vinculada à decisão.

---

# 133. Decisão pode manter fila

Exemplo:

Gestor decide:

```text
Manter posição atual
```

A recusa do solicitante não necessariamente muda a fila.

---

# 134. Decisão pode alterar recurso

Exemplo:

```text
Adicionar executor
```

para tentar cumprir prazo sem alterar prioridade.

Esse tipo de ação será analisado posteriormente.

---

# 135. Escalonamento precisa terminar

Um escalonamento não deve ficar aberto indefinidamente.

Deve possuir estado como:

```text
aberto
em análise
resolvido
```

A nomenclatura será definida depois.

---

# 136. Escalonamento resolvido não apaga conflito

O histórico deve preservar:

- problema;
- decisão;
- resultado.

---

# 137. Gestão por exceção

No futuro, o gestor não deveria precisar olhar todas as tarefas.

A LPS deve destacar exceções:

- atraso;
- conflito;
- gargalo;
- fila crescendo;
- reordenação excessiva;
- devolução;
- bloqueio.

Isso reduz carga gerencial.

---

# 138. D0 ainda pode exigir acompanhamento mais manual

No início, não haverá inteligência suficiente.

O importante é capturar dados para evoluir.

---

# 139. Fila e notificações configuráveis

A empresa deve poder definir quais eventos geram aviso.

Exemplos:

- qualquer mudança de posição;
- mudança superior a X posições;
- mudança de prazo;
- entrada em conflito;
- conclusão;
- atraso.

A decisão exata será detalhada no documento 06.

---

# 140. O dono deve sempre saber da conclusão

A decisão consolidada é:

> conclusão da atividade deve notificar o dono.

Demais notificações podem ser configuráveis.

---

# 141. Nova proposta de prazo deve ser visível

Não pode ficar escondida.

O dono precisa:

- receber aviso;
- visualizar;
- aceitar;
- rejeitar.

---

# 142. Recusa deve gerar escalonamento

A decisão consolidada é:

> se o novo prazo proposto for recusado, o sistema deve escalar automaticamente conforme regra.

---

# 143. Exemplo completo — orçamento

Solicitação:

```text
Entregar orçamento hoje
```

Setor Comercial possui:

```text
negociação de R$ 10 milhões em fechamento
```

O executor avalia:

```text
Não consigo entregar hoje.
```

Propõe:

```text
Terça-feira às 15h.
```

O dono:

```text
Aceita
```

Resultado:

```text
Prazo comprometido = terça-feira 15h
```

Tudo registrado.

---

# 144. Exemplo completo — conflito

Mesmo cenário.

Dono:

```text
Recusa.
```

Sistema:

```text
Escalonamento automático.
```

Gestores decidem:

```text
manter terça-feira
```

ou:

```text
repriorizar a fila
```

A decisão fica auditada.

---

# 145. Exemplo completo — Almoxarifado

Solicitante:

```text
Preciso de veículo às 17h.
```

Almoxarifado:

```text
Fila atual:
17 demandas
```

Solicitante vê:

```text
4 de 17
```

Não vê:

- nomes;
- conteúdos;
- clientes;
- valores das outras demandas.

Depois:

```text
posição 16 de 18
```

O solicitante é avisado conforme regra.

---

# 146. Exemplo completo — mudança de capacidade

Se o setor adiciona um segundo executor, a fila pode avançar mais rápido.

No futuro, a LPS poderá aprender:

```text
Com 1 executor:
média 12 tarefas/dia

Com 2 executores:
média 20 tarefas/dia
```

No D0, basta registrar execução.

---

# 147. Exemplo de dado gerencial

Depois de histórico suficiente:

```text
Setor: Compras

Tempo médio em fila:
1,8 dia

Tempo médio em execução:
3,2h

Renegociação de prazo:
34%

Escalonamento:
8%

Devoluções:
21%
```

Isso começa a mostrar capacidade e processo.

---

# 148. O que não fazer

Evitar:

- mostrar todas as demandas para qualquer solicitante;
- permitir que qualquer pessoa mude a fila;
- apagar histórico de posição;
- substituir prazo solicitado pelo comprometido;
- resolver conflito apenas por mensagem;
- deixar proposta recusada sem escalonamento;
- fixar gestores e regras no código;
- usar posição como previsão exata no D0;
- criar parametrização excessiva antes da necessidade.

---

# 149. O que pertence ao D0

O D0 precisa suportar:

- fila por setor;
- posição exata;
- total de demandas;
- visão do solicitante;
- visão interna do setor;
- reordenação por pessoas autorizadas;
- histórico de posição;
- prazo solicitado;
- prazo comprometido;
- proposta de novo prazo;
- aceite;
- rejeição;
- escalonamento básico;
- notificações essenciais;
- auditoria de mudanças.

---

# 150. O que pode ficar depois do D0

Pode ficar para evolução:

- previsão automática;
- SLA sofisticado;
- capacidade calculada automaticamente;
- risco preditivo;
- prioridade sugerida por IA;
- reordenação automática;
- múltiplas filas por setor;
- regras complexas por tipo de tarefa;
- previsão de conclusão baseada em histórico;
- benchmark entre empresas.

---

# 151. Dados mínimos que precisam ser preservados

Para fila:

- setor;
- tarefa;
- posição;
- total da fila;
- entrada;
- saída;
- alterações;
- autor;
- data e hora.

Para prazo:

- solicitado;
- proposto;
- comprometido;
- histórico;
- quem propôs;
- quem aceitou;
- quem recusou;
- data e hora.

Para escalonamento:

- motivo;
- origem;
- destinatário;
- nível;
- decisão;
- datas;
- encerramento.

---

# 152. Métricas futuras derivadas

A partir destes dados, a LPS poderá calcular:

- tempo médio em fila;
- variação de posição;
- frequência de reordenação;
- percentual de prazos renegociados;
- diferença média entre solicitado e comprometido;
- percentual de cumprimento;
- taxa de escalonamento;
- tempo para resolver conflito;
- tamanho médio da fila;
- tendência de backlog;
- capacidade por setor.

---

# 153. Perguntas que a LPS deverá responder

## Para o solicitante

- Onde está minha tarefa?
- Qual minha posição?
- Quantas demandas existem?
- Qual o prazo comprometido?
- Mudou algo?
- Foi concluída?

## Para o executor

- O que faço agora?
- Qual a ordem?
- Qual o prazo?
- Quem é o dono?
- O que está em conflito?

## Para o gestor

- Qual o tamanho da fila?
- Onde está o gargalo?
- Quantos prazos estão em conflito?
- Quantas tarefas estão atrasadas?
- Quantas foram escaladas?
- Quanto tempo as tarefas esperam?
- A capacidade está compatível com a demanda?

---

# 154. Decisões consolidadas neste documento

## Fila

- existe por setor;
- posição exata é visível ao solicitante;
- total também deve ser exibido;
- solicitante não precisa enxergar outras demandas;
- pessoas autorizadas podem reordenar;
- mudanças ficam auditadas.

## Reordenação

- deve ser simples;
- pode ser realizada por gestor e pessoas autorizadas;
- histórico não é apagado;
- motivo pode ser exigido em mudanças relevantes.

## Prazo

- prazo solicitado e comprometido são diferentes;
- ambos devem ser preservados;
- setor pode propor novo prazo;
- dono pode aceitar ou rejeitar;
- histórico de negociação deve permanecer.

## Escalonamento

- é obrigatório como conceito;
- é configurável;
- recusa de novo prazo gera escalonamento;
- escalonamento deve produzir decisão;
- histórico precisa ser preservado.

## Transparência

- posição deve reduzir cobrança;
- transparência não significa exposição;
- solicitante vê sua situação;
- setor vê sua fila;
- gestor vê capacidade e conflitos.

## Inteligência

- no D0, prazo e fila são majoritariamente manuais;
- histórico deve permitir aprendizado futuro;
- previsão e sugestão ficam para evolução.

---

# 155. Decisões ainda pendentes

Ainda precisam ser detalhadas em documentos futuros:

- regra exata para tarefas bloqueadas na fila;
- se tarefas em execução continuam numeradas;
- critérios para exigir motivo de reordenação;
- canais de notificação;
- regras de silenciamento;
- quantidade de níveis de escalonamento;
- quem pode encerrar escalonamento;
- cálculo futuro de previsão;
- definição de impacto;
- modelo de prioridade operacional;
- comportamento de filas segmentadas;
- relação entre fila e tarefas aguardando terceiros.

---

# 156. Relação com os demais documentos

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Define:

- atividade;
- tarefa;
- setor;
- executor;
- fluxo;
- retorno.

Este documento define o que acontece quando a tarefa entra na fila do setor.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

Detalhará:

- tempo em fila;
- tempo de execução;
- histórico;
- métricas;
- indicadores.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Detalhará:

- quem pode ver;
- quem pode reordenar;
- quem pode propor;
- quem pode aceitar;
- quem pode escalar.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Detalhará:

- avisos;
- mudanças de posição;
- novo prazo;
- rejeição;
- conclusão;
- escalonamento.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Detalhará:

- previsão;
- capacidade;
- sugestão de prazo;
- risco;
- aprendizado histórico.

## `08_BANCO_DE_DADOS.md`

Traduzirá estes conceitos para:

- tabelas;
- eventos;
- relacionamentos;
- integridade;
- histórico.

---

# 157. Resumo funcional

A lógica central pode ser representada assim:

```text
TAREFA ENTRA NO SETOR
↓
ENTRA NA FILA
↓
GANHA POSIÇÃO
↓
SOLICITANTE ENXERGA 4 DE 17
↓
SETOR AVALIA PRAZO
↓
ACEITA O PRAZO SOLICITADO
OU
PROPÕE NOVO PRAZO
↓
DONO ACEITA
OU
RECUSA
↓
SE RECUSA:
ESCALONAMENTO
↓
GESTÃO DECIDE
↓
TAREFA É EXECUTADA
↓
CONCLUSÃO
↓
TODO O HISTÓRICO FICA REGISTRADO
```

---

# 158. Regra de ouro da fila

> **Quem pede precisa enxergar onde está; quem executa precisa conseguir organizar; quem gerencia precisa enxergar capacidade e conflito.**

---

# 159. Regra de ouro do prazo

> **Necessidade não é a mesma coisa que compromisso. A LPS deve preservar os dois.**

---

# 160. Regra de ouro do escalonamento

> **Conflito que não pode ser resolvido no nível atual deve subir para quem possui autoridade para decidir.**

---

# 161. Encerramento

A LPS não precisa prever tudo no início.

Ela precisa tornar o trabalho visível.

Se a empresa conseguir saber:

```text
quantas demandas existem
```

```text
qual a posição
```

```text
qual prazo foi solicitado
```

```text
qual prazo foi comprometido
```

```text
quando houve conflito
```

```text
quem decidiu
```

```text
quanto tempo a tarefa ficou esperando
```

então já existe uma base concreta para gestão.

Com histórico suficiente, essa mesma estrutura poderá evoluir de transparência para previsão, de previsão para recomendação e de recomendação para inteligência operacional.

---

# 162. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação das regras de filas, prazos, negociação e escalonamento da LPS |
