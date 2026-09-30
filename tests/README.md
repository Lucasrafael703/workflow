# Testes do checklist

Backend (a partir da pasta `workflow`):

```powershell
.venv/Scripts/python.exe manage.py test activities.test_views.TaskChecklistViewTests
```

Componente JavaScript, usando Node.js 18+ e jsdom em uma pasta temporária,
sem adicionar dependências de execução ao Django:

```powershell
$checklistDeps = Join-Path $env:TEMP 'lps-checklist-test-deps'
npm install --prefix $checklistDeps --no-save --package-lock=false --ignore-scripts jsdom@26.1.0
$env:NODE_PATH = Join-Path $checklistDeps 'node_modules'
node --test tests/checklist.test.cjs
```

Os testes renderizam o template Django real e exercitam eventos de formulário,
requisições, permissões visuais e preservação do DOM. Use `PYTHON` para informar
outro interpretador se o ambiente virtual não estiver em `.venv`.

Assistente "Aplicar processo" (`static/js/process-apply.js`), com as mesmas
dependências; renderiza o template real `activities/activity_process_apply.html`
com objetos de mentira, sem banco:

```powershell
$env:NODE_PATH = Join-Path $env:TEMP 'lps-checklist-test-deps\node_modules'
node --test tests/process-apply.test.cjs
```

Popup "Já realizei este trabalho" (`static/js/retroactive-work.js`), também com o
template real e o `RetroactiveWorkForm` real (sem banco):

```powershell
node --test tests/retroactive-work.test.cjs
```

O jsdom não valida layout nem o envio implícito por Enter do navegador. Conferir
também no navegador: botão Adicionar e Enter, página e painel lateral, largura
de celular e desktop, quebra de textos longos e foco por teclado.

## Editor e janelas de atividades

```powershell
.venv/Scripts/python.exe manage.py test activities.test_activity_workspace
node --test tests/modal.test.cjs tests/activity-workspace.test.cjs
```

Os testes JavaScript usam o mesmo jsdom e NODE_PATH descritos acima. Cobrem
validação, envio duplicado, erros de rede e preservação do formulário anterior.
Os testes Django cobrem rascunhos, publicação, permissões, anexos, auditoria,
fuso horário e retorno à visualização de origem.
