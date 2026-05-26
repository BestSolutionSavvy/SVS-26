import yaml

from models.rule import Rule
from models.state import State
from models.transition import Transition


def parse_yaml(content: str) -> dict:
    """Parse YAML content and return a dictionary"""
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return {}


def parse_yaml_file(file_path: str) -> dict:
    """Parse a YAML file and return a dictionary"""
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return {}


def parse_rule_file(file_path: str) -> Rule:
    """Parse a YAML file and return a Rule object"""
    data = parse_yaml_file(file_path)
    if not data:
        return None
    state_machine = data.get('state_machine', {})
    state_names = set(state_machine.get('states', []))
    states_dict = {name: State(name) for name in state_names}
    transitions = []
    for t in state_machine.get('transitions', []):
        from_name = t.get('from', '')
        to_name = t.get('to', '')
        if from_name != "[*]":
            if from_name not in states_dict:
                states_dict[from_name] = State(from_name)
            if to_name not in states_dict:
                states_dict[to_name] = State(to_name)
            transitions.append(Transition(
                condition=t.get('condition', ''),
                source=states_dict[from_name],
                target=states_dict[to_name]
            ))
    
    return Rule(
        name=data.get('metadata', {}).get('title', 'Unnamed Rule'),
        constants=data.get('metadata', {}).get('constants', {}),
        transitions=transitions
    )
    

if __name__ == "__main__":
    parsed_data = parse_rule_file('./admin/rules/lane_keeping.yaml')
    print(parsed_data)
    print(f"Initial state: {parsed_data.initial_state}")
    def print_transitions(state, visited=None):
        if visited is None:
            visited = set()
        if state.name in visited:
            return
        visited.add(state.name)
        print(f"Transitions from {state.name}:")
        for t in parsed_data.transitions_from(state):
            print(f"  -> {t.target.name} (condition: {t.condition if t.condition else 'always'})")
            print_transitions(t.target, visited)
            
    print_transitions(parsed_data.initial_state)
