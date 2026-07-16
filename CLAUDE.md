# Working agreement for this repo

This file is about *process* — how to work on NFLUIDS, not what the code does.
For architecture/module reference, see `CODEBASE_REFERENCE.md`. For user-facing
features, see `README.md`. Keep both of those in sync with the code whenever
you change something they describe — that's a standing expectation, not a
one-off request.

## Who you're working with

The user is a 3rd-year aerospace engineering student, not a software engineer.
Their CFD/numerical judgment is strong and should be trusted (Rhie-Chow,
distance-weighted interpolation, refinement-zone grading were all their calls
and were correct). Their software-architecture experience is genuinely
limited by their own account, so:
- Don't assume they'll independently catch architectural risk — flag
  tradeoffs explicitly, especially for anything touching shared
  infrastructure (rendering, the state machine, solver internals).
- Don't dumb down the CFD/numerics side. Explain mechanisms, not just fixes,
  when something behaves confusingly (e.g. why a residual plot looked flat,
  why a color field looked like it was oscillating).
- When asked for an honest assessment of the project, give one — specifics,
  not flattery.

## Verification — what you can and can't check yourself

This is a Pygame + PyOpenGL + ImGui desktop app. You can and should:
- `py_compile` every file you edit before calling something done.
- Do a short backgrounded launch (`timeout 6 ./.venv/Scripts/python.exe NFluid.py`)
  to catch import/startup errors.

You cannot drive the GUI (click buttons, scroll, watch a solve run) from the
CLI. Say so explicitly rather than implying a UI fix has been confirmed
working. The user's manual, in-app testing is the real verification step —
their bug reports are precise (exact repro steps, expected vs. actual), and
that's the highest-leverage thing they provide. Match that: when investigating
a report, read the actual code paths involved (multiple files at once if
needed — use Explore agents for that) and ground the diagnosis in exact
`file:line` references before proposing a fix, rather than guessing.

## Scope discipline

The user often gives conditional scope in the same message ("if it's too much
just do the simple version," "unless it needs big architecture changes, leave
it as is"). Treat that as delegated decision authority: make the call, then
explain the reasoning in the response. Don't re-ask when they've already told
you the decision rule.

## Big refactors need a design pass first

Two are planned before further solver work: unifying the rendering engine
(currently scattered per-module VBO/draw logic) and restructuring
`main.py`'s state machine / solver module boundaries. For work at this
level — shared infrastructure, high blast radius, hard to unwind — use plan
mode and talk through the approach before writing code, even if the user
frames it casually. This is different from the day-to-day bug fixes in this
repo, which don't need that ceremony.

## Testing gap (known, not yet addressed)

There is no real automated test suite (`test_holes.py` is one end-to-end
script). Manual testing covers the current surface area fine, but won't scale
once multiple solvers (SIMPLE, temperature, transient) share code. Bring this
up again before the temperature-field work lands if it hasn't been addressed
by then.

## Commit messages

Do not append a `Co-Authored-By: Claude ...` trailer to commit messages.
Commits are already authored under the user's own git identity — this
trailer is unwanted noise, not attribution the user asked for.

## Release process

- Bump `version` and `description` in `pyproject.toml`.
- Commit with a multi-line message summarizing *what* changed and *why*,
  grouped by file/module.
- Create an annotated tag (`git tag -a vX.Y.Z -m "..."`) with the same
  summary — the project tags every release (check `git tag -l` for the
  existing `v1.x.x` sequence).
- Push both the branch and the tag.
- Don't commit stray backup artifacts (e.g. manual `.zip` backups made before
  a big diff) — clean them up and make sure `.gitignore` covers the pattern
  going forward.

## Roadmap context (as of v1.6.0)

- **v1.6 (done)**: Visualizer update — smoke-particle tracer generator
  (alongside the existing velocity vectors), save/load for visualizations
  (mirroring the existing mesh save/load), and VTU export for
  cross-validating the solver against other codes. A "fake streamlines"
  static-path feature was also built and shipped, then removed after
  in-app testing — the cell-to-cell centroid walk looked jagged on the
  unstructured mesh with no cheap fix (would need a real pathline
  integrator, out of scope). Smoke particles' speed/count controls were
  widened afterward based on the same testing round.
- **Next**: the two refactors flagged above (rendering engine unification,
  main.py/solver structure) — deliberately sequenced *before* more solver
  features, so temperature/transient work lands on a cleaner base.
- **End goal**: additional solvers — a decoupled temperature (scalar
  transport) field first, then a transient/timestepped version of the
  existing solver, visualized with the same live-monitor machinery built in
  v1.5.0.


## Behavioural guidelines

1- Think Before Coding. State your assumptions explicitly. If uncertain, ask.
2- Simplicity First. Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.
3- Surgical Changes. Touch only what you must. Clean up only your own mess. If you notice unrelated dead code, mention it.
4- Goal-Driven Execution. Define success criteria. Loop until verified.