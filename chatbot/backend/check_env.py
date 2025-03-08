import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# List installed packages
print("\nInstalled packages:")
import pkg_resources
for package in pkg_resources.working_set:
    print(f"{package.project_name}=={package.version}")
