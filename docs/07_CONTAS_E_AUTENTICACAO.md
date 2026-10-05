# 07 — Contas e autenticação

> Como uma pessoa passa a existir na LPS e como entra. Especificação das telas
> em `Telas/09_01_LOGIN.md`, `09_02_CRIAR_CONTA.md`, `09_03_CONFIRMAR_EMAIL.md`
> e `09_04_CADASTRO_NOVO_USUARIO_LPS.md`. Código em `accounts/` e nas telas de
> usuário de `core/`.
> Atualizado em 03/10/2026 (código no commit `add5acd`; o app `accounts` não
> mudou nos commits de 01–02/10).

---

## 1. Duas formas de criar uma pessoa

| | Autocadastro (`/accounts/criar-conta/`) | Cadastro pelo administrador (`/usuarios/novo/`) |
|---|---|---|
| Quem faz | a própria pessoa | quem tem `usuario.editar` |
| Conta nasce | **inativa** até confirmar o e-mail | ativa, com senha definida pelo admin |
| `username` | gerado (`conta-<20 hex>`) | digitado pelo admin |
| Organização | **nenhuma** | a do admin (campo obrigatório, travado nela) |
| Setores | nenhum | "Setores em que atua" e "Setores que gerencia" no formulário (`AccessService.sync_user_sectors`) |
| Auditoria | não | `USER_CREATED` (+ `SECTORS_CHANGED`) |

Em ambos os casos o signal `accounts.signals` cria o `Profile` vazio no
`post_save` do `User`; o `UserFormView` preenche a organização em seguida.

O cadastro pelo administrador (`UserForm` em `core/forms.py`, tela
`core/user_form.html`) pede nome, e-mail, nome de usuário, organização, senha
e confirmação (obrigatórias ao cadastrar: **não há convite por e-mail**, então
o admin informa a senha inicial à pessoa) e setores. Na edição
(`/usuarios/<id>/`), senha em branco mantém a atual; preencher grava
`PASSWORD_RESET` no log, e desmarcar "Permitir que esta pessoa entre na LPS"
inativa a conta sem apagar o histórico. Os acessos (perfis e concessões) são
definidos depois, em `/usuarios/<id>/acessos/` ([05_AUTORIZACAO.md](05_AUTORIZACAO.md)).

Uma conta criada pelo autocadastro consegue logar depois de confirmar o
e-mail, mas **toda tela da LPS a redireciona para `/accounts/me/`** até um
administrador vinculá-la a uma organização (hoje, pelo Admin do Django —
a tela `/usuarios/` só lista pessoas que já são da organização).

---

## 2. Autocadastro e confirmação de e-mail

```mermaid
sequenceDiagram
    participant P as Pessoa
    participant S as SignUpView
    participant V as VerifyEmailView
    participant DB as Banco
    P->>S: nome, e-mail, senha, aceite dos termos
    S->>DB: User (is_active=False) + Profile vazio
    S->>DB: EmailVerification.issue (código de 6 dígitos)
    S-->>P: e-mail com o código (sessão guarda pending_verification_user_id)
    P->>V: código
    V->>DB: verify(código)
    V-->>P: conta ativa → tela de login
```

- `SignUpForm` (`accounts/forms.py`): nome (gravado em `first_name`), e-mail
  único sem diferenciar maiúsculas (gravado em minúsculas), senha validada
  pelos validadores do Django (`AUTH_PASSWORD_VALIDATORS`), confirmação de
  senha e aceite dos termos obrigatório.
- `EmailVerification` (`accounts/models.py`):
  - código de 6 dígitos, válido por **15 minutos** (`CODE_TTL`);
  - no máximo **5 tentativas** (`MAX_ATTEMPTS`);
  - reenviar só depois de **60 segundos** (`RESEND_COOLDOWN`); o novo código
    substitui o anterior.
- A tela de confirmação mostra o e-mail mascarado (`ab***@dominio`) e usa a
  sessão (`PendingVerificationMixin`) para saber qual conta está pendente; sem
  ela, volta para o cadastro. Código expirado ou com 5 tentativas esgotadas
  pede um novo código; reenviar antes de 60 s é recusado com aviso.
- O e-mail do código (assunto "Confirme seu e-mail — LPS") é enviado por
  `send_mail` direto na view, sem tratamento de erro: sem SMTP configurado em
  produção, "Criar conta" dá erro 500 ([12_DEPLOY_RENDER.md](12_DEPLOY_RENDER.md)).
- Não existe tela para retomar a confirmação sem a sessão, nem limpeza de
  contas pendentes: uma conta abandonada continua ocupando o e-mail.
- `confirmar-email/alterar/` troca o e-mail da conta pendente (também único) e
  emite um novo código.
- Em dev, o e-mail com o código aparece no console do `runserver`.

| URL | Nome | View |
|---|---|---|
| `/accounts/criar-conta/` | `signup` | `SignUpView` |
| `/accounts/confirmar-email/` | `verify-email` | `VerifyEmailView` |
| `/accounts/confirmar-email/reenviar/` (POST) | `verify-email-resend` | `ResendVerificationCodeView` |
| `/accounts/confirmar-email/alterar/` | `verify-email-change` | `ChangeVerificationEmailView` |

---

## 3. Login

- `/accounts/login/` usa `LoginView` com `EmailAuthenticationForm` (o campo
  "username" vira um campo de e-mail).
- `accounts.auth_backends.EmailBackend` é o **único** backend: busca
  `User` por `email__iexact`, confere a senha e `user_can_authenticate`
  (contas inativas são recusadas). Se houver dois usuários com o mesmo e-mail,
  o login é recusado.
- O `username` continua existindo como identificador interno e para
  @menções.
- Após o login: `home` (`/`), ou o `next` informado. Logout:
  `/accounts/logout/` → login (`LOGIN_URL`, `LOGIN_REDIRECT_URL` e
  `LOGOUT_REDIRECT_URL` em [03_CONFIGURACAO.md](03_CONFIGURACAO.md)).

---

## 4. Recuperação de senha

Views nativas do Django, com templates próprios em `templates/accounts/`:

| URL | Nome |
|---|---|
| `/accounts/esqueci-senha/` | `password_reset` |
| `/accounts/esqueci-senha/enviado/` | `password_reset_done` |
| `/accounts/redefinir-senha/<uidb64>/<token>/` | `password_reset_confirm` |
| `/accounts/redefinir-senha/concluido/` | `password_reset_complete` |

Corpo e assunto do e-mail: `templates/registration/password_reset_email.html`
e `password_reset_subject.txt`. A troca pelo próprio usuário **não** é
auditada; `AuditLog.PASSWORD_RESET` só é gravado quando um admin define nova
senha em `/usuarios/<id>/`.

---

## 5. Perfil e superusuário

- `/accounts/me/` (`profile`): a pessoa edita telefone e setor principal
  (`ProfileForm`). A organização aparece só para leitura.
- Superusuário: criado por `createsuperuser` (local) ou por
  `ensure_superuser` (deploy; lê `DJANGO_SUPERUSER_USERNAME`,
  `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD`, não faz nada se
  faltarem usuário ou senha e nunca altera um usuário já existente). Passa por
  todas as verificações de autorização, mas precisa de organização no `Profile`
  para usar as telas da LPS — e de **e-mail** para conseguir logar.

---

## 6. Modelos e Admin

| Modelo | Papel | No Admin |
|---|---|---|
| `Profile` | 1:1 com `User`: organização (`PROTECT`, opcional), telefone, setor principal | sim (`ProfileAdmin`) |
| `UserSector` | Participação em setor (`MEMBRO`/`GESTOR`) com `joined_at`/`removed_at`; única por usuário e setor enquanto ativa. Salvar ou apagar invalida o cache do motor de autorização (`accounts/signals.py`) | sim (`UserSectorAdmin`) |
| `EmailVerification` | 1:1 com `User`: código, expiração, tentativas, `confirmed_at` | não |

Detalhes de campos em [04_MODELOS_DE_DADOS.md](04_MODELOS_DE_DADOS.md).
Migrations do app: `0001_initial`, `0002_alter_usersector_options_and_more` e
`0003_emailverification`.
