# Cadastro de Novo Usuário — LPS

## Objetivo

O cadastro de usuário deve ser simples, guiado e dividido em **3 etapas sequenciais**.

A pessoa não precisa preencher tudo em uma única tela.

Fluxo:

**1. Dados pessoais → 2. Estrutura organizacional → 3. Conta e acesso**

Os dados preenchidos devem ser preservados ao avançar ou voltar entre as etapas.

---

# 1. Dados pessoais

Objetivo: identificar a pessoa que será cadastrada.

Campos:

- Nome completo
- E-mail
- Usuário
- Telefone (opcional)
- Situação: Ativo / Inativo

## Regras

- O campo **Usuário** pode ser sugerido automaticamente a partir do nome ou e-mail.
- O administrador pode alterar a sugestão antes de continuar.
- A situação define se a pessoa poderá acessar o sistema.
- Validar os campos obrigatórios antes de avançar.

Ações:

- Cancelar
- Continuar

---

# 2. Estrutura organizacional

Objetivo: definir onde a pessoa está inserida dentro da organização.

## Organização

Na LPS, o termo correto é **Organização**.

Exemplo:

**Organização: Biasi**

Não utilizar "Empresa" nesta tela quando o conceito representado for a organização principal à qual o usuário pertence.

## Onde atua

Permite selecionar um ou mais setores em que a pessoa trabalha.

Exemplo:

- Comercial
- Compras
- Engenharia

A seleção deve ser feita por campo pesquisável com chips, evitando listas grandes de checkboxes.

## O que gerencia

Permite selecionar os setores pelos quais a pessoa possui responsabilidade gerencial.

Exemplo:

- Compras

## Regra importante

**Setor não é permissão.**

Estar em um setor ou gerenciar um setor define a posição estrutural da pessoa dentro da organização, mas não concede automaticamente acesso a funções do sistema.

As permissões são configuradas posteriormente em **Acessos**.

Ações:

- Voltar
- Cancelar
- Continuar

---

# 3. Conta e acesso

Objetivo: definir como a pessoa receberá acesso inicial à LPS.

## Forma de acesso

### Opção recomendada — Enviar convite por e-mail

A pessoa recebe um convite e cria a própria senha.

### Opção alternativa — Definir senha manualmente

Campos:

- Senha inicial
- Confirmar senha

Deve existir opção para mostrar ou ocultar a senha.

---

## Resumo do usuário

Antes de criar, mostrar um resumo com:

- Nome
- E-mail
- Organização
- Setores em que atua
- Setores que gerencia
- Situação da conta
- Forma de acesso

Exemplo:

**Arthur Naressi**  
Organização: Biasi  
Onde atua: Comercial, Compras, Engenharia  
Gerencia: Compras  
Situação: Ativo

---

## Finalização

Ações:

- Voltar
- Cancelar
- Criar usuário

Após a criação:

**Usuário criado com sucesso**

Próxima ação recomendada:

**Configurar acessos →**

A criação do usuário e a configuração de permissões devem continuar sendo etapas separadas.

---

# Comportamento geral

- O cadastro deve acontecer dentro do mesmo fluxo, sem parecer três sistemas diferentes.
- O usuário pode voltar de etapa sem perder os dados já preenchidos.
- Cada etapa valida apenas os campos necessários para avançar.
- O progresso deve ficar visível no topo:
  - Dados pessoais
  - Estrutura organizacional
  - Conta e acesso
- Evitar textos técnicos e excesso de explicações.
- Priorizar campos pesquisáveis, seleção por chips e ações claras.
- Manter a identidade visual oficial da LPS.
