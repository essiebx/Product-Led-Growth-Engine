import sys
import os

# Ensure the project root is always on sys.path so that
# 'from scripts.xxx import ...' resolves correctly in both
# the terminal (pytest) and in the VS Code language server.
sys.path.insert(0, os.path.dirname(__file__))
