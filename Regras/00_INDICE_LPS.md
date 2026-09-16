# 00 — Índice Geral da LPS

> Documento mestre de navegação, escopo e controle da documentação da LPS.

---

## 1. Objetivo deste documento

Este arquivo é o ponto de entrada da documentação da LPS.

Ele existe para:

- organizar os documentos do projeto;
- deixar claro o papel de cada arquivo;
- indicar a ordem recomendada de leitura;
- registrar o status de evolução da documentação;
- evitar duplicidade entre documentos;
- evitar que decisões importantes fiquem perdidas em conversas;
- impedir que o projeto se desvie do problema principal;
- separar o que pertence ao D0 do que deve ficar para fases futuras.

Este documento **não substitui** os documentos especializados. Ele apenas organiza, conecta e orienta a leitura deles.

---

## 2. O que é a LPS

A LPS é uma plataforma de gestão do trabalho voltada para:

- organização de atividades e tarefas;
- definição clara de responsabilidade;
- gestão de filas;
- monitoramento de prazos;
- acompanhamento de execução;
- medição de tempo;
- identificação de gargalos;
- auditoria do fluxo de trabalho;
- comunicação contextual ligada às atividades;
- escalonamento;
- geração de dados para gestão;
- aprendizado contínuo a partir do histórico operacional.

A LPS deve nascer simples para operar, mas estruturalmente preparada para ser configurável por diferentes empresas.

A proposta não é recriar um ERP completo nem copiar sistemas consolidados do mercado. Sistemas como o Sienge servem como referência de conceitos que já provaram funcionar, principalmente em:

- cadastros;
- autorização;
- perfis;
- ações;
- configuração;
- organização estrutural.

O diferencial da LPS deve estar principalmente na combinação de:

**gestão do trabalho + monitoramento + controle + filas + auditoria + aprendizado.**

---

## 3. Princípio central do projeto

A LPS deve registrar fatos operacionais de forma estruturada.

Exemplos:

- quando uma atividade foi criada;
- quem é o dono;
- quando ocorreu a primeira ação;
- quais tarefas foram necessárias;
- quais setores participaram;
- quem trabalhou;
- quanto tempo cada pessoa trabalhou;
- quanto tempo a demanda ficou esperando;
- por quais setores passou;
- quando foi devolvida;
- por que foi devolvida;
- quando mudou de posição na fila;
- qual prazo foi solicitado;
- qual prazo foi comprometido;
- quando houve atraso;
- quando houve escalonamento;
- quando foi concluída.

O sistema não deve tentar “ser inteligente” antes de possuir dados suficientes.

A evolução esperada é:

```text
Registrar
↓
Medir
↓
Comparar
↓
Identificar padrões
↓
Prever
↓
Recomendar
```

---

## 4. Regra para evitar desvio de escopo

Toda nova funcionalidade deve responder a pelo menos uma destas perguntas:

1. Isso melhora a gestão do trabalho?
2. Isso melhora o monitoramento?
3. Isso melhora o controle?
4. Isso melhora a transparência?
5. Isso gera dados úteis para tomada de decisão?
6. Isso ajuda a identificar gargalos?
7. Isso permite que a LPS aprenda com a operação?

Se a resposta for **não** para todas, a funcionalidade deve ir para o backlog e não para o D0.

---

## 5. Conceitos fundamentais já definidos

### 5.1 Processo

Processo é um modelo reutilizável que define como um tipo recorrente de trabalho deve ser executado com clareza.

A estrutura mínima é:

```text
INPUT
↓
EXECUÇÃO / TRANSFORMAÇÃO
↓
OUTPUT
↓
CRITÉRIOS DE ACEITE
```

O processo pode também definir um fluxo padrão de tarefas e setores.

O processo **não é a atividade**.

- processo = padrão reutilizável;
- versão do processo = fotografia imutável daquele padrão publicado;
- atividade = execução real;
- tarefa = parte do trabalho necessário para chegar ao resultado.

Uma atividade pode existir sem processo no D0 para preservar criação rápida e demandas não recorrentes. Quando um processo é selecionado, a atividade fica vinculada à versão aplicada.

---

### 5.2 Atividade

A atividade representa um problema, objetivo ou resultado que precisa ser resolvido.

Exemplo:

> Material disponível na obra.

Uma atividade possui **um único dono**.

Não existem dois responsáveis finais pela mesma atividade.

O dono da atividade é responsável por acompanhar o resultado até que o problema esteja efetivamente resolvido.

---

### 5.3 Tarefa

A atividade pode possuir diversas tarefas.

As tarefas representam as partes necessárias para chegar ao resultado final da atividade.

Exemplo:

```text
Atividade:
Material disponível na obra

Tarefas:
1. Engenharia gerar lista
2. Compras realizar aquisição
3. Financeiro realizar pagamento
4. Almoxarifado receber material
5. Obra confirmar disponibilidade
```

Mais de uma pessoa pode trabalhar na mesma tarefa.

Os tempos de trabalho de cada pessoa devem ser registrados separadamente e somados para análise de esforço.

---

### 5.4 Dono da atividade

Toda atividade possui um único dono.

O dono:

- precisa do resultado;
- acompanha o andamento;
- monitora as tarefas;
- acompanha a fila;
- recebe informações relevantes;
- cobra quando necessário;
- acompanha mudanças de prazo;
- recebe notificação de conclusão;
- continua responsável pelo acompanhamento mesmo quando a atividade está sendo executada por outro setor.

Transferir uma tarefa para outro setor não elimina a responsabilidade do dono da atividade sobre o resultado final.

---

### 5.5 Setor

Os setores são configuráveis por empresa.

A LPS não deve nascer com setores fixos no código, como:

- Financeiro;
- Comercial;
- Suprimentos;
- Engenharia;
- Administrativo.

Cada empresa cria sua própria estrutura.

Um usuário pode participar de mais de um setor.

Exemplo:

```text
Usuário: Paulo

Setores:
- Comercial
- Administrativo
- Diretoria
```

Participar de um setor não significa automaticamente possuir todas as permissões daquele setor.

---

### 5.6 Fluxo entre setores

Uma atividade pode percorrer vários setores por meio de suas tarefas.

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

O objetivo é permitir que a LPS descubra:

- onde a demanda permaneceu mais tempo;
- onde houve espera;
- onde houve retrabalho;
- onde ocorreram devoluções;
- qual setor gerou maior atraso;
- qual tarefa consumiu mais tempo;
- qual etapa foi mais eficiente.

O fluxo deve possuir histórico e auditoria.

---

### 5.7 Devolução

Uma tarefa pode voltar para um setor ou etapa anterior.

Toda devolução deve:

- ficar registrada;
- possuir origem;
- possuir destino;
- registrar data e hora;
- identificar quem realizou;
- possuir motivo obrigatório.

A devolução é um dado relevante para identificar retrabalho e problemas recorrentes.

---

### 5.8 Fila

Cada setor pode possuir sua própria fila de tarefas.

O solicitante não precisa enxergar o conteúdo das outras demandas.

Ele precisa enxergar a posição da sua demanda.

Exemplo:

> Posição atual: 4 de 17.

O objetivo é gerar transparência sem expor informações desnecessárias de outras atividades.

A pessoa responsável pela fila precisa conseguir reorganizá-la de forma simples.

Alterações na posição devem ser auditadas.

---

### 5.9 Prioridade

A prioridade não deve depender apenas da percepção de quem solicita.

Quem pede conhece o impacto para si.

Quem administra a fila conhece o conjunto das demandas.

Por isso, a LPS deve separar conceitos como:

- prazo solicitado;
- impacto informado pelo solicitante;
- posição na fila;
- prioridade operacional;
- prazo comprometido pelo setor executor;
- risco calculado futuramente pela LPS.

---

### 5.10 Prazo solicitado e prazo comprometido

A LPS deve diferenciar:

**Prazo solicitado**

Data em que o solicitante deseja receber a entrega.

**Prazo comprometido**

Data em que o setor executor declara que consegue entregar.

Exemplo:

```text
Prazo solicitado:
Hoje

Prazo comprometido:
Terça-feira às 15h
```

Se houver diferença, existe um conflito de capacidade ou prioridade que precisa ficar visível.

O setor executor pode propor um novo prazo.

O dono da atividade pode:

- aceitar;
- recusar.

Se houver recusa, a situação deve seguir a regra de escalonamento configurada.

---

### 5.11 Escalonamento

O escalonamento deve existir como conceito estrutural.

A regra deve ser configurável.

A empresa pode definir:

- quando escalar;
- para quem escalar;
- em qual nível;
- em quais tipos de tarefa;
- em quais atrasos;
- em quais conflitos de prazo;
- em quais impactos.

A LPS não deve depender apenas de cobrança manual.

---

### 5.12 Comunicação

A LPS não deve nascer como um Slack corporativo completo.

A comunicação deve estar ligada ao contexto do trabalho.

Atividades e tarefas podem possuir conversas próprias.

O objetivo é fazer com que as conversas também gerem dados e inteligência.

A conversa, porém, não deve substituir o dado estruturado.

Exemplo:

> “Consigo entregar terça-feira às 15h.”

Essa mensagem pode futuramente ser interpretada pela LPS como possível alteração de prazo, mas o prazo oficial só deve ser alterado após uma ação estruturada no sistema.

---

### 5.13 Auditoria

A auditoria é um dos pilares da LPS.

O sistema deve ser capaz de reconstruir a história de uma atividade.

Exemplo:

```text
08:00 — atividade criada
10:17 — primeira ação
11:30 — tarefa enviada para Compras
15:20 — Compras iniciou execução
Dia seguinte 09:10 — tarefa devolvida
09:11 — motivo registrado
10:30 — Engenharia corrigiu
11:00 — reenviado para Compras
14:00 — compra concluída
```

A auditoria deve permitir analisar:

- tempo até a primeira ação;
- tempo em cada etapa;
- tempo em fila;
- tempo efetivamente trabalhado;
- tempo parado;
- tempo de devolução;
- tempo total;
- quantidade de participantes;
- quantidade de retornos;
- quantidade de alterações;
- duração por setor;
- duração por tarefa.

---

### 5.14 Retroalimentação

A LPS deve aprender com os próprios dados.

No início, informações como prazo e fluxo serão predominantemente fornecidas manualmente.

Com histórico suficiente, a LPS poderá evoluir para:

- calcular médias;
- identificar padrões;
- apontar gargalos;
- identificar retrabalho recorrente;
- estimar tempos;
- sugerir prazos;
- sugerir fluxos;
- alertar riscos;
- sugerir melhorias;
- comparar processos;
- gerar resumos automáticos;
- apoiar tomada de decisão.

A inteligência deve nascer dos dados registrados na operação.

---

## 6. Documentos oficiais da LPS

A documentação oficial será dividida nos seguintes arquivos.

---

### `00_INDICE_LPS.md`

**Objetivo:**  
Ser o mapa geral da documentação.

**Conteúdo principal:**

- visão geral;
- objetivo da documentação;
- conceitos fundamentais;
- lista dos documentos;
- ordem de leitura;
- status;
- dependências;
- regras de manutenção;
- decisões já consolidadas;
- decisões ainda abertas.

**Status:**  
🟢 Em desenvolvimento / documento mestre.

---

### `01_VISAO_E_PRINCIPIOS_LPS.md`

**Objetivo:**  
Definir o que é a LPS, por que ela existe e quais princípios não devem ser quebrados ao longo do desenvolvimento.

**Conteúdo previsto:**

- problema;
- proposta de valor;
- posicionamento;
- princípios;
- transparência;
- responsabilidade;
- configurabilidade;
- dinamismo;
- simplicidade;
- retroalimentação;
- limites;
- o que a LPS não é;
- critérios para entrada de novas funcionalidades;
- visão do D0.

**Status:**  
🟠 Em revisão.

---

### `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

**Objetivo:**  
Documentar o núcleo operacional da LPS.

**Conteúdo previsto:**

- atividade;
- dono;
- tarefa;
- executor;
- setor;
- responsabilidade;
- dependências;
- fluxo;
- movimentação entre setores;
- devolução;
- retorno;
- motivo obrigatório;
- conclusão;
- reabertura;
- histórico;
- fluxo padrão;
- fluxo configurável;
- comportamento inicial sem inteligência.

**Status:**  
🟠 Em revisão.

---

### `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

**Objetivo:**  
Documentar como a LPS gerencia capacidade, ordem de execução, negociação de prazo e escalonamento.

**Conteúdo previsto:**

- fila por setor;
- posição;
- transparência;
- privacidade das demais demandas;
- reordenação;
- histórico de posição;
- prazo solicitado;
- prazo comprometido;
- proposta de novo prazo;
- aceite;
- recusa;
- conflito;
- atraso;
- escalonamento;
- responsáveis por escalonamento;
- configuração por empresa.

**Status:**  
🟠 Em revisão.

---

### `04_AUDITORIA_TEMPO_E_METRICAS.md`

**Objetivo:**  
Definir tudo o que a LPS precisa registrar para permitir análise operacional.

**Conteúdo previsto:**

- timeline;
- criação;
- primeira ação;
- tempo até primeira ação;
- início;
- pausa;
- retomada;
- conclusão;
- tempo em fila;
- tempo trabalhado;
- tempo parado;
- tempo por pessoa;
- horas-homem;
- tempo por setor;
- tempo por tarefa;
- duração total;
- quantidade de participantes;
- quantidade de devoluções;
- planejado x realizado;
- métricas;
- indicadores;
- gargalos;
- comparações;
- auditoria de alterações.

**Status:**  
🟠 Em revisão.

---

### `05_USUARIOS_SETORES_E_AUTORIZACOES.md`

**Objetivo:**  
Definir a estrutura organizacional mínima e o sistema configurável de autorização.

**Conteúdo previsto:**

- organização;
- empresa;
- usuário;
- setor;
- usuário em vários setores;
- perfil;
- grupo de ações;
- ação;
- autorização;
- escopo;
- permissões;
- quem pode consultar;
- quem pode inserir;
- quem pode editar;
- quem pode excluir;
- quem pode assumir;
- quem pode atribuir;
- quem pode alterar fila;
- quem pode criar cadastros;
- configuração por empresa.

**Status:**  
🟠 Em revisão.

---

### `06_NOTIFICACOES_E_COMUNICACAO.md`

**Objetivo:**  
Definir como as pessoas recebem informação e se comunicam dentro do contexto do trabalho.

**Conteúdo previsto:**

- conversa da atividade;
- conversa da tarefa;
- mensagens;
- participantes;
- menções;
- notificações;
- preferências;
- mudança de posição;
- mudança de prazo;
- devolução;
- atraso;
- escalonamento;
- conclusão;
- resumo da atividade;
- diferença entre conversa e dado oficial.

**Status:**  
🟠 Em revisão.

---

### `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

**Objetivo:**  
Definir como a LPS poderá aprender com os dados operacionais sem depender de inteligência artificial no D0.

**Conteúdo previsto:**

- coleta de dados;
- histórico;
- qualidade dos dados;
- métricas;
- padrões;
- análise;
- gargalos recorrentes;
- devoluções recorrentes;
- estimativa;
- previsão;
- recomendação;
- sugestão de prazo;
- sugestão de fluxo;
- sugestão de melhoria;
- resumo automático;
- inteligência artificial;
- aprendizado entre empresas;
- anonimização;
- autorização de uso de dados.

**Status:**  
🟠 Em revisão.

---

### `08_BANCO_DE_DADOS.md`

**Objetivo:**  
Traduzir os conceitos de negócio para uma estrutura de dados coerente.

**Schemas previstos:**

- `core`
- `acessos`
- `cadastros`
- `produtividade`
- `comunicacao`
- `configuracoes`
- `auditoria`

**Conteúdo previsto:**

- tabelas;
- finalidade;
- campos;
- chaves;
- relacionamentos;
- integridade;
- índices;
- histórico;
- auditoria;
- segurança;
- regras de negócio;
- isolamento entre empresas.

**Regra importante:**

O banco deve refletir as decisões de produto.

O banco não deve ser usado para inventar funcionalidades que ainda não foram decididas.

**Status:**  
⚪ Precisa ser revisado com base nas decisões atuais.

---

### `09_TELAS_E_EXPERIENCIA_DO_USUARIO.md`

**Objetivo:**  
Traduzir as regras da LPS em experiência de uso.

**Conteúdo previsto:**

- login;
- home;
- minhas atividades;
- criar atividade;
- detalhe da atividade;
- tarefas;
- fila;
- timer;
- histórico;
- conversa;
- notificações;
- visão do setor;
- visão do gestor;
- cadastros;
- configurações;
- permissões;
- simplicidade;
- responsividade;
- experiência web;
- experiência mobile.

**Status:**  
🟠 Em revisão.

---

### `10_ROADMAP_D0_D1_D2.md`

**Objetivo:**  
Controlar a evolução do produto e evitar que funcionalidades futuras entrem prematuramente no desenvolvimento.

**Conteúdo previsto:**

#### D0 — Fazer funcionar

- estrutura básica;
- usuários;
- setores;
- permissões;
- atividades;
- tarefas;
- fluxo;
- filas;
- prazos;
- tempo;
- auditoria;
- notificações essenciais.

#### D1 — Gerir

- indicadores;
- gargalos;
- escalonamento avançado;
- relatórios;
- visão do gestor;
- resumos;
- comparações;
- gestão de capacidade.

#### D2 — Aprender

- padrões históricos;
- previsão;
- sugestão de prazo;
- sugestão de fluxo;
- recomendações;
- inteligência artificial;
- benchmarking anonimizado;
- aprendizado entre empresas.

**Status:**  
🟠 Em revisão.

---

### `11_PROCESSOS_INPUTS_OUTPUTS_E_CRITERIOS_DE_ACEITE.md`

**Objetivo:**  
Definir processo como modelo reutilizável da LPS, incluindo input, output, critérios de aceite, fluxo padrão, versionamento e comportamento quando o processo é aplicado a uma atividade.

**Conteúdo principal:**

- diferença entre processo, atividade, tarefa e tipo de atividade;
- inputs configuráveis;
- output verificável;
- critérios de aceite;
- fluxo padrão de tarefas;
- versões imutáveis publicadas;
- aplicação do processo em atividades;
- comportamento de conclusão;
- experiência de cadastro;
- limites do D0.

**Status:**  
🟢 Consolidado nesta revisão.

---

## 7. Ordem recomendada de construção da documentação

A ordem lógica de leitura não precisa ser igual à numeração física dos arquivos.

```text
00 — Índice
↓
01 — Visão e princípios
↓
11 — Processos, inputs, outputs e critérios de aceite
↓
02 — Atividades, tarefas e fluxos
↓
03 — Filas, prazos e escalonamento
↓
04 — Auditoria, tempo e métricas
↓
05 — Usuários, setores e autorizações
↓
06 — Notificações e comunicação
↓
07 — Inteligência e retroalimentação
↓
08 — Banco de dados
↓
09 — Telas e experiência do usuário
↓
10 — Roadmap D0, D1 e D2
```

O documento `11` foi criado depois dos demais, mas conceitualmente fica entre visão e atividade porque processo passou a ser um conceito de negócio de primeira classe.

---

## 8. Dependência entre os documentos

### `01` influencia todos os demais

O documento de visão define as regras que não devem ser quebradas pelo restante do projeto.

### `11` define o padrão reutilizável que pode originar atividades

`11` influencia diretamente `02`, `04`, `05`, `07`, `08`, `09` e `10`.

O banco e a interface não devem inventar regras de processo fora desse documento.

### `02` alimenta `03`, `04`, `06`, `08` e `09`

Sem entender atividade, tarefa e fluxo, não é possível definir corretamente filas, auditoria, comunicação, banco ou interface.

### `03` influencia `04`, `06`, `07`, `08` e `09`

Fila e prazo geram dados fundamentais para auditoria, notificações e aprendizado.

### `04` alimenta diretamente `07`

A inteligência futura depende da qualidade da auditoria e das métricas registradas desde o início.

### `05` atravessa praticamente todo o sistema

Permissões e escopos precisam ser respeitados em atividades, filas, cadastros, comunicação, relatórios e configurações.

### `08` deve ser consequência dos documentos anteriores

O banco deve armazenar os conceitos definidos pelo produto.

### `09` deve ser consequência do comportamento

A tela deve simplificar a operação, e não criar regras novas que não existam na documentação.

### `10` controla quando cada capacidade entra

O roadmap evita antecipação desnecessária de funcionalidades.

---

## 9. Status geral da documentação

| Documento | Status | Prioridade |
|---|---|---|
| 00 — Índice Geral | 🟠 Em revisão | Alta |
| 01 — Visão e Princípios | 🟠 Em revisão | Alta |
| 02 — Atividades, Tarefas e Fluxos | 🟠 Em revisão | Crítica |
| 03 — Filas, Prazos e Escalonamento | 🟠 Em revisão | Crítica |
| 04 — Auditoria, Tempo e Métricas | 🟠 Em revisão | Crítica |
| 05 — Usuários, Setores e Autorizações | 🟠 Em revisão | Alta |
| 06 — Notificações e Comunicação | 🟠 Em revisão | Média |
| 07 — Inteligência e Retroalimentação | 🟠 Em revisão | Média |
| 08 — Banco de Dados | 🟠 Em revisão | Alta |
| 09 — Telas e Experiência | 🟠 Em revisão | Alta |
| 10 — Roadmap D0/D1/D2 | 🟠 Em revisão | Alta |
| 11 — Processos, Inputs, Outputs e Critérios de Aceite | 🟠 Em revisão | Crítica |

---

## 10. Convenção de status

Utilizar os seguintes estados:

```text
⚪ Não criado
🟡 Em discussão
🟠 Em revisão
🟢 Aprovado
🔵 Em implementação
✅ Implementado
🔴 Bloqueado
```

---

## 11. Regras para manutenção dos documentos

### 11.1 Cada conceito possui um documento principal

Evitar repetir a mesma regra completa em vários arquivos.

Exemplo:

A definição detalhada de fila pertence ao documento:

`03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Outros documentos podem fazer referência à fila, mas não devem criar regras conflitantes.

### 11.2 Decisão de produto antes da decisão técnica

Primeiro definir:

> O que precisa acontecer?

Depois:

> Como o banco representará isso?

Depois:

> Como a interface permitirá fazer isso?

### 11.3 Não transformar benchmark em requisito automaticamente

Sistemas consolidados podem servir de referência.

Isso não significa que a LPS deva reproduzir:

- todos os módulos;
- todos os cadastros;
- todos os campos;
- todas as configurações;
- todas as regras.

O benchmark deve responder:

> Existe um conceito útil aqui para o problema que a LPS está resolvendo?

### 11.4 Evitar valores fixos que pertencem à empresa

Não colocar no código valores como:

```text
Financeiro
Comercial
Engenharia
Suprimentos
Almoxarifado
```

quando esses valores fazem parte da estrutura configurável da empresa.

A plataforma deve permitir que diferentes empresas possuam estruturas diferentes.

### 11.5 Nem tudo precisa ser configurável

A LPS precisa ser dinâmica, mas não pode se tornar indefinida.

Alguns comportamentos fundamentais devem permanecer controlados pelo produto.

Exemplos:

- uma atividade possui um único dono;
- alterações importantes devem ser auditadas;
- devoluções devem possuir motivo;
- mensagens não alteram dados oficiais automaticamente;
- tempo deve ser registrado de forma rastreável.

### 11.6 Não apagar histórico operacional relevante

Sempre que possível, registros utilizados operacionalmente devem ser:

- inativados;
- versionados;
- encerrados;

em vez de simplesmente apagados.

A LPS depende do histórico para análise e aprendizado.

### 11.7 Simplicidade operacional é requisito

Um conceito pode ser sofisticado internamente sem tornar a operação difícil.

Exemplos:

- criar atividade deve ser rápido;
- assumir tarefa deve ser simples;
- reorganizar fila deve ser fácil;
- registrar devolução não deve exigir dezenas de campos;
- acompanhar posição deve ser imediato.

---

## 12. Decisões consolidadas até o momento

### Processos

- processo é um modelo reutilizável;
- processo possui input, output e critérios de aceite;
- processo pode possuir fluxo padrão de tarefas;
- processo publicado é versionado;
- atividade que usa processo aponta para uma versão específica;
- alterar um processo publicado gera nova versão;
- uma atividade antiga não muda quando o processo evolui;
- processo não é obrigatório para toda atividade no D0.

### Estrutura do produto

- A LPS não será uma recriação do Sienge.
- O Sienge é referência de arquitetura configurável, autorização e cadastros.
- O núcleo da LPS é gestão de trabalho, monitoramento, controle e aprendizado.
- O produto deve nascer configurável para outras empresas.
- A primeira validação prática será realizada na Biasi.

### Atividades

- Toda atividade possui um único dono.
- O dono permanece responsável por monitorar o resultado até a resolução.
- Uma atividade pode possuir várias tarefas.
- Várias pessoas podem trabalhar na mesma tarefa.
- O tempo de cada pessoa deve ser registrado individualmente.

### Setores

- Setores são cadastráveis.
- Não existem setores fixos obrigatórios.
- Um usuário pode participar de vários setores.
- Acesso e participação em setor são conceitos diferentes.
- Quem pode cadastrar setor depende de autorização.

### Fluxos

- Uma atividade pode percorrer diversos setores.
- O fluxo deve ser rastreável.
- Uma tarefa pode voltar para etapa anterior.
- Toda devolução exige motivo.
- Fluxos inicialmente serão definidos manualmente.
- Futuramente a LPS poderá sugerir fluxos com base no histórico.

### Filas

- Cada setor pode possuir fila.
- O solicitante deve enxergar sua posição exata.
- O solicitante não precisa visualizar o conteúdo das outras demandas.
- Pessoas autorizadas do setor podem reorganizar a fila.
- Toda mudança de posição deve ser registrada.
- Mudanças de posição devem poder gerar notificações.

### Prazos

- Existe prazo solicitado.
- Existe prazo comprometido.
- O setor executor pode propor um novo prazo.
- O dono da atividade pode aceitar ou recusar.
- Recusa pode gerar escalonamento.
- No D0 os prazos serão informados manualmente.
- Futuramente a LPS poderá sugerir prazos.

### Notificações

- Notificações devem ser configuráveis.
- O dono da atividade deve ser notificado sobre conclusão.
- Outros participantes podem receber notificações conforme configuração.
- Mudanças de posição podem gerar notificação.
- Devolução, atraso e escalonamento são eventos relevantes.

### Comunicação

- A LPS não precisa nascer com canais livres como um Slack.
- A conversa deve estar ligada a atividades e tarefas.
- Mensagens podem gerar inteligência futura.
- Mensagens não alteram dados estruturados automaticamente.

### Auditoria

- Atividades devem possuir histórico completo.
- Deve ser possível medir o tempo até a primeira ação.
- Deve ser possível medir tempo por tarefa.
- Deve ser possível medir tempo por setor.
- Deve ser possível medir tempo por pessoa.
- Deve ser possível medir tempo em fila.
- Deve ser possível medir tempo total.
- Deve ser possível identificar devoluções.
- Deve ser possível identificar onde uma atividade passou mais tempo.
- Deve ser possível comparar atividades.

### Inteligência

- O sistema precisa se retroalimentar.
- O D0 deve priorizar coleta de dados confiáveis.
- A inteligência futura deve usar dados históricos.
- A LPS poderá futuramente sugerir prazos.
- A LPS poderá futuramente sugerir fluxos.
- A LPS poderá futuramente identificar gargalos automaticamente.
- A LPS poderá futuramente resumir atividades.
- Uso de dados entre empresas deve considerar anonimização e autorização.

---

## 13. Decisões deliberadamente adiadas

Os seguintes temas não precisam ser fechados antes de avançar no núcleo do produto:

- holding;
- subsidiárias;
- grupos de empresas avançados;
- departamentos;
- área de negócio;
- módulos fiscais;
- módulos contábeis;
- contas correntes;
- impostos;
- estoque completo;
- compras completas;
- orçamento de obras completo;
- financeiro completo;
- folha;
- patrimônio;
- canais de conversa livres;
- inteligência artificial preditiva no D0;
- benchmarking entre empresas no D0.

Esses assuntos podem ser revisitados quando houver necessidade operacional real.

---

## 14. Fora do escopo inicial

A LPS não deve tentar resolver no D0:

- ERP completo;
- contabilidade;
- fiscal;
- folha de pagamento;
- gestão bancária;
- CRM completo;
- compras completas;
- estoque completo;
- planejamento completo de obra;
- orçamento completo de engenharia;
- mensageria corporativa completa;
- BI corporativo genérico;
- inteligência artificial sem dados históricos suficientes.

Integrações futuras podem conectar a LPS a ferramentas especializadas nessas áreas.

---

## 15. Critério para entrada no D0

Uma funcionalidade entra no D0 quando é necessária para validar pelo menos um dos seguintes pontos:

- criação da atividade;
- responsabilidade;
- execução;
- fluxo;
- fila;
- prazo;
- tempo;
- auditoria;
- comunicação operacional mínima;
- notificação essencial;
- escalonamento;
- permissão;
- medição de gargalo.

Caso contrário, deve ser avaliada para D1 ou D2.

---

## 16. Perguntas que a LPS precisa ser capaz de responder

O produto deve evoluir para responder perguntas como:

### Sobre atividades

- Quem é o dono?
- Quando foi criada?
- Quanto tempo levou para ocorrer a primeira ação?
- Quanto tempo levou para ser concluída?
- Quantas tarefas foram necessárias?
- Quantas pessoas participaram?

### Sobre tarefas

- Quem executou?
- Quanto tempo cada pessoa trabalhou?
- Quanto tempo ficou esperando?
- Qual tarefa demorou mais?
- Qual tarefa demorou menos?
- Quantas vezes foi devolvida?

### Sobre setores

- Quanto tempo uma demanda permaneceu em cada setor?
- Qual setor possui maior fila?
- Qual setor está atrasando mais?
- Onde existe maior tempo de espera?
- Onde existe maior retrabalho?

### Sobre prazo

- Qual era o prazo solicitado?
- Qual foi o prazo comprometido?
- O prazo foi renegociado?
- Quantas vezes?
- Houve escalonamento?
- O prazo final foi cumprido?

### Sobre gargalos

- Onde a atividade ficou mais tempo?
- O problema foi execução ou espera?
- O gargalo é pessoa, setor, fornecedor ou processo?
- Quais motivos de devolução mais se repetem?
- Quais atividades possuem comportamento semelhante?

### Sobre capacidade

- Quantas demandas existem na fila?
- Qual a posição de cada solicitação?
- Quanto tempo normalmente uma demanda leva para avançar?
- A capacidade atual é compatível com a demanda?

---

## 17. Visão de evolução da LPS

### Fase 1 — Transparência

Saber:

- o que existe;
- quem é responsável;
- onde está;
- qual a posição;
- qual o prazo;
- quem está executando.

### Fase 2 — Medição

Saber:

- quanto tempo levou;
- quanto tempo trabalhou;
- quanto tempo esperou;
- onde parou;
- quantas vezes voltou.

### Fase 3 — Controle

Permitir:

- negociar prazo;
- reordenar fila;
- escalonar;
- notificar;
- identificar atraso;
- acompanhar capacidade.

### Fase 4 — Aprendizado

Descobrir:

- padrões;
- gargalos;
- retrabalho;
- tempos típicos;
- riscos;
- comportamentos recorrentes.

### Fase 5 — Recomendação

Sugerir:

- prazo;
- fluxo;
- responsável;
- sequência;
- melhoria;
- prevenção de gargalo.

---

## 18. Princípio de dados da LPS

A LPS deve preferir registrar eventos e fatos.

Exemplo:

Evitar armazenar apenas:

> Compras é lento.

Registrar:

```text
Entrada em Compras: 10/09 08:00
Primeira ação: 10/09 14:20
Início real: 11/09 09:10
Devolução: 11/09 11:30
Motivo: especificação incompleta
Retorno: 12/09 08:40
Conclusão: 12/09 16:20
```

A conclusão gerencial deve ser produzida a partir dos fatos.

---

## 19. Princípio de configurabilidade

A LPS deve separar:

### Estrutura do produto

Controlada pela LPS.

Exemplos:

- atividade;
- tarefa;
- dono;
- auditoria;
- fila;
- prazo;
- devolução;
- escalonamento.

### Configuração da empresa

Controlada pelo cliente conforme autorização.

Exemplos:

- setores;
- usuários;
- perfis;
- permissões;
- ações autorizadas;
- tipos de atividade;
- regras de notificação;
- regras de escalonamento;
- fluxos;
- prioridades;
- cadastros auxiliares.

Essa separação permite que o produto seja dinâmico sem virar um sistema sem padrão.

---

## 20. Princípio de responsabilidade

A LPS deve evitar responsabilidade difusa.

Uma atividade possui um dono.

Uma tarefa pode possuir múltiplos executores, mas isso não cria múltiplos donos da atividade.

O objetivo é evitar situações como:

> “Achei que era responsabilidade dele.”

A responsabilidade final deve permanecer clara.

---

## 21. Princípio de transparência

Transparência não significa acesso irrestrito.

Exemplo:

O solicitante pode enxergar:

```text
Sua posição: 4 de 17
Status: aguardando execução
Prazo comprometido: 15/09 16:00
```

Ele não precisa enxergar:

- nomes das outras 16 tarefas;
- clientes envolvidos;
- detalhes confidenciais;
- justificativas internas não autorizadas.

A informação deve ser suficiente para reduzir ansiedade e cobrança desnecessária sem comprometer privacidade operacional.

---

## 22. Princípio de auditoria

Toda ação relevante deve deixar rastro.

Exemplos:

- criação;
- alteração;
- atribuição;
- mudança de setor;
- mudança de responsável;
- início;
- pausa;
- retomada;
- mudança de posição;
- alteração de prazo;
- aceite;
- recusa;
- devolução;
- motivo;
- escalonamento;
- conclusão;
- reabertura.

A auditoria deve responder:

> Quem fez o quê, quando e por quê?

---

## 23. Princípio de aprendizado

A LPS deve aprender primeiro com a própria empresa.

Antes de sugerir:

> “Esta tarefa leva 2 dias.”

o sistema precisa ter histórico suficiente para sustentar essa afirmação.

O produto deve evitar apresentar estimativas como certezas quando não houver dados confiáveis.

---

## 24. Estrutura de pastas sugerida

```text
/docs

├── 00_INDICE_LPS.md
├── 01_VISAO_E_PRINCIPIOS_LPS.md
├── 02_ATIVIDADES_TAREFAS_E_FLUXOS.md
├── 03_FILAS_PRAZOS_E_ESCALONAMENTO.md
├── 04_AUDITORIA_TEMPO_E_METRICAS.md
├── 05_USUARIOS_SETORES_E_AUTORIZACOES.md
├── 06_NOTIFICACOES_E_COMUNICACAO.md
├── 07_INTELIGENCIA_E_RETROALIMENTACAO.md
├── 08_BANCO_DE_DADOS.md
├── 09_TELAS_E_EXPERIENCIA_DO_USUARIO.md
├── 10_ROADMAP_D0_D1_D2.md
└── 11_PROCESSOS_INPUTS_OUTPUTS_E_CRITERIOS_DE_ACEITE.md
```

---

## 25. Como utilizar esta documentação

Antes de implementar uma nova funcionalidade:

1. verificar se o conceito já está documentado;
2. identificar o documento responsável pelo assunto;
3. validar se a funcionalidade pertence ao D0, D1 ou D2;
4. registrar a decisão no documento correto;
5. atualizar o banco somente depois da decisão de negócio;
6. atualizar a interface somente depois do comportamento estar definido;
7. atualizar este índice caso seja criado, removido ou renomeado algum documento.

---

## 26. Regra de ouro

> A LPS não deve tentar saber tudo desde o início.

Ela deve nascer sabendo **registrar corretamente o trabalho**.

Se os dados forem bons, a inteligência poderá crescer.

Se os dados forem ruins, nenhuma inteligência artificial corrigirá a base operacional.

---

## 27. Estado atual do projeto

Neste momento, os conceitos mais amadurecidos são:

- processo reutilizável;
- input;
- output;
- critérios de aceite;
- versionamento de processo;
- atividade;
- dono único;
- tarefas;
- múltiplos executores;
- setores configuráveis;
- usuários em vários setores;
- fluxo entre setores;
- devolução com motivo;
- filas;
- posição;
- prazo solicitado;
- prazo comprometido;
- negociação;
- escalonamento;
- notificações configuráveis;
- comunicação contextual;
- auditoria;
- tempo;
- gargalos;
- retroalimentação.

Os próximos documentos devem transformar esses conceitos em regras detalhadas e posteriormente em estrutura técnica.

---

## 28. Próxima validação recomendada

A documentação principal já existe.

O próximo passo recomendado não é criar outro documento por padrão.

É validar com uso real, nesta ordem:

```text
11 — Processo
↓
09 — Experiência de cadastro e execução
↓
08 — Banco de dados
↓
10 — Escopo do D0
```

Somente criar novo arquivo se surgir um conceito com comportamento próprio que não pertença claramente aos documentos atuais.

---

## 29. Controle de versão do documento

| Versão | Descrição |
|---|---|
| 0.1 | Estrutura inicial do índice geral da LPS |
| 1.0 | Consolidação das principais decisões de produto discutidas até o momento |
| 1.1 | Inclusão de processo como conceito de primeira classe, novo documento 11 e revisão das dependências |

---

## 30. Observação final

Este documento deve permanecer simples de navegar e atualizado.

Sempre que surgir uma nova ideia, a primeira pergunta deve ser:

> Em qual documento essa decisão pertence?

Se a resposta for “nenhum”, somente então deve ser considerada a criação de um novo arquivo de documentação.
