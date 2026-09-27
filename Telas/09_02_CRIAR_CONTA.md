# 09_02 — Tela Criar Conta

> Documento funcional e visual da tela de criação de conta da LPS.
>
> Esta tela cria a identidade de acesso da pessoa à plataforma. Ela não cria organização, empresa, setor, perfil, permissões ou assinatura.

---

# 1. Objetivo

Permitir que uma nova pessoa crie sua conta de acesso à LPS.

A tela deve permitir cadastrar:

- nome de exibição;
- e-mail;
- senha;
- confirmação de senha;
- aceite dos Termos de Uso e da Política de Privacidade.

A criação da conta deve ser simples, rápida e clara.

---

# 2. Princípio da tela

A pessoa deve entender imediatamente:

1. qual nome aparecerá na LPS;
2. qual e-mail será utilizado para acesso;
3. como definir sua senha;
4. como confirmar a senha;
5. quais termos precisa aceitar;
6. como criar a conta;
7. como voltar ao Login.

A tela não deve parecer um cadastro empresarial completo.

---

# 3. Conta x Usuário da Organização

A LPS deve separar dois conceitos.

## Conta

Representa a identidade da pessoa na plataforma.

Exemplo:

```text
Nome de exibição:
Paulo Confar

E-mail:
paulo@email.com
```

## Usuário da organização

Será criado ou configurado posteriormente dentro de uma organização.

Exemplo:

```text
Organização:
Biasi

Usuário:
@pauloconfar
```

Regra:

```text
CONTA
≠
USUÁRIO DA ORGANIZAÇÃO
```

Uma mesma conta poderá participar de mais de uma organização.

---

# 4. Estrutura geral — Desktop

A tela é dividida em duas áreas principais:

```text
┌──────────────────────────────┬────────────────────────────────┐
│                              │                                │
│      ÁREA INSTITUCIONAL      │     ÁREA CRIAR CONTA           │
│                              │                                │
│     Azul institucional       │      Fundo claro               │
│                              │      Card branco               │
│                              │                                │
└──────────────────────────────┴────────────────────────────────┘
```

Proporção aproximada:

```text
50% área institucional
50% área de criação da conta
```

A divisão pode variar conforme a resolução, preservando equilíbrio visual.

---

# 5. Área institucional — Lado esquerdo

## 5.1 Fundo

Usar predominantemente tons de azul da identidade visual da LPS.

Base recomendada:

```text
Azul-marinho:   #0F2747
Azul principal: #2563EB
Azul vivo:      #38BDF8
```

O verde deve aparecer como apoio visual.

```text
Verde evolução: #18B981
```

Regra:

> O azul deve dominar a composição. O verde deve possuir presença menor.

---

## 5.2 Identificação superior

No topo esquerdo pode existir uma identificação discreta:

```text
LPS   —
```

Ela funciona como elemento de composição e não substitui o logotipo oficial.

---

## 5.3 Mensagem principal

Texto da referência visual:

```text
Comece sua gestão
com mais clareza.
```

Hierarquia:

- `Comece sua gestão` com maior destaque;
- `com mais clareza.` com peso visual inferior.

---

## 5.4 Texto de apoio

Texto da referência visual:

```text
Crie seu acesso à LPS e tenha todas
as ferramentas para planejar, acompanhar
e entregar seus projetos com mais
produtividade.
```

O texto deve ser curto e não competir com a ação principal da tela.

---

## 5.5 Símbolo da LPS

Utilizar o símbolo oficial da LPS:

```text
duas pessoas + seta ascendente
```

Pode aparecer em tamanho grande como elemento institucional.

Regras:

- utilizar o arquivo oficial;
- não redesenhar manualmente;
- não alterar proporções;
- não trocar as cores da marca;
- preservar a área de proteção;
- evitar sombra ou efeitos excessivos.

---

# 6. Área Criar Conta — Lado direito

## 6.1 Fundo da aplicação

Cor recomendada:

```text
#F5F8FC
```

---

## 6.2 Card

Utilizar card branco centralizado.

Cor:

```text
#FFFFFF
```

Características:

- cantos arredondados;
- sombra discreta;
- espaçamento interno confortável;
- largura adequada para leitura e preenchimento;
- sem excesso de elementos visuais.

---

# 7. Logotipo no card

Utilizar o logotipo oficial completo da LPS:

```text
[Símbolo] LPS
O amigo do gestor.
```

Regras:

- utilizar a versão positiva sobre fundo branco;
- respeitar área de proteção;
- não reconstruir o logo com texto comum;
- não modificar a assinatura `O amigo do gestor.`.

---

# 8. Título da tela

Texto:

```text
Criar sua conta
```

Fonte:

```text
Inter Bold
32–40 px
```

Cor:

```text
#172033
```

---

# 9. Texto de apoio

Texto:

```text
Comece criando seu acesso à LPS.
```

Fonte:

```text
Inter Regular
```

Cor:

```text
#64748B
```

---

# 10. Campo — Nome de exibição

Rótulo:

```text
Nome de exibição
```

Placeholder:

```text
Seu nome
```

Objetivo:

> Definir como a pessoa será apresentada na LPS.

Exemplos:

```text
Paulo Confar
Jennifer Silva
Ryan Santos
```

Características:

- obrigatório;
- não é login;
- não é o `@usuário` da organização;
- pode ser alterado posteriormente no perfil da conta;
- ícone de pessoa à esquerda.

Não utilizar o rótulo `Nome completo`, pois a LPS não precisa exigir nome civil completo para criar a conta.

---

# 11. Campo — E-mail

Rótulo:

```text
E-mail
```

Placeholder:

```text
seu@email.com
```

Características:

- obrigatório;
- validar formato de e-mail;
- utilizado para autenticação;
- utilizado para recuperação de senha;
- deve identificar uma única conta;
- ícone de e-mail à esquerda.

---

# 12. Campo — Senha

Rótulo:

```text
Senha
```

Placeholder:

```text
Sua senha
```

Características:

- obrigatório;
- caracteres ocultos por padrão;
- ícone de cadeado à esquerda;
- ação visualizar/ocultar senha à direita;
- requisitos de senha devem ser validados durante o preenchimento.

A política técnica de senha deve ser definida no documento específico de autenticação e segurança.

---

# 13. Campo — Confirmar senha

Rótulo:

```text
Confirmar senha
```

Placeholder:

```text
Confirme sua senha
```

Características:

- obrigatório;
- caracteres ocultos por padrão;
- ação visualizar/ocultar senha;
- deve corresponder exatamente ao campo `Senha`.

---

# 14. Termos de Uso e Política de Privacidade

Exibir checkbox:

```text
[ ] Li e aceito os Termos de Uso e a Política de Privacidade.
```

`Termos de Uso` e `Política de Privacidade` devem ser links independentes.

Ao abrir os documentos, os campos já preenchidos não devem ser perdidos.

O aceite é obrigatório para criar a conta.

---

# 15. Botão — Criar conta

Texto:

```text
Criar conta   →
```

Cor principal:

```text
#2563EB
```

Características:

- largura total do formulário;
- texto branco;
- principal ação visual da tela;
- cantos arredondados;
- seta discreta;
- possuir estado de carregamento;
- impedir múltiplos envios simultâneos.

Fluxo:

```text
Criar conta
↓
Validar campos
↓
Validar aceite dos termos
↓
Validar disponibilidade do e-mail
↓
Criar identidade da conta
↓
Continuar fluxo de entrada na LPS
```

---

# 16. Já possui uma conta

Na parte inferior do card:

```text
Já possui uma conta?  Entrar
```

`Entrar` deve ser clicável.

Fluxo:

```text
Criar conta
↓
Entrar
↓
Login
```

---

# 17. Validações

## Nome de exibição vazio

```text
Informe seu nome.
```

## E-mail vazio

```text
Informe seu e-mail.
```

## E-mail inválido

```text
Informe um e-mail válido.
```

## E-mail já cadastrado

Mensagem:

```text
Já existe uma conta com este e-mail.
```

Oferecer ações:

```text
Entrar
```

ou:

```text
Esqueci minha senha
```

## Senha vazia

```text
Informe uma senha.
```

## Senha fora dos requisitos

Informar de forma objetiva o requisito que ainda não foi atendido.

## Confirmação de senha vazia

```text
Confirme sua senha.
```

## Senhas diferentes

```text
As senhas não coincidem.
```

## Termos não aceitos

```text
Aceite os Termos de Uso e a Política de Privacidade para continuar.
```

---

# 18. Comportamento do formulário

## Ao pressionar Enter

O sistema pode tentar criar a conta se os campos obrigatórios estiverem preenchidos.

## Durante criação

O botão deve entrar em estado de carregamento.

Exemplo:

```text
Criando conta...
```

## Após erro de validação

Preservar:

- nome de exibição;
- e-mail;
- aceite dos termos, desde que juridicamente permitido pela implementação.

As senhas devem seguir a política de segurança definida para o produto.

---

# 19. Estados visuais

Os campos devem possuir estados claros:

```text
Normal
Foco
Preenchido
Erro
Desabilitado
```

O botão deve possuir:

```text
Normal
Hover
Pressionado
Carregando
Desabilitado
```

O checkbox deve possuir:

```text
Desmarcado
Marcado
Foco
Erro
```

---

# 20. Pagamento e assinatura

O pagamento não ocorre nesta tela.

A tela `Criar Conta` cria a identidade da pessoa.

Ela não deve pedir:

- cartão;
- plano;
- CNPJ;
- quantidade de usuários;
- responsável financeiro;
- dados de cobrança.

A contratação deve acontecer posteriormente no contexto da organização.

Fluxo conceitual:

```text
CRIAR CONTA
↓
IDENTIDADE DA PESSOA CRIADA
↓
CRIAR OU ENTRAR EM ORGANIZAÇÃO
↓
CONFIGURAR ORGANIZAÇÃO
↓
PLANO / ASSINATURA
↓
PAGAMENTO
↓
ORGANIZAÇÃO HABILITADA CONFORME REGRA COMERCIAL
```

Regra importante:

> Possuir uma conta na LPS não significa, sozinho, possuir uma assinatura paga ativa.

A regra comercial final de cobrança será definida em documento próprio.

---

# 21. O que não existe nesta tela

Não incluir:

- organização;
- empresa;
- CNPJ;
- setor;
- cargo;
- `@usuário` da organização;
- perfil;
- permissões;
- administrador;
- gestor;
- plano;
- cartão;
- dados de faturamento.

Essas informações pertencem aos próximos fluxos.

---

# 22. Tipografia

Fonte oficial da interface:

```text
Inter
```

Hierarquia recomendada:

```text
H1
Inter Bold
32–40 px

H2
Inter SemiBold
24 px

H3
Inter SemiBold
20 px

H4
Inter Medium
16 px

Body
Inter Regular
14 px

Caption
Inter Regular
12 px
```

---

# 23. Paleta da tela

## Cores da marca

```text
Azul-marinho      #0F2747
Azul principal    #2563EB
Azul vivo         #38BDF8
Verde evolução    #18B981
```

## Cores neutras

```text
Fundo              #F5F8FC
Cards              #FFFFFF
Bordas             #E2E8F0
Texto principal    #172033
Texto secundário   #64748B
Texto desabilitado #94A3B8
```

---

# 24. Mobile

No mobile, a área institucional lateral não deve ser comprimida ao lado do formulário.

Prioridade:

```text
Logo
↓
Criar sua conta
↓
Nome de exibição
↓
E-mail
↓
Senha
↓
Confirmar senha
↓
Termos
↓
Criar conta
↓
Entrar
```

A área institucional pode:

- desaparecer;
- virar um cabeçalho compacto;
- utilizar apenas o logotipo ou símbolo oficial.

O formulário deve ocupar a maior parte da tela.

---

# 25. Critérios de aceite

A tela está pronta quando:

- utiliza o logotipo oficial da LPS;
- segue a paleta oficial da marca;
- utiliza a fonte Inter;
- possui campo `Nome de exibição`;
- possui campo de e-mail;
- possui campo de senha;
- possui confirmação de senha;
- senha pode ser visualizada ou ocultada;
- possui aceite dos Termos de Uso;
- possui aceite da Política de Privacidade;
- possui ação `Criar conta`;
- possui ação `Entrar`;
- e-mail duplicado é tratado;
- senhas diferentes são tratadas;
- campos obrigatórios são tratados;
- o botão possui estado de carregamento;
- funciona no desktop;
- funciona no mobile;
- não solicita dados de organização;
- não configura permissões;
- não solicita pagamento.

---

# 26. Fluxo resumido

```text
LOGIN
↓
CRIAR CONTA
↓
NOME DE EXIBIÇÃO
↓
E-MAIL
↓
SENHA
↓
CONFIRMAR SENHA
↓
ACEITAR TERMOS
↓
CRIAR CONTA
↓
VALIDAÇÃO
↓
┌───────────────────────┐
│                       │
ERRO                    SUCESSO
│                       │
CORRIGIR DADOS          CONTA CRIADA
│                       │
PERMANECE NA TELA       PRÓXIMO CONTEXTO
```

---

# 27. Próximos fluxos relacionados

```text
Criar conta
├── Entrar
│   └── Login
├── Termos de Uso
├── Política de Privacidade
└── Conta criada
    └── Próximo contexto de entrada na LPS
```

O próximo contexto será definido nos documentos seguintes da sequência de telas.

---

# 28. Referência visual

A referência visual aprovada para esta tela utiliza:

- painel institucional azul à esquerda;
- fundo claro à direita;
- card branco centralizado;
- logotipo oficial completo no topo;
- título `Criar sua conta`;
- subtítulo `Comece criando seu acesso à LPS.`;
- campo `Nome de exibição`;
- campo `E-mail`;
- campo `Senha`;
- campo `Confirmar senha`;
- checkbox de Termos de Uso e Política de Privacidade;
- botão azul `Criar conta`;
- ação `Entrar`;
- símbolo da LPS como elemento visual institucional.

O layout visual pode receber ajustes finos durante implementação, mas deve preservar essa arquitetura e a identidade visual oficial da LPS.
