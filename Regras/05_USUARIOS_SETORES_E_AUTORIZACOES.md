# 05 — Usuários, Setores e Autorizações

> Documento funcional da LPS para definir quem pertence à organização, em quais empresas e setores atua, quais ações pode executar, sobre quais dados essas ações são permitidas e como a configuração de acesso deve permanecer dinâmica sem comprometer segurança ou simplicidade.

---

# 1. Objetivo deste documento

Este documento define a estrutura de usuários, setores e autorizações da LPS.

Ele deve responder:

- o que é a organização da LPS;
- o que é uma empresa dentro da organização;
- como um usuário pertence à organização;
- como um usuário participa de um ou vários setores;
- por que participar de um setor não significa automaticamente ter todas as permissões desse setor;
- o que é um perfil;
- o que é um grupo de ações;
- o que é uma ação;
- o que é uma autorização;
- o que é um escopo;
- como a LPS decide se alguém pode ou não executar determinada ação;
- como permitir que um usuário veja atividades de setores dos quais não faz parte operacionalmente;
- quem pode criar cadastros;
- quem pode visualizar;
- quem pode alterar fila;
- quem pode atribuir responsáveis;
- quem pode mover uma tarefa;
- quem pode aprovar;
- quem pode concluir;
- como manter essa estrutura configurável por empresa;
- como impedir que a flexibilidade vire perda de controle.

Este documento não define:

- a estrutura física completa das tabelas;
- a política técnica final de segurança no banco;
- o layout das telas;
- todos os cadastros auxiliares;
- todos os relatórios;
- integrações externas;
- a estrutura completa de holdings ou grupos econômicos.

Esses assuntos pertencem aos documentos específicos da LPS.

---

# 2. Princípio central

A regra central de autorização da LPS é:

> **Quem pode fazer o quê, sobre qual informação e dentro de qual escopo?**

A LPS não deve depender de regras fixas como:

```text
Se usuário é gestor:
    pode editar tudo
```

ou:

```text
Se usuário é do Financeiro:
    vê todas as tarefas financeiras
```

Essas regras são rígidas demais.

A LPS precisa separar:

```text
USUÁRIO
+
PERFIL
+
AÇÃO
+
ESCOPO
=
AUTORIZAÇÃO
```

---

# 3. Inspiração sem cópia

Sistemas consolidados demonstram que autorização configurável é um diferencial importante.

A LPS deve aproveitar o conceito de:

- grupos de ações;
- ações individuais;
- perfis;
- usuários;
- autorizações;
- escopos;
- cópia de autorizações;
- configuração por empresa.

Mas não deve reproduzir toda a estrutura de outro ERP.

O objetivo é usar o princípio:

> **O comportamento de acesso deve ser configurável sem alterar o código para cada cliente.**

---

# 4. Estrutura geral

A estrutura conceitual da LPS pode ser vista assim:

```text
ORGANIZAÇÃO LPS
│
├── EMPRESAS
│
├── USUÁRIOS
│
├── SETORES
│
├── PERFIS
│
├── GRUPOS DE AÇÕES
│   └── AÇÕES
│
└── AUTORIZAÇÕES
    ├── quem
    ├── pode fazer o quê
    └── em qual escopo
```

---

# 5. Organização da LPS

A organização é o ambiente principal de um cliente dentro da LPS.

Exemplos conceituais:

```text
Biasi
```

```text
Instaladora X
```

Cada organização possui seus próprios:

- usuários;
- empresas;
- setores;
- perfis;
- autorizações;
- atividades;
- tarefas;
- filas;
- configurações.

---

# 6. Uma organização não é a mesma coisa que uma empresa operacional

A organização representa o ambiente da LPS.

Dentro dela podem existir uma ou várias empresas operacionais.

Exemplo:

```text
Organização LPS:
Biasi
```

Dentro:

```text
Empresa:
Biasi Engenharia
```

e futuramente outras empresas que pertençam ao mesmo ambiente operacional.

---

# 7. Usuário pertence a uma única organização

Decisão consolidada:

> Um usuário da LPS pertence a uma única organização.

Exemplo:

```text
Paulo
→ Organização Biasi
```

Ele não pertence simultaneamente à:

```text
Biasi
+
Instaladora X
```

com o mesmo vínculo organizacional.

---

# 8. Isolamento entre organizações

Dados de uma organização não devem ser acessíveis por usuários de outra organização.

Exemplo:

```text
Usuário da Biasi
❌ não acessa dados da Instaladora X
```

Esse isolamento é estrutural.

Não deve depender apenas da interface.

---

# 9. Empresa dentro da organização

Uma organização pode possuir uma ou várias empresas.

A empresa pode representar uma entidade operacional ou jurídica utilizada no trabalho.

Exemplo:

```text
Organização:
Biasi
```

Empresas:

```text
Biasi Engenharia
Via Appia
Outra empresa operacional
```

conforme a realidade configurada.

---

# 10. Empresa pode também possuir outro papel

Uma entidade cadastrada pode, em outro contexto, também ser cliente.

Exemplo:

```text
Via Appia
```

pode ser:

```text
Empresa operacional
```

e também:

```text
Cliente
```

A modelagem técnica será detalhada no banco de dados.

---

# 11. Acesso por empresa

Mesmo pertencendo à organização, um usuário não precisa possuir acesso a todas as empresas internas.

Exemplo:

```text
Paulo
Organização: Biasi

Acesso:
✅ Biasi Engenharia
❌ Empresa B
```

---

# 12. Organização define o limite máximo

Nenhuma autorização pode ultrapassar a organização do usuário.

Primeiro limite:

```text
organização
```

Depois, dentro dela, podem existir limites menores como:

- empresa;
- setor;
- obra;
- centro de custo;
- atividade própria;
- tarefa atribuída.

---

# 13. Usuário

Usuário é a identidade que acessa a LPS.

Um usuário deve possuir, no mínimo:

- identificação;
- vínculo com organização;
- situação ativa/inativa;
- autenticação;
- perfis;
- setores;
- autorizações;
- escopos.

---

# 14. Usuário não é sinônimo de colaborador

No futuro, podem existir usuários como:

- colaborador;
- gestor;
- diretor;
- prestador;
- consultor;
- auditor;
- administrador.

A autorização é o que define o que cada um pode fazer.

---

# 15. Tipo de usuário não deve controlar tudo

Evitar regras como:

```text
tipo_usuario = "gerente"
→ pode tudo
```

ou:

```text
tipo_usuario = "colaborador"
→ só pode visualizar
```

A LPS deve utilizar permissões configuráveis.

---

# 16. Status do usuário

Um usuário pode possuir estados como:

```text
ativo
```

```text
inativo
```

Quando inativado:

- histórico permanece;
- ações anteriores permanecem associadas;
- sessões e auditorias não são apagadas;
- acesso é interrompido.

---

# 17. Não apagar usuário que possui histórico

Se Ryan executou tarefas durante dois anos e depois saiu da empresa:

```text
Ryan
→ inativo
```

O histórico continua mostrando:

```text
Executado por Ryan
```

Nunca substituir por:

```text
Usuário inexistente
```

---

# 18. Setor

Setor representa uma unidade organizacional configurada pela empresa.

Exemplos:

```text
Comercial
```

```text
Financeiro
```

```text
Administrativo
```

```text
Engenharia
```

```text
Almoxarifado
```

---

# 19. Setores não são fixos no código

A LPS nunca deve exigir:

```text
Financeiro
Comercial
Suprimentos
```

como nomes obrigatórios.

Uma empresa pode possuir:

```text
Administrativo
Operações
Projetos
```

e funcionar normalmente.

---

# 20. Setor é cadastro configurável

A empresa cria sua estrutura.

Exemplo:

```text
Cadastros
↓
Setores
↓
Novo setor
```

Quem pode criar depende de autorização.

---

# 21. Não criar setor durante a atividade no D0

Decisão consolidada:

> O setor não precisa ser criado diretamente no formulário da atividade.

Se não existir:

```text
Usuário autorizado
→ vai ao cadastro de setores
→ cria
→ retorna à atividade
```

Isso reduz complexidade inicial.

---

# 22. Duplicidade de setor

A LPS deve impedir duplicidade óbvia.

Exemplo:

```text
Financeiro
FINANCEIRO
 financeiro
```

podem ser considerados equivalentes.

---

# 23. Nomes parecidos não são automaticamente duplicados

Exemplo:

```text
Financeiro
```

e:

```text
Financeiro e Administrativo
```

podem representar setores diferentes.

A LPS não deve bloquear por similaridade sem necessidade.

---

# 24. Usuário pode participar de vários setores

Decisão consolidada:

> Um usuário pode pertencer a mais de um setor.

Exemplo:

```text
Paulo

Setores:
- Comercial
- Administrativo
- Diretoria
```

---

# 25. Participar de setor não é a mesma coisa que visualizar setor

Exemplo:

Paulo pode atuar operacionalmente no:

```text
Comercial
```

e possuir autorização para visualizar:

```text
Administrativo
```

sem ser executor habitual desse setor.

---

# 26. Participação operacional

O vínculo usuário-setor pode indicar:

> Esta pessoa faz parte deste setor.

Isso pode ser usado para:

- distribuição de tarefas;
- filtros;
- responsáveis elegíveis;
- visão de equipe;
- fila.

---

# 27. Autorização de acesso é separada

A autorização responde:

> Esta pessoa pode executar determinada ação sobre dados deste setor?

Assim:

```text
Paulo
Setor operacional:
Comercial
```

pode possuir:

```text
atividade.visualizar
Escopo:
Administrativo
```

---

# 28. Exemplo do orçamentista

Usuário:

```text
Paulo
```

Função operacional:

```text
Orçamentista
```

Setor principal:

```text
Comercial
```

Mas pode ser configurado para:

```text
Visualizar atividades do Administrativo
```

A LPS deve permitir isso sem alterar código.

---

# 29. Setor principal

Pode ser útil existir um setor principal para:

- organização;
- relatórios;
- experiência inicial;
- filtros padrão.

Mas isso não limita os demais vínculos.

Exemplo:

```text
Setor principal:
Comercial

Outros setores:
Administrativo
Diretoria
```

---

# 30. Um setor pode ter vários gestores

A LPS não deve presumir obrigatoriamente um único gestor por setor.

A empresa pode possuir:

- gestor;
- coordenador;
- pessoas autorizadas.

O conceito de dono único se aplica à atividade, não necessariamente à estrutura do setor.

---

# 31. Gestor não significa acesso irrestrito

Ser gestor do setor não precisa automaticamente permitir:

- excluir;
- alterar configurações;
- acessar outra empresa;
- criar usuários;
- alterar segurança.

Essas ações dependem de autorização.

---

# 32. Perfil

Perfil é um conjunto reutilizável de autorizações.

Exemplos:

```text
Colaborador Comercial
```

```text
Gestor de Setor
```

```text
Administrador
```

```text
Diretoria
```

---

# 33. Perfil não deve ser rígido no código

Cada organização pode criar seus próprios perfis.

Exemplo:

Empresa A:

```text
Assistente
Supervisor
Gerente
```

Empresa B:

```text
Analista
Coordenador
Diretor
```

---

# 34. Perfil reduz configuração repetitiva

Sem perfil:

```text
configurar 80 ações para cada usuário
```

Com perfil:

```text
configurar perfil uma vez
↓
atribuir a vários usuários
```

---

# 35. Usuário pode possuir mais de um perfil

Exemplo:

```text
Paulo

Perfil 1:
Gestor Comercial

Perfil 2:
Visualizador Administrativo
```

A autorização final é composta pelas permissões válidas desses perfis e seus escopos.

---

# 36. Perfil não é setor

Exemplo:

```text
Setor:
Comercial
```

é estrutura organizacional.

```text
Perfil:
Gestor Comercial
```

é conjunto de autorizações.

Não misturar.

---

# 37. Perfil não é cargo

Exemplo:

```text
Cargo:
Engenheiro
```

```text
Perfil:
Aprovador de atividades
```

São conceitos diferentes.

A mesma função pode possuir diferentes permissões em empresas diferentes.

---

# 38. Grupo de ações

Grupo de ações organiza ações relacionadas.

Exemplo:

```text
Grupo:
Gestão de Atividades
```

Ações:

```text
Consultar atividade
Criar atividade
Editar atividade
Alterar dono
Cancelar atividade
Concluir atividade
Reabrir atividade
```

---

# 39. Grupo de ações não concede acesso sozinho

O grupo serve para organização.

A autorização acontece sobre as ações.

Exemplo:

```text
Grupo:
Cadastros
```

não significa automaticamente:

```text
pode tudo em Cadastros
```

---

# 40. Exemplo de grupo — Atividades

```text
Gestão de Atividades
```

Ações possíveis:

```text
atividade.visualizar
atividade.criar
atividade.editar
atividade.alterar_dono
atividade.cancelar
atividade.concluir
atividade.reabrir
```

---

# 41. Exemplo de grupo — Tarefas

```text
Gestão de Tarefas
```

Ações:

```text
tarefa.visualizar
tarefa.criar
tarefa.editar
tarefa.assumir
tarefa.atribuir
tarefa.iniciar
tarefa.pausar
tarefa.retomar
tarefa.devolver
tarefa.concluir
tarefa.cancelar
```

---

# 42. Exemplo de grupo — Filas

```text
Gestão de Filas
```

Ações:

```text
fila.visualizar
fila.visualizar_completa
fila.reordenar
fila.priorizar
```

---

# 43. Exemplo de grupo — Prazos

```text
Gestão de Prazos
```

Ações:

```text
prazo.visualizar
prazo.propor
prazo.aceitar
prazo.recusar
prazo.alterar
```

---

# 44. Exemplo de grupo — Setores

```text
Cadastro de Setores
```

Ações:

```text
setor.visualizar
setor.criar
setor.editar
setor.inativar
```

---

# 45. Exemplo de grupo — Usuários

```text
Gestão de Usuários
```

Ações:

```text
usuario.visualizar
usuario.criar
usuario.editar
usuario.inativar
usuario.atribuir_setor
usuario.atribuir_perfil
```

---

# 46. Exemplo de grupo — Segurança

```text
Segurança
```

Ações:

```text
perfil.visualizar
perfil.criar
perfil.editar
perfil.inativar
autorizacao.visualizar
autorizacao.editar
autorizacao.copiar
```

---

# 47. Exemplo de grupo — Auditoria

```text
Auditoria
```

Ações:

```text
auditoria.visualizar
auditoria.exportar
```

---

# 48. Ação

Ação é a menor capacidade que a LPS autoriza.

Exemplo:

```text
atividade.visualizar
```

---

# 49. Ação precisa representar comportamento

Evitar ações vagas como:

```text
atividades
```

Preferir:

```text
atividade.visualizar
atividade.criar
atividade.editar
atividade.concluir
```

---

# 50. Ação não deve depender da tela

A autorização deve ser sobre capacidade de negócio.

Evitar:

```text
tela_atividade_botao_3
```

Preferir:

```text
atividade.concluir
```

Assim, se a interface mudar, a regra de segurança continua válida.

---

# 51. Ação deve ser reutilizável em web e mobile

Exemplo:

```text
fila.reordenar
```

vale tanto para:

- navegador;
- aplicativo;
- API;
- integração.

---

# 52. Autorização

Autorização é o resultado de combinar:

```text
quem
+
ação
+
escopo
```

Exemplo:

```text
Paulo
pode
atividade.visualizar
no setor Administrativo
```

---

# 53. Escopo

Escopo define onde a autorização é válida.

Exemplos de escopo:

```text
Organização inteira
```

```text
Empresa específica
```

```text
Setor específico
```

```text
Obra específica
```

```text
Centro de custo específico
```

```text
Somente atividades próprias
```

```text
Somente tarefas atribuídas
```

---

# 54. Por que escopo é necessário

Sem escopo, a permissão:

```text
atividade.visualizar
```

poderia significar:

```text
visualizar todas as atividades da organização
```

Isso é amplo demais.

Com escopo:

```text
atividade.visualizar
+
Setor Comercial
```

a permissão fica precisa.

---

# 55. Escopo da organização

É o escopo mais amplo.

Exemplo:

```text
Diretor
atividade.visualizar
Organização inteira
```

Pode visualizar atividades permitidas em toda a organização.

---

# 56. Escopo por empresa

Exemplo:

```text
Usuário
atividade.visualizar

Empresa:
Biasi Engenharia
```

Não acessa automaticamente outra empresa operacional.

---

# 57. Escopo por setor

Exemplo:

```text
Paulo
atividade.visualizar

Setores:
Comercial
Administrativo
```

Mesmo que seu setor operacional principal seja Comercial.

---

# 58. Escopo por obra

Exemplo:

```text
Engenheiro da Obra X

atividade.visualizar
obra = X
```

Não acessa necessariamente atividades da Obra Y.

---

# 59. Escopo por centro de custo

Exemplo:

```text
Gestor
atividade.visualizar

Centro de custo:
Escritório
```

---

# 60. Escopos podem ser combinados

Exemplo:

```text
Empresa:
Biasi Engenharia

Setor:
Comercial

Obra:
Vale
```

A autorização pode ser restrita à interseção necessária.

A implementação técnica será detalhada no banco.

---

# 61. Escopo próprio

Algumas ações podem valer apenas para itens do próprio usuário.

Exemplo:

```text
atividade.visualizar_proprias
```

ou lógica equivalente:

```text
escopo = dono
```

---

# 62. Escopo de tarefas atribuídas

Exemplo:

```text
tarefa.editar
escopo = atribuídas ao usuário
```

A pessoa consegue editar somente as tarefas em que participa.

---

# 63. Participação em setor pode ajudar no escopo

Quando fizer sentido, a regra pode ser:

```text
visualizar tarefas dos setores dos quais participa
```

Mas isso deve ser uma autorização configurada, não um comportamento impossível de alterar.

---

# 64. Acesso além do setor

Exemplo desejado:

```text
Paulo
pertence ao Comercial
```

Mas possui:

```text
atividade.visualizar
escopo Administrativo
```

A LPS deve suportar esse cenário naturalmente.

---

# 65. Participar não significa visualizar tudo

Também pode ocorrer o contrário.

Usuário pertence ao setor:

```text
Financeiro
```

mas só pode visualizar:

```text
tarefas atribuídas a ele
```

A LPS deve suportar isso.

---

# 66. Regra de negação por padrão

Princípio:

> **Se não existe autorização válida, a ação é negada.**

Isso é conhecido como:

```text
default deny
```

ou:

```text
negação por padrão
```

---

# 67. Por que negar por padrão

Se o sistema permitir tudo até alguém bloquear, qualquer erro de configuração pode expor dados.

O modelo seguro é:

```text
não autorizado
↓
até existir permissão explícita
```

---

# 68. A interface não é segurança

Esconder um botão não basta.

Exemplo:

```text
Botão "Excluir"
não aparece
```

Isso melhora a interface.

Mas a API e o banco também precisam impedir a ação.

---

# 69. Segurança em camadas

A autorização deve ser respeitada em:

```text
Interface
↓
API / aplicação
↓
Banco de dados
```

A implementação técnica será definida no documento do banco.

---

# 70. RLS

No banco Supabase/PostgreSQL, uma camada futura recomendada é:

**RLS — Row Level Security**, ou **segurança em nível de linha**.

Ela permite que o próprio banco valide quais registros cada usuário pode acessar.

A configuração técnica ficará no documento `08_BANCO_DE_DADOS.md`.

---

# 71. Perfis concedem ações

Exemplo:

```text
Perfil:
Colaborador Comercial
```

Pode conceder:

```text
atividade.visualizar
atividade.criar
tarefa.visualizar
tarefa.assumir
tarefa.iniciar
tarefa.pausar
tarefa.retomar
tarefa.concluir
```

---

# 72. Perfil pode possuir escopo padrão

Exemplo:

```text
Perfil:
Colaborador de Setor
```

Regra:

```text
ações válidas
nos setores associados ao usuário
```

Esse tipo de regra deve ser definido com cuidado para permanecer compreensível.

---

# 73. Perfis diferentes podem somar permissões

Exemplo:

```text
Paulo

Perfil:
Colaborador Comercial

+
Perfil:
Visualizador Administrativo
```

Resultado:

```text
executa no Comercial
+
visualiza Administrativo
```

---

# 74. Exceção individual

Pode existir necessidade de conceder uma autorização específica para uma pessoa.

Exemplo:

```text
Ryan
normalmente não pode reordenar fila
```

Mas recebe:

```text
fila.reordenar
no Comercial
```

---

# 75. Exceções não devem virar regra principal

Se todo usuário exige dezenas de exceções individuais, os perfis estão mal desenhados.

A prioridade deve ser:

```text
perfil
↓
exceções quando necessário
```

---

# 76. Permissão direta ao usuário

A LPS pode suportar autorização direta.

Exemplo:

```text
usuario:
Ryan

ação:
fila.reordenar

escopo:
Comercial
```

---

# 77. Negação explícita

No início, evitar um sistema excessivamente complexo de:

```text
ALLOW
DENY
OVERRIDE
PRIORITY
```

A regra básica de negação por padrão + concessões explícitas tende a ser suficiente para o D0.

Negações explícitas podem ser avaliadas se surgir necessidade real.

---

# 78. Cópia de autorizações

Pode ser útil copiar configuração de um usuário ou perfil.

Exemplo:

```text
Novo usuário:
Luan
```

Copiar de:

```text
Ryan
```

Isso reduz trabalho operacional.

---

# 79. Cópia não deve criar vínculo permanente

Se autorizações forem copiadas:

```text
Ryan → Luan
```

alterar Ryan depois não deve necessariamente alterar Luan, salvo se ambos usam o mesmo perfil.

A cópia é uma operação pontual.

---

# 80. Perfil é melhor que copiar tudo

Quando várias pessoas realmente devem possuir a mesma regra, preferir:

```text
mesmo perfil
```

em vez de cópias independentes.

---

# 81. Quem pode criar usuário

Precisa da ação:

```text
usuario.criar
```

no escopo adequado.

---

# 82. Quem pode editar usuário

Precisa:

```text
usuario.editar
```

---

# 83. Quem pode inativar usuário

Precisa:

```text
usuario.inativar
```

A inativação não apaga histórico.

---

# 84. Quem pode associar setor ao usuário

Precisa da ação:

```text
usuario.atribuir_setor
```

ou equivalente.

---

# 85. Quem pode associar perfil

Precisa:

```text
usuario.atribuir_perfil
```

Isso é uma ação sensível porque altera capacidade de acesso.

---

# 86. Alterações de segurança precisam ser auditadas

Registrar:

- quem alterou;
- usuário afetado;
- perfil anterior;
- perfil novo;
- setor anterior;
- setor novo;
- autorizações concedidas;
- autorizações removidas;
- data e hora.

---

# 87. Quem pode criar setor

Precisa:

```text
setor.criar
```

Não depende simplesmente de ser gestor.

---

# 88. Quem pode editar setor

Precisa:

```text
setor.editar
```

---

# 89. Quem pode inativar setor

Precisa:

```text
setor.inativar
```

Setor com histórico não deve ser apagado livremente.

---

# 90. Setor inativo

Quando inativado:

- não aparece para novos vínculos;
- não recebe novas tarefas;
- histórico permanece;
- atividades antigas continuam apontando corretamente.

---

# 91. Quem pode visualizar atividade

A ação:

```text
atividade.visualizar
```

precisa ser combinada com escopo.

Exemplo:

```text
Paulo
atividade.visualizar
setores Comercial + Administrativo
```

---

# 92. Quem pode criar atividade

Ação:

```text
atividade.criar
```

Pode ser limitada por:

- empresa;
- setor;
- obra;
- centro de custo.

---

# 93. Quem pode editar atividade

Ação:

```text
atividade.editar
```

Pode existir regra mais restrita:

```text
somente atividades próprias
```

ou:

```text
atividades do setor
```

---

# 94. Quem pode alterar dono

Ação sensível:

```text
atividade.alterar_dono
```

Não deve ser incluída automaticamente em todo perfil.

---

# 95. Quem pode concluir atividade

Ação:

```text
atividade.concluir
```

A regra pode permitir:

- dono;
- gestor;
- pessoas autorizadas.

A decisão detalhada pertence ao fluxo.

---

# 96. Quem pode reabrir atividade

Ação:

```text
atividade.reabrir
```

Deve ser mais restrita que simples edição.

---

# 97. Quem pode cancelar atividade

Ação:

```text
atividade.cancelar
```

Cancelamento precisa gerar auditoria.

---

# 98. Quem pode visualizar tarefa

Ação:

```text
tarefa.visualizar
```

Escopo pode ser:

- própria;
- atribuída;
- setor;
- empresa;
- organização.

---

# 99. Quem pode criar tarefa

Ação:

```text
tarefa.criar
```

Pode estar associada ao dono, gestor ou perfil específico.

---

# 100. Quem pode assumir tarefa

Ação:

```text
tarefa.assumir
```

Essa permissão permite que pessoa da fila assuma atividade sem distribuição prévia.

---

# 101. Configuração sobre assumir tarefa

Empresa A:

```text
qualquer membro autorizado do setor
pode assumir
```

Empresa B:

```text
somente gestor atribui
```

A LPS deve suportar os dois modelos.

---

# 102. Quem pode atribuir responsável

Ação:

```text
tarefa.atribuir
```

Pode ser concedida para:

- gestor;
- coordenador;
- dono;
- outro perfil autorizado.

---

# 103. Atribuir responsável não significa poder editar tudo

Uma pessoa pode possuir:

```text
tarefa.atribuir
```

sem possuir:

```text
tarefa.editar
```

em outros campos.

As ações precisam ser independentes.

---

# 104. Quem pode iniciar tarefa

Ação:

```text
tarefa.iniciar
```

Normalmente limitada a executores autorizados.

---

# 105. Quem pode pausar

Ação:

```text
tarefa.pausar
```

---

# 106. Quem pode retomar

Ação:

```text
tarefa.retomar
```

---

# 107. Quem pode devolver

Ação:

```text
tarefa.devolver
```

Devolução exige motivo conforme definido no documento de fluxo.

---

# 108. Quem pode concluir tarefa

Ação:

```text
tarefa.concluir
```

---

# 109. Quem pode alterar fluxo

Ação sensível:

```text
fluxo.alterar
```

Pode incluir:

- adicionar tarefa;
- remover/cancelar tarefa;
- mudar ordem;
- mudar dependência;
- mudar setor.

---

# 110. Fluxo padrão x exceção

Um usuário pode:

```text
usar fluxo padrão
```

sem possuir:

```text
alterar fluxo
```

Isso ajuda a preservar processo.

---

# 111. Quem pode visualizar fila completa

Ação:

```text
fila.visualizar_completa
```

Essa permissão é diferente de:

```text
visualizar própria posição
```

---

# 112. Solicitante pode ver posição sem ver fila

Exemplo:

```text
posição:
4 de 17
```

mas não:

```text
lista das 17 demandas
```

Isso exige permissões separadas.

---

# 113. Quem pode reordenar fila

Ação:

```text
fila.reordenar
```

Decisão consolidada:

> Gestor + pessoas autorizadas.

Não qualquer membro do setor.

---

# 114. Quem pode priorizar

Pode existir ação:

```text
fila.priorizar
```

caso seja necessário diferenciar:

```text
mudar ordem
```

de:

```text
marcar prioridade
```

A necessidade final será validada no banco.

---

# 115. Quem pode propor prazo

Ação:

```text
prazo.propor
```

Pode ser concedida a:

- executor;
- gestor;
- pessoas autorizadas.

---

# 116. Quem pode aceitar prazo

Normalmente:

```text
dono da atividade
```

ou pessoa autorizada.

Ação:

```text
prazo.aceitar
```

---

# 117. Quem pode recusar prazo

Ação:

```text
prazo.recusar
```

A recusa pode gerar escalonamento automático.

---

# 118. Quem pode alterar prazo diretamente

Pode existir ação mais forte:

```text
prazo.alterar
```

Ela não deve substituir o fluxo normal de negociação sem necessidade.

---

# 119. Quem pode escalar

Pode existir:

```text
escalonamento.criar
```

Além de regras automáticas.

---

# 120. Quem pode resolver escalonamento

Ação:

```text
escalonamento.resolver
```

Restrita a responsáveis definidos pela empresa.

---

# 121. Quem pode visualizar auditoria

Ação:

```text
auditoria.visualizar
```

Pode ser limitada por escopo.

---

# 122. Quem pode corrigir tempo

Ação:

```text
tempo.corrigir
```

Correções devem ser auditadas.

---

# 123. Quem pode lançar tempo retroativo

Ação:

```text
tempo.lancar_manual
```

Pode ser diferente de:

```text
tempo.corrigir
```

---

# 124. Quem pode visualizar métricas

Ação:

```text
metricas.visualizar
```

Escopo pode variar por:

- próprio usuário;
- setor;
- empresa;
- organização.

---

# 125. Quem pode visualizar métricas pessoais

Usuário pode possuir:

```text
metricas.visualizar_proprias
```

sem acessar dados consolidados da equipe.

---

# 126. Quem pode visualizar métricas de setor

Gestor pode possuir:

```text
metricas.visualizar_setor
```

---

# 127. Quem pode visualizar métricas corporativas

Diretoria pode possuir:

```text
metricas.visualizar_organizacao
```

---

# 128. Configuração por empresa

A LPS precisa permitir que cada organização configure:

- setores;
- perfis;
- ações atribuídas;
- escopos;
- pessoas autorizadas;
- regras de visualização;
- regras de atribuição;
- regras de fila;
- regras de prazo;
- regras de escalonamento.

---

# 129. Configuração não significa código diferente

Empresa A:

```text
Colaborador pode assumir tarefas.
```

Empresa B:

```text
Somente gestor atribui tarefas.
```

A implementação da LPS é a mesma.

A diferença está na autorização.

---

# 130. Empresa sem Financeiro

Se uma empresa não possui setor Financeiro:

```text
não há problema.
```

Ela pode criar:

```text
Administrativo
```

e configurar seus fluxos.

Esse é exatamente o motivo para a estrutura ser dinâmica.

---

# 131. Empresa com muitos setores

Também deve funcionar.

Exemplo:

```text
30 setores
```

O sistema não deve depender de uma quantidade fixa.

---

# 132. Empresa pequena

Pode possuir:

```text
Administrativo
Operações
Comercial
```

e utilizar a mesma LPS.

---

# 133. Organização inicial simples

No início da implantação, a empresa pode criar:

- poucos setores;
- poucos perfis;
- poucas regras.

A configuração pode amadurecer depois.

---

# 134. Não exigir configuração excessiva antes do uso

A LPS precisa ser configurável, mas não pode exigir semanas de parametrização para começar.

O D0 deve permitir:

```text
criar organização
↓
criar empresa
↓
criar setores
↓
criar usuários
↓
atribuir perfil
↓
começar a operar
```

---

# 135. Perfis iniciais sugeridos

A LPS pode oferecer modelos iniciais como sugestão.

Exemplo:

```text
Administrador
Gestor
Colaborador
Visualizador
```

Mas a empresa deve poder adaptar.

---

# 136. Modelo não significa regra fixa

Se a empresa quiser:

```text
Coordenador de Campo
```

pode criar.

---

# 137. Administrador

Perfil administrativo pode possuir acesso amplo às configurações.

Mas mesmo o administrador deve permanecer limitado à própria organização.

---

# 138. Superadministrador da plataforma

Pode existir internamente para operação da LPS.

Esse papel não deve ser confundido com administrador da empresa cliente.

A implementação técnica será tratada separadamente.

---

# 139. Princípio do menor privilégio

Cada usuário deve receber apenas o acesso necessário para sua função.

Esse princípio reduz risco.

---

# 140. Evitar “dar tudo para funcionar”

Durante implantação, é comum liberar tudo porque é mais fácil.

Isso gera:

- risco;
- dificuldade de auditoria;
- excesso de acesso;
- confusão.

A LPS deve favorecer perfis claros.

---

# 141. Autorização de consulta

Consulta também é permissão.

Nem todo usuário precisa visualizar:

- valores;
- métricas de outras pessoas;
- atividades de outra obra;
- filas completas;
- auditoria detalhada.

---

# 142. Visualizar x editar

Essas ações precisam ser separadas.

Exemplo:

```text
Paulo
✅ visualizar Administrativo
❌ editar Administrativo
```

---

# 143. Criar x editar

Também podem ser diferentes.

Exemplo:

```text
Usuário
✅ criar atividade
❌ editar atividade de terceiros
```

---

# 144. Editar x excluir

Excluir é mais sensível.

Não deve ser consequência automática de editar.

---

# 145. Executar x administrar

Executar tarefa não deve conceder automaticamente capacidade de:

- configurar setor;
- mudar perfil;
- editar fluxo padrão;
- acessar métricas corporativas.

---

# 146. Configurar x operar

A LPS deve separar claramente:

```text
operação
```

de:

```text
administração do sistema
```

---

# 147. Cadastros

Uma área de:

```text
Cadastros
```

ou:

```text
Apoio
```

pode concentrar configurações como:

- setores;
- perfis;
- usuários;
- tipos;
- motivos;
- regras.

A nomenclatura final da interface será definida no documento 09.

---

# 148. Quem pode criar cadastros

Cada cadastro deve possuir ações próprias.

Exemplo:

```text
setor.criar
tipo_atividade.criar
motivo_devolucao.criar
```

Não utilizar uma única permissão genérica:

```text
pode_criar_tudo
```

salvo perfil administrativo que agregue as ações.

---

# 149. Grupo “Cadastros”

Pode reunir visualmente essas ações.

Exemplo:

```text
CADASTROS

Setores
- consultar
- criar
- editar
- inativar

Tipos de atividade
- consultar
- criar
- editar
- inativar
```

---

# 150. Escopo em cadastros

Cadastros podem existir em níveis diferentes.

Exemplo:

```text
Setor
→ organização
```

Outro cadastro pode ser:

```text
Centro de custo
→ empresa
```

A autorização precisa respeitar o nível.

---

# 151. Ações sensíveis

Exemplos de ações que merecem maior cuidado:

- atribuir perfil;
- editar autorização;
- excluir;
- reabrir atividade;
- alterar dono;
- corrigir tempo;
- alterar auditoria;
- visualizar dados corporativos;
- exportar dados.

---

# 152. Auditoria de ações sensíveis

Toda ação de segurança deve ser auditada.

Exemplo:

```text
Paulo concedeu a Ryan:
fila.reordenar
no Comercial
em 12/09/2026 14:20
```

---

# 153. Auditoria de login

Pode ser útil registrar:

- login;
- logout;
- falhas;
- sessão;
- dispositivo quando aplicável.

A profundidade técnica será definida no banco.

---

# 154. Auditoria de consulta sensível

Em alguns contextos, pode ser útil saber quem acessou informações sensíveis.

Não é requisito geral do D0, mas a arquitetura não deve impedir.

---

# 155. Alteração de perfil

Quando um usuário muda de perfil:

```text
Perfil anterior:
Colaborador

Novo:
Gestor
```

registrar.

---

# 156. Remoção de perfil

Também deve ficar registrada.

---

# 157. Inativação de perfil

Um perfil antigo pode ser inativado sem apagar usuários históricos que o utilizaram.

---

# 158. Perfil em uso

Se um perfil estiver atribuído a usuários, evitar exclusão física.

Preferir:

```text
inativar
```

---

# 159. Ação inativada

Se uma ação deixar de existir funcionalmente, pode ser inativada.

Histórico permanece.

---

# 160. Grupo de ações inativado

Mesma lógica.

---

# 161. Nomenclatura amigável

O código técnico pode ser:

```text
atividade.visualizar
```

A interface pode mostrar:

```text
Visualizar atividades
```

---

# 162. Descrição da ação

Cada ação deve possuir explicação clara.

Exemplo:

```text
Visualizar fila completa
Permite ver todas as tarefas e detalhes da fila do setor dentro do escopo autorizado.
```

Isso reduz erro de configuração.

---

# 163. Grupos ajudam administradores

Em vez de uma lista com centenas de permissões sem organização:

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

# 164. Pesquisa de ações

Quando houver muitas ações, a tela de autorização deve permitir busca.

Exemplo:

```text
buscar: fila
```

Resultados:

```text
Visualizar fila
Visualizar fila completa
Reordenar fila
```

---

# 165. Quantidade de ações pode crescer

Uma empresa consolidada pode possuir dezenas ou centenas de ações.

A arquitetura não deve depender de poucas permissões fixas.

---

# 166. Mas o D0 deve começar enxuto

Evitar criar 500 ações antes de existir funcionalidade.

As ações devem nascer conforme capacidades reais do produto.

---

# 167. Uma funcionalidade nova deve declarar suas ações

Exemplo:

Nova funcionalidade:

```text
Aprovações
```

Pode introduzir:

```text
aprovacao.visualizar
aprovacao.solicitar
aprovacao.aprovar
aprovacao.reprovar
```

---

# 168. Nenhuma funcionalidade deve ignorar segurança

Ao criar uma nova tela, perguntar:

> Quais ações existem aqui?

> Quem pode executá-las?

> Em qual escopo?

---

# 169. Escopo deve ser explícito

Evitar permissões que dependam de lógica escondida.

Exemplo ruim:

```text
gestor vê algumas coisas
```

Exemplo melhor:

```text
atividade.visualizar
escopo = setores A, B e C
```

---

# 170. Escopo herdado

Pode ser útil permitir:

```text
todos os setores da empresa
```

em vez de selecionar um por um.

Exemplo:

```text
Diretor
→ todos os setores da Empresa Biasi
```

---

# 171. Escopo dinâmico “meus setores”

Pode existir regra:

```text
escopo:
setores dos quais o usuário participa
```

Isso facilita manutenção.

Se o usuário mudar de setor, o acesso acompanha.

---

# 172. Escopo fixo

Também pode existir:

```text
escopo:
Administrativo
```

mesmo que usuário não pertença ao setor.

---

# 173. Meus setores + exceção

Exemplo:

```text
Paulo
Meus setores:
Comercial

Exceção:
visualizar Administrativo
```

---

# 174. Escopo de gestor

Um gestor pode possuir:

```text
fila.reordenar
nos setores que gerencia
```

Se mudar de setor, regra pode acompanhar.

A estrutura técnica precisa permitir isso sem criar regras obscuras.

---

# 175. Escopo por obra

Exemplo:

```text
Engenheiro A:
Obras X e Y
```

Pode visualizar atividades dessas obras, conforme ação.

---

# 176. Escopo por centro de custo

Exemplo:

```text
Administrativo:
Centro de custo Escritório
```

---

# 177. Obra e centro de custo são independentes

A autorização pode utilizar:

- obra;
- centro de custo;
- ambos.

O modelo completo será definido no banco.

---

# 178. Setor é escopo operacional relevante

Mesmo que a atividade tenha empresa e obra, o setor continua sendo importante para:

- fila;
- execução;
- visão da equipe;
- gestão.

---

# 179. Ação + escopo é a unidade lógica

Exemplo:

```text
ação:
atividade.visualizar

escopo:
setor Administrativo
```

Sem escopo, a permissão fica ambígua.

---

# 180. Autorizações por perfil

Um perfil pode definir ações.

Os escopos podem ser definidos:

- no perfil;
- no vínculo do usuário;
- em regra dinâmica.

A decisão técnica final deve buscar simplicidade.

---

# 181. Evitar explosão de perfis

Não criar:

```text
Gestor Comercial Obra A
Gestor Comercial Obra B
Gestor Comercial Obra C
```

apenas para mudar escopo.

Melhor:

```text
Perfil:
Gestor Comercial

Escopo do usuário:
Obras A e B
```

---

# 182. Perfil define o “o quê”

Exemplo:

```text
pode visualizar
pode criar
pode reordenar
```

---

# 183. Escopo define o “onde”

Exemplo:

```text
Comercial
Obra Vale
Empresa Biasi
```

---

# 184. Usuário define “quem”

Assim:

```text
Paulo
+
Gestor Comercial
+
Empresa Biasi / Setor Comercial
```

---

# 185. Benefício dessa separação

Permite reutilizar o mesmo perfil para várias pessoas.

Exemplo:

```text
Rian
Gestor Comercial
Escopo Comercial
```

```text
Outro usuário
Gestor Comercial
Escopo Comercial de outra empresa
```

---

# 186. Exemplo completo de autorização

```text
Usuário:
Paulo

Perfil:
Gestor Comercial

Ação:
fila.reordenar

Escopo:
Empresa Biasi
Setor Comercial

Resultado:
Permitido
```

---

# 187. Exemplo negado

```text
Usuário:
Paulo

Ação:
fila.reordenar

Escopo solicitado:
Financeiro
```

Sem autorização válida:

```text
Negado
```

---

# 188. Exemplo de visualização cruzada

```text
Usuário:
Paulo

Setor operacional:
Comercial

Ação:
atividade.visualizar

Escopo:
Administrativo
```

Resultado:

```text
Pode visualizar atividades administrativas
```

sem necessariamente poder editá-las.

---

# 189. Exemplo de gestor de fila

```text
Usuário:
Igor

Setor:
Almoxarifado

Ações:
fila.visualizar_completa
fila.reordenar
tarefa.atribuir
```

---

# 190. Exemplo de colaborador do Almoxarifado

```text
Usuário:
Matheus

Ações:
fila.visualizar
tarefa.visualizar
tarefa.assumir
tarefa.iniciar
tarefa.concluir
```

Pode executar sem reorganizar toda a fila.

---

# 191. Exemplo de solicitante externo ao setor

```text
Paulo
Setor:
Comercial

Solicitou tarefa ao Almoxarifado
```

Pode visualizar:

```text
posição 4 de 17
status
prazo
```

Mas não:

```text
fila completa
```

---

# 192. Exemplo de diretor

```text
Diretor

atividade.visualizar
fila.visualizar_completa
metricas.visualizar

Escopo:
organização inteira
```

Pode possuir visão ampla sem precisar participar de todos os setores.

---

# 193. Exemplo de administrador

```text
Administrador LPS da organização

usuario.criar
usuario.editar
setor.criar
perfil.criar
autorizacao.editar
```

Ainda limitado à própria organização.

---

# 194. Perfis padrão podem ser clonados

A LPS pode fornecer:

```text
Colaborador
Gestor
Administrador
```

A organização clona e ajusta.

Isso acelera implantação sem impor padrão.

---

# 195. Template de segurança

Futuramente, pode existir modelo recomendado por tipo de empresa.

Exemplo:

```text
Construtora
Instaladora
Escritório de Engenharia
```

Mas isso não pertence ao D0.

---

# 196. Usuário convidado

No futuro, pode existir acesso externo limitado.

Exemplo:

```text
Cliente
Fornecedor
Auditor
```

O princípio continua:

```text
ação + escopo
```

---

# 197. Acesso externo deve ser extremamente limitado

Exemplo:

Cliente pode visualizar:

```text
status da própria atividade
```

sem acesso à fila interna completa.

Não é prioridade do D0.

---

# 198. Temporariedade

Futuramente, uma autorização pode possuir:

```text
válida até 30/09
```

Útil para:

- temporários;
- consultores;
- substituições.

Não é prioridade inicial.

---

# 199. Substituição de gestor

Exemplo:

Gestor sai de férias.

Pode haver concessão temporária para outro usuário.

A arquitetura não deve impedir.

---

# 200. Aprovação de permissões sensíveis

Futuramente, alterações críticas podem exigir aprovação.

Exemplo:

```text
conceder acesso à organização inteira
```

Não é necessário no D0.

---

# 201. Revisão periódica de acessos

Uma organização madura pode revisar:

- usuários ativos;
- perfis;
- exceções;
- acessos amplos.

Esse recurso pode vir depois.

---

# 202. Relatório de acesso

Futuramente:

```text
Quem pode reordenar a fila do Financeiro?
```

A LPS deveria responder.

---

# 203. Relatório por usuário

Exemplo:

```text
Paulo pode:
- visualizar Comercial
- visualizar Administrativo
- reordenar Comercial
- criar atividades
- aceitar prazos próprios
```

---

# 204. Relatório por ação

Exemplo:

```text
Quem pode:
fila.reordenar
```

Resultado:

```text
Igor — Almoxarifado
Paulo — Comercial
...
```

---

# 205. Relatório por setor

Exemplo:

```text
Setor:
Financeiro

Quem visualiza?
Quem edita?
Quem reordena?
Quem atribui?
```

---

# 206. Explicabilidade da autorização

Se usuário recebe:

```text
Acesso negado
```

o sistema pode explicar de forma segura:

```text
Você não possui permissão para reordenar esta fila.
```

Não precisa expor regras internas sensíveis.

---

# 207. Administrador precisa entender por que acesso existe

Na tela de segurança, pode ser útil mostrar:

```text
Permitido via perfil:
Gestor Comercial
```

ou:

```text
Permitido diretamente ao usuário
```

---

# 208. Origem da permissão

Futuramente, a LPS deve conseguir dizer:

```text
Esta autorização veio de:
Perfil X
```

ou:

```text
Concessão individual
```

Isso facilita manutenção.

---

# 209. Conflito de autorizações

No modelo inicial, priorizar concessões claras para evitar conflitos complexos.

Se houver múltiplos perfis, a soma das concessões válidas define acesso.

A negação por padrão se aplica ao que não foi concedido.

---

# 210. Ações destrutivas

Exemplos:

- excluir;
- cancelar;
- reabrir;
- corrigir auditoria;
- alterar autorização.

Devem possuir permissão própria.

---

# 211. Confirmação na interface

Ações destrutivas podem exigir confirmação adicional.

Isso é UX, não segurança.

A autorização continua obrigatória.

---

# 212. Autorização não substitui regra de negócio

Mesmo que usuário tenha:

```text
atividade.concluir
```

o sistema pode impedir conclusão se regra obrigatória não foi atendida.

Exemplo:

```text
tarefas obrigatórias pendentes
```

Permissão responde:

> Pode tentar realizar a ação?

Regra de negócio responde:

> A ação é válida neste estado?

---

# 213. Regra de negócio não substitui autorização

O fato de uma atividade estar pronta para concluir não significa que qualquer pessoa pode concluir.

As duas validações são necessárias.

---

# 214. Autorização para própria atividade

Exemplo:

```text
dono pode aceitar prazo da própria atividade
```

Isso pode ser modelado por ação + relação com o objeto.

---

# 215. Autorização baseada em relação

Além de escopos fixos, existem relações como:

- sou dono;
- sou executor;
- sou criador;
- sou gestor do setor.

Essas relações podem participar da decisão.

---

# 216. Exemplo — dono

```text
Se usuário é dono
e possui prazo.aceitar
→ pode aceitar
```

---

# 217. Exemplo — executor

```text
Se usuário é executor
e possui tarefa.iniciar
→ pode iniciar
```

---

# 218. Exemplo — gestor

```text
Se usuário gerencia o setor
e possui fila.reordenar
→ pode reordenar
```

---

# 219. Relação não deve conceder ação sozinha

Ser executor não significa automaticamente:

```text
pode excluir tarefa
```

A ação continua necessária.

---

# 220. Separação entre vínculo e autorização

Esse é um princípio importante:

```text
Vínculo
=
quem está relacionado ao objeto

Autorização
=
o que pode fazer
```

---

# 221. Exemplos de vínculos

- dono da atividade;
- executor da tarefa;
- membro do setor;
- gestor do setor;
- criador;
- responsável por aprovação.

---

# 222. Exemplos de ações

- visualizar;
- editar;
- concluir;
- reordenar;
- aprovar;
- devolver;
- atribuir.

---

# 223. Matriz conceitual

```text
USUÁRIO
↓
possui vínculos
↓
possui perfis
↓
perfis concedem ações
↓
ações são válidas em escopos
↓
regras de negócio validam o estado
↓
ação permitida ou negada
```

---

# 224. Cadastro de ações deve ser central

A LPS deve possuir catálogo de ações conhecido pelo sistema.

A organização configura quais perfis recebem cada uma.

---

# 225. Empresa não cria qualquer ação arbitrária no D0

Ações correspondem a capacidades reais do produto.

Exemplo:

A empresa pode escolher:

```text
quem possui tarefa.devolver
```

Mas não inventar:

```text
tarefa.teletransportar
```

se essa função não existe.

---

# 226. Grupos podem ser organizados pela LPS

A LPS define os grupos principais conforme suas funcionalidades.

A organização configura acesso.

---

# 227. Perfil é configurável pela organização

Exemplo:

```text
Perfil:
Orçamentista Sênior
```

Ações:

```text
atividade.visualizar
atividade.criar
tarefa.criar
tarefa.atribuir
fila.visualizar_completa
```

---

# 228. Setores são configuráveis pela organização

Exemplo:

```text
Orçamentos
```

em vez de:

```text
Comercial
```

Sem necessidade de alteração técnica.

---

# 229. Configuração de visibilidade

A empresa precisa poder decidir quem visualiza:

- atividades;
- tarefas;
- filas;
- métricas;
- auditoria;
- conversas.

---

# 230. Conversa segue escopo do trabalho

Se usuário não pode visualizar a atividade, normalmente não deve visualizar sua conversa.

A regra detalhada pertence ao documento 06.

---

# 231. Anexos seguem autorização do objeto

Se anexo pertence à tarefa, acesso deve respeitar a tarefa.

Não criar acesso paralelo inseguro.

---

# 232. Exportação é uma ação

Pode existir:

```text
atividade.exportar
```

```text
auditoria.exportar
```

```text
metricas.exportar
```

Exportar pode ser mais sensível que visualizar.

---

# 233. Download de anexos

Pode existir ação específica se necessário.

Não precisa ser detalhado no D0.

---

# 234. API também respeita autorização

Se futuramente existir integração:

```text
API
```

ela deve respeitar os mesmos conceitos.

Não criar uma “porta lateral” sem controle.

---

# 235. Contas técnicas

Integrações podem usar usuários técnicos ou credenciais próprias.

O escopo deve ser limitado.

Não é prioridade funcional do D0.

---

# 236. Acesso ao banco não deve depender do front-end

Princípio de segurança:

> Nenhum dado sensível deve ficar protegido apenas porque uma tela não mostra um botão.

---

# 237. Isolamento organizacional é obrigatório

Mesmo um erro de permissão interna não deve permitir atravessar organização.

Esse é o limite de segurança mais importante.

---

# 238. Empresa como segundo nível de isolamento

Dentro da organização, a empresa pode limitar ainda mais.

---

# 239. Setor como nível operacional

Dentro da empresa, setor organiza trabalho e acesso operacional.

---

# 240. Obra e centro de custo como escopos adicionais

Quando relevantes, restringem atividades e tarefas.

---

# 241. Escopo deve acompanhar os dados

Se atividade pertence à:

```text
Empresa A
Obra X
Setor Comercial
```

a autorização precisa conseguir avaliar esses atributos.

---

# 242. Atividade sem obra

Nem toda atividade terá obra.

Exemplo:

```text
Picotar folhas
```

Pode pertencer apenas à:

```text
Empresa
Setor
```

A autorização não deve exigir obra.

---

# 243. Atividade sem centro de custo

Também permitido.

Escopos opcionais não podem quebrar acesso.

---

# 244. Setor obrigatório na tarefa, não necessariamente na atividade inteira

Como definido no fluxo, tarefas possuem setores responsáveis.

A atividade pode envolver vários setores.

Por isso, autorização precisa considerar o objeto que está sendo acessado.

---

# 245. Visualização da atividade com tarefas de vários setores

Esse é um caso importante.

Exemplo:

Atividade:

```text
Material disponível na obra
```

Tarefas:

```text
Engenharia
Compras
Financeiro
Almoxarifado
```

O dono precisa acompanhar a atividade inteira mesmo que não pertença a todos os setores.

---

# 246. Dono precisa de visibilidade transversal da própria atividade

A LPS deve permitir que o dono visualize informações necessárias da atividade que possui.

Isso não significa acesso geral ao setor Financeiro.

Exemplo:

```text
Paulo
dono da atividade
```

Pode enxergar:

```text
tarefa financeira daquela atividade
```

sem enxergar:

```text
todas as tarefas do Financeiro
```

---

# 247. Esse é um escopo relacional

Conceitualmente:

```text
atividade.visualizar
escopo = atividades das quais sou dono
```

---

# 248. Executor precisa de contexto suficiente

Um executor precisa acessar a tarefa e o contexto necessário da atividade.

Não necessariamente todos os dados confidenciais.

---

# 249. Visibilidade parcial

Futuramente, alguns campos podem possuir restrição maior.

Exemplo:

```text
valor financeiro
```

Não é prioridade do D0.

No início, a autorização pode ser por objeto/ação.

---

# 250. Permissão por campo

Evitar no D0.

É poderosa, mas aumenta muito a complexidade.

Só adotar quando houver necessidade real.

---

# 251. Permissão por registro

Já é necessária por causa dos escopos.

Exemplo:

```text
atividade A permitida
atividade B negada
```

conforme setor/obra/dono.

---

# 252. Permissão por ação

Também necessária.

Exemplo:

```text
ver permitido
editar negado
```

---

# 253. Permissão por campo fica para evolução

Exemplo:

```text
ver atividade
mas ocultar valor
```

Pode vir depois.

---

# 254. Perfis não devem ser excessivamente genéricos

Perfil:

```text
Usuário
```

com dezenas de exceções provavelmente não ajuda.

Melhor criar perfis alinhados a responsabilidades.

---

# 255. Perfis não devem ser excessivamente específicos

Evitar:

```text
Orçamentista Paulo Obra X
```

como perfil.

Use escopo para especificidade.

---

# 256. Boa separação

```text
Perfil:
Orçamentista
```

```text
Escopo:
Comercial + Obras X/Y
```

---

# 257. Onboarding de usuário

Fluxo conceitual:

```text
Criar usuário
↓
Vincular à organização
↓
Selecionar empresas
↓
Selecionar setores
↓
Atribuir perfis
↓
Definir escopos/exceções
↓
Ativar
```

---

# 258. Onboarding simples

A tela deve facilitar escolhas.

Não exigir que administrador entenda banco de dados.

---

# 259. Copiar configuração de usuário

Pode acelerar:

```text
Criar Luan baseado em Ryan
```

Depois revisar diferenças.

---

# 260. Segurança na cópia

A interface deve mostrar claramente o que será copiado:

- setores;
- perfis;
- escopos;
- permissões diretas.

---

# 261. Desligamento

Fluxo:

```text
Inativar usuário
↓
encerrar acesso
↓
preservar histórico
↓
tratar tarefas abertas
```

---

# 262. Tarefas abertas de usuário inativado

A LPS precisa identificar:

```text
tarefas atribuídas ao usuário inativado
```

e permitir reatribuição.

Não deixar tarefas órfãs sem aviso.

---

# 263. Dono inativado

Se dono de atividade for inativado:

```text
atividade precisa de novo dono
```

A LPS deve alertar administrador/gestor.

---

# 264. Setor inativado com tarefas abertas

Também precisa tratamento.

Não permitir simplesmente inativar e esconder trabalho ativo.

---

# 265. Perfil inativado

Usuários vinculados podem perder permissões.

A LPS deve avisar impacto antes de concluir.

---

# 266. Configuração segura

Ações que podem causar grande impacto devem mostrar consequências.

Exemplo:

```text
Inativar perfil usado por 42 usuários.
```

---

# 267. Auditoria da configuração

Toda alteração administrativa relevante precisa ir para auditoria.

---

# 268. Ambientes de configuração

A área administrativa pode ser separada da operação diária.

Isso evita poluir experiência do colaborador.

---

# 269. Menu de apoio/cadastros

Pode concentrar:

```text
Empresas
Usuários
Setores
Perfis
Ações
Autorizações
```

A interface final será definida depois.

---

# 270. O usuário só vê configurações autorizadas

Exemplo:

```text
Paulo
não possui perfil.visualizar
```

Então não precisa ver menu de Perfis.

---

# 271. Ocultar menu melhora UX

Mas a segurança continua validada no backend e banco.

---

# 272. Princípio de configuração progressiva

A organização começa simples.

Depois adiciona:

- novos perfis;
- novos setores;
- novos escopos;
- regras mais específicas.

Não precisa configurar tudo no primeiro dia.

---

# 273. Configuração precisa ser compreensível

Evitar regras que só desenvolvedor entende.

Administrador da empresa deve conseguir responder:

> Por que Paulo vê Administrativo?

---

# 274. Resposta esperada

```text
Porque Paulo possui o perfil "Visualizador Administrativo" com escopo no setor Administrativo.
```

---

# 275. Evitar regras implícitas demais

Exemplo ruim:

```text
Paulo vê porque é gerente nível 4 e a configuração herdada do grupo 9 somada ao setor 3...
```

A arquitetura pode ser poderosa, mas precisa ser explicável.

---

# 276. Herança controlada

Perfis podem agregar ações.

Escopos podem ser reutilizados.

Mas evitar cadeias profundas de herança no D0.

---

# 277. Não usar cargo como autorização automática

Cargo pode informar:

```text
Engenheiro
```

Mas não decide sozinho o acesso.

---

# 278. Não usar salário, senioridade ou título para liberar ação

Autorização deve ser explícita.

---

# 279. Funções temporárias

Uma pessoa pode exercer papel adicional.

Exemplo:

```text
Substituto do gestor
```

Futuramente, perfil temporário pode resolver.

---

# 280. Permissões e notificações

Possuir acesso a uma atividade não significa necessariamente receber notificações dela.

Notificação possui configuração própria.

Exemplo:

```text
Paulo pode visualizar Financeiro
```

mas:

```text
não quer receber todas as notificações financeiras
```

---

# 281. Acesso e responsabilidade são diferentes

Visualizar algo não torna o usuário responsável.

---

# 282. Responsabilidade e notificação também são diferentes

Dono deve receber eventos essenciais.

Outros usuários podem optar conforme configuração.

---

# 283. Acesso e fila

Visualizar uma tarefa não significa poder mudar sua posição.

---

# 284. Acesso e prazo

Visualizar prazo não significa poder alterá-lo.

---

# 285. Acesso e auditoria

Visualizar atividade não significa necessariamente visualizar todo histórico de segurança.

---

# 286. Separação das ações evita excesso de poder

Esse é um dos principais benefícios do modelo.

---

# 287. Exemplo de perfil — Colaborador

Possível configuração:

```text
atividade.visualizar
atividade.criar
tarefa.visualizar
tarefa.assumir
tarefa.iniciar
tarefa.pausar
tarefa.retomar
tarefa.concluir
```

Sem:

```text
fila.reordenar
usuario.editar
autorizacao.editar
```

---

# 288. Exemplo de perfil — Gestor

Além das anteriores:

```text
tarefa.atribuir
fila.visualizar_completa
fila.reordenar
prazo.propor
metricas.visualizar_setor
escalonamento.resolver
```

---

# 289. Exemplo de perfil — Administrador

Pode incluir:

```text
usuario.criar
usuario.editar
setor.criar
setor.editar
perfil.criar
perfil.editar
autorizacao.editar
```

---

# 290. Exemplo de perfil — Diretoria

Pode incluir:

```text
atividade.visualizar
fila.visualizar_completa
metricas.visualizar_organizacao
auditoria.visualizar
```

Sem necessidade de operar tarefas.

---

# 291. Exemplos são referência, não padrão obrigatório

Cada organização configura conforme necessidade.

---

# 292. Grupo de ações pode ter dezenas de ações

Isso é aceitável.

O importante é organização.

---

# 293. Não expor ações técnicas desnecessárias ao cliente

Ações internas do sistema podem permanecer técnicas.

A tela administrativa deve mostrar apenas o necessário.

---

# 294. Nomenclatura consistente

Preferir padrão técnico:

```text
recurso.acao
```

Exemplos:

```text
atividade.visualizar
tarefa.devolver
fila.reordenar
setor.criar
```

---

# 295. Nome amigável separado

Exemplo:

```text
Código:
fila.reordenar

Nome:
Reordenar fila
```

---

# 296. Descrição

```text
Permite alterar a ordem das tarefas na fila dos setores autorizados.
```

---

# 297. Grupos organizacionais

Exemplo:

```text
Atividades
Tarefas
Filas
Prazos
Cadastros
Segurança
Auditoria
Métricas
```

---

# 298. Ações futuras

Quando surgirem módulos:

```text
Aprovações
```

ou:

```text
Integrações
```

novos grupos podem ser adicionados.

---

# 299. Estrutura não precisa mudar para crescer

Esse é o objetivo do modelo dinâmico.

---

# 300. Controle de mudanças em segurança

Alterações em:

- perfil;
- ação;
- escopo;
- usuário;
- setor;

devem gerar evento de auditoria.

---

# 301. Data efetiva

Futuramente, alteração pode ser programada para começar em data específica.

Não é prioridade do D0.

---

# 302. Histórico de autorização

A LPS deve poder responder:

> Paulo tinha acesso ao Financeiro em 10/09?

Isso pode ser importante em auditoria.

---

# 303. Não apenas estado atual

Assim como atividades, autorizações também possuem história.

---

# 304. Alterações de autorização não reescrevem passado

Se hoje o acesso foi removido, isso não significa que nunca existiu.

---

# 305. Exportações de segurança

Futuramente:

```text
exportar matriz de permissões
```

Pode ser útil para auditoria.

Não é prioridade do D0.

---

# 306. Usuários órfãos

Evitar usuário ativo sem:

- organização;
- empresa quando necessária;
- perfil;
- configuração mínima.

---

# 307. Perfis sem ações

Podem existir durante configuração, mas não oferecem acesso.

---

# 308. Setor sem usuários

Pode existir.

Exemplo:

Setor criado antes de equipe ser cadastrada.

---

# 309. Setor sem gestor

Pode existir tecnicamente.

Mas a LPS pode alertar se regras de escalonamento dependem de gestor.

---

# 310. Escalonamento depende da estrutura configurada

Se a empresa configurar:

```text
escalar para gestor do setor
```

precisa existir alguém definido como gestor.

---

# 311. Validação de configuração

A LPS deve detectar inconsistências.

Exemplo:

```text
Regra de escalonamento aponta para gestor
mas setor não possui gestor.
```

---

# 312. Configuração incompleta não deve falhar silenciosamente

Mostrar alerta administrativo.

---

# 313. Permissão para configurar notificações

Pode existir:

```text
notificacao.configurar_proprias
```

e:

```text
notificacao.configurar_organizacao
```

---

# 314. Permissão para configurar escalonamento

Ação:

```text
escalonamento.configurar
```

---

# 315. Permissão para configurar fluxos

Ação:

```text
fluxo.configurar
```

---

# 316. Permissão para configurar tipos

Ações específicas conforme cadastro.

---

# 317. Configurações pessoais x corporativas

Usuário pode ajustar:

```text
preferências de notificação
```

sem poder alterar:

```text
regra corporativa de segurança
```

---

# 318. Regras corporativas prevalecem quando obrigatórias

Exemplo:

```text
Dono sempre recebe notificação de conclusão.
```

O usuário não pode desligar se a empresa definiu como obrigatória.

---

# 319. Segurança precisa ser testável

Administrador deve poder testar:

> O que Ryan consegue fazer?

Futuramente, uma função de simulação pode ser útil.

Não é prioridade do D0.

---

# 320. Modo “ver como usuário”

Pode ser útil futuramente para suporte.

Precisa de forte auditoria.

---

# 321. Princípio da rastreabilidade

Qualquer concessão sensível precisa poder ser atribuída a uma origem.

---

# 322. Princípio da simplicidade

O modelo interno pode ser robusto.

A configuração precisa ser compreensível.

---

# 323. Princípio do mínimo necessário

Não criar:

- hierarquia infinita de perfis;
- herança complexa;
- regras condicionais indecifráveis;
- permissões por campo no D0.

---

# 324. Princípio da expansão futura

A estrutura precisa permitir crescer para:

- novos módulos;
- novos escopos;
- novos tipos de usuário;
- integrações;
- clientes externos.

Sem reescrever a base.

---

# 325. Relação com atividades

Autorização controla:

- criação;
- visualização;
- edição;
- dono;
- conclusão;
- cancelamento;
- reabertura.

---

# 326. Relação com tarefas

Controla:

- criação;
- atribuição;
- assumir;
- iniciar;
- devolver;
- concluir.

---

# 327. Relação com filas

Controla:

- visualizar posição própria;
- visualizar fila completa;
- reordenar.

---

# 328. Relação com prazos

Controla:

- visualizar;
- propor;
- aceitar;
- recusar;
- alterar.

---

# 329. Relação com auditoria

Controla:

- consultar;
- exportar;
- corrigir dados quando permitido.

---

# 330. Relação com comunicação

Controla acesso conforme atividade/tarefa.

---

# 331. Relação com métricas

Controla:

- próprio usuário;
- setor;
- empresa;
- organização.

---

# 332. Relação com inteligência futura

Sugestões da LPS também devem respeitar autorização.

Exemplo:

Usuário sem acesso ao Financeiro não deve receber insight contendo dados financeiros internos.

---

# 333. Segurança de IA

A IA não pode “vazar” informação de outro escopo apenas porque analisou dados globais.

Esse princípio deve ser preservado desde o início.

---

# 334. Uso entre organizações

Qualquer aprendizado agregado entre empresas deve ser anonimizado e autorizado conforme política futura.

Não altera autorização operacional.

---

# 335. D0 — Estrutura mínima de segurança

O D0 precisa suportar:

- organização;
- empresa;
- usuário;
- setor;
- usuário em vários setores;
- perfil;
- grupo de ações;
- ação;
- perfil com ações;
- usuário com perfil;
- escopo;
- autorização por escopo;
- inativação;
- auditoria de alterações.

---

# 336. D0 — Ações mínimas recomendadas

## Usuários

```text
usuario.visualizar
usuario.criar
usuario.editar
usuario.inativar
usuario.atribuir_setor
usuario.atribuir_perfil
```

## Setores

```text
setor.visualizar
setor.criar
setor.editar
setor.inativar
```

## Atividades

```text
atividade.visualizar
atividade.criar
atividade.editar
atividade.alterar_dono
atividade.concluir
atividade.cancelar
atividade.reabrir
```

## Tarefas

```text
tarefa.visualizar
tarefa.criar
tarefa.editar
tarefa.assumir
tarefa.atribuir
tarefa.iniciar
tarefa.pausar
tarefa.retomar
tarefa.devolver
tarefa.concluir
tarefa.cancelar
```

## Filas

```text
fila.visualizar
fila.visualizar_completa
fila.reordenar
```

## Prazos

```text
prazo.visualizar
prazo.propor
prazo.aceitar
prazo.recusar
prazo.alterar
```

## Segurança

```text
perfil.visualizar
perfil.criar
perfil.editar
perfil.inativar
autorizacao.visualizar
autorizacao.editar
autorizacao.copiar
```

## Auditoria

```text
auditoria.visualizar
```

---

# 337. D0 — Escopos mínimos recomendados

A arquitetura precisa considerar pelo menos:

```text
organização
```

```text
empresa
```

```text
setor
```

```text
obra
```

```text
centro de custo
```

```text
atividades próprias
```

```text
tarefas atribuídas
```

Nem todos precisam aparecer na primeira tela de configuração.

---

# 338. O que pode ficar para depois do D0

- permissão por campo;
- expiração automática;
- aprovação de concessão;
- simulação avançada;
- usuário externo;
- acesso temporário;
- herança complexa;
- negação explícita sofisticada;
- políticas condicionais avançadas;
- relatórios completos de segurança;
- segregação de funções automatizada.

---

# 339. Segregação de funções

Futuramente, a LPS pode detectar situações como:

```text
mesma pessoa cria e aprova
```

se a empresa considerar inadequado.

Não é prioridade do D0.

---

# 340. Matriz de responsabilidade

Autorização pode apoiar conceitos futuros como:

```text
quem executa
quem aprova
quem acompanha
quem visualiza
```

Mas a LPS não precisa implementar uma matriz complexa no início.

---

# 341. Perguntas que a configuração precisa responder

- Quem pode criar usuário?
- Quem pode criar setor?
- Quem pode ver Comercial?
- Quem pode ver Financeiro?
- Quem pode alterar fila?
- Quem pode atribuir responsável?
- Quem pode aceitar prazo?
- Quem pode escalar?
- Quem pode concluir?
- Quem pode visualizar métricas?
- Quem pode alterar permissões?

---

# 342. Perguntas que o sistema precisa responder automaticamente

Para uma ação:

> Usuário X pode executar ação Y sobre objeto Z?

A resposta precisa ser:

```text
sim
```

ou:

```text
não
```

com base em regras previsíveis.

---

# 343. Fórmula conceitual de autorização

```text
1. Usuário está ativo?
2. Usuário pertence à organização do objeto?
3. Usuário possui a ação?
4. O objeto está dentro do escopo permitido?
5. A regra de negócio permite a ação neste estado?
```

Se todas as condições necessárias forem atendidas:

```text
permitir
```

Caso contrário:

```text
negar
```

---

# 344. Exemplo de avaliação

Usuário:

```text
Paulo
```

Ação:

```text
fila.reordenar
```

Objeto:

```text
Fila Comercial
```

Verificação:

```text
Usuário ativo? ✅
Mesma organização? ✅
Possui ação? ✅
Escopo inclui Comercial? ✅
Regra de negócio permite? ✅
```

Resultado:

```text
PERMITIDO
```

---

# 345. Exemplo negado por escopo

Mesmo usuário:

```text
fila.reordenar
```

Objeto:

```text
Fila Financeiro
```

Verificação:

```text
Usuário ativo? ✅
Mesma organização? ✅
Possui ação? ✅
Escopo inclui Financeiro? ❌
```

Resultado:

```text
NEGADO
```

---

# 346. Exemplo permitido por atividade própria

Paulo não possui acesso geral ao Financeiro.

Mas é dono de atividade que possui uma tarefa no Financeiro.

Pode existir regra:

```text
atividade.visualizar
escopo = atividades próprias
```

Resultado:

```text
visualiza aquela atividade
```

sem:

```text
visualizar toda a fila financeira
```

---

# 347. Essa diferença é essencial

A LPS precisa ser transparente para o dono sem quebrar privacidade de outros setores.

---

# 348. Acesso a detalhes da tarefa própria

O dono deve visualizar informações suficientes para monitoramento:

- setor;
- status;
- posição;
- prazo;
- conclusão;
- devolução.

Não necessariamente informações confidenciais internas além do necessário.

---

# 349. Escopo de conversa

Se o dono tem acesso à tarefa, pode participar da conversa relacionada conforme regra.

---

# 350. Ações de gestor sobre atividades alheias

Gestor pode possuir:

```text
atividade.visualizar
```

e:

```text
tarefa.atribuir
```

em seu setor.

Isso permite gestão sem ser dono.

---

# 351. Papel da autorização na transparência

Transparência é controlada, não irrestrita.

---

# 352. Papel da autorização na simplicidade

Usuário comum deve ver apenas ações úteis para ele.

Menos botões, menos confusão.

---

# 353. Papel da autorização na escalabilidade

Sem autorização dinâmica, cada novo cliente gera mudança de código.

Com autorização dinâmica:

```text
configura
```

em vez de:

```text
customiza
```

---

# 354. Papel da autorização no produto pago

Uma LPS madura pode oferecer:

- modelos de perfis;
- melhores práticas;
- análises de risco de acesso;
- recomendações de configuração.

Mas isso vem depois da base funcional.

---

# 355. Não copiar 90 grupos apenas porque outro sistema possui

A quantidade deve crescer conforme a LPS cresce.

O diferencial está no mecanismo, não no número.

---

# 356. Ações precisam nascer junto com funcionalidades reais

Se a LPS ainda não possui determinado recurso, não precisa criar ações fictícias para ele.

---

# 357. Controle de complexidade

Toda nova ação precisa responder:

> Existe realmente uma necessidade de separar esta permissão?

Se não:

pode pertencer a outra ação existente.

---

# 358. Exemplo de separação necessária

```text
fila.visualizar
```

e:

```text
fila.reordenar
```

claramente precisam ser diferentes.

---

# 359. Exemplo potencialmente desnecessário no início

```text
fila.reordenar_para_cima
fila.reordenar_para_baixo
```

Não agrega valor.

---

# 360. Granularidade adequada

Ação deve representar uma capacidade de negócio significativa.

---

# 361. Configuração herdada por organização

Perfis pertencem à organização.

Uma organização não utiliza diretamente perfil de outra.

---

# 362. Templates globais

A LPS pode oferecer modelo global copiável.

Mas, ao copiar, a organização passa a administrar sua configuração.

---

# 363. Atualização de template global

Não deve alterar silenciosamente perfis de clientes existentes.

---

# 364. Segurança precisa ser previsível

Mudanças do produto não podem conceder acesso novo automaticamente sem análise.

Exemplo:

Nova ação:

```text
metricas.exportar
```

Não deve ser concedida a todos apenas porque já possuíam:

```text
metricas.visualizar
```

---

# 365. Novas ações começam negadas por padrão

Isso preserva segurança.

---

# 366. Administrador decide concessão

Ou um perfil padrão pode ser atualizado conscientemente.

---

# 367. Auditoria das novas concessões

Sempre registrar.

---

# 368. Migração de autorização

Quando funcionalidades mudarem, a LPS precisa tratar migração de ações cuidadosamente.

Detalhamento técnico futuro.

---

# 369. Testes de autorização

Cada ação importante deve possuir testes.

Exemplo:

```text
usuário sem fila.reordenar
não consegue reordenar pela API
```

Pertence à implementação técnica, mas é princípio obrigatório.

---

# 370. Segurança não pode depender de boa intenção

Mesmo que usuários internos sejam confiáveis, erros acontecem.

A autorização protege contra:

- engano;
- excesso de acesso;
- uso indevido;
- falha de interface.

---

# 371. Auditoria não substitui prevenção

Registrar que alguém fez algo indevido é útil.

Melhor ainda é impedir quando não autorizado.

---

# 372. Prevenção + rastreabilidade

A LPS precisa dos dois.

---

# 373. Resumo conceitual

```text
ORGANIZAÇÃO
↓
EMPRESA
↓
SETOR
↓
USUÁRIO
↓
PERFIL
↓
AÇÃO
↓
ESCOPO
↓
AUTORIZAÇÃO
↓
AUDITORIA
```

Essa representação é simplificada.

Na prática, usuários podem participar de vários setores e possuir vários perfis.

---

# 374. Outra visão

```text
QUEM?
Usuário

PODE FAZER O QUÊ?
Ação

ONDE?
Escopo

POR QUE PODE?
Perfil ou concessão direta
```

---

# 375. Regra de ouro do usuário

> **Usuário pertence a uma organização, mas seu acesso interno depende das autorizações configuradas.**

---

# 376. Regra de ouro do setor

> **Setor representa estrutura operacional e é configurável; não deve ser codificado de forma fixa na LPS.**

---

# 377. Regra de ouro do perfil

> **Perfil agrupa capacidades reutilizáveis, mas não deve ser confundido com cargo ou setor.**

---

# 378. Regra de ouro da ação

> **Ação representa uma capacidade real do produto e deve ser independente da tela onde aparece.**

---

# 379. Regra de ouro do escopo

> **Permissão sem escopo é ampla demais; escopo define onde a ação é válida.**

---

# 380. Regra de ouro da autorização

> **Se não existe concessão válida para a ação e o escopo, o sistema deve negar.**

---

# 381. Regra de ouro da segurança

> **Esconder botão melhora a experiência, mas a proteção real precisa existir também na aplicação e no banco.**

---

# 382. Decisões consolidadas neste documento

## Organização

- usuário pertence a uma única organização;
- dados são isolados entre organizações;
- organização pode conter várias empresas.

## Empresa

- usuário pode ter acesso a uma ou várias empresas internas;
- empresa é escopo de autorização;
- uma empresa pode também assumir outros papéis, como cliente, em outro contexto.

## Usuário

- pode participar de vários setores;
- pode possuir vários perfis;
- pode receber exceções individuais;
- deve ser inativado, não apagado, quando possuir histórico.

## Setor

- é configurável;
- não é fixo no código;
- pode possuir vários usuários;
- usuário pode pertencer a vários setores;
- participar do setor não concede automaticamente todas as permissões;
- cadastro depende de autorização.

## Perfil

- é configurável por organização;
- agrupa ações;
- pode ser atribuído a vários usuários;
- usuário pode possuir vários perfis;
- perfil não é cargo e não é setor.

## Grupo de ações

- organiza ações;
- não concede acesso sozinho;
- pode crescer conforme o produto cresce.

## Ação

- representa capacidade de negócio;
- deve ser granular o suficiente para segurança;
- não deve depender da tela;
- novas ações começam negadas por padrão.

## Autorização

- resulta da combinação de usuário/perfil, ação e escopo;
- é negada por padrão quando não existe concessão;
- pode existir concessão direta para exceções;
- precisa ser auditada.

## Escopo

- pode considerar organização;
- empresa;
- setor;
- obra;
- centro de custo;
- atividades próprias;
- tarefas atribuídas;
- relações como dono ou executor.

## Filas

- visualizar posição própria é diferente de visualizar fila completa;
- reordenar exige ação específica;
- gestor e pessoas autorizadas podem reordenar.

## Responsáveis

- assumir tarefa e atribuir responsável são ações diferentes;
- participação em setor não significa automaticamente poder atribuir.

## Cadastros

- criação ocorre em telas próprias no D0;
- quem cadastra depende de ação;
- não haverá criação automática de setor dentro do formulário de atividade no D0.

## Segurança

- interface não é barreira suficiente;
- aplicação e banco também precisam validar;
- princípio do menor privilégio;
- negação por padrão;
- histórico de alterações deve ser mantido.

---

# 383. Decisões ainda pendentes

Precisam ser detalhadas posteriormente:

- estrutura técnica exata dos escopos;
- se perfil guarda escopo ou apenas ações;
- forma de combinar perfil com escopos de usuário;
- necessidade de negação explícita;
- permissões por campo;
- acessos temporários;
- usuários externos;
- política de aprovação de concessões sensíveis;
- relatórios de segurança;
- simulação de acesso;
- detalhes da implementação com RLS;
- comportamento de múltiplas empresas por usuário;
- política de senha/autenticação;
- autenticação multifator;
- sessão e timeout;
- integração com diretórios corporativos.

---

# 384. Relação com os demais documentos

## `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`

Define os objetos que recebem controle de acesso.

## `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`

Define ações como:

- visualizar fila;
- reordenar;
- propor prazo;
- escalar.

Este documento define quem pode executá-las.

## `04_AUDITORIA_TEMPO_E_METRICAS.md`

Recebe eventos de:

- concessão;
- remoção;
- alteração de perfil;
- mudança de setor;
- ações sensíveis.

## `06_NOTIFICACOES_E_COMUNICACAO.md`

Usará autorizações para decidir:

- quem pode participar da conversa;
- quem pode configurar notificações;
- quem recebe eventos.

## `07_INTELIGENCIA_E_RETROALIMENTACAO.md`

A inteligência deve respeitar os mesmos escopos de acesso.

## `08_BANCO_DE_DADOS.md`

Traduzirá este documento em estruturas como:

- organizações;
- usuários;
- setores;
- usuário-setores;
- perfis;
- grupos de ações;
- ações;
- perfil-ações;
- usuário-perfis;
- escopos;
- autorizações;
- auditoria.

---

# 385. Estrutura técnica conceitual sugerida

Sem fechar nomes definitivos de tabelas, o banco provavelmente precisará representar:

```text
core.organizacoes
core.usuarios
core.setores
core.usuario_setores
```

```text
acessos.grupos_acoes
acessos.acoes
acessos.perfis
acessos.perfil_acoes
acessos.usuario_perfis
acessos.escopos
acessos.autorizacoes
```

Possivelmente:

```text
acessos.usuario_autorizacoes
```

para exceções diretas.

A modelagem final será feita no documento 08.

---

# 386. Não fixar nomes técnicos prematuramente

O conceito é mais importante neste momento que o nome exato da tabela.

Primeiro:

```text
comportamento correto
```

Depois:

```text
modelagem técnica
```

---

# 387. Exemplo completo — Paulo

```text
Organização:
Biasi

Empresas:
Biasi Engenharia

Setores:
Comercial
Administrativo

Setor principal:
Comercial
```

Perfis:

```text
Gestor Comercial
Visualizador Administrativo
```

Autorizações resultantes:

```text
Comercial:
visualizar ✅
criar ✅
atribuir ✅
reordenar fila ✅

Administrativo:
visualizar ✅
editar ❌
reordenar fila ❌
```

---

# 388. Exemplo completo — Ryan

```text
Setor:
Comercial

Perfil:
Colaborador Comercial
```

Pode:

```text
visualizar tarefas do Comercial
assumir tarefas
iniciar
pausar
retomar
concluir
```

Não pode:

```text
editar segurança
criar setores
reordenar fila
```

salvo autorização adicional.

---

# 389. Exemplo completo — Igor

```text
Setor:
Almoxarifado

Perfil:
Gestor de Almoxarifado
```

Pode:

```text
visualizar fila completa
reordenar
atribuir tarefas
propor prazo
visualizar métricas do setor
```

---

# 390. Exemplo completo — solicitante

Paulo solicita algo ao Almoxarifado.

Mesmo sem acesso ao setor inteiro, pode visualizar:

```text
sua atividade
sua tarefa
posição 4 de 17
prazo comprometido
status
```

Não vê:

```text
detalhes das outras 16 tarefas
```

---

# 391. Exemplo completo — diretoria

```text
Perfil:
Diretoria
```

Escopo:

```text
Organização inteira
```

Pode:

```text
visualizar atividades
visualizar filas
visualizar métricas
visualizar escalonamentos
```

Sem necessariamente operar tarefas.

---

# 392. Exemplo completo — administrador

```text
Perfil:
Administrador da Organização
```

Pode:

```text
criar usuário
editar usuário
criar setor
editar setor
criar perfil
editar perfil
atribuir perfil
editar autorizações
```

Ainda não pode acessar outra organização.

---

# 393. Exemplo de regra configurável de assumir tarefa

Empresa A:

```text
Qualquer membro autorizado do setor
pode assumir.
```

Empresa B:

```text
Somente gestor pode atribuir.
```

A LPS não muda.

A configuração muda.

---

# 394. Exemplo de regra configurável de visualização

Empresa A:

```text
Membros do setor veem toda a fila.
```

Empresa B:

```text
Membros veem apenas tarefas atribuídas.
Gestor vê fila completa.
```

---

# 395. Exemplo de regra configurável de cadastro

Empresa A:

```text
Gestores podem criar setores.
```

Empresa B:

```text
Somente administradores.
```

---

# 396. Exemplo de regra configurável de prazo

Empresa A:

```text
Executor pode propor novo prazo.
```

Empresa B:

```text
Somente gestor do setor pode propor.
```

---

# 397. Exemplo de regra configurável de escalonamento

Empresa A:

```text
Escalonar para gestor do setor.
```

Empresa B:

```text
Escalonar para gestor + diretor.
```

---

# 398. O diferencial dinâmico

O diferencial não está em permitir que o cliente altere qualquer coisa.

Está em permitir que ele configure:

```text
estrutura
+
papéis
+
ações
+
escopos
```

sem alterar o produto.

---

# 399. O que deve permanecer fixo

Mesmo com toda flexibilidade:

- usuário pertence a uma organização;
- histórico não é apagado;
- autorização precisa ser validada;
- ação precisa existir no produto;
- acesso entre organizações é proibido;
- segurança não depende apenas da interface.

---

# 400. O que deve permanecer configurável

- setores;
- usuários;
- perfis;
- vínculos;
- ações concedidas;
- escopos;
- responsáveis autorizados;
- regras de fila;
- regras de prazo;
- regras de escalonamento.

---

# 401. Critério para nova permissão

Antes de criar uma ação, perguntar:

1. Há risco real em conceder esta capacidade junto com outra?
2. Empresas podem querer separar quem faz isso?
3. A ação representa um comportamento de negócio claro?
4. O escopo pode variar?
5. Precisa aparecer em auditoria?

Se sim, provavelmente merece ação própria.

---

# 402. Critério para novo escopo

Perguntar:

> Empresas precisam limitar acesso por esta dimensão?

Se sim, pode fazer sentido.

Exemplo:

```text
obra
```

é relevante.

Não criar escopos sem necessidade prática.

---

# 403. Critério para novo perfil

Perguntar:

> Existe um conjunto recorrente de ações que várias pessoas compartilham?

Se sim:

```text
criar perfil
```

---

# 404. Critério para exceção individual

Perguntar:

> Este caso é realmente excepcional?

Se sim:

```text
concessão direta
```

Se muitas pessoas precisam:

```text
novo perfil
```

---

# 405. Critério para vínculo de setor

Perguntar:

> A pessoa realmente atua ou participa operacionalmente deste setor?

Se sim:

```text
vincular setor
```

Se apenas precisa visualizar:

```text
autorização de escopo
```

---

# 406. Isso evita distorção organizacional

Sem essa separação, poderíamos colocar Paulo como membro do Administrativo apenas porque ele precisa enxergar algumas atividades.

Isso polui a estrutura.

Melhor:

```text
membro do Comercial
+
acesso de visualização ao Administrativo
```

---

# 407. Setor representa estrutura real

Permissão representa acesso.

Essa diferença deve ser preservada.

---

# 408. Auditoria da estrutura organizacional

Alterações como:

```text
usuário entrou no setor
```

```text
usuário saiu do setor
```

também precisam ser registradas.

---

# 409. Histórico de gestor

Se uma pessoa deixa de gerenciar setor, o histórico deve preservar quem gerenciava em cada período quando necessário.

---

# 410. Escalonamentos históricos dependem disso

Ao analisar evento antigo, deve ser possível saber:

```text
quem era o gestor naquele momento
```

quando relevante.

---

# 411. Dados históricos não devem depender apenas da estrutura atual

Isso vale para:

- dono;
- gestor;
- setor;
- perfil;
- autorização.

---

# 412. Snapshot de contexto

Alguns eventos podem precisar registrar contexto suficiente para não mudar de significado quando cadastros forem alterados.

Detalhamento técnico futuro.

---

# 413. Autorização e desempenho

A permissão não deve ser usada para esconder métricas que o próprio usuário precisa para trabalhar.

Mas deve respeitar confidencialidade.

---

# 414. Transparência gerencial progressiva

Um colaborador pode ver:

```text
próprias métricas
```

Gestor:

```text
equipe
```

Diretoria:

```text
organização
```

---

# 415. Rankings devem ser evitados no D0

Mesmo que os dados permitam.

O foco é gestão de fluxo e melhoria.

---

# 416. Acesso ao custo

Se futuramente houver custo por hora ou margem, isso pode exigir ações específicas.

Não pertence ao D0.

---

# 417. Acesso financeiro

Da mesma forma, não presumir que todo gestor pode ver valores.

Pode existir escopo/ação futura.

---

# 418. Dados sensíveis futuros

A arquitetura deve permitir novas ações de consulta conforme surgirem módulos.

---

# 419. Evolução sem quebrar perfis existentes

Quando nova funcionalidade surgir:

```text
nova ação
```

começa negada.

Administrador pode conceder.

---

# 420. D0 deve ser administrável por uma pessoa não técnica

Esse é um requisito de produto.

Se configurar um usuário exigir SQL ou desenvolvedor, falhamos no dinamismo.

---

# 421. Interface futura de autorização

Conceitualmente pode mostrar:

```text
Perfil: Gestor Comercial

Atividades
[x] Visualizar
[x] Criar
[x] Editar
[x] Alterar dono

Filas
[x] Visualizar
[x] Visualizar completa
[x] Reordenar

Cadastros
[x] Consultar setores
[ ] Criar setores
```

---

# 422. Escopo futuro na interface

Exemplo:

```text
Este perfil/usuário vale para:

Empresa:
Biasi Engenharia

Setores:
[x] Comercial
[x] Administrativo
[ ] Financeiro
```

A forma final será definida no documento 09.

---

# 423. Evitar uma tela impossível de usar

Centenas de ações precisam ser agrupadas, pesquisáveis e talvez filtráveis.

---

# 424. Presets

Futuramente:

```text
Somente leitura
Operacional
Gestão
Administração
```

podem acelerar configuração.

---

# 425. Preset é apenas ponto de partida

A empresa continua podendo ajustar.

---

# 426. Segurança e usabilidade precisam coexistir

Sistema muito rígido:

```text
ninguém consegue trabalhar
```

Sistema permissivo demais:

```text
todo mundo vê e altera tudo
```

A LPS precisa equilibrar.

---

# 427. Teste prático de configuração

Ao cadastrar usuário, administrador precisa conseguir responder:

```text
Em quais setores ele atua?
```

```text
Quais ações pode executar?
```

```text
Em quais setores/empresas/obras?
```

---

# 428. Se a resposta não for clara, a configuração está complexa demais

Esse será um critério de UX.

---

# 429. Matriz simples de exemplo

| Usuário | Setor | Visualizar | Executar | Reordenar fila | Criar setor |
|---|---|---:|---:|---:|---:|
| Paulo | Comercial | Sim | Sim | Sim | Conforme perfil |
| Paulo | Administrativo | Sim | Não | Não | Não |
| Ryan | Comercial | Sim | Sim | Não | Não |
| Igor | Almoxarifado | Sim | Sim | Sim | Não |

Essa tabela é apenas exemplo conceitual.

---

# 430. A matriz real não deve ser fixa

Ela é resultado dos perfis e escopos configurados.

---

# 431. Importância da auditoria de autorizações

Se alguém perguntar:

> Por que esse usuário conseguiu alterar a fila?

A LPS deve conseguir responder:

```text
Porque possuía fila.reordenar no setor naquele momento.
```

---

# 432. Segurança como parte da confiabilidade

Uma plataforma de gestão só é confiável se:

- dados corretos;
- autoria correta;
- acesso correto.

---

# 433. Usuário compartilhado é inadequado

Evitar contas coletivas como:

```text
financeiro@empresa
```

usadas por várias pessoas.

A auditoria perderia autoria individual.

---

# 434. Cada pessoa deve possuir identidade própria

Isso é fundamental para:

- tempo;
- responsabilidade;
- auditoria;
- segurança.

---

# 435. Contas de integração são exceção

Devem ser claramente identificadas como técnicas.

---

# 436. Autenticação e autorização são diferentes

## Autenticação

Responde:

> Quem é você?

## Autorização

Responde:

> O que você pode fazer?

A LPS precisa das duas.

---

# 437. Login válido não significa acesso total

Após autenticar, todas as ações ainda passam por autorização.

---

# 438. Sessão expirada

Pertence à autenticação.

Não altera perfis ou permissões.

---

# 439. Permissão revogada durante sessão

Idealmente, deve deixar de valer sem exigir dias para refletir.

Detalhamento técnico futuro.

---

# 440. Cache de permissão

Se houver cache por performance, precisa ser invalidado corretamente.

Assunto técnico do banco/aplicação.

---

# 441. Acesso em tempo real

Mudanças críticas de permissão devem refletir rapidamente.

---

# 442. Segurança e multiempresa

Se usuário possui acesso a duas empresas internas:

```text
Empresa A
Empresa B
```

a interface pode permitir troca de contexto.

---

# 443. Contexto atual não substitui autorização

Selecionar Empresa A não concede acesso a ela.

O usuário já precisa ter autorização.

---

# 444. Filtro de empresa

Serve para experiência.

A segurança continua independente.

---

# 445. Ação fora de contexto

Mesmo que usuário altere URL ou chamada manualmente, backend deve negar.

---

# 446. Organização não pode ser trocada por parâmetro do cliente

O servidor precisa conhecer a organização autenticada de forma confiável.

Assunto técnico do banco.

---

# 447. Segurança por design

Autorização precisa nascer junto com o produto.

Não ser adicionada no final.

---

# 448. Por que isso é importante para a LPS

A LPS quer ser altamente configurável.

Sem uma base de autorização dinâmica, cada nova configuração aumenta risco.

---

# 449. Dinamismo controlado

A equação é:

```text
flexibilidade
+
regras claras
+
auditoria
=
dinamismo seguro
```

---

# 450. Flexibilidade sem controle

Geraria:

- acesso excessivo;
- dados vazados;
- regras contraditórias;
- dificuldade de suporte.

---

# 451. Controle sem flexibilidade

Geraria:

- necessidade de customização;
- empresa presa ao organograma da LPS;
- baixa aderência.

---

# 452. Objetivo da arquitetura

Permitir que:

```text
Empresa A
```

e:

```text
Empresa B
```

tenham organizações muito diferentes usando a mesma base de produto.

---

# 453. Exemplo de Empresa A

```text
Setores:
Financeiro
Comercial
Compras
Almoxarifado
```

---

# 454. Exemplo de Empresa B

```text
Setores:
Administrativo
Operações
Engenharia
```

---

# 455. Mesmo motor de autorização

Nos dois casos:

```text
usuário
+
perfil
+
ação
+
escopo
```

---

# 456. Perguntas de validação para qualquer nova função

Ao criar nova funcionalidade, perguntar:

1. Qual recurso está sendo acessado?
2. Quais ações existem?
3. Quem normalmente pode executar?
4. O escopo pode variar?
5. Existe diferença entre visualizar e alterar?
6. Existe ação sensível?
7. Precisa auditar?
8. Como negar por padrão?

---

# 457. Exemplo — novo módulo de aprovações

Recurso:

```text
aprovação
```

Ações:

```text
visualizar
solicitar
aprovar
reprovar
```

Escopos:

```text
empresa
setor
atividade própria
```

---

# 458. Exemplo — novo módulo de relatórios

Recurso:

```text
relatorio
```

Ações:

```text
visualizar
exportar
```

Escopos:

```text
setor
empresa
organização
```

---

# 459. Crescimento consistente

Esse padrão evita inventar segurança diferente em cada módulo.

---

# 460. O que o D0 precisa provar

A primeira versão precisa demonstrar que:

- usuário de uma organização não acessa outra;
- usuário pode pertencer a vários setores;
- usuário pode visualizar setor sem pertencer a ele;
- perfis funcionam;
- ações funcionam;
- escopos funcionam;
- fila pode ter autorização separada;
- cadastros podem ser protegidos;
- auditoria de alterações funciona.

---

# 461. Teste de cenário 1

```text
Ryan
Setor Comercial
```

Tenta:

```text
criar setor
```

Sem:

```text
setor.criar
```

Resultado:

```text
NEGADO
```

---

# 462. Teste de cenário 2

```text
Paulo
Comercial
```

Possui visualização do Administrativo.

Resultado:

```text
visualiza
```

Mas tenta editar:

```text
NEGADO
```

---

# 463. Teste de cenário 3

```text
Igor
Almoxarifado
```

Possui:

```text
fila.reordenar
```

Resultado:

```text
PERMITIDO
```

---

# 464. Teste de cenário 4

```text
Solicitante do Comercial
```

acessa tarefa do Almoxarifado que pertence à sua atividade.

Pode ver:

```text
posição
status
prazo
```

Não vê:

```text
fila completa
```

---

# 465. Teste de cenário 5

Usuário da Organização B tenta acessar ID de atividade da Organização A.

Resultado:

```text
NEGADO
```

independentemente da interface.

---

# 466. Teste de cenário 6

Usuário inativo tenta autenticar ou executar ação.

Resultado:

```text
NEGADO
```

---

# 467. Teste de cenário 7

Administrador remove perfil do usuário.

A ação deixa de ser permitida.

Histórico registra remoção.

---

# 468. Teste de cenário 8

Usuário possui dois perfis.

A autorização final soma ações válidas dentro dos escopos correspondentes.

---

# 469. Teste de cenário 9

Dono de atividade acessa tarefa da própria atividade em setor que não participa.

Vê contexto permitido daquela atividade.

Não recebe acesso geral ao setor.

---

# 470. Teste de cenário 10

Usuário tenta concluir tarefa sem ação `tarefa.concluir`.

Resultado:

```text
NEGADO
```

mesmo sendo executor.

---

# 471. Critério de aceite do módulo

O módulo está correto quando essas regras são previsíveis, configuráveis e auditáveis.

---

# 472. Não criar exceções em código para pessoas

Evitar:

```text
if user.email == "paulo@...":
    permitir
```

Qualquer exceção deve ser configuração.

---

# 473. Não criar exceções em código para cliente

Evitar:

```text
if organization == "Biasi":
```

para regras de acesso.

Usar configuração.

---

# 474. Não criar exceções em código para setor

Evitar:

```text
if sector == "Financeiro":
```

para liberar funções.

Usar ações e escopos.

---

# 475. Essa é a base da escalabilidade

Sem isso, cada novo cliente gera dívida técnica.

---

# 476. Autorizações como produto

Uma LPS madura pode transformar a segurança configurável em diferencial competitivo.

A empresa controla sua estrutura sem depender de desenvolvimento.

---

# 477. Mas a segurança não deve virar um projeto interminável

O D0 precisa do necessário para operar.

Não precisa copiar toda a complexidade de sistemas com décadas de evolução.

---

# 478. Estrutura inicial recomendada

```text
Organização
Empresa
Usuário
Setor
Usuário-Setor

Perfil
Grupo de Ações
Ação
Perfil-Ação
Usuário-Perfil

Escopo
Autorização
```

---

# 479. Evoluções posteriores

```text
Permissões diretas
Expiração
Usuários externos
Negação explícita
Permissão por campo
Aprovação de concessão
```

somente quando necessário.

---

# 480. Regra de ouro do dinamismo

> **A LPS não deve conhecer antecipadamente o organograma de cada cliente; ela deve fornecer os mecanismos para cada cliente configurar sua própria operação.**

---

# 481. Regra de ouro da participação

> **Pertencer a um setor descreve a estrutura da empresa; autorização descreve o acesso. Não misturar os dois.**

---

# 482. Regra de ouro da escalabilidade

> **Quando um cliente precisar de uma regra diferente, primeiro perguntar se isso pode ser configuração antes de alterar código.**

---

# 483. Regra de ouro da auditoria de segurança

> **Toda alteração que muda o que alguém pode fazer precisa deixar histórico.**

---

# 484. Resumo funcional

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
PERFIS SÃO ATRIBUÍDOS
↓
PERFIS CONCEDEM AÇÕES
↓
ESCOPOS DEFINEM ONDE AS AÇÕES VALEM
↓
EXCEÇÕES PODEM SER CONCEDIDAS
↓
CADA AÇÃO É VALIDADA
↓
SE NÃO HÁ PERMISSÃO:
NEGAR
↓
SE HÁ PERMISSÃO E REGRA DE NEGÓCIO VÁLIDA:
PERMITIR
↓
TODA ALTERAÇÃO DE SEGURANÇA É AUDITADA
```

---

# 485. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação da estrutura de usuários, setores, perfis, ações, escopos e autorizações da LPS |

---

# 486. Encerramento

A LPS precisa nascer configurável sem nascer descontrolada.

A empresa deve poder decidir:

- quais setores existem;
- quem participa de cada setor;
- quais perfis existem;
- quais ações cada perfil possui;
- quem pode visualizar;
- quem pode criar;
- quem pode executar;
- quem pode reordenar fila;
- quem pode atribuir responsáveis;
- quem pode alterar prazos;
- quem pode escalar;
- quem pode configurar o próprio sistema.

Ao mesmo tempo, a LPS precisa manter princípios fixos:

- isolamento entre organizações;
- negação por padrão;
- rastreabilidade;
- autorização independente da interface;
- histórico preservado;
- segurança baseada em capacidades reais do produto.

Essa combinação permite que a LPS seja utilizada por empresas com estruturas muito diferentes sem exigir que o código seja refeito para cada uma.

O resultado esperado é:

> **um produto único, com operação configurável, regras claras e segurança auditável.**
