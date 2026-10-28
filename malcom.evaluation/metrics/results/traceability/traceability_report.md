# Trace-link resolvability and requirement coverage

*Resolvability* is the fraction of emitted links whose target element
exists in the generated artefact; *coverage* is the fraction of
requirements with at least one emitted link. The two are independent:
`effective_coverage` (in the CSVs) is the stricter reading that counts
only requirements whose link also resolves. Resolution uses the
pipeline's own locators (`MALCOMp/trace_locator.py`), so these figures
measure the same property the pipeline stamps as `source.resolved`.

Runs scored: **9**

## Summary (link-weighted across runs)

| Layer | Runs | Links | Resolved | Resolvability | Resolvability (named elements) | Coverage (mean) | Coverage (min-max) | Agreement with recorded `source.resolved` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| concept | 7 | 714 | 660 | 0.9244 | 1.0000 (628 links) | 1.0000 | 1.00-1.00 | 1.0000 |
| notation | 7 | 195 | 195 | 1.0000 | 1.0000 | 1.0000 | 1.00-1.00 | 1.0000 |
| model | 5 | 421 | 421 | 1.0000 | 1.0000 | 1.0000 | 1.00-1.00 | 1.0000 |
| behaviour | 6 | 106 | 106 | 1.0000 | 1.0000 | 0.6543 | 0.59-0.67 | 1.0000 |
| architectural (pooled) | 7 | 1330 | 1276 | 0.9594 | 1.0000 (1244 links) | 1.0000 | 1.00-1.00 | n/a |

The concept layer emitted 86 links naming a metamodel **type** rather than a specific instance (resolvability 0.372). A type name is normally written as prose in the requirement ("Robotic Platform" for `RoboticPlatform`), so it does not resolve by identifier match. The *named elements* column excludes these; it is the figure comparable to the other layers.

## Per run

| Run | Layer | Links | Resolvability | Coverage | Artefact |
|---|---|---:|---:|---:|---|
| pipeline_20260616_143114 | behaviour | 18 | 1.0000 | 0.6667 | result_behaviour_model.rct |
| pipeline_20260617_081950 | behaviour | 16 | 1.0000 | 0.5926 | result_behaviour_model.rct |
| web_20260530_182240_auto1 | concept | 171 | 0.9181 | 1.0000 | requirement text |
| web_20260530_182240_auto1 | notation | 20 | 1.0000 | 1.0000 | result_DSL.emf |
| web_20260530_182240_auto1 | model | 75 | 1.0000 | 1.0000 | result_eol_program.eol |
| web_20260530_182240_auto1 | behaviour | 18 | 1.0000 | 0.6667 | STM.txt |
| web_20260530_191159_auto2 | concept | 277 | 0.8917 | 1.0000 | requirement text |
| web_20260530_191159_auto2 | notation | 63 | 1.0000 | 1.0000 | result_DSL.emf |
| web_20260530_191159_auto2 | model | 131 | 1.0000 | 1.0000 | result_eol_program.eol |
| web_20260530_191159_auto2 | behaviour | 18 | 1.0000 | 0.6667 | STM.txt |
| web_20260530_195147_auto3 | concept | 174 | 0.9425 | 1.0000 | requirement text |
| web_20260530_195147_auto3 | notation | 22 | 1.0000 | 1.0000 | result_DSL.emf |
| web_20260530_195147_auto3 | model | 71 | 1.0000 | 1.0000 | result_eol_program.eol |
| web_20260530_195147_auto3 | behaviour | 0 |  | 0.0000 | STM.txt |
| web_20260615_190332 | concept | 32 | 1.0000 | 1.0000 | requirement text |
| web_20260615_190332 | notation | 26 | 1.0000 | 1.0000 | result_dsml.emf |
| web_20260615_190332 | model | 74 | 1.0000 | 1.0000 | result_model.eol |
| web_20260615_190332 | behaviour | 18 | 1.0000 | 0.6667 | result_behaviour_model.rct |
| web_20260616_095309 | concept | 20 | 1.0000 | 1.0000 | requirement text |
| web_20260616_095309 | notation | 20 | 1.0000 | 1.0000 | result_dsml.emf |
| web_20260616_110920 | concept | 20 | 1.0000 | 1.0000 | requirement text |
| web_20260616_110920 | notation | 24 | 1.0000 | 1.0000 | result_dsml.emf |
| web_20260616_113256 | concept | 20 | 1.0000 | 1.0000 | requirement text |
| web_20260616_113256 | notation | 20 | 1.0000 | 1.0000 | result_dsml.emf |
| web_20260616_113256 | model | 70 | 1.0000 | 1.0000 | result_model.eol |
| web_20260616_113256 | behaviour | 18 | 1.0000 | 0.6667 | result_behaviour_model.rct |

## Unresolved links (examples)

Each entry is `requirement:element` — a link whose target
was not found in the artefact.

- **web_20260530_182240_auto1** / concept: `interface3:Parameter (type name)`, `interface3:ReturnValue (type name)`, `sd2:RoboticPlatform (type name)`, `sd2:Interface (type name)`, `pt1:PrimitiveType (type name)`, `ct1:CompositeType (type name)`, `interface1:Value (type name)`, `interface2:Event (type name)`
- **web_20260530_191159_auto2** / concept: `sd2:RoboticPlatform (type name)`, `sd2:Interface (type name)`, `pt1:PrimitiveType (type name)`, `sd2:RoboticPlatform (type name)`, `sd2:Interface (type name)`, `pt1:PrimitiveType (type name)`, `sd2:RoboticPlatform (type name)`, `sd2:Interface (type name)`
- **web_20260530_195147_auto3** / concept: `sd1:System (type name)`, `sd1:System (type name)`, `sd1:System (type name)`, `sd2:RoboticPlatform (type name)`, `pt1:PrimitiveType (type name)`, `ct1:CompositeType (type name)`, `interface1:Value (type name)`, `interface2:Event (type name)`

## Warnings

- **web_20260530_195147_auto3** / behaviour: a trace file exists but emitted no links (failed phase). Excluded from the coverage average; see `runs_empty` in the summary.
