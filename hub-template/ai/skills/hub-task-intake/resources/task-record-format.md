# Task record format

Use `Task ID:`, `Status:`, and `Due: YYYY-MM-DD`. Both legacy `due:` and
canonical `Due:` can be read, but new task writes use `Due:`. A date must be a
real calendar date. Current, future, and paused records keep their existing
status sets and must carry an ID belonging to their registered project.
