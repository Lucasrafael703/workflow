# LPS — Especificação da Visualização por Calendário

## 1. Objetivo

A visualização por **Calendário** organiza os mesmos itens do Quadro em uma linha do tempo baseada em uma coluna do tipo Data.

Na LPS, o Calendário não deve ser um módulo separado nem possuir dados próprios. Ele é uma **visualização configurável dos mesmos itens** exibidos na Tabela (Quadro) e no Kanban.

Exemplo:

```text
Quadro: Demandas

Demanda                      | Responsável     | Prazo       | Status
Arena Center Norte           | Ryan            | 06/10/2026  | Em andamento
GEHAKA                        | Luan            | 12/10/2026  | Aguardando retorno
Ahlstrom                      | Jennifer        | 14/10/2026  | Confirmada
```

Calendário:

```text
06/10
Arena Center Norte

12/10
GEHAKA

14/10
Ahlstrom
```

Nenhum item foi duplicado.

---

# 2. Princípio central

> O dado pertence ao Quadro. O Calendário é apenas uma maneira temporal de enxergar e editar esse dado.

Consequências:

- a mesma Demanda ou Tarefa aparece na Tabela, Kanban e Calendário;
- alterar a data no Calendário altera o mesmo campo utilizado nas demais visualizações;
- alterar Status, Pessoa, Setor ou outra informação pelo Calendário deve refletir imediatamente nas outras visualizações;
- o Calendário não deve criar cópias dos itens;
- pequenas alterações devem acontecer sem o usuário sair da tela;
- a visualização deve privilegiar compromissos, prazos e entregas, e não vigilância de pessoas.

---

# 3. Relação com a arquitetura atual da LPS

Hoje a LPS já possui calendários para Atividades e Tarefas dentro do app `activities`.

A documentação atual estabelece que Lista, Kanban e Calendário de Atividades utilizam o mesmo filtro de dados.

A evolução proposta mantém esse princípio, mas transforma o Calendário em uma visualização configurável do novo motor de Quadros.

## 3.1 Demandas

Na interface, **Atividade passa a ser chamada de Demanda**.

Internamente, enquanto a migração arquitetural não estiver concluída:

```text
Demanda = Activity
```

O campo nativo disponível atualmente para prazo da Demanda é:

```text
Activity.requested_deadline
```

Esse campo pode ser usado como Data padrão da visualização de Calendário de Demandas.

## 3.2 Tarefas

A Tarefa possui atualmente dois conceitos de prazo:

```text
requested_deadline
committed_deadline
```

Significados:

```text
Prazo solicitado    = prazo pedido por quem solicitou
Prazo comprometido  = prazo assumido pelo executor
```

A visualização deve permitir escolher qual coluna temporal será utilizada.

No template padrão de Tarefas, a preferência deve ser:

```text
Prazo comprometido
```

Se a organização quiser trabalhar visualmente com Prazo solicitado, deve poder criar outra visualização de Calendário usando esse campo.

Não esconder a diferença conceitual entre os dois prazos.

---

# 4. Regra estrutural da visualização

O Calendário precisa estar vinculado a:

```text
Board
└── BoardView
    ├── type = CALENDAR
    └── settings
```

Exemplo conceitual:

```json
{
  "name": "Calendário de prazos",
  "type": "calendar",
  "settings": {
    "date_field": "prazo",
    "period": "month",
    "color_by": "status",
    "show_weekends": true
  }
}
```

A visualização salva **configuração**, não cópia de dados.

---

# 5. Pré-requisito para criar um Calendário

Uma visualização de Calendário precisa de pelo menos uma coluna compatível com Data.

Tipos compatíveis inicialmente:

```text
Data
Data + hora
```

Tipos futuros:

```text
Intervalo de datas
Cronograma
```

Se o Quadro não tiver uma coluna de Data:

```text
Criar visualização → Calendário
```

A LPS deve orientar:

```text
Para usar o Calendário, escolha ou crie uma coluna de Data.

[ + Criar coluna de Data ]
```

O usuário não deve precisar sair da tela.

---

# 6. Uma coluna Data, duas formas de uso

Data e Data + hora não devem ser tratadas como dois campos completamente independentes para o usuário.

A coluna deve possuir configuração:

```text
Data
Exibir horário: Não
```

Ao ativar horário:

```text
Data
Exibir horário: Sim
```

Exemplo:

```text
15/10/2026
```

passa a aceitar:

```text
15/10/2026 14:00
```

## 6.1 Regra

> A hora é opcional e pertence à mesma informação de Data.

Não exigir horário para usar o Calendário.

---

# 7. Item sem horário

Se o item possuir:

```text
Data = 15/10/2026
Hora = vazia
```

o Calendário deve tratá-lo como compromisso do dia.

Exemplo:

```text
15
┌─────────────────────────────┐
│ Revisar proposta comercial │
└─────────────────────────────┘
```

Não inventar horário.

---

# 8. Item com horário

Se o item possuir:

```text
Data = 15/10/2026
Hora = 14:00
```

o Calendário pode mostrar:

```text
14:00  Visita técnica
```

Na visão mensal, o horário deve ser compacto.

Na futura visão diária/semanal, o item pode ocupar a faixa correspondente ao horário.

---

# 9. Estrutura principal da tela

A visualização deve possuir cinco áreas:

1. cabeçalho;
2. abas de visualização;
3. barra de ações;
4. navegação temporal;
5. grade do Calendário.

---

# 10. Cabeçalho

Exemplo para Demandas:

```text
Demandas
Gestão das demandas internas e intersetoriais.
```

Exemplo para Tarefas:

```text
Tarefas
Execução operacional das tarefas vinculadas às demandas e processos.
```

A identidade do módulo continua sendo a mesma.

Apenas a visualização muda.

---

# 11. Abas de visualização

Exemplo:

```text
[ Quadro principal ] [ Kanban ] [ Calendário ] [ + ]
```

Regras:

- `Calendário` deve ficar destacado quando ativo;
- mudar de visualização não altera o conjunto de dados;
- filtros salvos podem ser próprios de cada visualização;
- o usuário pode ter mais de um Calendário no mesmo Quadro.

Exemplo:

```text
Calendário de prazos
Calendário de visitas técnicas
Calendário de entregas
```

Os três podem usar os mesmos itens, mas colunas de Data diferentes.

---

# 12. Barra de ações

Exemplo:

```text
[Criar demanda] [Adicionar ferramenta] Pesquisar Pessoa Filtro ...
```

ou:

```text
[Criar tarefa] [Adicionar ferramenta] Pesquisar Pessoa Filtro ...
```

Itens principais:

- Criar item;
- Pesquisar;
- Pessoa / Responsável;
- Filtro;
- Hoje;
- período anterior;
- período seguinte;
- mês/período atual;
- seletor de visualização temporal;
- Configurações;
- Mais ações.

---

# 13. Botão Criar

O nome do botão deve respeitar o contexto.

```text
Demandas → Criar demanda
Tarefas  → Criar tarefa
Genérico → Criar item
```

O botão não deve mandar o usuário para outra página.

Deve abrir o formulário por cima da visualização atual.

---

# 14. Navegação temporal

A barra deve conter:

```text
[ Hoje ]  <  >  outubro 2026  [ Mês v ]
```

## 14.1 Hoje

`Hoje` leva a visualização diretamente ao período que contém a data atual.

## 14.2 Anterior

Na visualização Mês:

```text
< = mês anterior
```

## 14.3 Próximo

Na visualização Mês:

```text
> = mês seguinte
```

## 14.4 Título do período

Exemplo:

```text
outubro 2026
```

Deve refletir o período atualmente carregado.

---

# 15. Escala temporal

Primeira entrega obrigatória:

```text
Mês
```

Estrutura preparada para:

```text
Semana
Dia
Agenda
```

A expansão para Semana e Dia não deve exigir criação de outro conjunto de dados.

---

# 16. Grade mensal

A visão Mês deve usar sete colunas:

```text
Seg | Ter | Qua | Qui | Sex | Sáb | Dom
```

Cada célula representa um dia.

Cada célula deve suportar:

- número do dia;
- itens daquele dia;
- estado de hover;
- criação rápida;
- limite visual de itens;
- indicador de itens adicionais;
- drag-and-drop de itens entre datas.

---

# 17. Dias de outros meses

Na primeira e última semana podem aparecer dias do mês anterior ou seguinte.

Devem ser visualmente discretos.

Exemplo:

```text
28 29 30 | 01 02 03 04
```

Os dias fora do mês ativo continuam clicáveis.

---

# 18. Data atual

O dia atual deve receber destaque discreto.

Exemplo:

```text
[ 02 ]
```

Não usar uma cor excessivamente forte que concorra com os cartões.

---

# 19. Hover sobre o dia

Essa é uma regra importante da experiência.

Quando o usuário não está interagindo:

```text
15
```

Ao passar o mouse:

```text
15

+ Adicionar
```

## 19.1 Regra

> A ação deve aparecer no contexto onde o usuário pretende agir.

Não manter `+ Adicionar` permanentemente em todas as células.

Isso poluiria a tela.

---

# 20. Criar item clicando no dia

Ao clicar em:

```text
+ Adicionar
```

dentro de `15/10/2026`, o formulário deve abrir sem sair do Calendário.

A Data deve vir preenchida automaticamente:

```text
Data = 15/10/2026
```

O usuário não deve informar novamente algo que o contexto já determinou.

---

# 21. Criação contextual

A regra é:

> O gesto do usuário pode preencher informações do item.

Exemplos:

```text
Clicou no dia 15
→ Data = 15/10/2026
```

```text
Criou dentro de uma visualização filtrada por Setor Comercial
→ a LPS pode sugerir Comercial, sem gravar automaticamente se houver ambiguidade
```

```text
Arrastou um item de 15 para 18
→ Data = 18/10/2026
```

Não preencher campos de forma implícita quando o contexto não for inequívoco.

---

# 22. Modal de criação de Demanda

Exemplo de campos:

```text
Criar demanda

Grupo
Responsável
Status
Prioridade
Setor
Cliente/Obra
Data
Descrição curta
```

Os campos exibidos devem vir da configuração do Quadro.

A lista acima é um template inicial, não uma estrutura rígida.

---

# 23. Modal de criação de Tarefa

Exemplo:

```text
Criar tarefa

Demanda vinculada
Responsável
Setor
Status
Prioridade
Prazo
Hora (opcional)
Checklist rápido
```

Novamente, os campos devem ser configuráveis.

A Tarefa precisa continuar vinculada às regras reais de `TaskService`.

---

# 24. Editores dentro do modal

Mesmo dentro de um modal maior, campos simples não devem abrir novas páginas.

Exemplo:

```text
Responsável
[ Paulo v ]
```

clicou:

```text
Pesquisar pessoa...

Paulo
Ryan
Luan
Jennifer
```

Selecionou:

```text
Paulo
```

O popover fecha.

---

# 25. Níveis de interação

A LPS deve trabalhar com três níveis.

## 25.1 Edição direta

Para:

- título;
- texto curto;
- número.

Fluxo:

```text
clicar → editar → salvar automaticamente
```

## 25.2 Popover contextual

Para:

- Data;
- Pessoa;
- Status;
- Prioridade;
- Setor;
- Lista suspensa;
- Cor.

Fluxo:

```text
clicar → popover → selecionar → pronto
```

## 25.3 Modal ou drawer

Para:

- criação completa;
- detalhes;
- checklist;
- comentários;
- anexos;
- histórico;
- configurações avançadas.

---

# 26. Regra global de navegação

> Não tirar o usuário do Calendário para editar uma informação que pode ser alterada no próprio contexto.

O usuário deve continuar enxergando o Calendário atrás do editor.

---

# 27. Cartão do Calendário

Cada item deve possuir um cartão compacto.

Exemplo:

```text
Arena Center Norte — Levantamento
● Planejamento
LT Lucas Tavares
Arena Center Norte
```

O cartão não deve tentar mostrar todos os campos do item.

---

# 28. Título do cartão

O título é obrigatório.

Demandas:

```text
Título da demanda
```

Tarefas:

```text
Título da tarefa
```

O título deve ser a informação visual principal.

---

# 29. Campos visíveis no cartão

A visualização deve permitir configurar quais campos aparecem.

Exemplos:

- Status;
- Responsável;
- Setor;
- Prioridade;
- Cliente;
- Obra;
- Demanda vinculada;
- horário;
- Tags;
- outros campos configuráveis.

---

# 30. Limite de informação no cartão

O cartão mensal deve ser compacto.

Recomendação:

```text
Título
+ até 3 informações secundárias
```

Informações adicionais ficam disponíveis ao clicar.

Evitar transformar cada célula do Calendário em um formulário.

---

# 31. Personalização do cartão

A configuração pode possuir:

```text
Personalizar item do Calendário

☑ Status
☑ Responsável
☑ Cliente/Obra
☐ Setor
☐ Prioridade
☐ Descrição
```

Os campos devem poder ser reordenados.

---

# 32. Cor dos itens

A visualização deve permitir:

```text
Colorir por:
[ Status v ]
```

Possíveis fontes:

- Status;
- Prioridade;
- Setor;
- Grupo;
- outra coluna categórica compatível.

---

# 33. Cor não é identidade do item

A cor é apenas uma representação visual.

Se:

```text
Status = Em andamento
Cor = azul
```

e a cor for alterada para verde:

- Quadro deve atualizar;
- Kanban deve atualizar;
- Calendário deve atualizar;
- filtros continuam funcionando;
- o item continua sendo o mesmo.

---

# 34. Status com identificador estável

Nunca ligar regras ao texto visual.

Errado:

```text
if status.name == "Em andamento":
```

Correto conceitualmente:

```text
status_option_id = 42
```

O usuário pode renomear:

```text
Em andamento
```

para:

```text
Em execução
```

sem quebrar:

- Calendário;
- filtros;
- automações;
- Kanban;
- relatórios.

---

# 35. Clique em um item

Ao clicar em um cartão:

```text
Arena Center Norte — Levantamento
```

não abrir outra página.

Abrir um drawer lateral ou modal de detalhe.

---

# 36. Drawer de Demanda

Pode conter:

- título;
- Status;
- Responsável;
- Solicitante;
- Setor;
- Prazo;
- Cliente;
- Obra;
- descrição;
- checklist/etapas;
- Tarefas vinculadas;
- comentários;
- arquivos;
- histórico.

O Calendário continua visível atrás.

---

# 37. Drawer de Tarefa

Pode conter:

- título;
- Demanda vinculada;
- Responsável;
- Setor;
- Status;
- prazo;
- horário;
- checklist;
- participantes;
- comentários;
- anexos;
- histórico;
- ações operacionais.

---

# 38. Drag-and-drop entre dias

O usuário deve poder segurar um item e mover para outro dia.

Exemplo:

```text
15/10
Visita técnica
```

arrastado para:

```text
17/10
```

Resultado:

```text
Data = 17/10/2026
```

---

# 39. Regra do drag-and-drop

Mover no Calendário altera **somente o campo de Data que alimenta aquela visualização**.

Não alterar automaticamente:

- Status;
- Responsável;
- Setor;
- Prioridade.

A menos que exista uma automação explícita configurada para isso.

---

# 40. Atualização otimista

Ao soltar o item:

1. mover visualmente imediatamente;
2. salvar em segundo plano;
3. confirmar silenciosamente;
4. se falhar, voltar ao dia anterior;
5. mostrar mensagem curta de erro.

Isso evita sensação de lentidão.

---

# 41. Autosave

Não criar botão:

```text
Salvar Calendário
```

Pequenas alterações devem ser gravadas automaticamente.

Exemplos:

- mudar Data;
- mudar hora;
- mudar Status;
- trocar Responsável;
- alterar Prioridade;
- mover item.

---

# 42. Data + hora inline

Ao clicar na Data, abrir um popover.

Exemplo:

```text
Hoje

15/10/2026

outubro 2026
Seg Ter Qua Qui Sex Sáb Dom
...
```

Mostrar ícone de relógio:

```text
🕒
```

---

# 43. Adicionar hora

Ao clicar no relógio:

```text
15/10/2026 | 14:00
```

Mostrar:

```text
Horário opcional

08:00
09:00
10:00
14:00
15:00
16:00
```

O usuário também pode digitar.

---

# 44. Remover hora

A interface deve permitir:

```text
Limpar horário
```

Sem apagar a Data.

Resultado:

```text
15/10/2026
```

---

# 45. Remover Data

Se o usuário limpar a Data:

```text
Data = vazia
```

o item deixa de aparecer na grade principal.

Ele não deve ser excluído.

---

# 46. Itens sem Data

A visualização deve oferecer acesso aos itens sem Data.

Exemplo:

```text
Sem data  7
```

Ao clicar:

```text
Itens sem data

- Revisar contrato
- Validar projeto
- Solicitar cotação
```

Isso evita que itens desapareçam da gestão.

---

# 47. Colocar item sem Data no Calendário

Da lista `Sem data`, o usuário pode:

- abrir e definir a Data;
- futuramente arrastar para um dia.

Ao definir:

```text
18/10/2026
```

o item passa a aparecer imediatamente no dia 18.

---

# 48. Muitos itens no mesmo dia

Se a célula não comportar todos:

```text
15

Demanda A
Demanda B
Demanda C
+ 5 mais
```

Não aumentar indefinidamente a altura da semana.

---

# 49. `+ N mais`

Ao clicar:

```text
+ 5 mais
```

abrir um popover ou painel com todos os itens do dia.

Não navegar para outra tela.

---

# 50. Busca

A barra deve permitir pesquisa textual.

Exemplos:

```text
Santa Isabel
Arena
Ahlstrom
SPDA
```

O Calendário mostra apenas itens compatíveis.

---

# 51. Filtro por Pessoa

Exemplo:

```text
Pessoa
[ Ryan ]
```

Mostrar somente itens relacionados ao Ryan conforme o campo usado pela visualização.

A regra de relacionamento precisa ser explícita.

Demandas:

```text
Responsável/Dono
Solicitante
Participante, se configurado
```

Tarefas:

```text
Responsável
Participante
```

Não misturar papéis sem informar.

---

# 52. Filtros disponíveis

A visualização deve reaproveitar o motor de filtros do Quadro.

Exemplos:

- Responsável;
- Solicitante;
- Setor;
- Status;
- Prioridade;
- Cliente;
- Obra;
- Centro de custo;
- Grupo;
- Tags;
- Demanda vinculada;
- campos customizados.

---

# 53. Composição de filtros

Permitir regras como:

```text
Setor = Comercial
E
Status != Concluído
E
Responsável = Ryan
```

Não criar um motor separado exclusivamente para o Calendário.

---

# 54. Filtros temporários e filtros salvos

Filtros aplicados apenas durante a navegação podem ser temporários.

Quando o usuário salvar a configuração:

```text
Calendário Comercial
```

o conjunto de filtros passa a fazer parte da configuração da visualização.

---

# 55. Configuração da visualização

Painel sugerido:

```text
Configurações do Calendário

Data utilizada
[ Prazo v ]

Colorir por
[ Status v ]

Campos do cartão
[ Configurar ]

Mostrar finais de semana
[ Sim ]

Mostrar concluídos
[ Sim ]

Itens sem data
[ Mostrar contador ]

Escala
[ Mês ]
```

---

# 56. Escolher a Data utilizada

Essa é a configuração mais importante.

Exemplos em Demandas:

```text
Prazo
Visita técnica
Data de entrega
Data de envio
```

Exemplos em Tarefas:

```text
Prazo solicitado
Prazo comprometido
Data de execução
```

O Calendário deve ler exatamente a coluna escolhida.

---

# 57. Múltiplos Calendários

O mesmo Quadro pode possuir:

```text
Calendário de prazos
Calendário de visitas técnicas
Calendário de entregas ao cliente
```

Todos exibindo os mesmos itens.

Isso é um dos principais ganhos do modelo de visualizações.

---

# 58. Finais de semana

Configuração:

```text
Mostrar finais de semana: Sim/Não
```

Se desativado:

```text
Seg | Ter | Qua | Qui | Sex
```

Não alterar as Datas dos itens.

É apenas visual.

---

# 59. Datas em final de semana oculto

Se um item estiver em sábado e os finais de semana estiverem ocultos:

- não mover automaticamente para sexta ou segunda;
- não alterar o banco;
- indicar que existem itens em dias ocultos;
- oferecer forma de exibi-los.

---

# 60. Concluídos

A visualização pode possuir:

```text
Mostrar concluídos: Sim/Não
```

Ocultar concluídos é um filtro visual.

Não excluir nem alterar o item.

---

# 61. Cancelados

Mesma regra.

A visualização pode ocultar cancelados por padrão.

O comportamento deve estar documentado na configuração da view.

---

# 62. Tarefas: prazo solicitado × comprometido

A LPS não deve apagar essa diferença.

Exemplo:

```text
Prazo solicitado:   15/10
Prazo comprometido: 18/10
```

Um Calendário pode mostrar:

```text
Calendário — prazo comprometido
```

Outra visualização pode mostrar:

```text
Calendário — prazo solicitado
```

Evitar escolher silenciosamente um deles em todos os contextos.

---

# 63. Template padrão de Demandas

Configuração inicial sugerida:

```text
Nome: Calendário
Data: Prazo
Colorir por: Status
Escala: Mês
Mostrar finais de semana: Sim
```

Cartão:

```text
Título
Status
Responsável
Cliente/Obra
```

---

# 64. Template padrão de Tarefas

Configuração inicial sugerida:

```text
Nome: Calendário
Data: Prazo comprometido
Colorir por: Status
Escala: Mês
Mostrar finais de semana: Sim
```

Cartão:

```text
Título
Status
Responsável
Demanda vinculada
```

Se `Prazo comprometido` ainda não existir para a Tarefa, a interface deve indicar isso claramente.

---

# 65. Tarefa sem prazo comprometido

Não inventar prazo.

Possibilidades:

```text
Sem prazo comprometido
```

ou, se a visualização tiver sido configurada explicitamente:

```text
Usar prazo solicitado enquanto não houver prazo comprometido
```

Essa opção deve ser visível na configuração.

Não aplicar fallback oculto.

---

# 66. Priorização visual

Prioridade pode ser mostrada como chip:

```text
Alta
Média
Baixa
```

Mas a cor principal do cartão deve seguir a regra `Colorir por`.

Não usar três códigos de cor concorrentes no mesmo cartão.

---

# 67. Atraso

Um item atrasado pode receber um indicador discreto.

Exemplo:

```text
⚠ Atrasada
```

ou borda específica.

Não transformar todo o cartão em vermelho se isso prejudicar a leitura do código de cores configurado.

---

# 68. Hoje + atraso

Ao abrir o Calendário no dia atual, itens anteriores ainda abertos podem ser acessados por:

- filtro `Atrasadas`;
- painel lateral;
- indicador/resumo.

O Calendário não deve esconder trabalho vencido.

---

# 69. Reagendamento não é conclusão

Mover:

```text
15/10 → 18/10
```

significa reagendar.

Não significa:

```text
Status = Concluído
```

---

# 70. Reagendamento não deve apagar histórico

A alteração de Data deve registrar:

```text
Data anterior
Nova Data
Usuário
Data/hora da alteração
```

---

# 71. Auditoria

Mudanças feitas pelo Calendário precisam passar pelo mesmo padrão da arquitetura da LPS:

```text
URL → View → Service → Model
```

O Calendário não deve gravar diretamente no model ignorando Services.

---

# 72. Alterações auditáveis

Pelo menos:

- mudança de Data;
- mudança de hora;
- troca de Responsável;
- mudança de Status;
- mudança de Prioridade;
- criação;
- edição relevante;
- exclusão/inativação conforme regra do domínio.

---

# 73. Permissões

Ver o botão não significa ter autorização.

O Calendário deve respeitar o motor:

```text
SUJEITO + AÇÃO + ESCOPO + ORIGEM
```

Exemplos:

```text
atividade.editar
tarefa.editar
tarefa.criar
atividade.criar
```

---

# 74. Drag-and-drop e autorização

Antes de aceitar um movimento de Data:

1. verificar organização;
2. verificar acesso ao recurso;
3. verificar permissão para editar;
4. validar o novo valor;
5. salvar por Service;
6. auditar.

Nunca repetir o problema atual do movimento de estágio do Kanban, que hoje possui lacunas de autorização/auditoria documentadas.

---

# 75. Multi-organização

O Calendário deve respeitar `Organization`.

Nenhum item de outra organização pode:

- aparecer;
- ser pesquisado;
- ser movido;
- ser aberto;
- ser editado.

---

# 76. Atualização entre visualizações

Exemplo:

Calendário:

```text
Visita técnica
15/10
```

Usuário arrasta para:

```text
17/10
```

Ao abrir a Tabela:

```text
Prazo = 17/10/2026
```

Não existe sincronização posterior.

É o mesmo dado.

---

# 77. Atualização de Status

Se o usuário clicar no cartão e alterar:

```text
Em andamento → Concluída
```

o Kanban deve refletir automaticamente.

Se o Kanban estiver agrupado por Status, o cartão muda de coluna.

---

# 78. Atualização de Pessoa

Se trocar:

```text
Ryan → Luan
```

Filtros e outras visualizações devem refletir imediatamente.

---

# 79. Renomear Status

Se:

```text
Em andamento
```

for renomeado para:

```text
Em execução
```

os cartões do Calendário passam a mostrar:

```text
Em execução
```

sem migração manual de itens.

---

# 80. Alterar cor do Status

Se a cor mudar:

```text
Azul → Verde
```

todos os cartões que usam aquela opção devem mudar imediatamente.

---

# 81. Calendário não é agenda de microgerenciamento

A finalidade é mostrar:

- compromissos;
- entregas;
- prazos;
- concentração de demandas;
- conflitos;
- sobreposição;
- datas críticas.

Não deve ser usado por padrão para medir:

- minutos trabalhados;
- presença contínua;
- cada pausa;
- cada movimento de funcionário.

---

# 82. Tempo estimado

Se existir como campo de Tarefa, pode aparecer no cartão.

Exemplo:

```text
Estimativa: 2h
```

Mas não deve ser obrigatório para o Calendário funcionar.

---

# 83. Sessões de trabalho

`WorkSession` não deve determinar onde um item aparece no Calendário.

Calendário trata de Data/Prazo.

Cronômetro trata de execução.

São conceitos diferentes.

---

# 84. Visão gerencial

O Calendário pode ajudar o gestor a enxergar:

- dias com excesso de entregas;
- concentração de visitas;
- prazos simultâneos;
- itens atrasados;
- capacidade temporal;
- compromissos por responsável;
- demanda por setor.

A visualização deve ajudar a decidir onde agir.

---

# 85. Visão do executor

O executor pode usar filtros:

```text
Responsável = Eu
```

e enxergar:

```text
meus compromissos da semana/mês
```

Sem exposição desnecessária de informações de outros setores quando a permissão não permitir.

---

# 86. Densidade

Em meses muito carregados, o sistema deve continuar legível.

Regras:

- cartões compactos;
- altura máxima por célula;
- `+ N mais`;
- tooltip/popover;
- filtros rápidos;
- não reduzir fonte indefinidamente.

---

# 87. Responsividade

Desktop é a experiência principal da primeira entrega.

Em telas menores:

- menu lateral pode recolher;
- Calendário pode horizontalizar/rolar;
- drawer pode ocupar a tela inteira;
- ações continuam acessíveis.

Não tentar comprimir sete dias em uma largura ilegível.

---

# 88. Performance

A visualização deve buscar somente o intervalo necessário.

Exemplo:

```text
outubro 2026
```

Carregar:

- dias visíveis do mês;
- margem necessária para a primeira/última semana.

Não carregar todo o histórico do Quadro.

---

# 89. Mudança de mês

Ao clicar em `>`:

1. atualizar título;
2. buscar apenas o novo intervalo;
3. manter filtros;
4. manter configuração;
5. evitar reload completo quando possível.

---

# 90. Estado vazio

Sem itens no mês:

```text
Nenhum item neste período.

Passe o mouse sobre um dia para adicionar.
```

Não tratar como erro.

---

# 91. Erro ao salvar

Exemplo:

```text
Não foi possível alterar a data.
O item voltou para 15/10/2026.
```

A mensagem precisa ser curta e explicativa.

---

# 92. Conflito de edição

Se outro usuário alterar o mesmo item simultaneamente:

- não sobrescrever silenciosamente uma versão mais recente;
- atualizar o cartão;
- informar conflito quando necessário;
- preservar a informação mais recente validada pelo servidor.

---

# 93. Acessibilidade

A experiência não pode depender exclusivamente de cor.

Exemplo:

```text
● Concluída
```

e não apenas uma faixa verde sem texto.

Itens interativos precisam suportar:

- foco de teclado;
- Enter;
- Esc;
- labels;
- contraste adequado;
- tooltip acessível.

---

# 94. Teclado

Comportamentos esperados:

```text
Enter = abrir/confirmar
Esc   = fechar popover/modal
Tab   = navegar
```

Drag-and-drop deve possuir alternativa acessível futura.

---

# 95. Formatação de Data

Interface brasileira:

```text
DD/MM/AAAA
```

Exemplo:

```text
15/10/2026
```

No cartão mensal, formas compactas podem ser usadas sem ambiguidade.

---

# 96. Fuso horário

Horas devem respeitar o fuso configurado para a organização/usuário.

Não assumir UTC na interface.

Armazenamento técnico pode utilizar horário timezone-aware, mas a exibição deve respeitar o contexto local.

---

# 97. Data sem hora × DateTime

A implementação precisa preservar a diferença sem inventar horário.

Conceitualmente:

```text
15/10/2026
```

não é automaticamente:

```text
15/10/2026 00:00
```

para fins de experiência do usuário.

O sistema deve saber que aquele item é `all day`.

---

# 98. Configuração salva

Uma visualização deve preservar:

- nome;
- tipo;
- Data utilizada;
- escala;
- filtros salvos;
- cor por;
- campos visíveis;
- ordem dos campos;
- finais de semana;
- exibição de concluídos;
- outras configurações visuais.

---

# 99. Configuração não deve alterar o dado

Trocar:

```text
Colorir por: Status
```

para:

```text
Colorir por: Setor
```

não deve modificar nenhum item.

Apenas a representação visual.

---

# 100. Exclusão da visualização

Excluir:

```text
Calendário de visitas
```

remove apenas a `BoardView`.

Não apagar:

- Demandas;
- Tarefas;
- Datas;
- Status;
- Pessoas;
- histórico.

---

# 101. Renomear a visualização

Exemplo:

```text
Calendário
```

para:

```text
Prazos Comercial
```

O rename deve ser inline e autosave.

---

# 102. Duplicar visualização

O usuário pode duplicar:

```text
Calendário de prazos
```

para criar:

```text
Calendário Comercial
```

A nova view copia configurações, não itens.

---

# 103. Compartilhamento

Uma visualização pode ser compartilhada conforme as permissões do Quadro.

Não conceder acesso a dados que o usuário não poderia visualizar pela regra de autorização.

---

# 104. Regras específicas para Demandas

O Calendário de Demandas deve privilegiar visão macro.

Informações úteis:

- Demanda;
- prazo;
- responsável;
- Status;
- Cliente/Obra;
- Setor.

Evitar excesso de checklist ou subtarefas no cartão principal.

---

# 105. Regras específicas para Tarefas

O Calendário de Tarefas é mais operacional.

Informações úteis:

- Tarefa;
- Demanda vinculada;
- Responsável;
- prazo;
- horário, se houver;
- Status;
- Prioridade.

Checklist deve aparecer apenas de forma resumida:

```text
3/5
```

---

# 106. Demanda e suas Tarefas

Uma Demanda e suas Tarefas são objetos diferentes.

Exemplo:

```text
Demanda:
Ahlstrom — Visita técnica
```

Tarefas:

```text
Confirmar acesso
Separar documentos
Realizar levantamento
Emitir relatório
```

O Calendário de Demandas pode mostrar a Demanda.

O Calendário de Tarefas pode mostrar cada Tarefa.

Não duplicar automaticamente a Demanda como se fosse uma Tarefa.

---

# 107. Mostrar Demanda vinculada no cartão de Tarefa

Exemplo:

```text
Realizar levantamento
Ahlstrom — Visita técnica
```

Isso ajuda a manter contexto sem abrir a Demanda.

---

# 108. Clique na Demanda vinculada

Deve abrir o drawer/contexto da Demanda.

Evitar abandonar o Calendário.

---

# 109. Calendário e notificações

Apenas visualizar o Calendário não gera notificação.

Alterações podem gerar notificações se a regra de negócio já determinar isso.

Exemplo:

- mudança de responsável;
- negociação de prazo;
- conclusão;
- bloqueio.

Não notificar por toda pequena mudança visual.

---

# 110. Calendário e automações

Automações podem reagir a mudanças no campo de Data.

Exemplo:

```text
Quando Prazo mudar
→ recalcular indicador de atraso
```

ou:

```text
2 dias antes do Prazo
→ criar lembrete
```

Essas regras pertencem ao motor de automações, não à visualização em si.

---

# 111. Calendário e integração externa

Sincronização com agendas externas pode ser evolução futura.

Exemplos:

```text
Google Calendar
Microsoft Outlook
```

Não faz parte da primeira entrega obrigatória.

Quando existir, precisa definir claramente:

- leitura;
- escrita;
- direção da sincronização;
- conflitos;
- privacidade;
- quais campos sincronizam.

---

# 112. O que não pertence à primeira versão

Não tornar obrigatório inicialmente:

- sincronização com Google;
- sincronização com Outlook;
- recorrência avançada;
- intervalos multi-dia;
- dependências visuais;
- Gantt;
- reservas de sala;
- gestão de recursos;
- timeboxing obrigatório;
- controle de ponto.

Primeiro entregar o núcleo simples e confiável.

---

# 113. Primeira versão obrigatória

A primeira versão funcional deve possuir:

1. visualização Mês;
2. escolha do campo de Data;
3. cartões no dia correspondente;
4. hover `+ Adicionar`;
5. criação contextual;
6. modal sem sair da tela;
7. edição de Data via popover;
8. hora opcional;
9. click no cartão → drawer;
10. drag-and-drop entre dias;
11. Pesquisa;
12. filtro por Pessoa;
13. filtros genéricos;
14. Hoje;
15. mês anterior/próximo;
16. personalização básica de cartões;
17. cor por Status;
18. itens sem Data;
19. autosave;
20. autorização e auditoria.

---

# 114. Critérios de aceite — criação

## CA-CAL-001

Ao passar o mouse sobre um dia vazio:

```text
+ Adicionar
```

deve aparecer.

## CA-CAL-002

Ao clicar em `+ Adicionar`, a LPS abre o formulário sem sair do Calendário.

## CA-CAL-003

A Data do dia clicado deve vir preenchida.

## CA-CAL-004

Cancelar fecha o formulário e mantém o Calendário exatamente no mesmo período.

## CA-CAL-005

Criar salva o item e o exibe no dia correto sem reload completo da página.

---

# 115. Critérios de aceite — Data e hora

## CA-CAL-006

Clicar na Data abre um seletor contextual.

## CA-CAL-007

O horário não é obrigatório.

## CA-CAL-008

Ativar horário permite selecionar ou digitar uma hora.

## CA-CAL-009

Remover a hora mantém a Data.

## CA-CAL-010

Remover a Data retira o item da grade, mas não exclui o item.

---

# 116. Critérios de aceite — edição

## CA-CAL-011

Clicar no Status permite alterar sem sair da tela.

## CA-CAL-012

Clicar em Responsável permite pesquisar e selecionar sem sair da tela.

## CA-CAL-013

Alterações pequenas usam autosave.

## CA-CAL-014

Ao salvar, outras visualizações passam a refletir o novo valor.

---

# 117. Critérios de aceite — drag-and-drop

## CA-CAL-015

Um item pode ser arrastado de uma Data para outra.

## CA-CAL-016

O movimento altera somente a Data utilizada pela visualização.

## CA-CAL-017

O item deve mover visualmente antes da confirmação do servidor.

## CA-CAL-018

Falha no servidor deve restaurar a Data anterior.

## CA-CAL-019

A mudança deve passar por autorização e auditoria.

---

# 118. Critérios de aceite — filtros

## CA-CAL-020

Pesquisar filtra os itens visíveis.

## CA-CAL-021

Filtro de Responsável funciona sem alterar os dados.

## CA-CAL-022

Combinações de filtros são suportadas.

## CA-CAL-023

Trocar o mês preserva os filtros ativos.

---

# 119. Critérios de aceite — consistência

## CA-CAL-024

Um item criado pelo Calendário deve aparecer na Tabela.

## CA-CAL-025

Se possuir Status compatível, deve aparecer corretamente no Kanban.

## CA-CAL-026

Alterar a Data na Tabela reposiciona o item no Calendário.

## CA-CAL-027

Renomear uma opção de Status atualiza seu texto no Calendário.

## CA-CAL-028

Mudar a cor da opção atualiza sua representação visual.

---

# 120. Critérios de aceite — itens sem Data

## CA-CAL-029

Itens sem Data continuam existentes.

## CA-CAL-030

A visualização mostra contador/acesso para `Sem data`.

## CA-CAL-031

Definir uma Data faz o item aparecer imediatamente na grade.

---

# 121. Critérios de aceite — segurança

## CA-CAL-032

Usuário de outra organização não acessa o item.

## CA-CAL-033

Usuário sem permissão de edição não consegue alterar Data via drag-and-drop.

## CA-CAL-034

Esconder botão não substitui a verificação no servidor.

## CA-CAL-035

A atualização deve passar por Service.

---

# 122. Critérios de aceite — experiência

## CA-CAL-036

Operações comuns não devem redirecionar para uma nova página.

## CA-CAL-037

A tela permanece visível atrás de popovers, modais e drawers.

## CA-CAL-038

Ações secundárias aparecem principalmente por contexto/hover.

## CA-CAL-039

A interface não deve exigir botão geral `Salvar Calendário`.

## CA-CAL-040

A densidade deve permanecer legível com vários itens.

---

# 123. Exemplo completo — Demandas

Quadro:

```text
Título                       | Prazo       | Status              | Responsável
Arena Center Norte           | 06/10/2026  | Planejamento        | Ryan
GEHAKA                        | 12/10/2026  | Aguardando retorno  | Luan
Ahlstrom                      | 14/10/2026  | Confirmada           | Jennifer
Martinichi                    | 16/10/2026  | Em andamento         | Ryan
```

Calendário:

```text
06
Arena Center Norte
Planejamento
Ryan

12
GEHAKA
Aguardando retorno
Luan

14
Ahlstrom
Confirmada
Jennifer

16
Martinichi
Em andamento
Ryan
```

---

# 124. Exemplo completo — Tarefas

Quadro:

```text
Tarefa                         | Prazo       | Responsável | Status
Agendar visita técnica         | 06/10/2026  | Jennifer    | Planejamento
Conferir projetos elétricos    | 07/10/2026  | Ryan        | Em andamento
Enviar devolutiva ao cliente   | 08/10/2026  | Luan        | Planejamento
Lançar pedido de compra        | 09/10/2026  | Ryan        | Em andamento
```

Calendário:

```text
06
Agendar visita técnica
Jennifer
Planejamento

07
Conferir projetos elétricos
Ryan
Em andamento

08
Enviar devolutiva ao cliente
Luan
Planejamento

09
Lançar pedido de compra
Ryan
Em andamento
```

---

# 125. Regra de produto

A experiência deve seguir:

```text
ver → clicar → alterar → continuar
```

e não:

```text
ver → abrir página → procurar formulário → editar → salvar → voltar
```

---

# 126. Regra de simplicidade

> A tela permanece limpa enquanto o usuário não demonstra intenção.

Por isso:

- `+ Adicionar` aparece no hover;
- menus avançados ficam escondidos;
- detalhes abrem sob demanda;
- cartões mostram apenas o necessário;
- configurações ficam em painel próprio.

---

# 127. Regra de contexto

> O usuário deve executar a ação no lugar em que percebeu a necessidade.

Exemplos:

```text
Viu um espaço no dia 15
→ cria no dia 15
```

```text
Viu prazo errado
→ arrasta para o dia correto
```

```text
Viu Status errado
→ clica no Status e corrige
```

---

# 128. Regra contra microgerenciamento

O Calendário deve responder perguntas como:

- O que vence esta semana?
- Onde temos muitas entregas no mesmo dia?
- Quais visitas estão programadas?
- Quais compromissos estão atrasados?
- Qual setor concentra entregas?
- Quem possui compromissos simultâneos?

Ele não deve responder, por padrão:

- Quem ficou parado por 12 minutos?
- Quem clicou menos?
- Quem manteve o cronômetro aberto?
- Quem trabalhou cada minuto do dia?

---

# 129. Regra arquitetural final

> Tabela, Kanban e Calendário devem ser três lentes sobre o mesmo trabalho.

```text
                    ┌──────────────┐
                    │    DADOS     │
                    │ Demandas /   │
                    │ Tarefas      │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
          TABELA        KANBAN      CALENDÁRIO
```

Uma mudança em qualquer uma delas atualiza a mesma fonte de verdade.

---

# 130. Definição final

A visualização por Calendário da LPS é:

> Uma representação temporal configurável dos itens de um Quadro, baseada em uma coluna de Data, que permite visualizar, criar, editar e reagendar Demandas e Tarefas diretamente no contexto do período exibido, sem duplicar dados e sem tirar o usuário da tela.

Ela deve unir:

- simplicidade;
- contexto;
- autosave;
- edição inline;
- filtros;
- Data + hora opcional;
- múltiplas visualizações;
- segurança;
- auditoria;
- integração com o restante da LPS.

O Calendário não é outro módulo.

É mais uma lente sobre o mesmo trabalho.
