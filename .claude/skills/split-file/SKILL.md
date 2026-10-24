---
name: split-file
description: Split a Python file that is over (or near) the 800-line ceiling without changing behaviour. Use when the structure gate reports a file too large, or a file is getting hard to read.
---

# Split a file

1. Run the tests that cover the file; they must be green before you start.
2. Choose cohesive groups of functions. Move them **verbatim** into a new
   sibling module.
3. Import them back into the original module so callers keep working; run the
   tests.
4. Update callers to the new home; run the tests; remove the re-imports.
5. A new module must be imported in the same change (orphan gate).
6. Module state is read through the module at call time, never copied at import.
7. No behaviour change in the same commit. `tools.checks all`.
