import zipfile
import os

zip_path = r"C:\Users\Admin\Downloads\6ab10eb3b23ba_student_resource.zip"

extract_path = r"E:\Amazon-ML-Challenge-2026\data"

os.makedirs(extract_path, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

print("Dataset extracted successfully!")

for root, dirs, files in os.walk(extract_path):
    level = root.replace(extract_path, '').count(os.sep)
    indent = '  ' * level
    print(f"{indent}{os.path.basename(root)}/")

    for file in files:
        print(f"{indent}  {file}")