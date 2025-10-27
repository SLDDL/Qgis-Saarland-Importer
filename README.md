# Saarland Geoportal WMS/WFS Plugin for QGIS

A QGIS plugin that provides easy access to WMS and WFS services from the Saarland Geoportal (Germany). This plugin allows users to browse and load geospatial data layers directly from Saarland's open data portal into their QGIS projects.

*Disabling rendering is recommended when importing more than 10 layers at the same time, as it may crash QGIS.*

Consider supporting me on [Ko-fi](https://ko-fi.com/smasse)!

## Requirements

- **QGIS**: Version 3.0 or higher
- **Python**: 3.6+ (included with QGIS)
- **Dependencies**: All required Python packages are included in the `vendor/` directory

## Installation from Source

### Method 1: Automatic Installation (Recommended)

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/SLDDL/Qgis-Saarland-Importer saarland_geoportal
   # or download and extract the ZIP file
   ```

2. **Run the installer**:
   ```bash
   cd saarland_geoportal
   python install.py
   ```
   
   The installer automatically detects your operating system and copies the plugin to the correct QGIS plugin directory:
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows**: `%APPDATA%\\QGIS\\QGIS3\\profiles\\default\\python\\plugins\\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

3. **Restart QGIS** and enable the plugin in the Plugin Manager.

### Method 2: Manual Installation

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/SLDDL/Qgis-Saarland-Importer saarland_geoportal
   # or download and extract the ZIP file
   ```

2. **Locate your QGIS plugins directory** (see paths above)

3. **Copy the plugin folder**:
   ```bash
   # Linux/macOS
   cp -r saarland_geoportal ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
   
   # Windows (using Command Prompt)
   xcopy saarland_geoportal "%APPDATA%\\QGIS\\QGIS3\\profiles\\default\\python\\plugins\\saarland_geoportal\\" /E /I
   ```

4. **Restart QGIS** and enable the plugin in the Plugin Manager.

## Usage

1. **Enable the Plugin**:
   - Open QGIS
   - Go to `Plugins` → `Manage and Install Plugins`
   - Find "SaarlandGeobasisdatenWMS" and enable it

2. **Access the Plugin**:
   - Look for the Saarland Geoportal icon in the toolbar
   - Or go to `Database` → `SaarlandOpendataWMS` in the menu

3. **Browse and Load Services**:
   - The plugin will automatically fetch available services from the Saarland Geoportal
   - Browse through categories (ALKIS, Historical Data, etc.)
   - Select desired layers and click to load them into your project

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
