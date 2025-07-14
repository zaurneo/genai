import os
import shutil

def delete_pycache_folders(root_folder):
    deleted = 0
    for dirpath, dirnames, filenames in os.walk(root_folder):
        if "__pycache__" in dirnames:
            pycache_path = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print(f"Deleted: {pycache_path}")
                deleted += 1
            except Exception as e:
                print(f"Failed to delete {pycache_path}: {e}")
    print(f"\nTotal __pycache__ folders deleted: {deleted}")

def clean_output_folder(output_folder):
    """Clean the output folder by removing all generated files."""
    deleted_files = 0
    deleted_folders = 0
    
    if not os.path.exists(output_folder):
        print(f"Output folder does not exist: {output_folder}")
        return
    
    try:
        for item in os.listdir(output_folder):
            item_path = os.path.join(output_folder, item)
            
            if os.path.isfile(item_path):
                os.remove(item_path)
                print(f"Deleted file: {item_path}")
                deleted_files += 1
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"Deleted folder: {item_path}")
                deleted_folders += 1
                
    except Exception as e:
        print(f"Error cleaning output folder: {e}")
    
    print(f"\nOutput folder cleanup complete:")
    print(f"- Files deleted: {deleted_files}")
    print(f"- Folders deleted: {deleted_folders}")

def clean_all():
    """Clean both __pycache__ folders and output folder."""
    root_folder = r"C:\Users\Zaur\OneDrive\Development\Genesis\genesis"
    output_folder = os.path.join(root_folder, "output")
    
    print("Starting cleanup process...")
    print("=" * 50)
    
    print("\n1. Cleaning __pycache__ folders...")
    delete_pycache_folders(root_folder)
    
    print("\n2. Cleaning output folder...")
    clean_output_folder(output_folder)
    
    print("\n" + "=" * 50)
    print("Cleanup process complete!")

if __name__ == "__main__":
    delete_pycache_folders()