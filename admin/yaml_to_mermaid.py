"""
Convert YAML rule files to Mermaid diagram code.
"""
import yaml
from pathlib import Path


def state_machine_to_mermaid(sm, metadata=None):
    """Convert state_machine YAML structure to Mermaid stateDiagram-v2 format
    
    Args:
        sm: Dictionary containing state_machine configuration
        metadata: Optional dictionary containing title, severity, fine
        
    Returns:
        String containing Mermaid diagram code
    """
    if not sm:
        return ''
    
    direction = sm.get('direction', 'TB')
    initial_state = sm.get('initial_state', 'start')
    transitions = sm.get('transitions', [])
    states = sm.get('states', [])
    
    lines = []
    
    if metadata:
        lines.append('---')
        if 'title' in metadata:
            lines.append(f'title: {metadata["title"]}')
        if 'severity' in metadata:
            lines.append(f'severity: {metadata["severity"]}')
        if 'fine' in metadata:
            lines.append(f'fine: {metadata["fine"]}')
        lines.append('---')
    
    lines.append('stateDiagram-v2')
    lines.append(f'\tdirection {direction}')
    
    lines.append(f'\t[*] --> {initial_state}')
    
    # Group transitions by their scope (parent state).
    # For qualified states like "intersection.warning", extract the parent "intersection".
    scope_transitions = {}
    top_level_transitions = []
    
    for trans in transitions:
        from_state = trans.get('from')
        to_state = trans.get('to')
        condition = trans.get('condition', '')
        conditions = trans.get('conditions', [])
        
        if not from_state or not to_state:
            continue
        
        # Determine the scope: check both from and to for nested states
        scope = None
        if '.' in from_state:
            scope = from_state.split('.')[0]
        elif '.' in to_state:
            scope = to_state.split('.')[0]
        
        # Skip top-level [*] transitions (already handled)
        if from_state == '[*]' and scope is None:
            continue
        
        trans_record = {
            'from': from_state,
            'to': to_state,
            'condition': condition,
            'conditions': conditions
        }
        
        if scope:
            if scope not in scope_transitions:
                scope_transitions[scope] = []
            scope_transitions[scope].append(trans_record)
        else:
            top_level_transitions.append(trans_record)
    
    # Render top-level transitions
    for trans in top_level_transitions:
        from_state = trans['from']
        to_state = trans['to']
        condition = trans['condition']
        conditions = trans['conditions']
        
        if condition:
            lines.append(f'\t{from_state} --> {to_state} : {condition}')
        elif conditions:
            for cond in conditions:
                lines.append(f'\t{from_state} --> {to_state} : {cond}')
        else:
            lines.append(f'\t{from_state} --> {to_state}')
    
    # Extract nested states (qualified with dot notation)
    nested_scopes = {}
    for state in states:
        if '.' in state:
            parts = state.split('.', 1)
            parent = parts[0]
            child = parts[1]
            if parent not in nested_scopes:
                nested_scopes[parent] = []
            if child not in nested_scopes[parent]:
                nested_scopes[parent].append(child)
    
    # Render nested state blocks
    for parent in sorted(nested_scopes.keys()):
        children = nested_scopes[parent]
        lines.append(f'\tstate {parent} {{')
        
        # Render transitions within this scope
        if parent in scope_transitions:
            for trans in scope_transitions[parent]:
                from_state = trans['from']
                to_state = trans['to']
                
                # Handle display conversion for nested states
                # If from_state is [*] or top-level, keep it as [*] (entry point)
                if from_state == '[*]':
                    from_display = '[*]'
                elif '.' in from_state:
                    # Remove parent prefix for display within scope
                    from_display = from_state.split('.', 1)[1]
                    # But if it's parent.start, convert to [*]
                    if from_display == 'start':
                        from_display = '[*]'
                else:
                    from_display = from_state
                
                # Same for to_state
                if to_state == '[*]':
                    to_display = '[*]'
                elif '.' in to_state:
                    # Remove parent prefix for display within scope
                    to_display = to_state.split('.', 1)[1]
                    # But if it's parent.end, convert to [*]
                    if to_display == 'end':
                        to_display = '[*]'
                else:
                    to_display = to_state
                
                condition = trans['condition']
                conditions = trans['conditions']
                
                if condition:
                    lines.append(f'\t\t{from_display} --> {to_display} : {condition}')
                elif conditions:
                    for cond in conditions:
                        lines.append(f'\t\t{from_display} --> {to_display} : {cond}')
                else:
                    lines.append(f'\t\t{from_display} --> {to_display}')
        
        lines.append(f'\t}}')
    
    return '\n'.join(lines)


def load_yaml_rule(filepath):
    """Load a YAML rule file and parse it
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        Tuple of (metadata, state_machine) or (None, None) if error
    """
    try:
        with open(filepath, 'r') as f:
            rule_data = yaml.safe_load(f)
        
        if rule_data and 'state_machine' in rule_data:
            metadata = rule_data.get('metadata', {})
            state_machine = rule_data['state_machine']
            return metadata, state_machine
        return None, None
    except Exception as e:
        raise ValueError(f'Error loading YAML file: {e}')


def yaml_to_mermaid(filepath):
    """Load a YAML rule file and convert to Mermaid diagram code
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        String containing Mermaid diagram code, or empty string if error
    """
    try:
        metadata, state_machine = load_yaml_rule(filepath)
        if state_machine:
            return state_machine_to_mermaid(state_machine, metadata)
        return ''
    except Exception as e:
        raise ValueError(f'Error converting YAML to Mermaid: {e}')
