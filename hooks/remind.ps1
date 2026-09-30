# PowerShell twin of remind.sh for agents that run Windows hooks through
# PowerShell (Codex): the same line on answer length with every prompt.
[Console]::Out.WriteLine('{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"awesome-agents-md: answer in at most 35 words unless the user asks for an explanation; code, the commit proposal and warnings are not counted."}}')
