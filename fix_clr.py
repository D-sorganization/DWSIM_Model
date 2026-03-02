with open("tests/conftest.py", "r") as f:
    text = f.read()
text = text.replace("import clr", "import clr  # noqa: F401")
with open("tests/conftest.py", "w") as f:
    f.write(text)
