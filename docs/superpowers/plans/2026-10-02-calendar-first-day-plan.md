# Calendar-first day planning

Approved user design, 2026-10-02: the user arranges Calendar first; requested
planning synchronizes task times before composition; joint edits are verified
afterwards. Output has exactly current calendar, synchronization, overdue tasks
(in that order). No daily automation or reminder. Due and completion remain
user decisions. Existing Calendar, canonical task, learning and privacy rules stay.

Implementation plan:
1. Update the day-plan validator tests; verify the old validator rejects the new format.
2. Update scenario, planning rules, router and discovery-warning placement together.
3. Make Calendar authoritative for unambiguous linked task times; reload records
   before composing; keep deadline warnings and partial-access safeguards.
4. Preserve learning and context inputs as analysis without deleted output sections.
5. Run output and scenario checks, consistency and module boundary checks.
6. Preview the installed Hub update, inspect exact replacements and apply the
   same reviewed plan hash; verify installed rules and registry afterwards.

Scope excludes changes to Calendar events, other projects, background jobs,
matching algorithms, and automatic deadline changes.
