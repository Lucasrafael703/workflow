# Revisão da documentação LPS — Processos e Navegação

Data: 15/09/2026

## Documentos revisados

- `00_INDICE_LPS.md`
- `01_VISAO_E_PRINCIPIOS_LPS.md`
- `02_ATIVIDADES_TAREFAS_E_FLUXOS.md`
- `04_AUDITORIA_TEMPO_E_METRICAS.md`
- `05_USUARIOS_SETORES_E_AUTORIZACOES.md`
- `07_INTELIGENCIA_E_RETROALIMENTACAO.md`
- `08_BANCO_DE_DADOS.md`
- `09_TELAS_E_EXPERIENCIA_DO_USUARIO.md`
- `10_ROADMAP_D0_D1_D2.md`
- `MODELO_DE_CONSTRUCAO_LPS.md`

## Documento novo

- `11_PROCESSOS_INPUTS_OUTPUTS_E_CRITERIOS_DE_ACEITE.md`

## Mantidos sem alteração funcional nesta revisão

- `03_FILAS_PRAZOS_E_ESCALONAMENTO.md`
- `06_NOTIFICACOES_E_COMUNICACAO.md`

## Decisões principais consolidadas

1. Processo passa a ser conceito de primeira classe da LPS.
2. Processo = Input → Execução → Output → Critérios de aceite.
3. Processo não é atividade; atividade é uma execução real.
4. Tipo de atividade é classificação, não processo.
5. Processo é opcional no D0 para preservar atividades rápidas e ad hoc.
6. Processo publicado é versionado e imutável.
7. Atividade guarda a versão exata aplicada.
8. Fluxo padrão pertence ao processo e gera tarefas reais.
9. `Cadastros > Processos` é a localização da tela.
10. Novo/editar processo usa modal grande com rolagem interna, cabeçalho e rodapé fixos.
11. Evitar modal sobre modal.
12. Cadastros, Perfis e permissões e Configurações recebem submenus; Home permanece sem submenu.
13. No D0, processo pertence a uma empresa para evitar inconsistência entre fluxo e setores.
