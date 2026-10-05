import sys
import os
import argparse
import unreal

def parse_args():
    parser = argparse.ArgumentParser(description="Generic Asset Importer for Unreal Engine")
    
    # 必需參數：源文件路徑
    parser.add_argument(
        "FilePath", 
        type=str, 
        help="Full path to the source file (e.g., 'D:/HDA/building.hda')"
    )
    
    # 可選參數：Content Browser 目標路徑 (預設為 /Game/HDAs)
    parser.add_argument(
        "ContentBrowserPath", 
        type=str, 
        nargs="?", 
        default="/Game/HDAs", 
        help="Target folder in Content Browser (e.g., '/Game/HDAs')"
    )
    
    # 可選參數：指定 Content Browser 入面嘅 Asset 名稱
    parser.add_argument(
        "NameInContentBrowser", 
        type=str, 
        nargs="?", 
        default=None, 
        help="Optional custom asset name. If omitted, uses source file name."
    )

    # 處理 Unreal command line 傳入時可能帶有嘅前綴參數
    args, unknown = parser.parse_known_args()
    return args

def sanitize_destination_path(path: str) -> str:
    """確保 Content Browser 路徑格式正確"""
    path = path.replace("\\", "/")
    if not path.startswith("/"):
        path = "/" + path
    if not path.startswith("/Game"):
        path = "/Game" + path if path.startswith("/") else "/Game/" + path
    return path.rstrip("/")

def import_asset(file_path: str, destination_path: str, custom_name: str = None) -> bool:
    # 1. 檢查檔案是否存在
    if not os.path.exists(file_path):
        unreal.log_error(f"[Importer] File does not exist: {file_path}")
        return False

    destination_path = sanitize_destination_path(destination_path)
    file_dir, full_filename = os.path.split(file_path)
    filename_without_ext, ext = os.path.splitext(full_filename)

    # 決定最終 Asset 名稱
    target_name = custom_name if custom_name else filename_without_ext

    # 2. 設定 AssetImportTask
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', file_path)
    task.set_editor_property('destination_path', destination_path)
    task.set_editor_property('destination_name', target_name)
    task.set_editor_property('automated', True)            # 靜默執行
    task.set_editor_property('save', True)                 # Import 後自動 Save .uasset
    task.set_editor_property('replace_existing', True)     # 若已有同名 Asset 則覆蓋

    # 3. 執行 Import
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    # 4. 驗證結果
    imported_objects = task.get_editor_property('imported_object_paths')
    if imported_objects and len(imported_objects) > 0:
        unreal.log(f"[Importer] Successfully imported asset to: {imported_objects[0]}")
        return True
    else:
        unreal.log_error(f"[Importer] Failed to import asset from: {file_path}")
        return False

if __name__ == "__main__":
    args = parse_args()
    
    unreal.log(f"[Importer] Starting import with args:")
    unreal.log(f"  - FilePath: {args.FilePath}")
    unreal.log(f"  - ContentBrowserPath: {args.ContentBrowserPath}")
    unreal.log(f"  - NameInContentBrowser: {args.NameInContentBrowser}")

    success = import_asset(
        file_path=args.FilePath,
        destination_path=args.ContentBrowserPath,
        custom_name=args.NameInContentBrowser
    )
    
    if not success:
        sys.exit(1)