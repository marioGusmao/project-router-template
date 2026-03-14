# Project Router Template

[English](README.md) | Português (Portugal)

<!-- repository-mode:begin -->
Este repositório é um repositório operacional privado do Project Router for VoiceNotes derivado do upstream partilhado `project-router-template`.

A relação com o upstream fica registada em `private.meta.json` e `template-base.json`, e as atualizações de `marioGusmao/project-router-template` devem entrar por pull requests revistos na branch `chore/template-sync`, não por copy-paste manual.
<!-- repository-mode:end -->

<!-- template-onboarding:begin -->
## Primeiros Passos No Repositório Privado

Se esta cópia já é um repositório operacional privado derivado:

1. Corre `python3 scripts/bootstrap_local.py`.
2. Corre `python3 scripts/project_router.py context`.
3. Revê `Knowledge/local/Roadmap.md` e adapta-o ao teu projeto.
<!-- template-onboarding:end -->

## Modelo Do Repositório

- `project-router-template`: template GitHub partilhável, neutro e reutilizável
- `project-router-private`: repositório privado diário derivado do template, onde podes manter branding, regras próprias e wording mais pessoal

O template é o upstream partilhado. O repositório privado é a casa operacional real.

## Objetivos Principais

- Manter uma cópia local JSON imutável de cada nota capturada.
- Normalizar notas em Markdown com frontmatter estável.
- Classificar de forma conservadora.
- Compilar briefs prontos para projeto antes de qualquer escrita downstream.
- Nunca fazer auto-dispatch.
- Exigir aprovação explícita para valores exatos de `source_note_id`.
- Manter notas ambíguas ou ainda sem destino em filas de revisão.
- Preservar relações de thread entre notas de seguimento.

## Estrutura Do Repositório

```text
data/
  raw/
    voicenotes/
    project_router/
  normalized/
    voicenotes/
    project_router/
  compiled/
    voicenotes/
    project_router/
  review/
    voicenotes/
    project_router/
  dispatched/
  processed/
Knowledge/
  ADR/
  Templates/
project-router/
  inbox/
  outbox/
  conformance/
projects/
  registry.shared.json
  registry.example.json
  registry.local.json
repo-governance/
  ownership.manifest.json
scripts/
  bootstrap_private_repo.py
  bootstrap_local.py
  check_adr_related_links.py
  check_agent_surface_parity.py
  check_knowledge_structure.py
  check_repo_ownership.py
  check_sync_manifest_alignment.py
  project_router.py
  project_router_client.py
src/
  project_router/
    cli.py
    sync_client.py
.agents/skills/
.codex/skills/
.claude/skills/
.github/workflows/
VERSION
CHANGELOG.md
template.meta.json
```

## Knowledge

O diretório `Knowledge/` fornece documentação curada de onboarding, registos de decisões arquiteturais e um glossário. Lê `Knowledge/ContextPack.md` para um guia de navegação pelo código, ou corre `python3 scripts/project_router.py context` para um briefing ao vivo no terminal.

## Configuração Local

Se criaste um repositório privado derivado, promove-o primeiro:

```bash
python3 scripts/bootstrap_private_repo.py
```

O bootstrap de promoção:

- muda `README.md`, `README.pt-PT.md`, `AGENTS.md` e `CLAUDE.md` para postura de repositório privado através de blocos geridos
- cria `private.meta.json` para metadata do repositório privado
- cria `template-base.json` para que `.github/workflows/template-upstream-sync.yml` consiga resolver o upstream template
- mantém inalteradas as regras de segurança e os comandos do pipeline

Vê [docs/private-derived-bootstrap.md](docs/private-derived-bootstrap.md) para o contrato completo desta promoção.

Num computador novo, começa por correr:

```bash
python3 scripts/bootstrap_local.py
```

Comportamento do bootstrap:

- cria `.env.local` a partir de `.env.example` apenas se ainda não existir
- cria `projects/registry.local.json` apenas se ainda não existir, exceto com `--force`
- lê `projects/registry.shared.json` para descobrir as chaves de projeto
- respeita variáveis `VN_ROUTER_ROOT_<PROJECT_KEY>` antes de pedir input
- permite deixar um projeto inativo nessa máquina

Mantém estes ficheiros fora do Git:

- `.env.local`
- `projects/registry.local.json`
- `state/`
- `data/`

## Overlay Do Registry

O registry de routing está dividido em três ficheiros:

- `projects/registry.shared.json`: metadata comitada, keywords, thresholds e note types
- `projects/registry.local.json`: valores locais de `router_root_path` e overrides locais, fora do Git
- `projects/registry.example.json`: template inicial para o overlay local

O template inclui projetos de exemplo neutros, como `home_renovation` e `weekly_meal_prep`. Os `router_root_path` reais existem apenas em `projects/registry.local.json`.

A classificação pode correr apenas com o registry partilhado. O dispatch real exige o overlay local.

## Workflow

```bash
python3 scripts/bootstrap_local.py
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes
python3 scripts/project_router.py normalize --source voicenotes
python3 scripts/project_router.py triage --source voicenotes
python3 scripts/project_router.py compile --source voicenotes
python3 scripts/project_router.py review --source voicenotes
python3 scripts/project_router.py dispatch --dry-run
python3 scripts/project_router.py discover
python3 scripts/project_router.py scan-outboxes
python3 scripts/project_router.py doctor --project home_renovation
```

O dispatch real exige sempre aprovação explícita por nota:

```bash
python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123 --note-id vn_456
```

O comportamento do dispatch é fail-closed:

- sem `projects/registry.local.json`, o dispatch é bloqueado
- sem `router_root_path` para um projeto candidato, esse candidato é saltado com uma razão explícita
- um inbox derivado de `router_root_path` mas inválido bloqueia esse candidato
- packages compilados em falta ou stale bloqueiam esse candidato
- a aprovação tem de nomear exatamente os `source_note_id` a despachar

## Superfícies De Agente

Este template usa um contrato de três camadas:

- Referência: `.agents/skills/`
- Codex: `AGENTS.md` + `.codex/skills/`
- Claude: `CLAUDE.md` + `.claude/skills/`

O modelo pretendido é:

- `.agents/skills/` é a camada de referência neutra e canónica para workflow e regras de segurança
- `.codex/skills/` e `.claude/skills/` adaptam essa referência a cada ferramenta
- notas específicas de plataforma são permitidas, mas o contrato operacional deve manter-se alinhado

O contrato de paridade é executável:

```bash
python3 scripts/check_agent_surface_parity.py
python3 scripts/check_agent_surface_parity.py --pre-publish
```

O validador verifica:

- se os skill IDs obrigatórios existem nas três superfícies
- se todas as superfícies documentam as mesmas regras críticas de segurança
- se todas usam `python3 scripts/project_router_client.py`
- se a documentação partilhada não referencia caminhos internos `.codex/...`

## Governance E Sync

O limite entre template e repositório privado está definido em `repo-governance/ownership.manifest.json`.

Classes de ownership:

- `template_owned`: seguro para updates automáticos do template
- `shared_review`: ficheiros partilhados que devem mudar via PR revisto
- `private_owned`: reservado para personalização de repositórios privados
- `local_only`: nunca deve ser commitado nem sincronizado

Valida as regras com:

```bash
python3 scripts/check_repo_ownership.py
```

Num repositório privado derivado, o sync do template nunca deve tocar em caminhos `private_owned` ou `local_only`.

## Versionamento

O template é versionado com semantic releases:

- `VERSION`
- `CHANGELOG.md`
- `template.meta.json`
- `.github/workflows/template-release.yml`

A automação de release usa Conventional Commits e `release-please`.

## Template Upstream Sync

O template também inclui `.github/workflows/template-upstream-sync.yml` para repositórios derivados.

O contrato de sync é:

- correr semanalmente e permitir execução manual
- comparar o repositório atual com a versão estável mais recente do template
- abrir ou atualizar um draft PR na branch `chore/template-sync`
- nunca fazer auto-merge
- respeitar `repo-governance/ownership.manifest.json`

O workflow espera:

- a variável de repositório `TEMPLATE_UPSTREAM_REPO` ou um `template-base.json` preenchido
- opcionalmente o secret `TEMPLATE_UPSTREAM_TOKEN` quando o template upstream for privado

Num repositório derivado novo, a sequência recomendada é:

```bash
python3 scripts/bootstrap_private_repo.py
python3 scripts/bootstrap_local.py
python3 scripts/refresh_knowledge_local.py
```

## Garantias De Segurança

- Nunca apagar ou sobrescrever o raw JSON canónico.
- Nunca fazer auto-dispatch.
- Tratar a confirmação como específica por `source_note_id`.
- Nunca fazer dispatch direto de uma nota normalizada.
- Os packages compilados têm de estar frescos antes do dispatch.
- A metadata canónica vive em `data/normalized/`; as review queues são apenas views.
- Repetir o pipeline não pode criar duplicados.

## Checklist De Publicação

Antes de publicar o template:

1. Corre `python3 scripts/check_agent_surface_parity.py --pre-publish`
2. Corre `python3 scripts/check_repo_ownership.py`
3. Corre `python3 scripts/check_sync_manifest_alignment.py`
4. Corre `python3 scripts/check_knowledge_structure.py --strict`
5. Corre `python3 scripts/check_adr_related_links.py --mode block`
6. Confirma que `projects/registry.shared.json` só tem exemplos neutros
7. Confirma que `.env.local`, `projects/registry.local.json`, `data/` e `state/` não estão tracked
8. Confirma que `.agents/skills/`, `.codex/skills/` e `.claude/skills/` continuam alinhados
9. Ativa o modo GitHub Template Repository no upstream
10. Ativa branch protection e required checks para testes, parity, ownership e release automation

## Contribuir

Contribuidores externos podem usar os templates públicos de issue e o template de pull request incluídos neste repositório.

Vê [`CONTRIBUTING.md`](CONTRIBUTING.md) para o workflow esperado, comandos de validação e a lista de artefactos locais que nunca devem ser commitados.
