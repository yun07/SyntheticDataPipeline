import json
from pathlib import Path
import unreal

PARAM_TYPE_MAP = {
    bool: "bool_values",
    int: "int32_values",
    float: "float_values",
    str: "string_values",
}

def convert_json_parameters(raw_params: dict) -> dict:
    """將 JSON dict 轉換為 Map<FName, HoudiniParameterTuple>"""
    hda_params = {}
    for name, value in raw_params.items():
        v_type = bool if isinstance(value, bool) else type(value)
        attr_name = PARAM_TYPE_MAP.get(v_type)
        
        if not attr_name:
            unreal.log_warning(f"[ParseHDA] Unsupported type {v_type} for '{name}', skipping.")
            continue

        param = unreal.HoudiniParameterTuple()
        setattr(param, attr_name, [value])
        hda_params[unreal.Name(name)] = param

    return hda_params


def parse_and_execute(json_path_str: str, euw_asset_path: str = "/Game/EUW_SWE") -> bool:
    """主入口點：讀取 JSON 參數並推送到 EUW"""
    json_path = Path(json_path_str)
    if not json_path.exists():
        unreal.log_error(f"[ParseHDA] File not found: {json_path_str}")
        return False

    # 1. 讀取 JSON
    with open(json_path, "r", encoding="utf-8") as f:
        raw_params = json.load(f).get("parameters", {})

    # 2. 獲取 EUW 實例 (spawn_and_register_tab 自帶單例處理)
    euw_subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
    euw_asset = unreal.EditorAssetLibrary.load_asset(euw_asset_path.split(".")[0])
    
    widget_obj = euw_subsystem.find_utility_widget_from_blueprint(euw_asset) if hasattr(euw_subsystem, "find_utility_widget_from_blueprint") else None
    if not widget_obj:
        widget_obj = euw_subsystem.spawn_and_register_tab(euw_asset)

    if not widget_obj:
        unreal.log_error(f"[ParseHDA] Failed to get EUW: {euw_asset_path}")
        return False

    # 3. 呼叫 EUW UpdateParams (僅傳遞轉換後的 hda_params)
    try:
        hda_params = convert_json_parameters(raw_params)
        widget_obj.call_method("UpdateParams", (hda_params,))
        return True
    except Exception as e:
        unreal.log_error(f"[ParseHDA] Failed to update EUW: {e}")
        return False