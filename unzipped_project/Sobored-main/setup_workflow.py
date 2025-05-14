#!/usr/bin/env python3
"""
Setup workflow for the Discord bot in Replit
This script creates the necessary .replit file with the correct workflow configuration
"""
import os
import json

def setup_workflow():
    """Set up the Discord bot workflow"""
    print("Setting up Discord bot workflow...")
    
    # Create the .replit file with the proper workflow configuration
    replit_config = {
        "run": "bash run.sh",
        "modules": ["python-3.11"],
        "entrypoint": "run.py",
        "nix": {
            "channel": "stable-24_05",
            "packages": [
                "cacert", "cairo", "ffmpeg-full", "freetype", "ghostscript", 
                "glibcLocales", "gobject-introspection", "gtk3", "lcms2", 
                "libimagequant", "libjpeg", "libsodium", "libtiff", "libwebp", 
                "libxcrypt", "nettle", "openjpeg", "openssh", "openssl", 
                "pkg-config", "qhull", "tcl", "tk", "zlib"
            ]
        },
        "workspaces": {
            "discord_bot": {
                "title": "Discord Bot",
                "run": "bash run.sh",
                "restartOn": {
                    "watch-path": "./.replit"
                }
            }
        }
    }
    
    # Write the configuration to the .replit file
    with open('.replit', 'w') as f:
        for key, value in replit_config.items():
            if key == "workspaces":
                f.write(f"[{key}]\n")
                for workspace_name, workspace_config in value.items():
                    f.write(f"[{key}.{workspace_name}]\n")
                    for wk_key, wk_value in workspace_config.items():
                        if isinstance(wk_value, dict):
                            f.write(f"[{key}.{workspace_name}.{wk_key}]\n")
                            for sub_key, sub_value in wk_value.items():
                                f.write(f'{sub_key} = "{sub_value}"\n')
                        else:
                            f.write(f'{wk_key} = "{wk_value}"\n')
            elif key == "nix":
                f.write(f"[{key}]\n")
                for nix_key, nix_value in value.items():
                    if nix_key == "packages":
                        f.write(f'{nix_key} = {json.dumps(nix_value)}\n')
                    else:
                        f.write(f'{nix_key} = "{nix_value}"\n')
            elif key == "modules":
                f.write(f'{key} = {json.dumps(value)}\n')
            else:
                f.write(f'{key} = "{value}"\n')
    
    print("Workflow setup completed. You can now run the Discord bot using the workflow.")

if __name__ == "__main__":
    setup_workflow()