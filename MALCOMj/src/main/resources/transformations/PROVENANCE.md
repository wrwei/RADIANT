# Vendored transformations — provenance

## robochart2rct.egl

Vendored **verbatim** from FORGE
(`formal_method_guided_vibe_coding/forge.transformations/src/main/resources/transformations/robochart2rct.egl`)
on 2026-06-16. REMEDIATE and FORGE are separate workspaces; this is REMEDIATE's
own copy and single source of truth — REMEDIATE does not read the FORGE checkout
at runtime.

**What it does:** given a RoboChart *state-machine* EMF model (`RoboChart!RCPackage`
with machines), it synthesises a complete, generator-ready `.rct` — deriving the
`Inputs`/`Outputs`/`Shared` interfaces from trigger-vs-action event usage, mining
guard/action expressions for `Ctrl_State` variables and `Constants`, and emitting
the `stm` (with `uses`/`requires`), `controller` (sref/opref/connections), and a
unified `module` with a `robotic platform` + platform→controller connections. Output
is compatible with the standalone RoboChart CSP generator.

**FORGE-pipeline couplings to handle when wiring it into REMEDIATE's Epsilon:**
- `constantDefaults` — a global Map FORGE injects (constant → default value). Used
  only behind `.isDefined()` guards; REMEDIATE must still bind it (an empty Map is
  fine → constants default to `= 1`).
- `extractRctTrace(out.toString())` at the end — builds an M2T trace; review whether
  REMEDIATE needs it or should neutralise it.

**Update policy:** keep byte-identical to FORGE's version where possible so fixes
flow across. Any REMEDIATE-specific adaptation must be recorded here.
