# 10 — Roadmap D0, D1 e D2

> Documento de controle de escopo da LPS.  
> Sua função é impedir que o produto cresça antes de provar o estágio anterior.

---

# 1. Objetivo deste documento

Este documento define o que pertence a cada etapa da LPS.

A regra é simples:

```text
D0 — FUNCIONAR
↓
D1 — GERIR
↓
D2 — APRENDER
```

A LPS não deve avançar para o próximo nível porque uma funcionalidade parece interessante.

Ela avança quando o nível atual:

- funciona;
- é utilizado;
- gera dados confiáveis;
- resolve o problema proposto;
- possui qualidade suficiente para sustentar a próxima etapa.

---

# 2. Regra central do roadmap

> **Não construir inteligência antes de possuir operação.  
> Não construir gestão avançada antes de possuir dados confiáveis.**

---

# 3. O que significa cada estágio

## D0 — Funcionar

Responder:

> A empresa consegue organizar e executar o trabalho dentro da LPS?

A prioridade é:

```text
operação
```

---

## D1 — Gerir

Responder:

> O gestor consegue entender o que está acontecendo e tomar decisões melhores?

A prioridade é:

```text
visibilidade
+
controle
+
gestão por exceção
```

---

## D2 — Aprender

Responder:

> A LPS consegue usar o histórico para reconhecer padrões, prever e sugerir?

A prioridade é:

```text
aprendizado
+
previsão
+
recomendação
```

---

# 4. Princípio de progressão

A evolução deve seguir:

```text
REGISTRAR
↓
EXECUTAR
↓
MEDIR
↓
GERIR
↓
COMPARAR
↓
APRENDER
↓
PREVER
↓
RECOMENDAR
```

Se uma etapa anterior estiver fraca, a próxima não deve ser antecipada.

---

# 5. D0 — FUNCIONAR

## Objetivo

Criar o núcleo operacional da LPS.

Ao final do D0, uma empresa deve conseguir:

- cadastrar sua estrutura básica;
- criar atividades;
- dividir atividades em tarefas;
- direcionar tarefas para setores;
- organizar filas;
- executar tarefas;
- medir tempo;
- acompanhar movimentações;
- registrar devoluções;
- negociar prazos;
- conversar dentro do contexto;
- receber notificações essenciais;
- reconstruir o histórico do trabalho.

---

# 6. D0 — Usuários

A LPS precisa permitir:

```text
criar usuário
editar usuário
inativar usuário
```

Registrar:

- nome;
- e-mail;
- organização;
- situação;
- setores;
- perfis.

---

# 7. D0 — Organizações e empresas

Precisa existir:

```text
Organização LPS
↓
Empresa(s)
```

Requisitos:

- isolamento entre organizações;
- usuário pertence a uma única organização;
- organização pode possuir várias empresas;
- empresa atual pode ser usada como contexto operacional.

---

# 8. D0 — Setores

Precisa permitir:

```text
criar
editar
inativar
```

Exemplos:

```text
Comercial
Engenharia
Compras
Financeiro
Almoxarifado
```

Requisitos:

- setor configurável;
- não fixo no código;
- usuário pode participar de vários setores;
- setor é separado de autorização.

---

# 9. D0 — Permissões

Modelo mínimo:

```text
Usuário
+
Perfil
+
Ação
+
Escopo
```

Precisa permitir:

- grupos de ações;
- ações;
- perfis;
- perfil com ações;
- usuário com perfil;
- escopo por organização/empresa/setor;
- concessões diretas quando necessário;
- negação por padrão.

Exemplos de ações:

```text
atividade.visualizar
atividade.criar
tarefa.iniciar
tarefa.concluir
fila.reordenar
setor.criar
```

---

# 10. D0 — Segurança

Obrigatório:

- isolamento por organização;
- validação no backend;
- validação no banco;
- RLS — Row Level Security, ou Segurança em Nível de Linha;
- histórico de alterações de acesso.

Não basta esconder botão.

---

# 11. D0 — Obras e centros de custo

Precisa existir:

```text
Obras
Centros de custo
```

Regras:

- tabelas separadas;
- obra opcional na atividade;
- centro de custo opcional;
- ambos podem coexistir;
- centro de custo pode estar ligado a uma obra.

---

# 11.1 D0 — Processos

D0 precisa permitir cadastrar processos reutilizáveis sem transformar a LPS em ferramenta completa de modelagem de processos.

Estrutura mínima:

```text
Processo
├── Informações básicas
├── Inputs
├── Output
├── Critérios de aceite
└── Fluxo padrão de tarefas
```

Precisa permitir:

- criar processo vinculado a uma empresa;
- salvar rascunho;
- cadastrar inputs;
- definir um output principal;
- cadastrar critérios de aceite;
- definir tarefas padrão e setores;
- publicar uma versão;
- criar nova versão a partir de processo publicado;
- inativar sem apagar histórico;
- aplicar processo em uma atividade.

Regra:

```text
versão publicada
=
imutável
```

Atividade antiga continua vinculada à versão que recebeu.

Atividade sem processo continua permitida no D0.

---

# 12. D0 — Atividades

Atividade representa:

> o resultado/problema que precisa ser resolvido.

Precisa permitir:

- criar;
- editar;
- definir dono;
- definir prazo;
- associar empresa;
- associar obra opcional;
- associar centro de custo opcional;
- associar processo opcional;
- preservar versão do processo aplicada;
- concluir;
- cancelar;
- reabrir quando autorizado.

Regra:

```text
1 atividade
=
1 dono
```

---

# 13. D0 — Criação simples de atividade

Fluxo desejado:

```text
O que precisa ser resolvido?
↓
Dono
↓
Prazo
↓
Criar
```

Campos adicionais entram depois.

Processo pode ser selecionado opcionalmente por ação simples `Usar processo`, sem transformar o cadastro rápido em formulário longo.

Objetivo:

> atividade simples criada em segundos.

---

# 14. D0 — Tarefas

Precisa permitir:

- criar tarefa;
- editar;
- vincular à atividade;
- definir setor;
- atribuir executores;
- possuir vários executores;
- iniciar;
- pausar;
- retomar;
- devolver;
- concluir;
- cancelar.

---

# 15. D0 — Atividade x tarefa

Regra:

```text
Atividade
=
resultado completo
```

```text
Tarefa
=
parte do trabalho
```

Não criar subtarefas no D0.

---

# 16. D0 — Fluxo

Precisa permitir que uma atividade passe por múltiplos setores através das tarefas.

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

Requisitos:

- ordem simples;
- dependências básicas;
- retornos;
- múltiplas passagens pelo mesmo setor;
- histórico real do caminho.

---

# 17. D0 — Fluxo padrão do processo

O fluxo reutilizável pertence ao processo.

Exemplo:

```text
Processo:
Solicitação de compra

Tarefas padrão:
Engenharia → Compras → Financeiro → Almoxarifado
```

Ao aplicar o processo, a LPS cria tarefas operacionais reais.

Não construir:

- BPMN — Business Process Model and Notation, ou Notação e Modelagem de Processos de Negócio — completo;
- regras condicionais avançadas;
- motor genérico de formulários;
- dezenas de tipos de validação;
- automação inteligente de processo antes de existir histórico.

---

# 18. D0 — Filas

Cada setor precisa possuir fila própria.

Exemplo:

```text
4 de 17
```

Precisa permitir:

- entrada na fila;
- posição;
- total;
- ordenação;
- reordenação;
- histórico de posição;
- visão completa para setor autorizado;
- visão limitada para solicitante.

---

# 19. D0 — Transparência da fila

Solicitante vê:

```text
Setor
Posição
Total
Status
Prazo
```

Não vê automaticamente:

- títulos das outras demandas;
- clientes;
- valores;
- detalhes das demais tarefas.

---

# 20. D0 — Reordenação

Quem possui autorização pode reorganizar.

Exemplo:

```text
4
↓
16
```

Registrar:

- posição anterior;
- posição nova;
- usuário;
- data/hora;
- motivo quando exigido.

---

# 21. D0 — Tempo

Precisa permitir:

```text
Iniciar
Pausar
Retomar
Concluir
```

Registrar sessões por usuário.

Regra:

```text
1 usuário
=
1 sessão ativa por vez
```

---

# 22. D0 — Horas-homem

Se:

```text
Ryan = 1h30
Jennifer = 1h30
```

Então:

```text
Horas-homem = 3h
```

Mesmo que tenham trabalhado simultaneamente.

---

# 23. D0 — Tempo cronológico

Não confundir:

```text
tempo total
```

com:

```text
horas-homem
```

Exemplo:

```text
Duração cronológica = 2h
Horas-homem = 3h
```

---

# 24. D0 — Auditoria

Toda ação importante precisa deixar rastro.

Exemplos:

- atividade criada;
- dono alterado;
- tarefa criada;
- tarefa iniciada;
- pausa;
- retomada;
- mudança de setor;
- reordenação;
- devolução;
- mudança de prazo;
- conclusão.

---

# 25. D0 — Timeline

Atividade deve possuir histórico legível.

Exemplo:

```text
08:00 — criada
10:17 — primeira ação
11:20 — enviada para Compras
14:00 — devolvida
15:30 — reenviada
17:10 — concluída
```

---

# 26. D0 — Primeira ação

O banco deve registrar dados suficientes para calcular:

```text
criação
↓
primeira ação operacional relevante
```

A definição final de quais eventos contam como primeira ação deve ser fechada antes da implementação.

---

# 27. D0 — Devoluções

Toda devolução precisa registrar:

- origem;
- destino;
- motivo;
- observação;
- usuário;
- data/hora.

Motivo estruturado é obrigatório.

---

# 28. D0 — Bloqueios

Precisa permitir:

```text
Marcar como bloqueada
```

com motivo.

Exemplos:

```text
Aguardando cliente
Aguardando fornecedor
Aguardando aprovação
Aguardando documento
Aguardando decisão
```

---

# 29. D0 — Prazos

Separar:

```text
Prazo solicitado
```

de:

```text
Prazo comprometido
```

Nunca substituir um silenciosamente pelo outro.

---

# 30. D0 — Negociação de prazo

Fluxo mínimo:

```text
Solicitado
↓
Setor avalia
↓
Aceita
OU
propõe novo prazo
↓
Dono aceita ou recusa
```

Toda decisão fica registrada.

---

# 31. D0 — Recusa de prazo

A recusa precisa gerar:

```text
conflito registrado
+
notificação aos responsáveis configurados
```

O motor completo de escalonamento fica para D1.

Assim, o D0 não perde o conflito, mas também não constrói uma estrutura avançada cedo demais.

---

# 32. D0 — Comunicação

A comunicação deve existir em:

```text
Atividade
```

e:

```text
Tarefa
```

Não criar canais livres no D0.

---

# 33. D0 — Conversa contextual

Precisa permitir:

- mensagem;
- autor;
- data/hora;
- menção;
- histórico;
- acesso conforme autorização.

---

# 34. D0 — Regra da conversa

```text
Mensagem
≠
mudança oficial
```

Exemplo:

> “Pode deixar para sexta.”

não altera prazo automaticamente.

---

# 35. D0 — Notificações básicas

Central interna precisa suportar pelo menos:

- tarefa atribuída;
- devolução;
- mudança de posição;
- novo prazo proposto;
- prazo aceito;
- prazo recusado;
- atraso;
- menção;
- conclusão da atividade.

---

# 36. D0 — Conclusão

Regra consolidada:

> dono da atividade sempre recebe notificação da conclusão.

---

# 37. D0 — Home

A Home operacional deve responder:

> O que preciso fazer agora?

Elementos mínimos:

```text
Em execução
Próximas tarefas
Pendências
Notificações
```

---

# 38. D0 — Telas mínimas

Precisam existir:

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
Usuários
Setores
Perfis e permissões
Cadastros básicos
Processos
Novo/editar processo em modal grande
```

---

# 39. D0 — Mobile

Mobile precisa permitir, no mínimo:

- ver tarefas;
- criar atividade simples;
- iniciar;
- pausar;
- retomar;
- concluir;
- comentar;
- ver posição;
- responder prazo;
- receber notificações.

---

# 40. D0 — Desktop

Desktop precisa permitir:

- operação;
- gestão de fila;
- cadastros;
- permissões;
- histórico;
- administração.

---

# 41. D0 — O que NÃO construir

Não construir ainda:

- IA;
- benchmarking;
- previsão;
- sugestão automática de prazo;
- sugestão de fluxo;
- ranking de pessoas;
- dashboard complexo;
- BPMN completo;
- motor de processo com regras condicionais avançadas;
- formulários dinâmicos complexos;
- chat corporativo genérico;
- canais livres;
- workflow com dezenas de condições;
- permissões por campo;
- data warehouse;
- score de produtividade;
- analytics sofisticado.

---

# 42. Critério de saída do D0

Antes de considerar o D0 encerrado, a organização também precisa conseguir:

```text
criar um processo
↓
publicar uma versão
↓
aplicar o processo em uma atividade
↓
receber inputs
↓
executar tarefas
↓
validar critérios
↓
registrar output
↓
concluir sem perder o vínculo com a versão
```

O D0 só está concluído quando uma empresa consegue operar uma demanda real do começo ao fim na LPS.

Exemplo:

```text
Criar atividade
↓
Criar tarefas
↓
Entrar em setores
↓
Entrar em filas
↓
Executar
↓
Medir tempo
↓
Devolver se necessário
↓
Negociar prazo
↓
Concluir
↓
Reconstruir histórico
```

---

# 43. Perguntas de aceite do D0

A resposta precisa ser **sim** para:

```text
[ ] Conseguimos criar uma atividade em segundos?
[ ] Existe um único dono?
[ ] As tarefas podem passar por vários setores?
[ ] A fila funciona?
[ ] O solicitante vê sua posição?
[ ] O setor consegue reordenar?
[ ] O tempo é registrado?
[ ] Vários executores somam horas-homem?
[ ] A devolução fica auditada?
[ ] Prazo solicitado e comprometido estão separados?
[ ] Existe histórico?
[ ] As permissões funcionam?
[ ] Uma organização não acessa outra?
[ ] As notificações essenciais chegam?
[ ] A atividade pode ser concluída?
```

Se qualquer ponto central falhar:

> ainda estamos no D0.

---

# 44. D1 — GERIR

## Objetivo

Transformar os dados gerados no D0 em informação de gestão.

Responder:

> Onde está o problema?

> O que precisa da atenção do gestor?

> Qual setor está acumulando demanda?

> Onde perdemos tempo?

---

# 45. Pré-requisito do D1

Não iniciar D1 porque “seria legal ter dashboard”.

D1 só começa quando:

- D0 está sendo utilizado;
- eventos estão sendo registrados;
- tempos são confiáveis;
- filas são utilizadas;
- devoluções são registradas;
- prazos possuem histórico.

---

# 46. D1 — Indicadores

Indicadores iniciais:

- tempo total;
- tempo até primeira ação;
- tempo em fila;
- tempo trabalhado;
- horas-homem;
- tempo por setor;
- quantidade de pessoas;
- devoluções;
- atraso;
- cumprimento de prazo;
- backlog;
- aging.

---

# 47. D1 — Aging

Aging responde:

> Há quanto tempo esse item está aberto ou parado?

Exemplo:

```text
Na fila há 4 dias.
```

---

# 48. D1 — Throughput

Throughput significa quantidade concluída em determinado período.

Exemplo:

```text
Compras:
22 tarefas/dia
```

Usar linguagem simples na interface quando possível.

---

# 49. D1 — Backlog

Medir:

```text
entrada
versus
saída
```

Exemplo:

```text
Entraram 30/dia
Saíram 20/dia
```

Tendência:

```text
backlog cresce
```

---

# 50. D1 — Gargalos

A LPS precisa distinguir:

```text
fila
execução
decisão
retrabalho
bloqueio
terceiro
```

---

# 51. D1 — Gargalo de fila

Exemplo:

```text
Fila:
3 dias

Execução:
40 min
```

O problema não está na execução.

---

# 52. D1 — Gargalo de execução

Exemplo:

```text
Fila:
20 min

Execução:
9h
```

---

# 53. D1 — Gargalo de decisão

Exemplo:

```text
Aguardando aprovação:
4 dias
```

---

# 54. D1 — Gargalo externo

Exemplo:

```text
Fornecedor:
7 dias
```

---

# 55. D1 — Retrabalho

Medir:

- devoluções;
- motivo;
- horas adicionais;
- tempo adicional;
- recorrência.

---

# 56. D1 — Pareto de problemas

Mostrar:

> Quais poucos motivos respondem pela maior parte do problema?

Exemplo:

```text
3 motivos
=
72% das devoluções
```

---

# 57. D1 — Escalonamentos

D1 implementa o motor formal de escalonamento.

Precisa permitir:

- regras;
- níveis;
- destinatários;
- abertura automática;
- abertura manual;
- decisão;
- encerramento;
- histórico.

---

# 58. D1 — Exemplos de gatilho

```text
prazo recusado
prazo ultrapassado
bloqueio prolongado
ausência de decisão
```

---

# 59. D1 — Níveis

Exemplo:

```text
Nível 1 — Gestor do setor
Nível 2 — Gestor do dono
Nível 3 — Diretoria
```

Configurável.

Não fixar organograma no código.

---

# 60. D1 — Gestão por exceção

O gestor não deve acompanhar cada item manualmente.

A LPS precisa destacar:

- atrasadas;
- bloqueadas;
- devolvidas;
- escaladas;
- sem ação;
- fila crescendo;
- prazo em conflito.

---

# 61. D1 — Visão do gestor

A tela precisa responder:

- qual o tamanho da fila?
- o que está atrasado?
- o que está bloqueado?
- quais prazos estão em conflito?
- quais atividades não avançam?
- onde está o maior gargalo?

---

# 62. D1 — Capacidade

Sem modelo sofisticado ainda.

Pode começar com:

```text
Entraram
Concluíram
Fila atual
Tempo em fila
```

por período.

---

# 63. D1 — Capacidade por setor

Exemplo:

```text
Setor: Compras

Entradas/dia:
25

Saídas/dia:
19

Fila:
47
```

---

# 64. D1 — Capacidade por tipo de tarefa

Depois do básico:

```text
Cotação simples:
30 min

Cotação complexa:
4h
```

Se houver dados suficientes.

---

# 65. D1 — Relatórios

Relatórios precisam responder decisões reais.

Exemplos:

- tempo por setor;
- devoluções por motivo;
- atividades atrasadas;
- prazos renegociados;
- fila por período;
- horas-homem;
- planejado x realizado.

---

# 66. D1 — Não criar relatório por vaidade

Pergunta obrigatória:

> O que alguém fará diferente depois de ver este relatório?

Se não há resposta:

> não priorizar.

---

# 67. D1 — Planejado x realizado

Comparar:

```text
Prazo solicitado
Prazo comprometido
Conclusão real
```

---

# 68. D1 — Fluxo planejado x real

Exemplo:

Planejado:

```text
A → B → C
```

Real:

```text
A → B → A → B → D → C
```

---

# 69. D1 — Antes x depois

Permitir medir melhoria.

Exemplo:

```text
Antes do checklist:
28% devolução

Depois:
12%
```

---

# 70. D1 — Resumos

A LPS pode começar a gerar resumos estruturados sem IA complexa.

Exemplo:

```text
Duração:
8d 03h

Maior espera:
Fornecedor — 7 dias

Devoluções:
1

Prazo renegociado:
Sim
```

---

# 71. D1 — Resumo da atividade

Pode combinar:

- timeline;
- tempos;
- devoluções;
- prazos;
- escalonamentos.

---

# 72. D1 — Resumo gerencial

Exemplo:

> A atividade atrasou 2 dias. O maior período de espera ocorreu no fornecedor. Houve uma devolução por especificação incompleta.

Pode ser gerado por regras/templates antes de IA generativa.

---

# 73. D1 — Notificações avançadas

Depois das básicas, permitir:

- agrupamento;
- filtros;
- regras por gestor;
- alertas de aging;
- alertas de bloqueio;
- alertas de conflito.

---

# 74. D1 — Configuração por setor

Exemplo:

```text
Gestor recebe:
atrasos do setor
bloqueios acima de X período
escalonamentos
```

---

# 75. D1 — Auditoria gerencial

Permitir navegar:

```text
indicador
↓
atividades que compõem o número
↓
eventos
```

---

# 76. D1 — Drill-down

Drill-down significa sair do número agregado e abrir os registros que o formam.

Exemplo:

```text
8 atrasadas
↓
ver as 8
```

---

# 77. D1 — O que NÃO construir ainda

Ainda não construir como prioridade:

- previsão por IA;
- reordenação automática;
- prazo automático;
- benchmark entre empresas;
- recomendação automática de treinamento;
- score de produtividade;
- inteligência que altera fluxo sozinha.

---

# 78. Critério de saída do D1

O D1 está concluído quando um gestor consegue abrir a LPS e responder:

```text
Onde está o gargalo?
O que está atrasado?
O que está parado?
Por quê?
Qual fila está crescendo?
Quais problemas se repetem?
O que precisa da minha decisão?
```

sem depender de planilhas paralelas.

---

# 79. Perguntas de aceite do D1

```text
[ ] Consigo medir tempo total?
[ ] Consigo separar fila de execução?
[ ] Consigo ver horas-homem?
[ ] Consigo ver devoluções por motivo?
[ ] Consigo ver backlog?
[ ] Consigo ver aging?
[ ] Consigo identificar gargalo?
[ ] Consigo comparar planejado x realizado?
[ ] Consigo abrir os itens por trás do indicador?
[ ] Escalonamentos funcionam?
[ ] Gestor possui visão por exceção?
[ ] Relatórios ajudam decisões reais?
```

Se não:

> D1 ainda não está pronto.

---

# 80. D2 — APRENDER

## Objetivo

Usar o histórico da operação para reconhecer padrões e reduzir incerteza.

Responder:

> O que normalmente acontece?

> O que provavelmente acontecerá?

> O que a LPS sugere fazer?

---

# 81. Pré-requisito do D2

D2 só deve começar quando:

- existe histórico suficiente;
- métricas são confiáveis;
- tipos de atividade são usados de forma consistente;
- tempos são registrados;
- devoluções possuem motivos;
- filas refletem trabalho real;
- D1 já produz análises úteis.

---

# 82. D2 — Padrões históricos

A LPS passa a identificar:

- duração típica;
- fluxo recorrente;
- devoluções recorrentes;
- gargalos recorrentes;
- comportamento de fila;
- renegociação de prazo;
- concentração de conhecimento.

---

# 83. D2 — Atividades semelhantes

A comparação precisa considerar contexto.

Possíveis dimensões:

- tipo;
- empresa;
- setor;
- obra;
- fluxo;
- cliente;
- período;
- complexidade futura.

---

# 84. D2 — Estatística

Começar com:

- média;
- mediana;
- percentis;
- dispersão;
- tamanho da amostra.

Antes de modelos mais complexos.

---

# 85. D2 — Previsão de duração

Exemplo:

```text
Previsão:
3,4 dias

Base:
86 atividades semelhantes

Faixa:
2,8 a 4,6 dias
```

---

# 86. D2 — Previsão de fila

Exemplo:

```text
Posição:
7 de 18

Início provável:
amanhã entre 09h e 12h
```

---

# 87. D2 — Risco de atraso

Combinar:

- prazo restante;
- etapas abertas;
- histórico;
- fila;
- bloqueios;
- fornecedor;
- devoluções.

---

# 88. D2 — Explicação do risco

Não mostrar apenas:

```text
Risco alto
```

Mostrar:

```text
Etapas restantes levam mediana de 5,7 dias.
Prazo disponível: 4 dias.
```

---

# 89. D2 — Sugestão de prazo

Exemplo:

```text
Solicitado:
3 dias

Histórico:
80% concluem em até 5,1 dias

Sugestão:
5 dias
```

Usuário decide.

---

# 90. D2 — Sugestão de fluxo

Exemplo:

```text
76% das atividades deste tipo seguem:
Engenharia → Compras → Financeiro
```

Sugestão:

```text
Usar como fluxo padrão?
```

---

# 91. D2 — Sugestão de etapa

Exemplo:

Com validação técnica:

```text
12% devolução
```

Sem validação:

```text
31%
```

Sugestão:

> Avaliar validação antes de Compras.

---

# 92. D2 — Sugestão de treinamento

Exemplo:

Em tarefas comparáveis:

```text
Jennifer:
1h15 / baixa devolução

Equipe:
2h40
```

Sugestão:

> Avaliar compartilhamento do método.

Não:

> Jennifer é melhor.

---

# 93. D2 — Sugestão de capacidade

Exemplo:

```text
Entradas:
25/dia

Saídas:
19/dia
```

Sugestão:

> Avaliar capacidade, priorização ou redistribuição.

Não recomendar contratação automaticamente.

---

# 94. D2 — IA

IA deve entrar como camada de apoio.

Bons usos:

- resumo;
- explicação;
- pesquisa em linguagem natural;
- classificação de contexto;
- sugestão;
- detecção de risco textual.

---

# 95. D2 — IA não controla o processo

A IA não deve:

- alterar prazo silenciosamente;
- mudar dono;
- reordenar fila automaticamente;
- concluir atividade;
- cancelar tarefa;
- alterar fluxo sem confirmação.

---

# 96. D2 — Human-in-the-loop

Human-in-the-loop significa:

> uma pessoa continua participando da decisão.

Fluxo:

```text
LPS identifica
↓
LPS sugere
↓
Pessoa confirma
↓
Sistema registra
```

---

# 97. D2 — Fato x previsão

A interface deve separar:

```text
FATO
Compras levou 2d 4h.
```

```text
PREVISÃO
Esta tarefa deve levar aproximadamente 2,5 dias.
```

---

# 98. D2 — Previsão x recomendação

Também separar:

```text
PREVISÃO
72% de risco de atraso.
```

```text
RECOMENDAÇÃO
Considere antecipar a etapa de Compras.
```

---

# 99. D2 — Resumo automático por IA

Exemplo:

> A atividade levou 8 dias e 3 horas. O maior período ocorreu aguardando fornecedor. Houve uma devolução por especificação incompleta e uma renegociação de prazo.

O resumo deve usar fatos reais.

---

# 100. D2 — Conversas como contexto

Mensagens podem ajudar a identificar:

- decisão;
- risco;
- impedimento;
- prazo;
- compromisso.

Mas mensagem continua sem alterar estado automaticamente.

---

# 101. D2 — Exemplo de interpretação

Mensagem:

> “Se o material não chegar quarta, a equipe para.”

LPS sugere:

```text
Possível impacto relevante detectado.
Deseja registrar?
```

---

# 102. D2 — Process mining

Process mining significa mineração de processos.

A LPS poderá reconstruir caminhos reais.

Exemplo:

```text
Planejado:
A → B → C
```

```text
Real:
A → B → A → B → D → C
```

---

# 103. D2 — Objetivo do process mining

Identificar:

- caminhos mais usados;
- retornos;
- desvios;
- fluxos rápidos;
- fluxos lentos.

---

# 104. D2 — Benchmark interno

Primeiro benchmark:

```text
empresa contra ela mesma
```

Exemplos:

- mês atual x anterior;
- fluxo A x B;
- obra A x B;
- antes x depois.

---

# 105. D2 — Benchmarking anonimizado

Somente depois.

Possível comparação entre empresas sem expor dados identificáveis.

Exemplo:

> Empresas semelhantes apresentam menor devolução quando usam validação técnica antes de Compras.

---

# 106. D2 — Requisitos do benchmarking

Obrigatório considerar:

- autorização;
- governança;
- anonimização;
- comparabilidade;
- privacidade;
- regras jurídicas.

---

# 107. D2 — O que nunca fazer com benchmark

Não mostrar:

```text
Empresa X demora 5 dias.
```

para outra empresa sem autorização apropriada.

---

# 108. D2 — Aprendizado agregado

Pode utilizar:

- medianas;
- percentis;
- padrões;
- boas práticas.

Sem revelar:

- nomes;
- pessoas;
- clientes;
- obras;
- mensagens.

---

# 109. D2 — Feedback das sugestões

Usuário pode:

```text
Aceitar
Ignorar
Rejeitar
```

Registrar resultado.

---

# 110. D2 — Medir se a sugestão funcionou

Exemplo:

Antes:

```text
22% devolução
```

Sugestão:

```text
Adicionar checklist
```

Depois:

```text
11%
```

A LPS aprende que a alteração teve resultado positivo naquele contexto.

---

# 111. D2 — Aprender com erro

Se:

```text
Previsão = 5 dias
Real = 9 dias
```

o erro deve alimentar avaliação do modelo.

---

# 112. D2 — Confiança

Toda previsão precisa considerar:

- tamanho da amostra;
- qualidade dos dados;
- proximidade do contexto;
- histórico recente.

---

# 113. D2 — Dados insuficientes

Resposta correta:

```text
Não há histórico suficiente para prever.
```

Melhor do que uma previsão inventada.

---

# 114. D2 — Ranking de pessoas

Não é objetivo.

Mesmo com IA, não criar:

```text
1º Jennifer
2º Ryan
3º Luan
```

baseado apenas em velocidade.

---

# 115. D2 — Pessoas e treinamento

A inteligência deve priorizar:

- conhecimento;
- padronização;
- capacidade;
- treinamento;
- concentração de trabalho.

---

# 116. D2 — ROI

ROI significa Return on Investment, ou retorno sobre investimento.

Futuramente, a LPS poderá traduzir melhoria em:

- horas economizadas;
- retrabalho evitado;
- prazo reduzido;
- capacidade liberada.

---

# 117. D2 — Exemplo de ROI

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

Com custo/hora confiável, pode ser monetizado.

---

# 118. D2 — O que NÃO automatizar inicialmente

Mesmo no D2:

- contratação;
- demissão;
- avaliação automática de colaborador;
- mudança irreversível de processo;
- autorização de acesso;
- decisões financeiras críticas.

---

# 119. Critério de saída do D2

O D2 está maduro quando a LPS consegue:

```text
identificar padrão
↓
explicar
↓
prever com confiança conhecida
↓
sugerir
↓
registrar decisão humana
↓
medir o resultado depois
```

---

# 120. Perguntas de aceite do D2

```text
[ ] Existe histórico suficiente?
[ ] A previsão mostra sua base?
[ ] A previsão mostra incerteza?
[ ] Recomendações são explicáveis?
[ ] Usuário continua decidindo?
[ ] IA respeita permissões?
[ ] Sugestões podem ser aceitas ou rejeitadas?
[ ] O resultado da sugestão é medido?
[ ] Benchmark não expõe empresas?
[ ] A LPS diz quando não possui dados?
```

---

# 121. Resumo do roadmap

| Estágio | Pergunta principal | Entrega |
|---|---|---|
| D0 — Funcionar | Conseguimos trabalhar na LPS? | Operação confiável |
| D1 — Gerir | Conseguimos entender e controlar a operação? | Indicadores e gestão |
| D2 — Aprender | Conseguimos usar histórico para prever e sugerir? | Inteligência |

---

# 122. D0 em uma frase

> **Registrar e executar trabalho de ponta a ponta.**

---

# 123. D1 em uma frase

> **Transformar execução em informação para decisão.**

---

# 124. D2 em uma frase

> **Transformar histórico em aprendizado, previsão e recomendação.**

---

# 125. Dependência entre os níveis

```text
D2 depende de D1
D1 depende de D0
```

Logo:

```text
D0 ruim
=
D1 ruim
=
D2 ruim
```

---

# 126. Anti-roadmap

Sempre que surgir nova ideia, perguntar:

> Isso é necessário para o D atual funcionar?

Se:

```text
não
```

registrar no nível futuro.

Não implementar imediatamente.

---

# 127. Exemplo — “vamos colocar IA para distribuir tarefas”

Classificação:

```text
D2
```

Não entra no D0.

---

# 128. Exemplo — “vamos criar um dashboard bonito”

Pergunta:

> O D0 já gera dados confiáveis?

Se não:

```text
não priorizar.
```

---

# 129. Exemplo — “vamos integrar WhatsApp”

Não é necessário para provar o núcleo.

Classificação:

```text
futuro / após D0
```

---

# 130. Exemplo — “vamos criar canais #comercial”

Decisão atual:

```text
fora do D0.
```

Comunicação contextual já resolve o objetivo inicial.

---

# 131. Exemplo — “vamos criar previsão de conclusão”

Classificação:

```text
D2
```

Antes precisamos medir duração real.

---

# 132. Exemplo — “vamos mostrar tempo por setor”

Classificação:

```text
D1
```

Mas D0 precisa registrar as passagens corretamente.

---

# 133. Exemplo — “vamos medir tempo trabalhado”

Classificação:

```text
D0
```

Porque é dado-base.

---

# 134. Exemplo — “vamos detectar gargalo”

Classificação:

```text
D1
```

Porque depende dos tempos registrados no D0.

---

# 135. Exemplo — “vamos sugerir treinamento”

Classificação:

```text
D2
```

Porque depende de comparação histórica confiável.

---

# 136. Regra para nova funcionalidade

Toda nova ideia precisa receber uma etiqueta:

```text
D0
D1
D2
FUTURO
```

---

# 137. Perguntas para classificar uma ideia

## Pergunta 1

Sem isso, o D0 deixa de operar?

Se sim:

```text
D0
```

---

## Pergunta 2

Isso transforma dados operacionais em visão gerencial?

Se sim:

```text
D1
```

---

## Pergunta 3

Isso usa histórico para prever, recomendar ou aprender?

Se sim:

```text
D2
```

---

# 138. Regra de congelamento

Durante desenvolvimento do D0:

> nenhuma funcionalidade D1/D2 deve entrar no sprint apenas porque parece simples.

Exceção:

se for necessária tecnicamente para evitar retrabalho estrutural.

Mesmo assim:

- preparar arquitetura;
- não construir experiência completa.

---

# 139. Preparar não significa implementar

Exemplo:

No D0:

```text
registrar dados necessários para previsão futura
```

Não significa:

```text
construir previsão agora
```

---

# 140. Outra aplicação

No D0:

```text
registrar eventos de escalonamento/conflito
```

No D1:

```text
construir motor completo de escalonamento
```

---

# 141. Prioridade dentro do D0

Ordem recomendada:

```text
1. Organização / usuários / setores
2. Permissões
3. Atividades
4. Tarefas
5. Fluxo
6. Tempo
7. Filas
8. Devoluções / bloqueios
9. Prazos
10. Auditoria
11. Comunicação
12. Notificações
13. Mobile operacional
```

---

# 142. Prioridade dentro do D1

```text
1. Métricas confiáveis
2. Visão do gestor
3. Gargalos
4. Backlog / aging
5. Escalonamentos
6. Relatórios
7. Resumos
8. Melhorias de notificações
```

---

# 143. Prioridade dentro do D2

```text
1. Padrões históricos
2. Estatística
3. Previsão
4. Alertas preditivos
5. Sugestões
6. IA generativa
7. Benchmark anonimizado
```

---

# 144. D0 — definição de pronto técnica

Uma funcionalidade D0 não está pronta apenas porque existe tela.

Precisa possuir:

```text
[ ] banco
[ ] autorização
[ ] validação
[ ] auditoria
[ ] estado de erro
[ ] estado vazio
[ ] teste
[ ] comportamento mobile quando aplicável
```

---

# 145. D0 — definição de pronto funcional

Precisa:

- resolver caso real;
- ser compreensível;
- não depender de planilha paralela;
- registrar dados corretos.

---

# 146. D1 — definição de pronto

Indicador só está pronto se:

- fórmula definida;
- fonte conhecida;
- dados confiáveis;
- drill-down possível;
- decisão associada.

---

# 147. D2 — definição de pronto

Previsão/recomendação só está pronta se:

- base de dados suficiente;
- confiança conhecida;
- explicação disponível;
- segurança respeitada;
- resultado mensurável.

---

# 148. Métricas do próprio produto — D0

A equipe LPS deve acompanhar:

- usuários ativos;
- atividades criadas;
- tarefas concluídas;
- sessões de tempo;
- percentual de atividades concluídas dentro da LPS;
- erros;
- abandono de criação.

---

# 149. Métricas do próprio produto — D1

Acompanhar:

- uso da visão do gestor;
- indicadores acessados;
- escalonamentos resolvidos;
- redução de planilhas paralelas;
- tempo de decisão.

---

# 150. Métricas do próprio produto — D2

Acompanhar:

- previsões geradas;
- erro de previsão;
- sugestões aceitas;
- sugestões rejeitadas;
- impacto real após aplicação.

---

# 151. Sinal de que o D0 falhou

Se usuários:

- controlam fila em planilha;
- registram tempo fora da LPS;
- cobram status pelo WhatsApp;
- não entendem quem é o dono;
- não usam tarefas;
- não confiam no histórico;

não adianta avançar para IA.

---

# 152. Sinal de que o D1 falhou

Se gestor ainda precisa:

- exportar tudo para Excel;
- perguntar individualmente;
- montar indicador manual;
- procurar gargalo em reunião;

D1 ainda não entregou seu objetivo.

---

# 153. Sinal de que o D2 falhou

Se a IA:

- inventa;
- não explica;
- recomenda sem contexto;
- tem previsões ruins;
- não mede resultado;

ela não está criando valor.

---

# 154. Roadmap não é calendário

D0, D1 e D2 são níveis de maturidade.

Não significam obrigatoriamente:

```text
mês 1
mês 2
mês 3
```

A passagem depende do produto estar pronto.

---

# 155. Roadmap não deve ser usado para justificar atraso

O objetivo é limitar escopo.

Não permitir que D0 vire projeto infinito.

---

# 156. D0 precisa ser mínimo, mas completo

Mínimo:

> somente o necessário.

Completo:

> consegue operar o ciclo inteiro.

---

# 157. Diferença entre MVP e protótipo

Protótipo:

```text
demonstra ideia
```

D0 operacional:

```text
empresa consegue usar de verdade
```

---

# 158. O D0 não precisa fazer tudo

Mas o que fizer precisa ser confiável.

---

# 159. Ordem de valor

```text
1. Fazer funcionar
2. Tornar visível
3. Tornar inteligente
```

---

# 160. Matriz de funcionalidades

| Funcionalidade | D0 | D1 | D2 |
|---|:---:|:---:|:---:|
| Usuários | ✅ |  |  |
| Setores | ✅ |  |  |
| Permissões | ✅ |  |  |
| Atividades | ✅ |  |  |
| Tarefas | ✅ |  |  |
| Fluxo básico | ✅ |  |  |
| Filas | ✅ |  |  |
| Timer | ✅ |  |  |
| Auditoria | ✅ |  |  |
| Prazo solicitado/comprometido | ✅ |  |  |
| Comunicação contextual | ✅ |  |  |
| Notificações básicas | ✅ |  |  |
| Indicadores |  | ✅ |  |
| Gargalos |  | ✅ |  |
| Escalonamento avançado |  | ✅ |  |
| Relatórios gerenciais |  | ✅ |  |
| Visão do gestor |  | ✅ |  |
| Resumos estruturados |  | ✅ |  |
| Padrões históricos |  |  | ✅ |
| Previsão |  |  | ✅ |
| Sugestão de prazo |  |  | ✅ |
| Sugestão de fluxo |  |  | ✅ |
| Sugestão de melhoria |  |  | ✅ |
| IA generativa |  |  | ✅ |
| Benchmark anonimizado |  |  | ✅ |

---

# 161. Funcionalidades híbridas

Algumas funcionalidades evoluem em níveis.

Exemplo:

## Notificações

D0:

```text
avisos essenciais
```

D1:

```text
regras e gestão por exceção
```

D2:

```text
alertas preditivos
```

---

# 162. Outro exemplo — prazo

D0:

```text
solicitado
comprometido
negociação
```

D1:

```text
cumprimento
desvio
renegociação
```

D2:

```text
prazo sugerido
risco previsto
```

---

# 163. Outro exemplo — fluxo

D0:

```text
fluxo configurado/manual
```

D1:

```text
fluxo real x planejado
```

D2:

```text
fluxo sugerido
```

---

# 164. Outro exemplo — tempo

D0:

```text
registrar
```

D1:

```text
analisar
```

D2:

```text
prever
```

---

# 165. Outro exemplo — comunicação

D0:

```text
conversa contextual
```

D1:

```text
resumo estruturado
```

D2:

```text
interpretação e resumo por IA
```

---

# 166. Decisões consolidadas deste roadmap

## D0

Pertencem ao D0:

- usuários;
- organizações e empresas;
- setores;
- permissões;
- obras;
- centros de custo;
- atividades;
- tarefas;
- fluxo básico;
- filas;
- tempo;
- auditoria;
- devoluções;
- bloqueios;
- prazos;
- comunicação contextual;
- notificações básicas;
- operação web/mobile essencial.

## D1

Pertencem ao D1:

- indicadores;
- gargalos;
- backlog;
- aging;
- capacidade básica;
- escalonamentos completos;
- relatórios;
- visão do gestor;
- resumos estruturados;
- gestão por exceção;
- planejado x realizado.

## D2

Pertencem ao D2:

- padrões históricos;
- estatística avançada;
- previsão;
- risco preditivo;
- sugestões;
- IA;
- process mining;
- recomendações de melhoria;
- treinamento sugerido;
- benchmarking anonimizado.

---

# 167. O que deve permanecer fora até necessidade real

- ERP financeiro;
- folha de pagamento;
- compras completas;
- CRM completo;
- chat corporativo completo;
- videochamada;
- gestão documental completa;
- BI genérico;
- organograma complexo;
- permissões por campo;
- workflow BPMN completo.

A LPS integra quando necessário.

Não precisa substituir tudo.

---

# 168. Pergunta obrigatória antes de qualquer desenvolvimento

> **Qual problema do D atual esta funcionalidade resolve?**

Se ninguém consegue responder:

> não entra agora.

---

# 169. Segunda pergunta obrigatória

> **Sem isso, o estágio atual deixa de cumprir seu objetivo?**

Se não:

> avaliar backlog futuro.

---

# 170. Terceira pergunta obrigatória

> **Já temos dados e maturidade para essa funcionalidade funcionar corretamente?**

Se não:

> preparar os dados, não construir a camada avançada.

---

# 171. Regra de ouro do D0

> **Primeiro a LPS precisa funcionar no trabalho real.**

---

# 172. Regra de ouro do D1

> **Depois ela precisa mostrar ao gestor onde agir.**

---

# 173. Regra de ouro do D2

> **Somente então ela deve aprender com o histórico e sugerir o futuro.**

---

# 174. Regra de ouro do escopo

> **Uma boa ideia fora do estágio atual continua sendo uma boa ideia — apenas não é prioridade agora.**

---

# 175. Regra de ouro contra divagação

> **Quando surgir algo novo, classificar antes de discutir implementação.**

```text
D0?
D1?
D2?
Futuro?
```

Só depois decidir.

---

# 176. Fluxo de decisão para novas ideias

```text
NOVA IDEIA
↓
É NECESSÁRIA PARA OPERAR?
├── SIM → D0
└── NÃO
     ↓
     TRANSFORMA DADOS EM GESTÃO?
     ├── SIM → D1
     └── NÃO
          ↓
          USA HISTÓRICO PARA PREVER/SUGERIR?
          ├── SIM → D2
          └── NÃO → FUTURO / FORA DO ESCOPO
```

---

# 177. Critério final de foco

O objetivo não é construir o maior sistema.

É construir a menor versão que prove, em sequência:

```text
1. A LPS organiza o trabalho.
2. A LPS melhora a gestão.
3. A LPS aprende com a operação.
```

---

# 178. Encerramento

O roadmap da LPS precisa proteger o produto contra o maior risco desta fase:

> construir muita coisa antes de provar o núcleo.

O D0 deve provar que a empresa consegue trabalhar dentro da LPS.

O D1 deve provar que os dados ajudam o gestor a tomar decisões.

O D2 deve provar que o histórico acumulado permite prever e recomendar com qualidade.

A ordem não deve ser invertida.

```text
D0 — FUNCIONAR
↓
D1 — GERIR
↓
D2 — APRENDER
```

Se mantivermos essa disciplina, cada nova camada nasce apoiada em algo real, e não em hipótese.

---

# 179. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Roadmap funcional da LPS dividido em D0 — Funcionar, D1 — Gerir e D2 — Aprender |
