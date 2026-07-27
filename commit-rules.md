# commit-rules.md — GIT GUIDELINES

Regras de versionamento do projeto. Seguir este guia garante histórico limpo, PRs revisáveis e deploys previsíveis.

## Verificação de branch antes de implementar

Verifique a branch atual com `git branch --show-current`. Se estiver em `main`, `staging` ou `develop`, **não comece** — crie uma nova branch:

- Nova funcionalidade → `feat/<nome>`
- Correção de bug → `fix/<nome>`
- Tarefa técnica/infra → `chore/<nome>`
- Refactor → `refactor/<nome>`
- Documentação → `docs/<nome>`
- Correção urgente em produção → `hotfix/<nome>`

## Lint e Testes antes do Commit

> **⚠ Não commite sem rodar lint e testes.** Código quebrado polui o histórico e trava o CI.

Backend:

```bash
make lint && make test
```

Frontend, quando `web/` foi tocado:

```bash
npm --prefix web run typecheck && npm --prefix web test
```

`make format` antes do lint resolve a maior parte do que o ruff aponta.

## Quando fazer um Commit

Após concluir a implementação e rodar lint e testes, sugira commitar. Nunca execute sem autorização.

> **⚠ NUNCA execute `git commit` sem ser solicitado.**

## Quando fazer Push e PR

Após tudo concluído, pode sugerir o push. Nunca execute sem autorização explícita.

> **⚠ NUNCA execute `git push` nem abra PR sem ser solicitado e autorizado.**

## Commits — Conventional Commits

Padrão: `<tipo>(<escopo opcional>): <descrição curta>`

**Tipos:**

| Tipo       | Quando usar                                   |
| ---------- | --------------------------------------------- |
| `feat`     | nova funcionalidade visível ao usuário        |
| `fix`      | correção de bug                               |
| `refactor` | mudança de código sem alterar comportamento   |
| `chore`    | tarefas de manutenção (deps, config, scripts) |
| `docs`     | apenas documentação                           |
| `test`     | adição ou correção de testes                  |
| `perf`     | melhoria de performance                       |
| `ci`       | mudanças em pipelines de CI/CD                |

**Regras:**

- Inglês, imperativo, sem ponto final: `add`, `fix`, `remove` — não `added`, `fixes`
- Máximo 72 caracteres na primeira linha
- Escopo identifica o módulo: `feat(auth):`, `fix(users):` ou apenas `feat:`
- Breaking changes: `feat(api)!:` com detalhes no corpo do commit

**Exemplos:**

```
feat(auth): add JWT refresh token rotation
fix(users): prevent duplicate email on signup
refactor(feed): extract pagination logic to helper
chore: update drizzle-orm to v0.30
```

Breaking change com corpo:

```
feat(payments)!: replace Stripe with Adyen

BREAKING CHANGE: PaymentIntent shape changed — see migration guide
```

## Branches

Inspirado no Git Flow, com nomenclatura curta:

```
main        ← produção (sempre estável)
develop     ← integração das features
└── feat/<descricao>
└── fix/<descricao>
└── chore/<descricao>
└── refactor/<descricao>
└── docs/<descricao>
└── hotfix/<descricao>    ← urgente, direto de main
```

Nomenclatura: `kebab-case`, curta e descritiva — `feat/user-avatar`, `fix/signup-validation`.

**Ciclo:**

1. Crie a branch a partir de `develop` (ou `main` para hotfix)
2. Commits atômicos — um assunto por commit, sempre após lint e testes verdes
3. Abra PR para `develop` ao concluir

## Regras técnicas de Push

- **Nunca force-push em `main` ou `develop`**
- Force-push em branches pessoais é permitido após rebase — use `--force-with-lease`
- Prefira rebase a merge para manter histórico linear: `git rebase develop`
- Faça push só ao concluir — evita rebase em branch que já está na origin

## Pull Requests

> **Tamanho e Revisão abaixo são propostas, não política acordada.** O time precisa confirmá-las ou substituí-las.

### Tamanho

Proposta: idealmente menos de 400 linhas de diff, excluindo lockfiles e arquivos gerados. PR maior deve dizer na descrição por que não foi fatiado.

### Revisão

Proposta: mínimo 1 aprovação. Dois casos pedem uma segunda: mudança no prompt do agente (`instructions.md`) ou nas descrições das tools, porque o efeito não aparece em teste automatizado; e mudança no contrato do stream SSE, porque quebra o destaque no viewer sem erro visível.

### CI

**Ainda não há CI configurado** — este repositório não tem `.github/workflows/` nem remoto. Enquanto isso, os checks são responsabilidade de quem abre o PR:

- `make lint` e `make test`
- `npm --prefix web run typecheck` e `npm --prefix web test`, se `web/` foi tocado

### Descrição

O que foi feito, por que, e como verificar. Para mudança que afete o desenho renderizado ou o comportamento do assistente, inclua a pergunta usada no teste manual e o que o viewer fez em resposta — o valor do produto está nessa ligação, e ela não aparece num diff.

## O que NÃO Fazer

- **Não execute `git commit` ou `git push` sem autorização explícita** — nem mesmo em sessões onde já houve autorização anterior
- **Não commite diretamente em `main`, `staging` ou `develop`** — sempre via PR
- **Não misture assuntos no mesmo commit** — um commit, uma responsabilidade
- **Não use mensagens vagas** — `fix bug`, `update`, `WIP` não são aceitáveis
- **Não force-push em branches compartilhadas** — prefira `--force-with-lease` em branches pessoais
- **Não adicione co-autoria nos commits** — nunca inclua linhas `Co-Authored-By:` em nenhuma mensagem de commit
