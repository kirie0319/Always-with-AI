# debug_import.py
import sys
print(sys.path)
try:
    import tasks
    print("tasks imported successfully")
except ImportError as e:
    print(f"Failed to import tasks: {e}")