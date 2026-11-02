# Publication code review

Reviewed the active Python source, prompts, shell launchers, tests, configuration,
and documentation for the classroom pipeline and supplementary position analysis.
Generated research datasets, results, notebooks, and paper drafts are retained
as local artifacts and excluded from the publication export.

## Changes from the review

- Removed commented-out subject lists, old prompts, inactive neutral controls,
  unused roster/replay configuration, compatibility aliases, and an unrelated
  SIFT annotation guide. Original subject/topic values and active prompts are preserved.
- Removed the validator fallback that invented an INCORRECT verdict after a
  parsing failure. Unknown verdicts and nonboolean style judgments now fail.
- Added corruption resume provenance for input content, condition settings,
  generation code, and helper configuration. Unmatched or unrecorded old
  checkpoints are rejected; use a new input filename to regenerate them.
- Preserved limited-run suffixes in evaluation filenames and added the required
  canonical corruption input to the README command for optional conditions.
- Stages preserve partial results but return nonzero status after processing
  failures. Worker/run counts must be positive and session IDs must be unique.
- Removed import-time directory creation and made the optional data root
  consistent across generation, original evaluation discovery, and critic review.
- Made launchers locate the repository from Slurm's submission directory when
  the scheduler copies a script elsewhere. Removed the final private cluster preset.
- Added input hashes and bootstrap settings to metric manifests.
- Included continuous position analysis and its tests in the export, and pinned
  direct dependencies to the installed versions used for verification.

VFR eligibility, matched-pair definitions, bootstrap sampling units, McNemar
calculations, GEE models, and failure category mappings were retained.

## Validation scope

Final verification passed 63 offline tests against a fresh export, with syntax
and local dependency checks for all 86 Python source files.

Verification includes the offline regression suites, a deterministic mocked
six-stage file workflow, source/import checks, and shell launcher checks in a
fresh publication export. The workflow checks session and condition counts,
shared baselines, critic lineage, metrics, failure classifications, and preservation
of source evaluations. No live model requests are made by these checks.

The export is tested with the existing Python 3.11 environment. A new dependency
installation, live API deployment compatibility, label accuracy, and reproduction
of the paper's exact numerical results are not verified by offline tests.

Generation records retain their validation flags. The published metric eligibility
rule is based on valid INCORRECT answer judgments and teacher vigilance labels;
it does not introduce a new stylistic validation filter in this cleanup.
Use the saved corruption inputs and provenance when inspecting realization quality.

Before publication, supply the project's license, citation, and the original
experiment artifacts needed to reproduce the paper's exact reported numbers.
GitHub pushing remains on hold.
