from nicegui import ui
from pathlib import Path
import re
from typing import Optional

from mermaid_to_yaml import mermaid_to_yaml_file
from yaml_to_mermaid import yaml_to_mermaid

ui.add_css('./style.css')

content = {'code': ''}
rules_dir = Path('rules')
chart = None
rules_drawer = None
rules_list_container = None
new_rule_dialog = None
new_rule_name_input = None
info_dialog = None
current_rule_name = None
current_rule_path = None


def toggle_rules_drawer():
    """Toggle the rules drawer visibility"""
    if rules_drawer is not None:
        rules_drawer.toggle()


def close_rules_drawer():
    """Close the rules drawer"""
    if rules_drawer is not None:
        rules_drawer.hide()


def open_info_dialog() -> None:
    """Open the dialog showing available data fields"""
    if info_dialog is not None:
        info_dialog.open()


def set_current_rule(rule_name: Optional[str], file_path: Optional[Path]) -> None:
    """
    Set the currently active rule

    Parameters
    -------
    rule_name: Optional[str]
        name of the current rule (without extension)
    file_path: Optional[Path]
        path to the rule file
    """
    global current_rule_name, current_rule_path
    current_rule_name = rule_name
    current_rule_path = file_path


def new_rule_template(rule_name: str) -> str:
    """
    Generate a YAML template for a new rule with Mermaid state diagram

    Parameters
    -------
    rule_name: str
        name of the new rule (without extension)
    """
    return f"""---
title: {rule_name}
severity: 4
fine: 250
---
stateDiagram-v2
	direction TB
	[*] --> idle
"""


def get_rules_list():
    """Get list of all .yaml files in rules directory"""
    if not rules_dir.exists():
        return []
    return sorted([f.stem for f in rules_dir.glob('*.yaml')])


def render_rules_list() -> None:
    """Render the list of available rules in the drawer"""
    if rules_list_container is None:
        return
    rules_list_container.clear()
    rules_list = get_rules_list()
    with rules_list_container:
        if not rules_list:
            ui.label('No rules found').classes('text-sm text-gray-500')
            return
        for rule_name in rules_list:
            with ui.row().classes('w-full justify-between items-center mb-2 gap-2'):
                ui.button(rule_name).on_click(lambda r=rule_name: handle_rule_click(
                    r)).classes('flex-1 justify-start truncate')
                ui.button(icon='delete', color='negative', on_click=lambda r=rule_name: delete_rule(
                    r)).props('flat round dense')


def delete_rule(rule_name: str) -> None:
    """
    Delete a rule file

    Parameters
    -------
    rule_name: str
        name of the rule to delete (without extension)
    """
    file_path = rules_dir / f'{rule_name}.yaml'
    try:
        file_path.unlink()
        ui.notify(f'Deleted {rule_name}')
        if current_rule_name == rule_name:
            set_current_rule(None, None)
            content['code'] = ''
            editor.set_value('')
        render_rules_list()
    except Exception as e:
        ui.notify(f'Error deleting rule: {e}')


def open_new_rule_dialog() -> None:
    """Open the dialog for creating a new rule"""
    if new_rule_name_input is not None:
        new_rule_name_input.value = ''
    if new_rule_dialog is not None:
        new_rule_dialog.open()


def create_new_rule() -> None:
    """Create a new rule from user input and open in editor"""
    if new_rule_name_input is None:
        return
    raw_name = (new_rule_name_input.value or '').strip()
    rule_name = re.sub(r'[^A-Za-z0-9_-]+', '_', raw_name).strip('_')
    if not rule_name:
        ui.notify('Please enter a rule name')
        return
    file_path = rules_dir / f'{rule_name}.yaml'
    rules_dir.mkdir(parents=True, exist_ok=True)
    set_current_rule(rule_name, file_path)
    content['code'] = new_rule_template(rule_name)
    editor.set_value(content['code'])
    update_chart()
    close_rules_drawer()
    if new_rule_dialog is not None:
        new_rule_dialog.close()


def save_current_rule() -> None:
    """Save the current rule to a YAML file"""
    if current_rule_path is None:
        ui.notify('Create a new rule first with +')
        return
    rules_dir.mkdir(parents=True, exist_ok=True)
    saved_path = mermaid_to_yaml_file(
        content['code'], current_rule_path, default_title=current_rule_name)
    ui.notify(f'Saved {saved_path.name}')
    render_rules_list()


def load_rule(filename: str):
    """
    Load a YAML rule file and update the editor with Mermaid code

    Parameters
    -------
    filename: str
        name of the rule file to load (with extension)
    """
    filepath = rules_dir / filename
    try:
        mermaid_code = yaml_to_mermaid(filepath)
        content['code'] = mermaid_code
        set_current_rule(filepath.stem, filepath)
        editor.value = mermaid_code
        update_chart()
    except Exception as e:
        ui.notify(f'Error loading rule: {e}')


def handle_rule_click(rule_name: str):
    """
    Handle rule selection from the drawer

    Parameters
    -------
    rule_name: str
        name of the rule clicked
    """
    load_rule(f'{rule_name}.yaml')
    close_rules_drawer()


def update_chart():
    """Update the Mermaid chart preview with current content"""
    global chart
    if chart:
        chart.content = content['code']


ui.button(icon='menu', color='primary', on_click=toggle_rules_drawer)\
    .props('unelevated')\
    .classes('fixed top-2 left-2 z-50')

with ui.left_drawer(value=True).props('overlay bordered').classes('w-64 p-4 bg-slate-100') as rules_drawer:
    with ui.column().classes('w-full overflow-auto'):
        with ui.row().classes('w-full items-center justify-between mb-2'):
            ui.label('Rules').classes('text-h6 font-bold')
            with ui.row().classes('items-center gap-1'):
                ui.button(icon='add', on_click=open_new_rule_dialog).props(
                    'flat round dense').tooltip('New rule')
                ui.button(icon='close', on_click=close_rules_drawer).props(
                    'flat round dense')

        rules_list_container = ui.column().classes('w-full')
        render_rules_list()

new_rule_dialog = ui.dialog()
with new_rule_dialog:
    with ui.card().classes('w-96'):
        ui.label('Create new rule').classes('text-h6 font-bold')
        new_rule_name_input = ui.input(label='Rule name').classes('w-full')
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancel', on_click=new_rule_dialog.close).props('flat')
            ui.button('Create', color='primary', on_click=create_new_rule)

info_dialog = ui.dialog()
with info_dialog:
    with ui.card().classes('w-full max-w-2xl'):
        with ui.column().classes('w-full gap-4'):
            ui.label('Available Data Fields').classes('text-h6 font-bold')
            try:
                data_content = (Path(__file__).parent / 'data.md').read_text()
                escaped_content = data_content.replace('_', '\\_')
                ui.markdown(escaped_content).classes('overflow-auto max-h-96')
            except:
                ui.label('Error loading data fields')
            ui.button('Close', on_click=info_dialog.close).props(
                'flat').classes('self-end')


with ui.row().classes('w-full no-wrap h-screen overflow-hidden'):
    with ui.column().classes('w-1/2 pt-10 h-full flex flex-col overflow-hidden'):
        with ui.row().classes('w-full items-center justify-between mb-2'):
            ui.label('Editor Mermaid').classes('text-h6')
            with ui.row().classes('gap-2'):
                ui.button(icon='info', color='primary',
                          on_click=open_info_dialog).props('unelevated')
                ui.button(icon='save', color='secondary',
                          on_click=save_current_rule).props('unelevated')

        editor = ui.codemirror(
            value=content['code'],
            language='Markdown',
            theme='githubLight',
            line_wrapping=True,
        ).classes('w-full flex-1').style('min-height: 0; height: calc(100vh - 120px);')

        editor.bind_value(content, 'code')

    with ui.column().classes('w-1/2 h-full flex items-center justify-center overflow-hidden border-l border-gray-300'):
        with ui.column().classes('w-full h-full flex items-center justify-center overflow-hidden'):
            ui.label('Preview').classes('text-h6')

            chart = ui.mermaid(content['code']).classes(
                'mermaid-preview').style('min-height: 75vh; max-width: 95%;')

        editor.on_value_change(lambda _: update_chart())

ui.run(native=True, title='Admin Rule Editor',
       window_size=(1200, 700), favicon='favicon.ico')
