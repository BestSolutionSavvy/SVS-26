import yaml

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
    
def main():
    parsed_data = parse_yaml_file('./admin/rules/stop.yaml')
    print(parsed_data)
    
if __name__ == "__main__":    main()