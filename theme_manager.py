import os
import sys
import json

def get_app_path(subdirectory=""):
    """Get the application path, accounting for PyInstaller's temporary directory."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    if subdirectory:
        return os.path.join(base_path, subdirectory)
    return base_path

def load_themes():
    """Loads themes from the themes.json file."""
    json_dir = get_app_path("json")
    themes_path = os.path.join(json_dir, 'themes.json')
    if not os.path.exists(themes_path):
        print("themes.json not found.")
        return {}
    with open(themes_path, 'r') as file:
        themes = json.load(file)
    return themes

def dict_to_stylesheet(style_dict):
    """Converts a dictionary of styles into a stylesheet string."""
    stylesheet = ""
    for widget, styles in style_dict.items():
        styles_str = "; ".join(f"{k}: {v}" for k, v in styles.items())
        stylesheet += f"{widget} {{ {styles_str} }}\n"
    return stylesheet
