#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skills_dir="$repo_root/skills"

legacy_pattern='AskQuestion|create-skill|(^|[^[:alnum:]_-])/?deslop([^[:alnum:]_-]|$)|control-cli|control-ui|autopilot-stack'

if grep -rn -i -e "$legacy_pattern" "$skills_dir"; then
	printf '%s\n' 'legacy port references remain' >&2
	exit 1
fi

for skill in writing-for-agents unslop playwright research; do
	test -f "$skills_dir/$skill/SKILL.md" || {
		printf '%s\n' "missing replacement skill: $skill" >&2
		exit 1
	}
done

test ! -e "$skills_dir/poteto-mode/playbooks/autopilot-stack.md"

missing=0
for reference in $(sed -n 's/.*`\(playbooks\/[^`]*\.md\)`.*/\1/p' "$skills_dir/poteto-mode/SKILL.md"); do
	if test ! -f "$skills_dir/poteto-mode/$reference"; then
		printf '%s\n' "missing routed playbook: $reference" >&2
		missing=1
	fi
done
test "$missing" -eq 0

grep -r -q '^description: .*use research for external libraries, API specifications, or general technical facts' "$skills_dir/why/SKILL.md"

printf '%s\n' 'ported skill references verified'
