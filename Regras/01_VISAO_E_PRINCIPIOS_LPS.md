# 01 — Visão e Princípios da LPS

> Documento de definição do produto: o que a LPS é, qual problema resolve, quais princípios orientam o desenvolvimento e quais limites não devem ser ultrapassados no D0.

---

## 1. Objetivo deste documento

Este documento define a visão da LPS antes de qualquer decisão detalhada de tela, banco de dados ou implementação.

Ele deve responder:

- o que estamos construindo;
- para quem estamos construindo;
- qual problema a LPS resolve;
- qual comportamento o produto deve incentivar;
- quais princípios são obrigatórios;
- o que deve ser configurável;
- o que deve permanecer estruturalmente fixo;
- o que a LPS não pretende ser;
- quais limites devem ser respeitados no D0.

Sempre que existir dúvida sobre uma nova funcionalidade, este documento deve ser usado como filtro.

A pergunta principal é:

> **Essa funcionalidade fortalece a gestão do trabalho, a transparência, o monitoramento, o controle ou o aprendizado da operação?**

Se não fortalecer nenhum desses pontos, provavelmente não pertence ao núcleo da LPS.

---

# 2. Definição da LPS

A LPS é uma plataforma de gestão do trabalho que organiza atividades e tarefas, torna filas e responsabilidades visíveis, registra o que acontece durante a execução e transforma esse histórico em informação para gestão.

A LPS deve permitir que uma empresa saiba:

- o que precisa ser feito;
- quem é o dono do resultado;
- quais tarefas compõem uma atividade;
- qual setor está responsável por cada tarefa;
- quem está executando;
- onde a demanda está;
- em qual posição da fila está;
- qual prazo foi solicitado;
- qual prazo foi comprometido;
- quanto tempo ficou esperando;
- quanto tempo foi efetivamente trabalhado;
- por onde passou;
- onde voltou;
- por que voltou;
- onde ficou mais tempo;
- onde existem gargalos;
- quais processos geram mais retrabalho;
- quais tarefas normalmente atrasam;
- quais padrões começam a surgir ao longo do tempo.

A LPS não deve apenas registrar que algo está “em andamento”.

Ela deve construir uma história operacional confiável.

---

# 3. Problema que a LPS resolve

## 3.1 Falta de visibilidade sobre o trabalho

Em muitas empresas, a demanda existe, mas sua situação real fica espalhada entre:

- conversas;
- mensagens;
- e-mails;
- planilhas;
- memória das pessoas;
- reuniões;
- sistemas diferentes.

O solicitante frequentemente sabe apenas:

> “Eu pedi.”

Mas não sabe:

- se alguém viu;
- quando será iniciado;
- quem está responsável;
- quantas demandas existem antes;
- se o prazo é viável;
- se a tarefa foi devolvida;
- se houve um impedimento;
- se mudou de responsável;
- se está próxima da conclusão.

A consequência é cobrança manual constante.

---

## 3.2 Falta de transparência das filas

Quem pede uma atividade normalmente enxerga apenas o próprio problema.

Quem administra o setor enxerga várias demandas simultaneamente.

Isso cria conflito.

Exemplo:

Para uma pessoa, ter um veículo disponível no final do dia pode ser a necessidade mais urgente.

Para o Almoxarifado, naquele mesmo momento, pode existir um caminhão com dezenas de bobinas aguardando descarga.

A LPS não deve transformar o solicitante em gestor da fila de outro setor.

Ela deve dar transparência suficiente para reduzir a incerteza.

Exemplo:

```text
Sua posição: 4 de 17
Status: aguardando execução
Prazo comprometido: hoje às 16h20
```

O solicitante não precisa visualizar todos os detalhes das outras 16 demandas.

---

## 3.3 Responsabilidade difusa

Quando uma atividade passa por várias pessoas e setores, surge facilmente a frase:

> “Agora não está mais comigo.”

A LPS deve evitar esse comportamento.

Uma atividade possui um único dono.

Esse dono continua responsável pelo acompanhamento do resultado até que o problema esteja resolvido.

As tarefas podem passar por diversos setores e possuir vários executores.

A responsabilidade pelo resultado final, porém, permanece clara.

---

## 3.4 Falta de dados sobre onde o tempo é perdido

Uma atividade pode levar dez dias para ser concluída.

Isso, isoladamente, diz pouco.

É necessário saber:

- quanto tempo levou para alguém agir pela primeira vez;
- quanto tempo ficou em fila;
- quanto tempo houve de trabalho real;
- quanto tempo ficou aguardando informação;
- quanto tempo permaneceu em cada setor;
- quantas vezes foi devolvida;
- por que foi devolvida;
- quanto tempo ficou com fornecedor;
- quanto tempo cada pessoa trabalhou;
- onde o prazo foi consumido.

Sem isso, “gargalo” vira opinião.

A LPS deve transformar gargalo em evidência.

---

## 3.5 Prazos definidos sem capacidade real

Quem solicita tende a definir o prazo com base em sua necessidade.

Quem executa conhece sua capacidade e sua fila.

Os dois pontos de vista são legítimos.

Por isso, a LPS deve diferenciar:

**Prazo solicitado**

> Quando o solicitante precisa.

**Prazo comprometido**

> Quando o setor executor declara que consegue entregar.

Essa diferença precisa ficar registrada.

Se o setor não consegue cumprir o prazo solicitado, ele deve poder propor outro prazo.

Se houver conflito, o sistema deve suportar negociação e escalonamento.

---

## 3.6 Trabalho invisível e retrabalho invisível

Muitas vezes a empresa sabe que algo atrasou, mas não sabe quantas pessoas trabalharam, quantas vezes voltou ou quantas horas foram consumidas.

Exemplo:

```text
Ryan       2h10
Jennifer   1h20
Luan       0h50
```

Tempo total de trabalho:

```text
4h20
```

Mesmo que a tarefa tenha ocorrido em uma janela de apenas duas horas do relógio.

A LPS precisa diferenciar:

- tempo decorrido;
- tempo trabalhado;
- horas-homem;
- tempo de espera.

---

## 3.7 Conhecimento operacional que não se acumula

Uma empresa pode executar o mesmo processo centenas de vezes e continuar planejando como se fosse a primeira vez.

Exemplo:

Após dezenas de solicitações de compra, a organização deveria conseguir saber:

- quanto tempo Engenharia normalmente leva;
- quanto tempo Compras normalmente leva;
- quanto tempo Financeiro normalmente leva;
- quanto tempo o fornecedor normalmente leva;
- quais informações faltam com maior frequência;
- quais devoluções se repetem;
- onde o processo costuma atrasar.

A LPS deve transformar execução passada em aprendizado futuro.

---

# 4. Proposta de valor

A proposta de valor central da LPS é:

> **Dar visibilidade ao trabalho enquanto ele acontece, registrar sua história e transformar essa história em capacidade de gestão.**

A LPS deve reduzir a dependência de perguntas como:

- “Você viu minha solicitação?”
- “Quando vai ficar pronto?”
- “Quem está fazendo?”
- “Por que voltou?”
- “Onde está parado?”
- “Quem atrasou?”
- “Quanto tempo isso costuma levar?”
- “Quantas demandas existem antes da minha?”
- “Por que esse processo sempre demora?”

A plataforma deve permitir que parte dessas respostas exista no próprio sistema.

---

# 5. Resultado esperado para o usuário

## 5.1 Para quem solicita

O solicitante deve conseguir saber, sem precisar cobrar alguém diretamente:

- se a demanda foi recebida;
- em qual setor está;
- qual a posição na fila;
- quem está responsável;
- qual prazo foi comprometido;
- se houve mudança;
- se houve devolução;
- se existe risco;
- quando foi concluída.

---

## 5.2 Para quem executa

O executor deve conseguir:

- visualizar sua fila;
- entender o que precisa fazer;
- iniciar trabalho rapidamente;
- registrar tempo sem burocracia excessiva;
- devolver quando necessário;
- registrar o motivo;
- propor novo prazo;
- concluir;
- enxergar as prioridades definidas para sua operação.

---

## 5.3 Para quem gerencia

O gestor deve conseguir identificar:

- tamanho da fila;
- tempo médio de espera;
- tempo médio de execução;
- atividades paradas;
- tarefas atrasadas;
- gargalos;
- retrabalho;
- devoluções;
- capacidade do setor;
- concentração de trabalho;
- atividades de maior duração;
- atividades de menor duração;
- desvios entre prazo solicitado e comprometido;
- pessoas ou etapas que exigem treinamento;
- processos que precisam ser redesenhados.

O gestor não deve depender apenas de percepção.

---

# 6. Princípios fundamentais do produto

## 6.1 Processo define o padrão; atividade registra a execução

Para trabalhos recorrentes, a LPS pode possuir um **processo** reutilizável.

O processo define, de forma estruturada:

```text
INPUT
↓
TAREFAS / FLUXO PADRÃO
↓
OUTPUT
↓
CRITÉRIOS DE ACEITE
```

A atividade representa uma execução real desse padrão.

Exemplo:

```text
Processo:
Elaborar orçamento

Atividade:
Entregar orçamento da obra X ao cliente
```

O processo não substitui o conceito de atividade, dono ou tarefa.

Também não deve virar burocracia obrigatória para toda demanda. No D0, atividades simples e não recorrentes podem existir sem processo.

Quando um processo publicado é utilizado, a atividade deve guardar a versão exata aplicada para preservar histórico.

---

Os princípios abaixo devem orientar toda decisão futura.

---

## 6.2 Uma atividade possui um único dono

Não existem dois donos de uma atividade.

O dono é a pessoa responsável por acompanhar o problema até a resolução.

A atividade pode envolver:

- vários setores;
- várias tarefas;
- vários executores;
- vários gestores;
- fornecedores;
- aprovações.

Ainda assim, o dono permanece único.

Isso evita responsabilidade difusa.

---

## 6.3 Atividades são compostas por tarefas

A atividade representa o resultado ou problema maior.

As tarefas representam partes necessárias para chegar ao resultado.

Exemplo:

```text
ATIVIDADE
Material disponível na obra
```

Pode possuir tarefas como:

```text
1. Engenharia gerar lista
2. Compras realizar aquisição
3. Financeiro realizar pagamento
4. Almoxarifado receber
5. Obra confirmar disponibilidade
```

A atividade termina quando o problema está resolvido, não apenas quando alguém “passou para frente”.

---

## 6.4 Uma tarefa pode possuir vários executores

Mais de uma pessoa pode trabalhar na mesma tarefa.

A LPS deve registrar o tempo de cada pessoa separadamente.

Depois, o sistema pode consolidar:

- tempo total de execução;
- horas-homem;
- quantidade de pessoas envolvidas;
- produtividade por tipo de tarefa;
- diferenças entre executores.

---

## 6.5 A responsabilidade pelo resultado não muda quando a tarefa muda de setor

Exemplo:

Um engenheiro precisa de material na obra.

O fluxo pode envolver:

```text
Engenharia
↓
Compras
↓
Financeiro
↓
Almoxarifado
```

Mesmo quando a tarefa está no Financeiro, a necessidade original continua sendo do engenheiro.

O dono deve conseguir acompanhar o processo até o resultado final.

---

## 6.6 O sistema registra fatos, não opiniões

Evitar armazenar conclusões vagas como:

> “Compras demora muito.”

Registrar fatos:

```text
Entrada em Compras: 08:00
Primeira ação: 13:20
Início de execução: 14:00
Devolução: 16:10
Motivo: especificação incompleta
Retorno: dia seguinte 09:15
Conclusão: 15:40
```

Depois, a LPS pode concluir se existe gargalo.

A inteligência deve nascer do histórico.

---

## 6.7 Toda movimentação relevante deve ser auditável

A LPS deve permitir reconstruir a história da atividade.

Eventos relevantes incluem:

- criação;
- atribuição;
- alteração;
- início;
- pausa;
- retomada;
- mudança de responsável;
- mudança de setor;
- mudança de posição;
- alteração de prazo;
- proposta de prazo;
- aceite;
- recusa;
- devolução;
- motivo da devolução;
- escalonamento;
- conclusão;
- reabertura.

A pergunta deve poder ser respondida:

> **Quem fez o quê, quando e por quê?**

---

## 6.8 Transparência não significa exposição total

O solicitante precisa de informação suficiente para acompanhar sua demanda.

Ele não precisa enxergar tudo que existe no setor executor.

Exemplo adequado:

```text
Sua posição: 4 de 17
Status: aguardando execução
Prazo comprometido: 18/09 às 15h
```

Exemplo desnecessário:

```text
1. Cliente X — problema financeiro
2. Obra Y — compra emergencial
3. Funcionário Z — veículo
4. Sua solicitação
...
```

A LPS deve equilibrar:

- transparência;
- contexto;
- privacidade;
- segurança;
- responsabilidade.

---

## 6.9 A fila deve ser visível e gerenciável

Cada setor pode possuir uma fila de trabalho.

A fila deve ser fácil de reorganizar por pessoas autorizadas.

Toda mudança relevante deve ficar registrada.

O solicitante deve enxergar sua posição exata.

Exemplo:

```text
4 de 17
```

Se a posição mudar:

```text
4 de 17
↓
16 de 17
```

a mudança deve ser registrada e pode gerar notificação conforme a configuração.

---

## 6.10 Prioridade não é definida apenas por quem solicita

Quem solicita conhece o próprio impacto.

Quem administra a fila conhece o conjunto.

Por isso, a LPS deve separar:

- impacto informado;
- prazo solicitado;
- posição na fila;
- prioridade operacional;
- prazo comprometido;
- risco calculado futuramente.

Esses conceitos não devem ser tratados como a mesma coisa.

---

## 6.11 Prazo solicitado e prazo comprometido são diferentes

A LPS deve preservar os dois.

Exemplo:

```text
Prazo solicitado:
Hoje

Prazo comprometido:
Terça-feira às 15h
```

Essa diferença é um dado gerencial.

Ela pode indicar:

- falta de capacidade;
- conflito de prioridade;
- planejamento inadequado;
- prazo irreal;
- gargalo recorrente.

O histórico não deve ser apagado quando houver renegociação.

---

## 6.12 Conflitos precisam escalar

Quando solicitante e executor não conseguem chegar a um acordo, não basta deixar a tarefa parada.

A LPS deve possuir conceito de escalonamento.

A regra pode variar por empresa.

Exemplo:

```text
Prazo solicitado recusado
↓
Novo prazo proposto
↓
Dono recusa
↓
Escalonamento
↓
Gestores responsáveis tomam decisão
```

O objetivo é evitar conflito silencioso.

---

## 6.13 Devolução deve gerar aprendizado

Uma tarefa pode voltar para uma etapa ou setor anterior.

Isso não é apenas uma movimentação.

É um dado de processo.

Toda devolução deve possuir motivo.

Exemplos:

- informação incompleta;
- especificação incorreta;
- falta de aprovação;
- documento ausente;
- escopo incorreto;
- dado divergente.

Com histórico suficiente, a LPS deve conseguir identificar padrões de retrabalho.

---

## 6.14 Comunicação deve estar ligada ao trabalho

A LPS não precisa nascer como um Slack corporativo.

Não é necessário criar canais livres como:

```text
#geral
#comercial
#financeiro
```

no D0.

A comunicação deve estar contextualizada em:

- atividade;
- tarefa.

Isso permite que a conversa tenha relação direta com o trabalho realizado.

---

## 6.15 Conversa não substitui dado estruturado

Uma mensagem pode dizer:

> “Consigo entregar terça-feira às 15h.”

Isso não significa automaticamente que o prazo oficial mudou.

A conversa é evidência contextual.

A alteração formal deve ocorrer por ação estruturada.

Futuramente, a LPS pode detectar mensagens que aparentem conter:

- prazo;
- risco;
- decisão;
- impedimento;
- devolução;
- compromisso.

Mas deve solicitar confirmação antes de alterar um dado oficial.

---

## 6.16 O sistema deve ser simples na operação

A sofisticação deve estar na estrutura, não na dificuldade de uso.

O usuário deve conseguir:

- criar atividade rapidamente;
- selecionar setor;
- definir dono;
- incluir tarefas;
- assumir tarefa;
- iniciar;
- pausar;
- retomar;
- devolver;
- concluir;
- visualizar fila;
- acompanhar prazo.

Sem precisar conhecer a complexidade interna do sistema.

---

# 7. Dinâmico x estático

A LPS deve ser dinâmica onde as empresas são diferentes e estática onde o produto precisa preservar coerência.

---

## 7.1 O que deve ser dinâmico

Exemplos:

- processos e suas configurações de input, output, critérios e fluxo;
- setores;
- usuários;
- participação de usuários em setores;
- perfis;
- ações autorizadas;
- permissões;
- tipos de atividade;
- tipos de tarefa;
- motivos de devolução;
- regras de notificação;
- regras de escalonamento;
- fluxos;
- cadastros auxiliares;
- prioridades operacionais;
- pessoas autorizadas a reorganizar filas.

A empresa pode possuir:

```text
Comercial
Financeiro
Suprimentos
Almoxarifado
```

ou:

```text
Administrativo
Operações
Projetos
Logística
```

A LPS não deve exigir uma estrutura organizacional específica.

---

## 7.2 O que deve permanecer estruturalmente fixo

Alguns conceitos não devem ser redefinidos por cada empresa.

Exemplos:

- processo é modelo reutilizável e atividade é execução real;
- versão publicada de processo não deve ser alterada retroativamente;
- atividade vinculada a processo deve preservar a versão aplicada;
- atividade possui um único dono;
- atividade pode possuir tarefas;
- tarefas podem possuir executores;
- histórico não deve ser apagado;
- devolução precisa ser auditável;
- alterações relevantes precisam gerar eventos;
- prazo solicitado e comprometido são conceitos distintos;
- mensagem não altera automaticamente dado oficial;
- posição de fila deve possuir histórico quando alterada;
- dados precisam respeitar a organização à qual pertencem.

Esses conceitos fazem parte da identidade da LPS.

---

## 7.3 Regra de equilíbrio

> **Estrutura do produto fixa. Vocabulário, permissões e operação configuráveis.**

Essa regra evita dois extremos.

### Extremo 1 — Sistema rígido

Exemplo:

```text
Todo cliente precisa possuir setor Financeiro.
```

Problema:

Uma empresa pode possuir apenas Administrativo.

### Extremo 2 — Sistema sem padrão

Exemplo:

```text
Cada empresa decide o que significa atividade, dono, tarefa e conclusão.
```

Problema:

A LPS perde coerência e deixa de conseguir medir e aprender.

---

# 8. Configurável x customizado

Esses conceitos devem ser separados.

---

## 8.1 Configurável

Uma mesma versão da LPS atende empresas diferentes por parâmetros e cadastros.

Exemplos:

Empresa A:

```text
Setores:
- Comercial
- Compras
- Financeiro
```

Empresa B:

```text
Setores:
- Administrativo
- Engenharia
- Operações
```

O software é o mesmo.

---

## 8.2 Customizado

Customização ocorre quando o código precisa ser alterado especificamente para um cliente.

Exemplo:

```text
if empresa == "Cliente X":
    usar_regra_especial()
```

Esse comportamento deve ser evitado.

A LPS precisa buscar:

> **produto configurável, não software diferente para cada cliente.**

---

## 8.3 Por que isso importa

Se cada cliente exigir código próprio:

- manutenção cresce;
- testes se multiplicam;
- atualizações ficam perigosas;
- bugs aumentam;
- produto perde escala;
- desenvolvimento vira prestação de serviço.

A configurabilidade deve ser usada para preservar escala.

---

# 9. Cadastros configuráveis

Processos são cadastros estruturais de comportamento e devem ser configuráveis pela organização.

Um processo pode definir:

- inputs;
- output;
- critérios de aceite;
- fluxo padrão de tarefas;
- setores normalmente envolvidos;
- versão publicada.

O cadastro do processo deve permanecer separado da execução das atividades.


A LPS deve permitir que empresas criem os cadastros necessários para sua realidade.

Porém, quem pode criar ou alterar esses cadastros deve depender de autorização.

Exemplo:

Um usuário está criando uma atividade e precisa selecionar um setor.

Se o setor não existe, ele não necessariamente deve conseguir criá-lo.

Pode existir uma tela específica:

```text
Apoio
↓
Setores
↓
Cadastro
```

A autorização define quem pode:

- consultar;
- inserir;
- editar;
- inativar.

A LPS não precisa, no D0, permitir criação de todos os cadastros diretamente dentro da tela da atividade.

---

# 10. Duplicidade em cadastros

A prevenção de duplicidade deve ser pragmática.

Não considerar automaticamente como duplicados:

```text
Financeiro
Financeiro e Administrativo
```

São nomes diferentes e podem representar estruturas legítimas diferentes.

Por outro lado:

```text
Financeiro
FINANCEIRO
 financeiro
```

podem ser tratados como equivalentes para impedir duplicação óbvia.

A LPS não deve tentar adivinhar que nomes parecidos significam a mesma coisa.

---

# 11. Transparência

A transparência é um dos pilares da LPS.

Ela deve reduzir ansiedade e cobrança sem gerar exposição desnecessária.

---

## 11.1 Transparência para o solicitante

O solicitante deve conseguir acompanhar:

- posição;
- status;
- setor atual;
- responsável quando aplicável;
- prazo solicitado;
- prazo comprometido;
- mudanças relevantes;
- devoluções;
- conclusão.

---

## 11.2 Transparência para o executor

O executor deve enxergar:

- fila do seu setor;
- ordem;
- prazos;
- impacto;
- tarefas atribuídas;
- tarefas disponíveis;
- informações necessárias para executar.

---

## 11.3 Transparência para o gestor

O gestor deve possuir visão ampliada:

- fila completa;
- prioridades;
- capacidade;
- atrasos;
- gargalos;
- devoluções;
- pessoas;
- tempos;
- conflitos;
- escalonamentos;
- atividades críticas.

---

## 11.4 Transparência não é direito irrestrito de acesso

O usuário só deve enxergar informações de acordo com:

- organização;
- empresa;
- setor;
- papel;
- ação;
- autorização;
- escopo.

A transparência operacional precisa coexistir com segurança.

---

# 12. Responsabilidade única

A ideia de responsabilidade única deve orientar a gestão dentro da LPS.

---

## 12.1 Atividade

Possui um único dono.

Pergunta que precisa ter resposta imediata:

> Quem responde pelo resultado desta atividade?

---

## 12.2 Tarefa

Pode possuir:

- um executor;
- vários executores;
- setor responsável.

A responsabilidade de execução pode ser compartilhada operacionalmente.

A responsabilidade final da atividade não.

---

## 12.3 Gestor de setor

O gestor do setor não precisa ser executor de todas as tarefas.

Ele precisa possuir visibilidade suficiente para administrar:

- fila;
- capacidade;
- conflitos;
- prioridades;
- atrasos;
- escalonamentos.

Dependendo da configuração, o gestor pode ser notificado sobre eventos específicos.

---

## 12.4 Responsabilidade não significa fazer tudo

O dono da atividade não precisa executar todas as tarefas.

Ele precisa garantir que o resultado seja acompanhado.

Exemplo:

```text
Dono:
Engenheiro
```

Tarefas:

```text
Compras — executa aquisição
Financeiro — executa pagamento
Almoxarifado — recebe material
```

O engenheiro continua acompanhando porque é quem precisa do material disponível.

---

# 13. Retroalimentação

A capacidade da LPS de aprender com a própria operação é um princípio central.

---

## 13.1 O sistema começa sem inteligência histórica

No início, a empresa precisará informar manualmente:

- prazos;
- fluxo;
- responsáveis;
- setores;
- prioridades;
- regras;
- estimativas.

A LPS não deve fingir possuir conhecimento que ainda não existe.

---

## 13.2 O histórico cria inteligência

Cada nova atividade gera dados.

Com o tempo, a LPS poderá analisar:

- duração por tipo de atividade;
- duração por tarefa;
- duração por setor;
- espera;
- execução;
- devoluções;
- motivos;
- pessoas envolvidas;
- fornecedor;
- prazo solicitado;
- prazo comprometido;
- atraso;
- mudanças de fila.

---

## 13.3 Sequência de maturidade

A LPS deve evoluir nesta ordem:

```text
1. Registrar
2. Medir
3. Comparar
4. Identificar padrões
5. Prever
6. Recomendar
```

Não inverter essa sequência.

---

## 13.4 Exemplo de aprendizado

Depois de histórico suficiente, a LPS pode descobrir:

```text
Solicitação de compra

Engenharia:
0,8 dia

Compras:
2,3 dias

Financeiro:
0,9 dia

Fornecedor:
6,8 dias
```

Se uma nova solicitação precisa ser entregue em dez dias, futuramente a LPS pode perceber:

```text
Fornecedor normalmente consome 6,8 dias.

Restam aproximadamente 3,2 dias para o processo interno.
```

A partir disso pode:

- alertar;
- sugerir prazo;
- sugerir sequência;
- mostrar risco.

No D0, esse cálculo não precisa existir.

O D0 precisa garantir que os dados necessários sejam coletados.

---

# 14. Inteligência artificial

A inteligência artificial deve ser consequência da maturidade dos dados, não o ponto de partida.

---

## 14.1 No início

A IA não deve decidir sozinha:

- prazo;
- prioridade;
- responsável;
- fluxo;
- alteração de atividade;
- conclusão.

---

## 14.2 Futuramente

A IA poderá apoiar:

- resumo da atividade;
- identificação de riscos;
- sugestão de prazo;
- sugestão de fluxo;
- identificação de gargalos;
- análise de devoluções;
- previsão de atraso;
- recomendação de melhoria;
- identificação de padrões;
- sugestão de treinamento.

---

## 14.3 IA não substitui auditoria

Se a IA recomendar algo, deve ser possível distinguir:

- dado real;
- cálculo;
- inferência;
- recomendação.

A plataforma não deve misturar fato e sugestão.

---

# 15. Comunicação contextual e inteligência

Conversas ligadas às atividades podem se tornar fonte complementar de informação.

Exemplo:

> “O fornecedor informou sete dias de prazo.”

Essa informação pode ser relevante.

Futuramente, a LPS pode identificar:

> Possível prazo de fornecedor detectado.

Mas deve solicitar confirmação antes de transformar a mensagem em dado oficial.

A comunicação serve para enriquecer o contexto.

Ela não substitui o registro operacional.

---

# 16. Monitoramento e controle

A LPS deve aplicar uma lógica simples:

> Não é possível controlar aquilo que não é observado.

Por isso, o sistema precisa capturar eventos suficientes para explicar o desempenho.

---

## 16.1 Monitoramento

Monitorar significa enxergar:

- estado atual;
- posição;
- responsável;
- tempo;
- prazo;
- fila;
- dependência;
- bloqueio;
- retorno.

---

## 16.2 Controle

Controlar significa permitir ação sobre o que foi observado.

Exemplos:

- reordenar fila;
- renegociar prazo;
- devolver;
- reatribuir;
- escalar;
- notificar;
- corrigir fluxo;
- mudar capacidade;
- treinar pessoas.

A LPS não deve ser apenas painel.

Ela precisa apoiar a tomada de ação.

---

# 17. Metodologia ágil como referência, não como prisão

A LPS pode aproveitar conceitos presentes em metodologias ágeis:

- backlog;
- fila;
- trabalho em andamento;
- transparência;
- fluxo;
- bloqueio;
- responsabilidade;
- melhoria contínua;
- inspeção;
- adaptação.

Porém, a plataforma não deve obrigar todas as empresas a trabalhar com uma metodologia específica.

Ela não deve exigir, por exemplo:

- Scrum;
- sprint;
- story point;
- cerimônia;
- daily;
- Kanban formal.

A LPS deve aproveitar os princípios que ajudam a operação sem transformar metodologia em burocracia.

---

# 18. Gestão de alta performance como referência

A LPS deve favorecer comportamentos de gestão como:

- clareza de responsabilidade;
- acompanhamento de resultado;
- medição;
- visibilidade;
- feedback;
- identificação de gargalo;
- melhoria contínua;
- cobrança baseada em fatos;
- capacidade de decisão.

O sistema deve reduzir frases como:

> “Eu achei que fulano estava fazendo.”

> “Não sabia que estava atrasado.”

> “Não sabia que tinha 17 coisas antes.”

> “Ninguém me avisou.”

> “Eu mandei para outro setor.”

A informação precisa estar disponível no fluxo.

---

# 19. O que a LPS não é

Definir o que não estamos construindo é tão importante quanto definir o que estamos construindo.

---

## 19.1 Não é um novo Sienge

O Sienge serve como referência de conceitos consolidados.

A LPS não deve copiar todos os seus módulos.

Não é objetivo reconstruir:

- fiscal;
- contabilidade;
- financeiro completo;
- estoque completo;
- compras completo;
- engenharia completa;
- contratos completos;
- patrimônio;
- folha;
- contas correntes;
- impostos;
- cadastros que não tenham relação direta com o núcleo da LPS.

---

## 19.2 Não é um ERP completo

ERP significa **Enterprise Resource Planning**, ou sistema integrado de gestão empresarial.

A LPS pode no futuro integrar-se a ERPs.

Ela não precisa substituir todos eles.

O foco é gestão do trabalho e inteligência operacional.

---

## 19.3 Não é apenas um gerenciador de tarefas

Criar:

```text
Tarefa
Responsável
Prazo
Status
```

não é suficiente.

A LPS precisa compreender também:

- fila;
- posição;
- tempo;
- espera;
- execução;
- retorno;
- motivo;
- setor;
- prazo solicitado;
- prazo comprometido;
- escalonamento;
- histórico;
- gargalo.

---

## 19.4 Não é apenas um cronômetro

Medir tempo é importante.

Mas tempo sem contexto tem pouco valor.

A LPS precisa saber:

> Tempo de quê?

> Em qual tarefa?

> Em qual atividade?

> Em qual setor?

> De qual pessoa?

> Em qual estado?

> Houve espera?

> Houve devolução?

---

## 19.5 Não é Slack

A LPS pode possuir conversas dentro do contexto do trabalho.

Não precisa competir inicialmente como ferramenta genérica de mensagens corporativas.

---

## 19.6 Não é uma ferramenta de inteligência artificial disfarçada

A IA não é o produto.

O produto é a estrutura operacional que produz dados confiáveis.

A IA é uma camada futura de análise e recomendação.

---

## 19.7 Não é um sistema que decide tudo sozinho

No início, pessoas continuarão definindo:

- fluxo;
- prazo;
- prioridade;
- responsáveis;
- ordem;
- decisões.

A LPS registra e organiza.

Com dados suficientes, passa a auxiliar.

---

# 20. Simplicidade como princípio

A LPS deve ser fácil para quem trabalha e poderosa para quem gerencia.

Essa diferença é fundamental.

O colaborador não precisa preencher dezenas de campos para alimentar um relatório gerencial.

O sistema deve obter dados naturalmente a partir do uso.

Exemplo:

Ao mover uma tarefa:

```text
Compras
↓
Financeiro
```

a LPS já pode registrar:

- momento de saída de Compras;
- momento de entrada no Financeiro;
- responsável pela movimentação;
- duração anterior;
- nova posição de fluxo.

O usuário não precisa informar manualmente tudo isso.

---

# 21. Dados como subproduto da operação

Um bom princípio para a LPS é:

> **O usuário trabalha; o sistema registra.**

Evitar depender de atividades administrativas paralelas apenas para “alimentar o sistema”.

Quanto mais informação puder ser coletada automaticamente a partir da operação, melhor.

Exemplos:

- criação gera timestamp;
- início gera timestamp;
- pausa gera timestamp;
- movimentação gera histórico;
- alteração de fila gera histórico;
- conclusão gera timestamp;
- devolução gera evento;
- usuário autenticado identifica quem realizou a ação.

---

# 22. Configuração por empresa

A LPS deve nascer preparada para empresas diferentes.

Uma empresa pode operar com:

```text
Comercial
Suprimentos
Financeiro
Almoxarifado
```

Outra pode operar com:

```text
Vendas
Operações
Administrativo
Logística
```

O sistema não pode depender de nomes específicos.

A estrutura deve funcionar independentemente do organograma.

---

# 23. Isolamento entre empresas

A LPS deve tratar os dados de cada organização de forma isolada.

O fato de a plataforma atender várias empresas não significa que uma empresa pode acessar os dados de outra.

Qualquer aprendizado entre empresas no futuro deve respeitar:

- segurança;
- privacidade;
- autorização;
- anonimização quando aplicável.

A arquitetura deve nascer preparada para múltiplas organizações sem misturar dados.

---

# 24. Notificações como parte da transparência

A transparência não pode depender de o usuário entrar continuamente no sistema.

Exemplo:

O solicitante está:

```text
4 de 17
```

Depois passa para:

```text
16 de 17
```

Se essa mudança for relevante conforme as regras configuradas, a LPS deve conseguir avisá-lo.

Eventos potencialmente notificáveis incluem:

- mudança de posição;
- novo prazo proposto;
- prazo aceito;
- prazo recusado;
- devolução;
- mudança de responsável;
- atraso;
- escalonamento;
- conclusão.

O usuário e a empresa devem possuir parâmetros para evitar excesso de notificações.

---

# 25. Princípio de não esconder conflito

A LPS não deve mascarar divergências.

Se:

```text
Prazo solicitado:
segunda-feira
```

e:

```text
Prazo comprometido:
quarta-feira
```

o sistema não deve simplesmente substituir uma data pela outra.

A divergência é informação gerencial.

O conflito precisa permanecer visível até existir decisão.

---

# 26. Princípio de preservação do histórico

Dados históricos importantes não devem ser sobrescritos como se nunca tivessem existido.

Exemplo:

Se o prazo mudou três vezes, a LPS deve conseguir saber:

```text
Prazo inicial
↓
Primeira proposta
↓
Prazo aceito
↓
Nova renegociação
↓
Prazo final
```

O estado atual é importante.

A história que levou até ele também.

---

# 27. Princípio de comparação

A LPS deve estruturar dados para permitir comparações futuras.

Exemplos:

- atividade A x atividade B;
- tarefa A x tarefa B;
- planejado x realizado;
- setor A x setor B;
- período atual x período anterior;
- mesmo tipo de processo ao longo do tempo;
- executor x média do processo.

O objetivo não é criar competição cega.

É identificar oportunidade de melhoria.

---

# 28. Princípio de contexto

Métricas sem contexto podem gerar conclusões erradas.

Exemplo:

Uma pessoa leva três vezes mais tempo que outra.

Isso não significa automaticamente baixa produtividade.

Pode existir:

- tarefa mais complexa;
- informação incompleta;
- mais devoluções;
- cliente diferente;
- dependência externa;
- interrupção;
- falta de treinamento.

A LPS deve registrar contexto suficiente para tornar a análise mais justa.

---

# 29. Princípio de melhoria contínua

A LPS não deve apenas apontar problemas.

Com maturidade, deve ajudar a organização a melhorar.

Exemplo:

Se Jennifer executa determinado levantamento em uma hora e Ryan normalmente leva três horas, o sistema pode futuramente sugerir:

> Existe diferença relevante de tempo entre executores neste tipo de tarefa.

Depois:

> Avaliar treinamento ou padronização do processo.

O objetivo não é apenas medir pessoas.

É melhorar o sistema de trabalho.

---

# 30. Limites do D0

D0 significa **dia zero**, a primeira versão funcional necessária para validar o núcleo do produto.

O D0 deve provar que a LPS consegue organizar e medir o fluxo real de trabalho.

---

## 30.1 O que precisa existir no D0

### Estrutura básica

- organização;
- empresa;
- usuários;
- setores;
- participação de usuários em setores;
- autenticação;
- perfis;
- ações;
- autorizações.

### Atividades

- criar;
- editar;
- visualizar;
- dono único;
- status;
- histórico;
- conclusão.

### Tarefas

- criar;
- ordenar;
- definir setor;
- definir prazo;
- atribuir executores;
- vários executores;
- iniciar;
- pausar;
- retomar;
- concluir;
- devolver;
- informar motivo da devolução.

### Fluxo

- movimentar tarefa;
- manter histórico;
- permitir retorno;
- registrar entrada e saída;
- identificar setor atual.

### Filas

- fila por setor;
- posição;
- visualização da posição pelo solicitante;
- reorganização por pessoas autorizadas;
- histórico das mudanças.

### Prazos

- prazo solicitado;
- prazo comprometido;
- proposta de novo prazo;
- aceite;
- recusa;
- escalonamento básico.

### Tempo

- início;
- pausa;
- retomada;
- fim;
- tempo por pessoa;
- tempo por tarefa;
- horas-homem;
- tempo total.

### Auditoria

- criação;
- mudanças relevantes;
- movimentações;
- responsáveis;
- devoluções;
- motivos;
- prazos;
- conclusão.

### Notificações essenciais

- mudança relevante de posição;
- novo prazo;
- devolução;
- escalonamento;
- conclusão.

### Comunicação básica

- conversa ligada à atividade;
- conversa ligada à tarefa;
- histórico de mensagens.

---

## 30.2 O que não precisa existir no D0

- previsão automática de prazo;
- fluxo sugerido por IA;
- benchmarking entre empresas;
- recomendações automáticas;
- resumo inteligente obrigatório;
- canais livres estilo Slack;
- ERP completo;
- financeiro completo;
- compras completo;
- estoque completo;
- contabilidade;
- fiscal;
- folha;
- BI corporativo genérico;
- modelagem avançada de holding;
- estrutura completa de subsidiárias;
- departamentos obrigatórios;
- área de negócio obrigatória;
- cadastro rápido de tudo dentro da atividade;
- inteligência artificial tomando decisões operacionais.

Esses itens podem ser avaliados posteriormente.

---

# 31. Critério de entrada de funcionalidade no D0

Uma funcionalidade deve entrar no D0 quando for necessária para provar pelo menos um destes pontos:

- responsabilidade;
- fluxo;
- fila;
- prazo;
- execução;
- tempo;
- auditoria;
- transparência;
- escalonamento;
- comunicação contextual;
- capacidade de medir gargalo.

Caso contrário, deve ser tratada como evolução.

---

# 32. Perguntas que o D0 precisa conseguir responder

Ao final do D0, a LPS precisa ser capaz de responder, com dados reais:

## Sobre uma atividade

- Quando foi criada?
- Quem é o dono?
- Quanto tempo levou para ocorrer a primeira ação?
- Quais tarefas foram criadas?
- Quais setores participaram?
- Quantas pessoas trabalharam?
- Quanto tempo total levou?
- Onde ficou mais tempo?
- Quantas vezes voltou?
- Por que voltou?
- Quando foi concluída?

## Sobre uma tarefa

- Qual setor é responsável?
- Quem executou?
- Quanto cada pessoa trabalhou?
- Quanto tempo ficou na fila?
- Quanto tempo ficou em execução?
- Qual era o prazo?
- Qual prazo foi comprometido?
- Foi devolvida?
- Foi concluída no prazo?

## Sobre um setor

- Quantas tarefas estão na fila?
- Qual a posição de cada tarefa?
- Quanto tempo as tarefas normalmente esperam?
- Quanto tempo normalmente levam para ser executadas?
- Quais tarefas mais retornam?
- Onde existem atrasos?

---

# 33. Indicadores de que estamos no caminho correto

A LPS estará cumprindo sua proposta quando situações como estas começarem a ocorrer:

### Situação 1

Antes:

> “Você viu meu pedido?”

Depois:

> “Minha demanda está em 4 de 17.”

### Situação 2

Antes:

> “Compras está demorando.”

Depois:

> “Esta atividade permaneceu 18 horas em fila e 2 horas em execução em Compras.”

### Situação 3

Antes:

> “Financeiro atrasou tudo.”

Depois:

> “O prazo solicitado era dia 10. O Financeiro recebeu no dia 9, propôs dia 12, a proposta foi recusada e o conflito foi escalado.”

### Situação 4

Antes:

> “Esse processo sempre volta.”

Depois:

> “27% das tarefas deste tipo voltaram por falta de especificação.”

### Situação 5

Antes:

> “Não sabemos quanto tempo isso leva.”

Depois:

> “Nas últimas 40 ocorrências, a mediana foi 3,2 dias.”

---

# 34. Filtro para decisões futuras

Antes de criar qualquer nova funcionalidade, perguntar:

1. Qual problema real isso resolve?
2. Quem usará?
3. Qual decisão ficará melhor com isso?
4. Qual dado novo será gerado?
5. Esse dado é realmente necessário?
6. Isso pertence ao D0?
7. Isso pode ser configuração em vez de código?
8. Isso aumenta a simplicidade ou cria burocracia?
9. Isso ajuda a medir o trabalho?
10. Isso ajuda a identificar gargalo?
11. Isso melhora transparência?
12. Isso preserva responsabilidade clara?
13. Isso respeita auditoria?
14. Isso cria inteligência futura?
15. Já existe outro conceito que resolve o mesmo problema?

Se a resposta não for clara, a funcionalidade não deve ser implementada ainda.

---

# 35. Resumo executivo dos princípios

A LPS deve nascer sobre os seguintes fundamentos:

```text
1. Uma atividade possui um único dono.
2. Atividades são compostas por tarefas.
3. Uma tarefa pode possuir vários executores.
4. Setores são configuráveis.
5. Usuários podem participar de vários setores.
6. Permissões são configuráveis.
7. Uma atividade pode percorrer vários setores.
8. Devoluções precisam de motivo.
9. Filas precisam ser transparentes.
10. O solicitante vê sua posição, não necessariamente toda a fila.
11. Prazo solicitado e prazo comprometido são diferentes.
12. Conflitos precisam poder ser escalados.
13. Toda ação relevante precisa ser auditável.
14. Tempo de espera e tempo de execução são diferentes.
15. Conversa não substitui dado estruturado.
16. O usuário trabalha; o sistema registra.
17. O histórico não deve ser apagado.
18. A LPS começa coletando dados antes de tentar prever.
19. A inteligência deve surgir da operação real.
20. A LPS é configurável, não customizada por cliente.
21. Transparência não significa acesso irrestrito.
22. Simplicidade operacional é requisito.
23. O produto não pretende recriar um ERP completo.
24. O D0 deve provar fluxo, responsabilidade, fila, prazo, tempo e auditoria.
```

---

# 36. Regra de ouro da LPS

> **A LPS deve transformar trabalho invisível em fluxo visível, fluxo visível em dados e dados em capacidade de gestão.**

No início:

```text
Registrar
```

Depois:

```text
Medir
```

Depois:

```text
Entender
```

E somente então:

```text
Prever e recomendar
```

---

# 37. Relação com os próximos documentos

Este documento define os princípios.

Os próximos documentos detalham como esses princípios funcionam.

### `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Detalhará:

- estrutura de atividades;
- tarefas;
- dono;
- executores;
- movimentações;
- dependências;
- devoluções;
- conclusão.

### `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Detalhará:

- filas;
- posição;
- prioridade;
- prazo solicitado;
- prazo comprometido;
- negociação;
- escalonamento.

### `04_AUDITORIA_TEMPO_E_METRICAS.md`

Detalhará:

- eventos;
- tempo;
- histórico;
- métricas;
- gargalos;
- indicadores.

### `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

Detalhará:

- organizações;
- usuários;
- setores;
- perfis;
- ações;
- permissões;
- escopos.

### `06_NOTIFICACOES_E_COMUNICACAO.md`

Detalhará:

- conversas;
- mensagens;
- notificações;
- preferências;
- eventos notificáveis.

### `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

Detalhará:

- aprendizado;
- padrões;
- previsões;
- recomendações;
- IA.

### `08_BANCO_DE_DADOS.md`

Traduzirá as decisões consolidadas para a estrutura técnica.

---

# 38. Decisões consolidadas neste documento

## Produto

- A LPS é uma plataforma de gestão do trabalho.
- Não é um ERP completo.
- Não é um clone do Sienge.
- Não é um Slack.
- Não é apenas um gerenciador de tarefas.
- Não é apenas um cronômetro.
- A inteligência artificial não é o núcleo inicial.

## Gestão

- Atividade possui um único dono.
- Tarefas compõem atividades.
- Tarefas podem possuir vários executores.
- Responsabilidade pelo resultado permanece com o dono da atividade.
- Gestores precisam de visibilidade para administrar capacidade e conflito.

## Configurabilidade

- Setores são configuráveis.
- Usuário pode pertencer a vários setores.
- Permissões são configuráveis.
- Quem pode criar cadastros depende de autorização.
- A LPS deve ser configurável, não customizada por cliente.

## Fluxo

- Atividades podem percorrer vários setores.
- Tarefas podem voltar.
- Toda devolução deve possuir motivo.
- O fluxo inicial pode ser configurado manualmente.
- A LPS poderá sugerir fluxos no futuro.

## Fila

- Setores podem possuir filas.
- Solicitante deve enxergar posição exata.
- Solicitante não precisa ver detalhes das demais demandas.
- Pessoas autorizadas podem reorganizar a fila.
- Mudanças ficam registradas.

## Prazos

- Existe prazo solicitado.
- Existe prazo comprometido.
- Executor pode propor novo prazo.
- Dono pode aceitar ou recusar.
- Conflitos podem escalar.

## Auditoria

- Histórico é obrigatório.
- Tempo até primeira ação importa.
- Tempo em fila importa.
- Tempo executado importa.
- Horas-homem importam.
- Tempo por setor importa.
- Devoluções importam.

## Comunicação

- Conversas ficam ligadas ao trabalho.
- Mensagem não altera dado oficial automaticamente.
- Notificações devem reduzir necessidade de cobrança manual.

## Inteligência

- Primeiro coletar.
- Depois medir.
- Depois comparar.
- Depois identificar padrões.
- Depois prever.
- Depois recomendar.

---

# 39. Decisões ainda não detalhadas neste documento

Alguns assuntos pertencem aos próximos documentos e não devem ser definidos completamente aqui:

- estrutura exata dos status;
- regras detalhadas de criação de tarefas;
- dependências entre tarefas;
- algoritmo de posição de fila;
- critérios detalhados de prioridade;
- níveis de escalonamento;
- regras completas de notificação;
- cálculo de métricas;
- definição técnica dos schemas;
- estrutura de tabelas;
- experiência de tela;
- regras de integração;
- critérios estatísticos para aprendizado;
- políticas futuras de benchmarking entre empresas.

Esses assuntos devem ser decididos no documento responsável.

---

# 40. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação da visão e dos princípios da LPS definidos até o momento |
| 1.1 | Inclusão de processo como padrão reutilizável com versões, input, output e critérios de aceite |

---

# 41. Encerramento

A LPS deve nascer pequena no escopo e forte na fundação.

Seu valor não estará em possuir centenas de módulos.

Estará em conseguir responder com clareza:

> O que está acontecendo?

> Quem responde por isso?

> Onde está?

> Quanto tempo está levando?

> Por que voltou?

> Qual a posição na fila?

> O prazo é viável?

> Onde está o gargalo?

> O que aprendemos com as últimas execuções?

Se a plataforma conseguir responder essas perguntas com dados confiáveis, existe uma base sólida para evoluir posteriormente para previsão, recomendação e inteligência operacional.
