# LPS — Especificação Completa das Colunas Dinâmicas

## 1. Objetivo

Este documento define o padrão oficial de **colunas dinâmicas da LPS**.

A coluna é uma das peças centrais do novo motor de Quadros.

A ideia é simples:

```text
Quadro
├── Colunas
├── Itens
└── Visualizações
```

Cada coluna define:

- qual informação existe;
- qual é o tipo da informação;
- como o usuário preenche;
- como o valor aparece;
- como o valor é validado;
- como pode ser filtrado;
- como pode ser ordenado;
- como pode ser agrupado;
- como aparece no Kanban;
- como aparece no Calendário;
- como pode participar de Fórmulas;
- quais permissões controlam sua edição e visualização.

A coluna não pertence exclusivamente à Tabela.

Ela pertence ao **Quadro**.

Tabela, Kanban e Calendário usam a mesma coluna e o mesmo valor.

---

# 2. Regra principal

> Um dado deve existir uma única vez e ser apresentado de formas diferentes pelas visualizações.

Exemplo:

```text
Coluna: Status
Valor: Em andamento
```

Na Tabela:

```text
| Em andamento |
```

No Kanban:

```text
coluna "Em andamento"
```

No Calendário:

```text
card com etiqueta "Em andamento"
```

No filtro:

```text
Status = Em andamento
```

Não criar uma versão do Status para cada tela.

---

# 3. Situação atual da LPS × nova arquitetura

Na LPS atual, `Activity` e `Task` ainda possuem vários campos definidos diretamente no código e no banco de dados.

Exemplos atuais:

```text
Activity.owner
Activity.requested_by
Activity.sector
Activity.client
Activity.site
Activity.status
Activity.urgency
Activity.requested_deadline

Task.responsavel
Task.sector
Task.status
Task.requested_deadline
Task.committed_deadline
```

Na nova arquitetura, esses conceitos passam a ser apresentados por um **motor comum de colunas**.

Exemplo:

```text
Responsável       → Pessoas
Solicitante       → Pessoas
Setor             → Relação
Cliente           → Relação
Obra              → Relação
Prazo             → Data
Valor da proposta → Moeda
Status            → Status
Prioridade        → Prioridade
Margem            → Fórmula
```

Isso permite adicionar novos campos sem criar nova tela e sem alterar o banco para cada pequena necessidade de negócio.

---

# 4. Tipos-base oficiais da LPS

A primeira arquitetura deve trabalhar com 13 tipos-base:

```text
1. Texto
2. Número
3. Moeda
4. Data
5. Pessoas
6. Status
7. Lista suspensa
8. Prioridade
9. Confirmação
10. Arquivo
11. Relação
12. Cronograma
13. Fórmula
```

Esses são os tipos fundamentais.

Colunas de negócio são construídas sobre eles.

Exemplo:

```text
"Responsável" não é um tipo.
É uma coluna do tipo Pessoas.

"Cliente" não é um tipo.
É uma coluna do tipo Relação.

"Valor da proposta" não é um tipo.
É uma coluna do tipo Moeda.
```

---

# 5. Estrutura conceitual de uma coluna

Toda coluna deve possuir propriedades comuns.

Exemplo conceitual:

```text
Column

id
board_id
name
type
position
width
required
description
is_visible
is_active
settings
created_at
updated_at
```

## 5.1 `id`

Identificador interno e imutável.

O nome visível nunca deve ser usado como identidade técnica.

## 5.2 `board_id`

Quadro ao qual a coluna pertence.

## 5.3 `name`

Nome mostrado ao usuário.

Exemplos:

```text
Responsável
Prazo
Cliente
Valor
Status
```

Pode ser renomeado sem quebrar dados.

## 5.4 `type`

Define o comportamento da coluna.

Exemplos:

```text
TEXT
NUMBER
MONEY
DATE
PEOPLE
STATUS
DROPDOWN
PRIORITY
CONFIRMATION
FILE
RELATION
TIMELINE
FORMULA
```

## 5.5 `position`

Define a ordem da coluna.

A ordem deve ser alterável por arrastar e soltar.

## 5.6 `width`

Largura visual da coluna na Tabela.

Deve ser persistida.

## 5.7 `required`

Indica se o valor é obrigatório em criação/edição.

## 5.8 `description`

Ajuda contextual da coluna.

Exemplo:

```text
Prazo comprometido de entrega ao solicitante.
```

## 5.9 `is_visible`

Controla se a coluna aparece na visualização atual.

Não significa exclusão.

## 5.10 `is_active`

Permite desativação lógica.

## 5.11 `settings`

Guarda configurações específicas de cada tipo.

Exemplo de Data:

```json
{
  "show_time": true,
  "date_format": "DD/MM/YYYY"
}
```

Exemplo de Pessoas:

```json
{
  "multiple": false
}
```

---

# 6. Regras comuns a todas as colunas

Toda coluna deve seguir as mesmas regras de experiência, exceto onde o tipo exigir comportamento diferente.

---

## 6.1 Criar coluna

Fluxo:

```text
[ + ]

Pesquisar ou descrever sua coluna

Status
Texto
Pessoas
Lista suspensa
Data
Números
...
```

O usuário escolhe o tipo.

A coluna aparece imediatamente.

Não abrir uma página separada.

---

## 6.2 Renomear

O nome deve ser editável inline.

Fluxo:

```text
Status
```

clicou:

```text
[ Status ]
```

digitou:

```text
Etapa comercial
```

Enter:

```text
Etapa comercial
```

Autosave.

---

## 6.3 Mover

A coluna deve poder ser arrastada horizontalmente.

Exemplo:

```text
Cliente | Responsável | Status | Prazo
```

vira:

```text
Cliente | Status | Responsável | Prazo
```

A ordem é salva automaticamente.

---

## 6.4 Redimensionar

O usuário arrasta a divisória lateral do cabeçalho.

Exemplo:

```text
| Responsável                   |
```

pode virar:

```text
| Responsável |
```

A largura é persistida.

---

## 6.5 Autoajuste

Duplo clique na divisória pode ajustar automaticamente a largura conforme o conteúdo.

---

## 6.6 Ordenar

Toda coluna ordenável deve oferecer:

```text
Ordenar crescente
Ordenar decrescente
Remover ordenação
```

Cada tipo define sua lógica de comparação.

---

## 6.7 Filtrar

Toda coluna filtrável deve abrir um filtro coerente com seu tipo.

Exemplos:

Texto:

```text
contém
não contém
é igual a
está vazio
```

Número:

```text
maior que
menor que
entre
igual a
```

Data:

```text
antes de
depois de
entre
hoje
esta semana
atrasado
```

Pessoas:

```text
contém Ryan
não contém Ryan
está vazio
```

---

## 6.8 Agrupar por

Tipos categóricos podem ser usados para agrupamento.

Exemplos:

```text
Status
Prioridade
Pessoa
Setor
Cliente
Lista suspensa
```

Tipos como Texto livre não devem ser a primeira opção para agrupamento.

---

## 6.9 Duplicar coluna

Duplica:

- tipo;
- configurações;
- opções;
- largura;
- validações.

Por padrão, não duplica os valores dos itens.

Uma opção futura pode permitir duplicar também valores.

---

## 6.10 Adicionar coluna à direita

A partir do menu:

```text
Adicionar coluna à direita
```

Abre o seletor de tipos sem mudar de tela.

---

## 6.11 Alterar tipo

Só deve ser permitido entre tipos compatíveis ou após validação de conversão.

Exemplos seguros:

```text
Número → Moeda
Texto → Número, somente se todos os valores forem válidos
Data → Data com hora
```

Exemplos perigosos:

```text
Pessoas → Número
Arquivo → Data
```

Nesses casos, bloquear ou exigir uma migração explícita.

---

## 6.12 Ocultar

Ocultar não exclui a coluna.

A coluna continua existindo e pode alimentar:

- filtros;
- Fórmulas;
- Kanban;
- Calendário;
- automações.

---

## 6.13 Excluir

Exclusão deve exigir confirmação.

Se houver dados históricos, Fórmulas ou automações usando a coluna:

```text
Esta coluna é usada por:
- 2 Fórmulas
- 1 visualização
- 3 filtros salvos
```

O sistema deve impedir exclusão insegura ou solicitar tratamento das dependências.

---

## 6.14 Autosave

Não criar botão geral:

```text
Salvar coluna
```

Pequenas mudanças devem ser persistidas automaticamente.

---

# 7. Modo de apresentação geral

A mesma coluna possui diferentes formas de apresentação.

---

## 7.1 Tabela

Exibe uma célula por item.

Exemplo:

```text
| Status       |
| Em andamento |
| Concluído    |
```

---

## 7.2 Kanban

Pode:

- ser usada para agrupar;
- aparecer dentro do cartão;
- ser editada pelo próprio cartão.

---

## 7.3 Calendário

Colunas de Data podem posicionar o item.

Outras colunas aparecem como informações do cartão.

---

## 7.4 Formulário de criação

O tipo determina o componente de entrada.

Exemplo:

Pessoas:

```text
Pesquisar pessoa...
```

Data:

```text
Calendário
```

Status:

```text
Lista de etiquetas
```

---

## 7.5 Drawer de detalhes

A coluna aparece como campo editável no detalhe do item.

---

# 8. Coluna Texto

## 8.1 Objetivo

Guardar uma informação textual curta e livre.

Exemplos:

```text
Código externo
Número do pedido
Objeto resumido
Observação curta
Nome complementar
```

---

## 8.2 Armazenamento

String.

---

## 8.3 Edição

Diretamente na célula.

Fluxo:

```text
clicar → digitar → Enter
```

---

## 8.4 Apresentação na Tabela

Texto simples.

Se for muito longo:

```text
Instalação elétrica do ...
```

Tooltip mostra o valor completo.

---

## 8.5 Apresentação no Kanban

Pode aparecer como linha textual.

Evitar mais de duas linhas no cartão.

---

## 8.6 Apresentação no Calendário

Pode aparecer como informação secundária.

Não deve dominar o cartão.

---

## 8.7 Filtros

```text
contém
não contém
é igual a
começa com
termina com
está vazio
não está vazio
```

---

## 8.8 Ordenação

Alfabética.

---

## 8.9 Resumo

Não possui soma ou média.

Pode oferecer contagem de preenchidos.

---

## 8.10 Regra

Texto não deve ser usado para armazenar números que precisam ser calculados.

Errado:

```text
"1500000"
```

para Valor.

Correto:

```text
Moeda = 1.500.000
```

---

# 9. Coluna Número

## 9.1 Objetivo

Guardar valores numéricos calculáveis.

Exemplos:

```text
Quantidade
Probabilidade
Número de lotes
Horas previstas
Pontos
Percentual
```

---

## 9.2 Armazenamento

Número decimal.

---

## 9.3 Edição

Inline.

Aceitar apenas números válidos.

---

## 9.4 Configurações

```text
Casas decimais
Separador
Prefixo
Sufixo
Valor mínimo
Valor máximo
```

Exemplo:

```text
85 %
```

---

## 9.5 Apresentação na Tabela

Formatada conforme configuração.

---

## 9.6 Filtros

```text
igual
diferente
maior que
menor que
maior ou igual
menor ou igual
entre
está vazio
```

---

## 9.7 Ordenação

Numérica.

Nunca lexicográfica.

Correto:

```text
2
10
100
```

e não:

```text
10
100
2
```

---

## 9.8 Resumo

Pode oferecer:

```text
Soma
Média
Mínimo
Máximo
Contagem
```

---

## 9.9 Fórmulas

Pode ser entrada e resultado de Fórmulas.

---

# 10. Coluna Moeda

## 10.1 Objetivo

Representar valores financeiros.

Exemplos:

```text
Valor da proposta
Custo
Contrato
Saldo
Valor medido
Orçamento
```

---

## 10.2 Base técnica

Pode compartilhar motor com Número, mas deve ser um tipo explícito para o usuário.

---

## 10.3 Configurações

```text
Moeda
Casas decimais
Exibir símbolo
Formato
```

Inicial:

```text
BRL — Real brasileiro
```

BRL significa **Brazilian Real**, código internacional do Real brasileiro.

---

## 10.4 Apresentação

```text
R$ 1.250.000,00
```

---

## 10.5 Filtros

Mesmos de Número.

---

## 10.6 Resumo

```text
Soma
Média
Mínimo
Máximo
```

---

## 10.7 Fórmulas

Pode participar de:

```text
Saldo = Contrato - Medido
```

---

# 11. Coluna Data

## 11.1 Objetivo

Guardar Data e, opcionalmente, horário.

Exemplos:

```text
Prazo
Data de envio
Visita técnica
Data de entrega
Próximo feedback
```

---

## 11.2 Regra central

Data e Data + hora são a mesma família de campo.

Não exigir uma coluna separada para Hora.

---

## 11.3 Configuração

```text
Exibir horário: Sim/Não
Formato da data
Permitir finais de semana
Definir como prazo
```

---

## 11.4 Sem horário

```text
15/10/2026
```

---

## 11.5 Com horário

```text
15/10/2026 14:00
```

---

## 11.6 Edição

Popover contextual com calendário.

O usuário não sai da tela.

---

## 11.7 Adicionar horário

Ícone de relógio.

Ao clicar:

```text
Horário opcional
```

---

## 11.8 Apresentação na Tabela

Compacta.

```text
15/10/2026
```

ou:

```text
15/10/2026 14:00
```

---

## 11.9 Kanban

Pode aparecer como chip:

```text
📅 15/10/2026
```

---

## 11.10 Calendário

Pode ser a coluna que posiciona o item no dia.

---

## 11.11 Filtros

```text
antes de
depois de
entre
hoje
amanhã
esta semana
este mês
atrasado
está vazio
```

---

## 11.12 Ordenação

Cronológica.

---

## 11.13 Fórmulas

Pode participar de cálculos de Data.

Exemplo:

```text
Dias restantes = Prazo - Hoje
```

---

# 12. Coluna Pessoas

## 12.1 Objetivo

Relacionar um item a usuários reais da organização.

Não é texto livre.

---

## 12.2 Exemplos

```text
Responsável
Solicitante
Aprovador
Participantes
Supervisor
Engenheiro responsável
```

---

## 12.3 Configuração

```text
Permitir:
- uma pessoa
- várias pessoas
```

---

## 12.4 Uma pessoa

Exemplo:

```text
Responsável
[ PB Paulo Biasi ]
```

---

## 12.5 Várias pessoas

Exemplo:

```text
Participantes
[ Ryan ] [ Luan ] [ Jennifer ]
```

---

## 12.6 Seleção

Popover:

```text
Pesquisar pessoas...

Ryan
Luan
Jennifer
Guilherme
```

---

## 12.7 Regra de identidade

Salvar `user_id`, não o nome digitado.

Se Ryan mudar o nome exibido, o vínculo continua correto.

---

## 12.8 Apresentação na Tabela

Avatar + nome.

Em pouco espaço:

```text
PB
```

ou:

```text
PB Paulo
```

---

## 12.9 Kanban

Pode aparecer como:

```text
PB Paulo
```

ou apenas avatar.

---

## 12.10 Calendário

Pode aparecer de forma compacta.

---

## 12.11 Filtros

```text
é Paulo
contém Ryan
não contém Ryan
é Eu
está vazio
```

---

## 12.12 Agrupamento

Pode agrupar por Pessoa.

Exemplo:

```text
Ryan
Luan
Jennifer
```

---

## 12.13 Permissões

O seletor só deve mostrar pessoas dentro do escopo permitido.

---

## 12.14 Importante

Uma coluna Pessoas não significa automaticamente "Responsável".

O significado é definido pelo nome da coluna e pela regra de negócio.

---

# 13. Coluna Status

## 13.1 Objetivo

Representar estado ou etapa de fluxo.

Exemplos:

```text
Não iniciado
Em andamento
Aguardando cliente
Em revisão
Concluído
```

---

## 13.2 Estrutura

Cada opção deve possuir:

```text
id
name
color
order
is_active
behavior opcional
```

---

## 13.3 Identidade estável

O ID nunca muda ao renomear.

Exemplo:

```text
id = 42
nome = Working on it
```

usuário altera:

```text
nome = Trabalhando nisso
```

continua:

```text
id = 42
```

---

## 13.4 Cor

A cor pertence à opção.

Alterar a cor deve atualizar todas as visualizações.

---

## 13.5 Edição

Clique na célula.

Popover:

```text
Trabalhando nisso
Parado
Concluído
+ Nova etiqueta
Editar etiquetas
```

---

## 13.6 Renomear

Pode ser feito sem sair da tela.

---

## 13.7 Alterar cor

Paleta visual inline.

---

## 13.8 Ordenação

Por ordem configurada das opções.

Não alfabeticamente.

---

## 13.9 Filtro

```text
é
não é
está em
não está em
está vazio
```

---

## 13.10 Agrupamento

É um dos principais tipos para agrupar Tabela e Kanban.

---

## 13.11 Kanban

Pode ser usado como coluna de agrupamento.

Mover um cartão entre grupos altera o valor da coluna Status configurada para aquele Kanban.

---

## 13.12 Cuidado arquitetural

Status visual configurável e estado de negócio crítico não devem ser confundidos sem uma regra explícita.

---

# 14. Coluna Lista suspensa

## 14.1 Objetivo

Classificar itens em opções configuráveis que não necessariamente representam fluxo.

Exemplos:

```text
Disciplina
Tipo de orçamento
Região
Categoria
Modalidade
Tipo de contrato
```

---

## 14.2 Diferença para Status

Status:

```text
Não iniciado → Em andamento → Concluído
```

Lista:

```text
Elétrica
Hidráulica
Mecânica
Civil
```

A Lista não exige uma sequência de progresso.

---

## 14.3 Configuração

Pode permitir:

```text
seleção única
seleção múltipla
```

---

## 14.4 Edição

Popover com opções.

---

## 14.5 Apresentação

Chips.

Exemplo:

```text
[ Elétrica ]
```

ou:

```text
[ Elétrica ] [ Dados ] [ SDAI ]
```

SDAI significa **Sistema de Detecção e Alarme de Incêndio**.

---

## 14.6 Filtros

```text
contém
não contém
é
não é
está vazio
```

---

## 14.7 Agrupamento

Permitido.

---

# 15. Coluna Prioridade

## 15.1 Objetivo

Representar importância relativa para decisão e organização do trabalho.

---

## 15.2 Valores iniciais

```text
Alta
Média
Baixa
```

Pode existir:

```text
Crítica
```

se houver necessidade real.

Evitar dez níveis.

---

## 15.3 Apresentação

Chip com ícone e cor.

```text
🔴 Alta
🟣 Média
🔵 Baixa
```

A interface não deve depender só da cor.

---

## 15.4 Ordenação

Ordem semântica:

```text
Crítica
Alta
Média
Baixa
```

---

## 15.5 Filtros

```text
é
não é
está em
está vazio
```

---

## 15.6 Agrupamento

Permitido.

---

## 15.7 Regra

Prioridade não deve virar mecanismo de pressão indiscriminada.

Se tudo for Alta, a coluna perde valor.

---

# 16. Coluna Confirmação

## 16.1 Objetivo

Guardar estado binário.

Exemplo:

```text
Sim / Não
Feito / Não feito
Confirmado / Não confirmado
```

---

## 16.2 Apresentação

Checkbox ou ícone.

```text
☐
☑
```

---

## 16.3 Exemplos

```text
Visita realizada
Projeto recebido
Cliente respondeu
Contrato assinado
```

---

## 16.4 Filtro

```text
marcado
não marcado
```

---

## 16.5 Ordenação

Marcados e não marcados.

---

## 16.6 Fórmula

Pode ser usada como condição booleana.

Booleana significa uma informação com dois estados lógicos: verdadeiro ou falso.

---

## 16.7 Regra

Não usar Confirmação para substituir um fluxo complexo.

Se existem cinco estados, usar Status.

---

# 17. Coluna Arquivo

## 17.1 Objetivo

Associar documentos ao item.

---

## 17.2 Exemplos

```text
Projeto
Memorial
Proposta
Foto
Planilha
PDF
Contrato
```

---

## 17.3 Apresentação na Tabela

```text
📎 4 arquivos
```

ou chips compactos.

---

## 17.4 Ao clicar

Abrir painel contextual.

Não redirecionar para uma página genérica de arquivos.

---

## 17.5 Configuração

Pode aceitar:

```text
um arquivo
vários arquivos
tipos permitidos
tamanho máximo
```

---

## 17.6 Segurança

Download deve respeitar:

- login;
- organização;
- autorização do recurso.

Não servir arquivos por URL pública sem validação.

---

## 17.7 Filtro

Inicialmente:

```text
tem arquivo
não tem arquivo
```

---

## 17.8 Ordenação

Pode ordenar por quantidade ou presença.

---

# 18. Coluna Relação

## 18.1 Objetivo

Relacionar um item a outro registro real.

---

## 18.2 Exemplos

```text
Setor
Cliente
Obra
Centro de custo
Demanda vinculada
Fornecedor
Contrato
Pedido
```

---

## 18.3 Regra central

Não armazenar apenas o texto mostrado.

Armazenar o ID do objeto relacionado.

---

## 18.4 Exemplo

```text
Demanda vinculada:
Arena Center Norte
```

internamente:

```text
activity_id = 381
```

---

## 18.5 Tipos de relação

Primeira versão:

```text
1 para 1 lógico
1 para vários
vários para vários
```

A escolha depende da configuração.

---

## 18.6 Seleção

Popover com busca.

Exemplo:

```text
Pesquisar obra...

Arena Center Norte
Ascenty Sumaré
Santa Isabel
```

---

## 18.7 Apresentação

Nome do objeto relacionado.

Pode possuir ícone do tipo.

---

## 18.8 Clique

Abre o drawer do objeto relacionado.

Evitar navegação completa.

---

## 18.9 Filtro

Por objeto relacionado.

---

## 18.10 Agrupamento

Permitido para relações categóricas.

Exemplo:

```text
agrupar por Setor
```

---

## 18.11 Colunas especializadas construídas sobre Relação

```text
Setor
Cliente
Obra
Centro de custo
Demanda vinculada
Processo
```

Não criar um tipo primitivo diferente para cada uma.

---

# 19. Coluna Cronograma

## 19.1 Objetivo

Guardar um intervalo temporal com início e fim.

---

## 19.2 Exemplo

```text
10/10/2026 → 18/10/2026
```

---

## 19.3 Diferença para Data

Data:

```text
Entrega: 18/10
```

Cronograma:

```text
Execução: 10/10 → 18/10
```

---

## 19.4 Apresentação na Tabela

Barra ou texto compacto.

```text
10/10 → 18/10
```

---

## 19.5 Linha do tempo

Pode alimentar visualização futura de Linha do tempo.

---

## 19.6 Gantt

Pode alimentar visualização futura de Gantt.

Gantt é uma visualização de planejamento em barras horizontais distribuídas ao longo do tempo.

---

## 19.7 Filtros

```text
inicia antes de
inicia depois de
termina antes de
termina depois de
sobrepõe período
```

---

## 19.8 Regra

Cronograma de processo da LPS não deve tentar substituir ferramentas completas de planejamento de obra, como Microsoft Project, sem um objetivo claro.

---

# 20. Coluna Fórmula

## 20.1 Objetivo

Calcular um valor automaticamente a partir de outras colunas.

O usuário não digita o resultado.

---

## 20.2 Exemplos

Margem:

```text
(Valor - Custo) / Valor
```

Saldo:

```text
Contrato - Medido
```

Valor total:

```text
Quantidade * Preço unitário
```

Dias restantes:

```text
Prazo - Hoje
```

Percentual:

```text
Concluídas / Total
```

---

## 20.3 Regra principal

> Fórmula é somente leitura.

O usuário altera as entradas.

O resultado é recalculado.

---

## 20.4 Não é automação

Fórmula:

```text
calcula valor
```

Automação:

```text
executa ação
```

Fórmula não deve:

- criar tarefa;
- alterar Status;
- enviar notificação;
- trocar responsável;
- apagar registro.

---

## 20.5 Configuração

Exemplo:

```text
Fórmula:
[ Quantidade ] * [ Preço unitário ]

Resultado:
[ Moeda ]
```

---

## 20.6 Tipos de resultado

```text
Número
Moeda
Percentual
Texto
Data
Duração
Booleano
```

Booleano significa verdadeiro ou falso.

---

## 20.7 Apresentação na Tabela

Mesmo padrão do tipo resultante.

---

## 20.8 Kanban

Pode aparecer como informação do cartão.

---

## 20.9 Calendário

Pode aparecer no cartão, mas não deve posicionar o item se o resultado não for Data.

---

## 20.10 Filtros

Dependem do tipo resultante.

---

## 20.11 Ordenação

Depende do tipo resultante.

---

## 20.12 Agrupamento

Somente se o resultado for categórico e a operação for suportada.

---

## 20.13 Dependências

Se a Fórmula usa:

```text
Valor
Custo
```

essas colunas não podem ser excluídas silenciosamente.

---

## 20.14 Referência por ID

Internamente:

```text
column_id_41 - column_id_52
```

Não:

```text
"Valor" - "Custo"
```

Assim renomear uma coluna não quebra a Fórmula.

---

## 20.15 Ciclos

Bloquear:

```text
A = B + 1
B = A + 1
```

Isso é uma dependência circular.

---

## 20.16 Erros

Exibir erro compreensível:

```text
#DIV/0
```

pode ser apresentado ao usuário como:

```text
Não foi possível calcular: divisão por zero.
```

---

# 21. Campos de negócio da LPS

Abaixo, como os principais campos da LPS atual devem ser representados no novo motor.

| Campo de negócio | Tipo-base |
|---|---|
| Título | Texto |
| Responsável | Pessoas |
| Solicitante | Pessoas |
| Participantes | Pessoas |
| Status | Status |
| Prioridade/Urgência | Prioridade |
| Setor | Relação |
| Cliente | Relação |
| Obra | Relação |
| Centro de custo | Relação |
| Demanda vinculada | Relação |
| Prazo | Data |
| Prazo solicitado | Data |
| Prazo comprometido | Data |
| Valor | Moeda |
| Quantidade | Número |
| Probabilidade | Número |
| Disciplina | Lista suspensa |
| Tags | Lista suspensa ou tipo Tag especializado |
| Projeto recebido | Confirmação |
| Arquivos | Arquivo |
| Período de execução | Cronograma |
| Margem | Fórmula |

---

# 22. Demandas — conjunto inicial sugerido

Template inicial:

```text
Título
Solicitante
Responsável
Setor
Cliente
Obra
Status
Prioridade
Prazo
```

Extras:

```text
Valor
Probabilidade
Disciplina
Visita técnica
Arquivos
```

---

# 23. Tarefas — conjunto inicial sugerido

Template inicial:

```text
Título
Demanda vinculada
Responsável
Setor
Status
Prioridade
Prazo solicitado
Prazo comprometido
```

Extras:

```text
Participantes
Checklist
Arquivos
Cronograma
```

Checklist pode permanecer inicialmente como recurso especializado de Tarefa e não como tipo de coluna-base.

---

# 24. Coluna obrigatória

Uma coluna pode ser configurada como obrigatória.

Exemplo:

```text
Responsável: obrigatório
```

Na criação:

```text
Não é possível criar a tarefa sem Responsável.
```

Não permitir item inválido silenciosamente.

---

# 25. Valor padrão

Alguns tipos podem ter valor padrão.

Exemplo:

```text
Status padrão = Não iniciado
Prioridade padrão = Média
```

Não preencher valores como Responsável automaticamente sem regra explícita.

---

# 26. Validações

Toda coluna deve aceitar regras de validação compatíveis.

Exemplos:

Número:

```text
mínimo 0
máximo 100
```

Data:

```text
não permitir data anterior a hoje
```

Texto:

```text
máximo 100 caracteres
```

Relação:

```text
somente Obras ativas
```

---

# 27. Resumo de coluna

A Tabela pode mostrar resumo na parte inferior.

Número:

```text
Soma: 1.250
```

Moeda:

```text
Total: R$ 4.820.000
```

Status:

```text
3 Em andamento
5 Concluídos
```

Pessoas:

```text
5 pessoas
```

Data:

```text
Mais próxima: 05/10
```

Não forçar resumo onde não fizer sentido.

---

# 28. Colunas em visualizações

A configuração do Quadro define quais colunas existem.

Cada visualização define quais aparecem.

Exemplo:

Quadro:

```text
15 colunas
```

Tabela Comercial:

```text
9 visíveis
```

Kanban Gerencial:

```text
5 campos no cartão
```

Calendário:

```text
4 campos no cartão
```

Não duplicar coluna.

---

# 29. Configuração do cartão

Kanban e Calendário devem permitir:

```text
Clique ou arraste os campos que deseja mostrar.
```

Exemplo:

```text
Status
Responsável
Prazo
Valor
```

A ordem deve ser alterável por arrastar.

---

# 30. Edição contextual

Regra global:

> Se o valor puder ser editado no local em que está sendo visto, não abrir outra página.

Exemplos:

Status:

```text
clicar → escolher etiqueta
```

Pessoa:

```text
clicar → pesquisar pessoa
```

Data:

```text
clicar → calendário
```

Prioridade:

```text
clicar → escolher prioridade
```

Texto:

```text
clicar → digitar
```

---

# 31. Popovers

Tipos indicados para popover:

```text
Pessoas
Status
Lista suspensa
Prioridade
Data
Relação
Confirmação
```

---

# 32. Modal ou drawer

Usar para:

- configuração avançada da coluna;
- criação completa de item;
- detalhes completos;
- arquivos;
- Fórmula complexa;
- permissões;
- histórico.

---

# 33. Segurança

Colunas não podem ignorar a autorização da LPS.

Exemplo:

Se o usuário pode ver a Demanda, mas não editar:

```text
célula visível
edição bloqueada
```

---

# 34. Restrição de visualização

Futuro:

```text
Esta coluna pode ser vista por:
- gestores
- financeiro
```

Isso exige cuidado porque filtros, Fórmulas e exportações também precisam respeitar a restrição.

Não implementar apenas escondendo no HTML.

---

# 35. Restrição de edição

Exemplo:

```text
Valor final
Visualização: Comercial + Diretoria
Edição: Diretoria
```

A validação real deve ocorrer no servidor.

---

# 36. Multi-organização

Pessoas, Relações, Status e opções devem sempre respeitar a organização do Quadro.

Não permitir selecionar:

- pessoa de outra empresa;
- obra de outra organização;
- cliente de outro tenant;
- status pertencente a outro tenant.

Tenant significa a organização isolada dentro de uma aplicação multiempresa.

---

# 37. Auditoria

Mudanças relevantes em colunas de negócio devem ser auditáveis.

Exemplos:

```text
Responsável alterado
Prazo alterado
Status alterado
Prioridade alterada
Cliente alterado
Obra alterada
```

---

# 38. Alterações visuais

Mudanças exclusivamente visuais podem possuir auditoria simplificada.

Exemplos:

```text
largura
posição
visibilidade na view
```

Não precisam gerar notificação de negócio.

---

# 39. Notificações

Editar uma coluna não significa automaticamente notificar alguém.

Notificação é regra de negócio.

Exemplos que podem notificar:

```text
troca de Responsável
prazo alterado
Status crítico
```

Exemplos que não devem:

```text
largura aumentada
coluna movida
coluna ocultada
```

---

# 40. Fórmulas e permissões

Uma Fórmula não deve revelar informação de uma coluna que o usuário não possui autorização para enxergar.

Esse ponto exige desenho técnico antes de habilitar restrição por coluna.

---

# 41. Valores vazios

Cada tipo precisa possuir representação visual limpa.

Exemplo:

```text
—
```

ou célula vazia.

Não usar:

```text
null
None
undefined
```

na interface.

---

# 42. Campo vazio e filtro

Todos os tipos devem suportar:

```text
está vazio
não está vazio
```

quando fizer sentido.

---

# 43. Cópia e cola

Evolução desejável para a Tabela:

```text
Ctrl+C
Ctrl+V
```

com validação por tipo.

Não permitir colar texto inválido em Número sem aviso.

---

# 44. Exportação

Valores exportados devem manter o significado.

Exemplo:

Pessoas:

```text
Paulo Biasi
```

e não:

```text
user_id=42
```

Moeda:

```text
1250000.00
```

mais formatação conforme formato de exportação.

---

# 45. Pesquisa global

A pesquisa pode indexar:

```text
Texto
Status
Lista
Pessoas
Relações
```

Número, Data e Fórmula podem entrar de forma específica.

---

# 46. Campos não editáveis

Algumas colunas podem ser somente leitura.

Exemplos:

```text
Código da Demanda
Criado em
Criado por
Última atualização
Margem calculada
Dias em atraso
```

Esses campos podem usar tipos-base, mas com `editable = false`.

---

# 47. Colunas de sistema

Além das 13 colunas-base, o sistema pode expor campos técnicos:

```text
ID
Código
Criado em
Criado por
Atualizado em
```

Eles não devem aparecer no seletor principal de criação como colunas comuns, salvo em uma área:

```text
Campos do sistema
```

---

# 48. Colunas futuras

Não fazem parte da primeira versão obrigatória:

```text
E-mail
Telefone
Localização
Link
Avaliação
Dependência
Progresso
Espelhamento
Documento rico
Extração por IA
```

IA significa **Inteligência Artificial**.

Esses tipos podem ser adicionados depois sem quebrar o motor central.

---

# 49. Extração por IA

A opção "Extract info" vista no Monday não deve ser copiada como tipo-base agora.

Na LPS, isso deve ser uma capacidade futura:

```text
Extrair valor de documento
Extrair CNPJ
Extrair prazo
Extrair valor contratual
```

Pode preencher outras colunas.

Não deve ser confundida com Fórmula.

---

# 50. Documento

A opção "monday Doc" também não é coluna-base da primeira versão da LPS.

Documento rico pode ser um recurso futuro.

---

# 51. Regras de nomes

Evitar nomes genéricos:

```text
Campo 1
Campo 2
Info
Outro
```

Preferir:

```text
Prazo de entrega
Responsável
Valor da proposta
Setor responsável
```

---

# 52. Duplicidade de nomes

O sistema pode permitir duas colunas visualmente iguais, mas isso gera confusão.

Recomendação:

```text
Status comercial
Status operacional
```

em vez de:

```text
Status
Status
```

---

# 53. Dependências de exclusão

Antes de excluir uma coluna, verificar:

- Fórmulas;
- filtros;
- agrupamentos;
- automações;
- visualizações;
- relatórios;
- integrações.

---

# 54. Soft delete

Soft delete significa exclusão lógica, mantendo o registro técnico e histórico.

Para colunas já utilizadas, preferir:

```text
is_active = false
```

em vez de apagamento físico imediato.

---

# 55. Performance

A Tabela pode possuir muitas colunas.

Regras:

- carregar apenas valores necessários;
- evitar consulta por célula;
- usar pré-carregamento de Pessoas e Relações;
- calcular Fórmulas de forma eficiente;
- indexar campos de busca e filtros mais usados.

---

# 56. Responsividade

No desktop:

- arrastar;
- redimensionar;
- edição inline.

No mobile:

- priorizar as colunas selecionadas;
- permitir scroll horizontal;
- abrir popovers como drawers;
- evitar células minúsculas.

---

# 57. Acessibilidade

Nunca usar apenas cor.

Status deve mostrar:

```text
● Em andamento
```

e não apenas um quadrado azul.

Pessoas devem ter nome acessível mesmo com avatar.

---

# 58. Teclado

Comportamentos desejados:

```text
Enter  = editar/confirmar
Esc    = cancelar/fechar
Tab    = próxima célula
Shift+Tab = célula anterior
```

---

# 59. Regra de UX

UX significa **User Experience**, ou experiência do usuário.

A regra central da LPS:

> O usuário clica na informação que quer mudar e altera ali.

Não:

```text
clicar
abrir tela
procurar formulário
editar
salvar
voltar
```

Mas:

```text
clicar
alterar
pronto
```

---

# 60. Regra de produto

As colunas são blocos reutilizáveis.

Não desenvolver novamente:

```text
seletor de Pessoa para Demandas
seletor de Pessoa para Tarefas
seletor de Pessoa para Compras
```

Desenvolver:

```text
PeopleColumn
```

e reutilizar.

---

# 61. Contrato conceitual por tipo

Cada tipo de coluna deve implementar:

```text
render()
editor()
validate()
serialize()
deserialize()
sort()
filter()
summarize()
format()
```

Alguns também:

```text
group()
calculate()
```

---

# 62. Exemplo de arquitetura

```text
BaseColumnType
│
├── TextColumnType
├── NumberColumnType
├── MoneyColumnType
├── DateColumnType
├── PeopleColumnType
├── StatusColumnType
├── DropdownColumnType
├── PriorityColumnType
├── ConfirmationColumnType
├── FileColumnType
├── RelationColumnType
├── TimelineColumnType
└── FormulaColumnType
```

---

# 63. Critérios de aceite gerais

## COL-GER-001

O usuário consegue criar uma coluna sem sair do Quadro.

## COL-GER-002

O usuário consegue renomear inline.

## COL-GER-003

O usuário consegue mover por arrastar e soltar.

## COL-GER-004

O usuário consegue redimensionar.

## COL-GER-005

A posição e largura permanecem após recarregar.

## COL-GER-006

Toda alteração simples usa autosave.

## COL-GER-007

Filtros respeitam o tipo.

## COL-GER-008

Ordenação respeita o tipo.

## COL-GER-009

Ocultar não exclui dados.

## COL-GER-010

Excluir verifica dependências.

---

# 64. Critérios de aceite — Pessoas

## COL-PES-001

A coluna pode ser configurada para uma ou várias pessoas.

## COL-PES-002

A seleção busca apenas usuários válidos da organização.

## COL-PES-003

O banco guarda referência ao usuário, não apenas nome.

## COL-PES-004

Renomear a pessoa não quebra vínculos.

## COL-PES-005

A coluna pode ser filtrada por usuário.

## COL-PES-006

Pode ser usada para agrupamento.

---

# 65. Critérios de aceite — Status

## COL-STA-001

As opções possuem ID estável.

## COL-STA-002

Nome pode ser alterado inline.

## COL-STA-003

Cor pode ser alterada inline.

## COL-STA-004

Todas as visualizações refletem a mudança.

## COL-STA-005

Renomear não quebra automações ou filtros.

## COL-STA-006

Pode agrupar Kanban.

---

# 66. Critérios de aceite — Data

## COL-DAT-001

Data funciona sem horário.

## COL-DAT-002

Horário pode ser ativado opcionalmente.

## COL-DAT-003

Remover horário mantém a Data.

## COL-DAT-004

Pode alimentar o Calendário.

## COL-DAT-005

Ordenação é cronológica.

---

# 67. Critérios de aceite — Fórmula

## COL-FOR-001

O valor é calculado automaticamente.

## COL-FOR-002

O resultado é somente leitura.

## COL-FOR-003

Referências usam IDs de colunas.

## COL-FOR-004

Renomear coluna referenciada não quebra a Fórmula.

## COL-FOR-005

Dependência circular é bloqueada.

## COL-FOR-006

Excluir coluna referenciada é bloqueado até corrigir a Fórmula.

## COL-FOR-007

O resultado possui tipo definido.

---

# 68. Critérios de aceite — Relação

## COL-REL-001

O valor referencia um objeto real.

## COL-REL-002

O usuário consegue pesquisar objetos.

## COL-REL-003

Objetos de outro tenant não aparecem.

## COL-REL-004

Clicar pode abrir o drawer do relacionado.

## COL-REL-005

Pode ser filtrada e agrupada.

---

# 69. Critérios de aceite — Arquivos

## COL-ARQ-001

Upload respeita autorização.

## COL-ARQ-002

Download exige autorização.

## COL-ARQ-003

A célula mostra quantidade de anexos.

## COL-ARQ-004

Abrir anexo não exige sair do contexto principal.

---

# 70. Matriz final

| Tipo | Editável inline | Filtrar | Ordenar | Agrupar | Resumo | Kanban | Calendário | Fórmula |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Texto | Sim | Sim | Sim | Limitado | Contagem | Sim | Sim | Entrada limitada |
| Número | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| Moeda | Sim | Sim | Sim | Sim | Sim | Sim | Sim | Sim |
| Data | Sim | Sim | Sim | Sim | Sim | Sim | Principal | Sim |
| Pessoas | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Não direta |
| Status | Sim | Sim | Sim | Sim | Distribuição | Principal | Sim | Condição |
| Lista suspensa | Sim | Sim | Sim | Sim | Distribuição | Sim | Sim | Condição |
| Prioridade | Sim | Sim | Sim | Sim | Distribuição | Sim | Sim | Condição |
| Confirmação | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Sim |
| Arquivo | Via painel | Básico | Básico | Não | Contagem | Sim | Sim | Não |
| Relação | Sim | Sim | Sim | Sim | Contagem | Sim | Sim | Limitado |
| Cronograma | Sim | Sim | Sim | Não | Duração | Sim | Futuro | Sim |
| Fórmula | Não | Sim | Sim | Depende | Depende | Sim | Depende | Resultado |

---

# 71. Definição final

A coluna na LPS é:

> Um componente reutilizável de dados e comportamento que define como uma informação é armazenada, editada, validada, filtrada, ordenada, agrupada, calculada e apresentada nas diferentes visualizações do sistema.

As 13 colunas-base oficiais são:

```text
Texto
Número
Moeda
Data
Pessoas
Status
Lista suspensa
Prioridade
Confirmação
Arquivo
Relação
Cronograma
Fórmula
```

Campos específicos da construção e da operação da Biasi devem nascer da composição desses tipos, e não da criação indiscriminada de novos tipos técnicos.

Essa é a base para a LPS ser dinâmica sem virar um sistema tecnicamente desorganizado.
