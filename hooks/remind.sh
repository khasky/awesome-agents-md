#!/usr/bin/env bash
# UserPromptSubmit hook: one line on answer length with every prompt. Deep in a
# long session the core loaded at start carries less weight; a reminder costs a
# few tokens per prompt, where sending a long answer back pays for it twice.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"awesome-agents-md: answer in at most 35 words unless the user asks for an explanation; code, the commit proposal and warnings are not counted."}}'
