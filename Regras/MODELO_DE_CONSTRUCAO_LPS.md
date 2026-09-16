# Modelo de Construção do Produto — LPS

> Documento-base para orientar produto, experiência, interface, tecnologia, métricas e evolução do sistema.
>
> **Objetivo central:** construir um sistema de gestão do trabalho que seja simples para quem executa, útil para quem gerencia e confiável para quem decide.

---

## 1. O que estamos construindo

A LPS não deve ser tratada como “mais um sistema de tarefas”. O produto precisa funcionar como uma camada de organização, medição e inteligência sobre o trabalho real da empresa.

O problema que queremos resolver não é simplesmente registrar atividades. O problema é que, nas empresas, especialmente em operações como engenharia e construção civil:

- existem muitas demandas simultâneas;
- a prioridade muda constantemente;
- o gestor não enxerga a fila real;
- urgências entram sem mostrar o impacto no restante do trabalho;
- atividades ficam paradas esperando cliente, decisão ou informação;
- pessoas diferentes executam a mesma atividade em tempos muito diferentes;
- parte do conhecimento está concentrada em poucas pessoas;
- retrabalho, espera, interrupções e falta de padrão consomem capacidade;
- o colaborador não quer gastar mais tempo alimentando o sistema do que executando o trabalho;
- o gestor precisa de informação pronta para decidir, e não de mais uma planilha para interpretar.

Portanto, o sistema precisa responder três perguntas simples:

1. **O que precisa ser feito agora?**
2. **O que está impedindo o trabalho de avançar?**
3. **Onde estamos perdendo tempo, capacidade e conhecimento?**

Se a LPS responder essas três perguntas melhor que as alternativas, ela terá valor real.

---

# 2. Princípio principal do produto

A regra mais importante é:

> **O sistema deve exigir menos esforço mental do que o problema que ele resolve.**

Isso significa que a pessoa não pode precisar “administrar o sistema”. O sistema deve ajudá-la a administrar o trabalho.

Uma interface bonita não compensa um fluxo burocrático.

Uma tela moderna não compensa 15 campos obrigatórios.

Um painel cheio de gráficos não compensa indicadores que não levam a nenhuma decisão.

Um sistema completo não é necessariamente um sistema bom.

O produto deve buscar a menor quantidade de passos, decisões e informações necessárias para levar o usuário do ponto A ao ponto B.

---

# 3. A ordem correta de construção

A ordem proposta para construir a LPS é:

**Problema → Processo → Arquitetura da informação → Regra de negócio → Experiência do usuário → Interação → Interface → Tecnologia → Medição → Aprendizado → Evolução**

Essa ordem é importante.

Começar pela tela é inverter o processo.

Antes de perguntar:

> “Como será essa tela?”

Devemos perguntar:

> “Essa tela precisa existir?”

E antes disso:

> “Esse processo precisa existir?”

E antes disso:

> “Qual problema real estamos resolvendo?”

---

# 4. Camada 1 — Problema

Toda funcionalidade deve nascer de um problema real.

Não devemos criar uma funcionalidade porque:

- um concorrente possui;
- parece interessante;
- é tecnicamente possível;
- um desenvolvedor quer experimentar;
- alguém pediu uma vez;
- deixa a demonstração mais bonita.

Uma funcionalidade deve nascer porque existe um comportamento ou problema recorrente.

## 4.1 Perguntas obrigatórias antes de criar uma funcionalidade

Para toda nova ideia, responder:

1. Qual problema estamos resolvendo?
2. Quem sofre com esse problema?
3. Com que frequência isso acontece?
4. Quanto tempo ou dinheiro isso consome?
5. Como a pessoa resolve hoje?
6. Por que a solução atual é insuficiente?
7. O que acontece se não construirmos isso?
8. Existe uma solução mais simples do que criar uma nova funcionalidade?
9. Podemos eliminar uma etapa em vez de digitalizá-la?
10. Como saberemos se a solução funcionou?

---

# 5. Camada 2 — Processo

Antes de transformar um processo em software, precisamos entender o processo real.

O software não deve automatizar desorganização.

Se um processo possui cinco aprovações desnecessárias, colocar as cinco aprovações dentro do sistema não resolve o problema. Apenas digitaliza a burocracia.

## 5.1 Regra de análise de processo

Para cada processo, mapear primeiro as duas pontas:

```text
INPUT → TRANSFORMAÇÃO → OUTPUT → CRITÉRIO DE ACEITE
```

Depois detalhar:

- input: o que precisa existir para o trabalho começar;
- informações e arquivos necessários;
- responsável;
- tarefas executadas;
- decisões necessárias;
- dependências;
- exceções;
- espera;
- retrabalho;
- output: o que precisa existir ao final;
- critérios de aceite: como comprovar que a entrega está pronta.

Depois perguntar:

- O que pode ser eliminado?
- O que pode ser automatizado?
- O que pode ser preenchido automaticamente?
- O que pode ser sugerido pelo sistema?
- O que realmente precisa da decisão humana?

---

# 6. Camada 3 — Arquitetura da Informação

**Arquitetura da Informação** é a forma como as informações são organizadas, relacionadas e encontradas dentro do sistema.

Ela vem antes da aparência visual.

Se a arquitetura da informação estiver errada, teremos uma interface bonita sobre uma estrutura confusa.

## 6.1 Estrutura-base discutida para o sistema

A LPS não deve tratar toda informação como uma única árvore obrigatória.

A estrutura conceitual mais correta é:

```text
CONTEXTO DA DEMANDA
Empresa / Cliente / Obra / Contrato
+
PROCESSO opcional
↓
ATIVIDADE
↓
TAREFAS
```

Processo é um modelo reutilizável e não precisa ser filho de cliente, obra ou contrato.

Dentro de uma atividade podemos relacionar:

- versão do processo aplicada;
- responsável;
- prazo;
- prioridade;
- tempo;
- status;
- pendências;
- histórico;
- origem da demanda;
- motivo de pausa;
- resultado.

O ponto importante é não obrigar o usuário a preencher toda essa estrutura toda vez.

A estrutura deve existir para organizar o sistema, mas o usuário deve ver somente o necessário para concluir sua ação.

## 6.2 Exemplo

O banco de dados pode saber que uma atividade possui o contexto:

**Cliente A + Obra B + Contrato C + Processo “Elaborar orçamento” versão 3**

Mas, se o usuário estiver dentro desse contexto e clicar em “Nova atividade”, o sistema já deveria preencher o que ele consegue inferir.

Se o processo for selecionado, a LPS também conhece os inputs esperados, output, critérios de aceite e fluxo padrão daquela versão.

Não faz sentido pedir novamente essas informações.

Essa diferença é fundamental:

> **O sistema pode possuir muita informação sem obrigar o usuário a preencher muita informação.**

---

# 7. Camada 4 — Regra de negócio

A regra de negócio define como o sistema se comporta independentemente da aparência da tela.

Exemplos de regras já discutidas:

## 7.1 Uma pessoa não executa duas atividades ao mesmo tempo

Assim como uma pessoa fisicamente não consegue estar em duas atividades simultaneamente, o sistema deve refletir essa realidade.

Se uma nova atividade for iniciada enquanto outra estiver ativa, o sistema deve:

1. identificar a atividade atual;
2. solicitar ou aplicar a pausa;
3. registrar o motivo adequado;
4. iniciar a nova atividade.

O objetivo não é vigiar a pessoa. O objetivo é medir o fluxo de trabalho de forma coerente.

## 7.2 Pausa curta não é a mesma coisa que atividade travada

Precisamos separar:

### Pausa curta

Exemplos:

- banheiro;
- café;
- almoço;
- pequena interrupção pessoal.

Isso não significa que o processo esteja bloqueado.

### Atividade travada

Exemplos:

- aguardando cliente;
- aguardando fornecedor;
- aguardando diretor;
- projeto incompleto;
- falta de definição;
- dependência de outro setor;
- falta de acesso;
- erro de sistema.

Isso representa um gargalo do processo e precisa ser mensurado.

## 7.3 “Aguardando cliente” não significa ficar sem trabalhar

Uma atividade que depende do cliente pode ficar em estado de pendência, mas o colaborador deve seguir para outra atividade disponível.

O sistema deve separar:

- **trabalho executável agora**;
- **trabalho pendente por dependência externa**.

Isso evita que uma atividade parada bloqueie artificialmente a fila de trabalho.

## 7.4 Apropriação posterior

A atividade pode ser concluída e ainda ficar em uma área de:

**Pendentes de apropriação**

Isso permite que o usuário não precise preencher todos os detalhes no exato momento da execução.

O sistema pode priorizar a fluidez do trabalho e permitir que informações complementares sejam preenchidas depois.

---

# 8. Camada 5 — UX: Experiência do Usuário

**UX — User Experience — Experiência do Usuário** é tudo aquilo que determina como a pessoa percebe e realiza uma tarefa no sistema.

Não é apenas a tela.

UX envolve:

- clareza;
- velocidade;
- esforço mental;
- quantidade de passos;
- previsibilidade;
- feedback;
- prevenção de erro;
- facilidade de aprender;
- facilidade de recuperar um erro;
- confiança.

## 8.1 Regra central de UX

> **Uma tarefa comum deve exigir o mínimo possível de pensamento e cliques.**

Exemplo de criação de atividade:

**+ Nova atividade → escrever o título → responsável → salvar**

Os outros campos aparecem somente se forem necessários.

## 8.2 Progressive Disclosure — Divulgação Progressiva

**Progressive Disclosure**, ou **Divulgação Progressiva**, significa mostrar primeiro somente aquilo que a pessoa precisa naquele momento.

Exemplo:

### Primeira camada

- título;
- responsável;
- salvar.

### Segunda camada — “Mais opções”

- prioridade;
- prazo;
- processo;
- cliente;
- contrato;
- observação;
- anexos.

O sistema continua poderoso sem parecer complexo.

## 8.2.1 Modal grande para cadastros administrativos

Cadastros curtos podem usar modal pequeno ou médio.

Cadastros estruturados, como Processo, podem usar um modal grande que ocupe a maior parte da tela.

Princípios:

- preservar a tela de origem ao fundo;
- cabeçalho fixo;
- rolagem interna;
- rodapé de ações fixo;
- seções claras;
- evitar modal sobre modal;
- no mobile, transformar em tela inteira.

O ganho não vem de deixar o modal grande por estética.

Ele precisa permitir que uma configuração complexa seja feita sem fragmentar a navegação em muitas páginas.

## 8.3 Redução de carga cognitiva

**Carga cognitiva** é a quantidade de informação e decisões que a pessoa precisa processar mentalmente.

Quanto maior a carga cognitiva, mais cansativo e sujeito a erro o sistema se torna.

Devemos reduzir:

- quantidade de opções simultâneas;
- textos longos;
- menus excessivos;
- campos redundantes;
- decisões desnecessárias;
- termos técnicos que não ajudam o usuário;
- telas que exigem lembrar informações de outra tela.

---

# 9. As cinco métricas básicas de uma tela

Toda tela importante deve ser analisada por pelo menos cinco perguntas:

1. **Quantos cliques são necessários?**
2. **Quanto tempo leva para concluir a tarefa?**
3. **Quantos campos precisam ser preenchidos?**
4. **Quantas decisões o usuário precisa tomar?**
5. **Uma pessoa nova consegue usar sem treinamento?**

Podemos adicionar outras:

6. Quantos erros acontecem?
7. Quantas pessoas abandonam o fluxo?
8. Quantas vezes precisam voltar para corrigir alguma coisa?
9. Quantas vezes procuram ajuda?
10. Quanto tempo demora para um novo usuário executar sozinho?

---

# 10. Camada 6 — IxD: Design de Interação

**IxD — Interaction Design — Design de Interação** define como o usuário interage com o sistema.

Enquanto a UX pergunta:

> “A experiência é simples?”

O Design de Interação pergunta:

> “O que acontece exatamente quando a pessoa clica, arrasta, inicia, pausa, conclui ou erra?”

## 10.1 Exemplos importantes para a LPS

### Iniciar atividade

Ao clicar em **Iniciar**:

- verificar se existe outra atividade ativa;
- pausar a anterior, se necessário;
- registrar horário;
- mudar o estado visual;
- mostrar claramente que o cronômetro está ativo.

### Pausar

Ao clicar em **Pausar**:

- não abrir uma burocracia enorme;
- apresentar motivos rápidos;
- permitir continuar outra atividade.

### Concluir

Ao clicar em **Concluir**:

- confirmar somente informações realmente importantes;
- registrar término;
- permitir apropriação posterior;
- apresentar a próxima ação recomendada.

### Desfazer

Ações críticas devem possuir recuperação.

Em vez de perguntar confirmação para tudo, muitas vezes é melhor permitir:

**“Atividade concluída — Desfazer”**

Isso reduz interrupções desnecessárias.

---

# 11. Camada 7 — UI: Interface do Usuário

**UI — User Interface — Interface do Usuário** é a camada visual do sistema.

Ela inclui:

- tipografia;
- cores;
- botões;
- cartões;
- tabelas;
- ícones;
- campos;
- espaçamento;
- hierarquia visual;
- estados;
- responsividade.

A UI deve servir à UX.

Não devemos acrescentar elementos apenas porque deixam a tela “mais tecnológica”.

## 11.1 Princípios visuais

A LPS deve buscar:

- pouca poluição visual;
- bastante espaço em branco;
- hierarquia clara;
- poucas cores funcionais;
- uma ação principal evidente por contexto;
- consistência entre telas;
- textos curtos;
- ícones conhecidos;
- estados claramente identificáveis;
- leitura rápida.

## 11.2 Regra da ação principal

Em uma tela, deve ser evidente qual é a principal ação disponível.

Exemplo:

Se o usuário está em “Minhas atividades”, a ação principal pode ser:

**+ Nova atividade**

Não faz sentido ter cinco botões diferentes disputando a atenção com a mesma importância visual.

---

# 12. Design System — Sistema de Design

**Design System**, ou **Sistema de Design**, é o conjunto padronizado de componentes, regras e comportamentos usados no produto.

Exemplos:

- botão primário;
- botão secundário;
- campo de texto;
- modal;
- tabela;
- cartão;
- badge de status;
- tooltip;
- menu;
- alerta;
- calendário;
- seletor de responsável;
- indicador de prioridade.

A vantagem é simples:

> não precisamos redesenhar a mesma solução em cada tela.

Também evita o problema de uma tela possuir um botão azul arredondado e outra possuir um botão quadrado diferente para a mesma função.

## 12.1 Ferramentas discutidas

### Figma

Para:

- wireframes;
- protótipos;
- componentes;
- Design System;
- validação antes do desenvolvimento.

### shadcn/ui

Biblioteca de componentes para aplicações web.

Pode servir como base para:

- botões;
- formulários;
- menus;
- diálogos;
- tabelas;
- seletores;
- notificações.

A vantagem é não construir todos os componentes do zero.

### Tailwind CSS

**CSS — Cascading Style Sheets — Folhas de Estilo em Cascata** é a tecnologia usada para estilizar páginas web.

O Tailwind ajuda a manter padrões de:

- espaçamento;
- tamanhos;
- responsividade;
- tipografia;
- estrutura visual.

### Lucide

Biblioteca de ícones minimalistas e consistentes.

### Storybook

Ferramenta para documentar e visualizar componentes da interface separadamente.

Ele pode funcionar como o catálogo oficial dos componentes da LPS.

---

# 13. UX Writing — Escrita da Experiência

**UX Writing** é o trabalho de escrever textos que ajudam a pessoa a entender e executar ações dentro do sistema.

Não é copy de marketing.

É clareza operacional.

Exemplo ruim:

> Alterar estado do objeto selecionado.

Exemplo melhor:

> Concluir atividade.

Outro exemplo ruim:

> Ocorreu uma inconsistência durante o processamento da solicitação.

Melhor:

> Não foi possível salvar. Verifique sua conexão e tente novamente.

## 13.1 Regras de escrita

- usar verbos claros;
- preferir palavras comuns;
- evitar linguagem de programador;
- dizer o que aconteceu;
- dizer o que a pessoa deve fazer;
- evitar frases vagas;
- evitar códigos de erro sem explicação;
- manter a mesma palavra para a mesma coisa em todo o sistema.

Exemplo:

Se chamamos de “Atividade”, não devemos chamar a mesma entidade de “Tarefa” em outra tela sem motivo.

---

# 14. Onboarding — Entrada e Aprendizado

**Onboarding** é a experiência inicial que ensina a pessoa a usar o produto.

A nossa meta não deve ser criar um curso para ensinar o sistema.

A meta deve ser reduzir a necessidade de curso.

O usuário deve aprender fazendo.

## 14.1 Princípios

- não abrir um tour de 20 etapas;
- apresentar ajuda no contexto certo;
- ensinar uma função quando ela aparecer;
- usar exemplos reais;
- preencher valores padrão sempre que possível;
- permitir pular explicações;
- mostrar progresso inicial.

## 14.2 Exemplo

Primeiro acesso:

1. “Estas são suas atividades.”
2. “Clique aqui para iniciar uma.”
3. “Ao iniciar outra, a atual será pausada automaticamente.”

Acabou.

O usuário não precisa aprender 30 funções antes de começar.

---

# 15. Acessibilidade

Acessibilidade não deve ser tratada como detalhe visual.

Ela melhora a experiência de todos.

Devemos pensar em:

- contraste de cores;
- tamanho de fonte;
- tamanho mínimo de áreas clicáveis;
- navegação por teclado;
- foco visível;
- textos alternativos;
- ícones acompanhados de significado quando necessário;
- não depender somente de cor para representar status;
- funcionamento em diferentes tamanhos de tela.

Exemplo:

Não usar apenas:

- vermelho = atrasado;
- verde = concluído.

Também escrever:

- **Atrasado**;
- **Concluído**.

---

# 16. Responsividade e experiência Web + Mobile

O produto nasce com necessidade de funcionar em computador e celular.

Isso não significa simplesmente “encolher a tela do computador”.

A experiência deve respeitar o contexto.

## 16.1 Computador

Ideal para:

- análise;
- tabelas;
- planejamento;
- gestão de várias atividades;
- relatórios;
- configuração;
- administração.

## 16.2 Celular

Ideal para:

- iniciar atividade;
- pausar;
- concluir;
- registrar pendência;
- consultar prioridade;
- receber alerta;
- anexar foto;
- responder rapidamente.

O celular deve privilegiar execução.

O computador pode privilegiar análise.

---

# 17. Performance percebida

Não basta o sistema ser tecnicamente rápido.

Ele precisa parecer rápido.

A pessoa não deveria clicar em um botão e ficar sem saber se algo aconteceu.

## 17.1 Regras

- feedback imediato ao clicar;
- carregamento visível;
- salvar automaticamente onde fizer sentido;
- evitar recarregar a página inteira;
- carregar primeiro o essencial;
- evitar bloquear o usuário sem necessidade;
- mensagens claras em falhas.

## 17.2 Exemplo

Ruim:

Usuário clica em “Concluir” e a tela fica parada por quatro segundos.

Bom:

O botão muda imediatamente para:

**Concluindo...**

Depois:

**Atividade concluída ✓**

A percepção muda completamente.

---

# 18. Product Analytics — Análise de Produto

**Product Analytics**, ou **Análise de Produto**, mede como as pessoas realmente usam o sistema.

Sem isso, ficamos dependendo de opiniões.

O usuário pode dizer:

> “Uso bastante essa função.”

Os dados podem mostrar que ele usou duas vezes no mês.

## 18.1 O que medir

- usuários ativos;
- atividades criadas;
- atividades iniciadas;
- atividades concluídas;
- tempo médio por atividade;
- tempo parado;
- quantidade de pendências;
- motivos de bloqueio;
- cliques por fluxo;
- abandono de formulário;
- uso por funcionalidade;
- erros;
- retrabalho;
- tempo até primeira ação;
- tempo para um usuário novo aprender o fluxo.

## 18.2 Ferramentas discutidas

### Microsoft Clarity

Pode ajudar a visualizar:

- gravações de sessões;
- mapas de calor;
- cliques;
- rolagem;
- comportamentos de frustração.

### PostHog

Pode ajudar com:

- eventos;
- funis;
- retenção;
- uso de funcionalidades;
- jornada do usuário;
- experimentos.

Essas ferramentas não substituem uma definição clara de métricas.

Primeiro decidimos o que precisamos aprender.

Depois escolhemos a ferramenta.

---

# 19. Experiência do colaborador

O colaborador não deveria entrar no sistema pensando:

> “Preciso alimentar a LPS.”

Ele deveria pensar:

> “A LPS está me dizendo o que fazer agora.”

A tela principal do colaborador precisa responder rapidamente:

- qual atividade está ativa;
- qual é a próxima atividade;
- o que está pendente;
- o que está atrasado;
- quais informações precisam ser apropriadas.

## 19.1 Backlog pessoal

Estrutura discutida:

### A fazer

Atividades disponíveis para execução.

### Pendentes

Atividades bloqueadas ou esperando alguma dependência.

### Revisão

Atividades que dependem de conferência, aprovação ou revisão.

Podemos manter outras classificações internamente, mas a experiência deve continuar simples.

---

# 20. Experiência do gestor

Aqui está um dos principais diferenciais potenciais do produto.

O gestor não precisa de mais dados.

Ele precisa de **decisões evidentes**.

O sistema deveria mostrar coisas como:

- “12 atividades estão aguardando cliente.”
- “7 atividades estão paradas há mais de três dias.”
- “Rian está levando 3 vezes mais tempo que a referência neste processo.”
- “Jennifer executa esta atividade em metade do tempo médio.”
- “Este setor recebeu 35 demandas acima da capacidade da semana.”
- “As urgências inseridas hoje empurraram 8 atividades para depois do prazo.”
- “Este cliente é responsável por 22% das pendências abertas.”

Isso é muito mais útil do que mostrar apenas um gráfico genérico de produtividade.

## 20.1 O sistema deve transformar dado em pergunta gerencial

Exemplo:

Dado bruto:

> Jennifer: 25 minutos. Rian: 75 minutos.

Informação:

> Rian demora três vezes mais que Jennifer na mesma atividade.

Ação gerencial:

> “Existe diferença de método? Jennifer pode demonstrar como executa? Precisamos criar um padrão?”

Essa é a lógica que o produto deve perseguir.

---

# 21. Capital intelectual e treinamento

Um dos desperdícios menos óbvios é a diferença de conhecimento entre pessoas.

Se uma pessoa executa determinada atividade muito melhor, o sistema pode identificar essa diferença.

O objetivo não deve ser criar um ranking simplista de funcionários.

O objetivo é identificar oportunidades de transferência de conhecimento.

## 21.1 Possível fluxo

1. O sistema mede atividades comparáveis.
2. Identifica diferenças persistentes de tempo ou resultado.
3. Verifica se há contexto suficiente para comparação.
4. Mostra a diferença ao gestor.
5. Sugere investigar método, treinamento ou processo.
6. O gestor decide a ação.
7. Após treinamento, o sistema mede novamente.

Assim podemos verificar se o treinamento gerou resultado real.

---

# 22. Gargalos e desperdícios que o produto deve revelar

O sistema não deve olhar apenas para “horas trabalhadas”.

Precisamos enxergar desperdícios como:

- espera;
- retrabalho;
- interrupções;
- troca constante de contexto;
- falta de padrão;
- informação incompleta;
- aprovação demorada;
- cliente demorando para responder;
- fornecedor demorando para responder;
- decisão da diretoria;
- atividade iniciada sem requisitos;
- processamento excessivo;
- tarefa desnecessária;
- duplicidade;
- comunicação ruim;
- conhecimento concentrado;
- baixa capacitação;
- prioridade conflitante;
- excesso de urgências;
- trabalho iniciado antes da hora;
- falta de capacidade.

O objetivo é transformar gargalos invisíveis em fatos mensuráveis.

---

# 23. Fila e capacidade

Uma das dores centrais levantadas é que quem solicita uma demanda não enxerga a fila existente.

Isso cria a falsa sensação de que toda demanda pode ser imediata.

O sistema deve conseguir representar:

- quantidade de demandas;
- capacidade disponível;
- posição aproximada na fila;
- prioridade;
- prazo estimado;
- impacto de uma nova urgência.

## 23.1 SLA — Acordo de Nível de Serviço

**SLA — Service Level Agreement — Acordo de Nível de Serviço** é um compromisso de tempo ou nível de atendimento.

O sistema pode calcular ou apoiar um SLA com base em:

- fila;
- capacidade;
- complexidade;
- histórico;
- prioridade;
- dependências.

A intenção é substituir promessas arbitrárias por previsibilidade.

---

# 24. Urgência com consequência visível

Uma diretoria ou gestor pode precisar alterar prioridade.

O sistema não deve impedir isso.

Mas deve mostrar o efeito.

Exemplo:

> “Tornar esta demanda urgente pode atrasar 4 atividades previstas para hoje.”

A decisão continua humana.

O sistema apenas mostra a consequência.

Isso cria responsabilidade sem criar burocracia.

---

# 25. Estados da atividade

O estado de uma atividade precisa refletir a realidade operacional.

Uma estrutura possível:

- A fazer;
- Em andamento;
- Pausada;
- Aguardando terceiro;
- Em revisão;
- Concluída;
- Cancelada.

Não devemos criar dezenas de estados sem necessidade.

Muitos detalhes podem ser tratados como **motivos**, não como estados.

Exemplo:

Estado:

**Aguardando terceiro**

Motivo:

- cliente;
- fornecedor;
- diretor;
- engenharia;
- financeiro;
- suprimentos.

Isso evita explodir o número de status.

---

# 26. Padrões de projeto de software aplicáveis

O livro **Padrões de Projeto — Soluções Reutilizáveis de Software Orientado a Objetos**, de Erich Gamma, Richard Helm, Ralph Johnson e John Vlissides, defende a reutilização de soluções recorrentes de projeto em vez de resolver cada problema do zero.

Para a LPS, alguns padrões são especialmente interessantes.

## 26.1 Façade — Fachada

O padrão **Façade**, ou **Fachada**, fornece uma interface simplificada para um conjunto mais complexo de funcionalidades internas.

Aplicação prática:

O usuário não precisa entender:

- tabelas;
- serviços;
- regras de permissão;
- cálculo de capacidade;
- notificações;
- histórico;
- integrações.

Ele só precisa clicar:

**Iniciar atividade**

A interface funciona como uma fachada simples para uma operação complexa.

Esse princípio combina muito com a visão da LPS.

## 26.2 State — Estado

O padrão **State**, ou **Estado**, permite que o comportamento de um objeto varie de acordo com seu estado atual.

Uma atividade pode se comportar de forma diferente quando está:

- em andamento;
- pausada;
- pendente;
- concluída.

Em vez de espalhar regras de status por todo o sistema, podemos centralizar os comportamentos de cada estado.

## 26.3 Observer — Observador

O padrão **Observer**, ou **Observador**, trabalha com notificações de mudança.

Exemplo:

Quando uma atividade muda de estado:

- painel do gestor atualiza;
- indicadores atualizam;
- responsável pode ser avisado;
- fila pode ser recalculada.

O módulo da atividade não precisa conhecer todos os detalhes de quem será atualizado.

## 26.4 Strategy — Estratégia

O padrão **Strategy**, ou **Estratégia**, permite trocar regras ou algoritmos sem reconstruir toda a aplicação.

Exemplo:

O cálculo de prioridade pode começar simples:

**prioridade manual**.

Depois pode evoluir para:

**prazo + impacto + cliente + capacidade**.

A interface permanece parecida, mas a estratégia de cálculo muda.

## 26.5 Command — Comando

O padrão **Command**, ou **Comando**, representa ações como objetos ou operações encapsuladas.

Pode ser útil para:

- iniciar;
- pausar;
- concluir;
- cancelar;
- alterar prioridade;
- desfazer ações.

Também ajuda a manter histórico do que aconteceu.

## 26.6 Composite — Composição

O padrão **Composite**, ou **Composição**, é útil para estruturas hierárquicas.

Exemplo:

- Cliente;
  - Obra;
    - Contrato;
      - Processo;
        - Atividade.

Precisamos, porém, tomar cuidado para não transformar a interface na mesma complexidade da estrutura interna.

## 26.7 Princípio importante: programar para interfaces

Uma arquitetura bem separada reduz dependência entre partes do sistema.

Na prática:

A tela não deve precisar saber como o cálculo interno funciona.

O módulo de produtividade não deve precisar conhecer detalhes do banco.

A integração externa não deve contaminar a regra principal do produto.

Isso facilita mudança e manutenção.

## 26.8 Princípio importante: preferir composição à herança

Em vez de construir grandes estruturas rígidas, podemos montar funcionalidades combinando componentes menores.

Isso vale tanto para código quanto para interface.

Exemplo visual:

Um cartão de atividade pode ser composto por:

- título;
- responsável;
- status;
- prazo;
- cronômetro;
- ações.

Cada parte é independente e reutilizável.

---

# 27. Arquitetura técnica: separação de responsabilidades

A tecnologia deve refletir a mesma simplicidade que queremos na experiência.

Uma arquitetura possível precisa separar, no mínimo:

## 27.1 Interface

Responsável por mostrar e receber ações do usuário.

## 27.2 Regra de negócio

Responsável por decidir:

- o que pode ser feito;
- transição de estados;
- prioridade;
- capacidade;
- cálculo de indicadores;
- permissões.

## 27.3 Dados

Responsável por persistir:

- usuários;
- clientes;
- obras;
- contratos;
- atividades;
- tempos;
- pendências;
- eventos;
- históricos.

## 27.4 Integrações

Responsável por conversar com sistemas externos.

A arquitetura não deve fazer a regra principal depender diretamente de um fornecedor específico.

---

# 28. Eventos e histórico

Uma decisão importante para a LPS é não guardar apenas o estado atual.

Também precisamos guardar eventos relevantes.

Exemplo:

Atividade 123:

- 08:02 — criada;
- 08:05 — iniciada;
- 08:47 — pausada;
- motivo: aguardando cliente;
- 09:10 — retomada;
- 10:03 — concluída;
- 10:06 — reaberta;
- 10:21 — concluída novamente.

Esse histórico permite entender o fluxo real.

Sem histórico, vemos apenas:

> Concluída.

E perdemos toda a história operacional.

---

# 29. Métricas de produto e métricas de negócio

Precisamos separar dois tipos de métricas.

## 29.1 Métricas do produto

Mostram se o sistema está sendo bem utilizado.

Exemplos:

- tempo para criar atividade;
- cliques por fluxo;
- adoção de funcionalidade;
- taxa de erro;
- usuários ativos;
- retenção;
- abandono;
- tempo de resposta.

## 29.2 Métricas de negócio

Mostram se o sistema gera resultado.

Exemplos:

- redução de retrabalho;
- redução de tempo parado;
- melhoria de previsibilidade;
- aumento de capacidade;
- redução de atraso;
- redução de horas desperdiçadas;
- tempo economizado pelo gestor;
- redução de tarefas esquecidas;
- redução de demandas sem responsável;
- tempo menor de treinamento.

O produto só será valioso se as métricas de uso se transformarem em métricas de negócio.

---

# 30. North Star Metric — Métrica Estrela-Guia

**North Star Metric**, ou **Métrica Estrela-Guia**, é uma métrica central que representa o valor recorrente entregue pelo produto.

Ainda não devemos escolher uma definitivamente sem dados.

Mas candidatos coerentes para a LPS poderiam ser:

- percentual de trabalho executado dentro do fluxo planejado;
- tempo de capacidade recuperada;
- redução de tempo perdido por gargalos;
- percentual de atividades com fluxo mensurado;
- horas úteis recuperadas por equipe.

Precisamos evitar métricas vaidosas como:

> “10.000 atividades cadastradas.”

Isso não prova valor.

Uma empresa pode cadastrar milhares de atividades e continuar improdutiva.

---

# 31. Produto orientado a decisão

A LPS deve evoluir de três níveis:

## Nível 1 — Registrar

> “Rian gastou 75 minutos.”

## Nível 2 — Explicar

> “Ele gastou três vezes mais que a referência.”

## Nível 3 — Recomendar

> “Há diferença recorrente. Compare o método com Jennifer e avalie padronização ou treinamento.”

O nível 3 é muito mais difícil de copiar apenas com uma tela bonita.

O diferencial não está apenas em armazenar atividade.

Está na inteligência acumulada sobre como o trabalho acontece.

---

# 32. Dados como vantagem competitiva

O sistema pode se tornar mais valioso à medida que acumula dados históricos.

Exemplos:

- quanto tempo uma atividade normalmente leva;
- quais atividades mais atrasam;
- quais clientes mais bloqueiam processos;
- quais equipes possuem maior variabilidade;
- quais treinamentos geram melhoria;
- qual capacidade real de um setor;
- qual impacto de urgências;
- quais processos geram mais retrabalho.

Esse histórico ajuda a sair de uma gestão baseada apenas em opinião.

Porém, não devemos confundir quantidade de dados com qualidade.

Dados ruins em grande volume continuam ruins.

---

# 33. Inteligência Artificial

A **Inteligência Artificial** deve entrar depois que o sistema possuir contexto suficiente.

Ela não deve ser usada apenas para colocar um chatbot na tela.

Aplicações mais úteis seriam:

- identificar padrões de atraso;
- resumir pendências;
- sugerir prioridade;
- detectar anomalias;
- sugerir treinamento;
- encontrar atividades semelhantes;
- prever tempo de execução;
- apontar risco de prazo;
- sugerir causa provável de gargalo;
- transformar dados em perguntas gerenciais.

## 33.1 Regra

A Inteligência Artificial não deve tomar decisões críticas sem contexto, explicação e possibilidade de revisão humana.

Em vez de:

> “Ryan é improdutivo.”

Melhor:

> “Nas últimas 12 atividades classificadas como X, o tempo mediano de Ryan foi 2,4 vezes maior que o restante da equipe. Verifique diferenças de escopo, experiência ou método.”

Isso é muito mais responsável e útil.

---

# 34. Segurança e permissões

Um sistema empresarial precisa controlar quem pode ver e alterar cada informação.

Precisamos definir papéis.

Exemplos:

### Colaborador

- vê suas atividades;
- inicia;
- pausa;
- conclui;
- registra pendências.

### Gestor

- vê equipe;
- redistribui;
- prioriza;
- analisa gargalos;
- acompanha capacidade.

### Diretor

- visão consolidada;
- capacidade por setor;
- prioridades estratégicas;
- impactos de decisões.

### Administrador

- configura usuários;
- permissões;
- cadastros;
- parâmetros.

Permissão deve ser desenhada desde cedo, não adicionada no final.

---

# 35. Privacidade e ética de produtividade

Existe um risco importante: transformar uma ferramenta de gestão em ferramenta de vigilância.

Isso prejudicaria a confiança e poderia distorcer o comportamento.

O objetivo da medição deve ser melhorar o sistema de trabalho.

Não devemos assumir que:

> menos tempo = melhor funcionário.

Uma atividade pode levar mais tempo porque:

- era mais complexa;
- havia informação incompleta;
- o cliente mudou o escopo;
- houve retrabalho externo;
- a pessoa estava treinando alguém;
- existiam interrupções.

Portanto, os indicadores precisam sempre preservar contexto.

---

# 36. Qualidade e testes

A simplicidade percebida exige muita disciplina técnica.

Precisamos testar diferentes camadas.

## 36.1 Testes de regra

Exemplo:

- é possível existir duas atividades ativas para a mesma pessoa?
- uma atividade concluída pode receber tempo novo?
- uma urgência recalcula a fila?

## 36.2 Testes de interface

- botão funciona?
- formulário valida?
- estados aparecem corretamente?
- mobile funciona?

## 36.3 Testes de usabilidade

Entregar o protótipo para alguém e pedir:

> “Crie uma atividade e comece a executá-la.”

Não ensinar.

Observar.

Se a pessoa perguntar:

> “Onde eu clico?”

O problema provavelmente está no produto, não no usuário.

---

# 37. Maze e testes de protótipo

O Maze pode ser usado para testar protótipos antes de desenvolver.

Podemos medir:

- tempo para concluir uma tarefa;
- caminho utilizado;
- erros;
- cliques incorretos;
- desistência.

Exemplo de teste:

> “Você recebeu uma nova demanda. Cadastre-a para o Ryan executar amanhã.”

Não perguntamos se a tela está bonita.

Observamos se a pessoa consegue concluir a missão.

---

# 38. Processo de construção de uma nova funcionalidade

Toda funcionalidade deveria passar por um fluxo semelhante:

## Etapa 1 — Problema

Escrever em uma frase.

Exemplo:

> “O gestor não sabe por que atividades ficam paradas.”

## Etapa 2 — Evidência

Coletar exemplos reais.

## Etapa 3 — Resultado desejado

> “O gestor deve conseguir identificar as principais causas de parada em menos de um minuto.”

## Etapa 4 — Fluxo mínimo

Desenhar a menor solução possível.

## Etapa 5 — Protótipo

Construir no Figma.

## Etapa 6 — Teste

Entregar para usuários reais.

## Etapa 7 — Simplificação

Remover passos e campos.

## Etapa 8 — Desenvolvimento

Construir somente depois da validação básica.

## Etapa 9 — Instrumentação

Definir eventos e métricas antes de lançar.

## Etapa 10 — Lançamento controlado

Liberar para grupo pequeno.

## Etapa 11 — Análise

Observar uso real.

## Etapa 12 — Evolução

Melhorar ou remover.

---

# 39. Critério de entrada no desenvolvimento

Uma funcionalidade não deveria entrar em desenvolvimento apenas com a frase:

> “Precisamos de um dashboard.”

Ela deve possuir pelo menos:

- problema;
- usuário;
- resultado desejado;
- fluxo;
- regra de negócio;
- protótipo ou representação;
- critério de sucesso;
- evento que será medido.

Isso reduz retrabalho.

---

# 40. Critério de funcionalidade pronta

Uma funcionalidade não está pronta apenas porque o código funciona.

Ela está pronta quando:

- resolve o problema definido;
- funciona nos estados previstos;
- possui tratamento de erro;
- funciona em tela adequada;
- possui texto revisado;
- é acessível no nível definido;
- possui eventos de análise;
- foi testada;
- não introduz inconsistência visual;
- possui documentação mínima;
- o usuário consegue utilizá-la.

---

# 41. Ferramentas por etapa

## Descoberta e produto

- entrevistas;
- observação;
- mapa de processo;
- jornada do usuário;
- análise de dados;
- protótipos.

## UX e prototipação

- Figma;
- Maze.

## Interface

- Figma;
- shadcn/ui;
- Tailwind CSS;
- Lucide;
- Storybook.

## Comportamento real

- Microsoft Clarity;
- PostHog.

## Desenvolvimento e versionamento

- GitHub pode apoiar versionamento, revisão e histórico de alterações.

A escolha definitiva da arquitetura tecnológica deve ser feita separadamente. Não devemos amarrar o modelo de produto a uma ferramenta antes de definir os requisitos técnicos.

---

# 42. MVP — Produto Mínimo Viável

**MVP — Minimum Viable Product — Produto Mínimo Viável** não significa produto mal feito.

Significa a menor versão capaz de provar uma hipótese de valor.

Um MVP coerente para a LPS não precisa começar com 50 módulos.

Uma versão inicial poderia provar apenas este ciclo:

1. criar demanda;
2. colocar na fila;
3. atribuir responsável;
4. iniciar;
5. pausar;
6. registrar bloqueio;
7. retomar;
8. concluir;
9. medir tempo;
10. mostrar gargalo básico ao gestor.

Se esse ciclo não gera valor, adicionar Inteligência Artificial, gráficos e dezenas de configurações não resolverá.

---

# 43. O que não deveria entrar cedo demais

Possíveis armadilhas:

- gamificação;
- ranking individual;
- dezenas de gráficos;
- personalização excessiva;
- automações complexas;
- Inteligência Artificial em tudo;
- marketplace;
- dezenas de integrações;
- módulos muito específicos;
- configuração para cada exceção.

Cada camada adicional aumenta:

- código;
- manutenção;
- testes;
- suporte;
- documentação;
- curva de aprendizado.

Complexidade precisa pagar aluguel.

Ou seja:

> toda complexidade adicionada precisa gerar valor suficiente para justificar sua existência.

---

# 44. Regra de remoção

Devemos ter coragem de remover funcionalidades.

Uma função pode ser removida se:

- quase ninguém usa;
- ninguém entende;
- gera suporte demais;
- não melhora nenhuma métrica relevante;
- pode ser substituída por fluxo mais simples;
- cria duplicidade;
- nasceu de uma exceção rara.

Software bom também é resultado do que foi retirado.

---

# 45. Roadmap orientado a aprendizado

Em vez de planejar somente:

- Tela A;
- Tela B;
- Tela C.

Podemos organizar o roadmap em hipóteses.

Exemplo:

### Hipótese 1

> Medir início, pausa e conclusão permitirá enxergar tempo real das atividades.

### Hipótese 2

> Registrar motivos de bloqueio permitirá identificar gargalos recorrentes.

### Hipótese 3

> Mostrar capacidade e fila reduzirá urgências artificiais.

### Hipótese 4

> Comparar tempos de processos semelhantes ajudará a detectar oportunidades de treinamento.

Cada fase produz aprendizado.

---

# 46. Ciclo de melhoria contínua

O produto deve operar em ciclo:

**Observar → Medir → Entender → Simplificar → Construir → Medir novamente**

Isso vale tanto para a operação do cliente quanto para o desenvolvimento da própria LPS.

---

# 47. Checklist de UX antes de aprovar uma tela

- [ ] O usuário entende o objetivo da tela em menos de cinco segundos?
- [ ] Existe uma ação principal clara?
- [ ] Existem campos que podemos remover?
- [ ] Algum campo pode ser preenchido automaticamente?
- [ ] Alguma informação pode aparecer somente depois?
- [ ] Estamos repetindo informação que o sistema já possui?
- [ ] O texto usa linguagem comum?
- [ ] Há feedback para cada ação?
- [ ] O usuário consegue corrigir erros?
- [ ] Funciona no celular, se necessário?
- [ ] Os estados estão claros?
- [ ] A tela continua utilizável sem treinamento?

---

# 48. Checklist de produto antes de criar uma funcionalidade

- [ ] Qual problema real resolve?
- [ ] Quem possui esse problema?
- [ ] Temos evidência?
- [ ] Qual impacto do problema?
- [ ] Como é resolvido hoje?
- [ ] Podemos eliminar o processo em vez de digitalizá-lo?
- [ ] Qual a solução mínima?
- [ ] Como mediremos sucesso?
- [ ] Qual risco estamos criando?
- [ ] O que acontecerá se não fizermos?

---

# 49. Checklist técnico

- [ ] Regra de negócio está separada da interface?
- [ ] Estados estão claramente definidos?
- [ ] Permissões estão definidas?
- [ ] Eventos importantes possuem histórico?
- [ ] Existe tratamento de erro?
- [ ] Existe monitoramento?
- [ ] A funcionalidade está instrumentada?
- [ ] Há testes das regras críticas?
- [ ] A arquitetura permite mudança futura sem reconstruir tudo?
- [ ] Estamos adicionando dependência desnecessária?

---

# 50. As regras constitucionais da LPS

Estas regras resumem o modelo de construção.

## Regra 1

**O problema vem antes da funcionalidade.**

## Regra 2

**O processo vem antes da tela.**

## Regra 3

**O usuário não deve informar ao sistema algo que o sistema já sabe.**

## Regra 4

**A ação mais comum deve ser a mais simples.**

## Regra 5

**Campos avançados aparecem depois, não antes.**

## Regra 6

**A interface deve esconder complexidade técnica.**

## Regra 7

**Todo clique precisa ter uma razão.**

## Regra 8

**Todo indicador precisa apoiar uma decisão.**

## Regra 9

**Toda funcionalidade precisa de uma métrica de sucesso.**

## Regra 10

**O sistema deve medir fluxo, não apenas pessoas.**

## Regra 11

**Contexto vem antes de julgamento.**

## Regra 12

**O gestor deve receber exceções e decisões, não apenas dados.**

## Regra 13

**A Inteligência Artificial deve aumentar a capacidade de decisão, não decorar o produto.**

## Regra 14

**A complexidade precisa justificar seu custo.**

## Regra 15

**Uma função que não gera valor pode ser removida.**

## Regra 16

**Construir menos, medir mais e aprender rápido.**

---

# 51. Modelo resumido em uma frase

A construção da LPS pode ser resumida assim:

> **Entender o trabalho real, eliminar complexidade desnecessária, organizar a informação, transformar regras em fluxos simples, medir o comportamento real e evoluir somente a partir de evidências.**

---

# 52. Modelo resumido em etapas

```text
1. PROBLEMA
   ↓
2. PROCESSO REAL
   ↓
3. SIMPLIFICAÇÃO DO PROCESSO
   ↓
4. ARQUITETURA DA INFORMAÇÃO
   ↓
5. REGRAS DE NEGÓCIO
   ↓
6. UX — EXPERIÊNCIA
   ↓
7. IXD — INTERAÇÃO
   ↓
8. UI — INTERFACE
   ↓
9. DESIGN SYSTEM
   ↓
10. DESENVOLVIMENTO
   ↓
11. TESTES
   ↓
12. ANALYTICS — MEDIÇÃO
   ↓
13. APRENDIZADO
   ↓
14. SIMPLIFICAÇÃO / EVOLUÇÃO
   ↺
```

---

# 53. O maior risco do projeto

O maior risco não é a tecnologia.

Também não é um concorrente copiar uma tela.

O maior risco é construirmos um sistema tecnicamente bom que exige mais trabalho do que economiza.

Se o usuário precisar:

- parar;
- pensar;
- classificar;
- preencher;
- justificar;
- atualizar;
- corrigir;

para cada pequena atividade, ele abandonará o sistema ou passará a alimentá-lo de forma artificial.

Portanto, nossa obsessão deve ser:

> **capturar o máximo de contexto com o mínimo de esforço do usuário.**

Esse é o equilíbrio mais importante do produto.

---

# 54. Onde pode estar o diferencial real

Telas podem ser copiadas.

Um cadastro de tarefas pode ser recriado rapidamente.

Um quadro de Kanban pode ser reproduzido.

**Kanban** é um modelo visual de gestão de fluxo de trabalho, normalmente representado por colunas como “A fazer”, “Fazendo” e “Concluído”.

O diferencial precisa estar em camadas mais profundas:

1. modelo de dados construído a partir de trabalho real;
2. histórico operacional acumulado;
3. regras de fluxo;
4. dados de tempo e gargalo;
5. inteligência de capacidade;
6. identificação de desperdícios;
7. aprendizado organizacional;
8. comparação contextual;
9. recomendações gerenciais;
10. integração ao processo real do cliente.

Uma pessoa pode copiar a aparência.

É muito mais difícil copiar anos de contexto, regras, aprendizado e dados estruturados.

---

# 55. Visão futura

No início, a LPS pode responder:

> “O que cada pessoa está fazendo?”

Depois:

> “Onde o trabalho está travando?”

Depois:

> “Por que está travando?”

Depois:

> “Qual é o impacto?”

E, em um estágio mais maduro:

> “O que provavelmente acontecerá e qual ação merece atenção agora?”

Essa evolução transforma o produto de um registrador de tarefas em um sistema de inteligência operacional.

---

# 56. Conclusão

UX e UI são fundamentais, mas não são suficientes.

A construção da LPS precisa combinar:

- estratégia de produto;
- entendimento de processo;
- arquitetura da informação;
- regras de negócio;
- experiência do usuário;
- design de interação;
- interface;
- escrita;
- onboarding;
- acessibilidade;
- performance;
- análise de produto;
- arquitetura técnica;
- padrões de software;
- segurança;
- testes;
- dados;
- melhoria contínua.

A interface é a parte que o usuário vê.

O produto é tudo o que faz aquela interface funcionar de forma coerente.

A meta não é construir o sistema com mais funcionalidades.

A meta é construir o sistema que mais facilmente transforma trabalho desorganizado em fluxo visível, mensurável e melhorável.

---

## Referência conceitual utilizada

- Erich Gamma, Richard Helm, Ralph Johnson e John Vlissides — **Padrões de Projeto: Soluções Reutilizáveis de Software Orientado a Objetos**.
- Conceitos discutidos no desenvolvimento da LPS: UX, UI, Arquitetura da Informação, Design de Interação, Design System, UX Writing, Onboarding, acessibilidade, performance percebida e Product Analytics.

