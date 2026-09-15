# 05 — Usuários, Setores e Autorizações

> Revisão consolidada da arquitetura funcional de identidade, estrutura organizacional, perfis, ações, escopos e autorizações da LPS.
>
> Esta versão incorpora as decisões do projeto e os aprendizados obtidos ao observar o modelo de segurança do Sienge, sem copiar sua estrutura, nomenclatura ou complexidade.

---

## 1. Objetivo

A LPS precisa responder, de forma simples e auditável:

> **Quem pode fazer o quê, onde e por quê?**

O módulo deve permitir que cada organização configure sua própria operação sem depender de desenvolvimento para situações normais.

A empresa deve conseguir cadastrar e administrar:

- usuários;
- setores;
- perfis;
- vínculos entre usuários e setores;
- ações permitidas em cada perfil;
- escopos onde essas ações valem;
- concessões adicionais para exceções;
- gestores e responsáveis estruturais;
- regras de acesso necessárias ao funcionamento da LPS.

A segurança não pode ficar presa a nomes como “Financeiro”, “Comercial” ou “Engenharia” escritos no código.

---

## 2. Princípio central

A arquitetura de autorização da LPS será baseada em quatro perguntas:

```text
QUEM?
Usuário ou perfil

O QUÊ?
Ação / capacidade

ONDE?
Escopo

POR QUE TEM ACESSO?
Origem da concessão
```

Forma resumida:

```text
SUJEITO + AÇÃO + ESCOPO + ORIGEM = AUTORIZAÇÃO EXPLICÁVEL
```

Exemplo:

```text
Paulo
+ fila.reordenar
+ Setor Comercial
+ Perfil Gestor Comercial
```

---

## 3. Dinamismo não significa ausência de regras

A LPS deve ser altamente configurável, mas o motor precisa ser previsível.

### Configurável pela organização

- usuários;
- setores;
- perfis;
- nomes dos perfis;
- composição dos perfis;
- vínculos usuário ↔ setor;
- vínculos usuário ↔ perfil;
- escopos concedidos;
- gestores de setores;
- exceções individuais;
- regras de notificação e escalonamento permitidas pelo produto.

### Controlado pela LPS

- isolamento entre organizações;
- funcionamento do motor de autorização;
- significado das ações atômicas do produto;
- regras de integridade;
- auditoria;
- validação no backend e no banco;
- estados internos que precisam ter significado estável.

Regra:

> **A empresa configura a operação; a LPS mantém o significado e a segurança do motor.**

---

## 4. O que aprendemos com o Sienge

O benchmark mostrou conceitos úteis:

- perfil agrupando autorizações;
- usuário podendo possuir vários perfis;
- autorizações diretas para usuário;
- filtros por autorizado / não autorizado;
- marcação e desmarcação por checkbox;
- configuração por diferentes contextos, como empresa e obra;
- relatórios por usuário e também pelo objeto autorizado;
- cópia de autorizações;
- grande granularidade de ações.

A LPS não deve copiar:

- milhares de ações antes de existir necessidade real;
- várias telas distintas para cada tipo de escopo;
- nomenclatura técnica difícil para o administrador;
- estruturas históricas criadas por décadas de evolução de um ERP;
- menus gigantes para resolver um produto inicialmente muito menor.

O conceito a preservar é:

> **O acesso não deve depender de alteração de código para cada cliente.**

---

## 5. Vocabulário oficial da LPS

### Organização

É o ambiente isolado de um cliente da LPS.

Exemplo:

```text
Organização: Biasi
```

Um usuário pertence a uma única organização.

### Empresa

É uma entidade operacional ou jurídica existente dentro da organização.

Uma organização pode possuir várias empresas.

### Usuário

É a identidade que acessa a LPS.

Usuário não é sinônimo de cargo, colaborador, setor ou perfil.

### Setor

Representa uma unidade operacional configurada pela empresa.

Exemplos:

```text
Comercial
Compras
Financeiro
Almoxarifado
Engenharia
```

Esses nomes são exemplos, não valores fixos do sistema.

### Cargo ou função organizacional

Quando necessário, pode descrever o papel humano da pessoa:

```text
Orçamentista
Comprador
Gerente Comercial
Assistente de Engenharia
```

Cargo **não concede acesso automaticamente**.

### Perfil

É um conjunto reutilizável de ações.

Exemplo:

```text
Gestor Comercial
```

pode conter:

```text
atividade.visualizar
atividade.criar
atividade.editar
fila.visualizar_completa
fila.reordenar
prazo.propor
```

### Grupo de ações

Organiza ações para facilitar administração.

Exemplos:

```text
Atividades
Tarefas
Filas
Prazos
Cadastros
Segurança
Auditoria
Comunicação
```

### Ação

É uma capacidade real do produto.

Exemplos:

```text
atividade.criar
tarefa.iniciar
fila.reordenar
setor.criar
usuario.inativar
```

### Escopo

Define **onde** determinada ação vale.

### Concessão direta

É uma autorização adicional aplicada especificamente a um usuário.

### Permissão efetiva

É o resultado final depois de combinar perfis, concessões diretas, escopo, situação do usuário e regras de negócio.

---

## 6. “Função” não deve ser um conceito ambíguo

Em sistemas antigos, a palavra “função” pode significar cargo, permissão ou ação dentro de um contexto.

Na LPS devemos separar:

```text
CARGO/FUNÇÃO ORGANIZACIONAL
= o papel da pessoa na empresa

PERFIL
= conjunto de capacidades

AÇÃO
= capacidade individual do sistema

ESCOPO
= onde a capacidade vale
```

Isso evita uma arquitetura confusa.

---

## 7. Usuários

O cadastro mínimo deve conter:

- nome;
- e-mail;
- organização;
- situação;
- setores;
- perfis;
- opcionalmente cargo/função organizacional;
- autenticação vinculada.

Estados mínimos:

```text
ativo
inativo
```

Usuário com histórico não deve ser apagado.

Ao inativar:

- perde acesso;
- histórico permanece;
- tarefas anteriores continuam associadas ao usuário;
- auditorias permanecem válidas.

---

## 8. Usuário pode participar de vários setores

Relação:

```text
USUÁRIO N : N SETOR
```

Exemplo:

```text
Paulo
├── Comercial
└── Engenharia
```

Participação operacional não significa acesso irrestrito.

Regra:

> **Vínculo organizacional descreve onde a pessoa atua; autorização define o que ela pode fazer.**

---

## 9. Setores são totalmente configuráveis

A LPS não deve possuir setores obrigatórios como:

```text
Financeiro
Comercial
Compras
```

Cada organização cadastra os seus.

O cadastro deve permitir:

- criar;
- editar;
- inativar;
- definir gestores;
- relacionar usuários.

No D0, criação de setor ocorre em tela própria de cadastro.

Não criar setor automaticamente dentro do formulário de atividade.

Duplicidade:

- impedir apenas duplicidade exata normalizada;
- não bloquear nomes apenas por semelhança.

Exemplo legítimo:

```text
Financeiro
Financeiro Administrativo
```

---

## 10. Gestor do setor

Um setor pode possuir um ou mais gestores.

Ser gestor é uma relação estrutural.

Não significa automaticamente:

```text
pode tudo no setor
```

Para executar ações administrativas, o gestor também precisa das autorizações correspondentes.

O vínculo de gestor pode ser usado por:

- escalonamentos;
- notificações;
- filtros;
- escopos relacionais;
- relatórios.

---

## 11. Perfis

Perfis são cadastráveis por organização.

Exemplos possíveis:

```text
Colaborador
Gestor Comercial
Gestor de Compras
Diretoria
Administrador LPS
Visualizador
```

A empresa pode usar outros nomes.

Perfil não deve ser fixado no código.

Um usuário pode possuir vários perfis.

Exemplo:

```text
Paulo
├── Gestor Comercial
└── Visualizador Corporativo
```

---

## 12. Perfil não é cargo e não é setor

Evitar:

```text
cargo = gerente
→ pode reordenar qualquer fila
```

ou:

```text
setor = financeiro
→ vê todas as informações financeiras
```

A autorização precisa continuar explícita.

---

## 13. Ações atômicas do produto

Ações representam comportamentos que realmente existem na aplicação.

Exemplos:

```text
usuario.consultar
usuario.criar
usuario.editar
usuario.inativar

setor.consultar
setor.criar
setor.editar
setor.inativar

atividade.visualizar
atividade.criar
atividade.editar
atividade.alterar_dono
atividade.concluir
atividade.reabrir

tarefa.visualizar
tarefa.criar
tarefa.atribuir
tarefa.assumir
tarefa.iniciar
tarefa.pausar
tarefa.retomar
tarefa.devolver
tarefa.concluir

fila.visualizar_posicao_propria
fila.visualizar_completa
fila.reordenar

prazo.propor
prazo.aceitar
prazo.recusar
prazo.alterar_diretamente

seguranca.gerir_perfis
seguranca.gerir_autorizacoes
seguranca.visualizar_historico

auditoria.visualizar
```

A lista cresce junto com o produto.

---

## 14. O cliente não deve inventar comportamento inexistente

Existe uma diferença importante entre **configuração** e **programação**.

A organização pode:

- criar qualquer perfil;
- dar qualquer nome ao perfil;
- escolher quais ações existentes entram nele;
- escolher usuários;
- escolher escopos.

Mas uma organização não deve criar, no D0, uma ação arbitrária como:

```text
aprovar_compra_especial_xpto
```

se a aplicação não possui comportamento correspondente.

Caso contrário, a autorização existe no banco, mas não protege ou habilita nada real.

Regra:

> **Ação atômica nasce com uma funcionalidade real; perfis e combinações são totalmente configuráveis.**

---

## 15. Grupos de ações

Grupos existem principalmente para organização e experiência do administrador.

Eles não concedem acesso sozinhos.

Exemplo:

```text
Grupo: Filas

[ ] Visualizar posição própria
[ ] Visualizar fila completa
[ ] Reordenar fila
```

A organização pode receber grupos padrão da LPS e, futuramente, reorganizar a apresentação se isso gerar valor.

---

## 16. Escopos

Escopo responde:

> Onde essa ação pode ser executada?

Escopos mínimos previstos:

```text
organização
empresa
setor
obra
centro de custo
relacional
```

---

## 17. Escopo de organização

Exemplo:

```text
atividade.visualizar
→ toda a organização
```

Uso restrito a quem realmente precisa.

---

## 18. Escopo de empresa

Exemplo:

```text
Paulo
perfil: Gestor Comercial
empresa: Biasi Engenharia
```

O mesmo usuário pode receber outro perfil em outra empresa interna.

---

## 19. Escopo de setor

Exemplo:

```text
fila.reordenar
→ Comercial
```

Isso não concede reordenação em Compras.

---

## 20. Escopo de obra

Exemplo:

```text
atividade.visualizar
→ Obra GEHAKA
```

Útil quando a pessoa deve acessar determinado trabalho independentemente do setor.

---

## 21. Escopo de centro de custo

Obra e centro de custo são conceitos independentes.

A autorização pode considerar um ou ambos conforme a necessidade.

---

## 22. Escopos relacionais

Alguns acessos dependem da relação do usuário com o objeto.

Exemplos:

```text
atividades das quais sou dono
tarefas atribuídas a mim
setores dos quais participo
setores que gerencio
```

Esses escopos precisam ter significado canônico na LPS.

---

## 23. Dono da atividade precisa de visibilidade transversal

Uma atividade pode atravessar vários setores.

O dono continua responsável pelo resultado.

Portanto, mesmo sem pertencer ao setor executor, precisa enxergar contexto suficiente da própria atividade para acompanhar:

- status;
- posição de fila da sua demanda;
- prazo;
- devoluções;
- bloqueios;
- conclusão;
- conversa vinculada ao trabalho.

Isso não significa enxergar toda a fila ou todos os detalhes de outras demandas.

---

## 24. Fila e autorização

Devem existir ações diferentes para:

```text
ver minha posição
ver fila completa
reordenar fila
```

O solicitante pode saber:

```text
4º de 17
```

sem visualizar os nomes e detalhes das outras 16 demandas.

A fila completa fica para o setor executor e pessoas autorizadas.

Reordenação:

- gestor do setor, se autorizado;
- outras pessoas explicitamente autorizadas.

Toda reordenação é auditada.

---

## 25. Prazo e autorização

Separar ações como:

```text
propor prazo
aceitar prazo
recusar prazo
alterar prazo diretamente
```

O executor/setor pode propor novo prazo.

O dono aceita ou recusa.

Recusa de prazo proposto gera escalonamento conforme a regra já definida no projeto.

---

## 26. Comunicação segue o acesso ao trabalho

No D0 não existem canais livres como um Slack corporativo completo.

A conversa está ligada a:

- atividade;
- tarefa.

Quem não pode acessar o objeto não deve receber seu conteúdo apenas porque foi citado em outro lugar.

Mensagens não concedem autorização.

---

## 27. Perfis + concessões diretas

A regra principal é usar perfis.

Exemplo:

```text
Ryan
→ Perfil Orçamento
```

Exceção:

```text
Ryan
+ fila.reordenar
+ somente Comercial
```

Concessão direta deve ser usada para exceções pontuais, não como forma padrão de administrar toda a empresa.

---

## 28. Sem negação explícita no D0

No D0, a recomendação é:

```text
não existe concessão válida
→ negar
```

Evitar inicialmente uma segunda camada de:

```text
ALLOW
DENY
```

porque conflitos de herança aumentam muito a complexidade.

Se futuramente houver necessidade real de negação explícita, ela pode ser adicionada com regra de precedência clara.

---

## 29. Regra de negação por padrão

Toda nova ação nasce sem acesso para usuários comuns.

O administrador precisa concedê-la por perfil ou exceção.

Isso evita que uma atualização de produto libere automaticamente uma capacidade sensível.

---

## 30. Como a LPS calcula o acesso efetivo

Fluxo conceitual:

```text
1. Usuário existe e está ativo?
   └── não → negar

2. Usuário pertence à organização do recurso?
   └── não → negar

3. Existe ação válida recebida por perfil ou concessão direta?
   └── não → negar

4. O escopo da concessão contém o recurso?
   └── não → negar

5. A regra de negócio permite a operação neste estado?
   └── não → negar

6. Permitir operação.
```

Autorização não substitui regra de negócio.

Regra de negócio também não substitui autorização.

---

## 31. Origem da permissão precisa ser explicável

Quando o administrador consulta um usuário, a LPS deve conseguir responder:

```text
Por que Paulo pode reordenar esta fila?
```

Exemplo de resposta:

```text
Permitido por:
Perfil: Gestor Comercial
Escopo: Setor Comercial
```

ou:

```text
Permitido por:
Concessão direta
Escopo: Obra GEHAKA
```

Essa explicabilidade reduz erros de segurança e facilita suporte.

---

## 32. UI/UX da matriz de autorizações

A experiência deve aproveitar o que funciona bem em sistemas consolidados, mas ser mais simples.

Tela principal:

```text
Quem estou configurando?
[ Perfil ▼ ]  Gestor Comercial

Buscar ação...

Filtro:
(•) Todas
( ) Autorizadas
( ) Não autorizadas
```

Ações agrupadas:

```text
▾ Atividades
  [x] Visualizar
  [x] Criar
  [x] Editar
  [ ] Alterar dono

▾ Filas
  [x] Visualizar fila completa
  [x] Reordenar
```

---

## 33. Flagar e desflaga precisa ser rápido

A operação de autorização deve ser simples:

- clicar no checkbox altera a seleção;
- alteração fica visualmente pendente até salvar;
- botão “Salvar” confirma o lote;
- grupo pode ter “Marcar grupo” e “Desmarcar grupo”;
- pesquisa não perde alterações pendentes;
- filtro “Autorizadas” ajuda revisão;
- filtro “Não autorizadas” ajuda concessão;
- ações sensíveis podem exigir confirmação adicional.

Evitar obrigar o administrador a abrir uma tela para cada ação.

---

## 34. Não criar uma lista plana com milhares de linhas

Mesmo que o produto cresça, a interface deve usar:

- grupos recolhíveis;
- busca;
- filtros;
- contador por grupo;
- seleção em massa controlada;
- descrição curta da ação;
- nome amigável como principal;
- código técnico apenas como detalhe.

Exemplo:

```text
Reordenar fila
Permite alterar a ordem das tarefas nas filas do escopo autorizado.

Código técnico: fila.reordenar
```

---

## 35. Configuração de escopo na interface

Depois de escolher o que o perfil pode fazer, o administrador define onde vale.

Exemplo:

```text
Perfil: Gestor Comercial

Ações: 18 selecionadas

Escopo:
Empresa: Biasi Engenharia
Setor: Comercial
```

O sistema deve permitir múltiplas atribuições quando necessário.

---

## 36. Permissão herdada precisa aparecer diferente

Se uma ação vem de perfil, não deve parecer uma concessão direta editável sem contexto.

Exemplo:

```text
[x] Reordenar fila
    via Gestor Comercial
```

Se também existir concessão direta:

```text
+ acesso adicional
```

Isso evita o problema de desmarcar algo e o usuário continuar autorizado por outro perfil sem entender o motivo.

---

## 37. Tela do usuário

Deve concentrar:

```text
Dados
Setores
Perfis
Acessos adicionais
Escopos
Atividades abertas
Histórico de segurança
```

conforme autorização de quem está administrando.

---

## 38. Tela do perfil

Deve possuir:

```text
Dados do perfil
Ações
Usuários vinculados
Escopos de atribuição
Histórico
```

---

## 39. Copiar autorizações

É útil como produtividade administrativa, mas não deve ser a base principal do modelo.

Possibilidades:

```text
Copiar perfil
Copiar configuração de usuário
```

A cópia cria uma configuração independente e auditada.

Ela não mantém vínculo oculto com a origem.

Preferir perfis reutilizáveis antes de duplicar centenas de concessões diretas.

---

## 40. Relatórios de segurança

A LPS deve conseguir responder pelos dois sentidos.

### Por usuário

```text
Paulo
├── perfis
├── setores
├── ações efetivas
├── escopos
└── origem de cada permissão
```

### Por perfil

```text
Gestor Comercial
├── ações
└── usuários vinculados
```

### Por ação

```text
fila.reordenar
└── quem possui acesso e em qual escopo
```

### Por escopo

```text
Obra GEHAKA
└── usuários com acesso
```

### Por alteração

```text
quem concedeu
quem removeu
quando
antes
depois
```

---

## 41. Auditoria obrigatória

Toda mudança que altera o que alguém pode fazer deve deixar histórico.

Exemplos:

- perfil criado;
- perfil alterado;
- ação adicionada ao perfil;
- ação removida;
- usuário recebeu perfil;
- perfil removido do usuário;
- concessão direta adicionada;
- concessão direta removida;
- escopo alterado;
- setor alterado;
- gestor alterado;
- usuário inativado.

A auditoria precisa registrar:

```text
quem
quando
o quê
antes
depois
```

---

## 42. Segurança em camadas

Esconder botão é experiência do usuário, não segurança suficiente.

A autorização precisa existir em três níveis:

```text
INTERFACE
→ não exibe ações sem permissão

BACKEND
→ valida a operação

BANCO
→ impede acesso indevido aos dados
```

Para PostgreSQL/Supabase, RLS — Row Level Security, ou Segurança em Nível de Linha — deve ser usada como barreira final onde aplicável.

---

## 43. Organização é o limite máximo

Nenhuma configuração de escopo pode permitir acesso fora da organização do usuário.

Mesmo que alguém manipule:

```text
empresa_id
obra_id
setor_id
```

na requisição, o banco precisa impedir cruzamento entre tenants.

---

## 44. Empresa não substitui organização

A organização é o tenant.

Empresa é contexto operacional interno.

Um usuário pode acessar uma ou várias empresas da própria organização conforme autorização.

---

## 45. Acesso por setor não deve virar autorização automática

Exemplo incorreto:

```text
Paulo pertence ao Comercial
→ automaticamente pode editar tudo do Comercial
```

Correto:

```text
Paulo pertence ao Comercial
+
Perfil Gestor Comercial
+
Escopo Comercial
```

---

## 46. Acesso por obra não precisa de tabela de segurança exclusiva

A LPS não deve criar um motor diferente para:

```text
autorização por empresa
autorização por obra
autorização por setor
autorização por centro de custo
```

Todos são casos do mesmo conceito:

```text
ESCOPO
```

Essa é uma simplificação importante em relação ao benchmark.

---

## 47. Ações sensíveis

Algumas ações merecem destaque na interface e auditoria reforçada.

Exemplos:

```text
seguranca.gerir_autorizacoes
usuario.inativar
fila.reordenar
prazo.alterar_diretamente
auditoria.exportar
```

A classificação de sensibilidade não concede ou remove acesso; apenas orienta UX, confirmação e auditoria.

---

## 48. D0 — mínimo necessário

O D0 deve permitir:

### Estrutura

- criar/editar/inativar usuário;
- criar/editar/inativar setor;
- usuário em vários setores;
- definir gestor(es) de setor;
- criar/editar/inativar perfil.

### Autorizações

- grupos de ações;
- ações atômicas do produto;
- marcar/desmarcar ações no perfil;
- atribuir vários perfis ao usuário;
- definir escopo da atribuição;
- concessão direta para exceção;
- negação por padrão;
- consulta de acesso efetivo;
- histórico das alterações.

### Escopos mínimos

- organização;
- empresa;
- setor;
- obra;
- centro de custo;
- relações essenciais como “minhas atividades” e “tarefas atribuídas”.

### UX

- busca;
- grupos recolhíveis;
- filtros todas/autorizadas/não autorizadas;
- checkboxes;
- marcar/desmarcar grupo;
- salvar lote;
- mostrar origem da permissão.

---

## 49. O que pode ficar depois do D0

- negação explícita;
- permissão por campo;
- acessos temporários com expiração;
- aprovação de concessões sensíveis;
- usuários externos sofisticados;
- simulador “ver como usuário”;
- comparação automática entre usuários;
- recomendação de perfil por inteligência artificial;
- construtor avançado de políticas;
- reorganização livre de grupos de ações;
- cópia em massa muito sofisticada.

---

## 50. Exemplos consolidados

### Ryan — executor de orçamento

```text
Setor: Comercial
Perfil: Orçamento

Pode:
- visualizar tarefas atribuídas
- iniciar
- pausar
- retomar
- concluir
- registrar tempo

Não pode automaticamente:
- reordenar fila
- alterar perfil de usuário
- enxergar fila completa de outros setores
```

### Paulo — gestor comercial

```text
Setor: Comercial
Perfil: Gestor Comercial

Pode, conforme configuração:
- criar atividade
- visualizar atividades do setor
- acompanhar atividades das quais é dono
- atribuir responsável
- ver fila completa do Comercial
- reordenar fila do Comercial
- negociar prazos
```

### Diretor

Pode receber perfil corporativo com escopo de organização para determinados relatórios e visões.

Isso não significa acesso irrestrito a toda configuração administrativa.

### Solicitante de outro setor

Pode acompanhar a própria demanda e sua posição exata na fila sem visualizar nomes e detalhes das outras demandas.

---

## 51. Testes mínimos de aceite

O módulo não está pronto se não conseguir provar estes cenários:

1. usuário participa de dois setores sem receber automaticamente todas as permissões;
2. dois usuários do mesmo setor podem ter acessos diferentes;
3. dois usuários com o mesmo perfil podem trabalhar em escopos diferentes;
4. usuário pode receber dois perfis e somar capacidades;
5. concessão direta pode adicionar uma exceção;
6. usuário sem concessão válida recebe negação;
7. usuário não acessa dados de outra organização;
8. dono acompanha sua própria atividade mesmo quando a tarefa está em outro setor;
9. solicitante vê sua posição na fila sem ver as demais demandas;
10. gestor autorizado reordena a fila e a alteração fica auditada;
11. administrador consegue descobrir de onde veio uma permissão;
12. inativar usuário preserva histórico;
13. alteração de perfil deixa trilha de auditoria;
14. interface permite marcar e desmarcar ações rapidamente.

---

## 52. Decisões consolidadas

- usuário pertence a uma única organização;
- organização pode possuir várias empresas;
- usuário pode ter acesso a uma ou várias empresas internas;
- usuário pode participar de vários setores;
- setor é configurável e não fixo no código;
- participação em setor não concede permissão automaticamente;
- um setor pode possuir vários gestores;
- gestor estrutural não significa acesso irrestrito;
- perfil é configurável pela organização;
- usuário pode possuir vários perfis;
- perfil não é cargo e não é setor;
- ações representam capacidades reais do produto;
- ações atômicas não são inventadas livremente pelo cliente no D0;
- cliente monta livremente perfis com as ações disponíveis;
- grupos organizam ações, mas não concedem acesso;
- escopo define onde a ação vale;
- empresa, setor, obra e centro de custo são tipos de escopo, não motores separados;
- concessões diretas servem para exceções;
- D0 usa negação por padrão e não precisa de DENY explícito;
- autorização precisa ser explicável;
- toda alteração de segurança é auditada;
- interface deve permitir check/uncheck rápido, busca e filtros;
- segurança real existe no backend e no banco;
- dono da atividade possui visibilidade transversal suficiente para acompanhar seu resultado;
- visualizar posição própria da fila é diferente de visualizar fila completa;
- reordenar fila exige ação específica;
- administrador deve conseguir consultar acesso por usuário, perfil, ação e escopo.

---

## 53. Questões que continuam abertas

Ainda podem ser refinadas durante implementação:

- se cargo/função organizacional entra no D0 ou fica para D1;
- necessidade de perfil com escopo padrão ou apenas escopo na atribuição ao usuário;
- UX exata para múltiplos escopos em uma mesma atribuição;
- necessidade futura de DENY explícito;
- política para usuários externos;
- acesso temporário e expiração;
- aprovação de concessões sensíveis;
- hierarquia formal de setores;
- política de autenticação multifator;
- simulação “ver como usuário”.

Esses pontos não alteram o princípio central da arquitetura.

---

## 54. Regra de ouro

> **A LPS deve conhecer suas capacidades, mas não deve conhecer antecipadamente a estrutura de cada cliente. O cliente cadastra usuários, setores, perfis e escopos; a LPS aplica o mesmo motor de autorização para todos.**

---

## 55. Resumo funcional

```text
ORGANIZAÇÃO É CRIADA
↓
EMPRESAS SÃO CADASTRADAS
↓
SETORES SÃO CONFIGURADOS
↓
USUÁRIOS SÃO CRIADOS
↓
USUÁRIOS PARTICIPAM DE 0..N SETORES
↓
PERFIS SÃO CRIADOS
↓
AÇÕES REAIS DO PRODUTO SÃO MARCADAS/DESMARCADAS NOS PERFIS
↓
PERFIS SÃO ATRIBUÍDOS A USUÁRIOS
↓
ESCOPOS DEFINEM ONDE ESSAS CAPACIDADES VALEM
↓
EXCEÇÕES DIRETAS PODEM SER CONCEDIDAS
↓
A LPS CALCULA A PERMISSÃO EFETIVA
↓
SE NÃO HOUVER CONCESSÃO VÁLIDA: NEGAR
↓
SE HOUVER CONCESSÃO + ESCOPO + REGRA DE NEGÓCIO VÁLIDOS: PERMITIR
↓
TODA ALTERAÇÃO DE SEGURANÇA É AUDITADA
```

---

## 56. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Estrutura inicial de usuários, setores, perfis, ações e escopos |
| 2.0 | Revisão após estudo do dinamismo de perfis, ações, usuários e autorizações por contexto; consolidação do modelo Sujeito + Ação + Escopo + Origem e da UX de marcação/desmarcação |

