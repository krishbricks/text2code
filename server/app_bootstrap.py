"""Bootstrap app that loads actual code from UC Volume."""
import sys
import os

# Temporarily suppress startup messages
import io
old_stdout = sys.stdout
old_stderr = sys.stderr

try:
    # Load the actual app code from the volume
    from databricks.sdk import WorkspaceClient
    
    w = WorkspaceClient()
    volume_app_path = "/Volumes/krish_catalog/krish_schema/test_vol/app_code/app.py"
    
    print(f"Loading app code from {volume_app_path}...", file=old_stdout)
    
    response = w.files.download(volume_app_path)
    
    # Read the app code
    if hasattr(response, 'contents'):
        app_code = response.contents.decode('utf-8')
    else:
        app_code = response.text
    
    print(f"Loaded {len(app_code)} bytes of app code", file=old_stdout)
    
    # Execute the app code in this namespace
    exec(app_code, globals())
    
    print(f"✅ App loaded successfully from volume!", file=old_stdout)
    
except Exception as e:
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    print(f"ERROR loading app from volume: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    raise
finally:
    sys.stdout = old_stdout
    sys.stderr = old_stderr

# The app FastAPI object should now be available from the executed code
