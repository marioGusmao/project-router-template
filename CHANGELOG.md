# Changelog

All notable changes to the shared Project Router starter will be documented in this file.

## Unreleased

- Fixed template sync coverage drift by syncing `requirements-extractors.txt`, making README managed-block files explicit in the workflow, and failing governance when tracked synced files are not covered by workflow paths.
- Renamed `VERSION` → `version.txt` so release-please `simple` type recognizes the file extension; updated all CI, governance, and documentation references.
- Removed `VERSION` from `extra-files` in `.release-please-config.json` (now the primary version file for `simple` type).
- Fixed `Knowledge/TLDR.md` to use neutral repo-mode phrasing and include the filesystem pipeline.
- Added deprecation note to design spec section 6 (upstream sync) documenting implementation drift.
- Added `template-base.json` and `private.meta.json` to README layout blocks (both languages).
- Realigned Codex `session-flow.md` with canonical skill: 8-step opener, filesystem pipeline, `pending_project` field name, `dispatch --dry-run` moved out of opener.
- Removed unused `import subprocess` from `cli.py`.
- Fixed template sync diff-only handling so review output lives outside the repo and is rendered in the sync PR body.
- Tightened contract validation with conflict-marker detection, reject-file detection, and release-note enforcement for upgrade-governance surfaces.
- Added regression tests for template sync governance tooling.
- Added filesystem source with ingestion protocol, modular extractors, and AI extraction workflow.
- Added router inbox consumption commands: `inbox-intake`, `inbox-status`, `inbox-ack`.
- Hardened dispatch with pre-validation of `--note-id`, ISO timestamps, and atomic batch rejection.
- Preserved manual review decisions (reject/approved) across triage reruns.
- Added tracked-file coverage gate to `check_customization_contracts.py`.
- Registered `Knowledge/runbooks/**` as local-only in ownership manifest and customization contracts.
- Gitignored `Knowledge/runbooks/plans/` as operational artifacts.

## [0.7.0](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.6.0...project-router-template-v0.7.0) (2026-03-20)


### Features

* add --dashboard flag to triage and review CLI commands ([618b2a2](https://github.com/marioGusmao/project-router-template/commit/618b2a26e54153c03552e618570f5bad739c4a24))
* add --exclude-category filter to Readwise sync client ([bd5de8c](https://github.com/marioGusmao/project-router-template/commit/bd5de8ce9cacce6c7c8c10451546929500820f84))
* add batch selection and command palette (Cmd+K) ([9023089](https://github.com/marioGusmao/project-router-template/commit/9023089d7a7be615dea288b7910ec24c0153e605))
* add dashboard backend — HTTP server + SQLite index ([d04218e](https://github.com/marioGusmao/project-router-template/commit/d04218ee136379f49da4db1f5309023066c09e16))
* add dashboard frontend — React + Tailwind dark mode UI ([d56e354](https://github.com/marioGusmao/project-router-template/commit/d56e3541009ce1f31aaab89181d515d607cea0d4))
* add dashboard suggestion fields to note frontmatter ([486adae](https://github.com/marioGusmao/project-router-template/commit/486adae6fece37a944c3e1574affb485211f2561))
* add decide actions (approve/reject/ambiguous) to dashboard ([d7066f6](https://github.com/marioGusmao/project-router-template/commit/d7066f62e26c9772130dd55bd9d97842e47f8fbd))
* add defer (rever mais tarde) decision to CLI and dashboard ([3d41490](https://github.com/marioGusmao/project-router-template/commit/3d41490bf1fee94a8350ba371b9bfa949ad78aec))
* add keyboard shortcuts, help overlay, and fix MainLayout wiring ([1e7e34f](https://github.com/marioGusmao/project-router-template/commit/1e7e34fdd1e8bb18a4f355f4f7d8297e0b19a242))
* add note detail split panel with project suggestion ([6ae9d04](https://github.com/marioGusmao/project-router-template/commit/6ae9d045faee81565a2970c513f9fd85ce64c3e2))
* add Readwise icon to source icons in notes list ([2355e24](https://github.com/marioGusmao/project-router-template/commit/2355e24a68a02dbac256d7547df8d3057d83e86f))
* add Readwise Reader normalizer with full metadata mapping ([8f0ce30](https://github.com/marioGusmao/project-router-template/commit/8f0ce30c9599edc106e673e3c1915eec800ac643))
* add Readwise Reader sync client with incremental fetch ([691e43c](https://github.com/marioGusmao/project-router-template/commit/691e43cc042be621aaf26fa9cb04c48cec9d82cb))
* add Rejected/Deferred sidebar views and auto-refresh on decide ([9c64bae](https://github.com/marioGusmao/project-router-template/commit/9c64baeccdf6d5cc8671d24a0489430f4cfceb16))
* add reviewer_notes to apply_note_annotations ([d59d253](https://github.com/marioGusmao/project-router-template/commit/d59d253c6fb371631d7ad96e51dfddfaabf07f0e))
* add source icon before note title in notes list ([2605efb](https://github.com/marioGusmao/project-router-template/commit/2605efb5a8cc660fbe73258152221b8fa2b53795))
* add source icons to dashboard home and triage pages ([b460ebd](https://github.com/marioGusmao/project-router-template/commit/b460ebd28e61fee7b07df03df4f8e9acf337489c))
* add suggestions service for dashboard write operations ([bb3f74a](https://github.com/marioGusmao/project-router-template/commit/bb3f74a092a0e738d00abe6d54c7e4669b668c06))
* add template update status checks ([89f2901](https://github.com/marioGusmao/project-router-template/commit/89f29015e029658cb8d718720895b8454dc70b1e))
* add undo snackbar and color-coded stale indicator ([bb04ead](https://github.com/marioGusmao/project-router-template/commit/bb04ead5ef77bab64ab9e87a33d3c6a9f50ab88b))
* blink-then-fade animation when note is decided ([5757b26](https://github.com/marioGusmao/project-router-template/commit/5757b26fa39b76326fd576074c85d9335b6a5d4b))
* clear suggestion fields on decide approve ([1f44bb5](https://github.com/marioGusmao/project-router-template/commit/1f44bb5d60def8d8778d260852ecfb3752133f50))
* dashboard UX improvements — keyboard shortcuts, sort, batch, annotate ([75c5dd8](https://github.com/marioGusmao/project-router-template/commit/75c5dd8694eecfb4b65b2e5a34c200d6d71cd474))
* **dashboard:** premium "Luxury Terminal" redesign ([4860d9d](https://github.com/marioGusmao/project-router-template/commit/4860d9d91bd539022a4860f2acec4cf5e0e53493))
* **dashboard:** redesign frontend with modern dark theme ([c2a4940](https://github.com/marioGusmao/project-router-template/commit/c2a49405b1b2c5031ec224eaeede6c62ecc94f46))
* enhance project detail tabs and file preview in note detail ([0fd4ea2](https://github.com/marioGusmao/project-router-template/commit/0fd4ea2f3727fa3915695c961bb3c24db6449af8))
* include suggestion fields in review command output ([3df3144](https://github.com/marioGusmao/project-router-template/commit/3df31446457a8a104fd81c80b60fb7c8173c80be))
* premium "Luxury Terminal" dashboard redesign ([ebd666c](https://github.com/marioGusmao/project-router-template/commit/ebd666c377261b3ade5e30f7f5f05d1da279fc67))
* use real VoiceNotes icon in notes list ([24384fc](https://github.com/marioGusmao/project-router-template/commit/24384fcbf591480160736f610e39ce0d5550d425))
* wire readwise source through pipeline infrastructure ([93595c9](https://github.com/marioGusmao/project-router-template/commit/93595c92cdfc712d37a1c2bbf01da7481f651f21))


### Bug Fixes

* force dark theme on native select/option dropdown elements ([a2a6f51](https://github.com/marioGusmao/project-router-template/commit/a2a6f5119a01d666ef33121d9e82bba3a5b0c87e))
* harden dashboard identity and ship frontend build ([33b5355](https://github.com/marioGusmao/project-router-template/commit/33b53557897a6cfc852037e2db2c257a13122393))
* harden dashboard identity and ship frontend build ([ca42d84](https://github.com/marioGusmao/project-router-template/commit/ca42d84087971161976ee4347f190a277d7d3202))
* propagate --notes CLI arg to reviewer_notes metadata ([be67233](https://github.com/marioGusmao/project-router-template/commit/be67233e4763e4441c7c248696414fe16c31f303))
* reconcile template sync metadata state ([f26fbc9](https://github.com/marioGusmao/project-router-template/commit/f26fbc92872cf944cad64a51d9f3297f10d46b4d))
* remove_review_copies also cleans legacy flat review directories ([0376a29](https://github.com/marioGusmao/project-router-template/commit/0376a292c90a04c20f438fde7d678f44fab1aca2))
* require explicit sync bootstrap scope ([24680b6](https://github.com/marioGusmao/project-router-template/commit/24680b6f434a66abcc6cc6eaf2d0eb4cfccc19ac))
* resolve dashboard frontend bugs — identity, types, pagination, lint ([538d6a1](https://github.com/marioGusmao/project-router-template/commit/538d6a1f40635adb86ee3e077acd972a94d81b7d))
* resolve horizontal overflow on Notes and Triage pages ([75d3f0a](https://github.com/marioGusmao/project-router-template/commit/75d3f0a2eb7f0c5fa573aa558805418b8fb01629))
* sanitize ISO timestamps for Readwise API and isolate token tests ([b72dd1e](https://github.com/marioGusmao/project-router-template/commit/b72dd1eadfcede5df220773b1e5399f5752f0ec1))
* serve dashboard attachments safely ([dc7dfa8](https://github.com/marioGusmao/project-router-template/commit/dc7dfa8e990854b1014e66f6e1306c53f309fe7c))
* unwrap note response in getNote API call ([fd18d41](https://github.com/marioGusmao/project-router-template/commit/fd18d414b6eab8a8989add433e49c9b7066a47fa))
* use fixed 480px width for detail panel instead of 40% ([a77ca04](https://github.com/marioGusmao/project-router-template/commit/a77ca048b07f8f233168a368720c1e331c3efe60))
* use fixed-position detail panel to prevent right-side clipping ([64ae435](https://github.com/marioGusmao/project-router-template/commit/64ae435efdeaabe752099d7fc24a7fff3e778085))
* use inline style for sidebar margin (Tailwind v4 arbitrary value fix) ([eefee8e](https://github.com/marioGusmao/project-router-template/commit/eefee8ecfd48b9513a91de9fb72ec0c492fe59e7))

## [0.6.0](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.5.1...project-router-template-v0.6.0) (2026-03-18)


### Features

* add downstream inbox guardrails ([a00e6ff](https://github.com/marioGusmao/project-router-template/commit/a00e6ff85ef72422b04101fe11cfdbbaa471800e))
* add multilingual parser profiles ([b0ef5ad](https://github.com/marioGusmao/project-router-template/commit/b0ef5ad2567a5bcb91e71fd325443b85420b5e60))


### Bug Fixes

* align template sync manifest governance ([20afd97](https://github.com/marioGusmao/project-router-template/commit/20afd97940736a8f4c0f9a7ae1fc4a38cbc424a3))
* tighten parser capture-kind terms ([08f42fb](https://github.com/marioGusmao/project-router-template/commit/08f42fb8de39ee436a60bcaa6017302bea879cab))

## [0.5.1](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.5.0...project-router-template-v0.5.1) (2026-03-18)


### Bug Fixes

* restore CI for release-please PRs ([#9](https://github.com/marioGusmao/project-router-template/issues/9)) ([7a7704e](https://github.com/marioGusmao/project-router-template/commit/7a7704e62df698ab52c3f4468d2fa1dd1dab5e4a))

## [0.5.0](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.4.0...project-router-template-v0.5.0) (2026-03-18)


### Features

* add filesystem source with ingestion protocol and modular extractors ([824a885](https://github.com/marioGusmao/project-router-template/commit/824a885e005672695b1e60323bdb4633515e303e))
* add filesystem source, inbox consumption, and dispatch hardening ([c2a362e](https://github.com/marioGusmao/project-router-template/commit/c2a362eb132475df9e89a6c739e0b91df13c63f4))
* add router inbox consumption with inbox-intake, inbox-status, inbox-ack ([30f65c5](https://github.com/marioGusmao/project-router-template/commit/30f65c5f00b1f2db78d6d83d9e4df80b4cf3b1ad))
* dispatch original blob alongside compiled brief for filesystem notes ([3308d47](https://github.com/marioGusmao/project-router-template/commit/3308d470fd28276105629b98a6366e3064e6bad6))
* enforce supported_packet_types in outbox validation and doctor ([bf45962](https://github.com/marioGusmao/project-router-template/commit/bf45962f8ce12fba9d55b6735502e10ea8ad0b7f))
* harden dispatch validation, gitignore plans, add tracked-file coverage gate ([daab033](https://github.com/marioGusmao/project-router-template/commit/daab0333e26a3cd4361254960c9a4aaa9106b1d4))


### Bug Fixes

* add error handling to read_registry_config ([6ccb521](https://github.com/marioGusmao/project-router-template/commit/6ccb52193619b6f9f22f1e362f43da82797b8901))
* address Codex review — ack default types, scan reconciliation ([2f18557](https://github.com/marioGusmao/project-router-template/commit/2f1855788c2fb5160e42ae0d5a94584d42dbaac0))
* address review findings — crash recovery, error handling, test gaps ([a731a5a](https://github.com/marioGusmao/project-router-template/commit/a731a5a0dca9bbd82c71bd98ae8bfdcea2bb2452))
* document intentional broad except in ingest, warn on manifest corruption ([425794e](https://github.com/marioGusmao/project-router-template/commit/425794e08ec96a71ec8ce60534f3ef405cc778b4))
* guard blob dispatch against path traversal in blob_ref and inbox_key ([e956c29](https://github.com/marioGusmao/project-router-template/commit/e956c299ae688b8ac05d581364f9092795b07b47))
* guard frontmatter parser against colon-free lines ([eb469a8](https://github.com/marioGusmao/project-router-template/commit/eb469a8edeeb2411d0ed656dca3294f6309b347d))
* harden inbox commands — non-zero exit on error, warn on corrupt state/contract ([442e5cf](https://github.com/marioGusmao/project-router-template/commit/442e5cf05a4f9593f33254ea2d4322ea65a6da9f))
* preserve extraction fields across re-normalization ([3a62185](https://github.com/marioGusmao/project-router-template/commit/3a621850c610eb3b9f231af80b7687ac9d415fdb))
* preserve manual review decisions (reject/approved) across triage reruns ([ce0cd7b](https://github.com/marioGusmao/project-router-template/commit/ce0cd7b479797f225c12ba71420c035033769161))
* remove dead --source argument from extract subcommand ([ef31003](https://github.com/marioGusmao/project-router-template/commit/ef310039ee1f90373f30c935c9e754f636751c47))
* remove stale extract --source, thread packet types in doctor, use relative compiled paths ([cd452d7](https://github.com/marioGusmao/project-router-template/commit/cd452d741f90b77a22aa6518b18c12079c6fa06a))
* resolve 6 documentation and config inconsistencies from project audit ([f08a5bf](https://github.com/marioGusmao/project-router-template/commit/f08a5bf03a8db47c65415a5d33daf6b6afef930e))
* return non-zero exit code from ingest_command on errors ([06ac9cf](https://github.com/marioGusmao/project-router-template/commit/06ac9cff9fbf0de1eedb37d79544f40036979140))
* save inbox state after ack write to prevent stuck terminal packets ([b77688e](https://github.com/marioGusmao/project-router-template/commit/b77688effc0756dadd4693068420cac1ee0585d8))
* warn on corrupt ingest state instead of silent None ([62dd7b6](https://github.com/marioGusmao/project-router-template/commit/62dd7b61b5cc64231331512f98aeddd6e53f92ec))

## [0.4.0](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.3.0...project-router-template-v0.4.0) (2026-03-16)


### Features

* add init-router-root and adopt-router-root commands ([#5](https://github.com/marioGusmao/project-router-template/issues/5)) ([cf92547](https://github.com/marioGusmao/project-router-template/commit/cf9254797e9c369cb1c69acf51c9a2c75aeaa1ea))

## [0.3.0](https://github.com/marioGusmao/project-router-template/compare/project-router-template-v0.2.0...project-router-template-v0.3.0) (2026-03-16)


### Features

* add knowledge foundation with ADRs, context command, and validator ([52080e4](https://github.com/marioGusmao/project-router-template/commit/52080e443d62aa4da8d9b8b017976628263c7436))
* add private repo promotion bootstrap ([0597c0f](https://github.com/marioGusmao/project-router-template/commit/0597c0f80c69bbeddeb07d241835f2b699f7c627))
* add source-aware router protocol ([a0835ab](https://github.com/marioGusmao/project-router-template/commit/a0835abce7e424c8fd1d5b40cbb0251b9074aa29))
* implement template upgrade safety — overlay model, surface-aware sync, and contract registry ([12a6f91](https://github.com/marioGusmao/project-router-template/commit/12a6f913781dd5dfee4804db64b788c89ca1539e))
* initialize voicenotes template ([87ca623](https://github.com/marioGusmao/project-router-template/commit/87ca623d183b7e6b64d4a3e6322923f3583faa21))
* template upgrade safety — overlay model, surface-aware sync, and contract registry ([ac7d423](https://github.com/marioGusmao/project-router-template/commit/ac7d4239718d38cfa8b4e33eae14f8b0ac452603))


### Bug Fixes

* add frontmatter to shared skill docs ([42b3745](https://github.com/marioGusmao/project-router-template/commit/42b37452043da055c9a84d1d9cd0645d29b5299d))
* add PID-based scan lock stale detection and bootstrap pre-validation ([442c058](https://github.com/marioGusmao/project-router-template/commit/442c05852b77a80ddc1d825153ed40e80c57a697))
* address review findings — path migration gap, lock robustness, test assertions ([6612e96](https://github.com/marioGusmao/project-router-template/commit/6612e96041a8ef7e56a32745d622a853c6d5d1b8))
* align context review counts ([8260672](https://github.com/marioGusmao/project-router-template/commit/8260672a42e7599a15ae6e4e2265d1f84580376c))
* align documentation, harden re.sub, and complete surface coverage ([da552fa](https://github.com/marioGusmao/project-router-template/commit/da552fabd30eeb1774cd7f9b8006efd80f786c3b))
* align status and context observability ([baf7337](https://github.com/marioGusmao/project-router-template/commit/baf73374cc462f4e7b2693831ed9c7fd2275c427))
* CI — install pytest and materialize scaffold before strict check ([be86fb8](https://github.com/marioGusmao/project-router-template/commit/be86fb80f6aeaddfaac7656a40a945ddbe2f695e))
* CI — install pytest and materialize scaffold before strict check ([6389bae](https://github.com/marioGusmao/project-router-template/commit/6389baedcdb65d29f01e918334b2286b31626a0f))
* close template sync governance gaps ([473399c](https://github.com/marioGusmao/project-router-template/commit/473399cac854d2088e5d02152e7b33917facbb6c))
* context command docstring extraction, safety invariants, and source filter ([f30bda9](https://github.com/marioGusmao/project-router-template/commit/f30bda9a45fc264dd42df06a95d90ed265082da2))
* harden ADR governance follow-up ([b6e1481](https://github.com/marioGusmao/project-router-template/commit/b6e1481b50f94c010ba2c867b7500db9098ed950))
* harden dispatch safety, frontmatter parsing, and doc alignment ([1e2ea23](https://github.com/marioGusmao/project-router-template/commit/1e2ea237d629418ffbaf2dd5757abb98897d89e1))
* harden governance tooling — bug fixes, full parity coverage, and unit tests ([81ef1c2](https://github.com/marioGusmao/project-router-template/commit/81ef1c2ae6c18f89b65e09495e59ffa43633a895))
* harden knowledge private-derived coherence ([7904e85](https://github.com/marioGusmao/project-router-template/commit/7904e850854c6528322d3ed6b92178a8cf95b2f1))
* harden knowledge scaffold and sync contract ([77a9e54](https://github.com/marioGusmao/project-router-template/commit/77a9e541e46bc9e143febbee6ef146c7210f0c77))
* harden router follow-up review ([b822c2e](https://github.com/marioGusmao/project-router-template/commit/b822c2e386d987ffdd0f9485e7f262f0db4ba8ab))
* materialize scaffold before tests job too ([6ed819a](https://github.com/marioGusmao/project-router-template/commit/6ed819aa7e356c2947d1aa1c8cd97ba02f34e006))
* resolve remaining review findings — lock TOCTOU, bootstrap markers, git warning, context surfacing ([881c490](https://github.com/marioGusmao/project-router-template/commit/881c4909b1d01c1470280f1b6b7be305368e9362))
* resolve review crash, parse error dedup, relative metadata paths, and observability gaps ([e9099f7](https://github.com/marioGusmao/project-router-template/commit/e9099f7418f17dc82e2dca760180fe44743a1a12))

## 0.1.0 - 2026-03-12

- Split the repository model into a neutral template upstream and a private daily repo.
- Added registry overlay support with candidate-level dispatch validation.
- Moved the VoiceNotes API client into `src/project_router/sync_client.py`.
- Added bootstrap, parity, and ownership governance tooling.
