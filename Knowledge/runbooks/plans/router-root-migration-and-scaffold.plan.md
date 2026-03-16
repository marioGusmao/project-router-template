# Router Root Migration And Scaffold

## Status

- Overall: `completed`
- Current phase: `P03`

## Summary

Close the remaining gaps from the `init-router-root` and `adopt-router-root` rollout by:

- failing closed when `init-router-root --packet-types` is empty or invalid
- adding regression tests for packet-type validation
- restoring the repo-native canonical plan artifact under `Knowledge/runbooks/plans/`

## Assumptions

- `projects/registry.shared.json` remains the canonical source of valid project keys.
- `project-router/router-contract.json` defines the canonical default packet-type order.
- `state/` remains gitignored and safe for local adoption artifacts.
- No migration behavior changes are needed beyond packet-type validation and plan-file closure.

## Execution Phases

- `P01` completed: inspect current implementation and confirm remaining gaps
- `P02` completed: harden `init-router-root --packet-types` and add regression tests
- `P03` completed: restore the canonical repo-native plan file and run the full validation lane

## Phase P01

- Status: `completed`
- Goal: confirm the remaining defects after the initial rollout.
- Dependencies: none.
- Owned files or surfaces: [src/project_router/cli.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/src/project_router/cli.py), [tests/test_project_router.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/tests/test_project_router.py)
- Interfaces or contracts: `init-router-root`, repo-native plan contract
- Implementation notes: identified that `--packet-types ',,,'` crashes with `IndexError` and that the canonical plan file was still missing from the repo.
- Validation: reproduce the CLI failure and confirm missing `Knowledge/runbooks/plans/` artifact.
- Rollback: none.
- Acceptance criteria: concrete defects are identified with file-level evidence.
- Blocker state: none.

## Phase P02

- Status: `completed`
- Goal: fail closed on invalid `--packet-types` input and lock the behavior with tests.
- Dependencies: `P01`
- Owned files or surfaces: [src/project_router/cli.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/src/project_router/cli.py), [tests/test_project_router.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/tests/test_project_router.py)
- Interfaces or contracts: `init-router-root --packet-types`
- Implementation notes: add explicit parsing/validation for empty and duplicate packet-type inputs before any scaffold writes occur.
- Validation: add regression tests for empty and duplicate packet-type lists.
- Rollback: revert the packet-type parser/helper and the new tests together.
- Acceptance criteria: invalid packet-type input raises clean `SystemExit` errors and no scaffold files are created.
- Blocker state: none.

## Phase P03

- Status: `completed`
- Goal: restore the canonical repo-native plan file and complete the full validation lane.
- Dependencies: `P02`
- Owned files or surfaces: [Knowledge/runbooks/plans/router-root-migration-and-scaffold.plan.md](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/Knowledge/runbooks/plans/router-root-migration-and-scaffold.plan.md), repo validation commands
- Interfaces or contracts: file-backed plan contract, repo governance/publish checks
- Implementation notes: this file is the canonical execution record; the repo validation lane completed successfully after promoting the plan path into the knowledge-structure contract.
- Validation: run the full repo validation lane listed below.
- Rollback: remove the plan file only if the implementation is fully reverted.
- Acceptance criteria: the plan file exists in the repo-native location and the validation lane passes.
- Blocker state: none.

## Validation Strategy

```bash
python3 scripts/refresh_knowledge_local.py --apply-missing
python3 -m pytest tests/test_project_router.py tests/test_template_governance.py -q
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_managed_blocks.py
python3 scripts/check_customization_contracts.py
python3 scripts/check_knowledge_structure.py --strict
python3 scripts/check_adr_related_links.py --mode block
```

## Risks and Rollback

- Risk: packet-type validation rejects inputs that previously slipped through.
  Mitigation: keep the behavior narrow and covered by regression tests.
- Risk: the plan file drifts from the implementation state.
  Mitigation: treat this file as the canonical execution record and update phase status inline.
- Rollback: revert [src/project_router/cli.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/src/project_router/cli.py), [tests/test_project_router.py](/Users/mariosilvagusmao/Documents/Code/MarioProjects/project-router-template/tests/test_project_router.py), and this plan file together if the change set must be abandoned.
