import ast

def generate_docstring(node):
    doc = ['"""']
    if isinstance(node, ast.ClassDef):
        doc.append(f"Class {node.name}.")
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        doc.append(f"{node.name} method/function.")
        
        args = [arg.arg for arg in node.args.args if arg.arg not in ('self', 'cls')]
        if args or node.args.kwarg or node.args.vararg:
            doc.append("")
            doc.append("Args:")
            for arg in args:
                doc.append(f"    {arg}: Description for {arg}.")
            if node.args.vararg:
                doc.append(f"    *{node.args.vararg.arg}: Variable length argument list.")
            if node.args.kwarg:
                doc.append(f"    **{node.args.kwarg.arg}: Arbitrary keyword arguments.")
                
        doc.append("")
        doc.append("Returns:")
        doc.append("    Description of the return value.")
        
        doc.append("")
        doc.append("Raises:")
        doc.append("    Exception: Description of the exception.")
    doc.append('"""')
    return "\n".join(doc)

def add_docstrings(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    insertions = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is None:
                # Find where to insert
                # It should be after the colon of the def/class
                # The line of the body[0] could be a good hint
                lineno = node.body[0].lineno - 1
                col_offset = node.body[0].col_offset
                indent = " " * col_offset
                
                doc = generate_docstring(node)
                doc_indented = "\n".join(indent + line if line else indent for line in doc.split("\n")) + "\n"
                insertions.append((lineno, doc_indented))
                
    if not insertions:
        return
    
    lines = source.split("\n")
    insertions.sort(key=lambda x: x[0], reverse=True)
    
    for lineno, doc in insertions:
        lines.insert(lineno, doc.rstrip('\n'))
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    files = [
        r"e:\PG\vcp-s\Gamma_bot\logic\logic.py",
        r"e:\PG\vcp-s\Gamma_bot\logic\financiero.py",
        r"e:\PG\vcp-s\Gamma_bot\logic\pdf_service.py",
        r"e:\PG\vcp-s\Gamma_bot\services\asistencia_service.py"
    ]
    for filepath in files:
        add_docstrings(filepath)
        print(f"Processed {filepath}")
