# server/scripts/migrate.py
"""
Database migration helper script
Usage:
    python scripts/migrate.py create "Description of change"
    python scripts/migrate.py upgrade
    python scripts/migrate.py downgrade
    python scripts/migrate.py current
"""
import sys
import os
import subprocess

def run_alembic(args):
    """Run alembic command"""
    cmd = ["alembic"] + args
    subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Provide migration description")
            sys.exit(1)
        message = sys.argv[2]
        run_alembic(["revision", "--autogenerate", "-m", message])
        
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_alembic(["upgrade", revision])
        
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        run_alembic(["downgrade", revision])
        
    elif command == "current":
        run_alembic(["current"])
        
    elif command == "history":
        run_alembic(["history"])
        
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)