import PyInstaller.__main__
import os
import shutil
import platform

def clean_previous_builds():
    print("🧹 Cleaning previous build files...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            try: shutil.rmtree(folder)
            except: pass
    if os.path.exists('SnapCapsule.spec'):
        try: os.remove('SnapCapsule.spec')
        except: pass

def build():
    separator = ';' if platform.system() == 'Windows' else ':'
    
    # 1. Assets (Source -> Destination)
    assets_data = f"src/assets{separator}src/assets"
    
    # 2. Tutorial File (Source -> Destination)
    # We place it in the root of the bundle
    tutorial_data = f"tutorial.md{separator}."

    icon_path = os.path.join("src", "assets", "icons", "snapcapsule.ico")
    icon_arg = f'--icon={icon_path}' if os.path.exists(icon_path) else None

    print("\n🚀 Starting PyInstaller Build...")
    
    args = [
        'src/main.py',
        '--name=SnapCapsule',
        '--onedir',
        '--windowed',
        '--noconfirm',
        '--clean',
        f'--add-data={assets_data}',
        f'--add-data={tutorial_data}', # <--- ADDED TUTORIAL
        '--paths=src',
        '--hidden-import=ffpyplayer',
        '--hidden-import=PIL._tkinter_finder'
    ]
    
    if icon_arg: args.append(icon_arg)

    PyInstaller.__main__.run(args)
    print("\n✅ Build Complete! Check dist/SnapCapsule folder.")

if __name__ == "__main__":
    clean_previous_builds()
    build()