#!/usr/bin/env python3
"""
项目代码合并脚本 - 修复空文件问题版本
将多目录的Python项目合并成单个py文件，自动处理依赖关系
"""

import os
import re
import ast
import sys
import inspect
from collections import defaultdict, deque
from pathlib import Path
from typing import Set, List, Dict, Optional, Tuple

class PythonProjectMerger:
    def __init__(self, root_dir: str, output_file: str, main_files: List[str] = None, debug: bool = True):
        self.root_dir = Path(root_dir).resolve()
        self.output_file = Path(output_file)
        self.main_files = main_files or ["main.py"]
        self.processed_files: Set[Path] = set()
        self.import_graph: Dict[Path, Set[Path]] = defaultdict(set)
        self.reverse_graph: Dict[Path, Set[Path]] = defaultdict(set)
        self.file_contents: Dict[Path, str] = {}
        self.module_to_file: Dict[str, Path] = {}
        self.debug = debug
        self.standard_libs = self._get_standard_libs()
        self.reachable_files: Set[Path] = set()
        
    def debug_print(self, message: str):
        """调试信息输出"""
        if self.debug:
            print(f"[DEBUG] {message}")
        
    def _get_standard_libs(self) -> Set[str]:
        """获取Python标准库列表"""
        common_stdlibs = {
            'abc','argparse','ast','base64','bz2','collections','configparser',
            'contextlib','copy','csv','dataclasses','datetime','email','enum',
            'functools','glob','gzip','hashlib','html','http','inspect','io',
            'itertools','json','logging','math','multiprocessing','numpy','operator',
            'os','pandas','pathlib','pickle','pprint','random','re','shutil','socket',
            'sqlite3','ssl','subprocess','sumolib','sys','tarfile','tempfile',
            'threading','time','tkinter','traceback','typing','typing','unittest',
            'urllib','warnings','weakref','xml','xmltodict','zipfile','zlib', 'concurrent',
            'errno'
        }
        return common_stdlibs
    
    def is_standard_lib(self, module_name: str) -> bool:
        """检查是否是标准库模块"""
        root_module = module_name.split('.')[0]
        return root_module in self.standard_libs
    
    def find_module_file(self, module_name: str) -> Optional[Path]:
        """根据模块名找到对应的文件"""
        # 直接查找完整模块名
        if module_name in self.module_to_file:
            file_path = self.module_to_file[module_name]
            if file_path.exists():
                return file_path
        
        # 逐级查找父模块
        parts = module_name.split('.')
        for i in range(len(parts), 0, -1):
            parent_module = '.'.join(parts[:i])
            if parent_module in self.module_to_file:
                file_path = self.module_to_file[parent_module]
                
                if file_path.is_dir():
                    # 如果是目录，查找对应的 __init__.py 或子模块文件
                    init_file = file_path / '__init__.py'
                    if init_file.exists():
                        return init_file
                    
                    # 查找子模块文件
                    if i < len(parts):
                        submodule_file = file_path / f"{parts[i]}.py"
                        if submodule_file.exists():
                            return submodule_file
                elif file_path.exists():
                    return file_path
        
        # 尝试直接查找文件
        possible_paths = [
            self.root_dir / f"{module_name.replace('.', '/')}.py",
            self.root_dir / module_name.replace('.', '/') / "__init__.py"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def extract_imports_from_code(self, code: str, file_path: Path) -> Set[str]:
        """从代码中提取所有导入的模块"""
        imports = set()
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                        self.debug_print(f"  找到导入: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:  # 处理相对导入的情况
                        level = node.level
                        module_name = node.module
                        
                        if level > 0:
                            # 处理相对导入
                            current_dir = file_path.parent
                            for _ in range(level - 1):
                                current_dir = current_dir.parent
                            
                            # 构建绝对模块路径
                            module_parts = []
                            try:
                                rel_path = current_dir.relative_to(self.root_dir)
                                for part in rel_path.parts:
                                    module_parts.append(part)
                                
                                if node.module != '*':
                                    module_parts.extend(node.module.split('.'))
                                
                                absolute_module = '.'.join(module_parts)
                                imports.add(absolute_module)
                                self.debug_print(f"  相对导入 {level} 级: {module_name} -> {absolute_module}")
                            except ValueError as e:
                                # 如果无法计算相对路径，使用原始模块名
                                imports.add(module_name)
                                self.debug_print(f"  相对导入 (路径计算失败): {module_name}, 错误: {e}")
                        else:
                            imports.add(module_name)
                            self.debug_print(f"  绝对导入: from {module_name}")
        except SyntaxError as e:
            print(f"警告: 文件 {file_path} 语法解析失败: {e}")
            # 使用正则表达式作为备选
            import_pattern = re.compile(r'^\s*(?:import|from)\s+(\S+)')
            for line in code.split('\n'):
                match = import_pattern.match(line)
                if match:
                    module = match.group(1)
                    imports.add(module)
                    self.debug_print(f"  正则匹配导入: {module}")
                    
        return imports
    
    def find_python_files(self) -> List[Path]:
        """查找项目中的所有Python文件"""
        python_files = []
        
        try:
            for py_file in self.root_dir.rglob("*.py"):
                # 跳过隐藏文件和__pycache__目录
                if any(part.startswith('.') or part == '__pycache__' 
                       for part in py_file.parts):
                    continue
                python_files.append(py_file)
        except Exception as e:
            print(f"错误: 遍历目录时出错: {e}")
            
        self.debug_print(f"找到 {len(python_files)} 个Python文件:")
        for file in python_files:
            self.debug_print(f"  - {file.relative_to(self.root_dir)}")
            
        return python_files
    
    def build_module_mapping(self) -> Dict[str, Path]:
        """构建模块名到文件路径的映射"""
        python_files = self.find_python_files()
        module_to_file = {}
        
        for file_path in python_files:
            try:
                # 计算模块名（相对于根目录）
                rel_path = file_path.relative_to(self.root_dir)
                module_parts = []
                
                for part in rel_path.parts:
                    if part.endswith('.py'):
                        if part == '__init__.py':
                            module_parts.append(part[:-3])
                        else:
                            module_parts.append(part[:-3])
                    else:
                        module_parts.append(part)
                
                module_name = '.'.join(module_parts)
                module_to_file[module_name] = file_path
                self.debug_print(f"  模块映射: {module_name} -> {file_path}")
                
                # 如果文件是__init__.py，也把目录作为模块
                if file_path.name == '__init__.py':
                    package_name = '.'.join(module_parts[:-1]) if module_parts else ''
                    if package_name:
                        module_to_file[package_name] = file_path
                        self.debug_print(f"  包映射: {package_name} -> {file_path}")
                        
            except Exception as e:
                print(f"错误: 处理文件 {file_path} 时出错: {e}")
                continue
        
        self.module_to_file = module_to_file
        return module_to_file
    
    def build_import_graph(self):
        """构建导入依赖图"""
        self.build_module_mapping()
        python_files = self.find_python_files()
        
        print("开始构建导入依赖图...")
        
        # 分析每个文件的导入
        for file_path in python_files:
            self.debug_print(f"分析文件: {file_path.relative_to(self.root_dir)}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"错误: 无法读取文件 {file_path}: {e}")
                continue
            
            self.file_contents[file_path] = content
            imports = self.extract_imports_from_code(content, file_path)
            
            # 处理所有导入
            for import_name in imports:
                self.debug_print(f"  处理导入: {import_name}")
                
                if self.is_standard_lib(import_name):
                    self.debug_print(f"    跳过标准库: {import_name}")
                    continue
                
                # 查找对应的文件
                imported_file = self.find_module_file(import_name)
                
                if imported_file and imported_file.exists():
                    self.debug_print(f"    找到文件: {imported_file.relative_to(self.root_dir)}")
                    
                    if imported_file != file_path:
                        self.import_graph[file_path].add(imported_file)
                        self.reverse_graph[imported_file].add(file_path)
                        self.debug_print(f"    添加依赖: {file_path.name} -> {imported_file.name}")
                else:
                    self.debug_print(f"    警告: 未找到模块文件: {import_name}")
    
    def find_reachable_files(self) -> Set[Path]:
        """从入口文件开始，找到所有可达的文件（BFS遍历）"""
        start_files = []
        
        print(f"查找入口文件: {self.main_files}")
        
        # 找到所有入口文件
        for main_file in self.main_files:
            main_path = self.root_dir / main_file
            if main_path.exists() and main_path.is_file():
                start_files.append(main_path)
                print(f"找到入口文件: {main_file}")
            else:
                print(f"错误: 入口文件不存在或不是文件: {main_file}")
                print(f"搜索路径: {main_path}")
        
        if not start_files:
            print("错误: 未找到任何有效的入口文件")
            print("请检查入口文件路径是否正确")
            return set()
        
        # BFS遍历找到所有可达文件
        visited = set()
        queue = deque(start_files)
        
        print("开始BFS遍历依赖关系...")
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
                
            visited.add(current)
            print(f"可达文件: {current.relative_to(self.root_dir)}")
            
            # 添加当前文件依赖的所有文件到队列
            dependencies = self.import_graph.get(current, set())
            self.debug_print(f"  {current.name} 的依赖: {[d.name for d in dependencies]}")
            
            for dependency in dependencies:
                if dependency not in visited and dependency.exists():
                    queue.append(dependency)
                    self.debug_print(f"    添加到队列: {dependency.relative_to(self.root_dir)}")
        
        self.reachable_files = visited
        print(f"BFS遍历完成，找到 {len(visited)} 个可达文件")
        return visited
    
    def topological_sort(self) -> List[Path]:
        """对可达文件进行拓扑排序"""
        print("开始拓扑排序...")
        
        if not self.reachable_files:
            print("错误: 没有可达文件可排序")
            return []
        
        all_files = self.reachable_files
        in_degree = defaultdict(int)
        
        # 初始化可达文件的入度
        for file_path in all_files:
            in_degree[file_path] = 0
        
        # 计算入度
        for file_path in all_files:
            for dep in self.import_graph.get(file_path, set()):
                if dep in all_files:
                    in_degree[file_path] += 1
        
        print("入度计算完成:")
        for file_path, degree in sorted(in_degree.items(), key=lambda x: str(x[0])):
            rel_path = file_path.relative_to(self.root_dir)
            print(f"  {rel_path}: 入度={degree}")
        
        # 找到所有入度为0的文件
        queue = deque([file_path for file_path, degree in in_degree.items() if degree == 0])
        sorted_files = []
        
        print(f"初始入度为0的文件: {[f.relative_to(self.root_dir) for f in queue]}")
        
        while queue:
            current = queue.popleft()
            sorted_files.append(current)
            
            # 找到所有依赖当前文件的可达文件
            for dependent in self.reverse_graph.get(current, set()):
                if dependent in all_files and dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # 检查循环依赖
        if len(sorted_files) != len(all_files):
            print(f"警告: 检测到循环依赖，已排序 {len(sorted_files)}/{len(all_files)} 个文件")
            remaining = all_files - set(sorted_files)
            sorted_files.extend(remaining)
        
        print("\n拓扑排序结果:")
        for i, file_path in enumerate(sorted_files):
            rel_path = file_path.relative_to(self.root_dir)
            print(f"  {i+1:2d}. {rel_path}")
        
        return sorted_files
    
    def should_keep_import_line(self, line: str) -> bool:
        """判断是否应该保留导入语句"""
        stripped = line.strip()
        
        if not stripped:
            return True
            
        if stripped.startswith(('import ', 'from ')):
            if stripped.startswith('import '):
                modules = stripped[7:].split(',')
                for module in modules:
                    module_name = module.strip().split()[0].split('.')[0]
                    if self.is_standard_lib(module_name):
                        return True
                    else:
                        return False
            elif stripped.startswith('from '):
                parts = stripped[5:].split(' import ')
                if len(parts) == 2:
                    module_name = parts[0].strip().split('.')[0]
                    if self.is_standard_lib(module_name):
                        return True
                    else:
                        return False
            return False
            
        return True
    
    def clean_content(self, content: str) -> str:
        """清理文件内容，只移除项目内部的导入"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if self.should_keep_import_line(line):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def merge_files(self):
        """合并指定入口文件及其依赖的文件"""
        print("=" * 80)
        print("开始项目代码合并")
        print("=" * 80)
        
        print(f"项目根目录: {self.root_dir}")
        print(f"入口文件: {self.main_files}")
        print(f"输出文件: {self.output_file}")
        
        # 构建依赖图
        self.build_import_graph()
        
        # 查找可达文件
        self.find_reachable_files()
        
        if not self.reachable_files:
            print("错误: 没有找到任何可达文件，无法继续合并")
            return
        
        print(f"\n找到 {len(self.reachable_files)} 个需要合并的文件:")
        for file_path in sorted(self.reachable_files, key=lambda x: str(x)):
            print(f"  - {file_path.relative_to(self.root_dir)}")
        
        # 拓扑排序
        sorted_files = self.topological_sort()
        
        if not sorted_files:
            print("错误: 拓扑排序失败，没有文件可合并")
            return
        
        print(f"\n开始合并 {len(sorted_files)} 个文件...")
        
        # 合并文件
        try:
            with open(self.output_file, 'w', encoding='utf-8') as out_f:
                # 写入文件头
                out_f.write('# -*- coding: utf-8 -*-\n')
                out_f.write('"""\n')
                out_f.write('合并后的项目代码\n')
                out_f.write(f'源项目: {self.root_dir}\n')
                out_f.write(f'入口文件: {", ".join(self.main_files)}\n')
                out_f.write('自动生成 - 请勿直接编辑\n')
                out_f.write('"""\n\n')
                
                # 按照拓扑排序顺序写入文件内容
                files_merged = 0
                for file_path in sorted_files:
                    rel_path = file_path.relative_to(self.root_dir)
                    print(f"合并文件: {rel_path}")
                    
                    # 读取文件内容
                    content = ""
                    if file_path in self.file_contents:
                        content = self.file_contents[file_path]
                    else:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except Exception as e:
                            print(f"错误: 无法读取文件 {file_path}: {e}")
                            continue
                    
                    if not content.strip():
                        print(f"警告: 文件 {rel_path} 为空，跳过")
                        continue
                    
                    # 清理内容
                    cleaned_content = self.clean_content(content)
                    
                    # 写入文件分隔符和内容
                    out_f.write(f'\n\n# {"-" * 76}\n')
                    out_f.write(f'# 原文件: {rel_path}\n')
                    out_f.write(f'# {"-" * 76}\n\n')
                    out_f.write(cleaned_content)
                    
                    files_merged += 1
                    self.processed_files.add(file_path)
                
                print(f"\n合并完成! 成功合并 {files_merged} 个文件到: {self.output_file}")
                
                # 检查输出文件大小
                output_size = self.output_file.stat().st_size
                print(f"输出文件大小: {output_size} 字节")
                
                if output_size == 0:
                    print("警告: 输出文件为空!")
                    print("可能的原因:")
                    print("1. 入口文件不存在或路径错误")
                    print("2. 所有文件都是空的")
                    print("3. 依赖分析失败")
                    print("4. 编码问题导致文件读取失败")
                    
        except Exception as e:
            print(f"错误: 写入输出文件时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def validate_merge(self) -> bool:
        """验证合并后的文件"""
        if not self.output_file.exists():
            print(f"错误: 输出文件不存在: {self.output_file}")
            return False
        
        file_size = self.output_file.stat().st_size
        if file_size == 0:
            print(f"错误: 输出文件为空")
            return False
        
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                print("错误: 输出文件内容为空")
                return False
            
            # 检查语法
            ast.parse(content)
            print("语法验证通过!")
            return True
            
        except SyntaxError as e:
            print(f"语法错误: {e}")
            return False
        except Exception as e:
            print(f"验证文件时出错: {e}")
            return False

def main():
    if len(sys.argv) < 2:
        print("用法: python merge_project.py <项目根目录> [输出文件] [入口文件...]")
        print("示例: python merge_project.py . merged_project.py main.py")
        print("示例: python merge_project.py . merged_project.py app/main.py")
        sys.exit(1)
    
    root_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "merged_project.py"
    main_files = sys.argv[3:] if len(sys.argv) > 3 else ["main.py"]
    
    print(f"参数: 根目录={root_dir}, 输出={output_file}, 入口文件={main_files}")
    
    if not os.path.exists(root_dir):
        print(f"错误: 目录 '{root_dir}' 不存在")
        sys.exit(1)
    
    merger = PythonProjectMerger(root_dir, output_file, main_files=main_files, debug=False)
    
    try:
        merger.merge_files()
        
        if merger.output_file.exists() and merger.output_file.stat().st_size > 0:
            if merger.validate_merge():
                print("项目合并成功!")
            else:
                print("警告: 合并后的文件可能存在语法问题")
        else:
            print("错误: 合并失败，输出文件为空或不存在")
            print("请检查:")
            print("1. 入口文件路径是否正确")
            print("2. 项目是否有Python文件")
            print("3. 依赖关系是否正确")
            
    except Exception as e:
        print(f"合并过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
