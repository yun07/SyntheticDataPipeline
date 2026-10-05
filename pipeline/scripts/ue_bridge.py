import os
import sys
from pathlib import Path
import yaml
import unreal

# ==========================================
# Load Global Configuration with Fallback
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_YAML_PATH = SCRIPT_DIR / "env.yaml"
EXAMPLE_YAML_PATH = SCRIPT_DIR / "env.example.yaml"

def load_yaml(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[UE_BRIDGE] Warning: Failed to parse {path.name}: {e}")
    return {}

config = load_yaml(ENV_YAML_PATH) or load_yaml(EXAMPLE_YAML_PATH)

MAP_ASSET_PATH = config.get("MAP_ASSET_PATH")
EUW_ASSET_PATH = config.get("EUW_ASSET_PATH")
# ==========================================

print("[UE_BRIDGE] Python script bridge initialized.")

def load_target_map(map_path: str) -> bool:
    """Loads the specified Level map."""
    print(f"[UE_BRIDGE] Loading map: {map_path}")
    
    if not map_path or not unreal.EditorAssetLibrary.does_asset_exist(map_path):
        print(f"[UE_BRIDGE ERROR] Map asset invalid or not found: {map_path}")
        return False

    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if subsystem.load_level(map_path):
        print(f"[UE_BRIDGE] Map loaded successfully: {map_path}")
        return True
        
    print(f"[UE_BRIDGE ERROR] Failed to load map: {map_path}")
    return False

def run_render_from_bridge(render_path: str):
    try:
        if not load_target_map(MAP_ASSET_PATH):
            print("[UE_BRIDGE ERROR] Execution aborted due to map load failure.")
            return

        print(f"[UE_BRIDGE] Preparing render job. Target JSON: {render_path}")
        euw_subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
        euw_asset = unreal.EditorAssetLibrary.load_asset(EUW_ASSET_PATH)
        
        if not euw_asset:
            print(f"[UE_BRIDGE ERROR] EUW asset not found: {EUW_ASSET_PATH}")
            return

        widget_obj = euw_subsystem.spawn_and_register_tab(euw_asset)
        widget_obj.call_method("ExecuteSampleRender", (render_path,))
        print("[UE_BRIDGE] ExecuteSampleRender triggered successfully!")

    except Exception as e:
        print(f"[UE_BRIDGE EXCEPTION]: {e}")

if __name__ == "__main__":
    target_path = None

    if len(sys.argv) > 1:
        target_path = sys.argv[1]
        print(f"[UE_BRIDGE] Acquired JSON path from CLI sys.argv: {target_path}")
    elif os.getenv("RENDER_JSON_PATH"):
        target_path = os.getenv("RENDER_JSON_PATH")
        print(f"[UE_BRIDGE] Acquired JSON path from RENDER_JSON_PATH: {target_path}")

    if not target_path:
        print("[UE_BRIDGE ERROR] No JSON path provided via sys.argv or RENDER_JSON_PATH.")
        sys.exit(1)

    run_render_from_bridge(target_path)