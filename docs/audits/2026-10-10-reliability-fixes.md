# Reliability fixes and topical knowledge lookup — 2026-10-10

The user authorized all registered projects for the audit and repairs of the identified defects. This is a targeted repair, not a complete runtime audit of all 82 projects. No live database, credentials, medical records, or external API calls were required.

## Verified changes

| Area | Result | Verification |
| --- | --- | --- |
| Both medical review bots | Bounded local document cache, expiration release, LRU eviction, four indexes chosen from actual comment/reminder queries | MAX: 15; Telegram: 16 offline tests |
| Both goal planners | File-lock coordinated publication with per-writer temporary files and revision-checked application saves | Original: 7; macOS: 29 Python checks |
| macOS planner recovery | Serialized browser saves, permanent error banner, local JSON copy and guarded reload | Two queue scenarios; recovery/export/failure/concurrent-edit scenarios |
| Analytics snapshots | Unique staging, validation of copied bytes, no-overwrite immutable publication, atomic pointer, safe target resolution | 133 synthetic snapshot/build checks |
| Hub knowledge | Conditional topic lookup after project confirmation, five published generic draft summaries, no relevant evidence means normal continuation | 25 architecture tests; fresh install with/without knowledge; repeat preview; independent scenario review |
| Project descriptions | 48 placeholder contexts filled from registered metadata and bounded local evidence; unknown facts remain explicit | No TBD remains in registered project contexts; preexisting useful sections retained |

## Knowledge behavior

The Hub entry rule points to the optional knowledge module. Before development/design/investigation, search only the confirmed project's knowledge and explicitly published generic Hub references. Read matching records, check applicability/status/source/date, and do not promote article claims into instructions. Absence or no match requires no question. Other projects remain isolated; links grant no access.

The five user-provided article summaries remain draft. Original project records are retained; the shipped reference edition is a deliberate generic publication, not an automatic project-memory sync. Later records remain project-local unless sharing is requested. No per-article skills were created.

## Material limits

Synthetic checks do not establish live database performance or installed application behavior. Existing bot databases receive indexes at next storage initialization. Running services and packaged applications were not restarted/rebuilt. API clients must obtain/pass revisions; direct legacy storage calls without revisions remain compatible and can blind-write. External editors ignoring locks are outside coordination. No automatic conflict merge; recovery is manual. Browser download initiation is not proof a file was saved. Windows locking was not exercised. Snapshot atomic visibility is not a power-loss durability guarantee. Cache limits entries, not bytes, and idle expiration cleanup is lazy.

## Deployment and history

Only ten selected Hub paths were deployed with backups and scoped installed-manifest hashes. Three preexisting learning override conflicts were retained; no broad release was applied. Application code is saved in scoped local history with no remote push. Context edits remain in their working trees where a clean pre-edit history baseline was not available; this avoids including unrelated older changes. Prior completed analytics task is preserved in a handoff.

## Contexts repaired

- `masha/ai/project-context.md`
- `zdorove-babushki/ai/project-context.md`
- `release-page-cardiology-center/ai/project-context.md`
- `release-page-laboratory-center/ai/project-context.md`
- `release-page-maxillofacial-surgery/ai/project-context.md`
- `release-page-head-neck-surgery/ai/project-context.md`
- `release-page-geriatric-center/ai/project-context.md`
- `release-page-endoscopy-center/ai/project-context.md`
- `release-page-nuclear-medicine/ai/project-context.md`
- `release-page-radiation-therapy/ai/project-context.md`
- `release-page-traumatology/ai/project-context.md`
- `release-page-pediatric-coloproctology/ai/project-context.md`
- `release-page-preventive-medicine/ai/project-context.md`
- `release-page-pediatric-urology/ai/project-context.md`
- `zdorove-businki/ai/project-context.md`
- `hadassah-analytics/ai/project-context.md`
- `hadassah-seo-audits/ai/project-context.md`
- `content-plan-release-backlog/ai/project-context.md`
- `hadassah-content-oncology/ai/project-context.md`
- `hadassah-content-weight-metabolism/ai/project-context.md`
- `hadassah-seo-audit-jul/ai/project-context.md`
- `ai-page-publishing/ai/project-context.md`
- `seo-hire-pitch/ai/project-context.md`
- `rolling-audio-recorder/ai/project-context.md`
- `hub-session-audit/ai/project-context.md`
- `sertraline-prescription/ai/project-context.md`
- `release-page-cardiovascular-surgery/ai/project-context.md`
- `seo-pages/ai/project-context.md`
- `release-page-stroke-center/ai/project-context.md`
- `release-page-cognitive-health-center/ai/project-context.md`
- `zdorove/ai/project-context.md`
- `release-page-rehabilitation/ai/project-context.md`
- `release-page-trichology/ai/project-context.md`
- `release-page-penile-prosthesis/ai/project-context.md`
- `release-page-varicocele/ai/project-context.md`
- `release-page-vasectomy-reversal/ai/project-context.md`
- `release-page-kidney-stones/ai/project-context.md`
- `release-page-emergency-urology/ai/project-context.md`
- `release-page-oncology-consilium/ai/project-context.md`
- `release-page-pediatric-rehabilitation/ai/project-context.md`
- `stranitsa-vyezdnoy-sluzhby/ai/project-context.md`
- `stranitsa-stomatologii/ai/project-context.md`
- `syomki/ai/project-context.md`
- `release-page-pediatric-neurology/ai/project-context.md`
- `stranitsa-plastiki-litsa/ai/project-context.md`
- `blok-keysov/ai/project-context.md`
- `stranitsa-plastiki-tela/ai/project-context.md`
- `zdorove-mamy/ai/project-context.md`
