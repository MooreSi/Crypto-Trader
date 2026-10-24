# File organisation and splitting

- **800 lines is the ceiling** for any Python file under `backend/` or `tools/`
  (structure gate). Aim well below; most files here are under 300.
- One domain per directory under `services/`. Name files for what they do:
  `*_repo.py` for SQL, `*_service.py` or a plain noun for logic.
- **Splitting a file:** move whole functions verbatim into a new sibling
  module, import them back, run the suite, then update callers. Never change
  behaviour in the same commit as a move. A new module nothing imports yet
  fails the orphan gate: wire it in the same change.
- A module's state is read through the module at call time, never copied at
  import (a copied reference keeps pointing at the old object after a rebind).
- Frontend: one page per directory under `frontend/src/components/<page>/`,
  shared pieces in `components/shared/`, all HTTP through `src/api/client.ts`.
