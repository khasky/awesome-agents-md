# Debug escalation ladder

Read this when a fix has failed twice, the same error keeps returning, or a debugging session is going in circles. The core carries the short form; this is the full ladder.

- Read the exact error message and the logs before guessing — the answer is usually printed. Quote the decisive line, not the whole dump.
- Form 3 different hypotheses before testing any. Test the most likely first — and design the check that would disprove it, not confirm it. Reverse the assumption too: "problem is in A" → test "problem is NOT in A".
- Trace backward to where the bad value originates, not where it surfaces; diff against the nearest working case (last green commit, the sibling endpoint that works, the passing test).
- Escalation ladder: 2nd failure → change methodology, not parameters; 3+ failed fixes → question the architecture, not the code.
- "Tried everything" requires listing the attempts; fewer than 3 distinct approaches = not exhausted.
- Use available tools instead of asking the user to debug manually; no "environment issue" claims without evidence.
- A fix that can't explain the original symptom is a coincidence, not a fix: state the mechanism ("X returned null because Y") before claiming resolution.
- Close the loop: re-run the original failing scenario and show it passing (core Verification gate).
