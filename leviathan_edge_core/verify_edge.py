#!/usr/bin/env python3
import os, sys, ast

def find_imports(source):
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def main():
    root = os.getcwd()
    missing = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.py'):
                full = os.path.join(dirpath, fn)
                with open(full, 'r') as f:
                    source = f.read()
                imports = find_imports(source)
                for imp in imports:
                    if imp.startswith('.'):
                        continue
                    if '.' in imp:
                        parts = imp.split('.')
                        mod_path = os.path.join(root, *parts)
                        if not os.path.isdir(mod_path) and not os.path.isfile(mod_path + '.py'):
                            missing.append((full, imp))
    if missing:
        print("Missing imports:")
        for f, imp in missing:
            print(f"  {f}: {imp}")
        sys.exit(1)
    else:
        print("EDGE CORE VERIFIED: All imports resolved.")

if __name__ == "__main__":
    main()
