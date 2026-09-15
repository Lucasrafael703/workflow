# 08 — Banco de Dados da LPS

> Revisão técnico-funcional do banco de dados da LPS.
>
> Esta versão consolida as decisões do projeto sobre organizações, empresas, usuários, setores, perfis, ações, escopos, atividades, tarefas, filas, prazos, tempo, comunicação, notificações, escalonamento, auditoria e inteligência futura.
>
> O benchmark do Sienge foi usado para aprender sobre dinamismo de autorizações, não para reproduzir sua estrutura histórica.

---

## 1. Regra principal

O banco deve seguir o produto.

```text
NEGÓCIO
↓
COMPORTAMENTO
↓
DADOS
```

Nunca o contrário.

A LPS não deve criar tabelas ou complexidade apenas porque outro ERP possui determinada estrutura.

---

## 2. Princípios de modelagem

O banco deve priorizar:

- isolamento entre organizações;
- consistência;
- rastreabilidade;
- histórico;
- segurança;
- simplicidade de operação;
- configuração sem alteração de código;
- baixo acoplamento entre módulos;
- dados estruturados;
- evolução sem reescrever a base;
- capacidade futura de análise e inteligência.

---

## 3. Fatos antes de conclusões

O banco deve registrar fatos operacionais.

Exemplo insuficiente:

```text
tarefa.status = concluida
```

Exemplo correto:

```text
status_atual = concluida
+
eventos:
- criada
- entrou na fila
- iniciou
- pausou
- retomou
- devolveu
- voltou
- concluiu
```

O estado atual atende a operação.

O histórico atende:

- auditoria;
- métricas;
- investigação;
- comparação;
- previsões futuras.

---

## 4. Tecnologia-base

A recomendação continua sendo PostgreSQL.

Pode ser operado em Supabase, Neon ou infraestrutura equivalente, desde que sejam preservados:

- PostgreSQL relacional;
- chaves estrangeiras;
- constraints;
- transações;
- índices;
- Row Level Security — RLS, Segurança em Nível de Linha — quando aplicável;
- funções seguras para operações críticas;
- logs e auditoria.

A arquitetura não deve ficar dependente de um fornecedor específico sem necessidade.

---

## 5. Identificadores

Registros principais usam `uuid`.

Exemplo:

```sql
id uuid primary key
```

Quando disponível, UUIDv7 é interessante para melhorar ordenação temporal e localidade de índice, mas não é requisito funcional do D0.

IDs internos nunca devem ser reutilizados.

---

## 6. Organização é o tenant

`organizacao_id` define o limite máximo de segurança.

Regra:

> Nenhum relacionamento pode atravessar organizações.

Exemplo proibido:

```text
atividade da Organização A
→ setor da Organização B
```

O banco precisa impedir esse cenário, não apenas a interface.

---

## 7. Empresa é contexto interno

Uma organização pode possuir várias empresas.

```text
ORGANIZAÇÃO
└── EMPRESAS
```

Empresa não é tenant.

Usuários da mesma organização podem possuir escopos diferentes por empresa.

---

## 8. Schemas

Estrutura consolidada:

```text
core
acessos
cadastros
produtividade
comunicacao
configuracoes
auditoria
```

Um schema futuro de `inteligencia` só deve surgir quando houver funcionalidades reais que justifiquem persistência própria.

---

# PARTE A — CORE

## 9. `core.organizacoes`

### Finalidade

Representar o tenant da LPS.

### Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| nome | text | Sim | Nome da organização |
| slug | text | Sim | Identificador amigável |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Auditoria |
| criado_por | uuid | Não | Administrador/plataforma |

### Índices

```text
unique(slug)
index(ativo)
```

---

## 10. `core.empresas`

### Finalidade

Representar empresas operacionais ou jurídicas dentro do tenant.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| codigo | text | Não |
| nome | text | Sim |
| documento | text | Não |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Regras

- pertence sempre a uma organização;
- código pode ser amigável;
- empresa inativa preserva histórico;
- uma entidade poderá futuramente assumir também papel de cliente sem duplicar identidade desnecessariamente.

### Índices

```text
unique(organizacao_id, codigo) where codigo is not null
index(organizacao_id, ativo)
```

---

## 11. `core.usuarios`

### Finalidade

Identidade de acesso da pessoa ou conta técnica.

### Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| auth_user_id | uuid | Não | Identidade do provedor de autenticação |
| codigo | text | Não | Código humano opcional |
| nome | text | Sim | Nome exibido |
| email | citext/text | Sim | Login/comunicação |
| ativo | boolean | Sim | Situação |
| tipo | text | Sim | humano / integracao |
| criado_em | timestamptz | Sim | Histórico |
| atualizado_em | timestamptz | Sim | Histórico |

### Regras

- um usuário pertence a uma única organização;
- inativar em vez de excluir quando houver histórico;
- e-mail não deve ser usado como chave histórica;
- `auth_user_id` não substitui o `id` de domínio;
- contas técnicas devem ser identificadas explicitamente.

### Índices

```text
unique(organizacao_id, email)
index(organizacao_id, ativo)
index(auth_user_id)
```

---

## 12. Cargo ou função organizacional

Não é necessário para o motor de segurança.

Se entrar no D0 ou D1, usar tabela separada:

```text
core.cargos
```

Campos possíveis:

```text
id
organizacao_id
nome
ativo
```

E no usuário:

```text
cargo_id nullable
```

Regra:

> Cargo descreve a pessoa; não concede permissão automaticamente.

---

## 13. `core.setores`

### Finalidade

Estrutura operacional configurável da organização.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| empresa_id | uuid | Não |
| codigo | text | Não |
| nome | text | Sim |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Regras

- não existem setores fixos no código;
- setor pode ser corporativo ou vinculado a empresa conforme necessidade;
- impedir apenas duplicidade exata normalizada dentro do mesmo contexto;
- nomes semelhantes podem coexistir;
- inativação preserva histórico.

### Índices

```text
index(organizacao_id, ativo)
index(empresa_id, ativo)
```

---

## 14. `core.usuario_setores`

### Finalidade

Relacionar usuários aos setores em que participam operacionalmente.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| usuario_id | uuid | Sim |
| setor_id | uuid | Sim |
| papel | text | Não |
| inicio_em | timestamptz/date | Não |
| fim_em | timestamptz/date | Não |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Chave

Pode usar chave composta ou `id` próprio se histórico de períodos for necessário.

### Regra crítica

```text
usuario_setores != autorização
```

Pertencer ao setor não significa receber todas as capacidades sobre ele.

---

## 15. Gestores de setor

Há duas opções técnicas aceitáveis.

### Opção simples

Usar `papel = gestor` em `core.usuario_setores`.

### Opção mais explícita

Criar:

```text
core.setor_gestores
```

com:

```text
setor_id
usuario_id
inicio_em
fim_em
```

A segunda opção facilita histórico e múltiplos gestores.

Para D0, ambas são válidas; evitar duplicar conceitos.

Ser gestor não concede autorização automaticamente.

---

# PARTE B — ACESSOS

## 16. Objetivo do schema `acessos`

Permitir que a LPS resolva:

```text
QUEM
+
AÇÃO
+
ESCOPO
+
ORIGEM
```

sem tabelas de autorização diferentes para cada módulo ou tipo de contexto.

---

## 17. Decisão arquitetural mais importante da revisão

Não criar motores separados como:

```text
usuario_empresa_autorizacoes
usuario_obra_autorizacoes
usuario_setor_autorizacoes
usuario_centro_custo_autorizacoes
```

A LPS deve usar um motor genérico de escopo.

Empresa, setor, obra e centro de custo são **tipos de escopo**.

Isso mantém o dinamismo sem copiar a fragmentação do benchmark.

---

## 18. `acessos.grupos_acoes`

### Finalidade

Organizar ações para a interface e administração.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| chave | text | Sim |
| nome | text | Sim |
| descricao | text | Não |
| ordem | integer | Sim |
| ativo | boolean | Sim |

### Exemplos

```text
atividades
tarefas
filas
prazos
cadastros
seguranca
auditoria
comunicacao
```

Grupo não concede acesso.

---

## 19. `acessos.acoes`

### Finalidade

Catálogo atômico das capacidades reais da LPS.

### Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| grupo_id | uuid | Sim | Organização visual |
| chave | text | Sim | Ex.: `fila.reordenar` |
| nome | text | Sim | Nome amigável |
| descricao | text | Sim | O que permite |
| sensivel | boolean | Sim | UX/auditoria reforçada |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Histórico |

### Índices

```text
unique(chave)
index(grupo_id, ativo)
```

### Regra crítica

Ação existe porque a aplicação possui comportamento correspondente.

No D0, a organização não cria ações arbitrárias que o código desconhece.

A organização configura **combinações** de ações através de perfis.

---

## 20. `acessos.perfis`

### Finalidade

Conjunto configurável de capacidades.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| nome | text | Sim |
| descricao | text | Não |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |
| atualizado_em | timestamptz | Sim |
| atualizado_por | uuid | Sim |

### Índices

```text
unique(organizacao_id, nome)
index(organizacao_id, ativo)
```

Perfil é totalmente configurável pela organização.

---

## 21. `acessos.perfil_acoes`

### Finalidade

Marcar/desmarcar quais ações fazem parte de um perfil.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| perfil_id | uuid | Sim |
| acao_id | uuid | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Chave

```text
primary key(perfil_id, acao_id)
```

Essa tabela é a base da UX de checkbox.

Marcar:

```text
INSERT perfil_acoes
```

Desmarcar:

```text
DELETE perfil_acoes
```

A auditoria registra ambas as operações.

---

## 22. `acessos.escopos`

### Finalidade

Representar onde uma concessão é válida.

### Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| tipo | text | Sim | Tipo do escopo |
| empresa_id | uuid | Não | Quando aplicável |
| setor_id | uuid | Não | Quando aplicável |
| obra_id | uuid | Não | Quando aplicável |
| centro_custo_id | uuid | Não | Quando aplicável |
| relacao | text | Não | Escopo relacional |
| nome_exibicao | text | Não | Leitura humana |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Histórico |

### Tipos iniciais

```text
organizacao
empresa
setor
obra
centro_custo
relacional
combinado
```

### Relações canônicas possíveis

```text
minhas_atividades
minhas_tarefas
meus_setores
setores_gerenciados
```

### Regra

O banco precisa validar coerência entre `tipo` e os campos preenchidos.

Exemplo:

```text
tipo = setor
→ setor_id obrigatório
→ obra_id nulo
```

---

## 23. Por que não usar apenas `scope_type + scope_id`

Um par genérico como:

```text
scope_type
scope_id
```

é simples, mas perde chaves estrangeiras reais para tabelas diferentes.

Para o D0, campos explícitos em `acessos.escopos` são mais seguros e fáceis de validar.

Caso o número de tipos de escopo cresça muito no futuro, a arquitetura pode ser reavaliada.

---

## 24. `acessos.usuario_perfis`

### Finalidade

Atribuir um perfil a um usuário dentro de determinado escopo.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| usuario_id | uuid | Sim |
| perfil_id | uuid | Sim |
| escopo_id | uuid | Sim |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Exemplo

```text
Paulo
+ Gestor Comercial
+ Setor Comercial
```

### Índices

```text
index(usuario_id, ativo)
index(perfil_id, ativo)
index(escopo_id, ativo)
unique(usuario_id, perfil_id, escopo_id) where ativo = true
```

---

## 25. Limitação consciente do D0

No D0, todas as ações do perfil compartilham o escopo da atribuição.

Exemplo:

```text
Gestor Comercial
aplicado ao Setor Comercial
```

Se o mesmo usuário precisar:

```text
ver atividades da empresa inteira
mas reordenar somente Comercial
```

há duas formas simples:

1. usar dois perfis diferentes;
2. usar concessão direta para a exceção.

Não criar um construtor de políticas complexo antes de existir necessidade real.

---

## 26. `acessos.usuario_acoes`

### Finalidade

Concessões diretas para exceções individuais.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| usuario_id | uuid | Sim |
| acao_id | uuid | Sim |
| escopo_id | uuid | Sim |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Regra

No D0, essa tabela representa apenas concessões positivas.

Sem concessão válida:

```text
NEGAR
```

Não implementar DENY explícito inicialmente.

---

## 27. Permissão efetiva não deve ser gravada como fonte de verdade

A permissão efetiva é derivada de:

```text
perfil_acoes
+
usuario_perfis
+
usuario_acoes
+
escopos
+
situação do usuário
+
regra de negócio
```

Pode existir uma `view` para facilitar consulta.

Exemplo:

```text
acessos.vw_permissoes_efetivas
```

Mas a view não substitui as tabelas de origem.

---

## 28. Pseudocálculo da autorização

```text
se usuario.ativo = false
    negar

se recurso.organizacao_id != usuario.organizacao_id
    negar

se existe perfil ativo do usuário
   onde perfil possui a ação
   e escopo contém o recurso
    candidato = permitido

se existe concessão direta ativa
   da ação
   em escopo que contém o recurso
    candidato = permitido

se nenhum candidato
    negar

se regra de negócio impedir a ação
    negar

permitir
```

---

## 29. Origem da permissão

A consulta administrativa deve conseguir retornar:

```text
usuario
acao
escopo
origem_tipo
origem_id
origem_nome
```

Exemplo:

```text
Paulo
fila.reordenar
Setor Comercial
perfil
Gestor Comercial
```

Não é necessário persistir isso como duplicação; pode ser produzido por view/consulta.

---

## 30. Auditoria de segurança

Toda alteração em:

```text
perfis
perfil_acoes
usuario_perfis
usuario_acoes
escopos
usuario_setores
```

deverá gerar evento de auditoria.

---

# PARTE C — CADASTROS

## 31. `cadastros.obras`

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| empresa_id | uuid | Sim |
| codigo | text | Não |
| nome | text | Sim |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

### Regra

Obra é cadastro operacional, não sinônimo de centro de custo.

---

## 32. `cadastros.centros_custo`

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| empresa_id | uuid | Sim |
| obra_id | uuid | Não |
| codigo | text | Não |
| nome | text | Sim |
| ativo | boolean | Sim |

### Regras

- pode existir sem obra;
- pode estar associado a obra;
- atividade pode referenciar obra e centro de custo simultaneamente;
- nenhuma atividade é obrigada a possuir obra.

---

## 33. Cliente

A modelagem definitiva de cliente ainda pode evoluir para um cadastro genérico de pessoas/entidades com múltiplos papéis.

Não bloquear o D0 por isso.

Atividade interna pode existir sem cliente.

---

# PARTE D — PRODUTIVIDADE

## 34. `produtividade.atividades`

### Finalidade

Representar o problema/resultado completo a ser entregue.

### Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| empresa_id | uuid | Sim | Contexto |
| obra_id | uuid | Não | Opcional |
| centro_custo_id | uuid | Não | Opcional |
| tipo_atividade_id | uuid | Não | Configuração |
| titulo | text | Sim | Identificação |
| descricao | text | Não | Contexto |
| dono_usuario_id | uuid | Sim | Um único dono |
| impacto_declarado | text/jsonb | Não | Conforme desenho final |
| prazo_solicitado_em | timestamptz | Não | Necessidade do dono/solicitante |
| prazo_comprometido_em | timestamptz | Não | Compromisso vigente |
| status | text | Sim | Estado atual canônico |
| criado_em | timestamptz | Sim | Métrica |
| criado_por | uuid | Sim | Auditoria |
| concluido_em | timestamptz | Não | Resultado |
| cancelado_em | timestamptz | Não | Quando aplicável |

### Regras

- uma atividade possui exatamente um dono atual;
- dono não é lista;
- obra é opcional;
- centro de custo é opcional;
- atividade pode ser interna;
- status atual não substitui histórico.

---

## 35. Histórico do dono

Mudança de dono precisa deixar evento de domínio/auditoria.

Não basta atualizar:

```text
dono_usuario_id
```

A LPS precisa saber:

```text
quem era
quem passou a ser
quando
quem alterou
motivo, quando exigido
```

Pode existir tabela específica futura se consultas justificarem; no D0, evento estruturado pode ser suficiente.

---

## 36. `produtividade.tarefas`

### Finalidade

Representar passos executáveis dentro da atividade.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Sim |
| tipo_tarefa_id | uuid | Não |
| setor_responsavel_id | uuid | Sim |
| titulo | text | Sim |
| descricao | text | Não |
| status | text | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |
| iniciado_em | timestamptz | Não |
| concluido_em | timestamptz | Não |

### Regra

Uma tarefa possui um setor responsável atual.

Uma atividade pode atravessar vários setores através de suas tarefas.

---

## 37. `produtividade.tarefa_executores`

### Finalidade

Permitir vários executores na mesma tarefa.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| tarefa_id | uuid | Sim |
| usuario_id | uuid | Sim |
| atribuido_em | timestamptz | Sim |
| removido_em | timestamptz | Não |
| atribuido_por | uuid | Sim |

### Regra

Executor não é dono da atividade.

Dois executores podem trabalhar simultaneamente e seus tempos são somados em horas-homem.

---

## 38. `produtividade.tarefa_dependencias`

### Finalidade

Representar dependências explícitas entre tarefas.

Campos:

```text
id
tarefa_id
depende_de_tarefa_id
tipo
criado_em
criado_por
```

No D0, não transformar isso em um motor BPM complexo.

---

## 39. `produtividade.sessoes_tempo`

### Finalidade

Medir tempo real de trabalho de cada executor.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| usuario_id | uuid | Sim |
| inicio_em | timestamptz | Sim |
| fim_em | timestamptz | Não |
| origem | text | Sim |
| observacao | text | Não |
| criado_em | timestamptz | Sim |

### `origem`

Exemplos:

```text
timer
manual
correcao
importacao
```

### Regras

- fim não pode ser anterior ao início;
- sessão aberta tem `fim_em` nulo;
- correção deve ser auditada;
- regra sobre pausar automaticamente outra tarefa deve permanecer configurável/pendente até ser consolidada, não hardcoded prematuramente.

---

## 40. Horas-homem

Derivadas pela soma das sessões.

Exemplo:

```text
Ryan: 1h30
Jennifer: 1h30

Horas-homem = 3h
```

Mesmo que o tempo corrido tenha sido 1h30.

---

## 41. Movimentação entre setores

Criar uma estrutura de histórico de passagem.

Nome sugerido:

```text
produtividade.passagens_setor
```

Campos:

```text
id
organizacao_id
atividade_id
tarefa_id
setor_origem_id nullable
setor_destino_id
entrada_em
saida_em nullable
tipo_movimentacao
motivo_id nullable
movido_por
```

Permite medir:

- permanência por setor;
- retornos;
- gargalos;
- tempo de trânsito.

---

# PARTE E — FILAS

## 42. `produtividade.fila_itens`

### Finalidade

Representar a posição atual da tarefa na fila do setor.

### Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| setor_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| posicao | integer/bigint | Sim |
| entrou_em | timestamptz | Sim |
| saiu_em | timestamptz | Não |
| ativo | boolean | Sim |

### Regra

A fila precisa responder rapidamente:

```text
qual minha posição?
quantos itens existem?
```

---

## 43. `produtividade.fila_historico_posicoes`

### Finalidade

Registrar cada mudança de posição.

### Campos principais

```text
id
organizacao_id
fila_item_id
setor_id
tarefa_id
posicao_anterior
posicao_nova
alterado_em
alterado_por
motivo
causa
```

### Regra consolidada

> Toda mudança de posição é registrada individualmente.

Ela gera evento/notificação dentro da LPS para o dono/solicitante conforme a regra funcional definida.

Canal externo, como e-mail ou push, pode ser configurável separadamente.

---

## 44. Reordenação concorrente

Reordenar a fila é operação crítica.

Precisa ser transacional.

Evitar que dois gestores salvem ordens incompatíveis simultaneamente.

Pode usar:

- lock transacional;
- versionamento otimista;
- campo de versão;
- estratégia de posições espaçadas.

A escolha técnica pode ser feita na implementação, preservando a regra funcional.

---

# PARTE F — DEVOLUÇÕES, BLOQUEIOS E PRAZOS

## 45. `produtividade.devolucoes`

### Finalidade

Registrar retorno estruturado de trabalho.

Campos:

```text
id
organizacao_id
atividade_id
tarefa_id
setor_origem_id
setor_destino_id
motivo_devolucao_id
descricao
devolvido_em
devolvido_por
```

Motivo é obrigatório.

Texto livre complementa, mas não substitui o motivo estruturado.

---

## 46. `produtividade.bloqueios`

Campos:

```text
id
organizacao_id
atividade_id nullable
tarefa_id nullable
motivo_bloqueio_id
descricao
inicio_em
fim_em nullable
registrado_por
```

Permite separar:

- trabalho em execução;
- espera;
- impedimento;
- dependência externa.

---

## 47. Prazo solicitado e prazo comprometido

Não são o mesmo campo.

Na atividade manter:

```text
prazo_solicitado_em
prazo_comprometido_em
```

O primeiro representa necessidade.

O segundo representa compromisso vigente.

---

## 48. `produtividade.prazos_historico`

### Finalidade

Registrar propostas e decisões de prazo.

Campos principais:

```text
id
organizacao_id
atividade_id
tarefa_id nullable
tipo
prazo_anterior
prazo_proposto
proposto_por
proposto_em
status_proposta
respondido_por nullable
respondido_em nullable
motivo_recusa nullable
```

### `tipo`

Exemplos:

```text
solicitado
comprometido
proposta_alteracao
ajuste_direto
```

### `status_proposta`

```text
pendente
aceita
recusada
cancelada
```

### Regra consolidada

Se o executor/setor propõe novo prazo:

- dono aceita → atualiza prazo comprometido;
- dono recusa → gera escalonamento automaticamente conforme configuração.

Nunca substituir silenciosamente o prazo solicitado.

---

# PARTE G — ESCALONAMENTO

## 49. `produtividade.escalonamentos`

Campos principais:

```text
id
organizacao_id
atividade_id
tarefa_id nullable
regra_escalonamento_id nullable
tipo
descricao
status
aberto_em
aberto_por
resolvido_em nullable
resolvido_por nullable
```

---

## 50. `produtividade.escalonamento_destinatarios`

Relaciona escalonamento às pessoas/setores que precisam ser acionados.

```text
escalonamento_id
usuario_id nullable
setor_id nullable
papel
```

---

## 51. `produtividade.escalonamento_eventos`

Histórico de:

- abertura;
- notificação;
- comentário;
- encaminhamento;
- resolução;
- encerramento.

---

# PARTE H — COMUNICAÇÃO

## 52. Princípio

D0 não é um clone completo do Slack.

Conversas existem dentro do contexto de trabalho.

---

## 53. `comunicacao.conversas`

Campos principais:

```text
id
organizacao_id
atividade_id nullable
tarefa_id nullable
criado_em
```

### Regra

Cada conversa precisa estar vinculada a atividade ou tarefa.

Não criar canais livres no D0.

---

## 54. `comunicacao.mensagens`

Campos:

```text
id
organizacao_id
conversa_id
autor_usuario_id nullable
tipo_autor
texto
criado_em
editado_em nullable
excluido_em nullable
```

### `tipo_autor`

```text
usuario
sistema
```

Mensagem não é automaticamente fonte oficial para alteração de prazo, devolução ou decisão estruturada.

---

## 55. `comunicacao.participantes`

Pode existir para otimizar notificações e participação explícita.

Campos:

```text
conversa_id
usuario_id
adicionado_em
removido_em nullable
```

Acesso à conversa continua condicionado ao acesso ao objeto vinculado.

---

## 56. `comunicacao.mencoes`

```text
mensagem_id
usuario_id
```

Mencionar alguém não deve ultrapassar regras de segurança.

---

# PARTE I — NOTIFICAÇÕES

## 57. `comunicacao.notificacoes`

### Finalidade

Central interna de notificações da LPS.

Campos principais:

```text
id
organizacao_id
usuario_id
tipo
entidade_tipo
entidade_id
titulo
mensagem
criado_em
lido_em nullable
prioridade nullable
dados jsonb nullable
```

### Eventos essenciais

- mudança de posição na fila;
- conclusão;
- retorno;
- mudança de responsável;
- proposta de prazo;
- prazo aceito/recusado;
- escalonamento;
- bloqueio relevante;
- menção.

### Regra consolidada da fila

Cada mudança de posição deve produzir registro interno individual da alteração/notificação aplicável.

Agrupamento visual ou canais externos não devem apagar o histórico individual.

### Regra consolidada da conclusão

Dono da atividade recebe notificação de conclusão obrigatoriamente.

---

## 58. Preferências de notificação

Tabela sugerida:

```text
comunicacao.preferencias_notificacao
```

Pode controlar:

```text
canal_email
canal_push
resumo
silenciamento
```

Preferência pessoal não deve desabilitar evento obrigatório de auditoria nem eliminar a notificação interna que o produto definiu como obrigatória.

---

## 59. Entrega por canal

Se houver e-mail/push, separar evento da entrega.

Sugestão futura:

```text
comunicacao.entregas_notificacao
```

Campos:

```text
notificacao_id
canal
status
tentativas
enviado_em
erro
```

---

# PARTE J — CONFIGURAÇÕES

## 60. Princípio

Configurações representam vocabulário e regras operacionais da organização.

Não devem transformar o banco em um construtor arbitrário de software.

---

## 61. `configuracoes.tipos_atividade`

Campos:

```text
id
organizacao_id
nome
descricao
ativo
```

---

## 62. `configuracoes.tipos_tarefa`

Mesmo padrão.

---

## 63. `configuracoes.motivos_devolucao`

Campos:

```text
id
organizacao_id
nome
descricao
ativo
```

Exemplos possíveis:

```text
informação incompleta
especificação incorreta
arquivo inválido
aprovação necessária
```

A empresa pode configurar sua lista.

---

## 64. `configuracoes.motivos_bloqueio`

Mesma lógica.

---

## 65. Modelos de fluxo

Tabelas futuras/gradativas:

```text
configuracoes.fluxos_modelo
configuracoes.fluxo_tarefas_modelo
configuracoes.fluxo_dependencias_modelo
```

No início, a empresa pode construir processos manualmente.

Com o tempo, a LPS pode sugerir modelos reaproveitáveis.

Modelo aplicado deve gerar estrutura operacional independente, preservando histórico mesmo se o template mudar depois.

---

## 66. Regras de notificação

Tabela sugerida:

```text
configuracoes.regras_notificacao
```

Deve guardar apenas regras realmente configuráveis.

Evitar um construtor genérico `IF X AND Y OR Z` no D0.

---

## 67. Regras de escalonamento

Tabela sugerida:

```text
configuracoes.regras_escalonamento
```

Pode evoluir para disparadores como:

- prazo proposto recusado;
- tarefa atrasada;
- bloqueio acima de limite;
- atividade sem resposta;
- retorno repetido.

Percentuais ou limites não devem ser hardcoded sem decisão de produto.

---

# PARTE K — AUDITORIA

## 68. `auditoria.eventos`

### Finalidade

Registrar alterações relevantes de sistema e negócio que precisam de rastreabilidade genérica.

### Campos principais

```text
id
organizacao_id
usuario_id nullable
tipo_evento
entidade_tipo
entidade_id
acao
ocorrido_em
dados_antes jsonb nullable
dados_depois jsonb nullable
contexto jsonb nullable
request_id nullable
```

### Exemplos

```text
perfil.alterado
usuario.inativado
fila.reordenada
prazo.recusado
setor.inativado
permissao.concedida
permissao.removida
```

---

## 69. Auditoria não substitui históricos de domínio

Exemplo:

```text
fila_historico_posicoes
```

é fonte operacional para análise de fila.

`auditoria.eventos` complementa respondendo:

```text
quem alterou e como
```

Não usar uma única tabela JSON genérica para todo o produto.

---

## 70. Eventos de auditoria devem ser imutáveis

Evitar edição e exclusão rotineira.

Correções devem gerar novo evento.

---

## 71. Auditoria de login

Pode existir tabela específica:

```text
auditoria.acessos
```

Campos possíveis:

```text
usuario_id
sucesso
ocorrido_em
ip
user_agent
motivo_falha
```

Seguir políticas de privacidade e retenção.

---

# PARTE L — SEGURANÇA TÉCNICA

## 72. RLS

RLS — Row Level Security, Segurança em Nível de Linha — deve garantir principalmente:

```text
usuario só acessa sua organização
```

E, conforme a tabela:

- escopo permitido;
- relação com atividade/tarefa;
- privilégios administrativos.

Não concentrar toda lógica de autorização apenas no frontend.

---

## 73. Funções auxiliares de autorização

Podem existir funções SQL seguras como:

```text
acessos.usuario_tem_acao(...)
acessos.usuario_pode_acessar_recurso(...)
```

Mas evitar lógica duplicada entre várias funções contraditórias.

A fonte de verdade precisa ser clara.

---

## 74. Índices para autorização

Essenciais:

```text
usuario_perfis(usuario_id, ativo)
perfil_acoes(perfil_id, acao_id)
usuario_acoes(usuario_id, acao_id, ativo)
escopos(organizacao_id, tipo)
usuario_setores(usuario_id, setor_id)
```

Consultas de segurança não podem exigir varrer tabelas inteiras.

---

## 75. Não confiar no contexto selecionado na tela

Trocar o seletor de empresa no frontend não cria autorização.

O banco continua validando:

```text
organização
+
ação
+
escopo
```

---

# PARTE M — INTEGRIDADE E HISTÓRICO

## 76. Exclusão física

Evitar exclusão física de registros com histórico relevante.

Preferir:

```text
ativo = false
```

ou estados de cancelamento/inativação.

`deleted_at` só quando houver necessidade real.

---

## 77. `ON DELETE`

Usar de forma intencional.

### `RESTRICT`

Para objetos com histórico que não podem desaparecer.

### `SET NULL`

Quando preservar fato histórico sem vínculo ativo é aceitável.

### `CASCADE`

Somente para objetos dependentes sem valor histórico independente.

Não usar cascade em massa por conveniência.

---

## 78. Timestamps

Padrão:

```text
criado_em
atualizado_em
concluido_em
cancelado_em
inativado_em
```

conforme o domínio.

Preferir `timestamptz`.

---

## 79. Histórico de nomes

IDs são a referência real.

Renomear setor não pode destruir métricas históricas.

Quando necessário para auditoria legível, eventos podem guardar snapshot textual.

---

# PARTE N — MÉTRICAS E INTELIGÊNCIA FUTURA

## 80. Dados que o D0 precisa capturar

Para aprender depois, o banco precisa registrar hoje:

- criação da atividade;
- criação da tarefa;
- entrada em fila;
- posições da fila;
- início do trabalho;
- pausas/retomadas;
- sessões por executor;
- mudanças de setor;
- devoluções;
- motivos;
- bloqueios;
- propostas de prazo;
- decisões sobre prazo;
- conclusão;
- escalonamentos;
- conversas contextuais;
- alterações de prioridade/ordem;
- usuário e setor envolvidos.

---

## 81. Não criar tabelas de IA no D0

A inteligência futura deve começar derivando padrões desses fatos.

Não criar agora:

```text
ia_previsoes
ia_recomendacoes
embeddings_de_tudo
```

sem funcionalidade real.

---

## 82. Evolução esperada

```text
D0
registrar corretamente

D1
analisar

D2
prever e recomendar
```

A camada de dados precisa permitir essa evolução sem obrigar inteligência artificial no início.

---

## 83. Possíveis análises futuras

- tempo médio por tipo de tarefa;
- tempo por setor;
- tempo de fila;
- retorno por motivo;
- gargalos recorrentes;
- concentração de horas-homem;
- estimativa de prazo;
- comparação entre processos semelhantes;
- sugestão de treinamento;
- sugestão de fluxo;
- resumo automático da atividade.

Nenhuma dessas conclusões precisa ser gravada como fato operacional no D0.

---

# PARTE O — CONSULTAS ESSENCIAIS

## 84. Usuário e segurança

A LPS precisa responder rapidamente:

```text
quais perfis este usuário possui?
quais ações efetivas?
em quais escopos?
de onde veio cada permissão?
```

---

## 85. Perfil

```text
quais ações estão marcadas?
quais usuários usam este perfil?
em quais escopos ele está atribuído?
```

---

## 86. Ação

```text
quem pode executar esta ação?
em qual escopo?
via qual perfil ou concessão direta?
```

---

## 87. Escopo

```text
quem pode atuar na Obra X?
quem pode reordenar o Setor Comercial?
quem pode visualizar a Empresa B?
```

---

## 88. Atividade

```text
quem é o dono?
qual prazo solicitado?
qual prazo comprometido?
quais tarefas?
quais setores tocaram?
quantas devoluções?
quanto tempo total?
quanto tempo de trabalho?
```

---

## 89. Fila

```text
posição da minha tarefa
total da fila
tempo em fila
histórico de posições
quem reordenou
motivo
```

---

# PARTE P — VIEWS RECOMENDADAS

## 90. `acessos.vw_permissoes_efetivas`

Uso administrativo e de suporte.

Colunas possíveis:

```text
usuario_id
acao_id
acao_chave
escopo_id
escopo_tipo
origem_tipo
origem_id
origem_nome
```

Não usar como única barreira de segurança.

---

## 91. `produtividade.vw_tempo_tarefa`

Pode calcular:

```text
tempo_decorrido
horas_homem
tempo_em_execucao
```

quando a consulta justificar.

---

## 92. `produtividade.vw_tempo_setor`

Deriva das passagens e eventos.

---

## 93. Materialized views

Só criar quando volume e custo de consulta exigirem.

Não antecipar otimização.

---

# PARTE Q — JSONB

## 94. Onde usar

Bom para:

- snapshots de auditoria;
- payload de integração;
- metadados extensíveis de evento;
- condições de configuração que ainda não justificam normalização.

---

## 95. Onde evitar

Não guardar em JSONB o que precisa de:

- FK;
- filtro frequente;
- validação;
- agregação;
- segurança por linha;
- relacionamento principal.

Exemplo ruim:

```text
atividade.dados = {
  "dono": "...",
  "setor": "...",
  "obra": "..."
}
```

Esses dados merecem colunas relacionais.

---

# PARTE R — CONCORRÊNCIA

## 96. Operações críticas

Precisam de transação/controle de concorrência:

- reordenar fila;
- aceitar/recusar prazo;
- concluir tarefa;
- mudar dono;
- alterar autorizações em lote;
- iniciar/finalizar sessões de tempo quando houver restrição de simultaneidade.

---

## 97. Optimistic locking

Pode ser usado com campo:

```text
versao integer
```

em objetos que sofrem edição simultânea.

Não é obrigatório em todas as tabelas.

---

# PARTE S — NOTIFICAÇÕES ASSÍNCRONAS

## 98. Outbox pattern

Pode ser útil futuramente para garantir entrega de eventos como:

- notificação;
- e-mail;
- integração;
- webhook.

Mas não superarquitetar o D0.

Se implementado, criar uma outbox transacional simples.

---

# PARTE T — ANEXOS

## 99. Arquivos

Não guardar binário pesado diretamente nas tabelas de atividade/mensagem.

Usar storage e guardar metadados:

```text
id
organizacao_id
entidade_tipo
entidade_id
caminho
nome_original
mime_type
tamanho
criado_por
criado_em
```

A autorização do anexo segue o objeto de origem.

---

# PARTE U — D0

## 100. Tabelas obrigatórias do D0

### `core`

```text
organizacoes
empresas
usuarios
setores
usuario_setores
```

### `acessos`

```text
grupos_acoes
acoes
perfis
perfil_acoes
escopos
usuario_perfis
usuario_acoes
```

### `cadastros`

```text
obras
centros_custo
```

### `produtividade`

```text
atividades
tarefas
tarefa_executores
tarefa_dependencias
sessoes_tempo
passagens_setor
fila_itens
fila_historico_posicoes
devolucoes
bloqueios
prazos_historico
escalonamentos
escalonamento_destinatarios
escalonamento_eventos
```

### `comunicacao`

```text
conversas
mensagens
participantes
mencoes
notificacoes
```

### `configuracoes`

```text
tipos_atividade
tipos_tarefa
motivos_devolucao
motivos_bloqueio
```

Fluxos, notificações e escalonamentos configuráveis podem entrar gradualmente conforme a primeira versão exigir.

### `auditoria`

```text
eventos
acessos
```

---

## 101. O que pode ficar para depois

- cargo formal, se não for necessário no D0;
- DENY explícito;
- permissões por campo;
- acessos temporários;
- simulação “ver como usuário”;
- modelos sofisticados de fluxo;
- outbox completa;
- materialized views;
- data warehouse;
- vector search;
- embeddings;
- tabelas de IA;
- benchmark entre empresas;
- regras avançadas de aprovação de concessão.

---

# PARTE V — ORDEM DE IMPLEMENTAÇÃO

## 102. Etapa 1 — Tenant e identidade

```text
organizacoes
empresas
usuarios
```

Garantir isolamento antes de criar operação.

---

## 103. Etapa 2 — Setores e segurança

```text
setores
usuario_setores
grupos_acoes
acoes
perfis
perfil_acoes
escopos
usuario_perfis
usuario_acoes
```

Implementar UI simples de marcar/desmarcar e consulta de permissão efetiva.

---

## 104. Etapa 3 — Cadastros de contexto

```text
obras
centros_custo
```

---

## 105. Etapa 4 — Atividades e tarefas

```text
atividades
tarefas
tarefa_executores
```

---

## 106. Etapa 5 — Tempo e movimentações

```text
sessoes_tempo
passagens_setor
dependencias
```

---

## 107. Etapa 6 — Filas

```text
fila_itens
fila_historico_posicoes
```

---

## 108. Etapa 7 — Devoluções, bloqueios e prazos

```text
devolucoes
bloqueios
prazos_historico
```

---

## 109. Etapa 8 — Escalonamento e notificação

```text
escalonamentos
notificacoes
```

---

## 110. Etapa 9 — Comunicação contextual

```text
conversas
mensagens
participantes
mencoes
```

---

## 111. Etapa 10 — Métricas

Criar consultas e views sobre dados já confiáveis.

Não começar pelo dashboard.

---

# PARTE W — TESTES DE ACEITE DO BANCO

## 112. Tenant

- usuário da Organização A não lê registro da Organização B;
- FK não permite cruzar objetos de tenants distintos;
- manipular IDs no frontend não rompe isolamento.

---

## 113. Autorizações

- perfil pode ser criado sem alterar código;
- ações podem ser marcadas/desmarcadas rapidamente;
- usuário pode possuir vários perfis;
- perfil pode ser atribuído em escopos diferentes;
- concessão direta adiciona exceção;
- sem concessão válida, acesso é negado;
- origem da permissão é consultável;
- alteração fica auditada.

---

## 114. Setores

- usuário participa de vários setores;
- participação não concede acesso sozinha;
- setor pode ser inativado sem apagar histórico;
- gestor pode existir sem receber automaticamente todas as ações.

---

## 115. Atividade e tarefa

- uma atividade possui um dono;
- tarefa possui setor responsável;
- tarefa pode ter vários executores;
- atividade pode existir sem obra;
- atividade pode existir sem centro de custo;
- obra e centro de custo podem coexistir.

---

## 116. Tempo

- sessões somam horas-homem corretamente;
- tempo corrido é diferente de horas-homem;
- correção manual fica auditada;
- sessão inválida é bloqueada.

---

## 117. Fila

- posição própria é consultável;
- histórico registra todas as mudanças;
- reordenação é transacional;
- responsável externo não recebe detalhes de outras demandas sem autorização.

---

## 118. Prazo

- prazo solicitado não é sobrescrito silenciosamente;
- prazo comprometido é separado;
- proposta fica registrada;
- aceitação registra responsável e data;
- recusa dispara escalonamento conforme regra.

---

## 119. Comunicação

- conversa está vinculada a atividade/tarefa;
- usuário sem acesso ao objeto não ganha acesso pela mensagem;
- mensagem não altera prazo automaticamente.

---

## 120. Notificações

- mudança de posição gera registro interno correspondente;
- conclusão notifica dono da atividade;
- preferências de canal não apagam histórico obrigatório.

---

# PARTE X — DECISÕES CONSOLIDADAS

## 121. Tenant e estrutura

- organização é tenant;
- usuário pertence a uma organização;
- organização pode possuir várias empresas;
- setores são dinâmicos;
- usuário pode participar de vários setores;
- participação estrutural e autorização são separadas.

---

## 122. Segurança

- ações representam capacidades reais da LPS;
- cliente não cria comportamento inexistente apenas cadastrando uma string;
- perfis são configuráveis;
- ações são marcadas/desmarcadas nos perfis;
- perfil pode ser atribuído em escopo;
- concessões diretas cobrem exceções;
- empresa, setor, obra e centro de custo usam o mesmo motor de escopo;
- D0 trabalha com concessões positivas e negação por padrão;
- origem da permissão é explicável;
- backend e banco validam segurança;
- alterações de segurança são auditadas.

---

## 123. Atividades e tarefas

- atividade é o resultado completo;
- um único dono responde pelo resultado;
- tarefa é passo executável;
- tarefa possui setor responsável;
- tarefa pode ter vários executores;
- atividade atravessa setores por suas tarefas e movimentações.

---

## 124. Fila

- solicitante vê posição exata própria;
- não vê detalhes das demais demandas sem autorização;
- gestor e pessoas autorizadas podem reordenar;
- cada mudança de posição é registrada;
- histórico de posição é fonte para métricas e transparência.

---

## 125. Prazo

- prazo solicitado e comprometido são diferentes;
- executor pode propor novo prazo;
- dono aceita ou recusa;
- recusa gera escalonamento configurado;
- histórico preserva propostas e decisões.

---

## 126. Tempo e auditoria

- medir tempo real é central;
- horas-homem somam sessões individuais;
- espera, fila, bloqueio e trabalho não devem ser confundidos;
- o banco guarda histórico suficiente para reconstruir a trajetória do trabalho.

---

## 127. Comunicação e IA futura

- D0 possui conversa contextual de atividade/tarefa;
- não possui canais livres;
- mensagem não vira mudança oficial sem confirmação estruturada;
- futura inteligência artificial usa dados estruturados e histórico;
- D0 coleta dados, não tenta adivinhar tudo.

---

# PARTE Y — QUESTÕES PENDENTES

## 128. Pontos para implementação decidir

- cargo/função organizacional entra no D0 ou D1;
- modelo exato para múltiplos gestores de setor;
- estrutura final de `escopos` combinados;
- necessidade de escopo por perfil versus escopo por atribuição em cenários avançados;
- necessidade futura de DENY explícito;
- modelo definitivo de cliente/pessoa/fornecedor;
- estratégia de posição de fila;
- política final de simultaneidade de timer;
- mecanismo de autenticação multifator;
- volume que justificará partições/materialized views;
- modelo futuro de analytics/warehouse.

Esses pontos não mudam a arquitetura central.

---

# PARTE Z — RESUMO DA ARQUITETURA

## 129. Estrutura resumida

```text
core.organizacoes
└── core.empresas
└── core.usuarios
└── core.setores
    └── core.usuario_setores

acessos.grupos_acoes
└── acessos.acoes

acessos.perfis
└── acessos.perfil_acoes

acessos.escopos

core.usuarios
├── acessos.usuario_perfis
└── acessos.usuario_acoes

cadastros.obras
cadastros.centros_custo

produtividade.atividades
└── produtividade.tarefas
    ├── produtividade.tarefa_executores
    ├── produtividade.tarefa_dependencias
    ├── produtividade.sessoes_tempo
    └── produtividade.fila_itens

produtividade.passagens_setor
produtividade.fila_historico_posicoes
produtividade.devolucoes
produtividade.bloqueios
produtividade.prazos_historico
produtividade.escalonamentos

comunicacao.conversas
└── comunicacao.mensagens

comunicacao.notificacoes

auditoria.eventos
```

---

## 130. Regra de ouro do banco

> **A LPS deve armazenar fatos com identidade, contexto, tempo e autoria suficientes para operar hoje, auditar amanhã e aprender no futuro.**

---

## 131. Regra de ouro da segurança

> **O cliente configura usuários, setores, perfis e escopos; a LPS mantém o mesmo motor de autorização para todos, sem criar exceções de código por pessoa, setor ou cliente.**

---

## 132. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Estrutura inicial do banco da LPS |
| 2.0 | Revisão da arquitetura de autorizações, consolidação do motor genérico de escopos, UX de perfis/ações e alinhamento com atividades, filas, prazos, comunicação, auditoria e aprendizado futuro |

