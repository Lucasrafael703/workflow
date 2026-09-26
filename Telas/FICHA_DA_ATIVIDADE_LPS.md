# Ficha da Atividade — LPS

## Objetivo

A ficha da atividade é a tela principal para acompanhar e conduzir uma atividade.

Ela deve permitir entender rapidamente:

- o que precisa acontecer;
- quem é o responsável;
- qual é o prazo;
- onde existe bloqueio;
- quais tarefas compõem a atividade;
- o que aconteceu na conversa e no histórico.

---

## 1. Cabeçalho

Exibe as informações principais da atividade:

- Nome da atividade
- Cliente
- Obra
- Centro de custo
- Status
- Prioridade
- Responsável
- Prazo

Quando houver atraso, a tela deve mostrar de forma clara, por exemplo:

**Atrasada há 4 dias**

A principal ação do cabeçalho é:

**+ Adicionar tarefa**

---

## 2. Situação atual

Resumo operacional da atividade.

Exibe:

- quantidade de tarefas concluídas;
- tarefas em fila;
- tarefas em execução;
- tarefas bloqueadas;
- setores envolvidos.

Quando existir um problema relevante, a LPS deve destacá-lo como **Próxima atenção**.

Exemplo:

**Gerar lista de materiais — Bloqueada**

Sempre que possível, deve existir uma ação direta, como:

**Resolver bloqueio**

---

## 3. Tarefas

A atividade possui uma lista de tarefas em formato de tabela.

Colunas principais:

- Tarefa
- Setor
- Executor
- Prazo
- Status
- Posição na fila

A linha inteira deve ser clicável e abrir os detalhes da tarefa sem perder o contexto da atividade.

---

## 4. Conversa

Painel lateral destinado à comunicação relacionada à atividade.

Permite:

- escrever mensagens;
- mencionar usuários;
- anexar arquivos;
- registrar decisões e atualizações.

A conversa não substitui o histórico oficial da atividade.

---

## 5. Histórico

O histórico registra os acontecimentos importantes da atividade.

Exemplos:

- mudança de responsável;
- mudança de prazo;
- bloqueio ou desbloqueio;
- entrada ou mudança na fila;
- início e conclusão de tarefas;
- alteração de status;
- devoluções;
- decisões relevantes.

O histórico deve mostrar **quem fez, o que aconteceu e quando aconteceu**.

---

## 6. Detalhes da atividade

Área compacta e recolhível com informações cadastrais.

Pode conter:

- Cliente
- Obra
- Centro de custo
- Empresa
- Processo
- Criador
- Data de criação
- Descrição

Campos sem informação não devem ocupar espaço desnecessário.

---

## Princípio da tela

A hierarquia da ficha deve seguir:

**Atividade → Situação atual → Problema → Tarefas → Conversa → Detalhes → Histórico**

A ficha não deve parecer um formulário de cadastro.

Ela deve funcionar como uma **central de comando da atividade**.
