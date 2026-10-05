# Teste de usabilidade do Workspace de Demandas (fase 1B)

> **Objetivo desta rodada não é construir o Workspace completo. É provar que uma pessoa consegue operar Demandas em um único contexto, sem precisar reaprender a interface ou perder seu estado.**
> Este roteiro e os critérios foram definidos **antes** de ver qualquer resultado. **Só se avança para o Calendário (1D) e para a extração de abstrações (1E) se o critério de passagem for atendido**; senão, corrige-se a 1A e o teste se repete com outras pessoas.
> O **Kanban** (1C) foi feito antes, por pedido explícito (ele passa a ser o mesmo de Quadros), atrás da mesma flag: ver `LPS_WORKSPACE_DEMANDAS.md` §8. Ele não é mais "legado" neste teste: as falhas dele têm origem própria (**K**).

## 1. Preparação (quem conduz)

1. Ligar a flag só para as 5 pessoas: `WORKSPACE_V2=allowlist` e `WORKSPACE_V2_USERS=` com os e-mails delas (Render → *Environment*). Conferir que cada uma vê a tela nova e que quem está fora da lista continua na antiga.
2. Dados de teste (podem ser a base real, desde que existam): o setor **Comercial**; uma pessoa com várias demandas (aqui chamada "Paulo"); o cliente **Santa Isabel** com ao menos uma demanda; ao menos 2 demandas **atrasadas** no Comercial; ao menos 1 demanda concluída.
3. Cada participante precisa da permissão **Visualizar todas as demandas** (senão a tarefa T2 não é possível). Se não tiver, use uma conta de teste.
4. Participantes: 5 pessoas que **nunca viram** a tela nova, de preferência com perfis diferentes (gestão, comercial, compras). Não mostrar a tela antes.
5. Material: o celular ou computador da pessoa, cronômetro, a planilha da seção 5.

## 2. Como conduzir

- Diga só: *"Vou pedir tarefas na tela de Demandas. Não existe resposta certa: eu estou testando a tela, não você. Pense em voz alta."*
- **Não explique a interface e não ajude.** Se a pessoa pedir ajuda, responda *"o que você faria?"* e anote como ajuda.
- **Hesitação** = ficou parada **mais de 5 segundos** procurando a ação. **Erro** = clicou num caminho incorreto (conte cada um). **Ajuda** = qualquer dica sua.
- Cronometre do fim da leitura da tarefa até a pessoa dizer que terminou.
- Comece sempre em `/demandas/` (a Lista), com o filtro limpo.

## 3. Tarefas

| # | O que dizer (exatamente) | Crítica? | Caminho esperado |
|---|---|---|---|
| T1 | *"Mostre só as demandas **atrasadas** do setor **Comercial**."* | sim | Filtros → Setor = Comercial, Prazo = Atrasadas → Aplicar filtros |
| T2 | *"Agora só as do **Paulo**."* | sim | Filtros → Responsável = Paulo → Aplicar. (Se o escopo estiver em "Minhas", observar se lê o aviso e escolhe **Ver Todas** por conta própria.) |
| T3 | *"Veja esse mesmo recorte como **Kanban** e depois como **Calendário**. O que **mudou** e o que **continuou igual**?"* | sim | Abas Kanban e Calendário. Avalia a **consistência do shell** (cabeçalho, barra, filtros, contador), não a qualidade do conteúdo do Kanban/Calendário |
| T4 | *"Abra uma demanda e **volte**: o recorte (visão, busca, filtros) precisa estar como estava."* | sim | Abrir uma demanda e usar "voltar" (da ficha ou do navegador) |
| T5 | *"**Limpe tudo** e ache as demandas do cliente **Santa Isabel**."* | sim | Limpar filtros → Filtros → Cliente (digitar 3 letras) → Aplicar |
| T6 | *"Mude o **prazo** de uma demanda."* | não | Clicar no prazo da linha (edição inline) |
| T7 | *"No **Kanban**, passe uma demanda para a **próxima etapa**."* | não | Arrastar o cartão para outra raia ou usar o ⋯ → "Mover para…". Em celular só o menu existe. Origem esperada das falhas: **K** |

**Pergunta final (compreensão):** *"Com suas palavras: o que são a Lista, o Kanban e o Calendário? Em que eles se parecem e em que se diferem?"* — **Compreendeu** se explica que são **os mesmos dados** (o mesmo conjunto de demandas) apresentados de formas diferentes.

## 4. Como classificar cada ocorrência

Toda hesitação, erro ou ajuda recebe uma **origem** (campo obrigatório). Isto impede rejeitar uma boa arquitetura por causa do problema errado:

| Origem | O que é | Exemplo | Conta contra o Workspace? |
|---|---|---|---|
| **S** — Shell/navegação/filtros | cabeçalho, abas, barra, estado preservado ao trocar de visão — é o que o Workspace promete | não achou "Filtros"; achou que "Escopo" era um filtro; perdeu o filtro ao trocar de aba | **sim** |
| **L** — Lista nova | a tabela, colunas, edição inline, agrupar | não entendeu a coluna Demanda; não achou o prazo | **sim** |
| **K** — Kanban novo (o mesmo de Quadros) | raias, cartões, arrastar e o menu "Mover para…" | não percebeu que o ⋯ move o cartão; achou os campos do cartão poucos | **não** conta contra o shell; vai para o backlog do Kanban. **Erro crítico aqui ainda bloqueia** (mover um cartão sem querer ou sem perceber para onde ele foi) |
| **V** — Visualização legada | conteúdo do **Calendário antigo** dentro do shell | o Calendário "é só uma lista" | **não** (vai para o backlog da fase 1D) |

**Erro crítico** (pesa mais que qualquer demora): a pessoa **acredita ver um recorte que não é o que está na tela** — por exemplo acha que filtrou só o Comercial e está vendo outra coisa; não percebe que o escopo é "Minhas"; perde o filtro sem notar — **ou altera um dado sem querer**. Oito segundos procurando um botão **não** é crítico.

## 5. Planilha de anotação (uma por participante)

Participante: ______ Perfil: ______ Data: ______ Dispositivo: ______

| Tarefa | Concluiu **sem ajuda**? (S/N) | Tempo | Nº de erros | Hesitou > 5 s? (S/N) | Origem (S/L/V) | **Erro crítico?** (S/N) | Observações (frases da pessoa) |
|---|---|---|---|---|---|---|---|
| T1 | | | | | | | |
| T2 | | | | | | | |
| T3 | | | | | | | |
| T4 | | | | | | | |
| T5 | | | | | | | |
| T6 | | | | | | | |
| T7 | | | | | | | |
| Pergunta final | Compreendeu? (S/N) | | | | | | |

Anote também: o nome que a pessoa deu a cada controle (Escopo, Mostrar, Filtros, Agrupar, Ordenar), o que ela esperava encontrar e não achou, e qualquer coisa que a surpreendeu.

## 6. Critério de passagem (fixado antes do teste)

Só se avança à fase 1C se **todas** forem verdadeiras:

1. **≥ 4 de 5 pessoas concluem cada tarefa crítica (T1–T5) sem orientação**;
2. **≥ 4 de 5 demonstram a compreensão** (Lista, Kanban e Calendário = os mesmos dados);
3. **nenhum erro crítico de origem S ou L**, mesmo que 4 de 5 tenham concluído. **Qualquer erro crítico bloqueia a passagem.**

Falhas de origem **K** e **V** não contam contra o Workspace (shell): vão para o backlog da visão correspondente, **exceto** um erro crítico de origem K, que bloqueia como qualquer outro.
Abaixo do critério: corrige-se a 1A (linguagem, filtros, colunas, navegação), registra-se o que mudou abaixo e **repete-se o teste com outras pessoas**.

## 7. O que a 1A tem de propósito "incompleto" (para não surpreender quem conduz)

- O **Kanban** já é o novo (o de Quadros: raias de cabeçalho colorido, cartões com borda na cor da raia, ⋯ "Mover para…"); falhas ali são **K**. O **Calendário** é o conteúdo antigo (lista de prazos) **dentro do shell novo**; falhas ali são **V**.
- No Kanban, **"+ Adicionar demanda"** de cada raia abre o assistente de sempre **sem** levar a etapa da raia (isso é uma rodada própria). Se alguém esperar que a demanda já nasça naquela etapa, anote como **K** e a necessidade.
- O menu de ações da linha (Concluir/Cancelar/Reabrir) não existe na Lista: está na ficha. Se alguém procurar, anote como **L** e a necessidade.
- "Mostrar" tem só **Em aberto** e **Concluídas** (sem "Todas").
- Os nomes **Escopo** e **Mostrar** são provisórios: anote como a pessoa os chama.
- Colunas padrão da Lista (6) são uma **hipótese** a validar: anote o que faltou ou sobrou.

## 8. Resultado e decisão (preencher depois)

| Item | Resultado |
|---|---|
| Tarefas críticas concluídas sem ajuda (T1…T5), de 5 | T1 __ T2 __ T3 __ T4 __ T5 __ |
| Compreensão (Lista/Kanban/Calendário = mesmos dados), de 5 | __ |
| Erros críticos de origem S ou L | __ |
| **Passou?** | __ |
| Falhas V (backlog 1C/1D) | |
| Mudanças que a 1A precisa (linguagem, filtros, colunas, navegação) | |
| Decisão e data | |
