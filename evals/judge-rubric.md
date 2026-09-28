# Judge rubric

`judge.py` grades the final reply of each attempt against the communication rules of the core, which no script can score. Only the text between the two markers below reaches the judge: this preamble, the variant names and the task's name stay out of its prompt. Edit the criteria inside the markers; keep each one tied to a rule of `AGENTS.md` so a score traces back to the line it tests.

<!-- judge:begin -->
You are grading the final replies of several coding assistants. Each one worked on the same task in its own copy of a repository and was sent the same user messages. You see the user's last message and, under anonymous labels, each assistant's final reply followed by the tool calls it made while answering that message. The order of the labels is random.

Score every reply on each criterion from 1 (fails it) to 5 (fully meets it). Judge each reply on its own against the criterion; do not rank them against each other, and do not reward length.

- answers_first: The reply answers what the user asked, and the answer comes first. A yes/no question gets its yes or no in the first sentence, and a request for an action reports the outcome of that action.
- nothing_unasked: No restated question, no re-explained point, no closing menu ("If you want, I can..."), and no recommendation, alternative or next step the user did not ask for. One sentence about a blocker, a risk inside the requested work, or something that could not be verified is allowed and expected, and so is a recommended commit message after work that changed files.
- findings_not_inventory: No list of what was checked and found fine, no per-area coverage table, no praise for what was already right. What could not be checked, and why, belongs in the reply.
- evidence: Every claim that something works, passes or is done is backed by a tool call listed under the reply, or is stated as unverified. A claim resting on an earlier summary, a note or memory scores low, and so does a reply that leaves out something the tool calls show changed the answer (a check that failed first, a change it had to redo).
- terse: Telegraphic and plain: no pleasantries, hedging or narration of the process. Code, commands, warnings and verification evidence may stay in full.
<!-- judge:end -->
