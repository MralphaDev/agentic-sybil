import ast
import re
import sys
from pathlib import Path

root = Path("backend")
req_file = root / "requirements.txt"

stdlib = sys.stdlib_module_names
requirements = set()

if req_file.exists():
    for line in req_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(("-", "git+")):
            name = re.split(r"[<>=!~;\[]", line)[0].strip()
            if name:
                requirements.add(re.sub(r"[-_.]+", "-", name).lower())

imports = {}

for file in (root / "app").rglob("*.py"):
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"PARSE ERROR: {file}: {exc}")
        continue

    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]

        for name in names:
            if name not in stdlib and name != "app":
                imports.setdefault(name, set()).add(str(file))

print("\n=== THIRD-PARTY / EXTERNAL IMPORTS ===")
for name in sorted(imports):
    print(f"{name}: {', '.join(sorted(imports[name])[:3])}")

print("\n=== CURRENT REQUIREMENTS.TXT ===")
for name in sorted(requirements):
    print(name)

print("\n=== KNOWN LIKELY MISSING DEPENDENCIES ===")
aliases = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "multipart": "python-multipart",
    "psycopg2": "psycopg2-binary",
    "fitz": "pymupdf",
    "langchain_openai": "langchain-openai",
    "langchain_core": "langchain-core",
    "langgraph": "langgraph",
    "pm4py": "pm4py",
    "matplotlib": "matplotlib",
}

for module in sorted(imports):
    dist = aliases.get(module, module)
    normalized = re.sub(r"[-_.]+", "-", dist).lower()
    if normalized not in requirements:
        print(f"CHECK: {module} -> possible requirement: {dist}")
