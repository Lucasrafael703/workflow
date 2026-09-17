# 11 — Processos, Inputs, Outputs e Critérios de Aceite

> Documento funcional da LPS para definir como um processo reutilizável descreve o que precisa entrar, o que acontece durante a execução, o que deve sair e como a organização comprova que a entrega está realmente pronta.

---

# 1. Objetivo deste documento

Este documento define o conceito de **processo** dentro da LPS.

Ele deve responder:

- o que é um processo;
- o que é input;
- o que é output;
- o que é critério de aceite;
- qual a diferença entre processo, atividade, tarefa e tipo de atividade;
- como um processo é cadastrado;
- como funciona versionamento;
- o que acontece quando um processo é aplicado a uma atividade;
- quando inputs obrigatórios impedem início;
- quando critérios impedem conclusão;
- como o fluxo padrão pertence ao processo;
- como a interface deve apresentar essa estrutura sem burocracia;
- o que pertence ao D0;
- o que deve ficar para fases futuras.

---

# 2. Princípio central

Um processo precisa deixar claras duas pontas:

```text
O QUE PRECISO RECEBER?
↓
O QUE PRECISA ACONTECER?
↓
O QUE PRECISO ENTREGAR?
↓
COMO SEI QUE ESTÁ PRONTO?
```

Na LPS:

```text
INPUT
↓
TRANSFORMAÇÃO / EXECUÇÃO
↓
OUTPUT
↓
CRITÉRIOS DE ACEITE
```

Se o processo não consegue explicar essas quatro partes, ele ainda não está suficientemente definido.

---

# 3. Processo

Processo é um **modelo reutilizável de execução**.

Ele descreve como uma categoria recorrente de trabalho normalmente deve acontecer.

Exemplo:

```text
Processo:
Elaborar orçamento
```

Esse processo pode definir:

- inputs;
- output;
- critérios de aceite;
- tarefas padrão;
- setores responsáveis;
- ordem;
- dependências simples.

Processo não representa trabalho já executado.

---

# 4. Processo x atividade x tarefa x tipo de atividade

## Processo

```text
modelo reutilizável
```

Exemplo:

```text
Elaborar orçamento
```

## Atividade

```text
execução real que precisa chegar a um resultado
```

Exemplo:

```text
Entregar orçamento da obra Alpha ao cliente
```

## Tarefa

```text
parte do trabalho da atividade
```

Exemplos:

```text
Levantar quantitativos
Realizar cotações
Precificar
Revisar
```

## Tipo de atividade

```text
classificação
```

Exemplo:

```text
Orçamento
```

Um tipo de atividade pode possuir vários processos diferentes.

---

# 5. Processo não deve ser obrigatório para toda atividade

No D0, a LPS precisa aceitar dois caminhos.

## Atividade simples

```text
Título
Dono
Prazo
Criar
```

Sem processo.

Serve para:

- demanda ad hoc;
- trabalho raro;
- atividade ainda não padronizada;
- captura rápida.

## Atividade estruturada

```text
Título
Processo
Dono
Prazo
Criar
```

Ao selecionar processo, a LPS carrega a estrutura daquela versão.

Obrigar processo em tudo transformaria padronização em burocracia.

---

# 6. Estrutura mínima de um processo

```text
PROCESSO
│
├── Informações básicas
├── Inputs
├── Output
├── Critérios de aceite
└── Fluxo padrão
    └── Tarefas modelo
```

---

# 7. Informações básicas

Campos mínimos:

```text
Nome
Descrição
Empresa
Tipo de atividade, opcional
Status
Versão
```

Exemplo:

```text
Nome: Elaborar orçamento
Empresa: Biasi Engenharia
Tipo de atividade: Orçamento
Descrição: transformar documentos recebidos em proposta comercial pronta para envio
```

No D0, o processo pertence a uma empresa. Isso evita que um fluxo de uma empresa referencie setores de outra. Compartilhamento de processo entre empresas pode evoluir depois com mapeamento próprio.

---

# 8. Input

Input é aquilo que precisa estar disponível para a execução acontecer corretamente.

Pode ser:

- informação;
- arquivo;
- data;
- número;
- link;
- seleção;
- documento recebido de terceiro.

Exemplo — Elaborar orçamento:

```text
Projeto
Escopo
Prazo desejado
Documentos complementares
```

---

# 9. Campos de um input

Cada definição de input deve possuir no mínimo:

```text
Nome
Tipo
Obrigatório: sim/não
Origem, opcional
Ajuda de preenchimento, opcional
Ordem
```

Exemplo:

```text
Nome: Projeto
Tipo: Arquivo
Obrigatório: Sim
Origem: Solicitante
Ajuda: Anexar o projeto utilizado como base da proposta
```

---

# 10. Input obrigatório não precisa impedir criar a atividade

A atividade pode nascer incompleta para permitir rastrear a demanda desde o momento em que ela chegou.

Exemplo:

```text
Inputs recebidos: 3 de 4
Falta: Projeto executivo
```

Mas, se um input é obrigatório para iniciar o processo, a primeira tarefa não deve começar como se a informação existisse.

No D0:

```text
Criar atividade incompleta = permitido
Iniciar processo com input obrigatório faltante = bloqueado
```

A interface precisa dizer o que falta.

---

# 11. Output

Output é a entrega principal produzida pelo processo.

No D0, cada versão de processo possui **um output principal**.

Exemplo:

```text
Proposta comercial pronta para envio ao cliente
```

Output deve ser escrito como resultado verificável.

Evitar:

```text
Elaborar proposta
```

Preferir:

```text
Proposta comercial pronta para envio
```

---

# 12. Evidência do output

O processo pode dizer como a entrega será comprovada.

Exemplos:

```text
Arquivo
Link
Checklist
Confirmação simples
```

No D0, não é necessário suportar dezenas de tipos.

---

# 13. Critério de aceite

Critério de aceite responde:

> Como sei que esse output está realmente pronto?

Exemplo — orçamento:

```text
Escopo revisado
Valores revisados
Condições comerciais preenchidas
Aprovação realizada
```

Critério pode ser:

```text
Obrigatório
Opcional
```

---

# 14. Critério obrigatório e conclusão

Se uma atividade utiliza processo:

```text
Critério obrigatório não atendido
=
atividade não pode ser concluída normalmente
```

A LPS deve explicar o motivo:

```text
Não é possível concluir.
Falta atender: Aprovação realizada.
```

Isso é melhor do que permitir que `Concluído` signifique coisas diferentes para cada pessoa.

---

# 15. Fluxo padrão

O processo pode possuir um fluxo padrão de **tarefas**.

Exemplo:

```text
1. Levantamento — Comercial
2. Cotação — Compras
3. Precificação — Comercial
4. Revisão — Gestão
```

A LPS não deve chamar cada etapa de nova atividade.

A atividade é o resultado completo.

As etapas do processo viram tarefas da atividade.

---

# 16. Tarefa modelo x tarefa real

No cadastro do processo existe tarefa modelo.

```text
Tarefa modelo:
Realizar cotação
```

Ao aplicar o processo:

```text
Tarefa modelo
↓
Tarefa real
```

A tarefa real possui:

- executor;
- fila;
- prazo;
- tempo;
- devolução;
- histórico.

O modelo não possui execução.

---

# 17. Versionamento

Processos precisam de versão.

Exemplo:

```text
Elaborar orçamento
Versão 1
Versão 2
Versão 3
```

A identidade do processo continua a mesma.

A definição publicada muda por versão.

---

# 18. Rascunho x publicado

## Rascunho

Pode ser editado.

## Publicado

Não deve ser alterado retroativamente.

No D0, um processo possui uma única versão publicada atual. Ao publicar uma nova versão, a anterior passa a ser histórica/substituída para novas atividades, mas continua válida para as atividades antigas.

Se o usuário quiser mudar:

```text
Criar nova versão
```

Isso evita que atividades antigas mudem de significado.

---

# 19. Atividade guarda a versão aplicada

Exemplo:

```text
Atividade A
→ Processo Elaborar orçamento
→ Versão 2
```

Se a versão 3 for publicada amanhã:

```text
Atividade A continua na versão 2
```

Esse vínculo é obrigatório para auditoria e aprendizado.

---

# 20. Aplicação do processo na prática

Fluxo:

```text
Usuário cria atividade
↓
Seleciona processo
↓
LPS identifica versão publicada
↓
Registra processo_versao_id
↓
Prepara inputs da execução
↓
Cria tarefas reais
↓
Prepara critérios de aceite
↓
Mostra output esperado
```

A pessoa não deve cadastrar tudo novamente.

---

# 21. Regra de UX — Experiência do Usuário

A sofisticação fica na configuração.

A execução deve permanecer simples.

Quem executa precisa enxergar principalmente:

```text
O que recebi?
O que falta?
O que faço agora?
O que preciso entregar?
O que falta para concluir?
```

**UX — User Experience — Experiência do Usuário** é a forma como a pessoa percebe e realiza sua ação no sistema.

---

# 22. Onde cadastrar processo

Navegação:

```text
Cadastros
↓
Processos
```

Processo não fica em Configurações.

Motivo:

```text
Processo = algo cadastrado que a empresa utiliza
Configuração = regra de comportamento do sistema
```

---

# 23. Tela de lista de processos

Página completa.

Cabeçalho:

```text
Processos
Gerencie os modelos reutilizáveis da organização.

[+ Novo processo]
```

Tabela:

```text
Nome
Tipo de atividade
Inputs
Output
Fluxo
Versão
Status
Ações
```

Filtros:

```text
Busca
Tipo de atividade
Status
Empresa, se necessário
```

---

# 24. Novo processo abre modal grande

No desktop:

```text
aproximadamente 85% a 90% da largura da janela
até aproximadamente 90% da altura
```

Com:

- fundo da aplicação escurecido;
- cabeçalho fixo;
- conteúdo com rolagem interna;
- rodapé fixo;
- botão fechar;
- `Cancelar`;
- `Salvar rascunho`;
- `Publicar versão`.

No mobile, esse fluxo vira tela inteira.

---

# 25. Estrutura do modal de processo

```text
NOVO PROCESSO

[Informações básicas]

[Inputs]

[Output]

[Critérios de aceite]

[Fluxo padrão]

------------------------
Cancelar | Salvar rascunho | Publicar
```

As seções podem ser cartões grandes.

---

# 26. Evitar modal sobre modal

O modal de processo já é o ambiente de trabalho.

Ao clicar em `Adicionar input`, `Editar output` ou `Adicionar critério`, preferir:

- expansão inline;
- painel interno;
- troca de conteúdo dentro do mesmo modal;
- linha editável.

Evitar:

```text
Modal
↓
Modal
↓
Modal
```

---

# 27. Interação deve ser mais clicável que digitada

Sempre que possível:

- tipo = seleção;
- obrigatório = alternador;
- origem = seleção;
- setor = seleção;
- ordem = arrastar;
- status = alternador ou ação;
- versão = controlada pelo sistema.

Digitação fica para conteúdo que realmente precisa ser escrito.

---

# 28. Atividade com processo — visão de execução

Dentro da atividade, mostrar um resumo claro.

Exemplo:

```text
PROCESSO
Elaborar orçamento — v3

INPUTS
3 de 4 recebidos
Falta: projeto executivo

ENTREGA ESPERADA
Proposta comercial pronta para envio

CRITÉRIOS
2 de 4 atendidos

FLUXO
Levantamento ✓
Cotação ✓
Precificação em execução
Revisão pendente
```

O usuário não precisa abrir a configuração do processo para entender o que fazer.

---

# 29. Inputs na atividade

Mostrar primeiro a situação.

```text
Inputs: 3/4
```

Ao expandir:

```text
✓ Escopo
✓ Prazo
✓ Documentos complementares
✕ Projeto executivo
```

Ação principal:

```text
Adicionar o que falta
```

---

# 30. Output na atividade

A entrega esperada deve permanecer visível.

Exemplo:

```text
Entrega esperada:
Proposta comercial pronta para envio ao cliente
```

Isso reduz atividades executadas sem clareza sobre o resultado.

---

# 31. Critérios na atividade

Exemplo:

```text
✓ Escopo revisado
✓ Valores revisados
□ Condições comerciais preenchidas
□ Aprovação realizada
```

Critérios obrigatórios não atendidos precisam ficar claros antes de o usuário tentar concluir.

---

# 32. Conclusão

Ao clicar `Concluir atividade`, a LPS verifica:

```text
Existe processo?
↓
Sim
↓
Inputs obrigatórios foram tratados?
Output foi registrado?
Critérios obrigatórios estão atendidos?
```

Se faltar algo:

```text
Não é possível concluir ainda.

Faltam:
- Aprovação realizada
- Evidência da proposta
```

Sem mensagem genérica.

---

# 33. Processo e permissões

Ações mínimas:

```text
processo.visualizar
processo.criar
processo.editar_rascunho
processo.publicar
processo.criar_versao
processo.inativar
processo.aplicar
```

Participar de um setor não concede automaticamente permissão para publicar processos.

---

# 34. Processo e auditoria

Eventos relevantes:

- processo criado;
- rascunho alterado;
- versão publicada;
- nova versão criada;
- processo inativado;
- processo aplicado a atividade;
- input preenchido;
- input alterado;
- critério atendido;
- critério reaberto;
- evidência de output registrada;
- fluxo real desviou do padrão;
- atividade concluída.

---

# 35. Processo e aprendizado

Com histórico, a LPS poderá responder:

- quais inputs mais faltam;
- quanto tempo se perde aguardando input;
- quais critérios mais impedem conclusão;
- quais tarefas são sempre adicionadas manualmente;
- quais etapas nunca são utilizadas;
- qual versão reduziu tempo;
- qual versão reduziu devolução;
- onde o fluxo real diverge do padrão.

O processo deixa de ser apenas documentação.

Ele vira uma unidade de aprendizado operacional.

---

# 36. D0 — o que construir

Construir:

- lista de processos;
- criar processo;
- rascunho;
- publicar versão;
- nova versão;
- inputs simples;
- um output principal;
- critérios simples;
- fluxo linear com dependências básicas;
- aplicar em atividade;
- conclusão validando critérios;
- histórico de versão.

---

# 37. D0 — o que não construir

Não construir ainda:

- BPMN — Business Process Model and Notation, ou Notação e Modelagem de Processos de Negócio — completo;
- regras condicionais complexas;
- scripts customizados por processo;
- múltiplos formulários encadeados;
- motor de aprovação genérico;
- dezenas de tipos de input;
- fórmula dinâmica;
- automação por Inteligência Artificial;
- processo que se altera sozinho.

---

# 38. Critérios de aceite do módulo Processo

O módulo está funcional no D0 quando for possível:

```text
[ ] criar processo
[ ] salvar rascunho
[ ] cadastrar input obrigatório e opcional
[ ] definir output
[ ] cadastrar critério obrigatório e opcional
[ ] definir tarefas padrão
[ ] definir setores
[ ] publicar versão
[ ] criar atividade usando versão publicada
[ ] visualizar inputs faltantes
[ ] executar tarefas reais
[ ] registrar output
[ ] atender critérios
[ ] impedir conclusão quando critério obrigatório faltar
[ ] concluir atividade
[ ] publicar nova versão sem alterar atividade antiga
```

---

# 39. Regra de ouro

> **O processo deve aumentar clareza sobre o que precisa ser recebido e entregue. Se ele apenas adicionar campos e cliques, está piorando o trabalho.**

---

# 40. Controle de versão

| Versão | Descrição |
|---|---|
| 1.0 | Definição inicial consolidada de Processos, Inputs, Outputs, Critérios de Aceite, fluxo padrão, versionamento, aplicação em atividades e experiência de cadastro |
