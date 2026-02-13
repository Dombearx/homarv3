from pathlib import Path

SRC_DIR = Path(__file__).parent
WORKFLOW_DIR = SRC_DIR / "workflows"
WORKFLOW_FILE = WORKFLOW_DIR / "workflow.json"
IMAGE_GENERATION_OUTPUT_DIR = SRC_DIR.parent / "displayer/media/images"
