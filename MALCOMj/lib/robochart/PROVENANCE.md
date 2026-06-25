# Vendored official RoboChart toolchain

Copied 2026-06-16 from FORGE
(`formal_method_guided_vibe_coding/forge.transformations/lib/robochart-csp-gen/*.jar`).

The official RoboChart Xtext language, CSP generator, and assertions
(`circus.robocalc.robochart.*`) plus their transitive runtime deps (Guice, Xtext
runtime, ANTLR, Guava, …). 41 jars.

Used by:
- `org.sawg.malcomj.RoboChartAssembler` — parse a `.rct` into a RoboChart EMF model
  (official Xtext setup) and run the vendored `robochart2rct.egl` to synthesise a
  complete, generator-ready `.rct`.
- The FDR4 verifier's CSP generation (`circus.robocalc.robochart.generator.csp.Main`).

Version pins: `robochart 2.0.0`, `textual 3.1.0`, `generator.csp 3.0.0`,
`assertions 2.1.0` (build 202506xx).

REMEDIATE and FORGE are separate workspaces; this is REMEDIATE's own copy and single
source of truth — REMEDIATE does not read the FORGE checkout at runtime. Keep aligned
with FORGE's bundle when it updates.
