# LPS — Plataforma de Gestão do Trabalho

Aplicação Django que implementa o núcleo D0 da LPS: uma plataforma de gestão do
trabalho **multi-organização** que organiza **Demandas** (no código, `Activity`)
e suas tarefas, torna responsabilidades visíveis, registra o que acontece durante
a execução e transforma esse histórico em informação para gestão. As Demandas e as
tarefas aparecem em quadros dinâmicos com visões Tabela, Kanban e Calendário.

> Atualizado em 03/10/2026 (código no commit `add5acd`). Vocabulário da interface:
> "Atividade" virou **Demanda**, "Situação" virou **Etapa** e "Condição" virou
> **Status** (glossário no começo de [`docs/01_ARQUITETURA.md`](docs/01_ARQUITETURA.md)).

- **O produto** (regras de negócio e telas) está em [`Regras/`](Regras/00_INDICE_LPS.md) e [`Telas/`](Telas/).
- **O código** (como essas regras foram implementadas) está documentado em [`docs/`](#documentação-técnica).

## Stack

| Item | Versão / escolha |
|---|---|
| Framework | Django 5.2 (LTS) |
| Python | 3.13/3.14 no desenvolvimento local (o `.venv` atual é 3.13) · 3.12.7 no Render |
| Banco | SQLite (dev) · PostgreSQL via `DATABASE_URL` (prod) |
| Servidor | `runserver` (dev) · gunicorn + whitenoise (prod) |
| Frontend | Templates Django + CSS/JS estáticos, sem bundler |
| Dependências | `django-environ`, `nh3` (sanitização de HTML), `gunicorn`, `whitenoise`, `psycopg` — ver [`requirements.txt`](requirements.txt) |
| Testes | Django `manage.py test` (Python) · `node --test` com `jsdom` (JavaScript, `npm run test:js`) |

## Início rápido (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # e defina SECRET_KEY
python manage.py migrate
python manage.py seed_lps_demo  # organização "Biasi", setores, ações e perfis
python manage.py createsuperuser
python manage.py runserver
```

Antes de usar as telas, **vincule seu usuário a uma organização** (Admin do
Django → Accounts → Perfis → campo "organização"); sem isso toda tela redireciona para o
perfil. Detalhes em [`docs/02_AMBIENTE_LOCAL.md`](docs/02_AMBIENTE_LOCAL.md).

O login é feito **por e-mail**, não por nome de usuário. A Caixa de Entrada
(`/entrada/`) vem **inativa** (`INTAKE_ENABLED`, ver
[`docs/03_CONFIGURACAO.md`](docs/03_CONFIGURACAO.md)) e o fluxo operacional antigo
de tarefas (`/fila/`, `/processos/`, `/tarefas/<id>/…`) está desativado (responde
410): as tarefas vivem no quadro de cada Demanda.

## Documentação técnica

| # | Documento | Conteúdo |
|---|---|---|
| 01 | [Arquitetura](docs/01_ARQUITETURA.md) | Apps, camadas, multi-tenancy, convenções do código |
| 02 | [Ambiente local](docs/02_AMBIENTE_LOCAL.md) | Instalação, dados de demonstração, management commands (incluindo os de `boards`) |
| 03 | [Configuração](docs/03_CONFIGURACAO.md) | Settings dev/prod, variáveis de ambiente, estáticos e download seguro de anexos |
| 04 | [Modelos de dados](docs/04_MODELOS_DE_DADOS.md) | Todos os models por app, enums, constraints, diagrama ER |
| 05 | [Autorização](docs/05_AUTORIZACAO.md) | Motor de acessos: ações, perfis, escopos, `AuthorizationService` |
| 06 | [Atividades e tarefas](docs/06_ATIVIDADES_E_TAREFAS.md) | Demandas e tarefas: ciclos de vida, fila, prazos, sessões, processos (o fluxo operacional de tarefas está desativado) |
| 07 | [Contas e autenticação](docs/07_CONTAS_E_AUTENTICACAO.md) | Cadastro, confirmação de e-mail, login por e-mail, recuperação de senha, perfil |
| 08 | [Notificações e auditoria](docs/08_NOTIFICACOES_E_AUDITORIA.md) | O que gera notificação, e-mail e registro de auditoria |
| 09 | [Rotas](docs/09_ROTAS.md) | Referência de todas as URLs |
| 10 | [Frontend](docs/10_FRONTEND.md) | Templates, JS, CSS, context processors, template tags |
| 11 | [Testes](docs/11_TESTES.md) | Como rodar, organização, helpers, teste JS |
| 12 | [Deploy no Render](docs/12_DEPLOY_RENDER.md) | `render.yaml`, primeiro deploy, limitações do plano free, histórico de correções |
| 13 | [Pendências conhecidas](docs/13_PENDENCIAS_CONHECIDAS.md) | Defeitos e dívidas técnicas mapeados |

## Especificações dos quadros dinâmicos

Além dos docs 01–13 (que descrevem o **código atual**), a pasta `docs/` guarda cinco
especificações `LPS_*.md` dos quadros dinâmicos (app `boards`). As de colunas
dinâmicas, Tabela e Kanban trazem, no começo, uma tabela de **status de implementação**
(o que está implementado, parcial ou não implementado, e onde está no código); a de
Calendário é texto de especificação, sem essa tabela, e a de Elementos/Subelementos
descreve uma evolução arquitetural **proposta**, ainda não implementada:

| Documento | Conteúdo |
|---|---|
| [`LPS_ESPECIFICACAO_COLUNAS_DINAMICAS.md`](docs/LPS_ESPECIFICACAO_COLUNAS_DINAMICAS.md) | Motor de colunas: tipos de coluna, configurações, etiquetas, células tipadas |
| [`LPS_VISUALIZACAO_TABELA_QUADRO.md`](docs/LPS_VISUALIZACAO_TABELA_QUADRO.md) | Tabela do Quadro (o "Quadro principal"): grupos, colunas, itens, edição inline |
| [`LPS_VISUALIZACAO_KANBAN.md`](docs/LPS_VISUALIZACAO_KANBAN.md) | Kanban: agrupamento, raias, cartões, movimentação |
| [`LPS_VISUALIZACAO_CALENDARIO.md`](docs/LPS_VISUALIZACAO_CALENDARIO.md) | Calendário: itens posicionados por uma coluna de Data |
| [`LPS_ELEMENTOS_SUBELEMENTOS_PROCESSOS.md`](docs/LPS_ELEMENTOS_SUBELEMENTOS_PROCESSOS.md) | Conceito de Elemento e Subelemento e a integração com Processos |

Uma versão compilada em PDF da documentação técnica (13 capítulos, 5 apêndices de especificação e capturas de tela com dados fictícios) está em
[`docs/LPS_Documentacao_Tecnica_2026-10-03.pdf`](docs/LPS_Documentacao_Tecnica_2026-10-03.pdf), gerada em 03/10/2026 a partir do commit `add5acd`.
O arquivo `docs/LPS_Documentacao_Tecnica.pdf` é a versão antiga (29/09/2026) e está desatualizada; em caso de dúvida, vale o texto dos `.md`.
