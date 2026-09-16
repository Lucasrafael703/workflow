# 08 — Banco de Dados da LPS

> Documento técnico-funcional para traduzir as decisões de produto da LPS em uma estrutura de dados coerente, auditável, multiempresa, segura e preparada para evolução.

---

# 1. Objetivo deste documento

Este documento define a estrutura conceitual do banco de dados da LPS.

Ele deve refletir as decisões já consolidadas nos documentos:

```text
01_VISAO_E_PRINCIPIOS_LPS.md
02_ATIVIDADES_TAREFAS_E_FLUXOS.md
03_FILAS_PRAZOS_E_ESCALONAMENTO.md
04_AUDITORIA_TEMPO_E_METRICAS.md
05_USUARIOS_SETORES_E_AUTORIZACOES.md
06_NOTIFICACOES_E_COMUNICACAO.md
07_INTELIGENCIA_E_RETROALIMENTACAO.md
```

Este documento não deve inventar o produto.

A regra é:

```text
NEGÓCIO
↓
COMPORTAMENTO
↓
DADOS
```

e não:

```text
BANCO
↓
FUNCIONALIDADE INVENTADA
```

---

# 2. Princípios de modelagem

O banco da LPS deve priorizar:

- clareza;
- rastreabilidade;
- isolamento entre organizações;
- integridade;
- histórico;
- simplicidade no D0;
- possibilidade de evolução;
- segurança;
- dados estruturados;
- baixa duplicidade;
- capacidade futura de análise.

---

# 3. Princípio mais importante

> **O banco deve registrar fatos operacionais, e não apenas o estado atual.**

Exemplo insuficiente:

```text
tarefa.status = concluida
```

Exemplo adequado:

```text
status_atual = concluida
+
histórico:
- criada
- entrou na fila
- iniciou
- pausou
- retomou
- devolveu
- voltou
- concluiu
```

O estado atual facilita a operação.

O histórico permite auditoria, métricas e inteligência.

---

# 4. Banco relacional

A LPS deve utilizar PostgreSQL como base relacional.

A modelagem deve aproveitar:

- chaves estrangeiras;
- restrições;
- índices;
- transações;
- RLS;
- JSONB apenas onde realmente fizer sentido;
- timestamps;
- views;
- funções quando necessárias.

Evitar transformar o PostgreSQL em um repositório de JSON sem estrutura.

---

# 5. Identificadores

Padrão recomendado:

```text
UUID
```

para as chaves primárias dos registros principais.

Exemplo:

```text
id uuid primary key
```

Benefícios:

- reduz colisão entre ambientes;
- facilita integrações;
- não expõe sequência simples;
- funciona bem em arquitetura multiempresa.

---

# 6. Organização como limite de segurança

A organização é o principal limite de isolamento da LPS.

Todo dado operacional pertencente a um cliente deve estar relacionado a:

```text
organizacao_id
```

direta ou indiretamente.

Para tabelas críticas e de alto volume, a recomendação é possuir:

```text
organizacao_id NOT NULL
```

explicitamente.

---

# 7. Regra contra cruzamento entre organizações

Nunca deve ser possível relacionar:

```text
atividade da Organização A
```

com:

```text
setor da Organização B
```

A aplicação e o banco precisam impedir isso.

---

# 8. Multiempresa

Dentro de uma organização podem existir várias empresas operacionais.

Estrutura conceitual:

```text
ORGANIZAÇÃO
↓
EMPRESAS
↓
SETORES / OBRAS / CENTROS DE CUSTO / ATIVIDADES
```

A empresa operacional não é o mesmo conceito que a organização da LPS.

---

# 9. Schemas propostos

A estrutura da LPS será dividida em schemas:

```text
core
acessos
cadastros
produtividade
comunicacao
configuracoes
auditoria
```

---

# 10. Responsabilidade de cada schema

## `core`

Estrutura fundamental do tenant:

- organizações;
- empresas;
- usuários;
- setores;
- vínculos estruturais.

## `acessos`

Autorização:

- grupos de ações;
- ações;
- perfis;
- perfil-ações;
- usuário-perfis;
- escopos;
- concessões diretas.

## `cadastros`

Cadastros operacionais de apoio:

- obras;
- centros de custo;
- clientes, quando a modelagem for fechada;
- outros cadastros auxiliares que não pertençam ao motor da LPS.

## `produtividade`

Núcleo operacional:

- atividades;
- tarefas;
- executores;
- dependências;
- sessões de tempo;
- passagens entre setores;
- filas;
- posições;
- devoluções;
- bloqueios;
- prazos;
- escalonamentos.

## `comunicacao`

Comunicação contextual:

- conversas;
- mensagens;
- participantes;
- menções;
- notificações;
- preferências.

## `configuracoes`

Cadastros de comportamento:

- processos;
- versões de processo;
- definições de inputs;
- critérios de aceite;
- tipos;
- motivos;
- modelos de fluxo vinculados à versão do processo;
- regras de escalonamento;
- regras de notificação;
- parâmetros operacionais.

## `auditoria`

Rastro técnico e funcional:

- eventos;
- alterações;
- ações administrativas;
- integrações futuramente.

---

# 11. Convenções gerais de campos

Tabelas mutáveis devem considerar, conforme necessidade:

```text
id
organizacao_id
criado_em
criado_por
atualizado_em
atualizado_por
ativo
```

Nem toda tabela precisa possuir todos esses campos.

Tabelas imutáveis de evento normalmente precisam de:

```text
id
organizacao_id
ocorrido_em
usuario_id
tipo_evento
```

---

# 12. Timestamps

Recomendação técnica:

```text
timestamptz
```

armazenado de forma consistente.

A interface converte para o fuso do usuário ou organização.

---

# 13. Exclusão física

Para dados operacionais com histórico:

> evitar exclusão física.

Preferir:

- cancelar;
- inativar;
- arquivar;
- encerrar.

Exclusão física deve ser restrita a casos específicos.

---

# 14. Campos de status

Os status internos devem possuir códigos estáveis.

Exemplo conceitual:

```text
aberta
em_andamento
bloqueada
concluida
cancelada
```

A lista final ainda não está fechada.

Não definir centenas de status no banco antes da decisão funcional.

---

# 15. Nome interno x nome apresentado

Futuramente:

```text
codigo interno:
em_andamento
```

pode ser exibido como:

```text
Em execução
```

ou outro rótulo configurado.

A lógica não deve depender do texto exibido.

---

# 16. Normalização de nomes

Cadastros como setor devem impedir duplicidade óbvia.

Exemplo:

```text
Financeiro
FINANCEIRO
 financeiro
```

podem utilizar uma coluna ou índice de normalização.

Não aplicar similaridade fuzzy como regra automática.

---

# 17. Schema `core`

---

# 18. `core.organizacoes`

## Finalidade

Representa o tenant principal da LPS.

Exemplos:

```text
Biasi
Instaladora X
```

## Campos principais

| Campo | Tipo conceitual | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| nome | text | Sim | Nome da organização |
| slug | text | Sim | Identificador amigável/técnico |
| ativo | boolean | Sim | Organização ativa |
| criado_em | timestamptz | Sim | Criação |
| atualizado_em | timestamptz | Sim | Última alteração |

## Regras

- `slug` único globalmente;
- organização inativa não deve aceitar operação normal;
- não excluir organização com histórico operacional sem processo próprio.

## Índices

```text
unique(slug)
index(ativo)
```

## Segurança

É a raiz das políticas de RLS.

---

# 19. `core.empresas`

## Finalidade

Representa empresas operacionais dentro da organização.

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | FK organização |
| codigo | text | Não | Código interno |
| razao_social | text | Não | Quando aplicável |
| nome_fantasia | text | Sim | Nome operacional |
| documento | text | Não | CNPJ/identificador |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Criação |
| atualizado_em | timestamptz | Sim | Alteração |

## Relacionamentos

```text
organizacao 1:N empresas
```

## Regras

- empresa sempre pertence a uma organização;
- documento pode ser único dentro da organização quando preenchido;
- inativação preserva histórico.

## Índices

```text
index(organizacao_id)
unique(organizacao_id, codigo) where codigo is not null
index(organizacao_id, ativo)
```

## Observação

Uma mesma entidade jurídica pode futuramente assumir também papel de cliente.

A modelagem genérica de entidades/papéis ainda não foi fechada e não deve ser inventada neste documento.

---

# 20. `core.usuarios`

## Finalidade

Representa usuários da organização.

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK interno |
| organizacao_id | uuid | Sim | FK organização |
| auth_user_id | uuid | Sim | Identidade do provedor de autenticação |
| nome | text | Sim | Nome exibido |
| email | text | Sim | Login/contato |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Criação |
| atualizado_em | timestamptz | Sim | Alteração |

## Regras

- usuário pertence a uma única organização;
- `auth_user_id` único;
- usuário inativo preserva histórico;
- e-mail deve ser único dentro da política adotada.

## Índices

```text
unique(auth_user_id)
index(organizacao_id, ativo)
index(organizacao_id, email)
```

## Segurança

O `auth_user_id` será usado para identificar o usuário autenticado nas políticas de segurança.

---

# 21. `core.setores`

## Finalidade

Representa os setores configuráveis da empresa.

Exemplos:

```text
Comercial
Financeiro
Almoxarifado
Engenharia
```

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| empresa_id | uuid | Sim no D0 | Empresa operacional |
| nome | text | Sim | Nome |
| nome_normalizado | text | Sim | Controle de duplicidade |
| codigo | text | Não | Código opcional |
| ativo | boolean | Sim | Situação |
| criado_em | timestamptz | Sim | Criação |
| criado_por | uuid | Sim | Usuário |
| atualizado_em | timestamptz | Sim | Alteração |

## Regras

- setor é cadastro;
- setor não é fixo no código;
- duplicidade normalizada deve ser impedida dentro da empresa;
- setores parecidos não são automaticamente duplicados;
- inativação preserva histórico.

## Índices

```text
unique(organizacao_id, empresa_id, nome_normalizado)
index(organizacao_id, empresa_id, ativo)
```

## Segurança

Criação e edição dependem de ações como:

```text
setor.criar
setor.editar
setor.inativar
```

---

# 22. `core.usuario_setores`

## Finalidade

Representa participação operacional de usuários nos setores.

Não representa autorização completa.

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| usuario_id | uuid | Sim | FK usuário |
| setor_id | uuid | Sim | FK setor |
| eh_principal | boolean | Sim | Setor principal |
| eh_gestor | boolean | Sim | Papel estrutural |
| ativo | boolean | Sim | Vínculo atual |
| entrou_em | timestamptz | Sim | Início |
| saiu_em | timestamptz | Não | Fim |

## Regras

- usuário pode pertencer a vários setores;
- um usuário pode possuir no máximo um setor principal ativo por empresa, se essa regra for adotada;
- `eh_gestor` não concede autorização automaticamente;
- histórico do vínculo precisa ser preservado.

## Índices

```text
index(organizacao_id, usuario_id)
index(organizacao_id, setor_id, ativo)
```

---

# 23. Regra importante sobre `usuario_setores`

```text
PARTICIPAÇÃO
≠
AUTORIZAÇÃO
```

Exemplo:

```text
Paulo participa do Comercial.
```

Mas pode visualizar Administrativo por perfil/escopo.

Não adicionar Paulo ao Administrativo apenas para liberar acesso.

---

# 24. Schema `acessos`

---

# 25. Objetivo do schema `acessos`

Permitir que a LPS responda:

> Usuário X pode executar ação Y sobre objeto Z?

Modelo conceitual:

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

# 26. `acessos.grupos_acoes`

## Finalidade

Organiza ações em grupos amigáveis.

Exemplos:

```text
Gestão de Atividades
Gestão de Tarefas
Filas
Cadastros
Segurança
Auditoria
```

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| codigo | text | Sim |
| nome | text | Sim |
| descricao | text | Não |
| ordem | integer | Sim |
| ativo | boolean | Sim |

## Regras

- grupo organiza;
- grupo não concede acesso;
- código é estável.

## Índices

```text
unique(codigo)
index(ativo, ordem)
```

---

# 27. `acessos.acoes`

## Finalidade

Representa capacidades reais da LPS.

Exemplos:

```text
atividade.visualizar
atividade.criar
tarefa.devolver
fila.reordenar
setor.criar
```

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| grupo_id | uuid | Sim |
| codigo | text | Sim |
| nome | text | Sim |
| descricao | text | Não |
| ativo | boolean | Sim |

## Regras

- `codigo` único;
- novas ações começam negadas por padrão;
- não vincular a botão específico;
- ação deve representar capacidade de negócio.

## Índices

```text
unique(codigo)
index(grupo_id, ativo)
```

---

# 28. `acessos.perfis`

## Finalidade

Agrupa ações reutilizáveis.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| nome | text | Sim |
| descricao | text | Não |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

## Regras

- perfil pertence à organização;
- perfil não é cargo;
- perfil não é setor;
- perfil inativo preserva histórico.

## Índices

```text
unique(organizacao_id, nome)
index(organizacao_id, ativo)
```

---

# 29. `acessos.perfil_acoes`

## Finalidade

Relaciona perfis às ações permitidas.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| perfil_id | uuid | Sim |
| acao_id | uuid | Sim |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

## Chave

```text
primary key(perfil_id, acao_id)
```

## Regra

O perfil define:

> o que pode fazer.

O escopo será definido no vínculo do usuário com o perfil.

---

# 30. `acessos.escopos`

## Finalidade

Define onde determinada concessão é válida.

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| tipo | text | Sim | Tipo do escopo |
| empresa_id | uuid | Não | Empresa |
| setor_id | uuid | Não | Setor |
| obra_id | uuid | Não | Obra |
| centro_custo_id | uuid | Não | Centro de custo |
| relacao | text | Não | Ex.: próprias, atribuídas |
| descricao | text | Não | Leitura humana |
| ativo | boolean | Sim | Situação |

## Tipos conceituais possíveis

```text
organizacao
empresa
setor
obra
centro_custo
relacional
combinado
```

## Regras

- escopo nunca cruza organização;
- campos aplicáveis dependem do tipo;
- não criar escopos genéricos sem necessidade;
- escopo precisa ser explicável.

---

# 31. Escopos relacionais

Alguns acessos dependem da relação do usuário com o objeto.

Exemplos:

```text
atividades das quais sou dono
tarefas atribuídas a mim
setores dos quais participo
setores que gerencio
```

Esses casos podem ser representados por:

```text
relacao
```

ou regra interna vinculada ao escopo.

A implementação final deve privilegiar clareza.

---

# 32. `acessos.usuario_perfis`

## Finalidade

Atribui um perfil a um usuário dentro de determinado escopo.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| usuario_id | uuid | Sim |
| perfil_id | uuid | Sim |
| escopo_id | uuid | Sim |
| ativo | boolean | Sim |
| valido_de | timestamptz | Não |
| valido_ate | timestamptz | Não |
| criado_em | timestamptz | Sim |
| criado_por | uuid | Sim |

## Exemplo

```text
Paulo
Perfil: Gestor Comercial
Escopo: Setor Comercial
```

Outro vínculo:

```text
Paulo
Perfil: Visualizador
Escopo: Setor Administrativo
```

Isso evita criar perfis extremamente específicos.

## Índices

```text
index(organizacao_id, usuario_id, ativo)
index(perfil_id, ativo)
index(escopo_id, ativo)
```

---

# 33. `acessos.usuario_acoes`

## Finalidade

Concessões diretas excepcionais.

## Campos principais

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

## Regra

Usar apenas para exceções.

Se muitas pessoas precisam da mesma concessão:

> criar ou ajustar perfil.

---

# 34. Avaliação conceitual da autorização

```text
1. usuário ativo?
2. mesma organização?
3. possui ação por perfil ou concessão direta?
4. objeto está dentro do escopo?
5. regra de negócio permite ação no estado atual?
```

Resultado:

```text
PERMITIR
```

ou:

```text
NEGAR
```

---

# 35. RLS

RLS significa:

**Row Level Security — Segurança em Nível de Linha.**

Deve ser utilizada como última barreira no PostgreSQL/Supabase.

Objetivos:

- impedir acesso entre organizações;
- limitar registros ao escopo autorizado;
- proteger dados mesmo se o front-end falhar.

---

# 36. A interface não é a barreira principal

Ocultar:

```text
botão Reordenar
```

é UX.

A segurança precisa existir também em:

```text
API
Banco
```

---

# 37. Schema `cadastros`

---

# 38. `cadastros.obras`

## Finalidade

Representa obras utilizadas no contexto operacional.

Decisão consolidada:

> obras e centros de custo serão tabelas separadas.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| empresa_id | uuid | Sim |
| codigo | text | Não |
| nome | text | Sim |
| cliente_id | uuid | Não |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |
| atualizado_em | timestamptz | Sim |

## Regras

- obra pertence a uma empresa;
- atividade pode existir sem obra;
- obra inativa preserva histórico.

## Índices

```text
index(organizacao_id, empresa_id, ativo)
unique(organizacao_id, empresa_id, codigo) where codigo is not null
```

---

# 39. `cadastros.centros_custo`

## Finalidade

Representa centros de custo.

Pode existir:

```text
centro de custo independente
```

ou:

```text
centro de custo associado a obra
```

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| empresa_id | uuid | Sim |
| obra_id | uuid | Não |
| codigo | text | Não |
| nome | text | Sim |
| ativo | boolean | Sim |
| criado_em | timestamptz | Sim |

## Regras

- centro de custo pode ou não estar associado a obra;
- atividade pode vincular obra e centro de custo simultaneamente;
- centro de custo não é obrigatório para toda atividade.

## Índices

```text
index(organizacao_id, empresa_id, ativo)
index(obra_id)
unique(organizacao_id, empresa_id, codigo) where codigo is not null
```

---

# 40. Cliente

A modelagem definitiva de cliente ainda não está fechada.

Existe requisito já conhecido:

> uma entidade pode ser empresa operacional e também cliente.

Por isso, evitar fechar rapidamente uma tabela que force duplicação conceitual.

No D0, as opções técnicas a avaliar são:

```text
A. cadastros.clientes separado
B. entidade genérica + papéis
C. empresa podendo ser referenciada também como cliente
```

A decisão deve ser tomada quando o cadastro de clientes entrar efetivamente no escopo técnico.

---

# 41. Área de negócio

Decisão consolidada:

```text
fora do D0.
```

Não criar tabela agora.

---

# 42. Departamentos

Decisão consolidada:

```text
não criar agora.
```

Setor atende o núcleo atual.

---

# 43. Schema `produtividade`

Este é o principal schema operacional da LPS.

---

# 44. `produtividade.atividades`

## Finalidade

Representa o resultado/problema que precisa ser acompanhado até resolução.

## Campos principais

| Campo | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| id | uuid | Sim | PK |
| organizacao_id | uuid | Sim | Tenant |
| empresa_id | uuid | Sim | Empresa |
| tipo_atividade_id | uuid | Não | Classificação configurável |
| processo_versao_id | uuid | Não | Versão imutável do processo aplicada |
| titulo | text | Sim | Resultado resumido |
| descricao | text | Não | Contexto |
| dono_usuario_id | uuid | Sim | Único dono |
| criado_por | uuid | Sim | Autor |
| obra_id | uuid | Não | Opcional |
| centro_custo_id | uuid | Não | Opcional |
| status | text | Sim | Código interno |
| prazo_solicitado | timestamptz | Não | Necessidade |
| prazo_comprometido | timestamptz | Não | Compromisso atual |
| primeira_acao_em | timestamptz | Não | Cache/derivável |
| concluida_em | timestamptz | Não | Conclusão |
| cancelada_em | timestamptz | Não | Cancelamento |
| criado_em | timestamptz | Sim | Criação |
| atualizado_em | timestamptz | Sim | Alteração |

## Regras

- exatamente um dono ativo;
- obra opcional;
- centro de custo opcional;
- obra e centro de custo podem coexistir;
- atividade pode existir sem obra;
- atividade pode existir sem processo no D0;
- quando `processo_versao_id` estiver preenchido, deve pertencer à mesma organização/empresa permitida;
- processo publicado não é alterado retroativamente;
- conclusão não depende apenas de todas as tarefas; quando houver processo, critérios obrigatórios e evidência configurada também precisam ser considerados;
- `prazo_solicitado` e `prazo_comprometido` são conceitos diferentes.

## Índices

```text
index(organizacao_id, empresa_id, status)
index(organizacao_id, dono_usuario_id, status)
index(organizacao_id, prazo_comprometido)
index(obra_id)
index(centro_custo_id)
index(tipo_atividade_id, status)
index(processo_versao_id, status)
```

## Segurança

RLS considera:

- organização;
- empresa;
- dono;
- escopos;
- permissões.

---

# 44.1 `produtividade.atividade_inputs`

## Finalidade

Armazena os valores dos inputs de uma execução de processo.

## Campos conceituais

```text
id
organizacao_id
atividade_id
processo_input_id
valor_jsonb
preenchido_por
preenchido_em
atualizado_em
```

`valor_jsonb` é aceitável neste ponto porque o valor varia conforme o tipo do input. A definição do input continua relacional e estruturada.

Arquivos não devem ser armazenados como binário nesta coluna; o valor referencia o mecanismo de anexos/armazenamento adotado.

## Regra

Um input obrigatório não precisa impedir a criação da atividade.

Ele pode impedir o início do fluxo do processo até ser preenchido.

---

# 44.2 `produtividade.atividade_outputs`

## Finalidade

Registra a entrega efetivamente produzida pela atividade quando ela utiliza processo.

## Campos conceituais

```text
id
organizacao_id
atividade_id unique
texto_resultado nullable
evidencia_jsonb nullable
registrado_por
registrado_em
atualizado_em
```

A definição do output esperado pertence à versão do processo.

Esta tabela registra a evidência ou confirmação da execução real.

---

# 44.3 `produtividade.atividade_criterios_aceite`

## Finalidade

Representa o estado dos critérios de aceite durante uma atividade.

## Campos conceituais

```text
id
organizacao_id
atividade_id
processo_criterio_id
atendido
atendido_por
atendido_em
evidencia_jsonb nullable
```

## Regras

- um critério obrigatório não atendido bloqueia a conclusão da atividade estruturada;
- alteração deve gerar auditoria;
- desmarcar critério já atendido também deve gerar evento;
- o critério referencia definição imutável da versão do processo.

---

# 45. Histórico de dono

Não confiar apenas em:

```text
dono_usuario_id
```

A mudança de dono precisa ser registrada em auditoria.

Se necessário para consultas frequentes, poderá existir tabela específica futura.

---

# 46. `produtividade.tarefas`

## Finalidade

Representa unidades de trabalho dentro da atividade.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Sim |
| tipo_tarefa_id | uuid | Não |
| titulo | text | Sim |
| descricao | text | Não |
| setor_atual_id | uuid | Não |
| status | text | Sim |
| ordem_fluxo | numeric | Não |
| prazo_solicitado | timestamptz | Não |
| prazo_comprometido | timestamptz | Não |
| criada_por | uuid | Sim |
| criada_em | timestamptz | Sim |
| primeira_acao_em | timestamptz | Não |
| iniciada_em | timestamptz | Não |
| concluida_em | timestamptz | Não |
| cancelada_em | timestamptz | Não |
| atualizado_em | timestamptz | Sim |

## Regras

- tarefa pertence a uma única atividade;
- pode nascer sem executor;
- pode possuir vários executores;
- pode mudar de setor;
- `setor_atual_id` representa fotografia atual;
- histórico de setores fica em tabela própria;
- tarefa concluída não conclui automaticamente a atividade;
- ordem pode mudar com auditoria.

## Índices

```text
index(organizacao_id, atividade_id)
index(organizacao_id, setor_atual_id, status)
index(organizacao_id, prazo_comprometido)
index(tipo_tarefa_id)
```

---

# 47. `produtividade.tarefa_executores`

## Finalidade

Relaciona 0..N executores a uma tarefa.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| usuario_id | uuid | Sim |
| atribuido_por | uuid | Sim |
| atribuido_em | timestamptz | Sim |
| removido_em | timestamptz | Não |
| ativo | boolean | Sim |

## Regras

- múltiplos executores permitidos;
- remoção não apaga histórico;
- executor inativo permanece associado historicamente.

## Índices

```text
index(tarefa_id, ativo)
index(usuario_id, ativo)
unique(tarefa_id, usuario_id) where ativo = true
```

---

# 48. `produtividade.tarefa_dependencias`

## Finalidade

Representa dependências entre tarefas.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Sim |
| tarefa_predecessora_id | uuid | Sim |
| tarefa_sucessora_id | uuid | Sim |
| tipo | text | Sim |
| criada_em | timestamptz | Sim |
| criada_por | uuid | Sim |

## D0

Tipo inicial:

```text
fim_para_inicio
```

ou equivalente.

## Regras

- ambas as tarefas precisam pertencer à mesma atividade no D0;
- impedir auto-dependência;
- impedir duplicidade;
- ciclos devem ser validados.

## Índices

```text
index(tarefa_predecessora_id)
index(tarefa_sucessora_id)
unique(tarefa_predecessora_id, tarefa_sucessora_id)
```

---

# 49. `produtividade.sessoes_tempo`

## Finalidade

Registra períodos efetivos de trabalho de cada executor.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| usuario_id | uuid | Sim |
| setor_id | uuid | Não |
| inicio_em | timestamptz | Sim |
| fim_em | timestamptz | Não |
| origem | text | Sim |
| lancada_em | timestamptz | Sim |
| lancada_por | uuid | Sim |
| observacao | text | Não |

## `origem`

Exemplos:

```text
timer
manual
importacao
```

## Regras

- uma pessoa não deve possuir duas sessões ativas simultâneas no D0;
- iniciar nova tarefa pode encerrar/pausar a sessão anterior;
- lançamento manual precisa ser distinguível;
- correções precisam de auditoria;
- fim nunca pode ser anterior ao início.

## Índices

```text
index(organizacao_id, usuario_id, inicio_em)
index(tarefa_id, inicio_em)
unique(usuario_id) where fim_em is null
```

---

# 50. Horas-homem

Não precisa ser armazenado como valor principal.

Pode ser derivado:

```text
SUM(fim_em - inicio_em)
```

por:

- tarefa;
- atividade;
- usuário;
- setor.

---

# 51. `produtividade.passagens_setor`

## Finalidade

Registra cada passagem de uma tarefa por um setor.

Esse histórico é essencial para medir permanência e retornos.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| setor_id | uuid | Sim |
| entrada_em | timestamptz | Sim |
| saida_em | timestamptz | Não |
| entrada_por | uuid | Sim |
| saida_por | uuid | Não |
| tipo_saida | text | Não |
| ordem_passagem | integer | Sim |

## Exemplo

```text
Engenharia — passagem 1
Compras — passagem 2
Engenharia — passagem 3
Compras — passagem 4
```

## Regras

- uma tarefa pode passar várias vezes pelo mesmo setor;
- cada passagem é independente;
- `tarefas.setor_atual_id` deve corresponder à passagem aberta atual;
- no máximo uma passagem ativa por tarefa.

## Índices

```text
index(tarefa_id, ordem_passagem)
index(setor_id, entrada_em)
unique(tarefa_id) where saida_em is null
```

---

# 52. `produtividade.fila_itens`

## Finalidade

Representa a presença atual de uma tarefa na fila operacional de um setor.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| setor_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| ordem | numeric | Sim |
| entrou_em | timestamptz | Sim |
| saiu_em | timestamptz | Não |
| estado | text | Sim |
| inserido_por | uuid | Não |

## Observação importante

A coluna:

```text
ordem
```

define ordenação.

A posição exibida:

```text
4 de 17
```

pode ser calculada com:

```text
row_number()
```

sobre os itens ativos.

Isso evita depender de renumerar todos os registros a cada alteração.

## Regras

- no máximo uma entrada ativa por tarefa/setor naquele momento;
- fila é por setor;
- tarefa bloqueada pode futuramente ter tratamento específico;
- posição exata é derivada da ordem.

## Índices

```text
index(organizacao_id, setor_id, estado, ordem)
unique(tarefa_id) where saiu_em is null
```

---

# 53. `produtividade.fila_historico_posicoes`

## Finalidade

Registra mudanças de posição percebidas pelo usuário.

Necessário para:

- auditoria;
- notificações;
- análise.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| setor_id | uuid | Sim |
| posicao_anterior | integer | Não |
| posicao_nova | integer | Sim |
| total_anterior | integer | Não |
| total_novo | integer | Sim |
| causa | text | Sim |
| alterado_por | uuid | Não |
| ocorrido_em | timestamptz | Sim |

## `causa`

Exemplos:

```text
reordenacao_manual
entrada_prioritaria
conclusao_item_anterior
entrada_nova_tarefa
cancelamento
mudanca_setor
```

## Regras

- mudanças precisam ser rastreáveis;
- `alterado_por` pode ser nulo em mudança automática;
- histórico alimenta notificações.

## Índices

```text
index(tarefa_id, ocorrido_em)
index(setor_id, ocorrido_em)
```

---

# 54. Reordenação da fila

A alteração de `ordem` precisa ocorrer em transação.

A mesma transação deve:

- alterar ordem;
- identificar tarefas afetadas;
- registrar histórico;
- gerar evento de auditoria;
- gerar notificações quando aplicável.

---

# 55. `produtividade.devolucoes`

## Finalidade

Registra devoluções formais de tarefas.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| setor_origem_id | uuid | Sim |
| setor_destino_id | uuid | Sim |
| motivo_devolucao_id | uuid | Sim |
| observacao | text | Não |
| devolvido_por | uuid | Sim |
| devolvido_em | timestamptz | Sim |
| resolvida_em | timestamptz | Não |
| retorno_origem_em | timestamptz | Não |

## Regras

- motivo obrigatório;
- devolução não apaga fluxo anterior;
- deve existir movimentação correspondente;
- permite medir tempo de correção.

## Índices

```text
index(tarefa_id, devolvido_em)
index(motivo_devolucao_id, devolvido_em)
index(setor_origem_id, setor_destino_id)
```

---

# 56. `produtividade.bloqueios`

## Finalidade

Registra períodos em que uma tarefa não consegue avançar.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| tarefa_id | uuid | Sim |
| motivo_bloqueio_id | uuid | Sim |
| observacao | text | Não |
| iniciado_em | timestamptz | Sim |
| encerrado_em | timestamptz | Não |
| iniciado_por | uuid | Sim |
| encerrado_por | uuid | Não |

## Regras

- permitir múltiplos bloqueios ao longo do tempo;
- bloquear não elimina responsabilidade;
- motivo estruturado;
- períodos alimentam métricas.

## Índices

```text
index(tarefa_id, iniciado_em)
index(motivo_bloqueio_id)
```

---

# 57. `produtividade.prazos_historico`

## Finalidade

Preserva histórico de prazo solicitado, proposto e comprometido.

Pode se aplicar a:

- atividade;
- tarefa.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Não |
| tarefa_id | uuid | Não |
| tipo | text | Sim |
| prazo_anterior | timestamptz | Não |
| prazo_novo | timestamptz | Sim |
| status_proposta | text | Não |
| proposto_por | uuid | Não |
| decidido_por | uuid | Não |
| ocorrido_em | timestamptz | Sim |
| decidido_em | timestamptz | Não |
| motivo | text | Não |

## Regra de integridade

Exatamente um:

```text
atividade_id
```

ou:

```text
tarefa_id
```

deve estar preenchido.

## `tipo`

Exemplos:

```text
solicitado
proposto
comprometido
alteracao_direta
```

## `status_proposta`

Exemplos:

```text
pendente
aceita
recusada
```

## Regras

- prazo anterior nunca é apagado;
- proposta não altera compromisso antes de aceite;
- recusa pode gerar escalonamento.

## Índices

```text
index(atividade_id, ocorrido_em)
index(tarefa_id, ocorrido_em)
index(status_proposta) where status_proposta = 'pendente'
```

---

# 58. Prazo atual

Para performance operacional:

```text
atividades.prazo_solicitado
atividades.prazo_comprometido
tarefas.prazo_solicitado
tarefas.prazo_comprometido
```

guardam o estado atual.

`prazos_historico` explica como chegou ali.

---

# 59. `produtividade.escalonamentos`

## Finalidade

Representa conflitos ou situações que subiram para decisão.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Sim |
| tarefa_id | uuid | Não |
| motivo | text | Sim |
| regra_escalonamento_id | uuid | Não |
| nivel_atual | integer | Sim |
| status | text | Sim |
| aberto_em | timestamptz | Sim |
| aberto_por | uuid | Não |
| resolvido_em | timestamptz | Não |
| resolvido_por | uuid | Não |
| decisao | text | Não |

## Regras

- atividade obrigatória;
- tarefa opcional;
- precisa gerar decisão;
- histórico não desaparece.

## Índices

```text
index(organizacao_id, status, aberto_em)
index(atividade_id)
index(tarefa_id)
```

---

# 60. `produtividade.escalonamento_destinatarios`

## Finalidade

Permite vários destinatários por escalonamento.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| escalonamento_id | uuid | Sim |
| usuario_id | uuid | Sim |
| nivel | integer | Sim |
| notificado_em | timestamptz | Não |
| ciencia_em | timestamptz | Não |

## Chave

```text
primary key(escalonamento_id, usuario_id, nivel)
```

---

# 61. `produtividade.escalonamento_eventos`

## Finalidade

Registra evolução do escalonamento.

Exemplos:

```text
aberto
subiu_nivel
comentario
decisao
resolvido
```

## Campos principais

```text
id
organizacao_id
escalonamento_id
tipo
dados
usuario_id
ocorrido_em
```

`dados` pode ser JSONB porque o formato varia conforme o evento.

---

# 62. Aprovações

Não criar um módulo completo de aprovações antes da necessidade.

Quando aparecer necessidade real, poderá existir:

```text
produtividade.aprovacoes
```

Mas não é obrigatório no D0 atual.

---

# 63. Schema `comunicacao`

---

# 64. `comunicacao.conversas`

## Finalidade

Representa conversa contextual da atividade ou tarefa.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| atividade_id | uuid | Não |
| tarefa_id | uuid | Não |
| criada_em | timestamptz | Sim |
| ativa | boolean | Sim |

## Regra

Exatamente um contexto:

```text
atividade
```

ou:

```text
tarefa
```

## Unicidade

Uma atividade pode ter uma conversa principal.

Uma tarefa pode ter uma conversa principal.

## Índices

```text
unique(atividade_id) where atividade_id is not null
unique(tarefa_id) where tarefa_id is not null
```

---

# 65. `comunicacao.mensagens`

## Finalidade

Armazena mensagens da conversa.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| conversa_id | uuid | Sim |
| autor_usuario_id | uuid | Não |
| tipo_autor | text | Sim |
| conteudo | text | Sim |
| criada_em | timestamptz | Sim |
| editada_em | timestamptz | Não |
| removida_em | timestamptz | Não |

## `tipo_autor`

Exemplos:

```text
usuario
sistema
```

## Regras

- mensagem não altera estado oficial automaticamente;
- remoção física deve ser evitada;
- autoria preservada.

## Índices

```text
index(conversa_id, criada_em)
index(autor_usuario_id, criada_em)
```

---

# 66. `comunicacao.participantes`

## Finalidade

Controla participantes explícitos da conversa quando necessário.

## Campos principais

```text
conversa_id
usuario_id
adicionado_em
adicionado_por
removido_em
```

## Observação

Acesso continua dependente de autorização.

Ser participante não deve burlar RLS.

---

# 67. `comunicacao.mencoes`

## Finalidade

Registra menções em mensagens.

## Campos principais

```text
id
organizacao_id
mensagem_id
usuario_mencionado_id
criada_em
```

## Regra

Menção válida pode gerar notificação.

---

# 68. `comunicacao.notificacoes`

## Finalidade

Representa notificações lógicas dentro da LPS.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| usuario_id | uuid | Sim |
| tipo_evento | text | Sim |
| atividade_id | uuid | Não |
| tarefa_id | uuid | Não |
| evento_auditoria_id | uuid | Não |
| titulo | text | Sim |
| resumo | text | Não |
| requer_acao | boolean | Sim |
| criada_em | timestamptz | Sim |
| lida_em | timestamptz | Não |
| arquivada_em | timestamptz | Não |

## Regras

- notificação não é fonte oficial do evento;
- aponta para atividade/tarefa/evento de origem;
- evento continua existindo mesmo se notificação for arquivada.

## Índices

```text
index(organizacao_id, usuario_id, lida_em, criada_em)
index(tipo_evento, criada_em)
```

---

# 69. `comunicacao.preferencias_notificacao`

## Finalidade

Armazena preferências opcionais do usuário.

## Campos principais

```text
id
organizacao_id
usuario_id
tipo_evento
canal
habilitado
atualizado_em
```

## Regras

- regras obrigatórias da organização prevalecem;
- preferência não apaga evento;
- canal interno da LPS pode permanecer sempre disponível.

---

# 70. Entregas por canal

Pode existir futuramente:

```text
comunicacao.entregas_notificacao
```

para:

- push;
- e-mail;
- integrações.

Não é necessário no D0 se a central interna for suficiente.

---

# 71. Schema `configuracoes`

---

# 72. Princípio do schema `configuracoes`

O que varia entre empresas deve ser cadastro/configuração quando fizer sentido.

O que define a identidade da LPS não deve ser completamente redefinido.

---

# 73. `configuracoes.tipos_atividade`

## Finalidade

Classifica atividades para comparação, fluxo e inteligência.

## Campos principais

```text
id
organizacao_id
empresa_id nullable
codigo
nome
descricao
ativo
```

## Regras

- evitar duplicidade;
- governança importante para inteligência;
- usuário comum não precisa criar tipos livremente.

---

# 74. `configuracoes.tipos_tarefa`

## Finalidade

Classifica tarefas.

Campos semelhantes a `tipos_atividade`.

Ajuda a comparar tarefas equivalentes.

---

# 75. `configuracoes.motivos_devolucao`

## Finalidade

Padroniza os motivos de devolução.

## Campos principais

```text
id
organizacao_id
codigo
nome
descricao
ativo
```

## Exemplos

```text
informacao_incompleta
especificacao_incorreta
documento_ausente
escopo_divergente
```

---

# 76. `configuracoes.motivos_bloqueio`

## Finalidade

Padroniza bloqueios.

Exemplos:

```text
aguardando_cliente
aguardando_fornecedor
aguardando_aprovacao
aguardando_documento
aguardando_decisao
```

---

# 77. Processos e versões

Processo passa a ser um conceito configurável de primeira classe.

## 77.1 `configuracoes.processos`

### Finalidade

Representa a identidade estável do processo.

Exemplos:

```text
Elaborar orçamento
Solicitação de compra
Admissão de colaborador
```

### Campos principais

```text
id
organizacao_id
empresa_id
tipo_atividade_id nullable
nome
descricao
ativo
criado_em
criado_por
atualizado_em
atualizado_por
```

### Regras

- processo pertence a uma organização;
- no D0, processo pertence a uma empresa para que setores do fluxo sejam consistentes;
- processo compartilhado entre várias empresas exige futura camada de mapeamento e não entra no D0;
- tipo de atividade é classificação opcional;
- inativar processo não altera atividades antigas.

## 77.2 `configuracoes.processo_versoes`

### Finalidade

Representa uma versão publicável e imutável do processo.

### Campos principais

```text
id
organizacao_id
processo_id
versao
status
output_titulo
output_descricao
output_tipo_evidencia
criado_em
criado_por
publicado_em nullable
publicado_por nullable
```

### Status mínimos

```text
rascunho
publicada
substituida
```

### Regras

- somente rascunho pode ser editado;
- publicar congela a definição;
- deve existir no máximo uma versão `publicada` atual por processo;
- ao publicar nova versão, a anterior passa para `substituida`;
- editar processo publicado cria nova versão rascunho;
- atividades guardam `processo_versao_id`;
- versão antiga nunca é reescrita para refletir versão nova.

## 77.3 `configuracoes.processo_inputs`

### Finalidade

Define os dados e arquivos necessários para iniciar a execução.

### Campos principais

```text
id
organizacao_id
processo_versao_id
nome
tipo
obrigatorio
origem nullable
ajuda_preenchimento nullable
ordem
```

### Tipos iniciais recomendados

```text
texto_curto
texto_longo
numero
data
arquivo
link
selecao
```

Evitar construtor de formulário completo no D0.

## 77.4 Output do processo

No D0 existe um output principal por versão.

Por simplicidade, sua definição fica em `processo_versoes`:

```text
output_titulo
output_descricao
output_tipo_evidencia
```

Se o produto comprovar necessidade de múltiplos outputs independentes, uma tabela própria pode ser criada depois.

## 77.5 `configuracoes.processo_criterios_aceite`

### Finalidade

Define como a LPS sabe que o output está realmente pronto.

### Campos principais

```text
id
organizacao_id
processo_versao_id
nome
obrigatorio
tipo_validacao
ordem
```

### D0

Tipos mínimos:

```text
checklist
evidencia
```

Não construir motor avançado de fórmulas ou condições no D0.

---

# 78. `configuracoes.fluxos_modelo`

## Finalidade

Representa o fluxo padrão de uma versão de processo.

## Campos principais

```text
id
organizacao_id
processo_versao_id
nome
descricao
criado_em
criado_por
```

## Regras

- no D0, uma versão de processo possui no máximo um fluxo padrão;
- setores referenciados pelo fluxo precisam pertencer à empresa do processo;
- não precisa de editor BPMN — Business Process Model and Notation, ou Notação e Modelagem de Processos de Negócio — completo;
- fluxo padrão não substitui o histórico real.

---

# 79. `configuracoes.fluxo_tarefas_modelo`

## Finalidade

Define tarefas padrão do processo.

## Campos principais

```text
id
organizacao_id
fluxo_modelo_id
tipo_tarefa_id nullable
titulo_padrao
setor_id nullable
ordem
obrigatoria
```

## Regra

Modelo não gera histórico operacional.

Ao aplicar o processo:

```text
criar tarefas reais em produtividade.tarefas
```

---

# 80. `configuracoes.fluxo_dependencias_modelo`

## Finalidade

Define dependências padrão entre tarefas do processo.

Campos:

```text
id
fluxo_modelo_id
tarefa_modelo_predecessora_id
tarefa_modelo_sucessora_id
tipo
```

No D0, dependências simples são suficientes.

## Aplicação do processo

Ao criar atividade com processo, a aplicação deve ocorrer de forma transacional:

```text
atividade criada
↓
processo_versao_id registrado
↓
inputs da execução preparados
↓
tarefas reais criadas
↓
dependências reais criadas
↓
critérios de aceite da execução preparados
↓
output esperado fica disponível para consulta
↓
auditoria registra processo aplicado
```

Se qualquer etapa crítica falhar, a operação não deve deixar uma atividade parcialmente instanciada.

---

# 81. `configuracoes.regras_notificacao`

## Finalidade

Define regras corporativas de notificação.

## Campos conceituais

```text
id
organizacao_id
tipo_evento
obrigatoria
destinatario_tipo
canal
condicoes
ativo
```

## `condicoes`

Pode usar JSONB para regras variáveis.

Exemplo:

```json
{
  "apenas_se_dono": true
}
```

JSONB aqui é aceitável porque regras podem evoluir.

---

# 82. `configuracoes.regras_escalonamento`

## Finalidade

Define quando e para quem escalar.

## Campos conceituais

```text
id
organizacao_id
nome
evento_disparador
nivel
destinatario_tipo
condicoes
ativo
```

## Exemplos de disparador

```text
prazo_recusado
prazo_vencido
bloqueio_prolongado
```

No D0, começar com poucos disparadores.

---

# 83. Configuração de status

Não criar uma tabela complexa antes de definir catálogo interno.

Futuramente pode existir:

```text
configuracoes.rotulos_status
```

para personalizar exibição.

O estado interno precisa permanecer estável.

---

# 84. Schema `auditoria`

---

# 85. Objetivo do schema `auditoria`

Registrar mudanças relevantes de forma genérica.

Ele não substitui históricos específicos de domínio.

Exemplo:

```text
produtividade.devolucoes
```

é dado de negócio.

```text
auditoria.eventos
```

registra que a devolução aconteceu e quem realizou.

---

# 86. `auditoria.eventos`

## Finalidade

Registro imutável de eventos relevantes.

## Campos principais

| Campo | Tipo | Obrigatório |
|---|---|---:|
| id | uuid | Sim |
| organizacao_id | uuid | Sim |
| usuario_id | uuid | Não |
| tipo_evento | text | Sim |
| entidade_tipo | text | Sim |
| entidade_id | uuid | Sim |
| atividade_id | uuid | Não |
| tarefa_id | uuid | Não |
| dados_antes | jsonb | Não |
| dados_depois | jsonb | Não |
| metadados | jsonb | Não |
| ocorrido_em | timestamptz | Sim |

## Exemplos

```text
atividade.criada
atividade.dono_alterado
tarefa.iniciada
tarefa.devolvida
fila.reordenada
prazo.aceito
usuario.perfil_atribuido
setor.inativado
```

---

# 87. Evento de auditoria deve ser imutável

Usuários comuns não devem editar.

Correções precisam gerar novo evento.

---

# 88. `dados_antes` e `dados_depois`

Devem ser usados apenas quando ajudam a explicar a mudança.

Exemplo:

```json
dados_antes:
{"prazo_comprometido":"2026-09-15T12:00:00Z"}

dados_depois:
{"prazo_comprometido":"2026-09-16T09:00:00Z"}
```

---

# 89. Não usar auditoria como banco operacional

Evitar consultar `auditoria.eventos` para descobrir o status atual de toda tela.

O estado atual fica nas tabelas de domínio.

Auditoria explica o passado.

---

# 90. `auditoria.acessos`

Pode existir futuramente para:

- login;
- logout;
- falhas;
- sessão;
- acesso sensível.

Não é essencial ao núcleo do D0.

---

# 91. `auditoria.integracoes`

Pode existir futuramente para registrar:

- origem;
- payload resumido;
- resultado;
- erro;
- identificador externo.

Fora do D0 atual.

---

# 92. Eventos de domínio x auditoria

Exemplo de devolução:

```text
produtividade.devolucoes
→ representa o fato de negócio
```

```text
auditoria.eventos
→ representa o rastro da ação
```

As duas camadas podem coexistir.

---

# 93. Relacionamentos principais

Visão simplificada:

```text
core.organizacoes
    ↓
core.empresas
    ↓
core.setores

core.organizacoes
    ↓
core.usuarios
    ↓
core.usuario_setores
```

---

# 94. Relacionamentos operacionais

```text
produtividade.atividades
    ↓ 1:N
produtividade.tarefas
    ↓ N:N
produtividade.tarefa_executores
```

---

# 95. Fluxo

```text
tarefas
    ↓
passagens_setor
    ↓
fila_itens
```

---

# 96. Tempo

```text
tarefas
    ↓
sessoes_tempo
```

---

# 97. Retorno

```text
tarefas
    ↓
devolucoes
```

---

# 98. Bloqueio

```text
tarefas
    ↓
bloqueios
```

---

# 99. Prazo

```text
atividades / tarefas
    ↓
prazos_historico
```

---

# 100. Comunicação

```text
atividade ou tarefa
    ↓
conversa
    ↓
mensagens
```

---

# 101. Notificação

```text
evento
    ↓
notificacao
    ↓
usuario
```

---

# 102. Autorização

```text
usuario
    ↓
usuario_perfis
    ↓
perfil
    ↓
perfil_acoes
    ↓
acao
```

com:

```text
usuario_perfis
    ↓
escopo
```

---

# 103. Organização em todas as relações

Mesmo quando FK já permite descobrir a organização, as relações críticas precisam impedir cruzamento de tenant.

Estratégias técnicas possíveis:

- FK composta com `organizacao_id`;
- triggers de consistência;
- constraints;
- RLS;
- validação na aplicação.

---

# 104. Índices multi-tenant

Consultas normalmente filtram por:

```text
organizacao_id
```

Por isso, muitos índices devem começar por essa coluna.

Exemplo:

```text
index(organizacao_id, setor_atual_id, status)
```

em vez de apenas:

```text
index(status)
```

---

# 105. Índices de atividades

Prioridades:

```text
organização + status
organização + dono
organização + prazo
organização + empresa
obra
centro de custo
```

---

# 106. Índices de tarefas

Prioridades:

```text
atividade
setor atual + status
prazo
tipo
```

---

# 107. Índices de fila

Críticos:

```text
setor + estado + ordem
```

---

# 108. Índices de tempo

Críticos:

```text
usuario + inicio
tarefa + inicio
```

---

# 109. Índices de auditoria

Críticos:

```text
entidade_tipo + entidade_id + ocorrido_em
atividade_id + ocorrido_em
tarefa_id + ocorrido_em
usuario_id + ocorrido_em
```

---

# 110. Índices de comunicação

Críticos:

```text
conversa + criada_em
usuario + notificacoes não lidas
```

---

# 111. Índices parciais

PostgreSQL permite índices úteis como:

```text
where ativo = true
```

ou:

```text
where fim_em is null
```

Isso é recomendado para:

- sessões abertas;
- fila ativa;
- vínculos ativos;
- propostas pendentes.

---

# 112. Integridade de atividade

Restrições possíveis:

```text
dono_usuario_id NOT NULL
```

```text
concluida_em só quando status concluído
```

```text
cancelada_em só quando cancelada
```

As regras exatas dependem do catálogo final de status.

---

# 113. Integridade de tarefa

Exemplos:

- atividade obrigatória;
- `concluida_em >= criada_em`;
- setor atual precisa pertencer à organização;
- executor precisa pertencer à organização.

---

# 114. Integridade de sessão

```text
fim_em >= inicio_em
```

e:

```text
uma sessão ativa por usuário
```

---

# 115. Integridade de conversa

Exatamente um contexto:

```text
atividade_id XOR tarefa_id
```

---

# 116. Integridade de prazo

Em `prazos_historico`:

```text
atividade_id XOR tarefa_id
```

---

# 117. Integridade de dependência

```text
predecessora != sucessora
```

e ambas pertencem à mesma atividade.

---

# 118. Integridade de fila

Uma tarefa não pode possuir duas entradas ativas simultaneamente.

---

# 119. Transações

Operações com várias alterações devem ser atômicas.

Exemplo:

```text
Devolver tarefa
```

precisa, em uma transação:

1. registrar devolução;
2. fechar passagem atual;
3. abrir nova passagem;
4. atualizar setor atual;
5. atualizar fila;
6. registrar auditoria;
7. gerar notificação.

Se uma parte falhar:

> não deixar o sistema em estado parcial.

---

# 120. Outro exemplo transacional

Reordenar fila:

1. alterar ordem;
2. recalcular posições afetadas;
3. registrar histórico;
4. registrar auditoria;
5. criar notificações.

---

# 121. Conclusão de tarefa

Pode envolver:

1. fechar sessão ativa;
2. atualizar status;
3. registrar `concluida_em`;
4. retirar da fila;
5. fechar passagem de setor quando aplicável;
6. liberar dependentes;
7. gerar auditoria;
8. gerar notificações.

---

# 122. Primeira ação

A definição funcional final ainda está pendente.

Quando fechada, o banco pode manter:

```text
primeira_acao_em
```

como campo cacheado para performance.

A fonte de verdade continua sendo eventos.

---

# 123. Campos derivados

Exemplos:

```text
tempo_total
horas_homem
tempo_em_fila
```

não precisam ser campos persistidos no D0.

Podem ser calculados.

---

# 124. Views

Views podem simplificar consultas.

Exemplos futuros:

```text
vw_atividade_metricas
vw_tarefa_metricas
vw_fila_atual
vw_usuario_permissoes
```

---

# 125. Materialized views

Podem ser usadas futuramente para métricas pesadas.

Não são necessárias antes de existir volume.

---

# 126. Analytics separado

Se a LPS crescer muito, análises históricas podem migrar para:

- data warehouse;
- lakehouse;
- réplicas analíticas.

Não precisa ser decidido no D0.

---

# 127. D0 deve priorizar consistência operacional

O banco principal precisa primeiro suportar bem:

- CRUD;
- fluxo;
- fila;
- tempo;
- auditoria;
- segurança.

---

# 128. JSONB

Usar JSONB apenas quando a estrutura realmente for variável.

Bons candidatos:

```text
auditoria.metadados
regras_notificacao.condicoes
regras_escalonamento.condicoes
```

---

# 129. Onde evitar JSONB

Evitar armazenar como JSON:

```text
atividade
tarefa
setor
executor
prazo
fila
```

Esses conceitos precisam de relações fortes.

---

# 130. Auditoria de alterações

Toda tabela crítica deve gerar eventos em:

```text
auditoria.eventos
```

por aplicação ou trigger, conforme decisão técnica.

---

# 131. Triggers

Triggers podem ajudar em:

- `updated_at`;
- auditoria;
- consistência;
- eventos específicos.

Mas não concentrar toda lógica de negócio no banco sem necessidade.

---

# 132. Lógica no banco x aplicação

Regra recomendada:

## Banco

Responsável por:

- integridade;
- FK;
- constraints;
- RLS;
- unicidade;
- validações estruturais.

## Aplicação

Responsável por:

- fluxo;
- decisões;
- notificações;
- regras configuráveis;
- orquestração.

---

# 133. Funções PostgreSQL

Podem ser usadas em operações críticas que exigem transação consistente.

Exemplo:

```text
reordenar_fila(...)
```

ou:

```text
devolver_tarefa(...)
```

A decisão depende da arquitetura da aplicação.

---

# 134. Segurança do schema `core`

RLS por organização.

Exemplo conceitual:

```text
usuario.organizacao_id = registro.organizacao_id
```

mais validação das ações/escopos quando necessário.

---

# 135. Segurança do schema `acessos`

Somente usuários com ações administrativas podem:

- criar perfil;
- editar perfil;
- conceder permissões;
- alterar escopos.

Usuários comuns podem consultar apenas o necessário.

---

# 136. Segurança do schema `cadastros`

Cada cadastro possui ações próprias.

Exemplo:

```text
obra.visualizar
obra.criar
obra.editar
```

quando necessário.

---

# 137. Segurança do schema `produtividade`

Acesso depende de:

- organização;
- ação;
- escopo;
- relação com atividade;
- setor;
- dono;
- executor.

---

# 138. Segurança da conversa

A conversa herda o contexto.

Se usuário não pode acessar atividade/tarefa:

> não pode acessar mensagens.

---

# 139. Segurança das notificações

Usuário só acessa suas próprias notificações.

---

# 140. Segurança da auditoria

Auditoria possui acesso mais restrito.

Nem todo usuário que vê uma atividade precisa ver detalhes administrativos de segurança.

---

# 141. Dados históricos

Inativar cadastro não deve quebrar FK.

Exemplo:

```text
Setor Financeiro inativado
```

Atividades antigas continuam relacionadas.

---

# 142. Não utilizar cascade delete em excesso

Evitar:

```text
apagar setor
→ apagar tarefas
```

Isso seria destrutivo.

---

# 143. `ON DELETE RESTRICT`

Deve ser padrão para objetos com histórico importante.

---

# 144. `ON DELETE SET NULL`

Pode ser usado em referências opcionais não essenciais ao histórico.

Avaliar caso a caso.

---

# 145. `ON DELETE CASCADE`

Usar apenas em objetos filhos que não têm significado independente.

Exemplo possível:

```text
perfil_acoes
```

quando perfil é fisicamente removível em ambiente sem uso.

Mas perfis em uso provavelmente serão inativados.

---

# 146. Versionamento de fluxo

Modelos podem possuir:

```text
versao
```

Atividades reais não devem mudar retroativamente.

---

# 147. Versionamento de configuração

Regras críticas podem futuramente exigir histórico.

No D0, auditoria de alterações pode ser suficiente.

---

# 148. Migrações

Toda alteração de schema deve ser versionada.

Usar:

- migrations;
- revisão;
- testes;
- rollback quando possível.

---

# 149. Não editar produção manualmente como rotina

Mudanças estruturais devem passar por migration.

---

# 150. Dados mestres

Cadastros como ações globais podem ser populados via seed controlado.

---

# 151. Ações do sistema

Exemplos de seed:

```text
atividade.visualizar
atividade.criar
tarefa.visualizar
tarefa.iniciar
fila.reordenar
```

---

# 152. Perfis

Perfis são da organização.

Não devem ser seeds globais obrigatórios, embora modelos possam ser oferecidos.

---

# 153. Tipos de atividade

Pertencem à organização.

---

# 154. Motivos

Pertencem à organização.

Pode haver modelos globais copiáveis futuramente.

---

# 155. Dados de teste

Ambiente de desenvolvimento deve possuir fixtures separadas de produção.

---

# 156. Auditoria e dados de teste

Não misturar métricas de teste com operação real.

---

# 157. Ambientes

Idealmente:

```text
dev
staging
prod
```

com bancos separados.

---

# 158. Segurança de credenciais

Credenciais nunca devem ser armazenadas em:

- mensagens;
- commits;
- documentação aberta.

Usar secrets/environment variables.

---

# 159. Chaves de serviço

Service role do Supabase deve ficar apenas em ambiente seguro de backend.

Nunca no front-end.

---

# 160. Public key

Mesmo com chave pública, RLS precisa estar correto.

---

# 161. RLS não pode depender de confiança no cliente

Política deve assumir que requisições podem ser manipuladas.

---

# 162. Testes de segurança

Cenários mínimos:

```text
Usuário Org A tentando abrir Org B
→ negado
```

```text
Usuário sem fila.reordenar
→ negado
```

```text
Usuário dono da atividade
→ vê contexto da própria atividade
```

```text
Usuário sem acesso ao setor
→ não vê fila completa
```

---

# 163. Testes de integridade

Exemplos:

```text
duas sessões abertas pelo mesmo usuário
→ impedir
```

```text
tarefa dependente dela mesma
→ impedir
```

```text
conversa vinculada a atividade e tarefa ao mesmo tempo
→ impedir
```

---

# 164. Testes de histórico

Exemplo:

Reordenar:

```text
4 → 16
```

deve gerar:

- nova ordem;
- histórico;
- evento;
- notificação.

---

# 165. Testes de devolução

Devolver:

```text
Compras → Engenharia
```

deve gerar:

- devolução;
- motivo;
- nova passagem;
- atualização da tarefa;
- fila;
- evento;
- notificação.

---

# 166. Testes de prazo

Propor:

```text
hoje → terça
```

não deve alterar `prazo_comprometido` até aceite.

---

# 167. Teste de recusa

Recusa:

```text
status_proposta = recusada
```

e:

```text
escalonamento criado
```

conforme regra.

---

# 168. Teste de conclusão

Concluir atividade:

- registra timestamp;
- registra evento;
- notifica dono;
- preserva histórico.

---

# 169. D0 — tabelas obrigatórias

Lista mínima recomendada.

## `core`

```text
organizacoes
empresas
usuarios
setores
usuario_setores
```

## `acessos`

```text
grupos_acoes
acoes
perfis
perfil_acoes
escopos
usuario_perfis
usuario_acoes
```

## `cadastros`

```text
obras
centros_custo
```

## `produtividade`

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
```

## `comunicacao`

```text
conversas
mensagens
mencoes
notificacoes
preferencias_notificacao
```

## `configuracoes`

```text
tipos_atividade
tipos_tarefa
motivos_devolucao
motivos_bloqueio
fluxos_modelo
fluxo_tarefas_modelo
fluxo_dependencias_modelo
regras_notificacao
regras_escalonamento
```

## `auditoria`

```text
eventos
```

---

# 170. Tabelas que podem ficar depois

```text
clientes
entidades
entidade_papeis
aprovacoes
entregas_notificacao
auditoria_acessos
auditoria_integracoes
metricas_materializadas
insights
previsoes
recomendacoes
feedback_recomendacao
```

Só criar quando o produto realmente exigir.

---

# 171. Não criar tabelas de IA no D0

O D0 precisa gerar os dados.

Não precisa armazenar:

```text
score_ia
embedding
modelo_previsao
```

sem uso real.

---

# 172. Base para inteligência futura

Os dados mais importantes são:

```text
atividade
tarefa
evento
tempo
fila
prazo
devolução
motivo
setor
executor
conclusão
```

---

# 173. Views futuras de métricas

Exemplos:

```text
vw_tarefa_tempo_total
vw_tarefa_horas_homem
vw_atividade_tempo_total
vw_tempo_por_setor
vw_devolucoes_por_motivo
vw_fila_atual
```

---

# 174. Exemplo de cálculo de horas-homem

```sql
SUM(fim_em - inicio_em)
```

agrupado por:

```text
tarefa
```

ou:

```text
atividade
```

---

# 175. Exemplo de tempo em setor

```text
saida_em - entrada_em
```

por passagem.

---

# 176. Exemplo de tempo em fila

```text
primeiro_inicio_execucao - entrou_em
```

por passagem relevante.

A definição formal será centralizada para evitar cálculos divergentes.

---

# 177. Dicionário de métricas

Futuramente pode existir documentação técnica com:

- nome;
- fórmula;
- fonte;
- unidade;
- exceções.

Não precisa ser tabela do banco no D0.

---

# 178. Desempenho

Não otimizar prematuramente.

Mas criar índices óbvios desde o início.

---

# 179. Volume de auditoria

Pode crescer rapidamente.

Índices e política de retenção precisam ser monitorados.

---

# 180. Particionamento

Pode ser necessário no futuro para:

```text
auditoria.eventos
mensagens
notificacoes
```

Não é necessário antes de existir volume real.

---

# 181. Arquivamento

Atividades antigas podem ser marcadas como arquivadas sem sair do banco.

---

# 182. Soft delete

Não aplicar genericamente em tudo.

Usar estado específico quando possível:

```text
ativo
cancelado
arquivado
```

---

# 183. Campo `deleted_at`

Pode existir em objetos onde exclusão lógica realmente faça sentido.

Não usar automaticamente.

---

# 184. Auditoria de segurança

Alterações em:

```text
usuario_perfis
usuario_acoes
perfil_acoes
escopos
```

devem gerar eventos.

---

# 185. Auditoria de configuração

Alterações em:

```text
setores
tipos
motivos
fluxos
regras
```

também devem gerar histórico.

---

# 186. Auditoria de domínio

Eventos de:

```text
atividade
tarefa
fila
prazo
devolução
bloqueio
```

são prioritários.

---

# 187. Evento não substitui FK

Mesmo com auditoria, as tabelas precisam ter relacionamentos normais.

---

# 188. Nomes de schemas

Usar nomes em português é aceitável e está alinhado ao domínio atual.

Manter consistência.

---

# 189. Nomes de tabelas

Preferir plural:

```text
atividades
tarefas
usuarios
```

---

# 190. Nomes de colunas

Preferir:

```text
snake_case
```

Exemplo:

```text
prazo_comprometido
```

---

# 191. Não misturar idiomas

Evitar:

```text
created_at
prazo_final
owner_id
```

no mesmo modelo.

Escolher padrão.

Neste documento, padrão funcional sugerido:

```text
português
```

A decisão final de nomenclatura técnica deve ser única.

---

# 192. Supabase

Se a LPS usar Supabase:

- PostgreSQL continua sendo a fonte;
- Auth fornece identidade;
- RLS protege dados;
- Realtime pode apoiar fila/notificações;
- Storage pode apoiar anexos.

---

# 193. Realtime

Pode ser útil para:

- mudança de posição;
- mensagem;
- notificação;
- tarefa atualizada.

Não deve substituir persistência.

---

# 194. Storage

Arquivos podem ser organizados por:

```text
organizacao
atividade
tarefa
```

com políticas compatíveis com RLS.

A modelagem detalhada de anexos não é prioridade deste documento.

---

# 195. Funções Edge

Podem ser úteis para:

- notificações externas;
- integrações;
- IA;
- operações administrativas.

Não usar para contornar RLS sem necessidade.

---

# 196. Neon ou Supabase

O modelo conceitual não deve depender excessivamente do fornecedor.

PostgreSQL é a base.

---

# 197. Portabilidade

Evitar recursos proprietários quando não agregarem valor suficiente.

---

# 198. Segurança do tenant

Toda query de negócio precisa estar implicitamente ou explicitamente limitada por:

```text
organizacao_id
```

---

# 199. Escopo de empresa

Depois do tenant:

```text
empresa_id
```

é filtro relevante em muitas consultas.

---

# 200. Escopo de setor

Para operação:

```text
setor_id
```

é central.

---

# 201. Dono

Para atividades:

```text
dono_usuario_id
```

é filtro central.

---

# 202. Executor

Para tarefas:

```text
tarefa_executores
```

é filtro central.

---

# 203. Fila

Para colaborador:

```text
setor + estado + ordem
```

é consulta crítica.

---

# 204. Dashboard futuro

Consultas agregadas podem exigir estrutura analítica separada.

Não comprometer OLTP com relatórios pesados sem necessidade.

---

# 205. OLTP

**OLTP — Online Transaction Processing**

É o banco operacional usado para:

- criar;
- editar;
- movimentar;
- executar.

A LPS começa focada nisso.

---

# 206. Analytics

Depois pode existir camada própria para análise.

---

# 207. Fonte de verdade

No D0:

```text
PostgreSQL operacional
```

é a fonte de verdade.

---

# 208. Concorrência de fila

Reordenação pode ser feita por mais de uma pessoa simultaneamente.

Precisa de transação e estratégia para evitar conflito.

Possíveis abordagens:

- lock por setor;
- versão da fila;
- retry otimista.

A decisão técnica será feita na implementação.

---

# 209. Concorrência de prazo

Duas pessoas não devem aceitar/rejeitar a mesma proposta de forma inconsistente.

Usar transação e status atual.

---

# 210. Concorrência de sessão

Uma pessoa iniciando duas tarefas quase simultaneamente precisa de restrição.

---

# 211. Concorrência de dono

Troca de dono precisa ser atômica.

---

# 212. Optimistic locking

Pode existir coluna:

```text
versao
```

ou utilizar `updated_at` em objetos críticos.

Não obrigatório no D0 para tudo.

---

# 213. Integridade antes de conveniência

Melhor rejeitar uma operação inconsistente do que gravar estado impossível.

---

# 214. Logs de erro

Logs técnicos de aplicação não precisam morar necessariamente no mesmo banco.

Não confundir:

```text
auditoria de negócio
```

com:

```text
log de erro técnico
```

---

# 215. Auditoria de negócio

Exemplo:

```text
Paulo alterou prazo.
```

---

# 216. Log técnico

Exemplo:

```text
timeout na API.
```

São coisas diferentes.

---

# 217. Observabilidade

Pode usar plataforma externa de logs.

Fora do escopo deste documento.

---

# 218. Dados obrigatórios mínimos para criar atividade

Do ponto de vista do banco:

```text
organização
empresa
título
dono
status
criador
```

Outros campos podem ser opcionais.

---

# 219. Não obrigar obra

Decisão consolidada.

---

# 220. Não obrigar centro de custo

Decisão consolidada.

---

# 221. Dados mínimos para criar tarefa

```text
atividade
título
status
criador
```

Setor pode ser definido no momento da criação ou antes de entrar em execução.

A regra final de UX pode exigir mais.

---

# 222. Tarefa sem executor

Permitida.

---

# 223. Tarefa sem setor

Pode existir temporariamente durante criação.

Antes de entrar em fila/execução, precisa de setor.

A validação pode ocorrer na aplicação.

---

# 224. Atividade sem tarefas

Pode existir durante criação inicial.

Mas precisa ser tratada na UX para não ficar esquecida.

---

# 225. Processo de criação simples

O banco não deve forçar dezenas de campos obrigatórios.

---

# 226. Campo de descrição

Texto livre útil.

Não usar como substituto de campos estruturados.

---

# 227. Campo de impacto

Ainda não existe decisão final de modelagem.

Não criar tabela complexa de criticidade agora.

Quando entrar, separar:

```text
impacto informado
```

de:

```text
prioridade operacional
```

---

# 228. Prioridade operacional

Pode futuramente ser campo na fila ou tarefa.

Ainda não consolidado.

Não confundir com ordem.

---

# 229. Posição

É derivada da ordem da fila.

---

# 230. Ordem

É controlada pelo setor.

---

# 231. Notificação da posição

Derivada do histórico de posição.

---

# 232. Previsão

Não armazenar no D0 como verdade.

Futuramente pode existir:

```text
previsao_conclusao
```

com origem e confiança.

---

# 233. Campos de IA

Quando surgirem, precisam diferenciar:

```text
valor previsto
confianca
modelo
gerado_em
```

Não misturar com prazo comprometido.

---

# 234. Auditoria de IA futura

Toda recomendação relevante deve registrar:

- modelo;
- versão;
- input resumido;
- resultado;
- usuário;
- aceite/rejeição.

Fora do D0.

---

# 235. Schema futuro de inteligência

Se necessário:

```text
inteligencia
```

poderá existir no futuro.

Não criar agora.

---

# 236. Por que não criar `inteligencia` agora

Porque ainda não existem:

- previsões;
- recomendações;
- modelos;
- feedbacks.

Criar antes seria modelar abstração sem uso.

---

# 237. Data warehouse futuro

Também não criar agora.

---

# 238. Matriz de schemas

| Schema | Responsabilidade principal |
|---|---|
| core | Tenant, empresas, usuários, setores |
| acessos | Perfis, ações, escopos e autorização |
| cadastros | Obras, centros de custo e apoio |
| produtividade | Atividades, tarefas, fluxo, tempo, fila, prazo |
| comunicacao | Conversas e notificações |
| configuracoes | Tipos, motivos, modelos e regras |
| auditoria | Histórico genérico e imutável |

---

# 239. Dependências entre schemas

```text
core
↓
todos
```

`core` é base.

---

# 240. `acessos`

Depende de:

```text
core.usuarios
core.organizacoes
core.setores
```

e pode referenciar cadastros de escopo.

---

# 241. `produtividade`

Depende de:

```text
core
cadastros
configuracoes
```

---

# 242. `comunicacao`

Depende de:

```text
core
produtividade
auditoria
```

---

# 243. `auditoria`

Referencia entidades de todos os schemas.

Por isso deve evitar FKs impossíveis em `entidade_id` genérico.

Campos específicos como:

```text
atividade_id
tarefa_id
```

podem possuir FK.

`entidade_tipo + entidade_id` funciona como referência lógica.

---

# 244. Não criar dependências circulares desnecessárias

A arquitetura deve manter schemas compreensíveis.

---

# 245. Cliente como decisão pendente

Não forçar relacionamento circular entre `core.empresas` e `cadastros.clientes` até a modelagem de entidades ser definida.

---

# 246. Regra para nova tabela

Antes de criar:

1. Qual conceito representa?
2. Existe comportamento próprio?
3. Precisa de histórico?
4. Já existe tabela que representa isso?
5. É realmente D0?
6. Precisa de FK?
7. Qual organização é dona?
8. Quais índices?
9. Quais permissões?

---

# 247. Regra para novo campo

Perguntar:

> Este dado é realmente necessário para operação, auditoria ou análise?

Evitar campos “talvez um dia”.

---

# 248. Regra para JSONB

Perguntar:

> A estrutura realmente varia ou estamos evitando modelar corretamente?

---

# 249. Regra para status

Não adicionar status para cada situação pequena.

Pode existir:

```text
status
+
bloqueio
+
prazo
+
fila
```

em vez de dezenas de estados combinados.

---

# 250. Explosão de status

Evitar:

```text
aguardando_cliente_atrasado
aguardando_cliente_sem_prazo
aguardando_cliente_urgente
```

Modelar dimensões separadas.

---

# 251. Estado ortogonal

Exemplo:

```text
status = em_andamento
bloqueio = aguardando_cliente
prazo = atrasado
```

Isso é mais flexível.

---

# 252. Fila e status

Fila é uma estrutura própria.

Não codificar posição no status.

---

# 253. Prazo e status

Atraso pode ser calculado.

Não precisa existir status:

```text
atrasado
```

se for apenas uma condição derivada.

---

# 254. Condições derivadas

Exemplos:

```text
atrasada = agora > prazo_comprometido e não concluída
```

---

# 255. Dados derivados não precisam virar coluna

A menos que performance exija.

---

# 256. Atualização de timestamps

`atualizado_em` deve refletir mudanças relevantes no registro.

Não usar como substituto da auditoria.

---

# 257. `criado_por`

Importante nos objetos principais.

---

# 258. `atualizado_por`

Útil em cadastros e configurações.

Em objetos com auditoria rica pode ser complementar.

---

# 259. Arquivamento de atividade

Pode existir campo futuro:

```text
arquivada_em
```

Não é necessário para o primeiro fluxo.

---

# 260. Cancelamento

Atividade e tarefa devem ter estado de cancelamento em vez de exclusão.

---

# 261. Motivo de cancelamento

Pode surgir futuramente como configuração.

Não está consolidado no D0 atual.

---

# 262. Reabertura

Evento em auditoria.

Pode atualizar status e timestamps.

---

# 263. Histórico de status específico

Pode ser derivado de `auditoria.eventos`.

Não criar tabela separada se não houver necessidade.

---

# 264. Histórico de fila específico

Precisa de tabela própria porque posição é métrica central.

---

# 265. Histórico de prazo específico

Precisa de tabela própria porque negociação possui estado.

---

# 266. Histórico de setor específico

Precisa de `passagens_setor` porque medição de permanência é central.

---

# 267. Histórico de tempo específico

Precisa de `sessoes_tempo` porque é dado operacional.

---

# 268. Históricos não são duplicação inútil

Cada um possui semântica própria.

---

# 269. Auditoria genérica complementa

Permite responder:

> quem alterou?

mesmo em mudanças administrativas.

---

# 270. Exemplo completo — criação de atividade

Operação:

```text
Criar atividade
```

Grava:

```text
produtividade.atividades
```

Pode criar:

```text
comunicacao.conversas
```

automaticamente.

Gera:

```text
auditoria.eventos
```

---

# 271. Exemplo completo — criar tarefa

Grava:

```text
produtividade.tarefas
```

Pode criar:

```text
comunicacao.conversas
```

para a tarefa.

Se setor definido:

```text
produtividade.passagens_setor
```

e talvez:

```text
produtividade.fila_itens
```

---

# 272. Exemplo completo — iniciar tarefa

Operação:

```text
Iniciar
```

Grava:

```text
sessoes_tempo
```

Atualiza:

```text
tarefas.status
tarefas.iniciada_em
tarefas.primeira_acao_em
```

quando aplicável.

Pode retirar da condição de espera da fila.

Gera:

```text
auditoria.eventos
```

---

# 273. Exemplo completo — devolver

Grava:

```text
devolucoes
```

Fecha:

```text
passagem_setor atual
```

Abre:

```text
nova passagem_setor
```

Atualiza:

```text
tarefas.setor_atual_id
```

Atualiza fila.

Gera:

```text
auditoria.eventos
notificacoes
```

---

# 274. Exemplo completo — propor prazo

Grava:

```text
prazos_historico
tipo = proposto
status = pendente
```

Não altera:

```text
prazo_comprometido
```

até aceite.

---

# 275. Exemplo completo — aceitar prazo

Atualiza:

```text
prazos_historico.status = aceita
tarefas/atividades.prazo_comprometido
```

Gera:

```text
auditoria
notificacao
```

---

# 276. Exemplo completo — recusar prazo

Atualiza proposta:

```text
recusada
```

Cria:

```text
escalonamentos
```

conforme regra.

---

# 277. Exemplo completo — reordenar

Atualiza:

```text
fila_itens.ordem
```

Registra:

```text
fila_historico_posicoes
```

Gera:

```text
auditoria
notificacoes
```

---

# 278. Exemplo completo — concluir tarefa

Fecha:

```text
sessoes abertas
fila
passagem
```

Atualiza:

```text
tarefas.status
tarefas.concluida_em
```

Libera dependentes.

Gera:

```text
auditoria
notificacao
```

---

# 279. Exemplo completo — concluir atividade

Atualiza:

```text
atividades.status
atividades.concluida_em
```

Gera:

```text
auditoria
```

Notifica obrigatoriamente:

```text
dono
```

---

# 280. Consultas essenciais do D0

O banco deve responder com eficiência:

```text
Minhas atividades abertas
```

```text
Minhas tarefas
```

```text
Fila do setor
```

```text
Posição da minha tarefa
```

```text
Atividades atrasadas
```

```text
Timeline da atividade
```

```text
Tempo trabalhado
```

```text
Devoluções
```

---

# 281. Consulta — posição

Conceitualmente:

```sql
row_number() over (
  partition by setor_id
  order by ordem
)
```

sobre itens ativos.

---

# 282. Consulta — total da fila

```text
count(itens ativos do setor)
```

---

# 283. Consulta — tempo total

```text
concluida_em - criado_em
```

---

# 284. Consulta — horas-homem

Soma das sessões.

---

# 285. Consulta — tempo por setor

Soma ou detalhamento das passagens.

---

# 286. Consulta — devoluções por motivo

Agrupar:

```text
motivo_devolucao_id
```

---

# 287. Consulta — tarefas sem ação

Usar:

```text
último evento relevante
```

ou campo cacheado futuro.

---

# 288. Consulta — atraso

```text
prazo_comprometido < now()
and concluida_em is null
```

---

# 289. Consulta — conflito de prazo

Propostas pendentes ou recusadas com escalonamento aberto.

---

# 290. Consulta — dono

Atividades por `dono_usuario_id`.

---

# 291. Consulta — executor

Tarefas via `tarefa_executores`.

---

# 292. Consulta — gestor

Filtrar escopos autorizados e setores gerenciados.

---

# 293. Segurança e performance

RLS pode aumentar custo de consulta.

Índices precisam apoiar colunas usadas nas políticas.

---

# 294. Índices para RLS

Exemplos:

```text
organizacao_id
empresa_id
setor_id
usuario_id
dono_usuario_id
```

---

# 295. Funções de autorização

Pode ser útil criar funções SQL estáveis como:

```text
acessos.usuario_tem_acao(...)
```

Mas precisam ser bem testadas para não virar gargalo.

---

# 296. Cache de autorização

Pode ser necessário futuramente.

Não otimizar antes de medir.

---

# 297. Perfis e escopos

A combinação proposta:

```text
usuario_perfis(perfil_id, escopo_id)
```

evita duplicação de perfil por setor.

---

# 298. Exemplo

```text
Paulo
Gestor Comercial
Escopo Comercial
```

e:

```text
Paulo
Visualizador
Escopo Administrativo
```

---

# 299. Concessão direta

`usuario_acoes` resolve exceções.

---

# 300. Negação explícita

Não está prevista no D0.

O modelo inicial é:

```text
default deny
+
grants
```

---

# 301. Por que evitar DENY explícito no início

Aumenta complexidade de precedência.

Exemplo:

```text
perfil permite
usuário nega
outro perfil permite
```

Não precisamos disso agora.

---

# 302. Empresas e escopos

Se usuário pode operar em várias empresas, atribuir perfis com escopos diferentes.

---

# 303. Setores por empresa

No D0, `setores.empresa_id` é obrigatório.

Se surgir necessidade de setor corporativo compartilhado, revisar.

---

# 304. Holding

Arquitetura deve permitir várias empresas dentro da organização.

Modelagem avançada de holding não pertence ao D0.

---

# 305. Grupos de empresas

Também não precisam ser tabelas agora.

A arquitetura pode evoluir.

---

# 306. Obra

Tabela separada.

---

# 307. Centro de custo

Tabela separada.

---

# 308. Associação centro de custo → obra

Opcional.

---

# 309. Atividade → obra + centro de custo

Ambos opcionais e podem coexistir.

---

# 310. Cliente

Pendente.

---

# 311. Fornecedor

Não é cadastro obrigatório do D0 deste módulo.

Pode entrar quando o processo exigir.

---

# 312. Integração com ERP

Futuramente, empresa/obra/centro de custo podem ser sincronizados.

Campos úteis:

```text
sistema_origem
id_externo
```

não precisam existir em todas as tabelas agora.

---

# 313. Tabela de mapeamento de integrações

Melhor futuramente criar:

```text
integracoes.mapeamentos
```

do que poluir todas as tabelas, se houver muitas origens.

Não é D0.

---

# 314. Auditoria e métricas

Não usar `updated_at` para calcular tempos.

Usar eventos específicos.

---

# 315. Exemplo

```text
updated_at
```

pode mudar por correção de título.

Isso não significa:

```text
atividade avançou.
```

---

# 316. Primeira ação

Precisa vir de evento operacional relevante.

---

# 317. Última ação

Pode ser derivada de eventos relevantes.

---

# 318. Eventos relevantes

Catálogo futuro pode marcar:

```text
conta_como_acao = true
```

para tipos de evento.

Não precisa ser tabela no D0.

---

# 319. Sequência temporal

Eventos precisam utilizar timestamp do servidor.

---

# 320. Ordenação de eventos

Se dois eventos têm mesmo timestamp, usar:

- ID ordenável;
- sequência;
- criado_em com precisão.

---

# 321. UUIDv7

Pode ser considerado futuramente por ordenação temporal.

Não é obrigatório.

---

# 322. Segurança de UUID

UUID não substitui autorização.

---

# 323. Anexos

Se entrarem no D0, estrutura possível:

```text
comunicacao.anexos
```

ou:

```text
core.anexos
```

com contexto.

Ainda não definido.

---

# 324. Não armazenar arquivo binário diretamente na tabela principal

Usar storage e guardar metadata.

---

# 325. Mensagens e anexos

Relacionamento:

```text
mensagem 1:N anexos
```

quando implementado.

---

# 326. Limites de tamanho

Política futura.

---

# 327. Backup

Banco operacional precisa de estratégia de backup.

Assunto de infraestrutura, mas obrigatório em produção.

---

# 328. Point-in-time recovery

Desejável quando volume e criticidade justificarem.

---

# 329. Restaurar backup não substitui auditoria

São camadas diferentes.

---

# 330. Segurança de dados

Criptografia em trânsito e repouso deve usar mecanismos do provedor.

---

# 331. Dados pessoais

Usuários e mensagens podem conter dados pessoais.

Políticas da LGPD precisam ser consideradas.

---

# 332. Não guardar segredo desnecessário

Evitar campos de senha próprios.

Autenticação deve usar provedor seguro.

---

# 333. Senhas

Nunca armazenar senha em texto puro.

Idealmente, delegar ao Supabase Auth ou provedor equivalente.

---

# 334. Tokens

Não armazenar tokens sensíveis em tabelas comuns.

---

# 335. Logs sensíveis

Auditoria não deve copiar credenciais ou secrets.

---

# 336. Eventos com JSONB

Sanitizar dados antes de salvar.

---

# 337. LGPD e auditoria

Direito de remoção precisa ser conciliado com obrigações de histórico.

Tema jurídico futuro.

---

# 338. Dados anonimizados

Podem ser usados futuramente para benchmark.

Não implementar sem política.

---

# 339. Inteligência futura

A modelagem atual já deve permitir extrair:

- tempos;
- fluxo real;
- fila;
- devoluções;
- prazos;
- executores;
- setores;
- conversa.

Isso é suficiente para começar.

---

# 340. Não criar tabelas de agregação prematuras

Primeiro medir performance real.

---

# 341. Quando criar materialização

Quando consultas analíticas passarem a impactar operação.

---

# 342. Observação sobre `primeira_acao_em`

Pode ser campo derivado/cacheado.

Não deve ser preenchido manualmente.

---

# 343. Observação sobre `status`

Catálogo final ainda depende de decisão do produto.

Não fechar enums rígidos agora.

---

# 344. PostgreSQL ENUM

Evitar enums excessivamente rígidos para estados ainda em discussão.

Pode usar:

```text
text + check
```

ou tabelas internas.

---

# 345. Status internos consolidados

Quando o catálogo estiver estável, revisar abordagem.

---

# 346. IDs externos

Não necessários no D0.

---

# 347. Códigos humanos

Atividades podem futuramente possuir código como:

```text
ATV-000123
```

Não é obrigatório para a PK.

---

# 348. Código amigável

Se implementado:

```text
organizacao + sequência
```

pode facilitar comunicação.

Ainda não decidido.

---

# 349. Busca

Campos que podem exigir busca:

- título;
- nome;
- código.

No D0, índice B-tree e ILIKE podem bastar.

---

# 350. Full-text search

Pode ser adicionado futuramente para mensagens e atividades.

---

# 351. Vector search

Pode ser útil para IA e atividades semelhantes.

Não pertence ao D0.

---

# 352. Embeddings

Não criar ainda.

---

# 353. Pesquisa semântica

Futura.

---

# 354. Nomenclatura do banco

Este documento usa nomes em português para clareza.

A implementação deve escolher e manter um único padrão.

---

# 355. Schema `public`

Se usar Supabase, evitar deixar todas as tabelas de negócio diretamente no `public` sem organização.

Os schemas propostos ajudam a separar responsabilidades.

---

# 356. Exposição via API

Supabase/PostgREST precisa estar configurado para schemas permitidos.

Nem todo schema precisa ser exposto diretamente.

---

# 357. Schema `auditoria`

Pode ter acesso mais restrito.

---

# 358. Schema `acessos`

Também sensível.

---

# 359. Funções seguras

Funções `security definer` exigem cuidado extremo.

Usar somente quando necessário.

---

# 360. Search path

Funções PostgreSQL devem definir `search_path` explicitamente quando aplicável.

Assunto técnico de segurança.

---

# 361. Foreign keys

Devem existir sempre que a relação é real.

Não depender apenas de UUID solto.

---

# 362. Foreign keys entre schemas

Permitidas e desejáveis.

---

# 363. Exemplo

```text
produtividade.atividades.dono_usuario_id
→ core.usuarios.id
```

---

# 364. Exemplo

```text
produtividade.tarefas.atividade_id
→ produtividade.atividades.id
```

---

# 365. Exemplo

```text
produtividade.devolucoes.motivo_devolucao_id
→ configuracoes.motivos_devolucao.id
```

---

# 366. Consistência de organização

FK simples não garante que os dois registros são da mesma organização.

A aplicação e/ou constraint adicional precisa validar.

---

# 367. Estratégia recomendada

Para relações críticas, considerar:

```text
UNIQUE(organizacao_id, id)
```

e FK composta:

```text
(organizacao_id, objeto_id)
```

→

```text
(organizacao_id, id)
```

Isso impede cruzamento de tenant no próprio banco.

---

# 368. Custo

FK composta aumenta verbosidade.

Mas melhora segurança e integridade.

Avaliar principalmente em tabelas de domínio.

---

# 369. RLS continua necessária

FK composta protege consistência.

RLS protege leitura/escrita do usuário.

---

# 370. Observabilidade de fila

Pode existir view:

```text
vw_fila_posicoes
```

com:

- tarefa;
- ordem;
- posição;
- total.

---

# 371. Notificação de posição

Serviço observa mudança e persiste histórico.

---

# 372. Não recalcular todos os históricos em leitura

Histórico precisa ser registrado no momento da mudança.

---

# 373. Concorrência de notificações

Gerar notificação após transação de negócio bem-sucedida.

---

# 374. Outbox pattern

Futuramente, pode existir tabela de outbox para eventos assíncronos.

Exemplo:

```text
infra.outbox_eventos
```

Não é necessário no D0 se volume pequeno.

---

# 375. Por que outbox pode ser útil

Evita:

```text
banco atualiza
notificação falha
```

sem possibilidade de retry.

---

# 376. Eventos assíncronos futuros

- e-mail;
- push;
- IA;
- integrações;
- relatórios.

---

# 377. Mas não superarquitetar

D0 pode começar simples.

---

# 378. Evolução possível

Quando volume crescer:

```text
transação
↓
outbox
↓
worker
↓
notificação/integracao
```

---

# 379. Auditoria continua síncrona

Eventos críticos de auditoria devem estar na mesma transação quando possível.

---

# 380. Mensagem do sistema

Pode ser gerada a partir do evento depois da transação.

---

# 381. Evitar duplicação de regra

Exemplo:

Prazo aceito deve ser processado em uma única operação de domínio.

Não duplicar lógica em:

- front-end;
- trigger;
- função;
- worker;

sem necessidade.

---

# 382. Fonte de verdade da regra

Definir camada responsável durante implementação.

---

# 383. API de domínio

Futuramente, operações podem ser endpoints semânticos:

```text
POST /tarefas/{id}/devolver
POST /filas/{setor}/reordenar
POST /prazos/{id}/aceitar
```

em vez de CRUD direto irrestrito.

Isso melhora consistência.

---

# 384. Banco suporta operação semântica

Mesmo usando Supabase, funções/RPC podem ser utilizadas quando a transação envolver várias tabelas.

---

# 385. D0 não precisa ter tudo via RPC

Escolher apenas operações críticas.

---

# 386. Operações críticas candidatas

- devolver tarefa;
- reordenar fila;
- aceitar/recusar prazo;
- concluir tarefa;
- escalar;
- alterar dono.

---

# 387. Operações simples

- editar descrição;
- criar tipo;
- consultar fila;

podem usar CRUD normal com RLS.

---

# 388. Auditoria de configurações

Exemplo:

```text
Administrador alterou perfil Gestor Comercial.
```

Registrar ações adicionadas/removidas.

---

# 389. Auditoria de escopo

Exemplo:

```text
Paulo ganhou acesso ao Administrativo.
```

---

# 390. Auditoria de setor

Exemplo:

```text
Setor Compras renomeado para Suprimentos.
```

Histórico operacional não pode se perder.

---

# 391. Nomes históricos

Se relatório antigo precisa mostrar o nome à época, pode ser necessário snapshot ou histórico de cadastro.

No D0, auditoria de alteração pode ser suficiente.

---

# 392. Snapshot em eventos

`dados_antes` e `dados_depois` preservam mudança.

---

# 393. Métrica de setor após renomear

Deve usar o mesmo `setor_id`.

Assim o histórico permanece contínuo.

---

# 394. IDs estáveis são essenciais

Nunca usar nome como FK.

---

# 395. Métrica de usuário inativado

Continua utilizando o mesmo `usuario_id`.

---

# 396. Não reutilizar IDs

---

# 397. Não reutilizar e-mail para identidade histórica

Usuário é identificado por ID.

---

# 398. Conta recontratada

Se mesma pessoa voltar, decisão sobre reutilizar ou criar novo vínculo precisa ser definida.

Não é central agora.

---

# 399. Dados de perfil

Nome e e-mail são suficientes para o núcleo.

Não criar RH completo.

---

# 400. A LPS não é sistema de folha

Evitar campos desnecessários:

- salário;
- cargo CLT detalhado;
- benefícios.

Podem vir de integração futura.

---

# 401. Setor não é departamento completo

Não criar hierarquia infinita.

---

# 402. Hierarquia de setores

Pode ser necessidade futura.

No D0, não implementar `parent_setor_id` sem uso comprovado.

---

# 403. Organograma

Não é objetivo atual.

---

# 404. Gestor do setor

Pode ser representado em `usuario_setores.eh_gestor`.

Se regras mais complexas surgirem, criar tabela específica.

---

# 405. Escalonamento usando gestor

A regra consulta membros com:

```text
eh_gestor = true
```

e autorização adequada.

---

# 406. Gestor estrutural não substitui permissão

Mesmo gestor precisa da ação correta.

---

# 407. Obra e setor

Não possuem relação direta obrigatória.

Atividade pode combinar ambos.

---

# 408. Centro de custo e setor

Também independentes.

---

# 409. Atividade sem obra

Suportada.

---

# 410. Atividade sem cliente

Suportada.

---

# 411. Atividade interna

Exemplo:

```text
Picotar papel
```

Pode possuir apenas:

```text
empresa
dono
tarefas
setor
```

---

# 412. Atividade operacional de obra

Pode possuir:

```text
empresa
obra
centro de custo
```

---

# 413. Não obrigar contexto excessivo

Isso preserva simplicidade.

---

# 414. Regras de campo obrigatório por tipo

Futuramente, um tipo de atividade pode exigir obra.

Não é regra global.

---

# 415. Configuração futura

Exemplo:

```text
Tipo: Solicitação de material de obra
obra obrigatória = sim
```

Não precisa no D0.

---

# 416. Tipos de atividade

Ajudam inteligência.

Mas não devem bloquear criação por excesso de configuração.

---

# 417. Tipo genérico

Pode existir um tipo:

```text
Outros
```

no início.

---

# 418. Governança

Com o tempo, tipos devem ser consolidados para análise.

---

# 419. Status de D0 das tabelas

Legenda:

```text
OBRIGATÓRIA
RECOMENDADA
FUTURA
PENDENTE DE DECISÃO
```

---

# 420. Matriz de prioridade

| Tabela | Prioridade D0 |
|---|---|
| core.organizacoes | OBRIGATÓRIA |
| core.empresas | OBRIGATÓRIA |
| core.usuarios | OBRIGATÓRIA |
| core.setores | OBRIGATÓRIA |
| core.usuario_setores | OBRIGATÓRIA |
| acessos.grupos_acoes | OBRIGATÓRIA |
| acessos.acoes | OBRIGATÓRIA |
| acessos.perfis | OBRIGATÓRIA |
| acessos.perfil_acoes | OBRIGATÓRIA |
| acessos.escopos | OBRIGATÓRIA |
| acessos.usuario_perfis | OBRIGATÓRIA |
| acessos.usuario_acoes | RECOMENDADA |
| cadastros.obras | OBRIGATÓRIA |
| cadastros.centros_custo | OBRIGATÓRIA |
| cadastros.clientes | PENDENTE DE DECISÃO |
| produtividade.atividades | OBRIGATÓRIA |
| produtividade.atividade_inputs | OBRIGATÓRIA PARA ATIVIDADE COM PROCESSO |
| produtividade.atividade_outputs | OBRIGATÓRIA PARA ATIVIDADE COM PROCESSO |
| produtividade.atividade_criterios_aceite | OBRIGATÓRIA PARA ATIVIDADE COM PROCESSO |
| produtividade.tarefas | OBRIGATÓRIA |
| produtividade.tarefa_executores | OBRIGATÓRIA |
| produtividade.tarefa_dependencias | RECOMENDADA |
| produtividade.sessoes_tempo | OBRIGATÓRIA |
| produtividade.passagens_setor | OBRIGATÓRIA |
| produtividade.fila_itens | OBRIGATÓRIA |
| produtividade.fila_historico_posicoes | OBRIGATÓRIA |
| produtividade.devolucoes | OBRIGATÓRIA |
| produtividade.bloqueios | OBRIGATÓRIA |
| produtividade.prazos_historico | OBRIGATÓRIA |
| produtividade.escalonamentos | OBRIGATÓRIA |
| produtividade.escalonamento_destinatarios | RECOMENDADA |
| comunicacao.conversas | OBRIGATÓRIA |
| comunicacao.mensagens | OBRIGATÓRIA |
| comunicacao.participantes | RECOMENDADA |
| comunicacao.mencoes | OBRIGATÓRIA |
| comunicacao.notificacoes | OBRIGATÓRIA |
| comunicacao.preferencias_notificacao | RECOMENDADA |
| configuracoes.processos | OBRIGATÓRIA |
| configuracoes.processo_versoes | OBRIGATÓRIA |
| configuracoes.processo_inputs | OBRIGATÓRIA |
| configuracoes.processo_criterios_aceite | OBRIGATÓRIA |
| configuracoes.tipos_atividade | OBRIGATÓRIA |
| configuracoes.tipos_tarefa | RECOMENDADA |
| configuracoes.motivos_devolucao | OBRIGATÓRIA |
| configuracoes.motivos_bloqueio | OBRIGATÓRIA |
| configuracoes.fluxos_modelo | OBRIGATÓRIA PARA PROCESSO COM FLUXO |
| configuracoes.fluxo_tarefas_modelo | OBRIGATÓRIA PARA PROCESSO COM FLUXO |
| configuracoes.fluxo_dependencias_modelo | FUTURA/RECOMENDADA |
| configuracoes.regras_notificacao | RECOMENDADA |
| configuracoes.regras_escalonamento | OBRIGATÓRIA |
| auditoria.eventos | OBRIGATÓRIA |

---

# 421. Sequência recomendada de implementação

## Etapa 1 — Tenant e segurança

```text
organizações
empresas
usuários
setores
usuário-setores
ações
perfis
escopos
RLS
```

---

# 422. Etapa 2 — Processos e núcleo operacional

```text
processos
processo_versoes
processo_inputs
processo_criterios_aceite
fluxos_modelo
fluxo_tarefas_modelo
atividades
atividade_inputs
atividade_outputs
atividade_criterios_aceite
tarefas
executores
```

---

# 423. Etapa 3 — Tempo e fluxo

```text
sessões
passagens de setor
dependências
```

---

# 424. Etapa 4 — Filas

```text
fila_itens
histórico de posição
```

---

# 425. Etapa 5 — Prazo, devolução e bloqueio

```text
prazos
devoluções
bloqueios
```

---

# 426. Etapa 6 — Escalonamento

```text
escalonamentos
destinatários
regras
```

---

# 427. Etapa 7 — Comunicação

```text
conversas
mensagens
menções
notificações
```

---

# 428. Etapa 8 — Evolução do processo

Depois do fluxo básico funcionar:

```text
dependências_modelo
versionamento publicado
comparação entre versões
```

Não antecipar regras condicionais avançadas.


---

# 429. Etapa 9 — Métricas

Criar views/consultas usando os dados reais.

---

# 430. Não começar por dashboard

Primeiro:

```text
dados corretos.
```

---

# 431. Não começar por IA

Primeiro:

```text
histórico confiável.
```

---

# 432. Critérios para considerar o banco D0 funcional

O banco precisa permitir:

```text
[ ] criar organização
[ ] criar empresa
[ ] criar usuário
[ ] criar setor
[ ] vincular usuário a setor
[ ] configurar perfil
[ ] configurar ação
[ ] restringir por escopo
[ ] criar processo
[ ] criar rascunho de versão
[ ] cadastrar inputs
[ ] definir output
[ ] cadastrar critérios de aceite
[ ] publicar versão
[ ] criar atividade sem processo
[ ] criar atividade com processo
[ ] preservar processo_versao_id
[ ] definir dono
[ ] criar tarefas
[ ] atribuir vários executores
[ ] mover entre setores
[ ] criar dependências simples
[ ] controlar fila
[ ] mostrar posição exata
[ ] registrar histórico da posição
[ ] registrar sessões de tempo
[ ] registrar devolução com motivo
[ ] registrar bloqueio
[ ] negociar prazo
[ ] escalar conflito
[ ] conversar dentro da atividade/tarefa
[ ] gerar notificações
[ ] registrar auditoria
```

---

# 433. Critérios de qualidade

Além de funcionar, o banco deve:

```text
[ ] impedir cruzamento de organização
[ ] preservar histórico
[ ] impedir duplicidades críticas
[ ] impedir sessões simultâneas indevidas
[ ] impedir relações inválidas
[ ] manter integridade referencial
[ ] possuir índices principais
[ ] possuir RLS
```

---

# 434. Decisões consolidadas neste documento

## Schemas

Serão utilizados:

```text
core
acessos
cadastros
produtividade
comunicacao
configuracoes
auditoria
```

## Tenant

- organização é o limite principal;
- empresas existem dentro da organização;
- dados não cruzam organizações.

## Usuários e setores

- usuário pertence a uma organização;
- usuário pode participar de vários setores;
- setor é configurável;
- participação não equivale a autorização.

## Autorizações

- ações são dinâmicas;
- perfis agrupam ações;
- perfis são atribuídos dentro de escopos;
- concessão direta pode existir;
- negação por padrão;
- RLS como última barreira.

## Processos

- processo é configuração reutilizável;
- processo possui versões;
- versão publicada é imutável;
- input e critérios pertencem à versão;
- output principal pertence à versão;
- fluxo padrão pertence à versão;
- atividade pode existir sem processo;
- atividade estruturada guarda `processo_versao_id`;
- execução possui valores de input, evidência de output e estado dos critérios.

## Cadastros

- obras e centros de custo são separados;
- obra é opcional na atividade;
- centro de custo é opcional;
- ambos podem coexistir;
- departamentos e área de negócio ficam fora do D0.

## Atividades

- um único dono;
- empresa obrigatória;
- contexto operacional opcional;
- prazo solicitado separado de comprometido;
- histórico preservado.

## Tarefas

- pertencem a atividade;
- podem possuir vários executores;
- podem mudar de setor;
- podem ter dependências;
- podem ser devolvidas;
- possuem tempo próprio.

## Tempo

- sessões por usuário;
- uma sessão ativa por usuário no D0;
- origem automática/manual distinguível;
- horas-homem derivadas.

## Fluxo

- passagens por setor são registradas;
- múltiplas passagens pelo mesmo setor permitidas;
- `setor_atual_id` é apenas estado atual.

## Fila

- fila por setor;
- ordem armazenada;
- posição derivada;
- histórico de posição persistido;
- reordenação auditada.

## Devolução

- motivo obrigatório;
- histórico preservado;
- permite medir correção e retrabalho.

## Prazo

- histórico separado;
- proposta não altera compromisso antes de aceite;
- recusa pode escalar.

## Escalonamento

- entidade própria;
- múltiplos destinatários;
- decisão final registrada.

## Comunicação

- conversa ligada à atividade ou tarefa;
- mensagem não altera estado oficial;
- notificações apontam para eventos.

## Configurações

- tipos;
- motivos;
- modelos;
- regras;
- configuráveis por organização.

## Auditoria

- evento imutável;
- não substitui tabelas de domínio;
- registra antes/depois quando relevante.

---

# 435. Decisões ainda pendentes

Ainda precisam ser fechadas antes ou durante implementação:

1. catálogo final de status internos;
2. definição formal de primeira ação;
3. modelagem definitiva de clientes/entidades;
4. se `setor.empresa_id` continuará obrigatório em todas as organizações;
5. detalhes do calendário útil;
6. comportamento de tarefa bloqueada na fila;
7. obrigatoriedade de fluxo modelo no D0;
8. política de exclusão de mensagens;
9. estrutura de anexos;
10. canais externos de notificação;
11. granularidade final dos escopos;
12. política de acesso temporário;
13. uso de FK composta por `organizacao_id`;
14. quais operações críticas serão RPC/função transacional;
15. catálogo inicial de ações.

---

# 436. Pontos que não devem ser decididos pelo banco

O banco não deve decidir:

- se usuário acha tarefa importante;
- se fluxo é bom;
- se um colaborador é produtivo;
- se setor é lento;
- se precisa contratar pessoa;
- se recomendação de IA deve ser aceita.

O banco registra fatos.

A camada de produto e gestão interpreta.

---

# 437. Regra de ouro do banco

> **Se um fato operacional será importante para entender o processo amanhã, ele precisa ser registrado corretamente hoje.**

---

# 438. Regra de ouro da segurança

> **Nenhuma autorização pode depender apenas da interface, e nenhuma relação pode cruzar organizações.**

---

# 439. Regra de ouro da auditoria

> **Estado atual responde “como está”; histórico responde “como chegou aqui”. A LPS precisa dos dois.**

---

# 440. Regra de ouro da inteligência

> **O banco do D0 deve ser construído para gerar dados confiáveis, não para fingir que a inteligência futura já existe.**

---

# 441. Regra de ouro da simplicidade

> **Não criar estrutura para problemas que ainda não existem.**

---

# 442. Estrutura resumida

```text
core
├── organizacoes
├── empresas
├── usuarios
├── setores
└── usuario_setores

acessos
├── grupos_acoes
├── acoes
├── perfis
├── perfil_acoes
├── escopos
├── usuario_perfis
└── usuario_acoes

cadastros
├── obras
└── centros_custo

produtividade
├── atividades
├── atividade_inputs
├── atividade_outputs
├── atividade_criterios_aceite
├── tarefas
├── tarefa_executores
├── tarefa_dependencias
├── sessoes_tempo
├── passagens_setor
├── fila_itens
├── fila_historico_posicoes
├── devolucoes
├── bloqueios
├── prazos_historico
├── escalonamentos
├── escalonamento_destinatarios
└── escalonamento_eventos

comunicacao
├── conversas
├── mensagens
├── participantes
├── mencoes
├── notificacoes
└── preferencias_notificacao

configuracoes
├── processos
├── processo_versoes
├── processo_inputs
├── processo_criterios_aceite
├── tipos_atividade
├── tipos_tarefa
├── motivos_devolucao
├── motivos_bloqueio
├── fluxos_modelo
├── fluxo_tarefas_modelo
├── fluxo_dependencias_modelo
├── regras_notificacao
└── regras_escalonamento

auditoria
└── eventos
```

---

# 443. Fluxo de dados resumido

```text
USUÁRIO AUTENTICA
↓
RLS IDENTIFICA ORGANIZAÇÃO
↓
AUTORIZAÇÃO VALIDA AÇÃO + ESCOPO
↓
USUÁRIO EXECUTA AÇÃO
↓
SE HOUVER PROCESSO, VERSÃO EXATA É APLICADA/VALIDADA
↓
TABELA DE DOMÍNIO É ALTERADA
↓
HISTÓRICO ESPECÍFICO É REGISTRADO
↓
AUDITORIA REGISTRA O EVENTO
↓
NOTIFICAÇÃO É GERADA QUANDO APLICÁVEL
↓
DADOS FICAM DISPONÍVEIS PARA MÉTRICAS
↓
FUTURAMENTE ALIMENTAM INTELIGÊNCIA
```

---

# 444. Encerramento

O banco da LPS precisa ser suficientemente robusto para preservar o histórico e suficientemente simples para não travar o desenvolvimento.

O D0 não precisa possuir:

- ERP completo;
- dezenas de módulos;
- data warehouse;
- IA;
- benchmark;
- modelagem infinita de organizações.

Ele precisa representar muito bem:

```text
quem
```

```text
o quê
```

```text
onde
```

```text
quando
```

```text
quanto tempo
```

```text
em qual fila
```

```text
qual prazo
```

```text
por onde passou
```

```text
por que voltou
```

```text
quem decidiu
```

```text
quando terminou
```

Se esses fatos forem registrados corretamente, a LPS terá uma base sólida para:

- gestão;
- auditoria;
- métricas;
- gargalos;
- previsão;
- recomendação;
- inteligência.

O banco deve ser consequência da lógica do produto.

Não o contrário.

---

# 445. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Consolidação da arquitetura conceitual do banco de dados da LPS com schemas, tabelas, relacionamentos, regras, índices, auditoria e segurança |
| 1.1 | Inclusão de processos versionados, inputs, output, critérios de aceite e vínculo imutável entre processo e atividade |
