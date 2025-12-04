# Cursor Workspace Path Updater

Automatic script to preserve Cursor's chat history when a folder name is changed.

## Usage

1. **Rename the folder** (e.g., `old_folder` → `new_folder`)

2. **Open Cursor with the new folder name** (to create the workspace)

3. **COMPLETELY CLOSE CURSOR** ⚠️
   - If the script is run while Cursor is open, Cursor may lock or recreate the file
   - Close all Cursor windows

4. **Run the script from CMD or PowerShell** (NOT from Cursor terminal!):
   ```bash
   cd C:\Users\Guzelbilen\Desktop\new_folder
   python update_cursor_workspace_path_EN.py
   ```

5. **The script will ask for the old folder name:**
   - Enter the old folder name (e.g., `old_folder`)
   - The script finds the old workspace (based on the old folder name)
   - The script finds the new workspace (based on the new folder name)
   - Copies the `state.vscdb` file from the old workspace to the new workspace (for chat history)
   - Updates all path references in the new workspace

6. **After the script completes, reopen Cursor**

## Features

- ✅ Prompts user for old folder name (reliable detection)
- ✅ Automatically finds old and new workspaces
- ✅ Preserves chat history (copies state.vscdb)
- ✅ Updates all path formats (Windows, URI, etc.)
- ✅ Updates nested paths within JSON
- ✅ Backup (existing state.vscdb is backed up)
- ✅ Safe update with user confirmation
- ✅ Windows, macOS and Linux support

## Example Usage

```bash
# 1. Rename folder: old_folder → new_folder
# 2. Open new folder with Cursor (to create workspace)
# 3. COMPLETELY CLOSE CURSOR
# 4. From CMD or PowerShell:

cd C:\Users\Guzelbilen\Desktop\new_folder
python update_cursor_workspace_path_EN.py

# Script will ask for old folder name:
# Old folder name: old_folder

# 5. After script completes, reopen Cursor
```

## How It Works?

1. **Finding Old Workspace**: Finds the old workspace based on the old folder name
2. **Finding New Workspace**: Finds the new workspace based on the new folder name
3. **Copying Chat History**: Copies the `state.vscdb` file from the old workspace to the new workspace
4. **Updating Paths**: Updates all path references in the new workspace

## Important Notes

- ⚠️ **Run the script from CMD or PowerShell, NOT from Cursor terminal!**
- ⚠️ **COMPLETELY CLOSE CURSOR before running the script!**
- The script copies the `state.vscdb` file to preserve chat history
- Existing `state.vscdb` file is backed up with `.backup` extension
- The script only updates actual path references
- Text content in chat messages is not changed
- Hash keys are not changed for security reasons
- If the new workspace is not found, try closing and reopening Cursor once

## Troubleshooting

**Workspace not found:**
- Make sure you opened the folder with Cursor (to create the workspace)
- Close and reopen Cursor once
- Check that the `workspaceStorage` folder is in the correct location

**Chat history didn't appear:**
- ⚠️ Make sure you ran the script from CMD/PowerShell, not from Cursor terminal
- ⚠️ Make sure you COMPLETELY CLOSED Cursor before running the script
- Check that the script successfully completed the copy operation (ItemTable check)
- Check that the `ItemTable` table exists in the `state.vscdb` file in the new workspace

**Paths not updated:**
- Completely close and reopen Cursor
- Try running the script as administrator (Windows)

