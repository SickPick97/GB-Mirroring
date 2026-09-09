"""Bootstrap for the embedded Python's isolated sys.path."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from link_bench import main
sys.exit(main())
