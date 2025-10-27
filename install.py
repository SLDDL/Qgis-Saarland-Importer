#!/usr/bin/env python3
import os
import shutil
import sys
import platform
from pathlib import Path

def get_qgis_plugin_dirs():
    """Return a list of QGIS plugin directories to consider based on the OS.

    On Linux we include both the regular user plugins directory and the
    Flatpak-specific location used by org.qgis.qgis. For non-Linux OSes a
    single path is returned inside a list for uniform handling by the caller.
    """
    home_dir = Path.home()
    system = platform.system().lower()

    if system == "linux":
        # Regular user location: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
        local = home_dir / ".local/share/QGIS/QGIS3/profiles/default/python/plugins"
        # Flatpak location for org.qgis.qgis: ~/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/plugins
        flatpak = home_dir / ".var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/plugins"
        return [local, flatpak]

    elif system == "darwin":  # macOS
        # Mac: ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
        return [home_dir / "Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"]

    elif system == "windows":
        # Windows: %APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/
        appdata = os.environ.get('APPDATA', str(home_dir / "AppData/Roaming"))
        return [Path(appdata) / "QGIS/QGIS3/profiles/default/python/plugins"]

    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

def get_plugin_info():
    """Get the plugin directory and name from where this script is located."""
    # Get the directory where this install.py script is located
    script_dir = Path(__file__).parent.resolve()
    # Always install using the canonical plugin folder name
    # This ensures the plugin is installed as 'saarland_geoportal'
    # regardless of the local checkout directory name.
    plugin_name = "saarland_geoportal"
    return script_dir, plugin_name

def main():
    """Main installation function."""
    try:
        # Get plugin source directory (where this script is located)
        source_dir, plugin_name = get_plugin_info()
        
        # Get candidate QGIS plugin directories (may be multiple on Linux)
        qgis_plugin_dirs = get_qgis_plugin_dirs()

        print(f"Installing plugin '{plugin_name}'...")
        print(f"Source: {source_dir}")
        print("Candidate targets:")
        for d in qgis_plugin_dirs:
            print(f"  - {d}")

        installed_any = False

        # Install into every candidate that is appropriate.
        # For the primary location (first in list) we create the directory if missing.
        # For additional locations (Flatpak) we only install if the destination parent exists
        # so we don't create system/Flatpak directories unexpectedly.
        for idx, qgis_plugin_dir in enumerate(qgis_plugin_dirs):
            target_dir = qgis_plugin_dir / plugin_name
            is_primary = (idx == 0)

            if is_primary:
                # Ensure the primary plugin directory exists (user location)
                qgis_plugin_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Only install to non-primary locations when their parent exists
                # (avoid creating Flatpak or other app-specific data dirs unexpectedly)
                if not qgis_plugin_dir.parent.exists() and not qgis_plugin_dir.exists():
                    print(f"Skipping {qgis_plugin_dir} (parent does not exist)")
                    continue

            print(f"Target: {target_dir}")

            # Remove existing installation if it exists
            if target_dir.exists():
                print(f"Removing existing installation at {target_dir}")
                shutil.rmtree(target_dir)

            # Copy plugin directory to QGIS plugin folder
            print("Copying plugin files...")
            shutil.copytree(source_dir, target_dir, ignore=shutil.ignore_patterns(
                '.git*', '__pycache__', '*.pyc', '*.pyo', 'test', 'tests', 
                '*.zip', 'install.py'
            ))

            print(f"✓ Plugin '{plugin_name}' successfully installed to:")
            print(f"  {target_dir}")
            installed_any = True

        if not installed_any:
            raise RuntimeError("No valid QGIS plugin target directories were found or writable.")

        print("\nRestart QGIS to see the plugin in the Plugins menu.")
        
    except Exception as e:
        print(f"✗ Installation failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()