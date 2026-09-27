# 09_01 — Tela de Login

> Documento funcional e visual da tela de Login da LPS.
>
> Esta tela deve seguir a identidade visual oficial da LPS e manter uma experiência simples, profissional e direta.

---

# 1. Objetivo

Permitir que uma pessoa já cadastrada acesse a LPS utilizando:

- e-mail;
- senha.

A tela deve transmitir:

- confiança;
- clareza;
- simplicidade;
- profissionalismo.

---

# 2. Princípio da tela

A tela de Login deve responder imediatamente:

1. Onde informo meu e-mail?
2. Onde informo minha senha?
3. Como entro?
4. Como recupero minha senha?
5. Como crio uma conta?

Não deve existir nenhuma configuração de organização, empresa, setor, perfil ou permissão nesta tela.

---

# 3. Estrutura geral — Desktop

A tela é dividida em duas áreas principais:

```text
┌──────────────────────────────┬────────────────────────────────┐
│                              │                                │
│      ÁREA INSTITUCIONAL      │        ÁREA DE LOGIN           │
│                              │                                │
│     Azul institucional       │      Fundo claro               │
│                              │      Card branco               │
│                              │                                │
└──────────────────────────────┴────────────────────────────────┘
```

Proporção aproximada:

```text
50% área institucional
50% área de login
```

A divisão pode variar conforme a resolução, preservando equilíbrio visual.

---

# 4. Área institucional — Lado esquerdo

## 4.1 Fundo

Usar predominantemente tons de azul da identidade visual da LPS.

Base recomendada:

```text
Azul-marinho: #0F2747
Azul principal: #2563EB
Azul vivo: #38BDF8
```

O verde deve aparecer apenas como apoio visual.

```text
Verde evolução: #18B981
```

Regra:

> O azul deve dominar a composição. O verde deve ser utilizado com menor presença.

---

## 4.2 Elemento superior

No topo esquerdo pode existir uma identificação discreta:

```text
LPS   —
```

Função:

- reforçar a marca;
- compor visualmente o painel;
- não competir com o logotipo principal da área de login.

---

## 4.3 Mensagem principal

Texto:

```text
Gestão de projetos
com mais clareza.
```

Hierarquia:

- `Gestão de projetos` com maior destaque;
- `com mais clareza.` com peso visual inferior.

A mensagem deve permanecer curta.

---

## 4.4 Texto de apoio

Texto:

```text
Planeje, acompanhe e entregue suas
atividades com mais produtividade,
controle e resultados.
```

O texto deve possuir contraste suficiente, mas não competir com o título principal.

---

## 4.5 Símbolo da LPS

Utilizar o símbolo oficial da LPS:

```text
duas pessoas + seta ascendente
```

Pode ser utilizado em tamanho grande como elemento visual no painel esquerdo.

Regras:

- utilizar o arquivo oficial;
- não redesenhar manualmente;
- não alterar proporções;
- não trocar as cores da marca;
- não aplicar sombra excessiva;
- preservar a área de proteção da marca.

---

## 4.6 Elementos gráficos

Podem existir formas abstratas derivadas da linguagem visual da marca.

Características:

- curvas suaves;
- variações de azul;
- pequenos destaques em verde;
- baixa interferência sobre os textos;
- sem excesso de elementos decorativos.

---

# 5. Área de Login — Lado direito

## 5.1 Fundo da aplicação

Cor recomendada:

```text
#F5F8FC
```

A área deve possuir aparência limpa e clara.

---

## 5.2 Card de Login

Utilizar um card branco centralizado.

Cor:

```text
#FFFFFF
```

Características:

- cantos arredondados;
- sombra discreta;
- espaçamento interno confortável;
- largura suficiente para leitura e preenchimento sem parecer excessivamente grande.

---

# 6. Logotipo no card

Utilizar o logotipo oficial completo da LPS na parte superior do card:

```text
[Símbolo] LPS
O amigo do gestor.
```

Regras:

- utilizar arquivo oficial;
- versão positiva sobre fundo branco;
- respeitar área de proteção;
- não recriar o logotipo com fonte de texto;
- não substituir a assinatura oficial.

---

# 7. Título da tela

Texto:

```text
Entrar na LPS
```

Fonte:

```text
Inter
```

Estilo recomendado:

```text
Inter Bold
32–40 px
```

Cor:

```text
#172033
```

---

# 8. Texto de apoio

Texto:

```text
Acesse sua conta para continuar.
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

# 9. Campo — E-mail

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
- aceitar formato de e-mail;
- ícone de e-mail no lado esquerdo;
- borda discreta;
- fundo branco;
- boa área de clique/toque.

Cor da borda:

```text
#E2E8F0
```

Texto principal:

```text
#172033
```

Placeholder:

```text
#94A3B8
```

---

# 10. Campo — Senha

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
- ícone de cadeado no lado esquerdo;
- ícone de visualizar/ocultar senha no lado direito.

A ação de visualizar a senha não deve alterar o valor digitado.

---

# 11. Esqueci minha senha

Link:

```text
Esqueci minha senha
```

Posição:

- abaixo do campo de senha;
- alinhado à direita.

Ao clicar:

```text
Login
↓
Esqueci minha senha
```

Essa ação pertence a outro fluxo e deve possuir documento próprio.

---

# 12. Botão — Entrar

Texto:

```text
Entrar   →
```

Cor principal:

```text
#2563EB
```

Características:

- largura total do formulário;
- destaque visual principal da tela;
- texto branco;
- seta discreta à direita do texto;
- cantos arredondados;
- estado de carregamento após clique.

Ao clicar:

```text
Validar campos
↓
Autenticar
↓
Credenciais válidas?
├── Sim → continuar fluxo
└── Não → exibir erro
```

---

# 13. Criar conta

Após o botão Entrar, utilizar um divisor visual discreto.

Texto:

```text
Ainda não tem uma conta?  Criar conta
```

`Criar conta` deve ser clicável.

Fluxo:

```text
Login
↓
Criar conta
```

A criação de conta pertence a outro documento.

---

# 14. Comportamento do formulário

## Ao pressionar Enter

O sistema deve tentar realizar o login.

## Durante autenticação

O botão deve impedir múltiplos envios simultâneos.

Exemplo:

```text
Entrando...
```

## Após erro

Manter:

```text
E-mail preenchido
```

Limpar:

```text
Senha
```

---

# 15. Validações

## E-mail vazio

Mensagem:

```text
Informe seu e-mail.
```

## E-mail inválido

Mensagem:

```text
Informe um e-mail válido.
```

## Senha vazia

Mensagem:

```text
Informe sua senha.
```

## Credenciais inválidas

Mensagem:

```text
E-mail ou senha inválidos.
```

Não informar qual credencial está incorreta.

---

# 16. Estados visuais

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

---

# 17. Tipografia

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

# 18. Paleta da tela

## Cores da marca

```text
Azul-marinho      #0F2747
Azul principal    #2563EB
Azul vivo         #38BDF8
Verde evolução    #18B981
```

## Cores neutras

```text
Fundo             #F5F8FC
Cards             #FFFFFF
Bordas            #E2E8F0
Texto principal   #172033
Texto secundário  #64748B
Texto desabilitado #94A3B8
```

---

# 19. Mobile

No mobile, não reproduzir o layout dividido do desktop de forma espremida.

Prioridade:

```text
Logo
↓
Entrar na LPS
↓
E-mail
↓
Senha
↓
Esqueci minha senha
↓
Entrar
↓
Criar conta
```

A área institucional do lado esquerdo pode:

- desaparecer;
- virar um pequeno cabeçalho visual;
- utilizar somente elementos mínimos da marca.

O formulário deve ocupar a maior parte da tela.

---

# 20. Segurança

A tela de Login trata apenas de autenticação.

```text
Autenticação
=
Quem é você?
```

Após autenticar, a LPS ainda precisa verificar:

```text
Autorização
=
O que você pode fazer?
```

Login válido não concede acesso irrestrito.

A validação não pode depender apenas da interface.

---

# 21. O que não existe nesta tela

Não incluir:

- escolha de organização;
- escolha de empresa;
- escolha de setor;
- criação de usuário da organização;
- definição de gestor;
- definição de administrador;
- configuração de perfil;
- configuração de permissões;
- configuração de escopo.

Esses elementos acontecem após a autenticação e possuem fluxos próprios.

---

# 22. Fora do D0

Podem ser avaliados futuramente:

- Entrar com Microsoft;
- Entrar com Google;
- autenticação corporativa;
- autenticação multifator.

Não devem aparecer na interface antes de existir funcionalidade real.

---

# 23. Critérios de aceite

A tela está pronta quando:

- o logotipo oficial da LPS é utilizado corretamente;
- a tela segue a paleta oficial da marca;
- a interface utiliza Inter;
- existe campo de e-mail;
- existe campo de senha;
- senha pode ser visualizada ou ocultada;
- existe ação Entrar;
- existe ação Esqueci minha senha;
- existe ação Criar conta;
- o sistema trata campos obrigatórios;
- credenciais inválidas apresentam erro;
- o botão possui estado de carregamento;
- o layout funciona no desktop;
- o layout funciona no mobile;
- nenhuma configuração de autorização ocorre no Login.

---

# 24. Fluxo resumido

```text
ABRIR LPS
↓
LOGIN
↓
E-MAIL + SENHA
↓
ENTRAR
↓
AUTENTICAÇÃO
↓
┌───────────────────────┐
│                       │
INVÁLIDA                VÁLIDA
│                       │
ERRO                     CONTINUAR
│                       │
PERMANECE NO LOGIN      PRÓXIMO CONTEXTO
```

---

# 25. Próximos fluxos relacionados

```text
Login
├── Criar conta
├── Esqueci minha senha
└── Login válido
    └── Próximo contexto da conta
```

A regra da próxima tela após login será definida nos documentos seguintes da sequência de telas.

---

# 26. Referência visual

A referência visual aprovada para esta tela utiliza:

- painel institucional azul à esquerda;
- fundo claro à direita;
- card branco centralizado;
- logotipo oficial completo no topo;
- título `Entrar na LPS`;
- campos de e-mail e senha;
- link `Esqueci minha senha`;
- botão azul `Entrar`;
- link `Criar conta`;
- símbolo da LPS como elemento visual institucional.

O layout visual pode receber ajustes finos durante implementação, mas deve preservar essa arquitetura.
