from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv()

sandbox = Sandbox()
pytest_install = "pip install pytest"
# Start the command in the background
command = sandbox.commands.run(pytest_install, background=True)

project_dir = Path("20241117_134413")
for file in project_dir.glob("*.py"):
    sandbox.files.write(f"/project/{file.name}", file.read_text())
    print(f"Uploaded {file.name}")
test = sandbox.commands.run("pytest /project/", background=True)


# Get stdout and stderr from the command running in the background.
# You can run this code in a separate thread or use command.wait() to wait for the command to finish.
for stdout, stderr, _ in test:
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)

files = sandbox.files.list("/project/")
for file in files:
    print(file.name)
# Kill the command
command.kill()
test.kill()
