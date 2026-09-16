# 09 — Telas e Experiência do Usuário

> Documento funcional da LPS para traduzir regras de negócio, fluxos, filas, prazos, auditoria, comunicação e permissões em uma experiência simples, rápida e consistente no computador e no mobile.

---

# 1. Objetivo deste documento

Este documento define como a LPS deve se apresentar para o usuário.

Ele deve responder:

- como o usuário entra no sistema;
- o que encontra na Home;
- como acompanha suas atividades;
- como acompanha tarefas;
- como enxerga posição em fila;
- como cria atividade rapidamente;
- como inicia e pausa trabalho;
- como acompanha histórico;
- como conversa dentro do contexto da atividade;
- como recebe notificações;
- como o gestor acompanha fila, gargalos e capacidade;
- como funcionam cadastros;
- como funcionam configurações;
- como funcionam permissões;
- como a experiência muda entre desktop e mobile;
- como evitar excesso de telas, cliques e campos;
- como tornar a LPS fácil para quem executa e completa para quem gerencia.

Este documento não define:

- código;
- framework;
- banco de dados;
- API;
- design system completo;
- identidade visual final;
- tipografia final;
- biblioteca de componentes;
- infraestrutura;
- inteligência artificial final.

Esses assuntos pertencem às etapas de implementação e design visual.

---

# 2. Princípio central de UX

A LPS precisa ser simples o suficiente para a pessoa usar sem treinamento extenso.

A regra principal é:

> **O usuário deve conseguir registrar, iniciar, movimentar, acompanhar e concluir trabalho com o mínimo de esforço possível.**

A experiência precisa favorecer:

```text
ação rápida
+
contexto claro
+
pouca digitação
+
dados capturados automaticamente
```

---

# 3. Regra mais importante deste documento

> **Cadastrar uma atividade precisa ser extremamente rápido.**

Criar atividade não pode parecer preencher um formulário de ERP.

A experiência precisa se aproximar de:

```text
Título
↓
Dono
↓
Prazo
↓
Criar
```

com os demais campos aparecendo apenas quando necessários.

---

# 4. O usuário não pode sentir que está “alimentando sistema”

A LPS precisa parecer uma ferramenta para resolver trabalho.

Não uma obrigação administrativa.

Evitar:

- dezenas de campos;
- formulários longos;
- telas fragmentadas;
- cadastros em cascata;
- obrigatoriedade sem motivo;
- menus excessivos;
- termos técnicos desnecessários.

---

# 5. Dados devem nascer da ação

Exemplo:

Ao clicar:

```text
Iniciar
```

a LPS registra:

- usuário;
- hora;
- tarefa;
- setor.

Ao clicar:

```text
Devolver
```

a LPS já sabe:

- quem está devolvendo;
- origem;
- atividade;
- tarefa;
- horário.

O usuário preenche apenas o que a LPS não consegue saber.

---

# 6. Desktop e mobile

A LPS deve nascer para:

```text
web desktop
+
mobile
```

A mesma lógica de produto deve existir nos dois.

Mas a interface não precisa ser idêntica.

---

# 7. Desktop

O desktop é ideal para:

- visualizar muitas informações;
- gerir fila;
- cadastrar estruturas;
- analisar histórico;
- configurar permissões;
- acompanhar métricas;
- gerenciar equipe.

---

# 8. Mobile

O mobile é ideal para:

- ver o que fazer;
- iniciar;
- pausar;
- retomar;
- concluir;
- comentar;
- receber notificação;
- acompanhar posição;
- aceitar ou rejeitar prazo;
- registrar informação rápida.

---

# 9. Mobile não deve ser desktop espremido

Não reproduzir uma tabela de 15 colunas em uma tela de celular.

O mobile precisa priorizar:

```text
ação
```

e não:

```text
densidade de informação
```

---

# 10. Hierarquia principal da navegação

A navegação desktop deve permanecer rasa.

Estrutura consolidada:

```text
OPERAÇÃO
Home
Minhas atividades
Minhas tarefas
Fila
Notificações

GESTÃO
Visão do gestor
Cadastros ▾
Usuários
Perfis e permissões ▾

RODAPÉ
Configurações ▾
```

## Home

Não possui submenu.

## Minhas atividades

Não possui submenu lateral.

Filtros ou abas ficam dentro da tela:

```text
Minhas
Participando
Concluídas
```

## Minhas tarefas

Não possui submenu lateral.

Dentro da tela podem existir:

```text
A fazer
Em execução
Bloqueadas
Concluídas
```

## Fila

Não possui submenu lateral.

Setor, status e demais recortes são filtros internos.

## Notificações

Não possui submenu lateral.

## Visão do gestor

Não possui submenu lateral.

Recortes como fila, prazo, bloqueio, capacidade e gargalo ficam dentro da própria visão.

## Cadastros

Submenus:

```text
Processos
Setores
Empresas
Obras
Centros de custo
Tipos de atividade
Tipos de tarefa
Motivos
```

`Motivos` pode reunir abas internas para devolução e bloqueio.

## Usuários

Não possui submenu lateral.

Dentro da tela:

```text
Ativos
Inativos
Convites
```

## Perfis e permissões

Submenus:

```text
Perfis
Grupos de ações
Ações
Autorizações específicas
```

## Configurações

Submenus:

```text
Organização
Notificações
Escalonamento
Calendário de trabalho
```

`Integrações` pode aparecer futuramente quando existir funcionalidade real.

A LPS não deve mostrar submenu vazio ou funcionalidade futura desabilitada apenas para parecer completa.

---

# 11. Menu não deve mostrar o que o usuário não pode usar

Exemplo:

Usuário sem:

```text
perfil.editar
```

não precisa ver:

```text
Permissões
```

Isso melhora UX.

A segurança continua no backend.

---

# 12. Navegação principal no mobile

Sugestão:

```text
Home
Atividades
Tarefas
Fila
Mais
```

Dentro de `Mais` podem ficar:

```text
Notificações
Visão do gestor, se autorizado
Cadastros, se autorizado
Usuários, se autorizado
Perfis e permissões, se autorizado
Configurações
```

Cadastros administrativos complexos podem abrir como tela inteira no mobile em vez de modal centralizado.

---

# 13. Princípio de profundidade

Usuário não deveria precisar navegar por:

```text
Menu
↓
Submenu
↓
Submenu
↓
Submenu
↓
Tela
```

para tarefas comuns.

As principais ações precisam estar a:

```text
1 ou 2 interações
```

sempre que possível.

---

# 14. Login

A tela de login precisa ser:

- limpa;
- profissional;
- rápida;
- sem distrações.

---

# 15. Campos de login

No mínimo:

```text
E-mail
Senha
Entrar
```

Complementos futuros:

```text
Entrar com Microsoft
Entrar com Google
SSO corporativo
```

---

# 16. Recuperação de senha

Acesso simples:

```text
Esqueci minha senha
```

---

# 17. Organização após login

No modelo atual, usuário pertence a uma única organização.

Logo, não é necessário perguntar:

```text
Qual organização você quer acessar?
```

em todo login.

---

# 18. Empresa atual

Se o usuário possuir acesso a várias empresas internas, a interface pode permitir seleção de contexto.

Exemplo:

```text
Empresa atual:
Biasi Engenharia
```

---

# 19. Troca de empresa

Pode existir no topo:

```text
Biasi Engenharia ▾
```

A mudança filtra contexto.

Não altera autorização.

---

# 20. Home

A Home precisa responder rapidamente:

> O que precisa da minha atenção agora?

---

# 21. A Home não deve ser um dashboard cheio de gráficos

Para usuário operacional, prioridade é:

- tarefas;
- prazos;
- pendências;
- notificações;
- atividades.

---

# 22. Home do colaborador

Sugestão de blocos:

```text
Em execução agora
Próximas tarefas
Pendências
Atividades que acompanho
Notificações importantes
```

---

# 23. Em execução agora

Se existe uma sessão ativa:

```text
Revisão do orçamento — 01:24:32
[PAUSAR]
[CONCLUIR]
```

Esse bloco deve ter grande destaque.

---

# 24. Sem tarefa ativa

Mostrar:

```text
Nenhuma tarefa em execução.
```

e ação:

```text
[Ver próximas tarefas]
```

---

# 25. Próximas tarefas

Lista curta.

Exemplo:

```text
1. Revisar escopo — hoje 14h
2. Levantar quantitativos — amanhã
3. Conferir proposta — sem prazo
```

---

# 26. Pendências

Exemplos:

```text
Novo prazo aguardando sua decisão
Tarefa devolvida
Escalonamento aguardando resposta
Tempo pendente de apropriação
```

---

# 27. Notificações importantes

Mostrar apenas as mais relevantes.

Não transformar Home em central completa.

---

# 28. Home do gestor

Pode priorizar:

```text
Fila do setor
Atrasadas
Conflitos de prazo
Bloqueadas
Escalonamentos
Capacidade
```

---

# 29. Home da diretoria

Pode priorizar:

```text
Gargalos
Setores com fila crescente
Atrasos relevantes
Escalonamentos
Visão consolidada
```

---

# 30. Home configurável

No futuro, os blocos podem variar por perfil.

No D0, usar poucos modelos de Home.

---

# 31. Minhas atividades

Tela destinada a responder:

> Quais resultados estão sob minha responsabilidade ou acompanhamento?

---

# 32. Abas sugeridas

```text
Minhas
Participando
Concluídas
```

Opcionalmente:

```text
Todas que posso visualizar
```

conforme autorização.

---

# 33. Atividades do dono

Em:

```text
Minhas
```

mostrar atividades onde:

```text
dono_usuario_id = usuário atual
```

---

# 34. Participando

Atividades onde a pessoa:

- executa tarefa;
- acompanha;
- participa da conversa;
- possui papel relevante.

---

# 35. Lista de atividades

Cada cartão/linha deve mostrar apenas o necessário.

Exemplo:

```text
Orçamento entregue ao cliente
Comercial
Prazo: 18/09
4 de 7 tarefas concluídas
Em andamento
```

---

# 36. Evitar poluição

Não mostrar no cartão:

- todos os executores;
- histórico inteiro;
- todos os prazos;
- todas as tags;
- todos os setores.

Detalhes ficam dentro da atividade.

---

# 37. Filtros de atividades

Inicialmente:

```text
Status
Prazo
Setor
Obra
Empresa
```

Filtros avançados podem vir depois.

---

# 38. Busca

Campo simples:

```text
Buscar atividades...
```

Por:

- título;
- código futuro;
- obra;
- contexto.

---

# 39. Ordenação

Opções úteis:

```text
Prazo
Última atualização
Criação
```

---

# 40. Estado de atraso

Atraso deve ser visível.

Exemplo:

```text
Atrasada 2 dias
```

Sem depender apenas de cor.

---

# 41. Atividade bloqueada

Mostrar claramente:

```text
Bloqueada — aguardando cliente
```

---

# 42. Atividade com conflito de prazo

Mostrar:

```text
Prazo em negociação
```

---

# 43. Criar atividade

A ação:

```text
+ Nova atividade
```

deve estar facilmente acessível.

Desktop:

```text
botão fixo no topo
```

Mobile:

```text
botão flutuante ou ação principal
```

---

# 44. Formulário inicial de atividade

O formulário deve começar pequeno.

Campos iniciais recomendados:

```text
O que precisa ser resolvido?
Dono
Prazo
```

---

# 45. Campo principal

Rótulo recomendado:

```text
O que precisa ser resolvido?
```

ou:

```text
Resultado esperado
```

Evitar apenas:

```text
Título
```

se a linguagem do produto puder orientar melhor.

---

# 46. Exemplo

```text
Material disponível na obra
```

em vez de:

```text
Comprar cabo
```

quando o resultado real é maior.

---

# 47. Campo dono

Pré-preenchimento possível:

```text
Eu
```

quando o usuário cria atividade para si.

Pode trocar.

---

# 48. Prazo

Pode ser:

```text
Sem prazo
Hoje
Amanhã
Escolher data
```

para acelerar.

---

# 49. Criar em segundos

Fluxo ideal:

```text
Digite o resultado
↓
Confirme dono
↓
Escolha prazo
↓
Criar
```

Depois, dentro da atividade:

```text
adicionar contexto
tarefas
obra
centro de custo
```

se necessário.

---

# 50. Campos avançados

Podem ficar em:

```text
Mais opções
```

Exemplos:

```text
Empresa
Obra
Centro de custo
Tipo de atividade
Descrição
```

---

# 50.1 Processo na criação de atividade

Processo deve ser opcional no D0.

A criação rápida continua possível:

```text
O que precisa ser resolvido?
Dono
Prazo
Criar
```

Pode existir uma ação discreta:

```text
Usar processo
```

ou um seletor opcional de processo.

Ao selecionar um processo, a LPS deve mostrar apenas um resumo imediato:

```text
Processo: Elaborar orçamento
Entrega esperada: Proposta pronta para envio
Inputs: 3 obrigatórios + 1 opcional
Fluxo: 4 etapas
```

Não abrir todos os campos do processo dentro do formulário inicial da atividade.

Depois de criar, a atividade passa a mostrar inputs, output, critérios e fluxo de forma contextual.

---

# 51. Não obrigar obra

Já decidido.

---

# 52. Não obrigar centro de custo

Já decidido.

---

# 53. Não obrigar tipo se isso travar criação

Pode existir padrão:

```text
Outros
```

ou ser definido depois.

---

# 54. Não criar setor inline

Decisão consolidada:

> setor é criado em cadastro próprio.

Se não existir:

```text
Selecione um setor existente
```

Sem:

```text
+ criar setor agora
```

no D0.

---

# 55. Criar atividade sem tarefas

Permitido.

Após criar:

```text
atividade criada
↓
usuário pode adicionar tarefas
```

---

# 56. Sugestão imediata após criação

Tela pode mostrar:

```text
Atividade criada.

Próximo passo:
[Adicionar primeira tarefa]
```

---

# 57. Detalhe da atividade

Essa é uma das telas mais importantes da LPS.

Ela precisa responder:

- o que precisa ser resolvido;
- quem é o dono;
- qual prazo;
- qual status;
- quais tarefas;
- onde está;
- o que aconteceu;
- o que foi conversado.

---

# 58. Cabeçalho da atividade

Mostrar:

```text
Título
Status
Dono
Prazo
Empresa
Obra/centro de custo quando houver
```

---

# 59. Ações principais

Exemplo:

```text
Editar
Adicionar tarefa
Concluir
Mais ▾
```

Ações aparecem conforme permissão.

---

# 60. Abas ou seções do detalhe

Sugestão:

```text
Visão geral
Tarefas
Histórico
Conversa
```

---

# 61. Visão geral

Pode conter:

- objetivo;
- progresso;
- prazo;
- setores envolvidos;
- tarefas principais;
- situação atual;
- bloqueios;
- último evento.

---

# 62. Progresso

Evitar progresso falso baseado só em porcentagem de tarefas.

Exemplo:

```text
4 de 6 tarefas concluídas
```

é melhor que:

```text
67%
```

quando tarefas possuem pesos diferentes.

---

# 63. Situação atual

Exemplo:

```text
Compras
Aguardando execução
Posição 4 de 17
Prazo comprometido: hoje 16h
```

---

# 64. A atividade pode ter várias tarefas em paralelo

A visão geral deve conseguir mostrar isso sem fingir um único “setor atual”.

---

# 65. Tarefas da atividade

Lista clara.

Exemplo:

```text
✓ Gerar lista
✓ Validar especificação
● Comprar material
○ Realizar pagamento
○ Receber material
```

---

# 66. Símbolos precisam ter texto

Não depender apenas de cor.

---

# 67. Tarefa

Cada tarefa precisa mostrar:

```text
Título
Setor
Status
Executor(es)
Prazo
Posição na fila quando aplicável
```

---

# 68. Detalhe da tarefa

Pode abrir:

```text
painel lateral
```

no desktop.

No mobile:

```text
tela própria
```

---

# 69. Objetivo do detalhe da tarefa

Responder:

- o que fazer;
- onde está;
- quem executa;
- prazo;
- dependências;
- posição;
- tempo;
- conversa;
- histórico.

---

# 70. Ações rápidas da tarefa

Conforme estado:

```text
Assumir
Iniciar
Pausar
Retomar
Devolver
Concluir
```

---

# 71. Uma ação principal por vez

Evitar mostrar seis botões com o mesmo destaque.

Exemplo:

Se tarefa está pronta para iniciar:

```text
[INICIAR]
```

é a ação principal.

Outras ficam em:

```text
Mais
```

---

# 72. Tarefa sem executor

Mostrar:

```text
Sem executor
```

Ações possíveis:

```text
Assumir
Atribuir
```

dependendo da permissão.

---

# 73. Tarefa com vários executores

Mostrar avatares ou nomes compactos.

Exemplo:

```text
Ryan + Jennifer +1
```

---

# 74. Tarefa bloqueada

Mostrar:

```text
Bloqueada
Aguardando fornecedor
Desde ontem 14:20
```

---

# 75. Tarefa devolvida

Mostrar:

```text
Devolvida para Engenharia
Motivo: especificação incompleta
```

---

# 76. Dependências

Mostrar de forma simples:

```text
Aguardando:
✓ Gerar quantitativo
○ Aprovação técnica
```

---

# 77. Não obrigar usuário a entender fluxograma

A interface deve traduzir dependência em linguagem simples.

---

# 78. Fluxo visual

Pode existir uma visualização leve.

Exemplo:

```text
Engenharia → Compras → Financeiro → Almoxarifado
```

---

# 79. Fluxo real

Se houver retorno:

```text
Engenharia
↓
Compras
↓
Engenharia
↓
Compras
```

O histórico mostra caminho real.

---

# 80. Editor de fluxo

No D0, evitar editor visual complexo.

Pode ser:

```text
lista ordenável de tarefas
```

---

# 81. Adicionar tarefa

Formulário simples:

```text
O que precisa ser feito?
Setor
Prazo
Executor opcional
```

---

# 82. Criar várias tarefas rapidamente

No desktop, pode existir ação:

```text
+ Adicionar outra
```

sem fechar modal.

---

# 83. Tarefa pode ser criada sem executor

Já definido.

---

# 84. Tarefa pode ser criada sem prazo

Permitido quando processo não exige.

---

# 85. Reordenar fluxo da atividade

Pessoa autorizada pode arrastar tarefas.

Toda alteração é auditada.

---

# 86. Diferenciar fluxo de fila

Essa diferença precisa ser clara na UX.

Fluxo:

```text
ordem/dependência dentro da atividade
```

Fila:

```text
ordem de execução do setor
```

---

# 87. Fila do setor

Essa é outra tela central.

Precisa ser extremamente fácil de usar.

---

# 88. Objetivo da fila

Responder:

> O que o setor executa agora e em que ordem?

---

# 89. Cabeçalho da fila

Mostrar:

```text
Setor
Quantidade ativa
Em execução
Aguardando
Bloqueadas
```

---

# 90. Lista principal

Exemplo:

```text
1  Receber 50 bobinas
2  Separar material obra X
3  Carregar caminhão
4  Disponibilizar veículo
5  Conferir estoque
```

---

# 91. Dados por item na visão interna

Exemplo:

```text
Título
Dono da atividade
Prazo solicitado
Prazo comprometido
Tempo em fila
Executor
Status
```

---

# 92. Não exagerar em colunas

Desktop pode permitir escolher colunas.

D0:

```text
ordem
tarefa
prazo
tempo na fila
responsável
status
```

é suficiente.

---

# 93. Reordenar

Gestor ou autorizado:

```text
arrastar e soltar
```

ou usar:

```text
Mover para posição...
```

---

# 94. Alteração rápida

Não exigir formulário completo a cada movimento.

---

# 95. Motivo de reordenação

Se a regra exigir:

```text
Motivo da mudança
```

pode aparecer após soltar.

---

# 96. Mudança pequena x grande

No futuro, motivo pode ser exigido apenas em mudanças relevantes.

---

# 97. Usuário externo ao setor

Não vê a fila completa.

Vê apenas:

```text
Sua posição:
4 de 17
```

---

# 98. Tela do solicitante

Exemplo:

```text
Almoxarifado

Sua tarefa:
Disponibilizar veículo

Posição:
4 de 17

Prazo comprometido:
Hoje 17h

Status:
Aguardando execução
```

---

# 99. Não mostrar títulos das outras tarefas

Essa regra precisa estar refletida na interface.

---

# 100. Mudança de posição

A tela mostra histórico compacto:

```text
09:00  4 de 17
11:20  7 de 19
13:10  16 de 18
```

---

# 101. Timer

O timer precisa ser uma das funções mais simples do sistema.

---

# 102. Ação iniciar

Botão grande:

```text
INICIAR
```

---

# 103. Após iniciar

Mostrar:

```text
01:14:32
```

com:

```text
PAUSAR
CONCLUIR
```

---

# 104. Timer persistente

Enquanto houver tarefa ativa, mostrar em lugar persistente.

Desktop:

```text
barra superior ou inferior
```

Mobile:

```text
barra fixa
```

---

# 105. Trocar de tarefa

Se usuário iniciar outra tarefa:

```text
A tarefa atual será pausada.
```

Confirmar quando necessário.

---

# 106. Uma pessoa, uma sessão ativa

A interface deve refletir essa regra.

---

# 107. Pausa

Ao pausar:

```text
timer para
```

A tarefa continua aberta.

---

# 108. Retomar

Botão:

```text
RETOMAR
```

---

# 109. Pausas curtas

A UX final de café/banheiro/almoço ainda precisa de decisão.

Não criar complexidade no D0.

---

# 110. Apropriação manual

Pode existir ação:

```text
Adicionar tempo
```

para usuários autorizados.

---

# 111. Tempo manual precisa ser identificado

Tela deve indicar:

```text
Lançado manualmente
```

---

# 112. Histórico de tempo

Exemplo:

```text
08:00–09:10  1h10
11:20–12:00  40min
Total        1h50
```

---

# 113. Vários executores

Cada pessoa vê o próprio timer.

No detalhe:

```text
Horas-homem totais:
4h20
```

---

# 114. Concluir tarefa com timer ativo

Ao concluir:

```text
finalizar sessão atual
↓
concluir tarefa
```

em uma única ação.

---

# 115. Devolver tarefa

Fluxo simples:

```text
[DEVOLVER]
↓
Destino
↓
Motivo
↓
Observação
↓
Confirmar
```

---

# 116. Destino

Preferir opções válidas do fluxo.

Não lista gigante sem contexto.

---

# 117. Motivo obrigatório

Exemplo:

```text
Especificação incompleta
```

---

# 118. Observação

Pode ser obrigatória conforme motivo/configuração.

Exemplo:

```text
Faltou informar a bitola do cabo.
```

---

# 119. Concluir tarefa

Ação simples:

```text
[CONCLUIR]
```

Se houver pendência:

```text
Esta tarefa possui bloqueio ativo.
Deseja resolver antes?
```

conforme regra.

---

# 120. Concluir atividade

A atividade deve deixar claro o resultado.

Exemplo:

```text
Confirmar conclusão:
Material está disponível na obra?
```

---

# 121. Confirmação de resultado

Evitar botão genérico:

```text
Fechar
```

Preferir linguagem relacionada ao resultado.

---

# 122. Histórico

A tela de histórico precisa mostrar:

> O que aconteceu e quando?

---

# 123. Linha do tempo

Exemplo:

```text
10/09 08:00  Atividade criada
10/09 10:17  Ryan iniciou
10/09 11:37  Enviada para Compras
11/09 10:30  Devolvida para Engenharia
11/09 11:55  Reenviada
...
```

---

# 124. Histórico não deve parecer log técnico

Evitar:

```text
UPDATE tarefa_id 8294 status 4→5
```

Mostrar linguagem humana.

---

# 125. Detalhe técnico opcional

Gestor/auditor pode abrir:

```text
Ver detalhes
```

---

# 126. Filtros no histórico

Exemplos:

```text
Todos
Tarefas
Prazos
Fila
Devoluções
Tempo
```

---

# 127. Histórico de fila

Mostrar mudanças de posição.

---

# 128. Histórico de prazo

Mostrar:

```text
Solicitado
Proposto
Aceito
Recusado
```

---

# 129. Histórico de executor

Mostrar:

```text
Ryan atribuído
Jennifer adicionada
Ryan removido
```

---

# 130. Histórico de dono

Mostrar:

```text
Paulo → Rian
```

quando houver mudança.

---

# 131. Conversa

A conversa precisa parecer integrada ao trabalho.

---

# 132. Conversa da atividade

Aba:

```text
Conversa
```

com mensagens gerais.

---

# 133. Conversa da tarefa

Dentro da tarefa:

```text
Conversa da tarefa
```

---

# 134. Contexto visível

Antes do campo de mensagem:

```text
Você está comentando em:
Tarefa — Cotação de cabos
```

---

# 135. Campo de mensagem

Simples:

```text
Escreva uma mensagem...
```

---

# 136. Menção

Suportar:

```text
@nome
```

---

# 137. Mensagem não muda processo

A interface pode reforçar.

Exemplo:

Se usuário escreve:

```text
"Consigo sexta."
```

o sistema não muda prazo.

---

# 138. Ações estruturadas próximas da conversa

Pode existir botão:

```text
Propor novo prazo
```

ao lado, para transformar decisão em dado formal.

---

# 139. Mensagens automáticas

Exemplo:

```text
LPS
Prazo comprometido alterado para 18/09 às 15h.
```

---

# 140. Não mostrar cada evento automático

Somente eventos úteis para entendimento.

---

# 141. Conversa no mobile

Precisa ser muito rápida.

Abrir, responder e voltar à atividade.

---

# 142. Notificações

A central precisa responder:

> O que mudou e eu preciso saber?

---

# 143. Ícone de notificações

Exemplo:

```text
🔔 5
```

Visual final pode mudar.

---

# 144. Lista de notificações

Exemplo:

```text
AÇÃO NECESSÁRIA
Novo prazo proposto

INFORMATIVO
Sua posição mudou para 3 de 14

AÇÃO NECESSÁRIA
Tarefa devolvida
```

---

# 145. Diferenciar notificação informativa de acionável

Esse é um princípio importante.

---

# 146. Ação necessária

Pode conter botão:

```text
Analisar
```

---

# 147. Abrir no ponto correto

Notificação de prazo:

```text
abre seção de prazo
```

Notificação de devolução:

```text
abre tarefa
```

---

# 148. Filtros da central

Inicialmente:

```text
Todas
Não lidas
Ação necessária
```

---

# 149. Outros filtros

Depois:

```text
Menções
Prazos
Filas
Escalonamentos
```

---

# 150. Marcar como lida

Individual ou em lote.

---

# 151. Lida não significa resolvida

Se exige ação, pode continuar em:

```text
Pendentes
```

---

# 152. Posição alterada

Notificação exemplo:

```text
Almoxarifado
Sua posição mudou de 4 de 17 para 16 de 18.
```

---

# 153. Prazo proposto

Exemplo:

```text
Novo prazo:
18/09 às 15h

[ACEITAR]
[RECUSAR]
```

---

# 154. Recusa

Pode pedir:

```text
Motivo da recusa
```

quando configurado.

---

# 155. Escalonamento

Notificação precisa destacar:

```text
Conflito de prazo
```

e quem precisa decidir.

---

# 156. Conclusão

Dono recebe:

```text
Atividade concluída:
Material disponível na obra.
```

---

# 157. Visão do gestor

O gestor não deve precisar abrir 50 atividades para entender sua área.

---

# 158. Perguntas principais da visão do gestor

- Qual tamanho da fila?
- O que está atrasado?
- O que está bloqueado?
- Onde existe conflito?
- Onde existe devolução?
- Quem está sobrecarregado?
- Qual atividade está parada?
- Qual prazo está em risco?

---

# 159. Tela inicial do gestor

Sugestão de blocos:

```text
Fila
Atrasos
Bloqueios
Escalonamentos
Capacidade
Gargalos
```

---

# 160. Evitar dashboard decorativo

Cada bloco precisa permitir decisão.

---

# 161. Exemplo — fila

```text
Compras
47 tarefas
+12 na semana
```

Ação:

```text
[Ver fila]
```

---

# 162. Exemplo — atrasos

```text
8 tarefas atrasadas
3 acima de 2 dias
```

---

# 163. Exemplo — bloqueios

```text
6 aguardando cliente
4 aguardando fornecedor
2 aguardando decisão
```

---

# 164. Exemplo — escalonamentos

```text
3 aguardando sua decisão
```

---

# 165. Exemplo — capacidade

No D0, não precisa de cálculo sofisticado.

Pode mostrar:

```text
Entraram 25 hoje
Concluídas 18
Fila atual 47
```

---

# 166. Visão de pessoas

Gestor pode ver:

```text
Em execução
Carga de tarefas
Tempo registrado
```

Mas não criar ranking simplista.

---

# 167. Evitar “melhor funcionário”

Não transformar tempo em competição.

---

# 168. Identificar concentração

Exemplo:

```text
82% das tarefas deste tipo estão com Jennifer
```

isso é mais útil que ranking.

---

# 169. Atividades paradas

Mostrar:

```text
Sem ação há 3 dias
```

---

# 170. Drill-down

Gestor clica no indicador e abre os casos.

---

# 171. Filtros gerenciais

```text
Setor
Empresa
Obra
Período
Tipo
```

---

# 172. Desktop do gestor

Pode ter maior densidade.

---

# 173. Mobile do gestor

Priorizar exceções:

```text
3 atrasos
2 escalonamentos
1 bloqueio crítico
```

---

# 174. Cadastros

Cadastros são administrativos.

Não devem poluir a experiência diária.

---

# 175. Área Cadastros

Submenus consolidados:

```text
Processos
Setores
Empresas
Obras
Centros de custo
Tipos de atividade
Tipos de tarefa
Motivos
```

Itens aparecem conforme autorização.

---

# 175.1 Tela de Processos

`Cadastros > Processos` é uma página completa.

Objetivo:

> localizar, visualizar, criar, versionar, duplicar e inativar processos reutilizáveis.

A tabela pode mostrar:

```text
Nome
Tipo de atividade
Inputs
Output
Fluxo
Versão publicada
Status
Ações
```

Ações rápidas:

```text
Visualizar
Editar rascunho
Criar nova versão
Duplicar
Inativar
```

No topo:

```text
+ Novo processo
```

---

# 175.2 Novo processo em modal grande

Ao clicar em `+ Novo processo`, abrir um **modal grande**, ocupando aproximadamente 85% a 90% da largura e até 90% da altura útil no desktop.

O objetivo é manter o usuário dentro do contexto de Cadastros sem transformar o formulário em uma página longa e perdida na navegação.

Estrutura:

```text
Cabeçalho fixo
Novo processo
Descrição curta
[X]

Conteúdo com rolagem interna

Rodapé fixo
Cancelar | Salvar rascunho | Publicar versão
```

A rolagem deve acontecer dentro do modal.

Cabeçalho e ações finais permanecem visíveis.

---

# 175.3 Estrutura visual do cadastro de processo

Dentro do modal:

```text
1. Informações básicas — incluindo empresa
2. Inputs — o que preciso receber
3. Output — o que precisa ser entregue
4. Critérios de aceite — como sei que está pronto
5. Fluxo padrão — tarefas e setores
```

As seções devem usar cartões claros e progressivos.

O usuário não precisa preencher tudo antes de salvar rascunho.

---

# 175.4 Não empilhar modais

Ao editar inputs, output, critérios ou fluxo dentro de `Novo processo`, evitar abrir um segundo modal por cima do primeiro.

Preferir uma destas abordagens dentro do mesmo modal:

- expandir a seção;
- trocar o conteúdo interno com ação `Voltar`;
- abrir painel lateral interno;
- editar diretamente na seção.

Regra:

> um modal grande pode conter um fluxo complexo; vários modais empilhados aumentam perda de contexto.

---

# 175.5 Inputs no cadastro de processo

Mostrar lista atual e ação de adicionar.

Cada input pode ter:

```text
Nome
Tipo
Obrigatório
Origem
Ajuda de preenchimento
Ordem
```

A maior parte da configuração deve ser clicável:

- seletor de tipo;
- alternador de obrigatório;
- seletor de origem;
- arrastar para ordenar.

Reduzir digitação livre ao nome e à orientação necessária.

---

# 175.6 Output no cadastro de processo

A seção precisa responder visualmente:

> O que exatamente deve existir ao final?

Campos mínimos:

```text
Entrega esperada
Tipo de evidência
Descrição complementar opcional
```

Mostrar uma prévia de como essa entrega aparecerá na atividade.

---

# 175.7 Critérios de aceite

A seção precisa responder:

> Como a LPS sabe que o output está realmente pronto?

Cada critério:

```text
Nome
Obrigatório para concluir
Tipo de validação
Ordem
```

No D0, priorizar:

```text
Checklist simples
Evidência
```

---

# 175.8 Fluxo padrão

O fluxo do processo representa tarefas padrão, não novas atividades.

Exemplo visual:

```text
1 Levantamento
→
2 Cotação
→
3 Precificação
→
4 Revisão
```

Cada cartão mostra no mínimo:

```text
Tarefa
Setor responsável
Obrigatória ou opcional
```

Permitir arrastar para reordenar no desktop.

Não criar editor BPMN — Business Process Model and Notation, ou Notação e Modelagem de Processos de Negócio — completo no D0.

---

# 175.9 Publicação e versão

Enquanto estiver em rascunho:

```text
Editar livremente
```

Ao publicar:

```text
Versão 1 publicada
```

Depois, alterações estruturais devem gerar:

```text
Criar nova versão
```

A interface deve explicar isso antes de o usuário editar uma versão já utilizada.

---

# 176. Cadastro de setor

Tela simples:

```text
Nome
Empresa
Código opcional
Ativo
```

Pode abrir em modal pequeno ou médio, pois é um cadastro curto.

---

# 177. Duplicidade

Ao salvar `Financeiro`, se já existe `financeiro`, mostrar:

```text
Já existe um setor com este nome.
```

---

# 178. Não sugerir similaridade automaticamente

`Financeiro` e `Financeiro e Administrativo` podem coexistir.

---

# 179. Cadastro de obra

Campos essenciais.

Não copiar dezenas de campos de ERP sem necessidade.

---

# 180. Cadastro de centro de custo

Pode permitir associação opcional à obra.

---

# 181. Tipo de atividade

Cadastro simples:

```text
Nome
Descrição
Ativo
```

Tipo de atividade é classificação. Não é processo e não carrega sozinho um fluxo completo.

---

# 182. Motivos

`Motivos` pode ser uma única tela com abas:

```text
Devolução
Bloqueio
```

Cada item:

```text
Nome
Descrição
Ativo
```

---

# 183. Inativação

Preferir `Inativar` em vez de `Excluir` para cadastros em uso.

---

# 184. Impacto da inativação

Mostrar impacto antes da confirmação quando relevante.

---

# 185. Configurações

Configurações são diferentes de cadastros.

```text
Cadastro = o que existe
Configuração = como a LPS se comporta
```

---

# 186. Área Configurações

Submenus consolidados:

```text
Organização
Notificações
Escalonamento
Calendário de trabalho
```

Integrações entram quando houver integração real.

---

# 187. Fluxos deixam de ser menu isolado

Fluxo padrão pertence ao cadastro de processo.

Não criar submenu `Fluxos` separado no D0.

Isso evita que o usuário configure um fluxo sem entender qual input e qual output ele atende.

---

# 188. Processo precisa unir as duas pontas

A experiência deve reforçar:

```text
O que entra?
↓
O que acontece?
↓
O que sai?
↓
Como valido?
```

---

# 189. Arrastar tarefas

Permitir reordenação visual dentro do fluxo do processo.

---

# 190. Dependência

Pode ser configurada de forma simples:

```text
Esta tarefa depende de:
[Selecionar tarefa]
```

---

# 191. Paralelismo

Se duas tarefas não dependem entre si, podem ser executadas em paralelo.

A interface pode representar isso sem diagrama avançado.

---

# 192. Regras de notificação

Tela deve evitar complexidade excessiva.

Exemplo:

```text
Evento:
Atividade concluída

Destinatário:
Dono

Obrigatória:
Sim
```

---

# 193. Preferências pessoais

Usuário pode configurar:

```text
Menções
Posição
Mensagens
Conclusões
```

dentro do que for opcional.

---

# 194. Regras de escalonamento

Exemplo simples:

```text
Quando:
Prazo recusado

Escalar para:
Gestor do setor
+
Gestor do dono
```

---

# 195. Evitar construtor de regras complexo no D0

Não criar:

```text
IF X AND Y OR Z THEN...
```

sem necessidade.

---

# 196. Permissões

A tela de permissões precisa ser poderosa, mas compreensível.

---

# 197. Objetivo

Responder:

> O que este perfil pode fazer?

---

# 198. Tela de perfil

Exemplo:

```text
Perfil:
Gestor Comercial
```

Grupos:

```text
Atividades
Tarefas
Filas
Prazos
Cadastros
Segurança
Auditoria
```

---

# 199. Dentro do grupo

Exemplo:

```text
Filas

[x] Visualizar
[x] Visualizar fila completa
[x] Reordenar
```

---

# 200. Busca de permissões

Campo:

```text
Buscar ação...
```

Essencial quando quantidade crescer.

---

# 201. Não mostrar códigos técnicos como principal

Mostrar:

```text
Reordenar fila
```

e, opcionalmente:

```text
fila.reordenar
```

em detalhe.

---

# 202. Descrição da permissão

Exemplo:

```text
Permite alterar a ordem das tarefas da fila nos setores autorizados.
```

---

# 203. Escopo

Após definir perfil:

```text
Onde vale?
```

Exemplo:

```text
Empresa:
Biasi Engenharia

Setor:
Comercial
```

---

# 204. Usuário com vários perfis

Tela do usuário pode mostrar:

```text
Gestor Comercial — Comercial
Visualizador — Administrativo
```

---

# 205. Exceções individuais

Mostrar em seção própria:

```text
Permissões adicionais
```

para não confundir com perfil.

---

# 206. Origem da permissão

Futuramente:

```text
Permitido via:
Gestor Comercial
```

isso ajuda muito suporte.

---

# 207. Cadastro de usuário

Fluxo simples:

```text
Nome
E-mail
Empresa(s)
Setor(es)
Perfil(is)
Ativar
```

---

# 208. Setor principal

Pode ser selecionado.

---

# 209. Vários setores

Interface multi-seleção.

---

# 210. Participação x acesso

A tela precisa deixar isso claro.

Exemplo:

```text
Setores em que atua
```

separado de:

```text
Acessos adicionais
```

---

# 211. Evitar confusão

Não misturar:

```text
Participa do Financeiro
```

com:

```text
Pode visualizar Financeiro
```

---

# 212. Inativar usuário

Mostrar:

```text
Este usuário possui 8 tarefas abertas.
```

Ação:

```text
Reatribuir antes de inativar
```

---

# 213. Tarefas órfãs

A UX precisa impedir que desligamento deixe tarefas perdidas.

---

# 214. Dono inativado

Mostrar atividades sob responsabilidade e exigir reatribuição.

---

# 215. Configuração inicial da organização

Fluxo ideal de onboarding:

```text
1. Empresa
2. Setores
3. Usuários
4. Perfis
5. Começar a usar
```

---

# 216. Não configurar tudo no onboarding

Evitar exigir:

- modelos de fluxo;
- escalonamento;
- dezenas de tipos;
- notificações avançadas;

antes da primeira atividade.

---

# 217. Configuração progressiva

A empresa começa simples.

Depois amadurece.

---

# 218. Empty states

Telas vazias precisam orientar.

Exemplo:

```text
Você ainda não possui atividades.
[CRIAR PRIMEIRA ATIVIDADE]
```

---

# 219. Outro exemplo

Fila vazia:

```text
Nenhuma tarefa aguardando neste setor.
```

---

# 220. Evitar tela vazia sem orientação

---

# 221. Feedback imediato

Após ação:

```text
Tarefa iniciada.
```

```text
Prazo enviado para aprovação.
```

```text
Tarefa devolvida.
```

Mensagens curtas.

---

# 222. Uso de modais

Modal não é ruim por definição. O problema é usar modal pequeno para fluxo grande ou empilhar vários níveis.

Usar modal grande para:

- criar ou editar processo;
- cadastrar usuário com várias seções;
- configurações administrativas autocontidas;
- ações que precisam preservar visualmente a tela de origem.

Usar modal pequeno ou médio para:

- devolução;
- bloqueio;
- confirmação sensível;
- cadastro curto.

Usar inline para microações:

- marcar critério;
- trocar filtro;
- ordenar;
- ativar/desativar opção simples.

## Regra do modal grande

No desktop:

```text
Largura aproximada: 85% a 90% da viewport
Altura máxima: aproximadamente 90% da viewport
Cabeçalho: fixo
Conteúdo: rolagem interna
Rodapé de ações: fixo
```

`Viewport` é a área visível da janela do navegador.

No mobile, fluxos grandes devem usar tela inteira ou painel de tela inteira.

Evitar modal sobre modal.

---

# 223. Confirmação

Não perguntar:

```text
Tem certeza?
```

em toda ação.

Reservar para:

- cancelar;
- inativar;
- concluir atividade;
- reabrir;
- ações sensíveis.

---

# 224. Undo

Quando possível, preferir desfazer.

Exemplo futuro:

```text
Executor removido. [DESFAZER]
```

---

# 225. Erros

Mensagem precisa dizer:

- o que ocorreu;
- como corrigir.

Exemplo ruim:

```text
Erro 422.
```

Exemplo melhor:

```text
Esta tarefa já foi concluída por outro usuário.
Atualize a página.
```

---

# 226. Concorrência

Se duas pessoas alterarem a fila:

```text
A fila mudou desde que você abriu.
Atualizamos a ordem.
```

---

# 227. Offline

No mobile, comportamento offline pode vir futuramente.

Não prometer D0 sem necessidade.

---

# 228. Velocidade

Telas principais precisam carregar rapidamente.

Prioridade:

```text
Home
Minhas atividades
Fila
Detalhe
Notificações
```

---

# 229. Skeleton loading

Pode ser usado para evitar sensação de travamento.

---

# 230. Não bloquear tela inteira por ação pequena

Exemplo:

Enviar mensagem não deve travar toda atividade.

---

# 231. Realtime

Mudanças como:

- fila;
- mensagem;
- notificação;
- status;

podem aparecer em tempo próximo do real.

---

# 232. Posição em tempo real

Se a fila muda, o solicitante não precisa atualizar manualmente.

---

# 233. Timer local + servidor

UX deve manter contagem fluida.

Servidor continua sendo referência de tempo.

---

# 234. Visual de estado

Usar combinação de:

- texto;
- ícone;
- cor.

Nunca apenas cor.

---

# 235. Acessibilidade

Considerar:

- contraste;
- tamanho de toque;
- teclado;
- leitores de tela;
- foco;
- estados.

---

# 236. Botões no mobile

Área de toque confortável.

---

# 237. Linguagem

Usar português simples.

Evitar termos técnicos desnecessários.

---

# 238. Exemplo

Em vez de:

```text
Alterar state da entity
```

usar:

```text
Alterar status da tarefa
```

---

# 239. SLA

Se futuramente aparecer na interface, explicar:

```text
Prazo de atendimento
```

em vez de exigir que todo usuário conheça SLA.

---

# 240. WIP

Não usar sigla para usuário comum se não agregar.

---

# 241. Consistência de termos

Usar sempre:

```text
Atividade
Tarefa
Dono
Executor
Setor
Fila
Prazo solicitado
Prazo comprometido
```

---

# 242. Não alternar termos

Evitar:

```text
Responsável
Owner
Dono
Gestor do item
```

para o mesmo conceito.

---

# 243. Dono

O sistema deve usar uma palavra consistente.

Se “Dono” for adotado internamente, avaliar o rótulo de interface:

```text
Responsável pelo resultado
```

ou:

```text
Dono
```

Decisão de linguagem visual pode ser testada.

---

# 244. Executor

Mostrar:

```text
Executores
```

quando houver vários.

---

# 245. Setor

Não chamar de departamento em algumas telas e setor em outras.

---

# 246. Prazo solicitado

Rótulo claro:

```text
Precisa para
```

pode ser mais humano.

---

# 247. Prazo comprometido

Pode ser:

```text
Compromisso do setor
```

ou:

```text
Prazo confirmado
```

A nomenclatura final deve ser testada.

---

# 248. Tela de negociação de prazo

Precisa mostrar lado a lado:

```text
Solicitado:
Hoje 17h

Proposto:
Amanhã 10h
```

---

# 249. Ações

```text
Aceitar
Recusar
```

---

# 250. Motivo

Ao propor prazo:

```text
Novo prazo
Motivo opcional/obrigatório conforme regra
```

---

# 251. Não exigir reunião

O sistema deve permitir resolver negociação dentro do fluxo.

---

# 252. Escalonamento visual

Quando recusado:

```text
Prazo em conflito
Escalonado para Rodrigo
```

---

# 253. Decisão

Mostrar:

```text
Aguardando decisão
```

---

# 254. Após decisão

Exemplo:

```text
Decisão:
Manter prazo de amanhã 10h
```

---

# 255. Bloqueio

Ação:

```text
Marcar como bloqueada
```

---

# 256. Formulário de bloqueio

```text
Motivo
Observação
```

---

# 257. Desbloquear

Ação simples:

```text
Resolver bloqueio
```

---

# 258. Aguardando cliente

Não deve significar que a pessoa para de trabalhar em tudo.

A tarefa fica bloqueada/aguardando.

Usuário continua com outras tarefas.

---

# 259. Visão de backlog pessoal

Pode possuir:

```text
A fazer
Em execução
Pendentes
```

---

# 260. Pendentes

Podem ser:

- apropriação de tempo;
- resposta;
- decisão;
- atividade aguardando acompanhamento.

Não misturar tudo sem classificação.

---

# 261. "Aguardando cliente" não é tarefa ativa

Não deve ocupar timer.

---

# 262. Histórico de bloqueio

Mostrar início/fim.

---

# 263. Tela de métricas pessoais

Pode existir depois.

No D0, não é essencial.

---

# 264. Métricas pessoais não devem virar ranking

---

# 265. Visão de atividade pelo solicitante

Se atividade passa por outro setor, o dono vê:

- status;
- posição;
- prazo;
- setor;
- devoluções;
- conclusão.

---

# 266. Não expor fila alheia

Já definido.

---

# 267. Transparência sem invasão

Esse equilíbrio é um princípio de UX.

---

# 268. Contexto do gestor

Gestor do setor enxerga mais:

- fila completa;
- detalhes;
- responsáveis;
- prazos;
- capacidade.

---

# 269. Contexto da diretoria

Enxerga agregação.

Não precisa executar tudo.

---

# 270. Contexto do administrador

Enxerga configurações.

Não significa que deve operar atividades.

---

# 271. Páginas administrativas

Podem ficar em:

```text
Administração
```

ou:

```text
Configurações
```

dependendo da navegação final.

---

# 272. Não misturar administração e operação

Usuário operacional não deve navegar por telas de segurança sem necessidade.

---

# 273. Pesquisa global

Futuramente, campo:

```text
Buscar na LPS...
```

Pode encontrar:

- atividades;
- tarefas;
- obras;
- usuários.

Não é obrigatório no D0.

---

# 274. Comando rápido

Futuramente:

```text
Ctrl + K
```

para:

- criar atividade;
- buscar;
- abrir tarefa.

Pode aumentar produtividade no desktop.

---

# 275. D0 deve funcionar sem atalhos

---

# 276. Favoritos

Futuramente, pode fixar atividades importantes.

---

# 277. Recentes

Pode existir:

```text
Atividades recentes
```

na Home.

---

# 278. Lembretes

Notificações já cumprem boa parte dessa função.

Evitar módulo de lembretes separado no início.

---

# 279. Responsividade

Desktop e mobile devem compartilhar:

- dados;
- regras;
- permissões.

Somente apresentação muda.

---

# 280. Breakpoints

Decisão técnica do design system.

---

# 281. Tabelas no mobile

Converter para cartões.

---

# 282. Fila no mobile

Pode ser lista vertical.

Reordenar por gesto apenas para usuários autorizados.

---

# 283. Drag and drop no mobile

Precisa ser testado.

Alternativa:

```text
Mover para posição...
```

pode ser mais confiável.

---

# 284. Reordenação em desktop

Drag and drop é mais natural.

---

# 285. Criação rápida no mobile

Precisa ser ainda mais curta.

Sugestão:

```text
O que precisa ser resolvido?
Dono
Prazo
[Criar]
```

---

# 286. Captura por voz

Futuramente, pode ajudar.

Exemplo:

```text
Criar atividade: revisar orçamento da obra X para amanhã.
```

Mas não é D0.

---

# 287. IA na criação

Futuramente, LPS pode interpretar texto e sugerir campos.

Ainda precisa confirmação.

---

# 288. Exemplo futuro

Usuário digita:

```text
Entregar orçamento da GEHAKA até sexta
```

LPS sugere:

```text
Título: Entregar orçamento da GEHAKA
Prazo: sexta
```

---

# 289. Não depender de IA para criar atividade

O formulário manual precisa continuar ótimo.

---

# 290. Processos reutilizáveis

Trabalhos recorrentes podem utilizar processo publicado.

O processo pode carregar:

- inputs;
- output;
- critérios;
- tarefas padrão;
- setores;
- dependências simples.

---

# 291. Aplicar processo

Ação possível na criação:

```text
Usar processo
```

Ou:

```text
Processo
[Selecionar]
```

A versão publicada mais adequada fica registrada na atividade.

---

# 292. Não obrigar processo

Nova atividade pode começar sem processo.

Isso preserva velocidade e permite demandas ad hoc.

---

# 293. Atividade simples

Uma atividade com uma única tarefa deve continuar simples.

---

# 294. Não forçar árvore complexa

Estrutura visual principal:

```text
Atividade
↓
Tarefas
```

---

# 295. Sem subtarefas no D0

Evitar nível adicional.

---

# 296. Checklist

Pode ser futuro dentro da tarefa.

Não obrigatório.

---

# 297. Estado de “sem dados”

Quando métrica ainda não existe:

```text
Ainda não há dados suficientes.
```

---

# 298. Não mostrar zero enganoso

Exemplo:

```text
Tempo médio: 0h
```

quando nunca houve execução.

Melhor:

```text
Sem histórico.
```

---

# 299. Inteligência futura na interface

Quando entrar:

```text
Sugestão da LPS
```

precisa ser claramente separada de:

```text
Dado real
```

---

# 300. Exemplo

```text
Prazo comprometido:
18/09
```

```text
Sugestão da LPS:
20/09
```

não misturar.

---

# 301. Confiança

Pode mostrar:

```text
Baseado em 42 atividades semelhantes
```

---

# 302. Explicação

Ação:

```text
Por quê?
```

---

# 303. Recomendação acionável

Exemplo:

```text
Sugestão:
Antecipar compra em 1 dia.

[APLICAR]
[IGNORAR]
```

---

# 304. Aplicar exige confirmação humana

---

# 305. Inteligência não deve criar mudanças silenciosas

Princípio já consolidado.

---

# 306. Histórico da recomendação

Pode aparecer futuramente na timeline quando aplicada.

---

# 307. Design visual

A identidade final deve ser:

- profissional;
- limpa;
- sóbria;
- simples;
- moderna;
- com alta legibilidade.

---

# 308. Não parecer ERP antigo

Evitar:

- excesso de bordas;
- tabelas gigantes;
- telas densas;
- campos minúsculos;
- menus profundos.

---

# 309. Não parecer aplicativo infantil

Simplicidade não significa visual informal demais.

---

# 310. Densidade equilibrada

Desktop pode ser mais denso.

Mobile mais direto.

---

# 311. Cards

Usar onde ajudam hierarquia.

Não transformar tudo em card.

---

# 312. Tabelas

Usar em:

- fila;
- cadastros;
- permissões;
- gestão.

---

# 313. Formulários

Preferir:

```text
1 coluna
```

em tarefas simples.

---

# 314. Formulários avançados

Podem utilizar seções.

---

# 315. Progress disclosure

**Progressive disclosure**, ou revelação progressiva:

mostrar primeiro o essencial.

Exemplo:

```text
Título
Dono
Prazo
```

Depois:

```text
Mais opções
```

---

# 316. Esse princípio é central na criação de atividade

---

# 317. Defaults inteligentes

Exemplos:

```text
Dono = eu
Empresa = atual
Setor = meu setor quando aplicável
```

Usuário pode alterar.

---

# 318. Defaults não devem criar erro silencioso

Sempre mostrar valor assumido.

---

# 319. Autofill

Pode preencher:

```text
empresa atual
```

automaticamente.

---

# 320. Data rápida

Atalhos:

```text
Hoje
Amanhã
Próxima segunda
```

---

# 321. Data e hora

Só pedir hora quando realmente necessária.

---

# 322. Prazo sem hora

Pode ser tratado como fim do dia conforme regra futura.

A UX precisa tornar isso claro.

---

# 323. Usuário e setor

Seletores com busca.

---

# 324. Listas longas

Campo de busca dentro do seletor.

---

# 325. Histórico de recentes

Pode mostrar usuários/setores mais usados.

Futuro.

---

# 326. Validação inline

Mostrar erro no campo.

---

# 327. Salvar automaticamente

Para descrição e alguns campos, autosave pode ser útil.

Mas alterações sensíveis precisam de ação explícita.

---

# 328. Alterações sensíveis

Exemplos:

- dono;
- prazo;
- setor;
- fila;
- conclusão.

---

# 329. Edição de descrição

Pode salvar automaticamente.

---

# 330. Indicador de salvamento

```text
Salvo
```

discreto.

---

# 331. Evitar botão “Salvar” em toda microação

---

# 332. Tabela de cadastros

Ações:

```text
Buscar
Filtrar
Novo
Editar
Inativar
```

---

# 333. Tabela de permissões

Agrupável por grupo.

---

# 334. Tela de perfil

Pode ter:

```text
Ações
Escopos
Usuários vinculados
Histórico
```

---

# 335. Histórico de alteração de perfil

Importante para administrador.

---

# 336. Tela do usuário

Pode ter:

```text
Dados
Setores
Perfis
Acessos adicionais
Atividades abertas
Histórico de segurança
```

conforme permissão.

---

# 337. Não mostrar tudo para quem não pode ver

---

# 338. Onboarding de colaborador

Usuário comum não precisa passar por tutorial longo.

Pode existir:

```text
3 passos
1. Veja suas tarefas
2. Inicie o que está fazendo
3. Conclua quando terminar
```

---

# 339. Onboarding de gestor

Pode explicar:

```text
Fila
Prazo
Escalonamento
```

---

# 340. Onboarding do administrador

Pode explicar:

```text
Setores
Perfis
Ações
Escopos
```

---

# 341. Ajuda contextual

Ícone:

```text
?
```

com explicação curta.

---

# 342. Documentação extensa fora da tela

Não colocar parágrafos longos no formulário.

---

# 343. Tooltips

Úteis para termos como:

```text
Prazo solicitado
Prazo comprometido
```

---

# 344. Exemplo de tooltip

```text
Prazo solicitado:
quando quem pediu precisa da entrega.
```

---

# 345. Outro

```text
Prazo comprometido:
quando o setor responsável se compromete a entregar.
```

---

# 346. Página 404

Simples:

```text
Não encontramos esta página.
```

---

# 347. Acesso negado

Diferenciar de 404 quando apropriado:

```text
Você não possui acesso a este conteúdo.
```

---

# 348. Objeto removido/inativado

Mostrar mensagem clara.

---

# 349. Estado concorrente

Se atividade foi concluída por outro usuário:

```text
Esta atividade foi concluída enquanto você estava nesta tela.
```

---

# 350. Atualização em tempo real

Mostrar estado atualizado.

---

# 351. Mobile first para ações, desktop first para gestão

Esse pode ser um bom princípio de desenho.

---

# 352. Jornada principal do colaborador

```text
Abrir LPS
↓
Ver próxima tarefa
↓
Iniciar
↓
Trabalhar
↓
Pausar/retomar
↓
Concluir
↓
Próxima tarefa
```

---

# 353. Jornada principal do dono

```text
Criar atividade
↓
Acompanhar tarefas
↓
Ver posição/prazo
↓
Receber notificações
↓
Negociar se necessário
↓
Confirmar resultado
```

---

# 354. Jornada principal do gestor

```text
Abrir visão do setor
↓
Ver fila
↓
Identificar conflitos
↓
Reordenar quando necessário
↓
Resolver escalonamentos
↓
Acompanhar gargalos
```

---

# 355. Jornada principal do administrador

```text
Cadastrar estrutura
↓
Criar usuários
↓
Definir perfis
↓
Definir escopos
↓
Auditar alterações
```

---

# 356. Jornada — criar atividade

Passos máximos desejáveis:

```text
1. Abrir Nova atividade
2. Digitar resultado
3. Confirmar dono
4. Definir prazo
5. Criar
```

Idealmente:

```text
menos de 30 segundos
```

para caso simples.

---

# 357. Não medir UX apenas em cliques

Mais importante:

- clareza;
- velocidade;
- baixa chance de erro.

---

# 358. Jornada — criar tarefa

```text
1. Adicionar tarefa
2. Digitar o que fazer
3. Selecionar setor
4. Salvar
```

Executor e prazo podem ser opcionais.

---

# 359. Jornada — reordenar fila

```text
1. Abrir fila
2. Arrastar item
3. Informar motivo se exigido
4. Salvar automaticamente
```

---

# 360. Jornada — acompanhar fila

Solicitante:

```text
Abrir atividade
↓
ver 4 de 17
```

Sem abrir tela do setor.

---

# 361. Jornada — mudança de posição

```text
Fila muda
↓
LPS registra
↓
solicitante recebe notificação
↓
abre contexto se quiser
```

---

# 362. Jornada — renegociar prazo

```text
Setor identifica incompatibilidade
↓
Propor novo prazo
↓
Dono é notificado
↓
Aceita ou recusa
```

---

# 363. Jornada — recusa

```text
Recusa
↓
Escalonamento automático
↓
Gestores notificados
↓
Decisão registrada
```

---

# 364. Jornada — devolução

```text
Executor clica Devolver
↓
Seleciona motivo
↓
Adiciona observação
↓
Confirma
↓
responsável destino é notificado
```

---

# 365. Jornada — conclusão

```text
Última tarefa concluída
↓
atividade pronta para encerramento
↓
dono confirma resultado
↓
atividade concluída
↓
dono recebe confirmação
```

---

# 366. Possível automação futura

Atividades padronizadas podem concluir automaticamente.

Não é regra geral.

---

# 367. Histórico como “filme”

A UX pode trabalhar com essa metáfora internamente:

```text
Agora = fotografia
Histórico = filme
```

---

# 368. Tela atual não precisa mostrar tudo

A visão principal mostra estado atual.

Histórico explica passado.

---

# 369. Não misturar estado atual com histórico

Exemplo:

```text
Setor atual: Financeiro
```

separado de:

```text
Já passou por:
Engenharia → Compras → Engenharia → Compras
```

---

# 370. Indicadores

Quando existirem, precisam ser clicáveis.

Exemplo:

```text
3 devoluções
```

abre detalhes.

---

# 371. Métrica sem detalhe gera desconfiança

---

# 372. Inteligência futura

Mesma regra.

Exemplo:

```text
Risco alto de atraso
```

deve permitir:

```text
Por quê?
```

---

# 373. D0 — telas obrigatórias

A primeira versão deve possuir:

```text
Login
Home
Minhas atividades
Criar atividade
Detalhe da atividade
Detalhe da tarefa
Fila do setor
Timer
Histórico
Conversa
Notificações
Visão do gestor
Cadastros
Lista de processos
Modal grande de novo/editar processo
Configurações
Permissões
```

---

# 374. D0 — componentes essenciais

```text
Botão de criar atividade
Lista de atividades
Lista de tarefas
Timer persistente
Fila ordenável
Indicador de posição
Prazo solicitado
Prazo comprometido
Modal de devolução
Modal de bloqueio
Modal de prazo
Timeline
Chat contextual
Central de notificações
Matriz de permissões
Seções de input, output, critérios e fluxo do processo
```

---

# 375. O que pode ficar depois do D0

- dashboard avançado;
- personalização de Home;
- pesquisa global;
- comando Ctrl+K;
- IA na criação;
- resumo automático;
- voz;
- canais livres;
- chat privado;
- reactions;
- threads avançadas;
- editor visual de fluxo;
- offline completo;
- widgets customizáveis;
- atalhos avançados.

---

# 376. Não criar no D0

- menu com dezenas de módulos;
- criação inline de todos os cadastros;
- BPMN completo;
- permissões por campo;
- dashboard com vinte gráficos;
- central de analytics sofisticada;
- ranking de colaboradores.

---

# 377. Métrica de sucesso da UX

Perguntas:

- usuário consegue criar atividade sem treinamento?
- consegue descobrir o que fazer?
- consegue iniciar trabalho rapidamente?
- entende onde sua demanda está?
- gestor entende a fila?
- dono sabe quando algo mudou?
- permissões são compreensíveis?

---

# 378. Teste simples de criação

Entregar sistema para uma pessoa nova.

Pedir:

> Crie uma atividade para receber material amanhã.

Se ela precisar de explicação longa:

> a UX está complexa demais.

---

# 379. Teste simples de fila

Perguntar ao solicitante:

> Onde está sua demanda?

Ele deve conseguir responder:

```text
4 de 17 no Almoxarifado.
```

em poucos segundos.

---

# 380. Teste simples de executor

Perguntar:

> O que você está fazendo agora?

Ele deve conseguir iniciar o timer sem navegar em vários menus.

---

# 381. Teste simples de gestor

Perguntar:

> Qual problema precisa da sua atenção?

A visão do gestor deve mostrar.

---

# 382. Teste simples de segurança

Perguntar ao administrador:

> Por que Paulo vê o Administrativo?

Ele deve conseguir encontrar a origem da permissão.

---

# 383. Cenário 1 — atividade simples

Usuário:

```text
+ Nova atividade
```

Preenche:

```text
Resultado:
Picotar folhas

Dono:
Eu

Prazo:
Hoje
```

Cria.

Sem obra.

Sem centro de custo.

Sem formulário longo.

---

# 384. Cenário 2 — atividade de obra

```text
Resultado:
Material disponível na obra

Dono:
Engenheiro

Prazo:
20/09
```

Depois adiciona:

```text
Obra
Centro de custo
Tarefas
```

---

# 385. Cenário 3 — tarefa sem executor

```text
Tarefa:
Realizar cotação

Setor:
Compras

Executor:
Não definido
```

A tarefa entra na fila.

---

# 386. Cenário 4 — solicitante acompanha fila

Visualiza:

```text
Compras
4 de 17
```

Sem ver outras demandas.

---

# 387. Cenário 5 — posição piora

Recebe:

```text
Sua posição mudou para 16 de 18.
```

---

# 388. Cenário 6 — prazo incompatível

Executor abre tarefa.

Clica:

```text
Propor novo prazo
```

Define:

```text
terça 15h
```

Dono recebe notificação.

---

# 389. Cenário 7 — recusa

Dono recusa.

Tela mostra:

```text
Prazo em conflito.
Escalonado.
```

---

# 390. Cenário 8 — devolução

Compras devolve.

Engenharia recebe:

```text
Tarefa devolvida.
Motivo: especificação incompleta.
```

---

# 391. Cenário 9 — múltiplos executores

Tarefa mostra:

```text
Ryan
Jennifer
```

Cada um possui tempo individual.

---

# 392. Cenário 10 — gestor

Gestor vê:

```text
47 na fila
8 atrasadas
3 escalonamentos
6 bloqueadas
```

---

# 393. Cenário 11 — usuário com acesso cruzado

Paulo:

```text
Comercial
```

mas visualiza:

```text
Administrativo
```

Tela permite consulta.

Não mostra ações que ele não possui.

---

# 394. Cenário 12 — usuário inativo

Administrador abre usuário.

Sistema mostra:

```text
8 tarefas abertas
3 atividades como dono
```

antes de inativar.

---

# 395. Decisões consolidadas neste documento

## Experiência geral

- simples;
- rápida;
- desktop + mobile;
- pouca digitação;
- dados capturados automaticamente;
- menus conforme permissão.

## Criação de atividade

- extremamente rápida;
- poucos campos iniciais;
- dono;
- prazo;
- resultado;
- campos adicionais depois;
- obra e centro de custo opcionais;
- sem criação inline de setor no D0.

## Home

- orientada à ação;
- colaborador vê trabalho atual;
- gestor vê exceções;
- evitar dashboard decorativo.

## Atividades

- lista simples;
- filtros básicos;
- estado atual claro;
- atraso visível;
- busca.

## Tarefas

- ações rápidas;
- executor opcional inicialmente;
- vários executores suportados;
- dependências simples;
- detalhe próprio.

## Timer

- persistente;
- iniciar, pausar, retomar e concluir;
- uma sessão ativa por pessoa;
- lançamento manual distinguível.

## Fila

- por setor;
- ordenável;
- posição exata;
- solicitante vê própria posição;
- solicitante não vê fila completa;
- mudanças notificáveis;
- reordenação simples.

## Prazo

- solicitado separado de comprometido;
- proposta clara;
- aceite/recusa;
- conflito visível;
- escalonamento integrado.

## Devolução

- destino;
- motivo obrigatório;
- observação;
- notificação;
- histórico.

## Histórico

- linguagem humana;
- timeline;
- filtros;
- estado atual separado de passado.

## Comunicação

- atividade e tarefa possuem conversa;
- mensagem não muda estado;
- menções;
- sistema pode publicar eventos relevantes.

## Notificações

- central interna;
- informativa x ação necessária;
- deep link;
- conclusão sempre chega ao dono.

## Gestor

- foco em fila, atraso, bloqueio, conflito e capacidade;
- gestão por exceção;
- sem ranking simplista.

## Cadastros

- área própria;
- simples;
- inativação;
- sem excesso de campos.

## Configurações

- fluxos;
- notificações;
- escalonamentos;
- comportamento configurável sem motor complexo no D0.

## Permissões

- grupos de ações;
- busca;
- escopo claro;
- origem da permissão;
- participação em setor separada de acesso.

---

# 396. Decisões ainda pendentes

Precisam ser detalhadas durante prototipação:

1. nomenclatura visual final de “dono”;
2. nomes finais dos status;
3. localização exata do timer persistente;
4. formato final da Home;
5. forma de reordenação no mobile;
6. se tarefa em execução continua numerada na fila;
7. comportamento visual de bloqueadas na fila;
8. se atividade conclui automaticamente em algum caso;
9. campos exatos do formulário rápido;
10. se tipo de atividade será obrigatório;
11. se push entra no D0;
12. política de anexos;
13. política de edição de mensagens;
14. componentes finais de métricas;
15. identidade visual final.

---

# 397. Relação com os demais documentos

## `01_VISAO_E_PRINCIPIOS_LPS.md`

Define a filosofia do produto.

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Define o que a interface precisa representar.

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Define fila, negociação de prazo e conflito.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

Define timer, histórico e métricas.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Define quais telas, ações e dados cada usuário pode acessar.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Define conversa e notificações.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Define como futuras sugestões aparecerão sem se confundir com fatos.

## `08_BANCO_DE_DADOS.md`

Define como as ações da interface são persistidas.

---

# 398. Mapa resumido das telas

```text
LOGIN
↓
HOME
├── Minhas atividades
├── Minhas tarefas
├── Fila
├── Notificações
└── Gestão

ATIVIDADE
├── Visão geral
├── Tarefas
├── Histórico
└── Conversa

TAREFA
├── Detalhe
├── Timer
├── Prazo
├── Fila
├── Histórico
└── Conversa

ADMINISTRAÇÃO
├── Cadastros
├── Configurações
├── Usuários
├── Perfis
└── Permissões
```

---

# 399. Fluxo principal do produto

```text
ENTRAR
↓
VER O QUE PRECISA DE ATENÇÃO
↓
CRIAR OU ASSUMIR ATIVIDADE/TAREFA
↓
INICIAR
↓
EXECUTAR
↓
PAUSAR/RETOMAR
↓
MOVIMENTAR / DEVOLVER / NEGOCIAR
↓
CONCLUIR
↓
AUDITORIA É GERADA AUTOMATICAMENTE
↓
NOTIFICAÇÕES SÃO DISTRIBUÍDAS
↓
GESTOR ENXERGA EXCEÇÕES
↓
HISTÓRICO ALIMENTA MÉTRICAS
```

---

# 400. Regra de ouro da UX

> **A pessoa precisa trabalhar na LPS, não trabalhar para a LPS.**

---

# 401. Regra de ouro da criação

> **Criar uma atividade simples deve levar segundos, não minutos.**

---

# 402. Regra de ouro da execução

> **O usuário deve enxergar claramente qual é a próxima ação disponível.**

---

# 403. Regra de ouro da fila

> **Quem pede precisa enxergar onde está; quem executa precisa organizar; quem gerencia precisa decidir.**

---

# 404. Regra de ouro da transparência

> **Mostrar o suficiente para dar previsibilidade, sem expor informação que o usuário não precisa ver.**

---

# 405. Regra de ouro do histórico

> **O estado atual deve ser simples; o histórico deve permitir entender tudo que aconteceu.**

---

# 406. Regra de ouro das permissões

> **O usuário só deve ver ações que pode executar, mas a segurança real continua no backend e no banco.**

---

# 407. Regra de ouro do mobile

> **No celular, priorizar executar e decidir; no desktop, priorizar organizar e analisar.**

---

# 408. Regra de ouro da inteligência futura

> **Sugestão deve aparecer como sugestão, nunca disfarçada de fato.**

---

# 409. Critério de aceite do UX D0

A experiência está adequada quando um novo usuário consegue, sem treinamento extenso:

```text
[ ] criar atividade
[ ] adicionar tarefa
[ ] iniciar tarefa
[ ] pausar
[ ] retomar
[ ] concluir
[ ] ver posição
[ ] entender prazo
[ ] receber notificação
[ ] conversar no contexto
```

E um gestor consegue:

```text
[ ] abrir fila
[ ] reordenar
[ ] ver atraso
[ ] ver bloqueio
[ ] resolver escalonamento
[ ] entender gargalos básicos
```

E um administrador consegue:

```text
[ ] criar setor
[ ] criar usuário
[ ] criar perfil
[ ] conceder ações
[ ] definir escopo
[ ] entender por que alguém tem acesso
```

---

# 410. Encerramento

A experiência da LPS precisa traduzir uma arquitetura robusta em uma sensação simples.

O usuário comum não precisa entender:

- schemas;
- RLS;
- eventos;
- tabelas;
- dependências técnicas;
- regras internas.

Ele precisa entender:

```text
O que preciso fazer?
```

```text
Onde está minha demanda?
```

```text
Qual o prazo?
```

```text
Quem está com ela?
```

```text
O que mudou?
```

```text
O que eu preciso decidir?
```

O gestor precisa entender:

```text
Onde está o gargalo?
```

```text
O que está atrasado?
```

```text
Qual fila está crescendo?
```

```text
O que precisa da minha decisão?
```

E o administrador precisa entender:

```text
Quem pode fazer o quê?
```

A LPS será bem-sucedida na experiência quando toda a complexidade necessária existir por trás, mas a operação diária continuar simples.

O princípio final deste documento é:

> **quanto mais sofisticada a LPS se tornar por dentro, mais simples ela deve parecer para quem usa.**

---

# 411. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação das telas, jornadas e princípios de experiência do usuário da LPS |
