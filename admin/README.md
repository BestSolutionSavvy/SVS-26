Admin Rule Editor
=================

Overview
-----------------
This small tool provides a lightweight desktop interface (NiceGUI) to
create, edit and save road rules modelled as state machines. The editor uses Mermaid diagrams for a visual definition of states and converts them into YAML files with a minimal structure containing ``metadata`` and ``state_machine`` sections.

This is part of a larger project to manage and apply road rules
in the CARLA simulator, but the editor itself is standalone and can be used independently to create YAML rule files.

Main components
---------------
- `rule_editor.py` – User interface (NiceGUI)
  - left panel: drawer with the list of rules (.yaml)
  - editor: CodeMirror instance to edit/display Mermaid code
  - preview: Mermaid rendering of the editor content
  - create/save: dialog to create a new rule and save to file

- `mermaid_to_yaml.py` – parser/serializer
  - Public functions:
    - `mermaid_to_yaml(mermaid_code, default_title=None)` -> str
      Converts Mermaid text (optionally preceded by a YAML metadata
      block) into a YAML string containing `metadata` and
      `state_machine`.
    - `mermaid_to_yaml_file(mermaid_code, file_path, default_title=None)` -> Path
      Writes the YAML to disk (UTF-8) and returns the written `Path`.
  - Private helpers: metadata block parsing, transition parsing and
    normalization of states/transitions.

- `yaml_to_mermaid.py` – reverse converter used to load existing rules and present them as Mermaid diagrams in the editor.
  - `yaml_to_mermaid(filepath)` reads a YAML rule and returns the
    Mermaid text to display in the editor/preview.

- `rules/` – directory where YAML rule files are stored (each rule is
  `<name>.yaml`).

- `style.css`, `favicon.ico`, etc. – static assets for the UI.

How it works (quick flow)
------------------------
1. The user selects a rule from the drawer or creates a new rule.
2. Mermaid code is loaded into the editor (or generated from a
   template).
3. The Mermaid preview updates in real time.
4. Pressing Save converts the Mermaid text to YAML and writes
   `rules/<name>.yaml` using `mermaid_to_yaml_file`.
5. YAML files can be reopened and converted back to Mermaid via
   `yaml_to_mermaid`.

Running the app
---------------
Prerequisites: Python 3.10+, and the packages listed in
`requirements.txt` (admin/requirements.txt includes `nicegui`, `pyyaml`,
`pywebview`).

Quick example (from the `admin/` folder):

```bash
# activate environment if needed (example for Conda):
# conda activate ./.conda

pip install -r requirements.txt
python rule_editor.py
```
