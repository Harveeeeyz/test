import os

def list_files(directory):
    file_structure = []
    for root, dirs, files in os.walk(directory):
        # Skip the venv directory
        if 'venv' in root:
            level = root.replace(directory, '').count(os.sep)
            indent = ' ' * 4 * level
            file_structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for file in files:
                file_structure.append(f"{subindent}{file}")
            continue

        level = root.replace(directory, '').count(os.sep)
        indent = ' ' * 4 * level
        file_structure.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            file_structure.append(f"{subindent}{file}")
    return "\n".join(file_structure)

def read_py_files(directory):
    py_files_content = []
    for root, dirs, files in os.walk(directory):
        # Skip the venv directory
        if 'venv' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                py_files_content.append(f"---\nFile: {file_path}\n---\n{content}\n")
    return "\n".join(py_files_content)

def generate_full_document(directory):
    file_structure = list_files(directory)
    py_content = read_py_files(directory)
    full_document = f"File Structure:\n\n{file_structure}\n\nPython Files Content:\n\n{py_content}"
    return full_document

directory = 'F:/telegramhelp2'  # 替换为你的项目路径
full_document = generate_full_document(directory)
print(full_document)

# 如果需要保存到文件中
with open('project_summary.txt', 'w', encoding='utf-8') as f:
    f.write(full_document)
