"""
Convert YAML rule files to Mermaid diagram code.
"""
import yaml


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
    
    lines = []
    
    if metadata:
        lines.append('---')
        # Dump metadata using YAML to preserve constants and quoting
        md_text = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
        if md_text:
            lines.extend(md_text.splitlines())
        lines.append('---')
    
    lines.append('stateDiagram-v2')
    lines.append(f'\tdirection {direction}')
    lines.append(f'\t[*] --> {initial_state}')
    
    for trans in transitions:
        from_state = trans.get('from')
        to_state = trans.get('to')
        condition = trans.get('condition', '')
        conditions = trans.get('conditions', [])
        
        if not from_state or not to_state:
            continue
        
        # Skip [*] transitions (already handled above)
        if from_state == '[*]':
            continue
        
        if condition:
            lines.append(f'\t{from_state} --> {to_state} : {condition}')
        elif conditions:
            for cond in conditions:
                lines.append(f'\t{from_state} --> {to_state} : {cond}')
        else:
            lines.append(f'\t{from_state} --> {to_state}')
    
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
