import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

# Hardcoded paths
PRIVATE_ROOT = Path("/path/to/private/LeafScan-CornDefoliation2025-v1")
PUBLIC_ROOT = Path("/path/to/public/LeafScan-CornDefoliation2025-v1")
NEW_MEDIA_DIR = Path("/path/to/NewMedia")

TEMPLATE_PATHS = [
    ("field", Path("/path/to/templates/field_template.json"), 2),
    ("section", Path("/path/to/templates/section_template.json"), 2),
    ("plant", Path("/path/to/templates/plant_template.json"), 2),
    ("media", Path("/path/to/templates/media_template.json"), 2),
]

def load_json(path):
    return json.load(open(path)) if path.exists() else {}

def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def update_metadata_entries(entry, metadata_path):
    data = load_json(metadata_path)
    data.update(entry)
    save_json(data, metadata_path)

def edit_json_template(template):

    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
        json.dump(template, tmp, indent=4)
        tmp_path = tmp.name

    subprocess.call([os.getenv("EDITOR", "nano"), tmp_path])

    with open(tmp_path) as f:
        edited = json.load(f)
    os.remove(tmp_path)
    return edited

def populateEntryIds(template_key, entry_id, ids, template_data):
    template_data[f"{template_key}_id"] = entry_id

    template_data.setdefault("backtrace", {})
    print(ids)
    for key, value in ids.items():
        template_data["backtrace"][f"{key}_id"] = value

    return template_data        

def get_padded_id(template_key, pad):
    is_valid = False
    while not is_valid:
        input_str = input(f"Enter {template_key} ID (e.g., 01): ")

        if not input_str.isdigit():
            print("ID must be numeric.")
        elif len(input_str) > pad:
            print(f"ID too long. Must be at most {pad}.")
        else: 
            is_valid = True
    
    return input_str.zfill(pad)

def strip_private_info(entry):
    return {k: v for k, v in entry.items() if k != "private_information"}
    
def prompt_or_load_non_final(template_params, priv_base_dir, pub_base_dir, ids):
    template_key, template_path, pad = template_params
    priv_meta_file = priv_base_dir / f"{template_key}_metadata.json"
    pub_meta_file = pub_base_dir / f"{template_key}_metadata.json"

    if not priv_meta_file.exists():
        print(f"Creating new metadata file: {priv_meta_file}")
        save_json({}, priv_meta_file)
    if not pub_meta_file.exists():
        print(f"Creating new metadata file: {pub_meta_file}")
        save_json({}, pub_meta_file)

    priv_metadata = load_json(priv_meta_file)
    pub_metadata = load_json(pub_meta_file)

    entry_id, entry_key, entry = prompt_or_load_entry(template_params, priv_metadata, ids)

    priv_entry_path = priv_base_dir / entry_key
    pub_entry_path = pub_base_dir / entry_key

    if entry is not None:
        priv_metadata[entry_key] = entry
        pub_metadata[entry_key] = strip_private_info(entry)
        save_json(priv_metadata, priv_meta_file)
        save_json(pub_metadata, pub_meta_file)

        priv_entry_path.mkdir(parents=True, exist_ok=True)
        pub_entry_path.mkdir(parents=True, exist_ok=True)
    
    return entry_id, entry_key, priv_entry_path, pub_entry_path


def prompt_or_load_final(template_params, priv_base_dir, pub_base_dir, ids, media_type=None):

    media_type = 'img' if media_type is None or media_type == 'img' else "vid"
    template_key, template_path, pad = template_params
    template_key = f'{template_key}_{media_type}'

    priv_meta_file = priv_base_dir / f"{template_key}_metadata.json"
    pub_meta_file = pub_base_dir / f"{template_key}_metadata.json"

    if not priv_meta_file.exists():
        print(f"Creating new metadata file: {priv_meta_file}")
        save_json({}, priv_meta_file)
    if not pub_meta_file.exists():
        print(f"Creating new metadata file: {pub_meta_file}")
        save_json({}, pub_meta_file)

    priv_metadata = load_json(priv_meta_file)
    pub_metadata = load_json(pub_meta_file)

    template_params = (template_key, template_path, pad) 
    entry_id, entry_key, entry = prompt_or_load_entry(template_params, priv_metadata, ids)

    priv_entry_path = priv_base_dir
    pub_entry_path = pub_base_dir

    if entry is not None:
        priv_metadata[entry_key] = entry
        pub_metadata[entry_key] = strip_private_info(entry)
        save_json(priv_metadata, priv_meta_file)
        save_json(pub_metadata, pub_meta_file)

        priv_entry_path.mkdir(parents=True, exist_ok=True)
        pub_entry_path.mkdir(parents=True, exist_ok=True)
    
    return entry_id, entry_key, priv_entry_path, pub_entry_path

def prompt_or_load_entry(template_params, priv_metadata, ids):
    template_key, template_path, pad = template_params

    entry_id = get_padded_id(template_key, pad)
    entry_key = f"{template_key}_{entry_id}"
    
    print(entry_key)

    if entry_key in priv_metadata:
        print(f"{entry_key} exists. Skipping.")
        entry = None
    else:
        choice = input("Entry not found. Use (t)emplate or (c)ustom entry? [t/c]: ").lower()
        if choice == 't':
            print("Using default template. Remember to edit this later with real values.")
            template = load_json(template_path)
            entry = populateEntryIds(template_key, entry_id, ids, template)
        else:
            template = load_json(template_path)
            template = populateEntryIds(template_key, entry_id, ids, template)
            entry = edit_json_template(template)
        
    return entry_id, entry_key, entry

def get_media_files():
    return sorted([f for f in NEW_MEDIA_DIR.glob("*.*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4']])

def remove_metadata_and_reencode(video_path, output_path):
    subprocess.run([
        "ffmpeg", "-i", str(video_path), "-map", "0:v:0", "-c:v", "libx264",
        "-an", str(output_path), "-y"
    ])

def main():
    media_files = get_media_files()
    for i, f in enumerate(media_files):
        print(f"[{i}] {f.name}")
    index = int(input("Select media file number: "))
    selected_file = media_files[index]

    path_private, path_public = PRIVATE_ROOT, PUBLIC_ROOT
    ids = {}

    # Traverse all template levels including media
    for template_params in TEMPLATE_PATHS[:-1]:
        entry_id, entry_key, path_private, path_public = prompt_or_load_non_final(template_params, path_private, path_public, ids)
        ids[template_params[0]] = entry_id
    
    media_type, prefix = ("videos", "vid") if selected_file.suffix.lower() == ".mp4" else ("images", "img")

    template_params = TEMPLATE_PATHS[-1]
    entry_id, entry_key, path_private, path_public = prompt_or_load_final(template_params, path_private, path_public, ids, prefix)
    ids[template_params[0]] = entry_id
    
    media_filename = f"{prefix}_{ids['field']}_{ids['section']}_{ids['plant']}_{ids['leaf']}{selected_file.suffix}"

    # Create final media directories
    private_dest = path_private / media_type
    public_dest = path_public / media_type
    private_dest.mkdir(parents=True, exist_ok=True)
    public_dest.mkdir(parents=True, exist_ok=True)

    shutil.copy(selected_file, private_dest / media_filename)

    if selected_file.suffix.lower() == ".mp4":
        remove_metadata_and_reencode(private_dest / media_filename, public_dest / media_filename)
    else:
        shutil.copy(selected_file, public_dest / media_filename)

    os.remove(selected_file)

    print("\n✅ Media organized and metadata updated.")

if __name__ == "__main__":
    main()

