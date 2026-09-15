# 06 — Notificações e Comunicação

> Documento funcional da LPS para definir como as pessoas se comunicam dentro do contexto do trabalho, quais eventos devem gerar notificações, como evitar excesso de alertas e como transformar conversas em contexto útil sem substituir dados estruturados, auditoria ou responsabilidade.

---

# 1. Objetivo deste documento

Este documento define o comportamento de comunicação e notificações da LPS.

Ele deve responder:

- onde as conversas acontecem;
- quem pode participar;
- qual a diferença entre conversa da atividade e conversa da tarefa;
- como mensagens são registradas;
- como funciona o histórico;
- como menções funcionam;
- quais eventos geram notificações;
- quais notificações são obrigatórias;
- quais podem ser configuradas;
- como comunicar mudança de posição na fila;
- como comunicar mudança de prazo;
- como comunicar devolução;
- como comunicar atraso;
- como comunicar conclusão;
- como comunicar escalonamento;
- como evitar excesso de notificações;
- como a comunicação pode gerar inteligência futura;
- como a LPS poderá resumir uma atividade;
- por que mensagens não substituem dados estruturados;
- por que a LPS não deve nascer como um Slack corporativo genérico.

Este documento não define:

- estrutura física definitiva das tabelas;
- tecnologia de push;
- integração com e-mail, Teams, WhatsApp ou SMS;
- layout final da central de notificações;
- algoritmo de inteligência artificial;
- política jurídica completa de retenção de mensagens;
- criptografia técnica;
- regras completas de autenticação.

Esses assuntos serão detalhados em documentos técnicos ou fases posteriores.

---

# 2. Princípio central

A comunicação da LPS deve existir **dentro do contexto do trabalho**.

A estrutura central é:

```text
ATIVIDADE
↓
CONVERSA DA ATIVIDADE
```

e, quando necessário:

```text
TAREFA
↓
CONVERSA DA TAREFA
```

A LPS não precisa nascer com canais livres como:

```text
#geral
#financeiro
#comercial
#random
```

O D0 deve focar em comunicação diretamente ligada ao que está sendo executado.

---

# 3. O que a LPS não pretende ser

A LPS não deve tentar substituir um Slack, Microsoft Teams ou outro mensageiro corporativo completo.

Ela não precisa, no D0, oferecer:

- canais livres;
- grupos sociais;
- mensagens privadas genéricas;
- chamadas;
- videoconferência;
- comunidades;
- threads sem relação com trabalho;
- bots genéricos;
- mural social;
- comunicação corporativa ampla.

O objetivo é diferente.

A LPS deve responder:

> O que foi conversado sobre esta atividade ou tarefa?

e:

> Quais decisões, riscos, devoluções, prazos e impedimentos surgiram durante esse trabalho?

---

# 4. Comunicação contextual

A conversa precisa nascer sabendo o contexto.

Exemplo:

```text
Atividade:
Material disponível na obra
```

Conversa:

```text
Ryan:
Fornecedor informou prazo de 7 dias.

Paulo:
Então precisamos liberar o pedido até amanhã.

Compras:
Consigo finalizar até 15h.
```

A LPS já sabe que essas mensagens pertencem à atividade específica.

Não é necessário perguntar:

> Sobre o que vocês estão falando?

---

# 5. Conversa da atividade

Toda atividade pode possuir uma conversa principal.

Ela serve para assuntos relacionados ao resultado da atividade como um todo.

Exemplos:

- alinhamento geral;
- dúvida transversal;
- decisão que afeta várias tarefas;
- atualização do dono;
- mudança de contexto;
- risco;
- impedimento geral;
- orientação;
- solicitação de posicionamento.

---

# 6. Exemplo de conversa da atividade

```text
Atividade:
Entregar orçamento ao cliente
```

Mensagem:

```text
Paulo:
O cliente antecipou a reunião para amanhã às 14h.
Precisamos revisar o prazo final.
```

Essa informação impacta a atividade inteira.

Por isso, deve ficar na conversa da atividade.

---

# 7. Conversa da tarefa

Cada tarefa pode possuir sua própria conversa.

Ela serve para assuntos específicos daquela execução.

Exemplo:

```text
Tarefa:
Cotação de cabos
```

Mensagem:

```text
Jennifer:
O fornecedor pediu confirmação da especificação do cabo.
```

Essa informação não precisa necessariamente poluir toda a conversa geral da atividade.

---

# 8. Quando usar conversa da atividade

Preferir atividade quando o assunto:

- afeta o resultado final;
- envolve vários setores;
- altera contexto geral;
- exige ciência do dono;
- envolve decisão transversal;
- não pertence claramente a uma única tarefa.

---

# 9. Quando usar conversa da tarefa

Preferir tarefa quando o assunto:

- é operacional;
- pertence àquela execução;
- envolve executores daquela tarefa;
- trata de informação técnica específica;
- trata de devolução;
- trata de dúvida localizada;
- não precisa envolver todos os participantes da atividade.

---

# 10. Uma mensagem deve pertencer a um contexto claro

No D0, toda mensagem operacional deve estar vinculada a:

```text
atividade
```

ou:

```text
tarefa
```

Evitar mensagem sem contexto.

---

# 11. Conversa não cria nova atividade automaticamente

Decisão consolidada:

> Uma mensagem não deve virar atividade ou tarefa diretamente.

Se uma nova necessidade surgir durante a conversa:

```text
usuário
↓
vai ao cadastro de atividade
↓
cria a atividade de forma simples
```

Isso preserva clareza.

---

# 12. Por que não criar atividade diretamente de uma mensagem no D0

Embora pareça prático, aumenta complexidade:

- qual seria o dono?
- qual setor?
- qual prazo?
- qual empresa?
- qual fluxo?
- qual relação com a mensagem original?
- quem teria acesso?

No D0, é melhor manter o cadastro simples e explícito.

---

# 13. Mensagem não substitui ação estruturada

Esse é um princípio obrigatório.

Exemplo:

Mensagem:

> “Pode deixar para sexta-feira.”

Isso não significa que o prazo oficial mudou.

A alteração precisa ocorrer por ação estruturada:

```text
Propor novo prazo
```

ou:

```text
Aceitar novo prazo
```

---

# 14. Outro exemplo

Mensagem:

> “Estou devolvendo porque faltou a bitola do cabo.”

A tarefa só deve ser formalmente devolvida quando alguém executar:

```text
Devolver tarefa
```

e registrar:

```text
Motivo:
Especificação incompleta
```

---

# 15. Conversa é contexto

Dados estruturados são estado oficial.

A distinção é:

```text
CONVERSA
=
contexto humano
```

```text
DADO ESTRUTURADO
=
estado oficial do processo
```

---

# 16. Por que essa separação importa

Sem essa separação, a LPS dependeria de interpretar linguagem natural para descobrir:

- se o prazo mudou;
- se uma tarefa foi concluída;
- se houve devolução;
- se alguém assumiu;
- se uma decisão foi aprovada.

Isso geraria ambiguidade.

---

# 17. Mensagem pode gerar sugestão futura

Futuramente, a inteligência da LPS poderá analisar:

> “Consigo entregar terça às 15h.”

e sugerir:

```text
Possível novo prazo comprometido detectado.

Deseja registrar?
[Sim]
[Não]
```

Mas a alteração só acontece após confirmação.

---

# 18. Fato x inferência

A LPS deve diferenciar claramente:

```text
Fato:
Prazo comprometido foi alterado para 15/09 às 15h.
```

de:

```text
Inferência:
A mensagem parece indicar uma possível mudança de prazo.
```

---

# 19. Participantes

A conversa não precisa ser aberta para toda a organização.

Os participantes devem ser definidos pelo contexto e pelas autorizações.

Possíveis participantes:

- dono da atividade;
- executores;
- membros autorizados dos setores envolvidos;
- gestores;
- pessoas mencionadas;
- pessoas com permissão de visualização;
- responsáveis por aprovação;
- pessoas incluídas explicitamente quando permitido.

---

# 20. Participante não é necessariamente executor

Exemplo:

```text
Diretor
```

pode participar de uma conversa sem executar a tarefa.

---

# 21. Executor não significa acesso ilimitado

O executor acessa a conversa necessária para sua tarefa.

Não ganha automaticamente acesso a todas as conversas da organização.

---

# 22. Dono da atividade precisa de contexto suficiente

Como o dono responde pelo acompanhamento do resultado, ele precisa visualizar o contexto necessário da atividade.

Isso inclui informações relevantes das tarefas que compõem sua atividade, respeitando regras de segurança.

---

# 23. Gestor do setor

O gestor pode ter acesso às conversas de tarefas de seu setor conforme autorização.

Isso permite:

- acompanhar conflitos;
- entender devoluções;
- analisar impedimentos;
- atuar em escalonamentos.

---

# 24. Acesso à conversa segue autorização

Princípio:

> Se o usuário não pode acessar a atividade ou tarefa, normalmente também não deve acessar sua conversa.

A comunicação não deve criar uma porta paralela para informação restrita.

---

# 25. Participação explícita

Pode existir ação para adicionar participante à conversa.

Exemplo:

```text
Adicionar Juliana à conversa
```

A ação deve respeitar autorização.

---

# 26. Remoção de participante

Se permitido, pode retirar acesso futuro à conversa.

Mas mensagens históricas permanecem associadas ao autor original.

---

# 27. Histórico de participantes

Pode ser relevante registrar:

```text
Paulo adicionou Juliana em 14/09 às 10h30.
```

e:

```text
Juliana deixou de participar em 15/09 às 08h.
```

---

# 28. Menções

A LPS pode utilizar menções:

```text
@Ryan
```

```text
@Paulo
```

```text
@Igor
```

para chamar atenção de pessoas específicas.

---

# 29. Menção não concede autorização

Se uma pessoa não possui acesso à atividade, simplesmente mencioná-la não deve necessariamente liberar o conteúdo.

A autorização precisa ser validada.

---

# 30. Menção pode sugerir inclusão

Se a pessoa mencionada não é participante, a LPS pode futuramente alertar:

```text
Ryan ainda não participa desta atividade.
Deseja adicioná-lo?
```

Mas isso não é obrigatório no D0.

---

# 31. Menção deve gerar notificação

Quando válida, uma menção deve gerar evento notificável.

Exemplo:

```text
Paulo mencionou você na tarefa:
"Cotação de cabos"
```

---

# 32. Menções de setor

No D0, evitar:

```text
@Financeiro
```

mencionando dezenas de pessoas.

Pode gerar excesso de notificações.

Começar com menções individuais.

---

# 33. Histórico da conversa

Mensagens devem possuir:

- autor;
- data;
- hora;
- contexto;
- conteúdo;
- atividade ou tarefa;
- eventual edição;
- eventual exclusão controlada;
- anexos quando houver.

---

# 34. Mensagens em ordem cronológica

A conversa deve ser facilmente reconstruída.

Exemplo:

```text
09:20 Ryan
10:15 Jennifer
10:40 Paulo
11:05 Compras
```

---

# 35. Mensagem editada

Se edição for permitida:

```text
editada
```

deve ficar indicado.

Em contextos mais sensíveis, pode ser necessário preservar versão anterior.

A profundidade será definida posteriormente.

---

# 36. Exclusão de mensagem

No D0, evitar exclusão irrestrita de mensagens operacionais.

Preferir:

- exclusão controlada;
- marcação de removida;
- auditoria.

---

# 37. Por que preservar histórico

A conversa pode explicar:

- decisões;
- contexto;
- dúvidas;
- riscos;
- motivos;
- mudanças de entendimento.

Apagar livremente destrói memória operacional.

---

# 38. Auditoria da conversa

Eventos relevantes podem registrar:

```text
mensagem criada
```

```text
mensagem editada
```

```text
mensagem removida
```

```text
participante adicionado
```

```text
menção realizada
```

---

# 39. Conversa e timeline

A timeline da atividade e a conversa são diferentes.

Timeline:

```text
evento operacional estruturado
```

Conversa:

```text
contexto textual
```

---

# 40. Exemplo

Timeline:

```text
10:30 — tarefa devolvida para Engenharia
```

Conversa:

```text
10:31 — Compras:
Faltou especificar a bitola do cabo.
```

As duas informações se complementam.

---

# 41. Não duplicar tudo na timeline

Não é necessário transformar cada mensagem em evento principal da atividade.

A timeline pode mostrar apenas eventos relevantes.

---

# 42. Notificação

Notificação é um aviso gerado por um evento que precisa chamar a atenção de alguém.

Exemplos:

- menção;
- tarefa atribuída;
- posição alterada;
- prazo proposto;
- prazo alterado;
- devolução;
- atraso;
- escalonamento;
- conclusão.

---

# 43. Evento x notificação

Nem todo evento precisa gerar notificação para todos.

Exemplo:

```text
atividade visualizada
```

pode ser auditada.

Não precisa notificar ninguém.

---

# 44. Notificação x canal

Notificação é o evento lógico.

Canal é como ela chega.

Exemplos futuros:

```text
Central da LPS
Push
E-mail
```

Talvez integrações externas depois.

---

# 45. Central de notificações

O D0 deve possuir, conceitualmente, uma central interna de notificações.

Ela pode mostrar:

- novas;
- lidas;
- tipo;
- atividade;
- tarefa;
- data;
- ação necessária.

---

# 46. Notificação acionável

Quando possível, a notificação deve levar diretamente ao contexto.

Exemplo:

```text
Novo prazo proposto.
```

Ações:

```text
[Ver atividade]
[Analisar proposta]
```

---

# 47. Notificações configuráveis

Decisão consolidada:

> O usuário e/ou a organização devem poder configurar quais eventos geram notificações.

Mas algumas notificações podem ser obrigatórias.

---

# 48. Configuração pessoal

Exemplos:

```text
Quero ser avisado quando:
[x] minha posição mudar
[x] eu for mencionado
[x] uma tarefa minha for devolvida
[ ] qualquer mensagem nova
```

---

# 49. Configuração corporativa

A organização pode definir regras obrigatórias.

Exemplo:

```text
Dono da atividade sempre recebe conclusão.
```

O usuário não pode desativar esse evento.

---

# 50. Notificação obrigatória x opcional

A LPS precisa separar:

```text
Obrigatória
```

de:

```text
Configurável
```

---

# 51. Conclusão da atividade

Decisão consolidada:

> O dono da atividade deve sempre ser notificado quando a atividade for concluída.

Outros participantes podem receber conforme configuração.

---

# 52. Conclusão da tarefa

Pode ser configurável.

Exemplo:

O dono pode querer ser avisado apenas quando:

- tarefa crítica concluir;
- tarefa final concluir;
- tarefa específica concluir.

Não necessariamente todas.

---

# 53. Tarefa atribuída

Normalmente deve notificar o executor.

Exemplo:

```text
Uma nova tarefa foi atribuída a você.
```

---

# 54. Inclusão como executor

Também deve gerar aviso.

---

# 55. Remoção como executor

Pode gerar aviso para evitar surpresa.

---

# 56. Mudança de posição

Decisão consolidada:

> Toda mudança de posição deve ser registrada e pode gerar notificação.

O usuário escolheu transparência máxima nesse ponto.

---

# 57. Exemplo de mudança

```text
Sua posição mudou:
4 de 17 → 5 de 17
```

---

# 58. Outro exemplo

```text
Sua posição mudou:
5 de 17 → 16 de 18
```

---

# 59. Toda mudança deve existir como evento

Mesmo que algum canal seja silenciado, o evento continua registrado.

---

# 60. Evitar confundir “gerar evento” com “enviar push”

Pode existir:

```text
evento de posição
```

sem obrigatoriamente:

```text
push no celular
```

em toda alteração.

A central interna pode receber todas.

Canais externos podem ser configurados.

---

# 61. Mudança de total da fila

Exemplo:

```text
4 de 17 → 4 de 24
```

A posição não mudou, mas o contexto mudou.

Pode ser registrado.

A necessidade de notificar sempre pode ser configurável.

---

# 62. Mudança causada por conclusão

Exemplo:

```text
4 de 17 → 3 de 16
```

porque uma demanda anterior foi concluída.

O sistema pode informar:

```text
Sua posição avançou.
```

---

# 63. Mudança causada por reordenação

Exemplo:

```text
4 de 17 → 10 de 17
```

Pode mostrar:

```text
Sua posição foi alterada pela gestão da fila.
```

Sem expor o conteúdo das outras demandas.

---

# 64. Mudança causada por nova prioridade

Se uma nova tarefa entrou na frente:

```text
Sua posição mudou devido à reordenação da fila.
```

Não precisa revelar o que entrou.

---

# 65. Mudança de prazo

Quando prazo comprometido muda:

```text
Prazo anterior:
Hoje às 17h

Novo prazo:
Amanhã às 10h
```

o dono precisa ser informado.

---

# 66. Novo prazo proposto

Antes de aceitar:

```text
Novo prazo proposto:
15/09 às 15h
```

A notificação deve permitir análise.

---

# 67. Aceite de prazo

Quem propôs deve ser informado do aceite.

Exemplo:

```text
Novo prazo aceito.
```

---

# 68. Recusa de prazo

Quem propôs e os responsáveis do escalonamento devem ser informados.

---

# 69. Mudança unilateral autorizada

Se alguma configuração permitir alteração direta de prazo:

- dono precisa ser avisado;
- histórico precisa ser preservado;
- motivo pode ser obrigatório.

---

# 70. Devolução

Toda devolução é evento relevante.

Ela deve notificar pelo menos as pessoas responsáveis por agir após a devolução.

---

# 71. Exemplo de devolução

```text
Tarefa devolvida:
Cotação de cabos

De:
Compras

Para:
Engenharia

Motivo:
Especificação incompleta
```

---

# 72. Dono da atividade e devolução

Dependendo da configuração, o dono pode receber toda devolução.

Isso pode ser importante para acompanhar retrabalho.

---

# 73. Gestor do setor e devolução

A empresa pode configurar:

```text
Gestor recebe devoluções de tarefas críticas
```

ou:

```text
Gestor recebe todas as devoluções
```

---

# 74. Devolução recorrente

Futuramente, a LPS pode alertar:

```text
Esta é a terceira devolução desta tarefa.
```

Isso pode justificar escalonamento.

---

# 75. Atraso

Atraso ocorre quando um prazo aplicável é ultrapassado.

A LPS precisa saber qual prazo está sendo usado.

Exemplo:

```text
Prazo comprometido:
14/09 às 17h

Agora:
14/09 às 17h01

Tarefa ainda aberta:
Atrasada
```

---

# 76. Notificação de atraso

Pode ser direcionada para:

- executor;
- dono;
- gestor;
- cadeia de escalonamento.

Conforme configuração.

---

# 77. Aviso antes do atraso

Futuramente, pode existir:

```text
80% do prazo consumido
```

ou:

```text
faltam 2h
```

No D0, isso pode ser simples ou ficar para evolução.

---

# 78. Atraso não deve gerar spam repetitivo

Evitar:

```text
17:01 atraso
17:02 atraso
17:03 atraso
```

Um evento de atraso pode ser criado e escalonado conforme regra.

---

# 79. Escalonamento

Quando um conflito sobe de nível, os destinatários precisam ser notificados.

Exemplo:

```text
Novo prazo proposto foi recusado.
Escalonamento criado.
```

---

# 80. Notificação de escalonamento precisa ter contexto

Mostrar:

- atividade;
- tarefa;
- motivo;
- prazo solicitado;
- prazo proposto;
- setor;
- pessoas envolvidas;
- ação esperada.

---

# 81. Exemplo

```text
Escalonamento:
Conflito de prazo

Solicitado:
Hoje às 17h

Proposto:
Amanhã às 10h

Dono:
Paulo

Setor:
Comercial
```

---

# 82. Escalonamento resolvido

Os envolvidos devem receber:

```text
Escalonamento resolvido.
```

com a decisão.

---

# 83. Decisão de escalonamento

Exemplo:

```text
Decisão:
Manter novo prazo para amanhã às 10h.
```

Esse dado precisa estar estruturado, não apenas em mensagem.

---

# 84. Conclusão

Conclusão é um evento central.

Exemplo:

```text
Atividade concluída:
Material disponível na obra.
```

Dono:

```text
notificação obrigatória.
```

---

# 85. Conclusão da atividade pode exigir confirmação

Se o processo exigir validação do dono:

```text
Todas as tarefas foram concluídas.
Aguardando confirmação do resultado.
```

A notificação deve pedir ação.

---

# 86. Reabertura

Se uma atividade for reaberta:

- dono é notificado;
- executores relevantes podem ser notificados;
- histórico permanece.

---

# 87. Cancelamento

Quando atividade ou tarefa é cancelada:

- dono deve saber;
- pessoas atribuídas devem saber;
- motivo deve ser visível conforme autorização.

---

# 88. Bloqueio

Ao marcar tarefa como bloqueada, pode ser necessário notificar:

- dono;
- gestor;
- executor;
- pessoas dependentes.

Conforme configuração.

---

# 89. Desbloqueio

Também pode gerar aviso para quem aguardava.

---

# 90. Menção

Quando alguém é mencionado:

```text
@Ryan
```

a notificação deve ter alta clareza.

Exemplo:

```text
Paulo mencionou você na tarefa "Revisar escopo".
```

---

# 91. Nova mensagem sem menção

Não deve obrigatoriamente gerar notificação para todos.

Pode ser configurável.

Caso contrário, a LPS vira um sistema ruidoso.

---

# 92. Seguir atividade

Futuramente, pode existir ação:

```text
Seguir atividade
```

para receber determinadas atualizações sem ser executor.

Não é obrigatório no D0.

---

# 93. Assinatura automática

Dono e executores podem ser automaticamente inscritos em eventos essenciais do seu contexto.

---

# 94. Sair de notificações opcionais

Usuário pode desativar notificações não obrigatórias.

---

# 95. Eventos obrigatórios

Exemplos candidatos:

- conclusão para dono;
- atribuição para executor;
- devolução para responsável que precisa agir;
- escalonamento para destinatário;
- prazo que exige aceite;
- menção.

---

# 96. Eventos configuráveis

Exemplos:

- qualquer mensagem nova;
- cada mudança de posição;
- conclusão de tarefa intermediária;
- mudança de participante;
- alterações menores.

---

# 97. Configuração por tipo de atividade

Futuramente, a empresa pode dizer:

```text
Em atividades de compra:
gestor quer receber devoluções.
```

Não é prioridade do D0.

---

# 98. Configuração por atividade específica

Usuário pode querer acompanhar uma atividade importante.

Exemplo:

```text
Notificar-me sobre todas as mudanças desta atividade.
```

---

# 99. Configuração por tarefa específica

Também pode existir:

```text
Notificar-me sobre esta tarefa.
```

---

# 100. Configuração por setor

Gestor:

```text
Quero receber atrasos do meu setor.
```

---

# 101. Configuração por criticidade ou impacto

Futuramente:

```text
Notificar somente tarefas bloqueadoras.
```

---

# 102. Configuração por papel

Dono:

```text
sempre recebe conclusão.
```

Executor:

```text
recebe atribuição.
```

Gestor:

```text
recebe escalonamento.
```

---

# 103. Notificação em massa

Evitar enviar o mesmo evento para dezenas de pessoas sem necessidade.

---

# 104. Preferência por relevância

A LPS deve buscar:

```text
menos notificações
+
mais significado
```

sem perder transparência.

---

# 105. Transparência não depende apenas de notificação

Mesmo que usuário ignore avisos, ele pode abrir a atividade e enxergar:

- posição;
- prazo;
- histórico;
- status.

---

# 106. Central de notificações como histórico

A central pode funcionar como caixa de entrada operacional.

Exemplo:

```text
[Não lida] Novo prazo proposto
[Não lida] Você foi mencionado
[Lida] Posição alterada
[Lida] Tarefa concluída
```

---

# 107. Estado da notificação

Pode possuir:

```text
não lida
```

```text
lida
```

```text
arquivada
```

A necessidade final será definida na UX.

---

# 108. Notificação com ação pendente

Diferenciar:

```text
informativa
```

de:

```text
requer ação
```

---

# 109. Exemplo informativo

```text
Sua posição mudou para 3 de 14.
```

---

# 110. Exemplo que requer ação

```text
Novo prazo proposto.
Aceitar ou recusar.
```

---

# 111. Caixa de pendências

Futuramente, notificações que exigem ação podem alimentar uma área:

```text
Pendentes
```

Não confundir com tarefas de trabalho.

---

# 112. Notificação não substitui tarefa

Receber:

```text
Revisar novo prazo
```

é uma pendência decisória.

Não significa criar automaticamente uma tarefa operacional nova.

---

# 113. Agrupamento de notificações

Futuramente, alterações repetidas podem ser agrupadas.

Exemplo:

```text
Sua posição mudou 5 vezes hoje.
Ver histórico.
```

Mas a decisão inicial foi registrar todas as mudanças.

---

# 114. Agrupamento preserva histórico

Mesmo que a interface agrupe, os eventos individuais continuam registrados.

---

# 115. Canais

No D0, o canal obrigatório é:

```text
LPS
```

Outros canais podem vir depois.

---

# 116. Push

Pode ser interessante no mobile para:

- menção;
- prazo;
- devolução;
- escalonamento;
- conclusão.

A implementação pertence à fase de interface/infraestrutura.

---

# 117. E-mail

Pode ser usado para eventos importantes.

Mas a LPS não deve depender exclusivamente de e-mail.

---

# 118. Teams, Slack ou outros mensageiros

Podem existir integrações futuras.

Isso não transforma a LPS em um mensageiro genérico.

---

# 119. WhatsApp

Integração futura exige cuidado com:

- segurança;
- privacidade;
- custo;
- volume;
- rastreabilidade.

Não pertence ao D0.

---

# 120. Preferência por central própria

A LPS precisa preservar sua própria central de notificações porque ela é a fonte de verdade do trabalho.

---

# 121. Falha de entrega externa

Se um e-mail falhar, a notificação continua existindo dentro da LPS.

---

# 122. Leitura

Futuramente, pode existir:

```text
lida em 14/09 às 10:22
```

---

# 123. Confirmação de ciência

Em alguns eventos, “lida” pode não ser suficiente.

Pode existir:

```text
Confirmar ciência
```

---

# 124. Ciência x aprovação

São diferentes.

```text
Ciência:
Eu vi.
```

```text
Aprovação:
Eu concordo.
```

---

# 125. Gestor ciente

A empresa pode configurar:

```text
Tarefa de alto impacto
→ gestor deve confirmar ciência.
```

---

# 126. Não obrigar ciência em tudo

Isso criaria burocracia.

Usar apenas onde a empresa decidir que é necessário.

---

# 127. Histórico de notificações

Pode ser importante registrar:

- gerada;
- destinatário;
- data;
- canal;
- lida;
- ação executada.

---

# 128. Auditoria de notificação

Exemplo:

```text
Escalonamento criado às 10:00.
Notificação entregue ao gestor às 10:00.
Decisão registrada às 10:45.
```

Isso permite medir tempo de resposta gerencial.

---

# 129. Notificação silenciosa

Alguns eventos podem aparecer apenas na central sem interrupção.

Exemplo:

```text
posição melhorou de 5 para 4
```

---

# 130. Notificação destacada

Exemplo:

```text
prazo recusado
```

pode merecer destaque.

---

# 131. Prioridade da notificação

Futuramente:

```text
informativa
atenção
ação necessária
crítica
```

Não confundir com prioridade da tarefa.

---

# 132. Prioridade da notificação não muda prioridade operacional

São conceitos distintos.

---

# 133. Conversa e privacidade

Mensagens podem conter informações sensíveis.

O acesso precisa seguir a atividade/tarefa.

---

# 134. Pesquisa em mensagens

Futuramente, usuário autorizado pode pesquisar conteúdo.

Não é prioridade do D0.

---

# 135. Busca por atividade

Mais importante no início é conseguir abrir a atividade e consultar sua conversa completa.

---

# 136. Anexos

Conversas podem possuir anexos.

Exemplos:

- imagem;
- documento;
- evidência;
- arquivo técnico.

A regra de arquivos será detalhada em outro documento, se necessário.

---

# 137. Anexo não deve existir sem contexto

Preferir que o arquivo esteja ligado à:

- atividade;
- tarefa;
- mensagem.

---

# 138. Histórico do anexo

Registrar:

- quem enviou;
- quando;
- em qual mensagem;
- em qual contexto.

---

# 139. Anexo removido

Se permitido, auditoria deve preservar que existiu.

---

# 140. Reações

Recursos como:

```text
👍
✅
```

podem ser úteis futuramente.

Mas não devem substituir:

- aprovação;
- conclusão;
- ciência formal.

---

# 141. Exemplo

Um:

```text
👍
```

não significa:

```text
Prazo aceito.
```

A ação estruturada continua necessária.

---

# 142. Threads

Como cada tarefa já possui contexto próprio, threads internas podem não ser necessárias no D0.

Evitar complexidade antes de validar necessidade.

---

# 143. Respostas a mensagem

Pode existir resposta simples para manter contexto.

Exemplo:

```text
Responder à mensagem de Ryan
```

Não é obrigatório para a primeira versão.

---

# 144. Mensagens automáticas do sistema

A conversa pode mostrar eventos automáticos relevantes.

Exemplo:

```text
Sistema:
Prazo comprometido alterado de 14/09 para 15/09.
```

---

# 145. Sistema não deve poluir a conversa

Nem todo evento de auditoria precisa aparecer como mensagem.

Mostrar apenas os que ajudam entendimento.

---

# 146. Eventos automáticos úteis na conversa

Exemplos:

- tarefa devolvida;
- prazo alterado;
- novo executor;
- tarefa concluída;
- escalonamento criado.

---

# 147. Timeline continua sendo fonte completa

A conversa pode ter uma visão resumida.

A timeline possui auditoria detalhada.

---

# 148. Resumo da atividade

Decisão consolidada:

> Futuramente a LPS deve conseguir gerar resumo automático da atividade.

---

# 149. Objetivo do resumo

Permitir que alguém entre numa atividade antiga ou complexa e entenda rapidamente:

- o que aconteceu;
- decisões;
- prazos;
- devoluções;
- riscos;
- pendências;
- resultado.

---

# 150. Exemplo de resumo

```text
A atividade foi criada em 10/09 para disponibilizar material na obra.

Compras recebeu a demanda em 11/09 e devolveu uma vez para Engenharia por especificação incompleta.

O prazo inicial era 15/09. Foi renegociado para 17/09 e aceito pelo dono.

O fornecedor informou prazo de 7 dias.

A atividade foi concluída em 17/09 às 14h.
```

---

# 151. Resumo precisa combinar duas fontes

A LPS poderá utilizar:

```text
dados estruturados
+
conversa
```

---

# 152. Dados estruturados têm prioridade

Exemplo:

Se a conversa diz:

> “Acho que termina terça.”

mas o prazo oficial é:

```text
quarta-feira
```

o resumo deve tratar terça como comentário, não como fato oficial.

---

# 153. Resumo deve distinguir fato de interpretação

Exemplo:

```text
Fato:
Tarefa foi devolvida duas vezes.

Possível interpretação:
As devoluções estão relacionadas a informações técnicas incompletas.
```

---

# 154. Resumo não deve inventar

Se não existe informação sobre o motivo:

```text
Motivo não registrado.
```

Não inferir como certeza.

---

# 155. Resumo atualizável

Enquanto a atividade está aberta, o resumo pode mudar com novos eventos.

---

# 156. Resumo final

Quando concluída, pode existir resumo de encerramento.

Exemplo:

- objetivo;
- resultado;
- prazo;
- duração;
- principais eventos;
- devoluções;
- decisão final;
- lições identificadas.

---

# 157. Resumo para gestor

Pode destacar:

- atraso;
- gargalo;
- retorno;
- escalonamento;
- impacto.

---

# 158. Resumo para executor

Pode ser mais operacional:

- o que falta;
- última decisão;
- prazo atual;
- próxima ação.

---

# 159. Resumo conforme permissão

O conteúdo do resumo precisa respeitar o que o usuário pode acessar.

A IA não pode resumir informação que o usuário não teria direito de ver.

---

# 160. Comunicação como fonte de inteligência

Mensagens podem conter sinais importantes:

- fornecedor;
- risco;
- decisão;
- dúvida;
- prazo;
- impedimento;
- mudança de cenário.

---

# 161. Inteligência futura

A LPS poderá detectar candidatos a:

```text
prazo
```

```text
risco
```

```text
impedimento
```

```text
decisão
```

```text
compromisso
```

```text
devolução
```

---

# 162. Exemplo — risco

Mensagem:

> “Se esse material não chegar até quarta, a equipe para.”

A LPS pode sugerir:

```text
Possível impacto relevante detectado.
Deseja registrar?
```

---

# 163. Exemplo — impedimento

Mensagem:

> “Não consigo avançar sem o projeto revisado.”

Sugestão:

```text
Possível bloqueio detectado.
Deseja registrar a tarefa como bloqueada?
```

---

# 164. Exemplo — decisão

Mensagem:

> “Vamos manter o fornecedor atual.”

Pode sugerir:

```text
Possível decisão registrada na conversa.
```

Mas não precisa virar campo formal se o processo não exigir.

---

# 165. Exemplo — prazo

Mensagem:

> “Fornecedor entrega em 7 dias.”

Pode sugerir registrar:

```text
prazo externo
```

quando existir estrutura para isso.

---

# 166. IA não pode alterar processo silenciosamente

Qualquer transformação de mensagem em dado operacional precisa de:

- regra;
- confirmação;
- auditoria.

---

# 167. Retroalimentação da comunicação

Ao longo do tempo, a LPS pode aprender:

- quais mensagens aparecem antes de atraso;
- quais palavras ou contextos indicam bloqueio;
- quais motivos se repetem;
- quais decisões geram melhor fluxo.

Isso pertence ao documento 07.

---

# 168. Conversa não deve ser usada como única base de métrica

Métricas devem priorizar eventos estruturados.

Texto pode enriquecer análise.

---

# 169. Linguagem natural é ambígua

Exemplo:

> “Pode deixar.”

Pode significar:

- concordância;
- encerramento;
- desistência;
- simples confirmação.

Por isso, não usar como mudança automática de status.

---

# 170. Notificação de mensagem

No D0, não é necessário notificar todos a cada nova mensagem.

Preferir:

- menção;
- participante diretamente envolvido;
- regra configurada.

---

# 171. Indicador de mensagens não lidas

Pode existir:

```text
3 mensagens novas
```

na atividade.

---

# 172. Leitura por contexto

Ao abrir atividade:

```text
última mensagem lida
↓
novas mensagens
```

Facilita retomada.

---

# 173. Conversa em atividade longa

Quanto maior a duração, mais importante:

- busca;
- resumo;
- marcadores futuros.

No D0, histórico cronológico é suficiente.

---

# 174. Fixar mensagem

Futuramente, pode existir:

```text
Fixar decisão importante
```

Não é obrigatório no D0.

---

# 175. Decisão formal deve continuar estruturada

Mesmo se mensagem for fixada.

---

# 176. Comentário de devolução

Ao devolver, o sistema pode criar automaticamente mensagem:

```text
Tarefa devolvida por Ryan.
Motivo: especificação incompleta.
```

---

# 177. Comentário de prazo

Ao aceitar prazo:

```text
Sistema:
Novo prazo comprometido: 15/09 às 15h.
```

---

# 178. Comentário de conclusão

```text
Sistema:
Tarefa concluída por Jennifer às 16h20.
```

---

# 179. Benefício

A conversa fica compreensível mesmo sem abrir timeline a todo momento.

---

# 180. Não duplicar informação desnecessária

A mensagem automática pode ser concisa.

Detalhes completos ficam na auditoria.

---

# 181. Configuração de notificação por atividade

Exemplo:

```text
Atividade importante

Notificar-me sobre:
[x] todas as mensagens
[x] posição
[x] prazo
[x] devoluções
[x] conclusão
```

---

# 182. Configuração por usuário

Preferências pessoais podem ser padrão.

Exemplo:

```text
Sempre notificar:
menções
tarefas atribuídas
```

---

# 183. Configuração por organização

Pode impor eventos obrigatórios.

---

# 184. Configuração por gestor

Gestor pode acompanhar:

```text
atrasos do setor
```

sem receber:

```text
todas as mensagens do setor
```

---

# 185. Notificação de fila para solicitante

O solicitante precisa poder acompanhar mudança de posição sem entrar toda hora.

Esse foi um requisito explícito de produto.

---

# 186. Informação mínima da notificação de fila

```text
Atividade
Setor
Posição anterior
Nova posição
Data/hora
```

---

# 187. Informação que não precisa aparecer

- título das demandas que passaram na frente;
- cliente das outras demandas;
- detalhes internos do setor.

---

# 188. Notificação de prazo

Informação mínima:

```text
prazo anterior
novo prazo/proposta
quem propôs
ação necessária
```

---

# 189. Notificação de devolução

Informação mínima:

```text
tarefa
origem
destino
motivo
```

---

# 190. Notificação de atraso

Informação mínima:

```text
tarefa
prazo
tempo em atraso
responsável
```

---

# 191. Notificação de conclusão

Informação mínima:

```text
atividade/tarefa
quem concluiu
quando
```

---

# 192. Notificação de escalonamento

Informação mínima:

```text
motivo
envolvidos
prazo
decisão pendente
```

---

# 193. Notificação de menção

Informação mínima:

```text
autor
trecho da mensagem
atividade/tarefa
```

---

# 194. Notificação de atribuição

Informação mínima:

```text
tarefa
atividade
prazo
setor
quem atribuiu
```

---

# 195. Notificação deve abrir no ponto certo

Ao clicar em:

```text
Novo prazo proposto
```

abrir:

```text
seção de prazo da atividade/tarefa
```

não apenas a home.

---

# 196. Deep link

Tecnicamente, isso pode ser implementado como link direto para o contexto.

Detalhamento no documento de UX.

---

# 197. Evitar notificação sem ação clara

Exemplo ruim:

```text
Houve uma atualização.
```

Exemplo bom:

```text
Sua tarefa foi devolvida para Engenharia por especificação incompleta.
```

---

# 198. Clareza

A notificação deve responder:

- o que aconteceu;
- onde;
- se preciso agir.

---

# 199. Notificação não deve exigir interpretação excessiva

O usuário precisa entender em segundos.

---

# 200. Histórico de notificação não substitui histórico da atividade

Mesmo se notificação for apagada ou arquivada, o evento continua na atividade.

---

# 201. Preferências não apagam eventos

Silenciar uma notificação:

```text
não receber push
```

não significa:

```text
não registrar mudança
```

---

# 202. Silenciar conversa

Futuramente, usuário pode silenciar mensagens de atividade.

Eventos obrigatórios continuam chegando.

---

# 203. Silenciar não deve impedir menções obrigatórias

Pode haver exceções.

A política será definida na UX.

---

# 204. Horário de silêncio

Futuramente:

```text
não enviar push após 20h
```

salvo críticos.

Não é necessário no D0.

---

# 205. Resumo diário

Futuramente, o usuário pode receber:

```text
Resumo das mudanças das suas atividades
```

Isso pode reduzir ruído.

Não é prioridade do D0.

---

# 206. Digest para gestor

Exemplo:

```text
Hoje:
3 atrasos
2 devoluções
1 escalonamento
7 tarefas concluídas
```

Evolução posterior.

---

# 207. Notificações críticas

A LPS pode futuramente permitir regras que ignoram horário de silêncio.

Exemplo:

```text
atividade bloqueadora
```

Não implementar sem necessidade.

---

# 208. Eventos do sistema

Lista inicial de eventos notificáveis:

```text
atividade_criada
atividade_atribuida
atividade_concluida
atividade_reaberta
atividade_cancelada

tarefa_criada
tarefa_atribuida
tarefa_assumida
tarefa_devolvida
tarefa_concluida
tarefa_bloqueada
tarefa_desbloqueada

fila_posicao_alterada

prazo_proposto
prazo_aceito
prazo_recusado
prazo_alterado
prazo_atrasado

escalonamento_criado
escalonamento_resolvido

usuario_mencionado

mensagem_nova
```

---

# 209. Nem todos precisam estar ativos no D0

O catálogo pode crescer conforme o produto.

---

# 210. Eventos obrigatórios iniciais sugeridos

Para D0:

```text
tarefa_atribuida
tarefa_devolvida
fila_posicao_alterada
prazo_proposto
prazo_aceito
prazo_recusado
prazo_atrasado
escalonamento_criado
atividade_concluida
usuario_mencionado
```

---

# 211. Evento de conclusão

Obrigatório para dono da atividade.

---

# 212. Evento de atribuição

Obrigatório para executor que recebe a tarefa.

---

# 213. Evento de devolução

Obrigatório para quem precisa agir após o retorno.

---

# 214. Evento de prazo proposto

Obrigatório para quem precisa aceitar ou recusar.

---

# 215. Evento de escalonamento

Obrigatório para quem precisa decidir.

---

# 216. Evento de menção

Obrigatório para mencionado quando possui acesso.

---

# 217. Evento de posição

A decisão funcional é registrar cada mudança.

A estratégia de canal pode ser configurada.

---

# 218. D0 — Conversa mínima

A primeira versão precisa permitir:

- conversar na atividade;
- conversar na tarefa;
- identificar autor;
- registrar data/hora;
- visualizar histórico;
- mencionar usuário;
- respeitar acesso;
- preservar mensagens.

---

# 219. D0 — Notificação mínima

A primeira versão precisa permitir:

- central interna;
- não lida/lida;
- vínculo com atividade/tarefa;
- eventos obrigatórios;
- posição;
- prazo;
- devolução;
- atraso;
- conclusão;
- escalonamento;
- menção.

---

# 220. D0 — Configuração mínima

Precisa permitir algum nível de configuração:

- usuário;
- organização;
- eventos opcionais.

Sem criar um motor excessivamente complexo.

---

# 221. O que pode ficar depois do D0

Pode ficar para evolução:

- canais livres;
- chat privado genérico;
- integração com Slack/Teams;
- integração com WhatsApp;
- reação;
- thread avançada;
- resumo diário;
- digest;
- push avançado;
- horário de silêncio;
- agrupamento inteligente;
- classificação de mensagem por IA;
- resumo automático por IA;
- tradução automática;
- transcrição de áudio;
- análise de sentimento;
- criação de tarefa por mensagem.

---

# 222. Áudio

Não é necessário no D0.

Se adicionado futuramente:

- transcrição;
- autoria;
- contexto;
- retenção;
- busca;

precisam ser considerados.

---

# 223. Vídeo

Também fora do D0.

---

# 224. Chamada

Fora do escopo inicial.

---

# 225. Emojis e reações

Podem melhorar comunicação, mas não são essenciais à proposta de valor.

---

# 226. Status de presença

Exemplo:

```text
online
ausente
```

não é prioridade.

A LPS não está tentando competir com mensageiros.

---

# 227. Mensagem privada genérica

Não necessária no D0.

Se Paulo quiser conversar sobre uma atividade, deve conversar dentro dela.

---

# 228. Benefício dessa restrição

A conversa não se perde em:

- WhatsApp;
- chat privado;
- e-mail;
- canal geral.

Ela fica junto do trabalho.

---

# 229. Contexto permanente

Meses depois, alguém abre a atividade e encontra:

- eventos;
- conversa;
- decisões;
- prazos;
- devoluções.

Isso cria memória operacional.

---

# 230. Comunicação como conhecimento institucional

Sem a LPS:

```text
conhecimento fica na cabeça das pessoas
```

ou:

```text
em chats dispersos
```

Com LPS:

```text
contexto fica vinculado ao trabalho
```

---

# 231. Pessoa sai da empresa

Mensagens históricas permanecem associadas à identidade inativada.

Não apagar autoria.

---

# 232. Setor muda de nome

Mensagens antigas permanecem no contexto correto.

---

# 233. Atividade concluída

A conversa deve continuar consultável conforme autorização.

---

# 234. Arquivamento

Atividades concluídas podem ser arquivadas visualmente.

Conversa continua preservada.

---

# 235. Pesquisa futura

Poderá permitir perguntas como:

> Onde já tivemos problema parecido?

A inteligência pode usar histórico autorizado.

---

# 236. Exemplo de aprendizado

Muitas mensagens contêm:

> “faltou especificação”

e muitas devoluções estruturadas possuem:

```text
Especificação incompleta
```

A LPS pode identificar padrão.

---

# 237. Dados estruturados validam linguagem

A combinação de texto + evento estruturado melhora aprendizado.

---

# 238. Comunicação não deve virar ruído analítico

Nem toda mensagem é importante.

A IA futura deve diferenciar:

- conversa casual operacional;
- decisão;
- risco;
- prazo;
- impedimento.

---

# 239. Sem IA no início

No D0, a conversa é armazenada e contextualizada.

Isso já é suficiente para gerar base futura.

---

# 240. Resumo manual

Antes de IA, o dono pode registrar um encerramento manual.

Exemplo:

```text
Resumo final:
Material entregue com 2 dias de atraso por prazo do fornecedor.
```

Pode ser útil, mas não deve ser obrigatório se gerar burocracia.

---

# 241. Resumo automático futuro

Depois, a LPS pode preparar o resumo usando:

- timeline;
- prazos;
- devoluções;
- mensagens;
- tempos.

---

# 242. Resumo como leitura, não fonte

Os dados originais continuam sendo a fonte oficial.

---

# 243. Notificações e auditoria

Toda notificação relevante deve ter origem em um evento identificável.

Exemplo:

```text
Notificação:
Sua posição mudou para 16 de 17.

Origem:
evento fila_posicao_alterada #1234
```

---

# 244. Evitar notificação sem evento

Isso dificulta auditoria.

---

# 245. Notificação e idempotência

Tecnicamente, o sistema deve evitar enviar o mesmo evento várias vezes acidentalmente.

Detalhamento técnico futuro.

---

# 246. Notificação e confiabilidade

Se o sistema diz:

```text
Atividade concluída
```

deve existir evento de conclusão correspondente.

---

# 247. Erro de notificação

Falha de canal não altera estado da atividade.

---

# 248. Permissões de configuração

Ações futuras podem incluir:

```text
notificacao.configurar_proprias
```

```text
notificacao.configurar_setor
```

```text
notificacao.configurar_organizacao
```

---

# 249. Configuração de organização

Somente pessoas autorizadas podem definir regras obrigatórias.

---

# 250. Configuração pessoal não pode quebrar obrigatórias

Exemplo:

Dono tenta desligar:

```text
conclusão da atividade
```

Se organização marcou como obrigatória:

```text
não pode desligar
```

---

# 251. Preferências por canal

Futuramente:

```text
Central LPS: sempre
Push: sim
E-mail: não
```

---

# 252. Central da LPS como canal obrigatório

Mesmo que e-mail ou push sejam desativados, eventos relevantes permanecem acessíveis na LPS.

---

# 253. Contador de não lidas

Pode existir:

```text
12
```

no sino de notificações.

---

# 254. Filtros

Futuramente:

```text
Todas
Menções
Prazos
Filas
Atrasos
Escalonamentos
```

---

# 255. Ações rápidas

Exemplo:

```text
Aceitar prazo
Recusar prazo
```

podem existir na própria notificação.

Isso depende de UX e segurança.

---

# 256. Notificação deve respeitar autorização atual

Se usuário perdeu acesso ao objeto, a notificação antiga não deve dar acesso indevido ao conteúdo.

---

# 257. Conteúdo sensível da notificação

Pode ser resumido.

Exemplo:

```text
Uma atividade do Financeiro foi atualizada.
```

se detalhes forem restritos.

---

# 258. Comunicação e multiempresa

Usuário com acesso a mais de uma empresa interna precisa saber em qual contexto a mensagem está.

Exemplo:

```text
Empresa:
Biasi Engenharia
```

---

# 259. Organização sempre implícita

Não deve existir mensagem cruzando organizações.

---

# 260. Segurança por contexto

A conversa herda:

- organização;
- empresa;
- atividade;
- tarefa;
- escopo.

---

# 261. Comunicação com externos

No futuro, cliente ou fornecedor pode participar de contexto limitado.

Não é prioridade do D0.

---

# 262. Se externo participar

Precisará haver regras específicas para:

- acesso;
- anexos;
- histórico;
- campos visíveis;
- mensagens internas.

---

# 263. Mensagem interna x externa

Pode surgir futuramente.

Não implementar no D0 sem necessidade.

---

# 264. Comentário interno

Também pode ser uma evolução.

Exemplo:

```text
visível somente para equipe interna
```

---

# 265. D0 deve manter modelo simples

Conversa visível a todos que possuem acesso ao contexto correspondente.

Regras especiais podem vir depois.

---

# 266. Comunicação e responsabilidade única

A conversa não muda o dono.

Se várias pessoas comentam ou ajudam:

```text
atividade continua com um único dono
```

---

# 267. Comunicação e executor

Comentar não torna alguém executor.

Atribuição é estruturada.

---

# 268. Comunicação e prazo

Dizer uma data não muda prazo.

---

# 269. Comunicação e conclusão

Escrever:

> “Pronto.”

não conclui tarefa automaticamente.

---

# 270. Comunicação e devolução

Escrever:

> “Volta para Engenharia.”

não devolve automaticamente.

---

# 271. Comunicação e fila

Escrever:

> “Coloca como prioridade.”

não reordena fila automaticamente.

---

# 272. Esse princípio evita ambiguidade

Conversa pode influenciar decisão.

Ação estruturada muda estado.

---

# 273. Inteligência pode reduzir atrito futuramente

A LPS pode detectar intenção e oferecer botão.

Exemplo:

```text
Mensagem parece solicitar devolução.

[Devolver tarefa]
```

---

# 274. Ainda exige confirmação

Nunca silenciosamente.

---

# 275. Mensagem pode citar evento

Exemplo:

```text
Ryan respondeu ao evento de devolução.
```

Futuramente útil.

---

# 276. Sistema pode contextualizar conversa

Ao abrir conversa de tarefa, mostrar:

```text
Setor:
Compras

Status:
Em execução

Prazo:
15/09 às 15h
```

Isso ajuda o usuário.

---

# 277. Contexto não deve ocupar excesso de tela

Detalhamento no documento 09.

---

# 278. Comunicação mobile

Precisa ser rápida.

Exemplo:

- abrir notificação;
- responder;
- mencionar;
- voltar para atividade.

---

# 279. Comunicação web

Pode mostrar:

- atividade;
- tarefas;
- conversa;
- timeline;

lado a lado ou em abas.

---

# 280. UX deve evitar duplicidade

Se existe uma conversa da atividade e outra da tarefa, precisa ficar claro onde o usuário está escrevendo.

---

# 281. Cabeçalho da conversa

Exemplo:

```text
Você está comentando em:
Tarefa — Cotação de cabos
```

---

# 282. Mensagem no contexto errado

Pode gerar confusão.

Uma interface clara reduz isso.

---

# 283. Mover mensagem

No D0, não precisa permitir mover mensagem entre atividade e tarefa.

Se escreveu no lugar errado, pode responder/corrigir.

---

# 284. Regras de retenção

A organização pode futuramente possuir política de retenção.

Mas não deve apagar histórico operacional essencial sem avaliação.

---

# 285. LGPD

Mensagens podem conter dados pessoais.

A implementação futura precisa respeitar a legislação aplicável.

Este documento apenas reconhece essa necessidade.

---

# 286. Dados sensíveis

A LPS deve desencorajar o uso da conversa para dados desnecessariamente sensíveis.

Políticas corporativas podem orientar.

---

# 287. Exportação de conversa

Pode existir futuramente.

Precisa de autorização específica.

---

# 288. Auditoria de exportação

Se implementada, deve ser registrada.

---

# 289. Mensagens e evidência

A conversa pode ajudar a explicar decisões.

Mas a LPS não deve prometer valor jurídico específico sem análise apropriada.

---

# 290. Histórico de leitura

Pode ser útil para confirmar ciência.

Não é obrigatório para toda mensagem.

---

# 291. “Visto por”

Recurso estilo mensageiro não é prioridade.

---

# 292. Ciência formal é mais importante

Quando necessário, usar ação:

```text
Confirmar ciência
```

em vez de inferir de “visualizou”.

---

# 293. Mensagem fixada por gestor

Evolução futura.

Pode destacar:

- decisão;
- instrução;
- risco.

---

# 294. Tags em mensagem

Também evolução futura.

Exemplo:

```text
#decisão
#risco
```

Mas IA pode tornar isso desnecessário posteriormente.

---

# 295. Evitar pedir que usuário classifique toda mensagem

Isso gera burocracia.

---

# 296. Inteligência futura deve ajudar sem exigir marcação manual constante

Exemplo:

identificar possíveis decisões automaticamente.

---

# 297. Comunicação e melhoria contínua

Mensagens podem revelar problemas que não aparecem apenas nos tempos.

Exemplo:

> “Toda vez falta essa informação.”

Isso pode indicar oportunidade de processo.

---

# 298. Comunicação e treinamento

Dúvidas recorrentes podem revelar:

- falta de padrão;
- falta de conhecimento;
- necessidade de treinamento.

---

# 299. Comunicação e documentação

Futuramente, a LPS pode sugerir transformar conhecimento recorrente em procedimento.

Isso pertence à inteligência.

---

# 300. Comunicação e gargalo

Exemplo:

Muitas mensagens:

> “Aguardando aprovação.”

podem reforçar dados de espera por decisão.

---

# 301. Dados estruturados continuam sendo base

Se a tarefa está formalmente bloqueada por:

```text
Aguardando aprovação
```

esse dado é mais confiável que apenas procurar a frase nas mensagens.

---

# 302. Conversa complementa o “por quê”

A auditoria pode dizer:

```text
bloqueado 2 dias
```

A conversa pode explicar:

> Diretor estava aguardando informação do cliente.

---

# 303. Resumo automático deve aproveitar isso

Exemplo:

> A tarefa ficou bloqueada por dois dias aguardando aprovação, conforme registrado no sistema. A conversa indica que a aprovação dependia de informação do cliente.

Aqui fato e contexto permanecem separados.

---

# 304. Métricas de comunicação

No D0, evitar métricas como:

- mensagens por pessoa;
- tempo online;
- quantidade de respostas.

Isso não representa produtividade.

---

# 305. Métricas úteis futuramente

Podem existir:

- tempo até decisão após escalonamento;
- tempo até resposta em situação crítica;
- quantidade de menções sem resposta.

Mas somente se ajudarem gestão.

---

# 306. Não medir produtividade por quantidade de mensagens

Esse é um antiobjetivo.

---

# 307. Notificação como apoio, não controle excessivo

A LPS deve ajudar pessoas a saber o que mudou.

Não deve criar ambiente de vigilância por cada clique.

---

# 308. Auditoria registra fatos relevantes

Não necessariamente cada movimento de mouse.

---

# 309. Comunicação deve reduzir reuniões desnecessárias

Se contexto está registrado:

- status;
- prazo;
- decisões;
- devoluções;

algumas reuniões de cobrança podem ser reduzidas.

---

# 310. Comunicação deve reduzir WhatsApp paralelo

Quanto mais fácil for conversar dentro da atividade, maior chance de contexto permanecer na LPS.

---

# 311. Mas não obrigar tudo a passar pela conversa

Telefonemas e reuniões continuarão existindo.

O sistema pode permitir registrar decisão depois.

---

# 312. Registro pós-reunião

Exemplo:

```text
Paulo:
Conforme reunião, ficou definido que o prazo será 18/09.
```

Depois:

```text
ação estruturada altera o prazo
```

---

# 313. Resumo de reunião futuro

Pode ser anexado ou relacionado à atividade.

Não faz parte do D0.

---

# 314. Conversa precisa ser rápida

Se enviar mensagem for lento ou burocrático, usuários voltarão para WhatsApp.

---

# 315. Campo simples

Conceitualmente:

```text
Digite uma mensagem...
```

com:

- texto;
- menção;
- anexo futuramente.

---

# 316. Notificação precisa ser rápida

Atrasos grandes na entrega reduzem valor.

---

# 317. Eventos críticos em tempo próximo do real

Exemplos:

- devolução;
- prazo;
- escalonamento;
- conclusão.

---

# 318. Consistência

Se um evento é registrado, a central precisa refletir corretamente.

---

# 319. Falha temporária

Sistema pode reprocessar notificação sem duplicar.

Detalhamento técnico futuro.

---

# 320. Preferências padrão

Ao criar usuário, a organização pode definir padrão.

Exemplo:

```text
Menções: ligadas
Atribuição: ligada
Conclusão de atividade própria: ligada
Mudança de posição: ligada na central
```

---

# 321. Usuário pode ajustar o que é opcional

---

# 322. Mudança de posição como caso especial

Como a posição pode mudar muitas vezes, a central interna pode receber todos os eventos.

Push/e-mail podem ser configurados separadamente.

Isso preserva a decisão de transparência sem criar excesso de interrupção.

---

# 323. Exemplo

Central:

```text
10:00 — 4 → 5
10:15 — 5 → 4
10:40 — 4 → 7
```

Push:

```text
configurável
```

---

# 324. Histórico de fila continua completo

Mesmo se notificação estiver agrupada.

---

# 325. Atraso e escalonamento têm maior importância

Esses eventos podem ter prioridade superior à simples mudança de posição.

---

# 326. Ordem de atenção

Conceitualmente:

```text
ação necessária
>
risco
>
informação
```

A UX pode refletir isso.

---

# 327. Badges

Exemplo futuro:

```text
AÇÃO NECESSÁRIA
```

```text
INFORMATIVO
```

---

# 328. Resumo de atividade no D1/D2

Pode ser acionado:

```text
Resumir atividade
```

ou gerado automaticamente em momentos específicos.

---

# 329. Momentos possíveis

- ao abrir atividade antiga;
- antes de reunião;
- ao escalar;
- ao concluir;
- após longo período sem acesso.

---

# 330. Resumo precisa mostrar data de referência

Exemplo:

```text
Resumo atualizado até 15/09 às 14:30.
```

---

# 331. Usuário deve poder abrir fontes

Futuramente, cada ponto do resumo pode levar ao evento ou mensagem de origem.

Isso aumenta confiabilidade.

---

# 332. Resumo não deve substituir timeline

É uma camada de síntese.

---

# 333. Inteligência e privacidade

O modelo de IA deve receber apenas dados que o usuário está autorizado a acessar.

---

# 334. Inteligência e organizações

Dados de outra organização não devem aparecer no resumo.

---

# 335. Aprendizado agregado futuro

Pode ocorrer de forma anonimizada e autorizada.

Pertence ao documento 07.

---

# 336. Notificação e IA

Futuramente, a LPS pode sugerir:

```text
Há risco de atraso.
```

Mas precisa distinguir:

```text
alerta calculado
```

de:

```text
prazo já vencido
```

---

# 337. Fato x previsão na notificação

Exemplo de fato:

```text
Prazo venceu há 2h.
```

Exemplo de previsão:

```text
Há risco de atraso com base no histórico.
```

Nunca misturar.

---

# 338. Explicabilidade do alerta

Futuramente:

```text
Risco alto porque restam 2 dias e etapas semelhantes levam mediana de 3,4 dias.
```

---

# 339. Comunicação como ativo da empresa

O histórico contextual pode se tornar um ativo de conhecimento.

Mas apenas se:

- estiver vinculado ao trabalho;
- for pesquisável;
- possuir autoria;
- possuir segurança;
- não for apagado indiscriminadamente.

---

# 340. D0 precisa provar o conceito

A primeira versão deve provar que:

- as pessoas conseguem conversar dentro da atividade;
- as pessoas conseguem conversar dentro da tarefa;
- eventos importantes geram avisos;
- o solicitante acompanha mudanças sem precisar entrar toda hora;
- o dono sabe quando algo foi concluído;
- devoluções chegam a quem precisa agir;
- prazos são negociados de forma visível;
- escalonamentos chegam a quem decide.

---

# 341. Cenário de teste 1 — posição

Estado inicial:

```text
Paulo:
4 de 17
```

Almoxarifado reordena:

```text
16 de 17
```

Esperado:

- histórico registra;
- Paulo recebe notificação conforme canal configurado;
- Paulo não vê detalhes das outras demandas.

---

# 342. Cenário de teste 2 — conclusão

Tarefa final é concluída.

Esperado:

```text
Dono recebe notificação obrigatória.
```

---

# 343. Cenário de teste 3 — prazo

Comercial recebe pedido para hoje.

Propõe:

```text
terça 15h
```

Esperado:

- dono é notificado;
- pode aceitar ou recusar;
- resposta gera evento;
- conversa não substitui ação.

---

# 344. Cenário de teste 4 — recusa

Dono recusa o prazo.

Esperado:

- escalonamento é criado;
- gestores configurados recebem aviso;
- atividade mantém histórico.

---

# 345. Cenário de teste 5 — devolução

Compras devolve para Engenharia.

Motivo:

```text
Especificação incompleta
```

Esperado:

- responsável por Engenharia recebe aviso;
- dono pode receber conforme configuração;
- evento aparece na timeline;
- mensagem automática pode aparecer na conversa.

---

# 346. Cenário de teste 6 — menção

Paulo escreve:

```text
@Ryan confira a especificação.
```

Esperado:

- Ryan recebe notificação;
- somente se possui acesso ao contexto.

---

# 347. Cenário de teste 7 — mensagem de prazo

Ryan escreve:

> “Consigo entregar sexta.”

Esperado no D0:

- apenas mensagem;
- nenhum prazo é alterado automaticamente.

---

# 348. Cenário de teste 8 — usuário inativo

Usuário antigo permanece como autor das mensagens históricas.

Não pode enviar novas.

---

# 349. Cenário de teste 9 — acesso negado

Usuário recebe link de atividade sem autorização.

Esperado:

```text
acesso negado
```

mesmo que tenha recebido o URL.

---

# 350. Cenário de teste 10 — notificação antiga

Usuário perdeu acesso depois.

A notificação histórica não deve abrir conteúdo restrito.

---

# 351. Critério de aceite funcional

O módulo está correto quando comunicação e notificação ajudam a responder:

- o que mudou;
- quem precisa saber;
- quem precisa agir;
- onde conversar;
- qual é o estado oficial;
- qual é apenas contexto.

---

# 352. Regra de ouro da comunicação

> **Toda conversa relevante deve permanecer ligada ao trabalho que lhe deu origem.**

---

# 353. Regra de ouro do dado estruturado

> **Mensagem explica; ação estruturada altera o processo.**

---

# 354. Regra de ouro da notificação

> **A LPS deve avisar quem precisa saber, sem obrigar o usuário a consultar continuamente o sistema.**

---

# 355. Regra de ouro do ruído

> **Nem tudo que acontece precisa interromper o usuário, mas tudo que é relevante precisa permanecer rastreável.**

---

# 356. Regra de ouro da conclusão

> **O dono da atividade sempre precisa saber quando o resultado foi concluído.**

---

# 357. Regra de ouro da posição

> **Mudanças de posição precisam ficar visíveis e registradas, pois transparência de fila é parte central da proposta da LPS.**

---

# 358. Regra de ouro da inteligência

> **A conversa pode alimentar inteligência futura, mas nunca deve ser tratada automaticamente como verdade operacional sem confirmação.**

---

# 359. Decisões consolidadas neste documento

## Comunicação

- a LPS não será um Slack corporativo genérico no D0;
- não haverá canais livres como `#geral`, `#financeiro` ou `#comercial`;
- comunicação será vinculada à atividade ou à tarefa;
- conversa é contexto;
- mensagem não cria automaticamente atividade ou tarefa;
- mensagem não altera automaticamente prazo, status, fila ou responsável;
- histórico precisa ser preservado.

## Participantes

- acesso depende da atividade/tarefa e das autorizações;
- dono precisa de contexto suficiente da própria atividade;
- executores acessam o contexto necessário;
- gestores podem acessar conforme permissão;
- menção não concede acesso automaticamente.

## Menções

- menções individuais são suportadas;
- menção válida gera notificação;
- menções coletivas de setor podem ficar para depois.

## Notificações

- existirão notificações internas na LPS;
- regras podem ser configuráveis;
- organização pode definir eventos obrigatórios;
- usuário pode configurar eventos opcionais;
- canal é separado do evento;
- silenciar canal não apaga histórico.

## Posição

- toda mudança é registrada;
- solicitante precisa conseguir saber que sua posição mudou;
- detalhes das outras demandas não são expostos;
- canal externo pode ser configurável.

## Prazo

- proposta gera notificação;
- aceite gera evento;
- recusa gera evento;
- mudança formal ocorre por ação estruturada;
- conversa não substitui negociação.

## Devolução

- gera evento;
- precisa chegar a quem deve agir;
- motivo deve ser exibido;
- gestor e dono podem ser notificados conforme configuração.

## Atraso

- atraso precisa gerar evento;
- destinatários dependem da configuração;
- notificações repetitivas devem ser evitadas.

## Conclusão

- dono da atividade sempre é notificado;
- demais participantes são configuráveis;
- conclusão de tarefa intermediária pode ser opcional.

## Escalonamento

- destinatários configurados recebem aviso;
- decisão precisa ser registrada;
- encerramento do escalonamento pode gerar notificação.

## Inteligência

- mensagens poderão alimentar análise futura;
- IA poderá identificar possíveis prazos, riscos, impedimentos e decisões;
- nada deve ser alterado automaticamente sem confirmação;
- resumo automático da atividade é uma evolução desejada.

---

# 360. Decisões ainda pendentes

Precisam ser detalhadas posteriormente:

- quais canais entram exatamente no D0;
- se push entra já na primeira versão mobile;
- política de e-mail;
- edição de mensagens;
- exclusão de mensagens;
- retenção;
- anexos;
- confirmação de ciência;
- agrupamento de notificações;
- horário de silêncio;
- prioridade visual das notificações;
- busca de mensagens;
- mensagens externas;
- comentários internos;
- regras de resumo automático;
- política de IA sobre mensagens;
- critérios de notificação de tarefas críticas.

---

# 361. Relação com outros documentos

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Define:

- atividade;
- tarefa;
- dono;
- executores;
- devolução;
- conclusão.

Este documento define como esses eventos são comunicados.

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Define:

- posição;
- prazo;
- conflito;
- escalonamento.

Este documento define como essas mudanças chegam às pessoas.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

Define:

- eventos;
- timeline;
- auditoria.

Notificações nascem desses eventos.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Define:

- quem pode acessar;
- quem pode conversar;
- quem pode configurar;
- quem pode receber determinadas informações.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Detalhará:

- análise de conversas;
- detecção de padrões;
- resumo automático;
- recomendações.

## `08_BANCO_DE_DADOS.md`

Traduzirá os conceitos para estruturas como:

```text
conversas
mensagens
participantes
menções
notificações
preferências
eventos
```

---

# 362. Estrutura conceitual sugerida para o banco

Sem fechar nomes definitivos, provavelmente serão necessários conceitos equivalentes a:

```text
comunicacao.conversas
comunicacao.mensagens
comunicacao.participantes
comunicacao.mencoes
```

e:

```text
comunicacao.notificacoes
comunicacao.preferencias_notificacao
```

Possivelmente:

```text
comunicacao.entregas_notificacao
```

para controlar canais no futuro.

A modelagem final será feita no documento 08.

---

# 363. Tipos de conversa

Conceitualmente:

```text
atividade
```

ou:

```text
tarefa
```

Evitar muitos tipos no D0.

---

# 364. Uma atividade pode possuir uma conversa principal

---

# 365. Cada tarefa pode possuir uma conversa própria

---

# 366. Mensagem sempre tem autor

Exceto mensagens automáticas do sistema.

---

# 367. Mensagem automática precisa estar identificada como sistema

Exemplo:

```text
LPS:
Tarefa devolvida para Engenharia.
```

---

# 368. Sistema não deve fingir ser usuário

---

# 369. Mensagem automática precisa apontar para evento estruturado

Quando aplicável.

---

# 370. Participante precisa ter acesso válido

---

# 371. Menção precisa validar acesso

---

# 372. Notificação precisa validar destinatário

---

# 373. Resumo precisa validar escopo

---

# 374. Inteligência precisa validar autorização

---

# 375. Exemplo completo — Solicitação de Compra

Atividade:

```text
Material disponível na obra
```

Dono:

```text
Paulo
```

Tarefa:

```text
Comprar material
```

Setor:

```text
Compras
```

Conversa:

```text
Ryan:
Fornecedor informou prazo de 7 dias.

Paulo:
O material precisa estar na obra até dia 20.

Ryan:
Consigo emitir o pedido amanhã até 15h.
```

Ação estruturada:

```text
Ryan propõe prazo:
amanhã 15h.
```

Notificação:

```text
Paulo recebe:
Novo prazo proposto.
```

Paulo:

```text
Aceita.
```

Sistema:

```text
Prazo comprometido atualizado.
```

Mais tarde:

```text
Compras devolve para Engenharia.
Motivo: especificação incompleta.
```

Notificação:

```text
Engenharia recebe devolução.
```

Conversa:

```text
LPS:
Tarefa devolvida para Engenharia.
Motivo: especificação incompleta.
```

---

# 376. Exemplo completo — fila

Paulo:

```text
4 de 17
```

Depois:

```text
16 de 17
```

Sistema registra:

```text
posição anterior
nova posição
data/hora
origem da mudança
```

Notificação:

```text
Sua posição mudou de 4 de 17 para 16 de 17.
```

Sem mostrar:

```text
quais 12 tarefas passaram na frente.
```

---

# 377. Exemplo completo — orçamento

Atividade:

```text
Entregar orçamento ao cliente
```

Solicitado:

```text
Hoje
```

Comercial:

```text
Consigo terça às 15h.
```

Ação:

```text
Propor novo prazo
```

Dono recebe notificação.

Se aceita:

```text
Prazo comprometido atualizado.
```

Se recusa:

```text
Escalonamento criado.
```

Gestores recebem notificação.

---

# 378. Exemplo completo — conclusão

Última tarefa concluída.

Se regra exigir confirmação:

```text
Atividade pronta para encerramento.
```

Dono recebe:

```text
Resultado pronto para validação.
```

Depois:

```text
Atividade concluída.
```

Notificação obrigatória:

```text
Dono recebe conclusão.
```

---

# 379. Exemplo completo — resumo futuro

Depois de concluída:

```text
Resumo:

A atividade foi criada em 10/09 e concluída em 18/09.

O prazo inicial era 15/09 e foi renegociado uma vez para 18/09.

Compras devolveu uma tarefa para Engenharia por especificação incompleta.

O maior período de espera foi de 7 dias com o fornecedor.

Participaram 4 pessoas em 3 setores.
```

---

# 380. O que a LPS ganha ao manter a comunicação contextual

Ganha:

- memória;
- rastreabilidade;
- contexto;
- redução de cobrança paralela;
- dados para IA;
- entendimento de decisões;
- base para resumos;
- menos informação perdida.

---

# 381. O que a LPS perde se tentar virar Slack no D0

Aumenta:

- escopo;
- complexidade;
- notificações;
- permissões;
- infraestrutura;
- UX;
- manutenção.

E desvia do diferencial principal.

---

# 382. Por isso, o foco é

```text
COMUNICAÇÃO DO TRABALHO
```

não:

```text
COMUNICAÇÃO DE TODA A EMPRESA
```

---

# 383. D0 — checklist funcional de comunicação

A primeira versão estará funcional quando:

```text
[ ] atividade possui conversa
[ ] tarefa possui conversa
[ ] mensagem registra autor
[ ] mensagem registra horário
[ ] acesso é validado
[ ] menção funciona
[ ] notificação interna funciona
[ ] tarefa atribuída gera aviso
[ ] devolução gera aviso
[ ] mudança de posição gera evento
[ ] prazo proposto gera aviso
[ ] atraso pode gerar aviso
[ ] escalonamento gera aviso
[ ] conclusão da atividade avisa o dono
[ ] conversa não altera dados oficiais
```

---

# 384. D0 — checklist de simplicidade

```text
[ ] enviar mensagem é simples
[ ] abrir contexto é rápido
[ ] notificação leva ao ponto correto
[ ] usuário sabe se precisa agir
[ ] usuário sabe em qual atividade está
[ ] não existem canais genéricos desnecessários
[ ] não existe configuração excessiva
```

---

# 385. D0 — checklist de segurança

```text
[ ] usuário sem acesso não vê conversa
[ ] menção não burla autorização
[ ] organização é isolada
[ ] mensagem mantém autoria
[ ] histórico não desaparece silenciosamente
[ ] notificação antiga não libera acesso atual indevido
```

---

# 386. D0 — checklist de auditoria

```text
[ ] mensagem tem timestamp
[ ] mensagem tem autor
[ ] edição pode ser rastreada quando implementada
[ ] eventos estruturados continuam separados
[ ] notificações têm evento de origem
```

---

# 387. Indicadores futuros possíveis

Sem transformar comunicação em medição de produtividade, podem ser úteis:

- tempo até decisão após escalonamento;
- tempo entre devolução e resposta;
- quantidade de atividades com conversa ativa;
- quantidade de decisões estruturadas após discussão;
- volume de notificações por tipo;
- taxa de leitura de eventos obrigatórios.

---

# 388. Indicadores que devem ser evitados como produtividade

Evitar:

```text
mensagens enviadas por colaborador
```

```text
quantidade de caracteres
```

```text
tempo online no chat
```

Esses números não representam resultado.

---

# 389. Comunicação precisa servir ao fluxo

Toda função deve responder:

> Isso ajuda o trabalho a avançar ou a ser entendido?

Se não:

provavelmente não pertence ao D0.

---

# 390. Regra de ouro do D0

> **A comunicação da LPS deve registrar contexto suficiente para evitar perda de informação, sem tentar substituir todos os mensageiros corporativos.**

---

# 391. Resumo funcional

A lógica central pode ser representada assim:

```text
ATIVIDADE É CRIADA
↓
POSSUI CONVERSA
↓
TAREFAS PODEM POSSUIR CONVERSAS
↓
PESSOAS AUTORIZADAS PARTICIPAM
↓
MENSAGENS REGISTRAM CONTEXTO
↓
AÇÕES ESTRUTURADAS ALTERAM O PROCESSO
↓
EVENTOS GERAM NOTIFICAÇÕES
↓
POSIÇÃO / PRAZO / DEVOLUÇÃO / ATRASO / CONCLUSÃO / ESCALONAMENTO
↓
USUÁRIO NÃO PRECISA ENTRAR TODA HORA PARA DESCOBRIR O QUE MUDOU
↓
HISTÓRICO FICA PRESERVADO
↓
CONVERSAS + EVENTOS ALIMENTAM RESUMO E INTELIGÊNCIA FUTURA
```

---

# 392. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação das regras de comunicação contextual, notificações e resumo futuro da LPS |

---

# 393. Encerramento

A LPS deve tratar comunicação como parte do trabalho, e não como um produto paralelo.

A conversa deve ajudar a responder:

> O que foi discutido?

> Por que essa tarefa voltou?

> Qual decisão foi tomada?

> Qual risco surgiu?

> Quem precisa agir?

As notificações devem ajudar a responder:

> O que mudou sem eu precisar abrir o sistema toda hora?

> Minha posição mudou?

> O prazo mudou?

> A tarefa voltou?

> Está atrasada?

> Foi concluída?

> Existe uma decisão que depende de mim?

A estrutura precisa preservar uma fronteira clara:

```text
CONVERSA
=
contexto
```

```text
AÇÃO ESTRUTURADA
=
mudança oficial
```

Essa separação permite que a LPS seja simples no presente e inteligente no futuro.

Quando houver histórico suficiente, mensagens, eventos, prazos, devoluções e decisões poderão ser combinados para gerar resumos e análises muito mais úteis.

Mas o D0 deve começar com o essencial:

> **comunicação contextual, notificações relevantes, histórico preservado e nenhuma ambiguidade sobre o estado oficial do trabalho.**
