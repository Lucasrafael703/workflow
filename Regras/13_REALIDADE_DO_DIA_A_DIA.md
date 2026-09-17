# 11 — Realidade do Dia a Dia

> Documento funcional para impedir que a LPS seja desenhada apenas com base em processos ideais.
>
> A empresa real possui interrupções, urgências, falhas de registro, atividades esquecidas, demandas verbais, decisões pendentes, retrabalho, revisões e trabalho não planejado.

---

# 1. Objetivo deste documento

Este documento registra comportamentos reais do dia a dia de uma construtora, instaladora ou empresa de engenharia.

A função deste arquivo é garantir que a LPS seja construída para funcionar em uma operação real, e não apenas em um processo perfeito.

A pergunta central é:

> **A LPS continua funcionando mesmo quando o dia sai do planejado?**

---

# 2. Princípio central

A operação real não acontece de forma linear.

Uma pessoa pode estar:

```text
fazendo orçamento
↓
ser chamada por outro setor
↓
receber uma ligação de cliente
↓
participar de uma decisão
↓
voltar para o orçamento
↓
descobrir que esqueceu de pausar
```

A LPS não deve depender de uma disciplina perfeita do usuário.

O sistema precisa tolerar:

- interrupções;
- esquecimentos;
- lançamentos retroativos;
- mudanças de prioridade;
- atividades não planejadas;
- trabalho verbal;
- dependências;
- revisões;
- devoluções;
- decisões pendentes;
- mudanças de rota.

---

# 3. A empresa é formada por estrutura e trabalho

A empresa possui:

```text
Empresa
↓
Setores
↓
Cargos
↓
Pessoas
↓
Atribuições
```

O trabalho possui:

```text
Atividades
↓
Tarefas
↓
Setor responsável
↓
Executor
↓
Prazo
↓
Execução
↓
Resultado
```

A LPS precisa relacionar essas duas estruturas.

---

# 4. Cargo não é apenas um nome

Um cargo precisa possuir atribuições.

Exemplo:

```text
Cargo:
Encarregado de Instalações
```

Pode possuir atribuições como:

- distribuir atividades;
- acompanhar execução;
- conferir qualidade;
- orientar equipe;
- validar serviços;
- apoiar planejamento;
- controlar materiais;
- reportar desvios.

Atribuições ajudam a entender:

- quais tarefas fazem sentido para aquela pessoa;
- quando uma demanda foi direcionada incorretamente;
- quem possui capacidade para executar;
- onde existe concentração de trabalho;
- onde existe falta de delegação.

---

# 5. Demanda deve nascer para o setor antes de nascer para a pessoa

Erro comum:

```text
"manda tudo para aquela pessoa"
```

Isso gera:

- sobrecarga;
- concentração;
- dependência;
- dificuldade de delegação;
- pessoas com o mesmo cargo trabalhando em níveis muito diferentes de carga.

Preferência:

```text
Demanda
↓
Setor responsável
↓
Fila do setor
↓
Distribuição para executor
```

A distribuição deve considerar:

- carga atual;
- prazos;
- atribuições;
- capacidade;
- disponibilidade;
- conhecimento necessário.

No início, a decisão pode ser humana.

Com histórico, a LPS pode sugerir distribuição.

---

# 6. Receber uma tarefa não significa aceitar a tarefa

Uma tarefa direcionada a uma pessoa não deve ser considerada automaticamente aceita.

Fluxo possível:

```text
Aguardando aceite
↓
Aceita
↓
Em fila
↓
Em execução
↓
Concluída
```

A pessoa precisa poder:

```text
[Aceitar]
[Questionar]
[Devolver]
[Propor outro prazo]
```

Exemplos de motivo de devolução:

- não é minha atribuição;
- setor incorreto;
- falta informação;
- não tenho capacidade no prazo;
- falta recurso;
- depende de outra definição;
- outro.

Texto livre deve ser complementar, não obrigatório para tudo.

---

# 7. Conversa não substitui estado oficial

Muitas demandas precisam de questionamento antes da execução.

Exemplo:

```text
"Essa atividade realmente pertence ao meu setor?"
```

A conversa deve existir dentro da atividade ou tarefa.

Porém:

```text
Mensagem
≠
mudança de estado
```

Se alguém escreve:

> "Pode deixar para amanhã."

o prazo oficial não deve ser alterado automaticamente.

A conversa fornece contexto.

A ação estruturada altera o processo.

---

# 8. Nem toda paralisação é igual

A LPS precisa diferenciar situações.

## 8.1 Pausada

A pessoa estava trabalhando e interrompeu temporariamente.

Exemplo:

```text
atividade em execução
↓
surge outra demanda
↓
atividade pausada
```

## 8.2 Aguardando

A pessoa não consegue avançar porque depende de algo externo.

Exemplos:

- aguardando cliente;
- aguardando fornecedor;
- aguardando documento;
- aguardando material;
- aguardando outro setor;
- aguardando aprovação;
- aguardando reunião;
- aguardando informação.

## 8.3 Aguardando decisão

Existe uma decisão necessária antes de continuar.

Exemplo:

```text
setor solicita posicionamento da gestão
↓
atividade fica aguardando decisão
```

## 8.4 Em revisão

A execução foi entregue, mas outra pessoa precisa validar.

## 8.5 Revisão solicitada

Quem valida não aceita o trabalho e devolve para correção.

---

# 9. Toda atividade parada precisa saber como volta

Um dos maiores riscos da operação não é iniciar uma atividade.

É lembrar de retomá-la.

Exemplo:

```text
fornecedor não veio hoje
↓
entrega fica para amanhã
↓
no dia seguinte ninguém lembra
```

Por isso, uma tarefa aguardando precisa possuir um gatilho de retorno.

Exemplos:

```text
retomar em determinada data/hora
```

ou:

```text
retomar quando outra tarefa for concluída
```

ou:

```text
retomar quando houver resposta externa
```

Regra:

> **Nenhuma tarefa deve parar sem existir uma forma clara de voltar para a atenção.**

---

# 10. Esquecimento de pausa faz parte da realidade

O usuário pode esquecer de pausar.

Exemplo:

```text
14:00 — iniciou orçamento
14:35 — foi ajudar outro setor
15:15 — voltou
16:00 — percebeu que não pausou
```

A LPS precisa permitir correção retroativa:

```text
Orçamento
14:00–14:35

Apoio a outro setor
14:35–15:15

Orçamento
15:15–16:00
```

O sistema deve registrar que houve ajuste retroativo.

O cronômetro não pode ser tratado como única verdade.

---

# 11. Nem tudo que acontece é uma tarefa planejada

O dia real possui:

- ligações;
- conversas;
- reuniões rápidas;
- solicitações verbais;
- problemas inesperados;
- dúvidas;
- decisões;
- alinhamentos.

Nem sempre é possível saber, no início, se aquilo vai gerar trabalho.

Exemplo:

```text
cliente liga
↓
conversa acontece
↓
somente no final fica claro que surgiram novas ações
```

A LPS precisa permitir registrar uma interação depois que ela aconteceu.

---

# 12. Interações

Uma interação pode ser registrada como:

```text
Ligação
Reunião
Conversa
Visita
Mensagem relevante
```

Campos mínimos:

- tipo;
- data/hora;
- duração aproximada ou exata;
- contexto;
- resultado.

Depois:

```text
Isso gerou alguma ação?
```

Opções:

```text
[Criar tarefa]
[Registrar decisão]
[Não gerou ação]
```

A interação pode existir sem virar tarefa.

---

# 13. Trabalho planejado x trabalho não planejado

A LPS precisa diferenciar:

## Trabalho planejado

Já estava na fila.

## Trabalho não planejado

Apareceu durante o dia.

Exemplos:

- cliente ligou;
- veículo quebrou;
- material precisou ser buscado;
- outro setor pediu ajuda;
- diretor pediu análise;
- fornecedor alterou entrega.

Isso ajuda a explicar por que o planejado não foi concluído.

Sem essa separação, o gestor pode interpretar incorretamente falta de entrega como baixa produtividade.

---

# 14. Revisões fazem parte do fluxo

Uma tarefa concluída pode precisar ser validada.

Exemplo:

```text
Área responsável executa
↓
Área solicitante revisa
↓
Aprova
OU
Solicita revisão
```

Fluxo:

```text
Executar
↓
Enviar para revisão
↓
Aprovar
OU
Solicitar revisão
↓
Corrigir
↓
Reenviar
```

A LPS precisa preservar:

- versão;
- quem executou;
- quem revisou;
- motivo da devolução;
- data;
- quantidade de revisões;
- tempo adicional causado pelo retrabalho.

---

# 15. Modelos reutilizáveis

Atividades recorrentes não devem ser reconstruídas do zero.

Exemplo:

```text
Processo:
Criar ou atualizar descrição de cargo
```

Pode gerar tarefas padrão:

```text
1. Agendar reunião
2. Levantar atribuições
3. Elaborar documento
4. Revisar
5. Corrigir, se necessário
6. Aprovar
7. Finalizar
```

Na próxima vez:

```text
Nova atividade
↓
Selecionar modelo
↓
Gerar tarefas padrão
↓
Ajustar somente o necessário
```

A pessoa não deve digitar novamente o que a empresa já aprendeu.

---

# 16. O sistema deve capturar dados através da ação

Evitar pedir:

```text
"descreva tudo que você fez"
```

Preferir capturar automaticamente quando a pessoa:

- aceita;
- inicia;
- pausa;
- retoma;
- devolve;
- questiona;
- aprova;
- solicita revisão;
- conclui;
- muda prazo;
- agenda retorno;
- move entre setores.

O usuário trabalha.

A LPS registra.

---

# 17. Digitação precisa ser exceção

As pessoas não possuem tempo para escrever relatórios durante todo o dia.

Preferir:

- botões;
- opções rápidas;
- motivos pré-cadastrados;
- seleção de pessoas;
- seleção de setor;
- modelos;
- histórico reutilizável;
- preenchimento automático;
- voz para captura rápida;
- sugestões baseadas no histórico.

Texto livre deve existir quando realmente acrescentar contexto.

---

# 18. Exemplo de operação real

Uma pessoa começa:

```text
08:00 — orçamento
```

Depois:

```text
09:15 — outro setor pede ajuda
```

Depois:

```text
09:45 — cliente liga
```

A ligação gera:

```text
decisão necessária da gestão
```

A decisão não vem.

Então:

```text
atividade fica aguardando decisão
```

Mais tarde:

```text
fornecedor informa atraso
```

Outra tarefa fica:

```text
aguardando fornecedor
retomar amanhã
```

No final do dia, o sistema precisa conseguir reconstruir o que aconteceu sem depender somente da memória da pessoa.

---

# 19. O sistema não deve presumir um mundo perfeito

A LPS não deve depender de:

- todo mundo lembrar de iniciar;
- todo mundo lembrar de pausar;
- todo mundo registrar imediatamente;
- toda tarefa ser prevista antes de começar;
- todo processo seguir o fluxo original;
- toda entrega ser aprovada na primeira tentativa;
- toda demanda chegar pelo sistema;
- toda pessoa aceitar corretamente o que recebeu;
- todos os prazos serem realistas;
- todas as prioridades permanecerem estáveis.

Essas situações são exceções apenas no desenho.

Na operação real, elas são rotina.

---

# 20. Perguntas que a LPS precisa responder

Ao longo do dia:

> O que preciso fazer agora?

Depois de uma interrupção:

> O que eu estava fazendo antes?

Ao voltar no dia seguinte:

> O que ficou aguardando e precisa ser retomado?

Para o gestor:

> O que minha equipe fez hoje?

> O que está parado?

> Por que está parado?

> Quem precisa agir?

> O que surgiu fora do planejado?

> Onde existe sobrecarga?

> Quem está com pouca carga?

> Quantas atividades voltaram para revisão?

> Quais tarefas são esquecidas depois de uma espera?

---

# 21. Regra final

A LPS não deve funcionar apenas quando o usuário se adapta ao sistema.

O sistema precisa se adaptar à realidade operacional.

A regra é:

> **A LPS deve continuar útil mesmo quando o dia sai completamente do planejado.**
