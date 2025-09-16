"""
Discovery module for finding and grouping code files
"""
import os
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict
from .models import CodeFile, CodeModule


class CodeDiscovery:
    """Discovers and groups code files in a project"""

    # File extensions by language
    LANGUAGE_EXTENSIONS = {
        'python': {'.py', '.pyx', '.pyi'},
        'javascript': {'.js', '.jsx', '.mjs'},
        'typescript': {'.ts', '.tsx'},
        'java': {'.java'},
        'csharp': {'.cs'},
        'cpp': {'.cpp', '.cc', '.cxx', '.c++', '.hpp', '.h', '.hxx'},
        'c': {'.c', '.h'},
        'go': {'.go'},
        'rust': {'.rs'},
        'ruby': {'.rb'},
        'php': {'.php'},
        'swift': {'.swift'},
        'kotlin': {'.kt', '.kts'},
        'scala': {'.scala'},
        'shell': {'.sh', '.bash', '.zsh'},
        'yaml': {'.yaml', '.yml'},
        'json': {'.json'},
        'xml': {'.xml'},
        'html': {'.html', '.htm'},
        'css': {'.css', '.scss', '.sass', '.less'},
        'sql': {'.sql'},
    }

    # Directories to skip
    SKIP_DIRS = {
        '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
        'dist', 'build', '.pytest_cache', '.mypy_cache', 'coverage',
        '.idea', '.vscode', 'target', 'bin', 'obj', '.next', '.nuxt'
    }

    def __init__(self, project_path: str, max_files_per_module: int = 50):
        self.project_path = Path(project_path).resolve()
        self.max_files_per_module = max_files_per_module

    def discover_files(self) -> List[CodeFile]:
        """Discover all code files in the project"""
        code_files = []

        for root, dirs, files in os.walk(self.project_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for file in files:
                file_path = Path(root) / file

                # Skip if not a code file
                language = self._get_language(file_path)
                if not language:
                    continue

                # Skip very large files
                try:
                    size = file_path.stat().st_size
                    if size > 1_000_000:  # 1MB
                        continue

                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)

                    relative_path = file_path.relative_to(self.project_path)

                    code_files.append(CodeFile(
                        path=str(file_path),
                        relative_path=str(relative_path),
                        language=language,
                        size=size,
                        lines=lines
                    ))
                except Exception:
                    # Skip files that can't be read
                    continue

        return code_files

    def group_into_modules(self, files: List[CodeFile]) -> List[CodeModule]:
        """Group files into logical modules based on directory structure"""
        modules_dict: Dict[str, List[CodeFile]] = defaultdict(list)

        for file in files:
            # Get the module name from directory structure
            parts = Path(file.relative_path).parts

            if len(parts) > 1:
                # Use first directory as module name
                module_name = parts[0]
            else:
                # Root level files
                module_name = "root"

            modules_dict[module_name].append(file)

        # Convert to CodeModule objects
        modules = []
        for module_name, module_files in modules_dict.items():
            # Split large modules
            if len(module_files) > self.max_files_per_module:
                # Group by subdirectory
                submodules = self._split_large_module(module_name, module_files)
                modules.extend(submodules)
            else:
                module = self._create_module(module_name, module_files)
                modules.append(module)

        return modules

    def _split_large_module(self, base_name: str, files: List[CodeFile]) -> List[CodeModule]:
        """Split a large module into smaller sub-modules"""
        submodules_dict: Dict[str, List[CodeFile]] = defaultdict(list)

        for file in files:
            parts = Path(file.relative_path).parts
            if len(parts) > 2:
                # Use second level directory
                submodule_name = f"{base_name}/{parts[1]}"
            else:
                submodule_name = base_name

            submodules_dict[submodule_name].append(file)

        modules = []
        for name, subfiles in submodules_dict.items():
            # Further split if still too large
            if len(subfiles) > self.max_files_per_module:
                # Just take first N files
                subfiles = subfiles[:self.max_files_per_module]

            module = self._create_module(name, subfiles)
            modules.append(module)

        return modules

    def _create_module(self, name: str, files: List[CodeFile]) -> CodeModule:
        """Create a CodeModule from a list of files"""
        # Determine primary language
        language_counts = defaultdict(int)
        for file in files:
            language_counts[file.language] += 1

        primary_language = max(language_counts, key=language_counts.get) if language_counts else "unknown"

        # Generate description
        total_files = len(files)
        total_lines = sum(f.lines for f in files)
        description = f"Module with {total_files} {primary_language} files ({total_lines} lines)"

        return CodeModule(
            name=name,
            description=description,
            files=files,
            primary_language=primary_language,
            total_lines=total_lines
        )

    def _get_language(self, file_path: Path) -> Optional[str]:
        """Determine the programming language of a file"""
        suffix = file_path.suffix.lower()

        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            if suffix in extensions:
                return language

        return None