import html

def escape_python_code(code: str) -> str:
    """Escape Python code for XML storage"""
    return html.escape(code, quote=True)

def unescape_python_code(code: str) -> str:
    """Unescape Python code from XML storage"""
    return html.unescape(code) 