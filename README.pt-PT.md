# Project Router Template

[English](README.md) | Português (Portugal)

Project Router Template é o template base partilhável para um fluxo de triagem de VoiceNotes que funciona tanto com Codex como com Claude Code.

O template mantém no Git o pipeline comum, as regras de segurança, as ferramentas de validação e exemplos neutros de routing. Cada utilizador guarda fora do Git os seus segredos locais, caminhos locais e dados reais de notas. Depois disso, cada pessoa pode criar o seu próprio repositório privado derivado deste template e personalizá-lo.

## Novo No GitHub Templates

Um template repository do GitHub é um projeto base que podes copiar para criares o teu próprio repositório.

Neste projeto, o template serve para te dar:

- o workflow e os scripts de VoiceNotes
- as regras de segurança e os checks de validação
- exemplos neutros de routing
- um ponto de partida público e limpo, sem notas privadas, tokens ou caminhos locais

Usa um template quando queres a tua própria cópia do projeto para a personalizares com segurança.

Neste caso, a configuração recomendada é:

1. Abre este repositório no GitHub.
2. Clica em `Use this template`.
3. Escolhe `Create a new repository`.
4. Cria o teu próprio repositório a partir deste template.
5. Define o teu novo repositório como `Private`, a menos que queiras mesmo partilhar a tua versão derivada.
6. Faz clone do teu novo repositório para a tua máquina.
7. Corre `python3 scripts/bootstrap_local.py` na tua cópia.

Diferenças importantes em relação a um fork:

- um template dá-te um repositório novo e limpo
- o teu repositório pode ser privado mesmo que este template seja público
- os teus ficheiros locais `.env.local`, `data/` e `state/` ficam só na tua máquina

Se só queres usar o workflow, cria um repositório a partir do template. Não precisas de contribuir de volta para este repositório upstream.

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
  normalized/
  compiled/
  review/
    ambiguous/
    needs_review/
    pending_project/
  dispatched/
  processed/
projects/
  registry.shared.json
  registry.example.json
  registry.local.json
repo-governance/
  ownership.manifest.json
scripts/
  bootstrap_local.py
  check_agent_surface_parity.py
  check_repo_ownership.py
  voice_notes.py
  voicenotes_client.py
src/
  voice_notes/
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

## Configuração Local

Num computador novo, começa por correr:

```bash
python3 scripts/bootstrap_local.py
```

Comportamento do bootstrap:

- cria `.env.local` a partir de `.env.example` apenas se ainda não existir
- cria `projects/registry.local.json` apenas se ainda não existir, exceto com `--force`
- lê `projects/registry.shared.json` para descobrir as chaves de projeto
- respeita variáveis `VN_INBOX_<PROJECT_KEY>` antes de pedir input
- permite deixar um projeto inativo nessa máquina

Mantém estes ficheiros fora do Git:

- `.env.local`
- `projects/registry.local.json`
- `state/`
- `data/`

## Overlay Do Registry

O registry de routing está dividido em três ficheiros:

- `projects/registry.shared.json`: metadata comitada, keywords, thresholds e note types
- `projects/registry.local.json`: caminhos locais de inbox e overrides locais, fora do Git
- `projects/registry.example.json`: template inicial para o overlay local

O template inclui projetos de exemplo neutros, como `home_renovation` e `weekly_meal_prep`. Os caminhos reais de inbox existem apenas em `projects/registry.local.json`.

A classificação pode correr apenas com o registry partilhado. O dispatch real exige o overlay local.

## Workflow

```bash
python3 scripts/bootstrap_local.py
python3 scripts/voicenotes_client.py sync --output-dir ./data/raw
python3 scripts/voice_notes.py normalize
python3 scripts/voice_notes.py triage
python3 scripts/voice_notes.py compile
python3 scripts/voice_notes.py review
python3 scripts/voice_notes.py dispatch --dry-run
python3 scripts/voice_notes.py discover
```

O dispatch real exige sempre aprovação explícita por nota:

```bash
python3 scripts/voice_notes.py dispatch --confirm-user-approval --note-id vn_123 --note-id vn_456
```

O comportamento do dispatch é fail-closed:

- sem `projects/registry.local.json`, o dispatch é bloqueado
- sem `inbox_path` para um projeto candidato, esse candidato é saltado com uma razão explícita
- um `inbox_path` local inválido bloqueia esse candidato
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
- se todas usam `python3 scripts/voicenotes_client.py`
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
3. Confirma que `projects/registry.shared.json` só tem exemplos neutros
4. Confirma que `.env.local`, `projects/registry.local.json`, `data/` e `state/` não estão tracked
5. Confirma que `.agents/skills/`, `.codex/skills/` e `.claude/skills/` continuam alinhados
6. Ativa o modo GitHub Template Repository no upstream
7. Ativa branch protection e required checks para testes, parity, ownership e release automation

## Contribuir

Contribuidores externos podem usar os templates públicos de issue e o template de pull request incluídos neste repositório.

Vê [`CONTRIBUTING.md`](CONTRIBUTING.md) para o workflow esperado, comandos de validação e a lista de artefactos locais que nunca devem ser commitados.
