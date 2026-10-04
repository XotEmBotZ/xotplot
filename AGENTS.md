This is an operational cum explorational project. No changes must be made without explecit instructions
For anything related to python and package management usage of UV and UVX is must, standard calling of python3 or pip is prehibited
Changes unless explecitly authorized in this folder is prohibited.

For rememberance, storage, referencial purpose. ALL agents must keep things (and frequently update) docs/agents/ folder.
Agents are not allower to wander off / proceed with any tasks other than whats explecitly specificed, if such requrements are deemed necessary, user must be notified of it for its approval.

The coding / style guide of this project is FAIL-FAST, SIMPLE-ONLY, LEAST-CODE-FOR-CORRECT-OUTPUT No mechanisms for auto fallback, auto fixation, or any changes to the sate automatically is welcome unless explecitly stated. This also expands to addition of aditional lines of code to "fail fast" which are disallowed

All default styling colors, assumptions, parameters, and constants must be placed in `src/xotplot/constants.py` rather than hardcoded in individual widget files. All plot canvases must strictly remain in light theme (`#ffffff` canvas background).

All plot related code must be in engine module, gui/tui/cli will just communicate with this engine module to get the things done. Engine must be a different process itself and must not interfear with execution of the GUI/TUI/CLI so that all stays resposnsive irrespective of what engine is doing.

We need debounce on all imputs which can be quickly changed, and all thing needs to be submited to the engine, GUI mustn't freeze because the computation is heavy

NEVER COMMIT UNLESS I EXPECITLY STATE TO.