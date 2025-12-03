"""
Cursor Workspace Path Updater
==============================

Used to preserve Cursor's chat history when a folder name is changed.

Usage:
    python update_cursor_workspace_path_EN.py

The script automatically:
1. Detects the current folder name
2. Finds the workspace associated with this folder in Cursor's workspace storage
3. Detects the old folder name (from workspace.json or state.vscdb)
4. Updates all path references with the new folder name
"""

import sqlite3
import os
import json
import sys
import shutil
from pathlib import Path

# Cursor workspace storage path (Windows)
CURSOR_STORAGE = os.path.join(
    os.path.expanduser('~'),
    'AppData', 'Roaming', 'Cursor', 'User', 'workspaceStorage'
)

# Alternative paths for Mac/Linux
if not os.path.exists(CURSOR_STORAGE):
    if sys.platform == 'darwin':  # macOS
        CURSOR_STORAGE = os.path.join(
            os.path.expanduser('~'),
            'Library', 'Application Support', 'Cursor', 'User', 'workspaceStorage'
        )
    elif sys.platform.startswith('linux'):  # Linux
        CURSOR_STORAGE = os.path.join(
            os.path.expanduser('~'),
            '.config', 'Cursor', 'User', 'workspaceStorage'
        )


def find_workspace_by_path(target_path, folder_name_hint=None):
    """Find workspace by a specific path - full path match is prioritized"""
    if not os.path.exists(CURSOR_STORAGE):
        return None
    
    try:
        target_path_normalized = str(Path(target_path).resolve())
        target_parent = str(Path(target_path).parent)
        target_folder = os.path.basename(target_path)
    except:
        target_path_normalized = target_path
        target_parent = os.path.dirname(target_path)
        target_folder = os.path.basename(target_path)
    
    # Check all workspace folders
    for folder in os.listdir(CURSOR_STORAGE):
        folder_path = os.path.join(CURSOR_STORAGE, folder)
        if not os.path.isdir(folder_path):
            continue
        
        workspace_json = os.path.join(folder_path, 'workspace.json')
        state_db = os.path.join(folder_path, 'state.vscdb')
        
        # Check from workspace.json (MOST RELIABLE METHOD)
        if os.path.exists(workspace_json):
            try:
                with open(workspace_json, 'r', encoding='utf-8') as f:
                    workspace_data = json.load(f)
                
                folder_uri = workspace_data.get('folder', '')
                
                if not folder_uri:
                    continue
                
                # Extract path from URI
                workspace_path = None
                if folder_uri.startswith('file:///'):
                    workspace_path = folder_uri.replace('file:///', '').replace('%3A', ':')
                else:
                    workspace_path = folder_uri
                
                # Normalize paths
                try:
                    workspace_path_normalized = str(Path(workspace_path).resolve())
                except:
                    workspace_path_normalized = workspace_path
                
                # Paths match exactly
                if workspace_path_normalized.lower() == target_path_normalized.lower():
                    return folder, state_db, workspace_json, folder_uri
                        
            except Exception as e:
                pass
        
        # Search for full path in state.vscdb (if workspace.json didn't match)
        if os.path.exists(state_db):
            try:
                conn = sqlite3.connect(state_db)
                cursor = conn.cursor()
                
                # First search for full path
                cursor.execute("SELECT COUNT(*) FROM ItemTable WHERE value LIKE ?", 
                             (f'%{target_path_normalized}%',))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    conn.close()
                    workspace_json_path = workspace_json if os.path.exists(workspace_json) else None
                    folder_uri = None
                    if workspace_json_path:
                        try:
                            with open(workspace_json_path, 'r', encoding='utf-8') as f:
                                workspace_data = json.load(f)
                            folder_uri = workspace_data.get('folder', '')
                        except:
                            pass
                    return folder, state_db, workspace_json_path, folder_uri
                
                # If full path not found, search for parent + folder name combination
                if folder_name_hint:
                    # Search for parent path and folder name together
                    search_pattern = f'%{target_parent}%{target_folder}%'
                    cursor.execute("SELECT COUNT(*) FROM ItemTable WHERE value LIKE ?", 
                                 (search_pattern,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        conn.close()
                        workspace_json_path = workspace_json if os.path.exists(workspace_json) else None
                        folder_uri = None
                        if workspace_json_path:
                            try:
                                with open(workspace_json_path, 'r', encoding='utf-8') as f:
                                    workspace_data = json.load(f)
                                folder_uri = workspace_data.get('folder', '')
                            except:
                                pass
                        return folder, state_db, workspace_json_path, folder_uri
                
                conn.close()
            except:
                pass
    
    return None


def find_workspace_by_current_folder(current_path):
    """Find workspace for current folder (new workspace)"""
    current_folder = os.path.basename(current_path)
    
    # First search with full path
    result = find_workspace_by_path(current_path)
    if result:
        return result
    
    # If not found, search with folder name
    return find_workspace_by_path(current_path, current_folder)


def copy_state_db(source_db_path, target_db_path):
    """Copy state.vscdb file from old workspace to new workspace"""
    if not os.path.exists(source_db_path):
        print(f"⚠️  Source state.vscdb not found: {source_db_path}")
        return False
    
    try:
        # Get source file info
        source_size = os.path.getsize(source_db_path)
        print(f"📊 Source file size: {source_size:,} bytes")
        
        # Check if ItemTable exists in source file
        try:
            conn = sqlite3.connect(source_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            has_itemtable = cursor.fetchone() is not None
            if has_itemtable:
                cursor.execute("SELECT COUNT(*) FROM ItemTable")
                item_count = cursor.fetchone()[0]
                print(f"📋 Source file has ItemTable ({item_count} records)")
            else:
                print(f"⚠️  ItemTable not found in source file!")
            conn.close()
        except Exception as e:
            print(f"⚠️  Source file check error: {e}")
        
        # Create target directory (if it doesn't exist)
        target_dir = os.path.dirname(target_db_path)
        os.makedirs(target_dir, exist_ok=True)
        
        # Backup (if exists)
        if os.path.exists(target_db_path):
            backup_path = target_db_path + '.backup'
            shutil.copy2(target_db_path, backup_path)
            print(f"📦 Existing state.vscdb backed up: {backup_path}")
        
        # Copy
        print(f"📋 Starting copy operation...")
        shutil.copy2(source_db_path, target_db_path)
        
        # Verify copy
        if not os.path.exists(target_db_path):
            print(f"❌ Target file could not be created!")
            return False
        
        target_size = os.path.getsize(target_db_path)
        print(f"📊 Target file size: {target_size:,} bytes")
        
        if source_size != target_size:
            print(f"❌ File sizes don't match! (Source: {source_size}, Target: {target_size})")
            return False
        
        # Check if ItemTable exists in target file
        try:
            conn = sqlite3.connect(target_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            has_itemtable = cursor.fetchone() is not None
            if has_itemtable:
                cursor.execute("SELECT COUNT(*) FROM ItemTable")
                item_count = cursor.fetchone()[0]
                print(f"✅ Target file has ItemTable ({item_count} records)")
            else:
                print(f"❌ ItemTable not found in target file!")
                conn.close()
                return False
            conn.close()
        except Exception as e:
            print(f"❌ Target file check error: {e}")
            return False
        
        print(f"✅ state.vscdb successfully copied and verified")
        print(f"   Source: {os.path.basename(os.path.dirname(source_db_path))}")
        print(f"   Target: {os.path.basename(os.path.dirname(target_db_path))}")
        return True
    except Exception as e:
        print(f"❌ state.vscdb copy error: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_paths_in_database(db_path, old_path, new_path):
    """Update all paths in database"""
    if not os.path.exists(db_path):
        return 0
    
    # Prepare path formats
    old_paths = []
    new_paths = []
    
    # Windows path formats
    old_paths.extend([
        old_path,
        old_path.replace('\\', '/'),
        old_path.replace('C:', 'c:'),
        old_path.replace('c:', 'C:'),
    ])
    
    new_paths.extend([
        new_path,
        new_path.replace('\\', '/'),
        new_path.replace('C:', 'c:'),
        new_path.replace('c:', 'C:'),
    ])
    
    # URI formats
    # Cannot use backslash in f-string, do the operation first
    old_path_for_uri = old_path.replace('\\', '/').replace(':', '%3A')
    new_path_for_uri = new_path.replace('\\', '/').replace(':', '%3A')
    old_uri = f"file:///{old_path_for_uri}"
    new_uri = f"file:///{new_path_for_uri}"
    
    old_paths.extend([
        old_uri,
        old_uri.replace('%3A', ':'),
        old_uri.replace('file:///', 'file:///c'),
    ])
    
    new_paths.extend([
        new_uri,
        new_uri.replace('%3A', ':'),
        new_uri.replace('file:///', 'file:///c'),
    ])
    
    # Just folder name
    old_folder = os.path.basename(old_path)
    new_folder = os.path.basename(new_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        total_updated = 0
        
        # Get all rows from ItemTable
        cursor.execute("SELECT key, value FROM ItemTable")
        rows = cursor.fetchall()
        
        for key, value in rows:
            if not value or not isinstance(value, str):
                continue
            
            updated_value = value
            
            # Replace each path format
            for old, new in zip(old_paths, new_paths):
                updated_value = updated_value.replace(old, new)
            
            # Also update paths within JSON
            if updated_value.startswith('{') or updated_value.startswith('['):
                try:
                    data = json.loads(updated_value)
                    data_str = json.dumps(data)
                    
                    for old, new in zip(old_paths, new_paths):
                        data_str = data_str.replace(old, new)
                    
                    updated_data = json.loads(data_str)
                    updated_value = json.dumps(updated_data)
                except:
                    pass
            
            # Update if there are changes
            if updated_value != value:
                cursor.execute("UPDATE ItemTable SET value = ? WHERE key = ?", 
                             (updated_value, key))
                total_updated += 1
        
        if total_updated > 0:
            conn.commit()
        
        conn.close()
        return total_updated
    
    except Exception as e:
        print(f"❌ Database update error: {e}")
        return 0


def update_workspace_json(workspace_json_path, old_path, new_path):
    """Update workspace.json file"""
    if not workspace_json_path or not os.path.exists(workspace_json_path):
        return False
    
    try:
        with open(workspace_json_path, 'r', encoding='utf-8') as f:
            workspace_data = json.load(f)
        
        folder_uri = workspace_data.get('folder', '')
        if folder_uri:
            # Replace old path with new path
            # Cannot use backslash in f-string, do the operation first
            new_path_for_uri = new_path.replace('\\', '/').replace(':', '%3A')
            new_uri = f"file:///{new_path_for_uri}"
            workspace_data['folder'] = new_uri
            
            with open(workspace_json_path, 'w', encoding='utf-8') as f:
                json.dump(workspace_data, f, indent=2)
            
            return True
    except Exception as e:
        print(f"⚠️  Could not update workspace.json: {e}")
    
    return False


def main():
    """Main function"""
    print("=" * 80)
    print("Cursor Workspace Path Updater")
    print("=" * 80)
    print()
    
    # Get current folder path
    current_path = os.getcwd()
    current_folder = os.path.basename(current_path)
    
    print(f"📁 Current folder: {current_folder}")
    print(f"   Full path: {current_path}")
    print()
    
    # Get old folder name from user
    print("💡 Please enter the old folder name (name before the folder was renamed):")
    old_folder_name = input("Old folder name: ").strip()
    
    if not old_folder_name:
        print("❌ Old folder name not entered. Operation cancelled.")
        return 1
    
    print()
    
    # Normalize paths
    try:
        current_path = str(Path(current_path).resolve())
    except:
        pass
    
    # Create old path
    current_parent = str(Path(current_path).parent)
    old_path = os.path.join(current_parent, old_folder_name)
    
    try:
        old_path = str(Path(old_path).resolve())
    except:
        pass
    
    # Check if paths are the same
    if old_path.lower() == current_path.lower():
        print(f"✅ Old and new paths are the same! No update needed.")
        return 0
    
    print("🔍 Searching for workspaces...")
    print()
    
    # 1. Find old workspace (based on old folder name)
    print(f"📂 Searching for old workspace (folder: {old_folder_name})...")
    old_workspace_info = find_workspace_by_path(old_path, old_folder_name)
    
    if not old_workspace_info:
        print("❌ Cursor workspace not found for old folder name!")
        print()
        print("💡 Tip:")
        print("   - Make sure you entered the old folder name correctly")
        print("   - Make sure you opened the old folder with Cursor before")
        return 1
    
    old_workspace_id, old_state_db_path, old_workspace_json_path, old_folder_uri = old_workspace_info
    print(f"✅ Old workspace found: {old_workspace_id}")
    
    # Show found workspace path (for verification)
    if old_workspace_json_path and os.path.exists(old_workspace_json_path):
        try:
            with open(old_workspace_json_path, 'r', encoding='utf-8') as f:
                workspace_data = json.load(f)
            found_path_uri = workspace_data.get('folder', '')
            if found_path_uri:
                if found_path_uri.startswith('file:///'):
                    found_path = found_path_uri.replace('file:///', '').replace('%3A', ':')
                else:
                    found_path = found_path_uri
                print(f"   Workspace path: {found_path}")
                
                # Compare paths
                try:
                    found_path_normalized = str(Path(found_path).resolve())
                    old_path_normalized = str(Path(old_path).resolve())
                    if found_path_normalized.lower() != old_path_normalized.lower():
                        print(f"   ⚠️  WARNING: Found path differs from expected path!")
                        print(f"   Expected: {old_path}")
                        print(f"   Found: {found_path}")
                        print()
                        response = input("Do you want to continue? (Y/n): ").strip().lower()
                        if response not in ['y', 'yes', 'e', 'evet', '']:
                            print("Operation cancelled.")
                            return 0
                except:
                    pass
        except:
            pass
    
    print()
    
    # 2. Find new workspace (for current folder)
    print(f"📂 Searching for new workspace (folder: {current_folder})...")
    new_workspace_info = find_workspace_by_current_folder(current_path)
    
    if not new_workspace_info:
        print("⚠️  Workspace not found for new folder!")
        print("   You may need to close and reopen Cursor once.")
        print("   Or a new workspace will be created...")
        print()
        
        # Create new workspace (as Cursor would)
        # Workspace ID will be a random hash, but we'll just prepare the folder
        print("❌ New workspace cannot be created automatically.")
        print("   Please open this folder with Cursor and run the script again.")
        return 1
    
    new_workspace_id, new_state_db_path, new_workspace_json_path, new_folder_uri = new_workspace_info
    print(f"✅ New workspace found: {new_workspace_id}")
    print()
    
    # 3. Copy state.vscdb from old workspace to new workspace
    print("=" * 80)
    print("📋 Copying state.vscdb file...")
    print()
    print("⚠️  IMPORTANT: Run this script from CMD or PowerShell, NOT from Cursor terminal!")
    print("⚠️  COMPLETELY CLOSE CURSOR (all windows) and reopen after the script completes!")
    print()
    print("   If file is copied while Cursor is open:")
    print("   - File may be locked")
    print("   - Cursor may recreate the file")
    print("   - Chat history may be lost")
    print()
    response = input("Have you closed Cursor and are you running the script from CMD/PowerShell? (Y/n): ").strip().lower()
    if response not in ['y', 'yes', 'e', 'evet', '']:
        print()
        print("⚠️  WARNING: Copying while Cursor is open or from Cursor terminal is not recommended!")
        print("   Chat history may be lost. Do you want to continue?")
        response2 = input("   Continue? (Y/n): ").strip().lower()
        if response2 not in ['y', 'yes', 'e', 'evet', '']:
            print("Operation cancelled.")
            return 0
        print()
    
    if not copy_state_db(old_state_db_path, new_state_db_path):
        print()
        print("❌ state.vscdb could not be copied!")
        print("   Please close Cursor and run the script again.")
        return 1
    print()
    print("=" * 80)
    print()
    
    # Now we'll use the new workspace
    workspace_id = new_workspace_id
    state_db_path = new_state_db_path
    workspace_json_path = new_workspace_json_path
    folder_uri = new_folder_uri
    
    print(f"🔄 Path update:")
    print(f"   Old: {old_path}")
    print(f"   New: {current_path}")
    print()
    
    # Get user confirmation
    response = input("Do you want to continue? (Y/n): ").strip().lower()
    if response not in ['y', 'yes', 'e', 'evet', '']:
        print("Operation cancelled.")
        return 0
    
    print()
    print("🔄 Updating...")
    print()
    
    # Update workspace.json
    if workspace_json_path:
        if update_workspace_json(workspace_json_path, old_path, current_path):
            print("✅ workspace.json updated")
    
    # Update state.vscdb
    updated_count = update_paths_in_database(state_db_path, old_path, current_path)
    
    if updated_count > 0:
        print(f"✅ {updated_count} rows updated in database")
    else:
        print("ℹ️  No paths found to update (may already be up to date)")
    
    print()
    print("=" * 80)
    print("✅ Operation completed!")
    print()
    print("💡 It is recommended to restart Cursor.")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

