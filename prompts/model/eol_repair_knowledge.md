# EOL Repair Knowledge Base

## Use exact feature names from the active metamodel

Error pattern:
`Property '<feature>' not found in object ...`

Cause:
The EOL program uses a feature name that is not declared by the current generated Emfatic metamodel.

Repair:
Inspect the current metamodel and replace the invalid feature with the exact declared feature.

Examples:
`module.robotic_platforms.add(platform);` must become `module.platform.add(platform);` if the generated metamodel declares `val RoboticPlatform[1] platform;`.
`module.platforms.add(platform);` must become `module.robotic_platforms.add(platform);` if the generated metamodel declares `val RoboticPlatform[*] robotic_platforms;`.

## Respect containment names

Error pattern:
The program executes but the model misses expected contained objects.

Cause:
Objects were created but not added to the generated metamodel's containment reference.

Repair:
After creating an object, add it to the exact containment feature declared by the owner class.

Examples:
If `Module` declares `val PrimitiveType[*] primitiveTypes;`, use `module.primitiveTypes.add(real);`.
If `CompositeType` declares `val Value[*] fields;`, use `composite.fields.add(value);`.
If `CompositeType` declares `val Value[*] values;`, use `composite.values.add(value);`.

## Match generated class names

Error pattern:
`Type '<class>' not found` or a reference expects another generated class.

Cause:
The EOL program uses a reference class from a different metamodel variant.

Repair:
Use the class names present in the current generated metamodel. If the metamodel declares `Field` rather than `Value` for composite type fields, instantiate `new M!Field` for those fields.

## EOL parse errors (MALCOMj / Epsilon)

Error pattern:
`Parse errors in ...candidate_XXX.eol` (or any Epsilon parser error before execution).

Cause:
The EOL program is not valid Epsilon syntax. This is different from `Property '...' not found` runtime errors.

Repair checklist (apply to the **entire** program, not only the latest lines):

1. **Object creation must use parentheses**
   - Wrong: `var m = new M!Module;`
   - Right: `var m = new M!Module();`
   - Same for every `new M!<Class>` expression.

2. **Do not use EOL/Java reserved words as variable names**
   - Wrong: `var int = new M!PrimitiveType();` / `var real = ...` / `var string = ...`
   - Right: `var intType = ...`, `var realType = ...`, `var stringType = ...` (rename and update all references).

3. **One statement per line; end statements with `;`**
   - No trailing prose, JSON trace blocks, or markdown fences (no ```).

4. **Keep only EOL**
   - No explanations after the program. No embedded requirement JSON.

5. **After renaming or fixing syntax, re-run mentally against the current generated metamodel**
   - Class names and features must still match the Emfatic metamodel in the error feedback.

Examples from failed runs:
```eol
// Bad
var int = new M!PrimitiveType;
auv_module.primitiveTypes.add(int);

// Better
var intType = new M!PrimitiveType();
auv_module.primitiveTypes.add(intType);
```

## Return complete EOL only

Error pattern:
Epsilon parser errors caused by prose, JSON, markdown fences, or partial code.

Cause:
The LLM response contains non-EOL text or an incomplete statement/block.

Repair:
Return only a complete EOL program. Do not include markdown fences, comments that contain JSON traceability payloads, or explanations after the program. For syntax-level parse failures, follow **EOL parse errors (MALCOMj / Epsilon)** above first.
