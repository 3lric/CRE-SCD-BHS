import json

def load_themes():
    """Loads the themes from the themes.json file."""
    try:
        with open('themes.json', 'r') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"Error loading themes: {e}")
        return {}
    except FileNotFoundError:
        print("themes.json not found.")
        return {}

def save_theme(theme_name, theme_style):
    """Saves the given theme to the themes.json file."""
    themes = load_themes()
    themes[theme_name] = theme_style
    with open('themes.json', 'w') as file:
        json.dump(themes, file, indent=4)

def dict_to_stylesheet(theme_dict):
    """Converts a theme dictionary to a stylesheet string."""
    if isinstance(theme_dict, str):
        return theme_dict
    stylesheet = ""
    for widget, properties in theme_dict.items():
        widget_style = f"{widget} {{\n"
        for property_name, value in properties.items():
            widget_style += f"    {property_name}: {value};\n"
        widget_style += "}\n"
        stylesheet += widget_style
    return stylesheet
