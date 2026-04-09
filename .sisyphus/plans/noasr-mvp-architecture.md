# noasr MVP Architecture & Execution Plan

## TL;DR
> **Summary**: Build a Windows-first Python voice input method MVP that records microphone audio while a single hotkey is held, sends raw audio plus prompt text to Xiaomi MiMo Omni through an OpenAI-compatible client, optionally supports safe multi-tool ReAct loops, post-processes the final text with ordered regex replacements, and injects the result via clipboard-save/restore plus simulated paste.
> **Deliverables**:
> - Python package scaffold with installable assets and CLI entrypoint
> - Config/bootstrap pipeline for `~/.noasr`
> - Flet overlay, `pynput` hotkey listener, `sounddevice` recorder
> - MiMo client, ToolManager, AgentManager, one datetime tool
> - Regex postprocessor, text injector, pytest suite, packaging config
> **Effort**: Large
> **Parallel**: YES - 4 waves
> **Critical Path**: bootstrap/config → core abstractions → runtime pipeline → integration/verification

## Context
### Original Request
Analyze `docs/prompt.txt`, interview on unclear/contradictory/impossible points, autonomously design missing but necessary details, complete the overall architecture design, then have a sub-agent implement it.

### Interview Summary
- Repository is currently blank except `docs/prompt.txt`.
- MVP priority is **Windows first**.
- Text injection is **clipboard save/restore + simulated paste**.
- Trigger model is **single-key hold-to-record**.
- Test strategy is **pytest-first**.
- Overlay UI stack is **Flet** and dependency cost is acceptable.
- Global hotkey stack is **pynput**.
- MVP keeps the **full non-destructive ReAct skeleton**, but ships only **one datetime tool** for verification.

### Metis Review (gaps addressed)
- Explicitly define audio normalization contract and MiMo payload shape in implementation tasks.
- Add guardrails for clipboard races, min/max recording duration, single-instance behavior, permission failures, and platform degradation.
- Keep MVP scope narrow: one tool only, no config UI, no autostart, no session persistence, no ASR fallback.

## Work Objectives
### Core Objective
Deliver an installable Python MVP of `noasr` that captures microphone audio on hotkey hold, sends prompt text + base64-encoded audio to MiMo Omni, supports safe tool-calling through a reusable agent framework, applies ordered regex substitutions to the final assistant text, and injects the result into the currently focused application without taking focus away during recording/loading UI.

### Deliverables
- `pyproject.toml` packaging/build/test config
- `src/noasr/` package with runtime modules and abstractions
- `assets/` templates for config and prompt files
- `tests/` suite for unit/integration coverage
- CLI entrypoint for launching the input method runtime
- One built-in safe tool: current date/time

### Definition of Done (verifiable conditions with commands)
- `python -m pytest` passes.
- `python -m noasr --help` returns exit code 0.
- First-run bootstrap creates `~/.noasr/` templates when absent and exits per spec.
- Second run loads user config/prompts/regex without recreating them.
- Holding the configured key starts recording and shows overlay state.
- Releasing the key sends one non-streaming MiMo request and logs full request/response JSON to stderr.
- Final assistant text is regex-transformed in configured order and injected via paste workflow.
- Tool loop can execute the built-in datetime tool and continue until a final assistant message without `tool_calls`.

### Must Have
- Windows-first stable path with documented degradation on macOS/Linux.
- `pynput` hold listener, `sounddevice` audio capture, Flet overlay.
- `importlib.resources`-based packaged asset resolution.
- `ToolManager` singleton + `@agenttool` decorator.
- `AgentType` + `AgentManager` + multi-round ReAct loop.
- Config access via `Path.home()` and defensive `.get()` dict reads with defaults.
- Ordered regex replacement pipeline with capture-group support.
- Clipboard preservation best effort with restore attempt after injection.
- Single-instance runtime lock to avoid duplicate global hook registrations.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- No ASR fallback or Whisper preprocessing.
- No config GUI, autostart, tray integration, or session persistence.
- No destructive tools and no approval subsystem.
- No multi-key mode, toggle-to-record mode, or alternate injection backends in MVP.
- No promise of identical overlay/non-focus behavior on all platforms.
- No live-network tests in CI; MiMo API interactions must be mocked/recorded.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: **tests-after with pytest-first infrastructure** (`pytest`, `pytest-mock`, `pytest-asyncio` only if needed).
- QA policy: Every task includes agent-executed verification; UI/global hook constraints use mocks/fakes where OS automation is unreliable.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: project scaffolding, dependency config, assets/bootstrap contracts, core models/interfaces, logging/config decisions

Wave 2: audio, regex, tool system, MiMo client, injection adapter, single-instance lock

Wave 3: overlay, hotkey runtime, agent loop, orchestration service, CLI integration

Wave 4: integration tests, platform docs, packaging verification, end-to-end mocked runtime validation

### Dependency Matrix (full, all tasks)
- 1 blocks 2,3,4,5,6,7,8,9,10,11,12
- 2 blocks 6,8,11
- 3 blocks 11
- 4 blocks 10,11
- 5 blocks 11
- 6 blocks 11
- 7 blocks 10,11
- 8 blocks 11
- 9 blocks 11
- 10 blocks 11,12
- 11 blocks 12
- 12 precedes Final Verification Wave

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 4 tasks → quick / writing / unspecified-low
- Wave 2 → 5 tasks → unspecified-high / quick
- Wave 3 → 2 tasks → unspecified-high / visual-engineering
- Wave 4 → 1 task → unspecified-high

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Scaffold package, build config, and dependency baseline

  **What to do**: Create the Python project skeleton using `src/` layout. Add `pyproject.toml`, package metadata, CLI entrypoint, pytest configuration, and package-data inclusion for `assets/`. Declare runtime dependencies for `openai`, `flet`, `pynput`, `sounddevice`, and clipboard/injection support selected by executor, plus test dependencies. Use `importlib.resources`-compatible packaging so installed assets are available as real files when copied to `~/.noasr`.
  **Must NOT do**: Do not add unused frameworks, CI-specific cloud services, or alternate GUI/audio stacks.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: mostly mechanical project bootstrap with explicit structure.
  - Skills: [] - no special skill required.
  - Omitted: [`frontend-ui-ux`] - UI polish is not the concern here.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2,3,4,5,6,7,8,9,10,11,12] | Blocked By: []

  **References**:
  - Pattern: `docs/prompt.txt:206-210` - required libraries, cross-platform intent, asset-copy requirement.
  - Pattern: `docs/prompt.txt:190-193` - user config and prompt files that bootstrap must support.
  - External: `https://docs.python.org/3/library/importlib.resources.html` - package resource access pattern.

  **Acceptance Criteria**:
  - [ ] `python -m pytest --collect-only` succeeds.
  - [ ] `python -m noasr --help` exits 0.
  - [ ] Installed package includes `assets/` files discoverable through `importlib.resources`.

  **QA Scenarios**:
  ```
  Scenario: Build/test scaffold is valid
    Tool: Bash
    Steps: Run `python -m pytest --collect-only` from repo root.
    Expected: Test collection completes with exit code 0.
    Evidence: .sisyphus/evidence/task-1-scaffold.txt

  Scenario: CLI entrypoint exists
    Tool: Bash
    Steps: Run `python -m noasr --help`.
    Expected: Help/usage text is printed and command exits 0.
    Evidence: .sisyphus/evidence/task-1-scaffold-help.txt
  ```

  **Commit**: YES | Message: `build(noasr): scaffold package and packaging baseline` | Files: [`pyproject.toml`, `src/noasr/**`, `tests/**`, `assets/**`]

- [ ] 2. Implement config bootstrap and packaged-asset installation

  **What to do**: Create the config/bootstrap service that resolves `Path.home()/".noasr"`, ensures the directory exists, copies template files from installed `assets/`, creates empty system prompt and empty regex registry when absent, and creates a template `config.json` plus warning-and-exit behavior on first run exactly as specified. Use defensive `dict.get()` reads everywhere. Keep file contents UTF-8.
  **Must NOT do**: Do not read home path from environment variables or hand-build OS-specific paths.

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Reason: file/bootstrap logic with careful defaulting.
  - Skills: [] - standard Python suffices.
  - Omitted: [`git-master`] - no git work needed.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [6,8,11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:180-193` - startup file behavior and creation rules.
  - Pattern: `docs/prompt.txt:209-210` - asset source must come from installation path.
  - External: `https://docs.python.org/3/library/pathlib.html` - home directory and file APIs.

  **Acceptance Criteria**:
  - [ ] When `~/.noasr` is absent, bootstrap creates directory and required template files.
  - [ ] First run emits one warning to stderr/stdout per CLI contract and exits without starting runtime.
  - [ ] Second run loads existing files and continues.

  **QA Scenarios**:
  ```
  Scenario: First-run bootstrap creates templates and exits
    Tool: Bash
    Steps: Run tests with HOME/USERPROFILE redirected to a temp directory; invoke bootstrap/startup once.
    Expected: temp `.noasr` contains config.json, input_user_prompt.md, input_system_prompt.md, regex.json; process exits in bootstrap mode.
    Evidence: .sisyphus/evidence/task-2-bootstrap.txt

  Scenario: Existing files are reused
    Tool: Bash
    Steps: Invoke startup a second time against the same temp home.
    Expected: No template recreation warning; startup proceeds to runtime initialization path.
    Evidence: .sisyphus/evidence/task-2-bootstrap-reuse.txt
  ```

  **Commit**: YES | Message: `feat(config): add bootstrap and asset install flow` | Files: [`src/noasr/config*.py`, `assets/**`, `tests/**`]

- [ ] 3. Define domain models, constants, and runtime contracts

  **What to do**: Implement typed data structures for app config, agent config, runtime states, overlay states, request/response wrappers, and platform capability flags. Hard-code MVP defaults for recording constraints: minimum duration 300ms, maximum duration 30s, normalized mono PCM/WAV payload at 16kHz 16-bit before base64 encoding. Explicitly document that `input_audio.data` is sent as a base64 data URI string. Include a single-instance lock contract and platform capability reporting.
  **Must NOT do**: Do not leave audio format or state names implicit.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: clear contract/model definition work.
  - Skills: [] - no special tooling.
  - Omitted: [`refactor`] - no existing code to restructure.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:172` - audio can be base64 URI.
  - Pattern: `docs/prompt.txt:198-201` - record on hold, send audio and text, non-streaming.
  - Pattern: `docs/prompt.txt:255` - dict access should use `.get()` with safe defaults.

  **Acceptance Criteria**:
  - [ ] Config parsing supplies safe defaults when optional fields are absent.
  - [ ] Audio payload helper produces a `data:` URI string for WAV bytes.
  - [ ] Runtime state model covers idle/listening/loading/error/apply-result lifecycle.

  **QA Scenarios**:
  ```
  Scenario: Missing config fields do not crash parsing
    Tool: Bash
    Steps: Run unit tests against minimal and malformed-ish config dict fixtures.
    Expected: Parser returns defaults and no uncaught exception occurs.
    Evidence: .sisyphus/evidence/task-3-models.txt

  Scenario: Audio payload encoding is deterministic
    Tool: Bash
    Steps: Unit-test helper on fixed WAV bytes fixture.
    Expected: Output starts with expected data URI prefix and decodes back to original bytes.
    Evidence: .sisyphus/evidence/task-3-audio-uri.txt
  ```

  **Commit**: YES | Message: `feat(core): define runtime contracts and defaults` | Files: [`src/noasr/models*.py`, `src/noasr/constants*.py`, `tests/**`]

- [ ] 4. Implement ToolManager, ITool, and built-in datetime tool

  **What to do**: Create the `ITool` abstraction with `name`, `function`, and `xeq(arguments: dict) -> str`. Implement `ToolManager` as a singleton with `getInstance()`, `toolDict`, `toolSetReg`, `@agenttool` registration, `getToolSets(list[str]) -> list[dict]`, and `xeqTool(name, arguments) -> str`. Ship one safe built-in tool that returns current local date/time in a stable ISO-like string and is discoverable through toolset config.
  **Must NOT do**: Do not add any system-mutating tool or approval flow.

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Reason: framework code with deterministic behavior.
  - Skills: [] - standard implementation.
  - Omitted: [`review-work`] - reserved for post-implementation, not task execution.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [10,11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:213-231` - complete ITool/ToolManager requirements.
  - Pattern: `docs/prompt.txt:208` - future extensibility and non-destructive tools.

  **Acceptance Criteria**:
  - [ ] `ToolManager.getInstance()` returns the same singleton object.
  - [ ] Decorated tools auto-register into `toolDict`.
  - [ ] `getToolSets()` de-duplicates tool names across multiple toolsets and returns only tool `function` dicts.
  - [ ] `xeqTool()` executes the datetime tool and returns a string.

  **QA Scenarios**:
  ```
  Scenario: Tool registration and deduplication work
    Tool: Bash
    Steps: Run unit tests covering duplicate toolset names and duplicate tool names across sets.
    Expected: Returned tools list contains each tool once and matches registered function metadata.
    Evidence: .sisyphus/evidence/task-4-tools.txt

  Scenario: Unknown tool is handled safely
    Tool: Bash
    Steps: Unit-test `xeqTool()` with a missing tool name.
    Expected: The method returns a controlled error string or raises a project-defined safe exception handled by caller tests.
    Evidence: .sisyphus/evidence/task-4-tools-error.txt
  ```

  **Commit**: YES | Message: `feat(tools): add tool manager and datetime tool` | Files: [`src/noasr/tools/**`, `tests/**`]

- [ ] 5. Implement regex postprocessor with ordered substitution semantics

  **What to do**: Build the regex registry loader and transformer for `~/.noasr/regex.json`. Preserve the on-disk mapping order, compile/apply patterns top-to-bottom, support capture groups and replacement strings containing escaped sequences like `\n`, and expose one pure transformation function usable by runtime and tests.
  **Must NOT do**: Do not reorder patterns, silently drop invalid entries, or require custom DSL syntax.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: isolated transformation logic.
  - Skills: [] - none needed.
  - Omitted: [`ai-slop-remover`] - unnecessary for single clean implementation.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:201-202` - replacement rules and sequential behavior.
  - Pattern: `docs/prompt.txt:255` - safe dict access and resilience.

  **Acceptance Criteria**:
  - [ ] Sequential ordering changes output as expected in tests.
  - [ ] `\n` escapes and `$1/$2` capture substitutions work.
  - [ ] Invalid regex entries produce controlled errors that do not crash startup unexpectedly.

  **QA Scenarios**:
  ```
  Scenario: Ordered replacements are preserved
    Tool: Bash
    Steps: Run unit tests with multiple mappings where order changes result.
    Expected: Output matches top-to-bottom registry semantics.
    Evidence: .sisyphus/evidence/task-5-regex.txt

  Scenario: Capture groups and escaped newlines work
    Tool: Bash
    Steps: Test replacements using groups and `\n` values.
    Expected: Output contains expected substituted text and newline characters.
    Evidence: .sisyphus/evidence/task-5-regex-escape.txt
  ```

  **Commit**: YES | Message: `feat(regex): add ordered replacement pipeline` | Files: [`src/noasr/regex*.py`, `tests/**`]

- [ ] 6. Implement MiMo client wrapper and request/response logging

  **What to do**: Build the OpenAI-compatible client wrapper around the configured `baseurl` and `api_key`, correcting the prompt example’s swapped variable semantics in project code/docs. Implement message builders for plain transcription mode and agent mode. For runtime requests, send exactly one system message using `input_system_prompt.md` content and one user message containing text from `input_user_prompt.md` and the audio input item. Add stderr JSON logging of the exact outbound payload dict and full inbound response JSON string. Provide mockable transport boundaries for tests.
  **Must NOT do**: Do not stream responses, hide payloads from stderr, or bake secrets into logs beyond what the spec explicitly requires.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: API contract, logging, and testability are central runtime concerns.
  - Skills: [] - standard Python networking library usage.
  - Omitted: [`tavily-search`] - research is already complete.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [11] | Blocked By: [1,2]

  **References**:
  - Pattern: `docs/prompt.txt:7-43` - audio input example.
  - Pattern: `docs/prompt.txt:80-129` - tool-call example.
  - Pattern: `docs/prompt.txt:197-200` - actual runtime message structure for MVP.
  - Pattern: `docs/prompt.txt:207` - stderr logging requirement.

  **Acceptance Criteria**:
  - [ ] Request builder produces the specified two-message payload for non-tool mode.
  - [ ] Agent-mode request builder includes tools from merged toolsets.
  - [ ] Full request dict and raw response JSON are written to stderr once per round.
  - [ ] Unit tests use mocked client calls only.

  **QA Scenarios**:
  ```
  Scenario: Non-tool MiMo payload matches spec
    Tool: Bash
    Steps: Run unit tests asserting outbound message JSON shape from fixed fixtures.
    Expected: Payload contains one system message and one multimodal user message with text + input_audio items.
    Evidence: .sisyphus/evidence/task-6-client.txt

  Scenario: Tool-call response is logged and parsed safely
    Tool: Bash
    Steps: Run mocked tests with a response containing `tool_calls` and with a response containing final text.
    Expected: Parser distinguishes both forms, stderr logging occurs, and no network call escapes test mocks.
    Evidence: .sisyphus/evidence/task-6-client-tools.txt
  ```

  **Commit**: YES | Message: `feat(client): add mimo client wrapper and logging` | Files: [`src/noasr/client*.py`, `tests/**`]

- [ ] 7. Implement audio recorder and normalization pipeline

  **What to do**: Implement in-memory microphone recording using `sounddevice`, keyed by start/stop lifecycle from the runtime. Normalize captured audio into mono 16kHz 16-bit WAV bytes suitable for base64 data-URI packaging. Enforce minimum duration 300ms (discard too-short recordings) and maximum duration 30s (auto-stop or clamp). Separate live device access from pure byte-normalization helpers so tests can use synthetic buffers.
  **Must NOT do**: Do not write temporary audio files during normal runtime and do not block the UI thread.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: audio device handling plus normalization plus test seams.
  - Skills: [] - implementation-focused.
  - Omitted: [`frontend-ui-ux`] - unrelated.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [10,11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:198-199` - in-memory recording starts on press and ends on release.
  - Pattern: `docs/prompt.txt:172` - audio data may be provided in base64 URI form.
  - External: `https://python-sounddevice.readthedocs.io/` - recording and device access patterns.

  **Acceptance Criteria**:
  - [ ] Pure helper converts synthetic float/int sample arrays into mono 16kHz 16-bit WAV bytes.
  - [ ] Too-short recordings are rejected safely.
  - [ ] Too-long recordings are capped.
  - [ ] Recorder lifecycle is non-blocking and testable with mocked device input.

  **QA Scenarios**:
  ```
  Scenario: Audio normalization produces correct WAV payload
    Tool: Bash
    Steps: Run unit tests on synthetic sample data.
    Expected: Output WAV headers are valid and duration/sample rate match normalized contract.
    Evidence: .sisyphus/evidence/task-7-audio.txt

  Scenario: Recording duration guards work
    Tool: Bash
    Steps: Test with synthetic durations below 300ms and above 30s.
    Expected: Short audio is rejected; long audio is capped or auto-stopped per implementation contract.
    Evidence: .sisyphus/evidence/task-7-audio-limits.txt
  ```

  **Commit**: YES | Message: `feat(audio): add recorder and normalization flow` | Files: [`src/noasr/audio*.py`, `tests/**`]

- [ ] 8. Implement clipboard-preserving text injector with Windows-first adapter

  **What to do**: Create a text injection service that snapshots clipboard contents, sets generated text, simulates paste into the currently focused application, then best-effort restores the prior clipboard. Implement Windows-first behavior explicitly and abstract platform adapters for future macOS/Linux support. Provide a fallback paste-key chain decision in code/docs: Windows uses `Ctrl+V` first and may fall back to `Shift+Insert` if explicitly safe in implementation. Guard against empty output and nested injection attempts.
  **Must NOT do**: Do not attempt native IME integration in MVP or promise zero clipboard race risk.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: OS interaction and state restoration demand careful handling.
  - Skills: [] - standard implementation.
  - Omitted: [`playwright`] - browser automation is irrelevant.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [11] | Blocked By: [1,2]

  **References**:
  - Pattern: `docs/prompt.txt:202` - output once at the cursor, not pseudo-streaming.
  - Research: clipboard+paste was selected in interview as MVP injection path.

  **Acceptance Criteria**:
  - [ ] Non-empty text is copied, pasted, and prior clipboard content restoration is attempted.
  - [ ] Empty/whitespace-only final text does not trigger paste.
  - [ ] Platform adapter interface exists for Windows/macOS/Linux.

  **QA Scenarios**:
  ```
  Scenario: Clipboard contents are restored after injection attempt
    Tool: Bash
    Steps: Run unit tests with mocked clipboard and key-simulation backends.
    Expected: Original clipboard value is restored after successful paste path.
    Evidence: .sisyphus/evidence/task-8-injector.txt

  Scenario: Paste is skipped for empty output
    Tool: Bash
    Steps: Test injector with empty and whitespace-only strings.
    Expected: No paste simulation occurs and clipboard remains unchanged.
    Evidence: .sisyphus/evidence/task-8-injector-empty.txt
  ```

  **Commit**: YES | Message: `feat(injector): add clipboard-preserving text injection` | Files: [`src/noasr/injector*.py`, `tests/**`]

- [ ] 9. Implement single-instance lock and runtime capability diagnostics

  **What to do**: Add a single-instance guard so only one noasr process owns the global hotkey runtime at a time. Add startup capability diagnostics for platform limitations (e.g. Windows recommended, macOS accessibility required, Linux/Wayland degraded). Expose these diagnostics through logs and controlled startup messages rather than crashes.
  **Must NOT do**: Do not silently allow multiple running instances with overlapping hotkeys.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: focused utility work with explicit outputs.
  - Skills: [] - no special toolchain.
  - Omitted: [`oracle`] - not a hard reasoning problem.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [11] | Blocked By: [1]

  **References**:
  - Pattern: `docs/prompt.txt:193` - keyboard latency and listener behavior matter.
  - Research: platform restrictions from pynput/Flet investigation.

  **Acceptance Criteria**:
  - [ ] Starting a second instance fails gracefully with a clear message.
  - [ ] Capability diagnostics report platform-specific limitations without aborting supported Windows flow.

  **QA Scenarios**:
  ```
  Scenario: Single-instance guard rejects second launcher
    Tool: Bash
    Steps: Run tests that acquire the lock once, then simulate a second acquisition.
    Expected: Second acquisition returns a controlled failure state/message.
    Evidence: .sisyphus/evidence/task-9-lock.txt

  Scenario: Capability diagnostics are platform-aware
    Tool: Bash
    Steps: Unit-test diagnostics with mocked platform identifiers.
    Expected: Windows, macOS, Linux/X11, and Linux/Wayland emit distinct capability messages.
    Evidence: .sisyphus/evidence/task-9-diagnostics.txt
  ```

  **Commit**: YES | Message: `feat(runtime): add single-instance and platform diagnostics` | Files: [`src/noasr/runtime*.py`, `tests/**`]

- [ ] 10. Implement AgentType, AgentManager, and multi-round ReAct loop

  **What to do**: Implement `AgentType` from config and `AgentManager` with `agentDict`, `@agenttype` registration, configured trigger bindings, and `runAgent(name, initial_messages) -> str`. The loop must continue while MiMo returns `tool_calls`, execute each tool via `ToolManager.getInstance().xeqTool(...)`, append tool result messages, resend, and stop only when no `tool_calls` remain; then return final `choices[0].message.content`. Keep the conversation in-memory only.
  **Must NOT do**: Do not persist sessions or introduce destructive-tool approval flows.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: central orchestration logic with iterative protocol handling.
  - Skills: [] - explicit protocol implementation.
  - Omitted: [`git-master`] - unrelated.

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: [11,12] | Blocked By: [1,4,6,7]

  **References**:
  - Pattern: `docs/prompt.txt:233-247` - AgentType and AgentManager contract.
  - Pattern: `docs/prompt.txt:245` - exact tool-call loop behavior.
  - Pattern: `docs/prompt.txt:247` - no conversation persistence.

  **Acceptance Criteria**:
  - [ ] Agent config maps toolsets to merged tool definitions.
  - [ ] `runAgent()` loops until no `tool_calls` remain.
  - [ ] Tool result messages include the correct tool identifiers and content.
  - [ ] Final assistant content is returned as string.

  **QA Scenarios**:
  ```
  Scenario: Single tool-call round completes correctly
    Tool: Bash
    Steps: Run mocked tests with one response containing a datetime tool call followed by a final assistant response.
    Expected: Tool executes once, tool result message is appended, and final text is returned.
    Evidence: .sisyphus/evidence/task-10-agent.txt

  Scenario: Multi-tool call batch is handled in one round
    Tool: Bash
    Steps: Mock a response with multiple tool calls in one assistant message.
    Expected: All tools are executed, appended, and the next request includes every tool result.
    Evidence: .sisyphus/evidence/task-10-agent-multi.txt
  ```

  **Commit**: YES | Message: `feat(agent): add agent manager and react loop` | Files: [`src/noasr/agent*.py`, `tests/**`]

- [ ] 11. Implement overlay, hotkey runtime, and end-to-end orchestration service

  **What to do**: Build the runtime coordinator that wires config loading, single-instance lock, hotkey listener, overlay state transitions, audio recording, MiMo request dispatch, tool-loop execution when an agent is selected, regex postprocessing, and text injection. Use `pynput` for the configured single-key hold lifecycle. Use Flet to render a bottom-of-screen black capsule with centered white text that shows `Listening MM:SS` during recording and `Loading` while waiting. Design the overlay as best-effort topmost/non-activating; on Windows, prioritize not stealing focus; on macOS/Linux, degrade gracefully and document limits. Ensure listener flow is event-driven, not polling.
  **Must NOT do**: Do not block keyboard processing with polling loops, do not pseudo-stream output, and do not let overlay focus hijack crash the app.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: combines UI behavior with runtime orchestration details.
  - Skills: [] - implementation remains custom.
  - Omitted: [`frontend-ui-ux`] - this is not product-design exploration; requirements are explicit.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [12] | Blocked By: [2,3,5,6,7,8,9,10]

  **References**:
  - Pattern: `docs/prompt.txt:193-202` - full runtime behavior from listener to output.
  - Pattern: `docs/prompt.txt:197` - exact overlay appearance.
  - Research: Flet accepted by user; true non-activation is best effort only.

  **Acceptance Criteria**:
  - [ ] Pressing configured key transitions runtime to listening state and starts timer updates.
  - [ ] Releasing key stops recording and shows loading state until response completes.
  - [ ] Final transformed text is injected once and runtime returns to idle.
  - [ ] Permission/device/network failures are surfaced as controlled runtime errors and idle recovery, not crashes.

  **QA Scenarios**:
  ```
  Scenario: Runtime state machine follows hold-to-record flow
    Tool: Bash
    Steps: Run integration tests with mocked hotkey, audio, client, overlay, and injector backends.
    Expected: idle -> listening -> loading -> applying-result -> idle transitions occur in order.
    Evidence: .sisyphus/evidence/task-11-runtime.txt

  Scenario: Failure during client call recovers safely
    Tool: Bash
    Steps: Simulate a MiMo timeout/network error in integration tests.
    Expected: Overlay leaves loading state, no paste occurs, error is logged, runtime returns to idle.
    Evidence: .sisyphus/evidence/task-11-runtime-error.txt
  ```

  **Commit**: YES | Message: `feat(runtime): wire overlay hotkey and dictation pipeline` | Files: [`src/noasr/main*.py`, `src/noasr/overlay*.py`, `src/noasr/hotkey*.py`, `tests/**`]

- [ ] 12. Finalize documentation-by-tests, mocked E2E coverage, and packaging validation

  **What to do**: Add comprehensive tests covering startup bootstrap, tool loop, regex ordering, audio guards, injection flow, runtime orchestration, and packaging/resource access. Include one mocked end-to-end test for the datetime tool path and one mocked end-to-end transcription path. Ensure evidence commands are stable on a clean machine and document platform caveats inline in test names/docstrings or runtime docs where appropriate.
  **Must NOT do**: Do not rely on live MiMo credentials, real microphone input, or manual GUI clicking in automated validation.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: broad integration and verification sweep.
  - Skills: [] - testing focus.
  - Omitted: [`playwright`] - browser tooling not needed.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: [] | Blocked By: [1,10,11]

  **References**:
  - Pattern: `docs/prompt.txt:207` - stderr logging is part of runtime contract and must be asserted.
  - Pattern: `docs/prompt.txt:255` - stability/defensive access requirement.

  **Acceptance Criteria**:
  - [ ] `python -m pytest` passes locally with no live external dependencies.
  - [ ] Mocked end-to-end tests cover both plain dictation and one-tool ReAct flow.
  - [ ] Packaging/resource tests verify assets are discoverable after install/build.

  **QA Scenarios**:
  ```
  Scenario: Mocked E2E dictation flow passes
    Tool: Bash
    Steps: Run `python -m pytest tests -q` with all external dependencies mocked.
    Expected: All tests pass, including dictation path from hotkey release to paste invocation.
    Evidence: .sisyphus/evidence/task-12-e2e.txt

  Scenario: Package resource access works after build
    Tool: Bash
    Steps: Run build/install-oriented tests or isolated resource-access tests against the packaged app.
    Expected: Asset lookup via `importlib.resources` succeeds and bootstrap can copy template files.
    Evidence: .sisyphus/evidence/task-12-package.txt
  ```

  **Commit**: YES | Message: `test(noasr): add integration and packaging verification` | Files: [`tests/**`, `pyproject.toml`, `src/noasr/**`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit after each numbered task using the provided conventional-style messages.
- Keep commits atomic by subsystem.
- Do not bundle unrelated modules into one commit.
- Final verification fixes, if any, should use follow-up fix commits rather than amend unless the executor created the immediately previous unpublished commit and hooks modified files.

## Success Criteria
- The app can be installed and started on Windows with a documented path for macOS/Linux degradation.
- First-run setup is self-bootstrapping and non-destructive.
- Hold-to-record flow is event-driven, not polling, and returns final text in one paste.
- The agent/tool framework is already reusable for future safe tools.
- All automated tests pass without live API/microphone/manual focus requirements.
