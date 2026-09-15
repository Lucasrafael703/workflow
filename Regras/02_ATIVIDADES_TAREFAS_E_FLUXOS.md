# 02 — Atividades, Tarefas e Fluxos

> Documento funcional do núcleo operacional da LPS: como uma necessidade vira atividade, como a atividade é dividida em tarefas, como essas tarefas percorrem setores, como pessoas executam o trabalho e como o sistema registra todo o fluxo até o resultado final.

---

# 1. Objetivo deste documento

Este documento define o comportamento central da LPS.

Ele deve responder:

- o que é uma atividade;
- o que é uma tarefa;
- quem é o dono da atividade;
- quem pode executar uma tarefa;
- como uma atividade percorre setores;
- como as tarefas são ordenadas;
- como dependências funcionam;
- como uma tarefa pode voltar para uma etapa anterior;
- como devoluções são registradas;
- quando uma atividade pode ser considerada concluída;
- como os fluxos são configurados;
- como a LPS deve começar operando antes de possuir inteligência histórica;
- quais eventos precisam ser preservados para auditoria e aprendizado futuro.

Este documento não define:

- estrutura física completa do banco;
- layout das telas;
- regras detalhadas de fila;
- regras detalhadas de escalonamento;
- algoritmo de priorização;
- regras completas de notificação;
- inteligência artificial.

Esses assuntos pertencem aos documentos específicos da LPS.

---

# 2. Princípio central

A estrutura fundamental da LPS é:

```text
ATIVIDADE
↓
TAREFAS
↓
EXECUÇÃO
↓
FLUXO ENTRE SETORES
↓
RESULTADO
```

Uma atividade representa algo que precisa ser resolvido.

As tarefas representam os trabalhos necessários para chegar ao resultado.

O fluxo representa o caminho percorrido.

A atividade termina quando o resultado é alcançado.

---

# 3. Conceito de atividade

Uma atividade representa:

- um problema;
- uma necessidade;
- uma entrega;
- um resultado esperado;
- uma demanda que precisa ser acompanhada até sua resolução.

A atividade deve possuir contexto suficiente para que qualquer pessoa autorizada entenda:

- o que precisa acontecer;
- por que precisa acontecer;
- quem precisa do resultado;
- qual o prazo;
- quais tarefas existem;
- onde está;
- quem está executando;
- o que já aconteceu;
- o que falta acontecer.

---

# 4. Atividade não é apenas uma tarefa grande

A atividade é o elemento de responsabilidade pelo resultado.

Exemplo:

```text
Atividade:
Material disponível na obra
```

Esse resultado pode exigir várias tarefas:

```text
1. Engenharia gerar lista de materiais
2. Compras cotar e comprar
3. Financeiro realizar pagamento
4. Almoxarifado receber
5. Obra confirmar disponibilidade
```

O resultado só está concluído quando o material efetivamente estiver disponível para a finalidade definida.

---

# 5. Exemplos de atividades

Exemplos possíveis:

```text
Material disponível na obra
```

```text
Orçamento entregue ao cliente
```

```text
Veículo disponível para utilização
```

```text
Documento aprovado
```

```text
Problema técnico solucionado
```

```text
Equipamento liberado para operação
```

A atividade deve representar resultado, e não apenas ação.

Comparação:

### Evitar

```text
Comprar cabo
```

quando o problema maior é:

```text
Disponibilizar material para execução da obra
```

### Preferir

A atividade registra o resultado.

A compra pode ser uma tarefa dentro dela.

---

# 6. Dono da atividade

Toda atividade possui um único dono.

A LPS deve responder sem ambiguidade:

> Quem responde pelo acompanhamento desta atividade até o resultado?

Não existem dois donos simultâneos da mesma atividade.

---

# 7. Papel do dono da atividade

O dono é a pessoa que:

- precisa que o resultado aconteça;
- acompanha o andamento;
- monitora as tarefas;
- acompanha prazos;
- acompanha retornos;
- recebe informações relevantes;
- cobra quando necessário;
- responde pelo acompanhamento;
- acompanha conflitos;
- participa de renegociações;
- recebe conclusão;
- valida, quando aplicável, se o problema foi realmente resolvido.

O dono não precisa executar todas as tarefas.

---

# 8. O dono não muda automaticamente quando a tarefa muda de setor

Exemplo:

```text
Atividade:
Material disponível na obra

Dono:
Engenheiro
```

Fluxo:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

Mesmo quando a tarefa está em Compras, Financeiro ou Almoxarifado, a atividade continua pertencendo ao dono original.

O dono acompanha o resultado até a resolução.

---

# 9. Responsabilidade não significa execução

A LPS precisa separar dois conceitos:

## Responsabilidade pelo resultado

Pertence ao dono da atividade.

## Responsabilidade pela execução

Pertence ao setor e aos executores de cada tarefa.

Exemplo:

```text
Dono da atividade:
Paulo

Tarefa:
Realizar cotação

Setor:
Compras

Executores:
Rian
Luan
```

Paulo continua dono da atividade.

Rian e Luan executam a tarefa.

---

# 10. Conceito de tarefa

A tarefa é uma unidade de trabalho dentro da atividade.

Ela representa uma parte necessária para alcançar o resultado final.

Uma atividade pode possuir:

```text
1 tarefa
```

ou:

```text
várias tarefas
```

A quantidade depende da necessidade real do processo.

---

# 11. Exemplos de tarefas

Dentro da atividade:

```text
Material disponível na obra
```

podem existir:

```text
Gerar lista de materiais
```

```text
Validar especificações
```

```text
Realizar cotação
```

```text
Emitir pedido
```

```text
Realizar pagamento
```

```text
Receber material
```

```text
Confirmar disponibilidade
```

---

# 12. Tarefa precisa ter propósito claro

Uma tarefa deve responder:

> O que precisa ser feito para a atividade avançar?

Evitar tarefas vagas como:

```text
Ver isso
```

```text
Resolver
```

```text
Analisar
```

quando não houver contexto suficiente.

A descrição precisa ser simples, mas compreensível.

---

# 13. Tarefa e setor

Cada tarefa possui um setor responsável em determinado momento do fluxo.

Exemplo:

```text
Tarefa:
Realizar cotação

Setor responsável:
Compras
```

Outro exemplo:

```text
Tarefa:
Efetuar pagamento

Setor responsável:
Financeiro
```

---

# 14. Setores são configuráveis

A LPS não deve depender de nomes fixos.

Exemplos de setores possíveis:

```text
Comercial
Financeiro
Engenharia
Compras
Almoxarifado
```

Outra empresa pode possuir:

```text
Administrativo
Operações
Projetos
Logística
```

A estrutura da LPS deve funcionar nos dois casos.

---

# 15. Uma atividade pode passar por vários setores

Esse é um dos comportamentos centrais da LPS.

Exemplo:

```text
Engenharia
↓
Compras
↓
Almoxarifado
↓
Financeiro
```

O objetivo não é apenas mover a atividade.

O objetivo é registrar o caminho percorrido.

---

# 16. O fluxo precisa gerar dados

Cada passagem deve permitir identificar:

- setor de origem;
- setor de destino;
- tarefa;
- data e hora;
- quem realizou a movimentação;
- posição no fluxo;
- responsável atual;
- tempo gasto até ali;
- devoluções;
- motivo de devolução;
- prazo;
- status.

Esse histórico será essencial para identificar gargalos.

---

# 17. Executor

Executor é a pessoa que efetivamente trabalha em uma tarefa.

Uma tarefa pode possuir:

```text
0 executores
```

quando ainda está aguardando alguém assumir.

Pode possuir:

```text
1 executor
```

ou:

```text
vários executores
```

quando o trabalho é compartilhado.

---

# 18. Uma tarefa pode nascer sem executor

Nem sempre, no momento da criação, é possível saber quem executará.

Exemplo:

```text
Tarefa:
Levantar quantitativos

Setor:
Comercial

Executor:
Não definido
```

A tarefa pode entrar na fila do setor.

Depois, conforme regras de autorização, alguém pode:

- assumir;
- ser atribuído;
- participar como executor.

---

# 19. Vários executores na mesma tarefa

Uma tarefa pode ser realizada por várias pessoas.

Exemplo:

```text
Tarefa:
Contagem de quantitativos

Executores:
Ryan
Jennifer
Luan
```

O sistema deve registrar o trabalho individual.

Exemplo:

```text
Ryan       2h10
Jennifer   1h20
Luan       0h50
```

Total de horas-homem:

```text
4h20
```

Esse dado não deve ser confundido com duração cronológica da tarefa.

---

# 20. Tempo decorrido x horas-homem

Exemplo:

Ryan e Jennifer trabalham simultaneamente durante 1 hora.

Tempo decorrido:

```text
1 hora
```

Horas-homem:

```text
2 horas
```

A LPS deve preservar essa diferença.

---

# 21. Setor responsável x executor

Esses conceitos não são equivalentes.

Exemplo:

```text
Setor responsável:
Compras

Executores:
Rian
Luan
```

O setor representa a unidade operacional responsável pela tarefa.

Os executores representam as pessoas que estão realizando o trabalho.

---

# 22. Gestor do setor

O gestor do setor não precisa executar todas as tarefas.

Ele precisa poder acompanhar, conforme autorização:

- fila;
- atrasos;
- conflitos;
- devoluções;
- mudanças de prazo;
- tarefas bloqueadoras;
- tarefas de maior impacto;
- escalonamentos.

A definição detalhada pertence ao documento de usuários, setores e autorizações.

---

# 23. Estrutura conceitual

A estrutura pode ser visualizada assim:

```text
ATIVIDADE
│
├── Dono único
│
├── Prazo da atividade
│
├── Histórico
│
└── TAREFAS
    │
    ├── Setor responsável
    ├── 0..N executores
    ├── Prazo
    ├── Posição no fluxo
    ├── Dependências
    ├── Histórico
    ├── Devoluções
    └── Tempo
```

---

# 24. Fluxo entre tarefas

As tarefas podem possuir uma sequência.

Exemplo:

```text
Tarefa 1
Gerar lista

↓ concluída

Tarefa 2
Realizar compra

↓ concluída

Tarefa 3
Realizar pagamento

↓ concluída

Tarefa 4
Receber material
```

Essa é a forma mais simples de fluxo.

---

# 25. Ordem das tarefas

No início, a ordem das tarefas será informada manualmente.

Exemplo:

```text
1. Engenharia
2. Compras
3. Financeiro
4. Almoxarifado
```

A LPS não precisa adivinhar o fluxo no D0.

O usuário configura.

---

# 26. A ordem deve poder ser alterada

Enquanto a atividade ainda permitir alteração, pessoas autorizadas podem ajustar a sequência.

Qualquer alteração relevante deve ser auditada.

Exemplo:

Fluxo inicial:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

Fluxo alterado:

```text
Engenharia
↓
Compras
↓
Almoxarifado
↓
Financeiro
```

O sistema precisa registrar que a mudança ocorreu.

---

# 27. Ordem não deve apagar histórico

Se uma tarefa já foi executada e o fluxo for alterado, a LPS não deve reescrever a história como se o fluxo antigo nunca tivesse existido.

A auditoria deve preservar:

- estrutura anterior;
- mudança;
- nova estrutura;
- autor da alteração;
- momento da alteração.

---

# 28. Dependências

Uma tarefa pode depender de outra.

Exemplo:

```text
Comprar material
```

depende de:

```text
Gerar lista de materiais
```

O sistema precisa saber que a segunda não deveria iniciar normalmente antes da primeira atingir a condição necessária.

---

# 29. Dependência simples

No D0, a dependência mais importante é:

```text
Tarefa B depende da conclusão da Tarefa A
```

Exemplo:

```text
Gerar quantitativos
↓
Realizar cotação
```

---

# 30. Dependências em paralelo

Uma atividade pode possuir tarefas independentes executadas simultaneamente.

Exemplo:

```text
              ┌→ Validar projeto elétrico
Atividade ────┤
              └→ Validar projeto hidráulico
```

Depois:

```text
Ambas concluídas
↓
Consolidar orçamento
```

A arquitetura deve permitir esse comportamento, mesmo que a primeira versão da interface seja simples.

---

# 31. Dependência deve representar realidade operacional

Evitar criar dependências apenas para montar um fluxograma bonito.

A dependência deve existir quando uma tarefa realmente necessita de outra para avançar.

---

# 32. Fluxo linear

Exemplo:

```text
A
↓
B
↓
C
↓
D
```

É o modelo mais simples.

---

# 33. Fluxo com paralelismo

Exemplo:

```text
       ┌→ B
A ─────┤
       └→ C

B + C
↓
D
```

A LPS deve estar preparada para reconhecer que mais de uma tarefa pode estar acontecendo ao mesmo tempo.

---

# 34. Fluxo com retorno

Exemplo:

```text
Engenharia
↓
Compras
↓
Financeiro
```

Compras identifica erro técnico:

```text
Compras
↓ devolução
Engenharia
↓ correção
Compras
```

Esse retorno faz parte do processo real.

A LPS não deve impedir isso.

---

# 35. Retorno para etapa anterior

Uma tarefa pode voltar para:

- setor anterior;
- tarefa anterior;
- responsável anterior;
- ponto específico do fluxo;

quando o processo exigir correção ou complementação.

---

# 36. Toda devolução precisa de motivo

A devolução não pode ser apenas:

```text
Voltar
```

Ela precisa registrar:

- quem devolveu;
- quando;
- de onde;
- para onde;
- qual tarefa;
- motivo.

---

# 37. Exemplos de motivos de devolução

Exemplos:

```text
Informação incompleta
```

```text
Especificação incorreta
```

```text
Documento ausente
```

```text
Necessidade de aprovação
```

```text
Escopo divergente
```

```text
Dados insuficientes
```

Os motivos podem ser configuráveis.

Pode também existir observação complementar.

---

# 38. Motivo estruturado + observação

Quando aplicável:

```text
Motivo:
Informação incompleta

Observação:
Faltou especificar a bitola do cabo.
```

Isso melhora a análise futura.

---

# 39. Retorno não apaga o caminho anterior

Exemplo:

```text
Engenharia
↓
Compras
↓
Engenharia
↓
Compras
```

O histórico precisa manter as quatro passagens.

Não deve ficar registrado apenas:

```text
Compras
```

como estado atual.

---

# 40. Número de retornos é um indicador

A LPS deve conseguir saber:

- quantas vezes uma tarefa retornou;
- para onde;
- por qual motivo;
- quanto tempo foi perdido;
- quais tipos de atividade mais retornam.

Esse dado será essencial para retroalimentação.

---

# 41. Retrabalho

Nem toda devolução representa erro.

Porém, muitas devoluções podem indicar:

- processo incompleto;
- falta de informação;
- treinamento insuficiente;
- padrão ruim;
- comunicação inadequada;
- validação ausente.

A LPS deve registrar os fatos.

A interpretação gerencial vem depois.

---

# 42. Estados da atividade

Os nomes finais dos status ainda pertencem a decisões futuras.

Mas conceitualmente a atividade precisa passar por estados equivalentes a:

```text
Aberta
Em andamento
Bloqueada
Concluída
```

A empresa poderá possuir nomenclatura configurável quando isso for definido.

A lógica central precisa permanecer consistente.

---

# 43. Estados da tarefa

Da mesma forma, a tarefa precisa possuir estados que permitam identificar, no mínimo:

- ainda não iniciada;
- disponível;
- em execução;
- aguardando;
- devolvida;
- bloqueada;
- concluída.

A estrutura detalhada será definida posteriormente.

---

# 44. Primeiro passo da atividade

A LPS deve registrar quanto tempo passou entre:

```text
atividade criada
```

e:

```text
primeira ação relevante
```

Esse indicador responde:

> Quanto tempo demorou para alguém começar a agir?

---

# 45. O que conta como primeira ação

A definição técnica ainda será detalhada no documento de auditoria.

Conceitualmente, não deve bastar apenas abrir a tela.

Primeira ação deve representar avanço operacional real, como:

- assumir tarefa;
- iniciar tarefa;
- movimentar;
- responder formalmente;
- definir prazo comprometido;
- executar uma ação configurada como relevante.

---

# 46. Conclusão de tarefa

Uma tarefa é concluída quando sua entrega específica foi realizada.

Exemplo:

```text
Tarefa:
Realizar cotação

Conclusão:
Cotação finalizada
```

Isso não significa necessariamente que a atividade inteira foi concluída.

---

# 47. Conclusão da atividade

A atividade é concluída quando o problema ou resultado que a originou foi resolvido.

Exemplo:

```text
Atividade:
Material disponível na obra
```

Não basta concluir:

```text
Compra realizada
```

ou:

```text
Pagamento realizado
```

Se o material ainda não chegou, a atividade não terminou.

---

# 48. Resultado alcançado

A lógica deve ser:

```text
Tarefas concluídas
≠
resultado necessariamente alcançado
```

Pode existir necessidade de uma confirmação final.

Exemplo:

```text
Compra feita
↓
Pagamento feito
↓
Material recebido
↓
Material disponível
↓
RESULTADO ALCANÇADO
```

---

# 49. Quem conclui a atividade

A regra exata deve ser configurável conforme autorização.

Conceitualmente, o dono da atividade precisa ser informado e participar do encerramento quando fizer sentido.

O sistema deve evitar que uma atividade seja considerada resolvida sem que o resultado tenha sido efetivamente alcançado.

---

# 50. Reabertura

Uma atividade concluída pode, em situações autorizadas, ser reaberta.

Exemplo:

```text
Atividade concluída
↓
Problema identificado
↓
Reabertura
```

A reabertura deve:

- ficar auditada;
- registrar responsável;
- registrar data e hora;
- registrar motivo quando aplicável.

---

# 51. Fluxo configurável

A LPS deve permitir que empresas definam fluxos.

Exemplo:

```text
Solicitação de compra
```

Fluxo configurado:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

Outro tipo de atividade pode possuir outro fluxo.

---

# 52. Fluxos não devem ser fixos no código

Evitar lógica como:

```text
Se atividade = compra:
    Engenharia
    Compras
    Financeiro
```

O fluxo precisa ser cadastro/configuração.

Isso permite empresas diferentes.

---

# 53. Fluxo inicialmente criado manualmente

No início da LPS:

- a empresa cria o fluxo;
- define as tarefas;
- define a ordem;
- define os setores;
- define dependências;
- define responsáveis quando necessário;
- informa prazos manualmente.

A LPS registra o que acontece.

---

# 54. Por que começar manualmente

No início, a LPS não possui histórico suficiente para afirmar:

- qual fluxo é melhor;
- qual prazo é adequado;
- qual setor deve participar;
- quanto tempo cada etapa leva.

Tentar automatizar isso sem dados seria inventar inteligência.

---

# 55. O sistema precisa aprender com os fluxos executados

Cada execução deve alimentar histórico para responder futuramente:

- quais tarefas normalmente aparecem;
- quais setores normalmente participam;
- quais etapas são puladas;
- quais etapas retornam;
- quais etapas demoram;
- quais fluxos geram menos retrabalho;
- quais fluxos geram melhor resultado.

---

# 56. Evolução futura dos fluxos

A evolução esperada é:

```text
D0
Fluxo configurado manualmente
```

Depois:

```text
Histórico suficiente
↓
LPS identifica padrão
```

Depois:

```text
LPS sugere fluxo
```

Exemplo:

> Atividades deste tipo normalmente seguem Engenharia → Compras → Financeiro → Almoxarifado. Deseja utilizar este fluxo?

A decisão continua com o usuário.

---

# 57. Sugestão não significa imposição

Mesmo no futuro, a LPS pode sugerir.

Não deve necessariamente impor.

A organização pode possuir exceções legítimas.

---

# 58. Tipos de atividade e fluxos

Futuramente, um tipo de atividade pode possuir um fluxo padrão.

Exemplo:

```text
Tipo:
Solicitação de compra
```

Fluxo padrão:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

Ao criar uma atividade desse tipo, o fluxo pode ser carregado automaticamente.

No D0, isso pode começar de forma simples.

---

# 59. Fluxo padrão não deve impedir exceção

Se a empresa autorizar, uma atividade específica pode precisar de ajuste.

Exemplo:

Fluxo padrão:

```text
Engenharia
↓
Compras
↓
Financeiro
```

Caso específico:

```text
Engenharia
↓
Diretoria
↓
Compras
↓
Financeiro
```

A alteração precisa ficar registrada.

---

# 60. Atividade sem fluxo pré-configurado

A LPS precisa permitir criar atividade mesmo quando ainda não existe um fluxo padrão.

Exemplo:

```text
Atividade nova
↓
Usuário cria tarefas manualmente
↓
Define setores
↓
Define sequência
```

Isso é importante para o início da adoção.

---

# 61. Fluxo criado a partir da experiência

A empresa pode executar algumas atividades manualmente.

Depois perceber:

```text
Essas atividades seguem praticamente o mesmo caminho.
```

Então transforma esse caminho em fluxo padrão.

A LPS deve favorecer esse amadurecimento.

---

# 62. Atividade pode evoluir enquanto acontece

Nem sempre todas as tarefas são conhecidas no momento inicial.

Exemplo:

```text
Atividade:
Resolver problema elétrico
```

Inicialmente:

```text
1. Inspecionar
```

Após inspeção:

```text
2. Comprar componente
3. Substituir componente
4. Testar
```

A LPS deve permitir adicionar tarefas durante a execução, conforme autorização.

---

# 63. Tarefa adicionada depois precisa ser auditada

Registrar:

- quem criou;
- quando;
- em qual momento da atividade;
- posição no fluxo;
- setor;
- dependências.

Isso permite entender mudanças de escopo.

---

# 64. Alteração de escopo

Quando o número ou natureza das tarefas muda significativamente, isso pode representar alteração de escopo.

A LPS deve preservar histórico suficiente para permitir análise futura.

No D0, não é necessário criar um módulo complexo de gestão de escopo.

O histórico já deve permitir identificar que a estrutura mudou.

---

# 65. Cancelamento

Uma atividade ou tarefa pode precisar ser cancelada.

Cancelamento não deve ser equivalente a exclusão.

Deve existir histórico.

Exemplo:

```text
Cancelada
Motivo:
Cliente desistiu
```

A definição detalhada de status será feita posteriormente.

---

# 66. Exclusão

Registros operacionais que já possuem histórico não devem ser apagados livremente.

Preferir:

- cancelar;
- inativar;
- encerrar;
- arquivar;

conforme o caso.

A exclusão deve ser restrita.

---

# 67. Bloqueio

Uma tarefa pode estar impossibilitada de avançar.

Exemplos:

```text
Aguardando cliente
```

```text
Aguardando fornecedor
```

```text
Aguardando decisão
```

```text
Aguardando documento
```

Bloqueio é diferente de trabalho em execução.

---

# 68. Bloqueio não elimina responsabilidade

Mesmo bloqueada, a tarefa continua pertencendo ao fluxo.

O dono continua acompanhando a atividade.

O setor continua ciente da situação.

---

# 69. Bloqueio deve gerar informação

Quando aplicável, registrar:

- início do bloqueio;
- fim;
- motivo;
- responsável;
- origem;
- observação.

Isso permitirá diferenciar:

```text
tempo trabalhando
```

de:

```text
tempo esperando
```

---

# 70. Espera

A LPS precisa considerar que grande parte do tempo de uma atividade pode ser espera.

Exemplo:

```text
Tempo total:
10 dias
```

Distribuição:

```text
Trabalho real:
6 horas

Fila:
2 dias

Fornecedor:
7 dias

Outras esperas:
1 dia
```

Esse é exatamente o tipo de informação que permite encontrar gargalos.

---

# 71. Tarefa aguardando terceiro

Uma tarefa pode depender de agente externo.

Exemplos:

- cliente;
- fornecedor;
- concessionária;
- transportadora;
- órgão público.

A LPS precisa conseguir registrar essa condição sem transformar o terceiro necessariamente em usuário do sistema.

---

# 72. A atividade pode continuar mesmo com uma tarefa aguardando

Dependendo das dependências, outras tarefas podem continuar.

Exemplo:

```text
Fornecedor preparando material
```

enquanto:

```text
Obra prepara área de recebimento
```

A LPS não deve presumir que toda atividade é estritamente linear.

---

# 73. Filas e fluxos são conceitos diferentes

Fluxo responde:

> Qual é o caminho da atividade?

Fila responde:

> Em qual ordem o setor pretende executar suas demandas?

Exemplo:

Fluxo:

```text
Engenharia
↓
Compras
↓
Financeiro
```

Fila de Compras:

```text
1. Demanda A
2. Demanda B
3. Sua demanda
4. Demanda D
```

Os conceitos devem permanecer separados.

---

# 74. Fluxo e prazo também são conceitos diferentes

O fluxo define sequência.

O prazo define tempo esperado ou comprometido.

A LPS precisa combinar ambos, mas não confundi-los.

---

# 75. Fluxo e responsabilidade também são diferentes

A tarefa pode mudar de setor.

O dono da atividade não muda automaticamente.

Essa separação precisa permanecer clara em toda a arquitetura.

---

# 76. Exemplo completo — solicitação de material

## Atividade

```text
Material disponível na obra
```

## Dono

```text
Engenheiro responsável pela necessidade
```

## Tarefas

```text
1. Elaborar lista
2. Validar especificações
3. Comprar
4. Pagar
5. Receber
6. Disponibilizar
```

## Fluxo

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
↓
Obra
```

## Possível devolução

```text
Compras
↓
Engenharia
```

Motivo:

```text
Especificação incompleta
```

Depois:

```text
Engenharia
↓
Compras
```

## Resultado final

```text
Material disponível na obra
```

Somente então a atividade pode ser concluída.

---

# 77. Exemplo completo — orçamento

## Atividade

```text
Orçamento entregue ao cliente
```

## Dono

```text
Responsável comercial
```

## Tarefas possíveis

```text
1. Conferir arquivos
2. Levantar quantitativos
3. Solicitar cotações
4. Levantar mão de obra
5. Revisar escopo
6. Validar preço
7. Aprovar internamente
8. Enviar ao cliente
```

## Participação

Pode envolver:

- Comercial;
- Engenharia;
- Suprimentos;
- Diretoria.

## Vários executores

A contagem pode ser realizada por mais de uma pessoa.

Os tempos devem ser registrados individualmente.

---

# 78. Exemplo completo — veículo

## Atividade

```text
Veículo disponível para utilização às 17h
```

## Dono

```text
Pessoa que precisa do veículo
```

## Setor responsável pela tarefa

```text
Almoxarifado / Frota
```

O solicitante pode entender que é urgente.

O setor pode possuir outras demandas mais prioritárias.

A LPS deve permitir acompanhar:

- posição;
- prazo;
- mudança;
- conclusão.

O fluxo não precisa expor as outras demandas.

---

# 79. Criação de atividade

No D0, criar atividade precisa ser simples.

O formulário não deve exigir dezenas de informações.

Os campos mínimos serão definidos no documento de experiência e no banco.

Conceitualmente, precisam existir dados suficientes para identificar:

- o que precisa ser resolvido;
- dono;
- contexto;
- prazo;
- setor inicial ou primeira tarefa;
- tarefas quando já conhecidas.

---

# 80. Criação de tarefas

As tarefas podem ser:

- criadas junto com a atividade;
- adicionadas depois;
- geradas a partir de fluxo padrão futuramente.

No D0, criação manual é suficiente.

---

# 81. Atividade sem todas as tarefas conhecidas

Permitido.

A realidade operacional nem sempre é completamente previsível.

Exemplo:

```text
Atividade:
Corrigir falha no equipamento
```

Primeira tarefa:

```text
Diagnosticar
```

O diagnóstico define as próximas tarefas.

---

# 82. Início da execução

Uma tarefa deve poder ser iniciada por pessoa autorizada.

O início deve gerar evento de auditoria.

Exemplo:

```text
Tarefa iniciada
Usuário: Jennifer
Data/hora: 09:12
```

---

# 83. Pausa

Uma tarefa pode ser pausada.

A pausa precisa permitir separar:

- tempo executado;
- tempo não executado.

A regra detalhada pertence ao documento de auditoria e tempo.

---

# 84. Retomada

Ao retomar:

```text
Pausa encerrada
↓
Nova sessão de trabalho
```

O sistema deve manter as sessões individuais.

---

# 85. Múltiplas sessões

Um executor pode trabalhar em uma tarefa várias vezes.

Exemplo:

```text
08:00–09:00
11:00–12:30
15:20–16:00
```

A LPS consolida o total.

---

# 86. Execução simultânea

Dois executores podem trabalhar ao mesmo tempo.

Exemplo:

```text
Ryan       08:00–10:00
Jennifer   08:30–09:30
```

Tempo decorrido máximo:

```text
2 horas
```

Horas-homem:

```text
3 horas
```

---

# 87. Transferência de executor

Uma tarefa pode mudar de executor.

Exemplo:

```text
Ryan
↓
Luan
```

Essa mudança deve ficar auditada.

Não apagar o trabalho anterior.

---

# 88. Inclusão de executor

Exemplo:

```text
Ryan
```

Depois:

```text
Ryan + Jennifer
```

A LPS registra a inclusão.

---

# 89. Remoção de executor

Se alguém deixar de participar, a remoção deve preservar:

- períodos trabalhados;
- histórico;
- ações realizadas.

A pessoa deixa de ser executor atual, mas não desaparece da história.

---

# 90. Mudança de setor

Uma tarefa pode ser encaminhada para outro setor quando o fluxo exigir.

A movimentação precisa registrar:

- setor de origem;
- setor de destino;
- responsável pela movimentação;
- data e hora;
- motivo quando necessário;
- etapa do fluxo.

---

# 91. Setor atual

A LPS precisa conseguir responder:

> Em qual setor esta tarefa está agora?

Mas também:

> Por quais setores ela já passou?

Estado atual e histórico devem coexistir.

---

# 92. Atividade com várias tarefas em setores diferentes

Uma atividade pode possuir tarefas simultaneamente em setores diferentes.

Exemplo:

```text
Atividade:
Preparar início da obra
```

Tarefas:

```text
Compras → comprar materiais
RH → mobilizar equipe
Engenharia → revisar projeto
Segurança → preparar documentação
```

Todas fazem parte da mesma atividade.

---

# 93. Dono acompanha o conjunto

Mesmo com tarefas simultâneas, a atividade continua com um único dono.

O dono precisa enxergar:

- tarefas abertas;
- concluídas;
- atrasadas;
- devolvidas;
- bloqueadas;
- setores envolvidos.

---

# 94. Atividade pode ter subtarefas?

Para o D0, evitar excesso de níveis.

A estrutura preferida é:

```text
Atividade
↓
Tarefa
```

Não criar inicialmente:

```text
Atividade
↓
Tarefa
↓
Subtarefa
↓
Subsubtarefa
```

Isso aumenta complexidade sem necessidade comprovada.

Se surgir necessidade real, revisar futuramente.

---

# 95. Checklists

Um checklist pode ser útil dentro de uma tarefa, mas não deve ser confundido com uma nova camada de responsabilidade.

Exemplo:

```text
Tarefa:
Conferir projeto

Checklist:
[ ] projeto abre
[ ] escala confere
[ ] disciplinas identificadas
```

A necessidade detalhada de checklist ainda não está consolidada.

Não faz parte obrigatória do D0 neste documento.

---

# 96. Tarefa recorrente

Recorrência pode existir no futuro.

Exemplo:

```text
Conferência semanal
```

Mas não é necessária para validar o núcleo inicial.

Manter fora do D0 até surgir necessidade clara.

---

# 97. Modelos de fluxo

Futuramente, empresas poderão possuir modelos.

Exemplo:

```text
Modelo:
Solicitação de compra
```

Ao selecionar:

```text
Criar tarefas padrão
↓
Aplicar sequência
↓
Aplicar setores
```

Essa é uma evolução natural depois de o fluxo manual estar validado.

---

# 98. Aprendizado a partir de modelos

A LPS poderá comparar:

```text
Fluxo padrão
```

com:

```text
Fluxo realmente executado
```

E descobrir:

- etapas normalmente adicionadas;
- etapas normalmente removidas;
- retornos;
- desvios;
- gargalos.

---

# 99. Fluxo planejado x fluxo realizado

Esse será um conceito importante.

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

A diferença gera aprendizado.

---

# 100. Prazo da atividade x prazo da tarefa

A atividade possui prazo relacionado ao resultado final.

As tarefas podem possuir prazos próprios.

No início, esses prazos podem ser informados manualmente.

A inteligência futura poderá sugerir distribuição.

---

# 101. A LPS não deve inventar prazos no D0

Se não existe histórico suficiente, a pessoa informa.

Exemplo:

```text
Atividade:
Prazo final: 20/09
```

Tarefas:

```text
Engenharia: 13/09
Compras: 15/09
Financeiro: 16/09
Fornecedor: 20/09
```

A LPS registra.

Depois aprende.

---

# 102. Impacto do fluxo no prazo

O sistema deverá futuramente conseguir perceber:

```text
Prazo final = 10 dias
Fornecedor normalmente = 7 dias
```

Restam:

```text
3 dias para etapas internas
```

Essa inteligência depende de histórico.

Não deve ser simulada artificialmente no D0.

---

# 103. Auditoria é parte do fluxo

O fluxo não pode existir apenas visualmente.

Cada evento precisa alimentar auditoria.

Exemplos:

```text
Criado
```

```text
Tarefa adicionada
```

```text
Executor atribuído
```

```text
Iniciado
```

```text
Movido de setor
```

```text
Devolvido
```

```text
Prazo alterado
```

```text
Concluído
```

---

# 104. O histórico é imutável como fato

Correções podem existir.

Mas fatos registrados não devem simplesmente desaparecer.

Se algo estiver errado, registrar:

```text
correção
```

em vez de apagar silenciosamente a história.

---

# 105. Linha do tempo da atividade

A atividade deve possuir uma timeline consolidada.

Exemplo:

```text
08:00 — atividade criada
08:05 — primeira tarefa criada
10:17 — primeira ação
11:00 — Engenharia concluiu
11:01 — enviada para Compras
14:30 — Compras iniciou
16:00 — devolvida para Engenharia
16:01 — motivo: informação incompleta
Dia seguinte 08:30 — corrigida
08:40 — reenviada para Compras
10:20 — Compras concluiu
...
```

---

# 106. Linha do tempo da tarefa

Cada tarefa também deve possuir seu próprio histórico.

Isso permite analisar:

- a atividade como um todo;
- cada componente separadamente.

---

# 107. Dados mínimos para aprendizado futuro

Cada tarefa deve gerar, quando aplicável:

- tipo;
- setor;
- executores;
- início;
- fim;
- sessões de trabalho;
- tempo em fila;
- tempo bloqueado;
- prazo;
- devoluções;
- motivos;
- movimentações;
- conclusão.

Esses dados formam a base da inteligência futura.

---

# 108. Comparação de tarefas

Com histórico, a LPS poderá comparar tarefas do mesmo tipo.

Exemplo:

```text
Levantamento de quantitativos

Jennifer:
média 1h15

Ryan:
média 2h50
```

Essa diferença não deve gerar conclusão automática de desempenho.

Pode indicar necessidade de analisar:

- complexidade;
- treinamento;
- padrão;
- contexto;
- qualidade.

---

# 109. Objetivo da comparação

A comparação deve apoiar melhoria.

Não criar apenas ranking.

A pergunta correta é:

> O que podemos melhorar no processo?

---

# 110. Gargalo de fluxo

A LPS deve permitir identificar gargalo por:

- tempo em fila;
- tempo em execução;
- tempo bloqueado;
- volume;
- devolução;
- capacidade;
- dependência.

O fluxo é a base para isso.

---

# 111. Gargalo não significa necessariamente setor ruim

Exemplo:

Compras pode aparecer como maior duração.

Mas o motivo pode ser:

```text
Fornecedor com prazo de 7 dias
```

Por isso, a LPS precisa separar tempos e contextos.

---

# 112. Motivos de espera

Futuramente pode existir classificação de espera.

Exemplos:

- fila interna;
- cliente;
- fornecedor;
- aprovação;
- informação;
- transporte;
- decisão;
- recurso;
- terceiro.

Essa classificação deve ser avaliada no documento de auditoria.

---

# 113. Alteração de dono

A regra geral é um dono por atividade.

Pode existir troca de dono.

Exemplo:

```text
Paulo
↓
Rian
```

A mudança deve ser:

- autorizada;
- auditada;
- registrada com data e hora.

Nunca existir dois donos ativos simultaneamente.

---

# 114. Dono anterior permanece no histórico

Depois da transferência:

```text
Dono atual:
Rian
```

Histórico:

```text
Paulo → Rian
```

Isso preserva accountability.

---

# 115. Atividade criada por uma pessoa e pertencente a outra

Permitido.

Exemplo:

```text
Criado por:
Jennifer

Dono:
Paulo
```

Criador e dono são conceitos diferentes.

---

# 116. Quem criou não é necessariamente quem executa

Da mesma forma:

```text
Criador:
Paulo

Executor:
Ryan
```

A LPS deve separar esses papéis.

---

# 117. Solicitante x dono

No D0, muitas vezes serão a mesma pessoa.

Mas conceitualmente podem ser diferentes.

Exemplo:

```text
Solicitante:
Diretor

Dono:
Gerente responsável por acompanhar
```

A necessidade de separar campos será validada no banco.

Este documento apenas reconhece que os conceitos podem ser diferentes.

---

# 118. Resultado esperado

Toda atividade deve possuir resultado suficientemente claro para permitir encerramento.

Exemplo ruim:

```text
Ver material
```

Exemplo melhor:

```text
Material disponível para instalação
```

---

# 119. Critério de conclusão

Sempre que possível, o critério deve ser verificável.

Exemplo:

```text
Atividade:
Enviar orçamento

Critério:
Proposta enviada ao cliente
```

Isso reduz conclusão subjetiva.

---

# 120. Atividade concluída x atividade aprovada

Esses conceitos podem ser diferentes.

Exemplo:

```text
Tarefa concluída:
Orçamento elaborado
```

Depois:

```text
Aprovação:
Diretoria valida
```

Aprovações detalhadas pertencem a documento posterior.

---

# 121. Cancelamento por perda de necessidade

Exemplo:

```text
Cliente desistiu
```

A atividade pode ser cancelada.

Esse resultado precisa permanecer registrado para análise.

---

# 122. Atividades abandonadas não devem desaparecer

Se algo foi iniciado e depois deixou de fazer sentido, o histórico continua útil.

Pode mostrar:

- horas gastas;
- motivo do cancelamento;
- setor envolvido;
- desperdício.

---

# 123. Configuração de quem pode alterar fluxo

Nem todo usuário pode:

- adicionar tarefa;
- excluir tarefa;
- alterar ordem;
- alterar setor;
- devolver;
- concluir;
- reabrir.

Essas ações serão controladas por permissões.

---

# 124. Configuração não muda princípio

Mesmo que a empresa configure permissões diferentes, os conceitos continuam os mesmos:

- atividade;
- dono;
- tarefa;
- executor;
- setor;
- fluxo;
- histórico.

---

# 125. Simplicidade de uso

Embora a estrutura seja completa, a interface precisa ser simples.

Exemplo:

Para devolver uma tarefa:

```text
Devolver
↓
Selecionar destino
↓
Selecionar motivo
↓
Observação opcional/obrigatória conforme regra
↓
Confirmar
```

O sistema registra o restante automaticamente.

---

# 126. Automação de auditoria

O usuário não deve preencher manualmente:

```text
Data da devolução
Hora da devolução
Usuário que devolveu
Setor de origem
```

A LPS já conhece essas informações.

O sistema deve registrar automaticamente.

---

# 127. Dados como subproduto da ação

Regra:

> O usuário executa a ação; a LPS registra o evento.

Exemplo:

Ao clicar:

```text
Iniciar
```

o sistema registra:

- usuário;
- data;
- hora;
- tarefa;
- setor.

---

# 128. Fluxo não deve exigir burocracia excessiva

Se cada mudança exigir um formulário longo, os usuários evitarão utilizar o sistema.

O equilíbrio é:

```text
mínima entrada manual
+
máxima captura automática
```

---

# 129. Histórico de alterações do fluxo

Deve ser possível saber:

- quem adicionou tarefa;
- quem removeu/cancelou;
- quem reordenou;
- quem mudou setor;
- quem mudou dependência;
- quem devolveu;
- quem concluiu.

---

# 130. Remover tarefa x cancelar tarefa

Se uma tarefa nunca foi utilizada e não possui histórico, pode existir exclusão controlada.

Se já possui movimentações, preferir cancelamento.

A regra técnica será definida no banco.

---

# 131. Fluxos reutilizáveis

Depois de validados, fluxos podem se tornar modelos reutilizáveis.

Exemplo:

```text
Fluxo:
Solicitação de compra padrão
```

Isso reduz trabalho de cadastro.

---

# 132. Reutilização não deve congelar o processo

O modelo ajuda.

Não impede melhoria.

A empresa pode revisar o fluxo padrão conforme aprende.

---

# 133. Versionamento de fluxo

Futuramente, fluxos padrões podem precisar de versões.

Exemplo:

```text
Solicitação de compra v1
Solicitação de compra v2
```

Atividades antigas continuam vinculadas ao fluxo que utilizaram.

Não é prioridade do D0, mas a arquitetura não deve impedir evolução futura.

---

# 134. Fluxo recomendado pela LPS

Futuramente, com histórico suficiente:

```text
Atividades semelhantes seguiram este fluxo em 82% dos casos.
```

A LPS pode sugerir.

Esse comportamento pertence à etapa de inteligência.

---

# 135. Fluxo entre empresas

O D0 deve priorizar aprendizado dentro da própria organização.

Sugestões baseadas em outras empresas exigem discussão de:

- anonimização;
- autorização;
- privacidade;
- comparabilidade.

Não fazem parte deste documento operacional inicial.

---

# 136. Atividade como unidade de aprendizado

A atividade reúne todo o contexto.

Ela permite correlacionar:

- tarefas;
- setores;
- pessoas;
- tempos;
- mensagens;
- devoluções;
- prazos;
- conclusão.

Por isso, ela é a unidade principal de acompanhamento.

---

# 137. Tarefa como unidade de execução

A tarefa é o nível mais adequado para registrar:

- executor;
- setor;
- tempo;
- status;
- devolução;
- dependência;
- conclusão.

---

# 138. Evento como unidade de auditoria

Cada mudança relevante gera evento.

Conceitualmente:

```text
atividade criada
tarefa criada
executor atribuído
tarefa iniciada
tarefa pausada
tarefa devolvida
tarefa movida
prazo proposto
tarefa concluída
atividade concluída
```

---

# 139. Três níveis conceituais

A LPS deve separar:

```text
RESULTADO
↓
TRABALHO
↓
HISTÓRICO
```

Onde:

```text
Atividade = resultado
Tarefa = trabalho
Evento = histórico
```

Essa é uma das regras mais importantes do desenho.

---

# 140. O que não deve acontecer

Evitar estruturas em que:

```text
Atividade = qualquer item genérico
```

e não exista distinção clara entre:

- resultado;
- tarefa;
- evento.

Isso dificulta gestão e aprendizado.

---

# 141. Exemplo de modelagem conceitual correta

```text
ATIVIDADE
Orçamento entregue ao cliente

Dono:
Paulo

TAREFA 1
Conferir projetos
Setor: Comercial
Executor: Rian

TAREFA 2
Levantar quantitativos
Setor: Comercial
Executores: Jennifer + Arthur

TAREFA 3
Solicitar cotações
Setor: Suprimentos

TAREFA 4
Revisar
Setor: Comercial
Executor: Paulo

RESULTADO
Proposta enviada
```

---

# 142. Exemplo de modelagem ruim

```text
Atividade:
Conferir projeto

Atividade:
Levantar quantitativo

Atividade:
Pedir preço

Atividade:
Revisar

Atividade:
Enviar
```

Nesse modelo, perde-se a visão do resultado maior.

A LPS ficaria parecida apenas com uma lista de tarefas.

---

# 143. Quando algo pode ser uma atividade independente

Se o item possui:

- resultado próprio;
- dono próprio;
- ciclo próprio;
- acompanhamento próprio;

pode ser atividade.

Exemplo:

```text
Regularizar documentação do equipamento
```

Mesmo que isso faça parte de um projeto maior.

---

# 144. Critério prático para diferenciar atividade de tarefa

Perguntar:

> Existe um resultado que alguém precisa acompanhar até estar resolvido?

Se sim, tende a ser atividade.

Perguntar:

> Isso é apenas uma parte necessária para chegar a esse resultado?

Se sim, tende a ser tarefa.

---

# 145. Fluxos diferentes dentro da mesma atividade

Uma atividade pode possuir ramos diferentes.

Exemplo:

```text
Atividade:
Mobilizar obra
```

Ramo 1:

```text
Engenharia
↓
Projeto
```

Ramo 2:

```text
RH
↓
Equipe
```

Ramo 3:

```text
Suprimentos
↓
Materiais
```

Todos convergem para:

```text
Obra mobilizada
```

---

# 146. Convergência

Quando várias tarefas precisam terminar para uma próxima começar:

```text
Tarefa A concluída
+
Tarefa B concluída
+
Tarefa C concluída
↓
Tarefa D liberada
```

A arquitetura deve permitir isso.

A interface detalhada pode ser simplificada inicialmente.

---

# 147. Divergência

Uma tarefa pode liberar várias outras.

Exemplo:

```text
Projeto aprovado
↓
Compras
↓
Planejamento
↓
Execução
```

onde mais de uma tarefa pode iniciar depois da aprovação.

---

# 148. Dependência como dado estruturado

Não confiar apenas em texto como:

> “Esperar Compras terminar.”

A dependência deve ser registrada de forma estruturada sempre que for necessária ao fluxo.

---

# 149. Dependência não precisa impedir exceção absoluta

Futuramente, permissões podem permitir avançar mesmo com dependência pendente, registrando justificativa.

Esse comportamento ainda precisa ser detalhado.

Não deve ser implementado sem necessidade.

---

# 150. Padrão inicial recomendado

Para o D0, priorizar:

- fluxos simples;
- ordem clara;
- dependências simples;
- devolução;
- paralelismo quando realmente necessário.

Evitar motor de workflow excessivamente complexo antes da validação operacional.

---

# 151. Não construir um BPM completo no D0

BPM significa **Business Process Management**, ou gestão de processos de negócio.

A LPS não precisa nascer com:

- diagramador complexo;
- dezenas de gateways;
- linguagem BPMN completa;
- regras condicionais sofisticadas;
- motor de automação empresarial genérico.

Precisamos primeiro provar:

```text
atividade
→ tarefas
→ setores
→ execução
→ retorno
→ conclusão
→ dados
```

---

# 152. Fluxo precisa ser compreensível por pessoas comuns

Um gestor deve conseguir entender:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

sem estudar uma linguagem técnica.

---

# 153. Padrão não significa burocracia

O fluxo existe para:

- orientar;
- dar previsibilidade;
- medir;
- aprender.

Não para criar etapas sem valor.

---

# 154. Alterações de fluxo geram aprendizado

Se usuários frequentemente ignoram uma etapa, isso pode indicar:

- etapa desnecessária;
- treinamento ruim;
- fluxo incorreto;
- exceção frequente.

A LPS deve permitir análise futura.

---

# 155. Tarefas adicionadas fora do fluxo padrão

Devem ficar registradas.

Exemplo:

Fluxo padrão:

```text
A
↓
B
↓
C
```

Execução real:

```text
A
↓
X
↓
B
↓
C
```

Isso é dado útil.

---

# 156. Tarefas puladas

Se uma tarefa padrão não for necessária, pode haver:

```text
Pular
```

ou:

```text
Não aplicável
```

conforme regra futura.

O histórico deve preservar que ela existia no fluxo e não foi executada.

---

# 157. Motivo para pular

Para tarefas relevantes, pode ser útil exigir motivo.

Ainda não é decisão consolidada para o D0.

Deixar para detalhamento posterior.

---

# 158. Fluxo obrigatório x flexível

Futuramente, um modelo pode ser:

```text
obrigatório
```

ou:

```text
flexível
```

conforme configuração.

No início, priorizar flexibilidade com auditoria.

---

# 159. A LPS deve mostrar o agora e o histórico

Na atividade, o usuário precisa saber:

```text
Onde está agora?
```

e também:

```text
Como chegou até aqui?
```

Essas duas visões são igualmente importantes.

---

# 160. Estado atual

Exemplo:

```text
Tarefa atual:
Pagamento

Setor:
Financeiro

Status:
Aguardando execução
```

---

# 161. Histórico

Exemplo:

```text
Engenharia → 4h
Compras → 2d 3h
Engenharia → 5h
Compras → 1d
Financeiro → atual
```

---

# 162. Visão consolidada

A atividade deve conseguir mostrar:

- progresso;
- tarefas;
- responsáveis;
- setores;
- prazos;
- histórico;
- tempo;
- devoluções;
- conversas.

A tela será definida posteriormente.

---

# 163. Indicadores diretamente derivados do fluxo

Com esta estrutura, será possível calcular:

- tempo total;
- tempo até primeira ação;
- tempo por tarefa;
- tempo por setor;
- horas-homem;
- número de executores;
- número de devoluções;
- número de setores;
- quantidade de tarefas;
- tarefas mais demoradas;
- tarefas mais rápidas;
- etapas mais devolvidas;
- tempo de espera.

---

# 164. Indicadores não devem ser cadastrados manualmente

Sempre que possível, devem ser derivados dos eventos.

Exemplo:

```text
Tempo no setor
=
saída - entrada
```

em vez de perguntar ao usuário:

> Quantas horas ficou neste setor?

---

# 165. Qualidade dos dados

A inteligência futura depende de:

- timestamps corretos;
- autoria correta;
- motivos bem definidos;
- movimentações registradas;
- tarefas realmente utilizadas;
- usuários utilizando início/pausa/conclusão adequadamente.

Por isso, o fluxo precisa ser simples o suficiente para ser adotado.

---

# 166. Conclusão automática da atividade

Não deve ser presumida apenas porque todas as tarefas estão concluídas, sem regra definida.

Pode existir:

```text
Todas as tarefas concluídas
↓
Aguardando confirmação final
```

quando o resultado precisa ser validado.

A regra será detalhada futuramente.

---

# 167. Conclusão automática futura

Para atividades muito padronizadas, pode ser possível configurar:

```text
Concluir atividade quando todas as tarefas obrigatórias estiverem concluídas.
```

Isso não precisa ser regra global.

---

# 168. Fluxo e notificações

Eventos de fluxo podem gerar notificações.

Exemplos:

- tarefa atribuída;
- devolvida;
- mudou de setor;
- novo prazo proposto;
- concluída;
- atividade concluída.

As regras pertencem ao documento de notificações.

---

# 169. Fluxo e conversas

Cada atividade pode possuir conversa contextual.

Cada tarefa pode possuir conversa contextual.

A comunicação acompanha o trabalho.

---

# 170. Mensagem não substitui movimentação

Exemplo:

Mensagem:

> “Estou devolvendo para Engenharia.”

Isso não deve, sozinho, mover a tarefa.

A pessoa precisa executar a ação estruturada:

```text
Devolver
```

Assim o sistema registra corretamente.

---

# 171. Fluxo e permissões

Ações como:

- criar;
- assumir;
- atribuir;
- devolver;
- mover;
- cancelar;
- concluir;
- reabrir;
- alterar fluxo;

dependem de autorização.

A lista detalhada pertence ao documento de acessos.

---

# 172. Fluxo e fila

Quando uma tarefa entra em um setor, ela pode entrar na fila daquele setor.

A posição é tratada no documento:

`03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Este documento apenas define que a entrada em um setor pode gerar entrada na fila.

---

# 173. Entrada em fila

Exemplo:

```text
Compras recebeu tarefa
↓
Tarefa entra na fila de Compras
↓
Posição inicial registrada
```

---

# 174. Saída da fila

Quando o setor começa a executar ou conclui conforme regra:

```text
Tarefa sai da condição de aguardando
```

Isso permite medir:

```text
tempo em fila
```

---

# 175. Tarefa pode voltar para fila

Se for pausada ou devolvida, conforme comportamento definido, pode existir nova passagem pela fila.

Cada passagem precisa ficar registrada.

---

# 176. Passagens repetidas

Exemplo:

```text
Compras — fila
Compras — execução
Engenharia — correção
Compras — fila novamente
Compras — execução
```

A LPS deve medir cada passagem.

---

# 177. Fluxo e escalonamento

Quando uma tarefa fica parada, atrasa ou entra em conflito de prazo, pode gerar escalonamento.

Isso não altera o conceito de dono.

O escalonamento é mecanismo de gestão.

---

# 178. Fluxo e impacto

Impacto pode influenciar:

- prioridade;
- notificação;
- escalonamento.

Mas impacto não substitui fila.

A decisão detalhada será tratada em outro documento.

---

# 179. Responsabilidade do setor

Ao receber uma tarefa, o setor passa a ter responsabilidade operacional sobre aquela etapa.

Isso não significa que o dono da atividade perdeu responsabilidade pelo resultado.

---

# 180. Responsabilidade do executor

Ao assumir, o executor passa a responder pela execução que assumiu.

Se houver vários executores, a divisão operacional pode ser compartilhada.

A atividade continua com um único dono.

---

# 181. Regra de clareza

A qualquer momento, deve ser possível responder:

```text
Quem é o dono da atividade?
```

```text
Qual tarefa está em andamento?
```

```text
Qual setor está responsável?
```

```text
Quem está executando?
```

```text
Qual o próximo passo?
```

---

# 182. Próximo passo

O sistema deve conseguir identificar qual tarefa ou conjunto de tarefas está liberado para avançar.

Isso é importante para reduzir incerteza.

---

# 183. Fluxo incompleto

Se uma atividade possui tarefas futuras ainda não definidas, o sistema deve permitir continuidade.

Não exigir que o processo inteiro seja conhecido no início.

---

# 184. Aprendizado do fluxo incompleto

Se isso acontecer frequentemente, a LPS pode futuramente sugerir:

> Este tipo de atividade normalmente adiciona estas tarefas depois.

Isso pertence à inteligência futura.

---

# 185. Atividade simples

Nem toda atividade precisa de fluxo complexo.

Exemplo:

```text
Atividade:
Enviar documento ao cliente

Tarefa:
Preparar e enviar documento
```

Pode existir apenas uma tarefa.

A LPS deve atender desde o simples ao mais complexo.

---

# 186. Não obrigar complexidade

Se uma atividade exige apenas uma tarefa, não criar etapas artificiais.

O sistema deve adaptar-se à necessidade.

---

# 187. Fluxo precisa servir a gestão

Pergunta de validação:

> Esta etapa ajuda a executar, monitorar, controlar ou aprender?

Se não, talvez não deva existir.

---

# 188. Gestão baseada em fluxo

A visão futura do gestor deve permitir identificar:

```text
volume entrando
volume saindo
fila
tempo
retorno
atraso
capacidade
```

A estrutura deste documento precisa sustentar isso.

---

# 189. Fluxo como fonte de conhecimento

Depois de meses, o histórico deverá permitir perguntas como:

- Qual atividade deste tipo dura menos?
- Qual dura mais?
- Qual tarefa costuma consumir mais tempo?
- Onde mais volta?
- Qual setor acumula maior espera?
- Quantas pessoas normalmente participam?
- Quais caminhos geram menor tempo total?
- Onde existem desvios do fluxo padrão?

---

# 190. A LPS precisa preservar exceções

Exceções são dados.

Se um processo padrão quase sempre muda, isso é informação sobre o processo.

Não esconder exceções apenas para manter um fluxo “bonito”.

---

# 191. Auditoria de exceções

Quando uma pessoa autorizada quebra o fluxo esperado, registrar:

- o que foi alterado;
- quem alterou;
- quando;
- motivo quando aplicável.

---

# 192. Atividade como processo vivo

Uma atividade não é apenas um registro criado no início.

Ela evolui.

Pode ganhar:

- tarefas;
- executores;
- retornos;
- bloqueios;
- novos prazos;
- decisões;
- alterações.

A LPS precisa acompanhar essa evolução sem perder a história.

---

# 193. Estado atual é uma fotografia

Exemplo:

```text
Setor atual:
Financeiro
```

Isso é apenas a fotografia atual.

---

# 194. Histórico é o filme

Exemplo:

```text
Engenharia
↓
Compras
↓
Engenharia
↓
Compras
↓
Financeiro
```

Esse filme é o que permite aprendizado.

---

# 195. Regra de ouro para atividades

> **A atividade só termina quando o resultado que a originou estiver resolvido.**

---

# 196. Regra de ouro para tarefas

> **A tarefa representa trabalho necessário para fazer a atividade avançar.**

---

# 197. Regra de ouro para fluxo

> **O fluxo deve registrar o caminho real percorrido, inclusive retornos e desvios.**

---

# 198. Regra de ouro para responsabilidade

> **Uma atividade possui um único dono, independentemente de quantas pessoas ou setores participem.**

---

# 199. Regra de ouro para auditoria

> **O sistema deve permitir reconstruir o que aconteceu sem depender da memória das pessoas.**

---

# 200. Regra de ouro para aprendizado

> **Primeiro registrar corretamente. Depois aprender com os dados.**

---

# 201. O que pertence ao D0 neste documento

O D0 precisa suportar:

- criação de atividade;
- dono único;
- criação de tarefas;
- setor por tarefa;
- tarefa sem executor inicial;
- um ou vários executores;
- ordem;
- dependências simples;
- fluxo entre setores;
- movimentação;
- retorno;
- motivo de devolução;
- início;
- pausa;
- retomada;
- conclusão de tarefa;
- conclusão de atividade;
- cancelamento;
- histórico;
- auditoria;
- alteração controlada de fluxo.

---

# 202. O que pode ficar depois do D0

Pode ficar para evolução:

- motor BPM completo;
- regras condicionais complexas;
- workflow visual avançado;
- sugestão automática de tarefas;
- sugestão automática de fluxo;
- geração de fluxo por IA;
- cálculo automático de prazo;
- versionamento avançado de modelos;
- recorrência complexa;
- subníveis ilimitados;
- automação entre sistemas externos;
- benchmarking entre empresas.

---

# 203. Decisões consolidadas

## Atividade

- representa um resultado ou problema;
- possui um único dono;
- pode possuir várias tarefas;
- pode atravessar vários setores;
- termina quando o resultado é alcançado.

## Dono

- é único;
- acompanha até o fim;
- não precisa executar tudo;
- permanece responsável mesmo quando o trabalho passa para outro setor;
- pode ser alterado, mas nunca existirão dois donos ativos simultaneamente.

## Tarefa

- representa uma parte do trabalho;
- pertence a uma atividade;
- pode possuir setor;
- pode possuir nenhum, um ou vários executores;
- pode possuir prazo;
- pode depender de outra;
- pode ser devolvida;
- pode ser concluída sem concluir a atividade.

## Executor

- é quem trabalha;
- pode ser mais de uma pessoa;
- tempo é registrado por pessoa;
- histórico não é apagado quando executor muda.

## Setor

- é configurável;
- não é fixo no código;
- representa responsabilidade operacional da tarefa;
- uma atividade pode envolver vários setores.

## Fluxo

- inicialmente será criado manualmente;
- pode possuir sequência;
- pode possuir paralelismo;
- pode possuir retorno;
- precisa preservar o caminho real;
- pode futuramente ser reutilizado como modelo;
- pode futuramente ser sugerido pela LPS.

## Devolução

- é permitida;
- deve ser auditada;
- exige motivo;
- pode retornar para etapa ou setor anterior;
- não apaga a passagem anterior.

## Conclusão

- tarefa concluída não significa atividade concluída;
- atividade termina quando o resultado estiver resolvido;
- conclusão precisa ficar auditada;
- reabertura pode existir com autorização e histórico.

---

# 204. Decisões ainda pendentes

As decisões abaixo ainda precisam ser detalhadas em documentos futuros:

- nomes e quantidade exata de status;
- quais eventos contam como primeira ação;
- regras exatas para conclusão automática;
- quando o dono precisa aprovar encerramento;
- comportamento exato de dependência bloqueante;
- possibilidade de ignorar dependência com justificativa;
- tipos de bloqueio;
- motivos padronizados de espera;
- necessidade de checklist;
- comportamento de tarefas “não aplicáveis”;
- regras de cancelamento e exclusão;
- versionamento de modelos de fluxo;
- permissões exatas de cada ação;
- comportamento da tarefa ao entrar e sair da fila.

---

# 205. Relação com os próximos documentos

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Detalhará:

- entrada em fila;
- posição;
- alteração da fila;
- prazo solicitado;
- prazo comprometido;
- negociação;
- escalonamento.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

Detalhará:

- eventos;
- sessões;
- tempo;
- horas-homem;
- espera;
- métricas;
- timeline.

## `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Detalhará:

- quem pode criar;
- quem pode mover;
- quem pode atribuir;
- quem pode devolver;
- quem pode alterar fluxo;
- quem pode concluir.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Detalhará:

- conversas;
- avisos;
- eventos notificáveis;
- preferências.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Detalhará:

- aprendizado sobre duração;
- padrões de fluxo;
- devoluções;
- sugestões futuras;
- previsões.

## `08_BANCO_DE_DADOS.md`

Traduzirá este documento para:

- tabelas;
- relacionamentos;
- chaves;
- eventos;
- integridade.

---

# 206. Resumo funcional

A essência deste documento pode ser representada assim:

```text
ALGUÉM PRECISA DE UM RESULTADO
↓
CRIA UMA ATIVIDADE
↓
DEFINE UM ÚNICO DONO
↓
CRIA OU APLICA TAREFAS
↓
CADA TAREFA POSSUI UM SETOR
↓
0..N PESSOAS EXECUTAM
↓
O TRABALHO PERCORRE O FLUXO
↓
PODE HAVER RETORNO
↓
TODO RETORNO TEM MOTIVO
↓
TODO EVENTO RELEVANTE É AUDITADO
↓
AS TAREFAS TERMINAM
↓
O RESULTADO É ALCANÇADO
↓
A ATIVIDADE É CONCLUÍDA
↓
O HISTÓRICO PASSA A ALIMENTAR APRENDIZADO
```

---

# 207. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação do núcleo de atividades, tarefas e fluxos da LPS |

---

# 208. Encerramento

O núcleo da LPS não é simplesmente uma lista de tarefas.

É a relação entre:

```text
resultado
+
responsabilidade
+
trabalho
+
setores
+
pessoas
+
tempo
+
movimentação
+
retorno
+
histórico
```

A qualidade da LPS dependerá de conseguir representar esse fluxo de forma simples para quem executa e detalhada o suficiente para quem gerencia.

O D0 deve priorizar esse equilíbrio.

Se a LPS registrar corretamente o caminho real das atividades, ela terá base para identificar gargalos, medir capacidade e aprender com a própria operação.
