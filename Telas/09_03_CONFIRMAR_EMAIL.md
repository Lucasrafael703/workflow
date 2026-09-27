# Tela — Confirmar E-mail

## 1. Objetivo

Confirmar que o e-mail informado na criação da conta pertence à pessoa que está realizando o cadastro.

Esta etapa acontece após:

```text
Criar Conta
↓
Confirmar E-mail
```

Após a confirmação:

```text
Confirmar E-mail
↓
Criar ou entrar em uma Organização
```

---

## 2. Princípio da tela

A confirmação deve ser simples, rápida e sem distrações.

A pessoa precisa entender imediatamente:

1. para qual e-mail o código foi enviado;
2. onde informar o código;
3. como confirmar;
4. como solicitar um novo código;
5. como corrigir o e-mail informado.

---

## 3. Layout

Manter o mesmo padrão visual das telas:

- Login;
- Criar Conta.

### Lado esquerdo

Área institucional da LPS.

Manter:

- identidade visual oficial;
- cores oficiais;
- tipografia Inter;
- padrão gráfico utilizado nas telas anteriores.

### Lado direito

Card branco contendo o fluxo de confirmação do e-mail.

---

## 4. Logo

Utilizar o logotipo oficial da LPS.

Assinatura:

```text
LPS
O amigo do gestor.
```

Respeitar:

- proporções;
- cores oficiais;
- área de proteção;
- tamanho mínimo;
- versões autorizadas da marca.

Não reconstruir o logotipo utilizando texto comum.

---

## 5. Título

```text
Confirme seu e-mail
```

### Texto auxiliar

```text
Enviamos um código de confirmação para:
pa***@empresa.com.br
```

O e-mail deve aparecer parcialmente oculto.

---

## 6. Código de confirmação

Utilizar código numérico de 6 dígitos.

Exemplo:

```text
[ 2 ] [ 8 ] [ 4 ] [ 1 ] [ 7 ] [ 3 ]
```

Comportamento esperado:

- aceitar somente números;
- avançar automaticamente para o próximo campo;
- permitir voltar com Backspace;
- permitir colar o código completo;
- permitir confirmar com Enter após preenchimento.

---

## 7. Botão principal

```text
Confirmar e-mail
```

Ao clicar:

1. validar se os 6 dígitos foram informados;
2. validar o código;
3. confirmar o e-mail;
4. registrar a confirmação;
5. direcionar para a próxima etapa.

---

## 8. Código correto

Após confirmação válida:

```text
E-mail confirmado com sucesso.
```

Em seguida:

```text
→ Criar ou entrar em uma Organização
```

---

## 9. Código incorreto

Mensagem:

```text
Código inválido. Confira e tente novamente.
```

A pessoa permanece na mesma tela.

---

## 10. Código expirado

Mensagem:

```text
Este código expirou.
Solicite um novo código para continuar.
```

Ação disponível:

```text
Reenviar código
```

---

## 11. Reenviar código

Texto:

```text
Não recebeu o código?
Reenviar
```

Ao solicitar novo código:

1. gerar um novo código;
2. enviar para o mesmo e-mail;
3. invalidar o código anterior;
4. informar que o novo código foi enviado.

Mensagem:

```text
Novo código enviado.
```

Deve existir um pequeno intervalo antes de permitir um novo reenvio consecutivo.

---

## 12. Alterar e-mail

Ação:

```text
E-mail errado?
Alterar e-mail
```

Ao clicar:

- permitir corrigir o e-mail;
- preservar os demais dados da conta;
- validar o novo endereço;
- enviar um novo código;
- invalidar o código anterior.

A pessoa não deve precisar recriar toda a conta.

---

## 13. Segurança

A confirmação de e-mail deve possuir proteção contra tentativas excessivas.

Regras:

- código possui validade limitada;
- novo código invalida o anterior;
- limitar tentativas consecutivas;
- limitar reenvios consecutivos;
- não exibir o código em logs ou mensagens da interface;
- registrar data e hora da confirmação.

O tempo exato de validade e os limites de tentativa devem ser parâmetros técnicos configuráveis.

---

## 14. Comportamento

- manter foco automático no primeiro campo vazio;
- funcionar corretamente com teclado;
- permitir colar o código completo;
- Enter confirma após preenchimento;
- evitar múltiplos cliques no botão;
- mostrar estado de carregamento durante validação;
- funcionar em desktop e mobile.

---

## 15. Mobile

No celular:

- manter o card em tela inteira ou largura adaptada;
- abrir teclado numérico;
- manter os seis campos legíveis;
- evitar rolagem desnecessária;
- manter ações de reenviar e alterar e-mail visíveis.

---

## 16. O que não pertence a esta tela

Não solicitar:

- organização;
- empresa;
- setor;
- usuário da organização;
- perfil;
- permissões;
- plano;
- pagamento;
- dados de cobrança.

Esta tela existe apenas para confirmar o e-mail da conta.

---

## 17. Fluxo principal

```text
Criar Conta
↓
LPS envia código
↓
Confirmar E-mail
↓
Informar código de 6 dígitos
↓
Código válido?
├── NÃO → mostrar erro
└── SIM
    ↓
E-mail confirmado
↓
Criar ou entrar em uma Organização
```

---

## 18. Critérios de aceite

- código é enviado ao e-mail cadastrado;
- e-mail aparece parcialmente oculto;
- código possui 6 dígitos;
- código correto confirma o e-mail;
- código incorreto não confirma;
- código expirado não confirma;
- usuário consegue solicitar novo código;
- novo código invalida o anterior;
- usuário consegue alterar o e-mail;
- dados da conta são preservados ao alterar o e-mail;
- confirmação funciona em desktop e mobile;
- após confirmar, a pessoa segue para a etapa de Organização.

---

## 19. Próxima tela

Após confirmação:

```text
→ Criar ou entrar em uma Organização
```
