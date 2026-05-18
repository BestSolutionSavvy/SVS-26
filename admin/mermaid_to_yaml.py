"""Convert Mermaid state diagrams to YAML rule files."""
from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

import yaml

_TRANSITION_PATTERN = re.compile(
    r"^(?P<from>.+?)\s*-->\s*(?P<to>.+?)(?:\s*:\s*(?P<condition>.+))?$"
)


def _parse_metadata_block(lines: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Extract YAML metadata block from ``lines``.

    Args:
        lines: list of stripped lines to inspect

    Returns:
        Tuple of (metadata dict, remaining lines)
    """
    if not lines or lines[0] != '---':
        return {}, lines

    end_index = None
    for index in range(1, len(lines)):
        if lines[index] == '---':
            end_index = index
            break

    if end_index is None:
        return {}, lines

    metadata_text = '\n'.join(lines[1:end_index]).strip()
    metadata = yaml.safe_load(metadata_text) if metadata_text else {}
    if not isinstance(metadata, dict):
        metadata = {}

    return metadata, lines[end_index + 1:]


def _parse_transition(line: str) -> tuple[str, str, str | None] | None:
    """Parse a transition line.

    Args:
        line: single diagram line

    Returns:
        (from_state, to_state, condition) or None if not a transition
    """
    match = _TRANSITION_PATTERN.match(line)
    if match is None:
        return None
    from_state = match.group('from').strip()
    to_state = match.group('to').strip()
    condition = match.group('condition')
    return from_state, to_state, condition.strip() if condition else None


def _append_state(states: list[str], state: str) -> None:
    """Append state to list if not present and not the start marker."""
    if state and state != '[*]' and state not in states:
        states.append(state)


def _append_transition(transitions: list[dict[str, Any]], from_state: str, to_state: str, condition: str | None) -> None:
    """Add or merge a transition into the transitions list.

    Args:
        transitions: list to append/merge into
        from_state: source state
        to_state: destination state
        condition: optional condition string
    """
    if condition is None:
        transitions.append({'from': from_state, 'to': to_state})
        return

    for transition in transitions:
        if transition.get('from') == from_state and transition.get('to') == to_state:
            if 'condition' in transition:
                existing_condition = transition['condition']
                if existing_condition == condition:
                    return
                transition.pop('condition')
                transition['conditions'] = [existing_condition, condition]
                return
            if 'conditions' in transition:
                if condition not in transition['conditions']:
                    transition['conditions'].append(condition)
                return

    transitions.append(
        {'from': from_state, 'to': to_state, 'condition': condition})


def _format_scalar(value: Any) -> str:
    """Format a Python value into a YAML-friendly scalar string."""
    if isinstance(value, str):
        if re.fullmatch(r'[A-Za-z0-9_]+', value):
            return value
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _format_yaml(rule_data: dict[str, Any]) -> str:
    """Serialize rule data to YAML string.

    Args:
        rule_data: mapping with 'metadata' and 'state_machine' keys

    Returns:
        YAML formatted string ending with a newline
    """
    lines: list[str] = []

    metadata = rule_data.get('metadata', {}) or {}
    lines.append('metadata:')
    for key in ('title', 'severity', 'fine'):
        if key in metadata:
            lines.append(f'  {key}: {_format_scalar(metadata[key])}')

    state_machine = rule_data.get('state_machine', {}) or {}
    lines.append('state_machine:')
    lines.append(
        f'  direction: {_format_scalar(state_machine.get("direction", "TB"))}')
    lines.append(
        f'  initial_state: {_format_scalar(state_machine.get("initial_state", "start"))}')
    lines.append('  states:')
    for state in state_machine.get('states', []):
        lines.append(f'    - {_format_scalar(state)}')

    lines.append('  transitions:')
    for transition in state_machine.get('transitions', []):
        lines.append(
            f'    - from: {_format_scalar(transition.get("from", ""))}')
        lines.append(f'      to: {_format_scalar(transition.get("to", ""))}')
        if 'condition' in transition:
            lines.append(
                f'      condition: {_format_scalar(transition["condition"])}')
        elif 'conditions' in transition:
            lines.append('      conditions:')
            for condition in transition['conditions']:
                lines.append(f'        - {_format_scalar(condition)}')

    return '\n'.join(lines) + '\n'


def mermaid_to_yaml(mermaid_code: str, default_title: str | None = None) -> str:
    """Convert Mermaid state diagram text to a YAML rule string.

    Args:
        mermaid_code: Mermaid source text (may include metadata block)
        default_title: title to use if metadata is absent

    Returns:
        YAML document as a string

    Raises:
        ValueError: if no 'stateDiagram-v2' header is found
    """
    raw_lines = [line.strip()
                 for line in mermaid_code.splitlines() if line.strip()]
    metadata, lines = _parse_metadata_block(raw_lines)

    while lines and lines[0] != 'stateDiagram-v2':
        lines = lines[1:]

    if not lines:
        raise ValueError('Missing stateDiagram-v2 header')

    direction = 'TB'
    initial_state = 'start'
    states: list[str] = []
    transitions: list[dict[str, Any]] = []

    for line in lines[1:]:
        if line.startswith('direction '):
            direction = line.split(None, 1)[1].strip() or 'TB'
            continue

        parsed_transition = _parse_transition(line)
        if parsed_transition is None:
            continue

        from_state, to_state, condition = parsed_transition
        _append_transition(transitions, from_state, to_state, condition)

        if from_state == '[*]':
            initial_state = to_state
        else:
            _append_state(states, from_state)
        _append_state(states, to_state)

    if not metadata and default_title:
        metadata = {'title': default_title}
    elif default_title and 'title' not in metadata:
        metadata['title'] = default_title

    rule_data: dict[str, Any] = {
        'metadata': metadata,
        'state_machine': {
            'direction': direction,
            'initial_state': initial_state,
            'states': states,
            'transitions': transitions,
        },
    }
    return _format_yaml(rule_data)


def mermaid_to_yaml_file(mermaid_code: str, file_path: str | Path, default_title: str | None = None) -> Path:
    """Write converted YAML to file.

    Args:
        mermaid_code: Mermaid source text
        file_path: destination file path
        default_title: optional default title

    Returns:
        Path pointing to the written file
    """
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(mermaid_to_yaml(
        mermaid_code, default_title=default_title), encoding='utf-8')
    return target_path
