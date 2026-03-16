# Changelog

All notable changes to the shared Project Router starter will be documented in this file.

## Unreleased

- Fixed template sync diff-only handling so review output lives outside the repo and is rendered in the sync PR body.
- Tightened contract validation with conflict-marker detection, reject-file detection, and release-note enforcement for upgrade-governance surfaces.
- Added regression tests for template sync governance tooling.

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
