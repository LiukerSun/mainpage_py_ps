#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @FileName:    file_manager.py
# @Time:        2025/6/8 10:00
# @Author:      evansun
# @Project:     mainpage

from pathlib import Path
from typing import List, Set, Dict, Any, Optional
import yaml
import shutil
from tqdm import tqdm

from .logger import get_logger


class FileManager:
    """文件管理类，用于批量修图程序的文件操作"""

    def __init__(
        self,
        source_dir: str = "source_data",
        result_dir: str = "result_data",
        config_file: str = "config.yaml",
    ) -> None:
        """
        初始化文件管理器

        Args:
            source_dir: 源文件目录路径
            result_dir: 结果文件目录路径
            config_file: 配置文件路径

        Raises:
            FileNotFoundError: 源目录不存在
        """
        self.source_dir = Path(source_dir)
        self.result_dir = Path(result_dir)
        self.config_file = Path(config_file)
        self.logger = get_logger("file_manager")

        # 支持的图片格式
        self.supported_formats = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

        # 加载配置文件
        self.config = self._load_config()

        # 确保目录存在
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        """
        加载YAML配置文件

        Returns:
            Dict[str, Any]: 配置字典

        Raises:
            yaml.YAMLError: YAML格式错误
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"成功加载配置文件: {self.config_file}")
                return config or {}
            else:
                self.logger.warning(f"配置文件不存在: {self.config_file}")
                return {}
        except yaml.YAMLError as e:
            self.logger.error(f"配置文件格式错误 {self.config_file}: {e}")
            raise
        except OSError as e:
            self.logger.error(f"读取配置文件失败 {self.config_file}: {e}")
            return {}

    def _ensure_directories(self) -> None:
        """
        确保源目录和结果目录存在

        Raises:
            FileNotFoundError: 源目录不存在
            OSError: 创建结果目录失败
        """
        if not self.source_dir.exists():
            raise FileNotFoundError(f"源目录不存在: {self.source_dir}")

        # 创建结果目录（如果不存在）
        try:
            self.result_dir.mkdir(exist_ok=True)
            self.logger.info(f"结果目录准备完成: {self.result_dir}")
        except OSError as e:
            self.logger.error(f"创建结果目录失败: {e}")
            raise

    def get_all_image_files(self) -> List[Path]:
        """
        获取源目录中的所有图片文件

        Returns:
            List[Path]: 图片文件路径列表

        Raises:
            OSError: 读取目录失败
        """
        image_files = []

        try:
            # 检查源目录是否存在
            if not self.source_dir.exists():
                self.logger.error(f"源目录不存在: {self.source_dir}")
                return []

            # 检查源目录是否是目录
            if not self.source_dir.is_dir():
                self.logger.error(f"源路径不是目录: {self.source_dir}")
                return []

            # 遍历目录获取图片文件
            for file_path in self.source_dir.iterdir():
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.supported_formats
                ):
                    image_files.append(file_path)

            # 记录找到的文件数量
            file_count = len(image_files)
            if file_count > 0:
                self.logger.info(f"发现 {file_count} 个图片文件")
            else:
                self.logger.warning(f"在目录 {self.source_dir} 中未找到任何图片文件")

            return sorted(image_files)

        except OSError as e:
            self.logger.error(f"读取源目录失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"获取图片文件时发生未知错误: {e}")
            return []

    def get_main_image_file_for_product(self, product_code: str) -> Optional[Path]:
        """
        获取指定货号的主图片文件
        优先级：货号_1 > 货号（无后缀）

        Args:
            product_code: 商品货号

        Returns:
            Optional[Path]: 主图片文件路径，如果未找到返回None
        """
        try:
            # 候选文件列表，按优先级排序
            candidates = []
            
            for file_path in self.source_dir.iterdir():
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.supported_formats
                ):
                    file_stem = file_path.stem
                    
                    # 检查是否匹配该货号
                    if file_stem == f"{product_code}_1":
                        # 最高优先级：货号_1
                        candidates.insert(0, file_path)
                    elif file_stem == product_code:
                        # 次优先级：货号（无后缀）
                        candidates.append(file_path)
            
            if candidates:
                main_file = candidates[0]
                self.logger.debug(f"货号 {product_code} 的主图片: {main_file.name}")
                return main_file
            else:
                self.logger.warning(f"未找到货号 {product_code} 的主图片文件")
                return None
                
        except OSError as e:
            self.logger.error(f"查找货号 {product_code} 主图片失败: {e}")
            return None

    def get_main_image_files(self) -> List[Path]:
        """
        获取所有货号的主图片文件

        Returns:
            List[Path]: 主图片文件路径列表

        Raises:
            OSError: 读取目录失败
        """
        product_codes = self.extract_product_codes()
        main_files = []
        
        for product_code in product_codes:
            main_file = self.get_main_image_file_for_product(product_code)
            if main_file:
                main_files.append(main_file)
        
        self.logger.info(f"发现 {len(main_files)} 个主图片文件")
        return sorted(main_files)

    def extract_product_codes(self) -> Set[str]:
        """
        从图片文件名中提取所有商品货号
        支持两种格式：
        1. 单张图片：A1079.jpg -> 货号: A1079
        2. 多张图片：D010_1.jpg, D010_2.jpg -> 货号: D010

        Returns:
            Set[str]: 去重后的商品货号集合
        """
        try:
            # 获取所有图片文件
            image_files = self.get_all_image_files()
            if not image_files:
                self.logger.warning("未找到任何图片文件，无法提取货号")
                return set()

            product_codes = set()

            for file_path in image_files:
                # 提取文件名（不包含扩展名）作为基础货号
                file_stem = file_path.stem
                
                # 检查是否有下划线加数字的后缀模式
                if '_' in file_stem and file_stem.split('_')[-1].isdigit():
                    # 如果是 货号_数字 的格式，提取货号部分
                    product_code = file_stem.rsplit('_', 1)[0]
                else:
                    # 如果没有后缀，整个文件名就是货号
                    product_code = file_stem

                # 验证货号有效性
                if self._is_valid_product_code(product_code):
                    product_codes.add(product_code)

            # 记录提取到的货号数量
            code_count = len(product_codes)
            if code_count > 0:
                self.logger.info(f"提取到 {code_count} 个有效货号")
            else:
                self.logger.warning("未找到任何有效的商品货号")

            return product_codes

        except Exception as e:
            self.logger.error(f"提取商品货号时发生错误: {e}")
            return set()

    def get_product_related_files(self, product_code: str) -> List[Path]:
        """
        获取某个货号相关的所有图片文件

        Args:
            product_code: 商品货号

        Returns:
            List[Path]: 该货号相关的所有图片文件路径列表
        """
        related_files = []
        
        try:
            for file_path in self.source_dir.iterdir():
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.supported_formats
                ):
                    file_stem = file_path.stem
                    
                    # 检查文件名是否匹配该货号
                    # 可能的格式：货号、货号_1、货号_2等
                    if file_stem == product_code or file_stem.startswith(f"{product_code}_"):
                        related_files.append(file_path)
            
            self.logger.debug(f"货号 {product_code} 找到 {len(related_files)} 个相关文件")
            return sorted(related_files)
            
        except OSError as e:
            self.logger.error(f"查找货号 {product_code} 相关文件失败: {e}")
            return []

    def copy_product_files_to_folder(self, product_code: str, target_folder: Path) -> Dict[str, Any]:
        """
        将某个货号的所有相关图片文件复制到目标文件夹

        Args:
            product_code: 商品货号
            target_folder: 目标文件夹路径

        Returns:
            Dict[str, Any]: 复制结果统计
        """
        related_files = self.get_product_related_files(product_code)
        
        if not related_files:
            return {
                "success": False,
                "message": f"未找到货号 {product_code} 的相关文件",
                "copied": 0,
                "main_image": None
            }
        
        copied_count = 0
        main_image_file = None
        
        try:
            # 确保目标文件夹存在
            target_folder.mkdir(parents=True, exist_ok=True)
            
            for file_path in related_files:
                # 目标文件路径
                target_path = target_folder / file_path.name
                
                # 复制文件
                import shutil
                shutil.copy2(file_path, target_path)
                copied_count += 1
                
                self.logger.debug(f"复制文件: {file_path.name} -> {target_path}")
            
            # 获取主图片文件（使用新的方法）
            main_image_file = self.get_main_image_file_for_product(product_code)
            
            self.logger.info(f"货号 {product_code} 复制了 {copied_count} 个文件到 {target_folder}")
            
            return {
                "success": True,
                "copied": copied_count,
                "main_image": main_image_file,
                "all_files": related_files
            }
            
        except OSError as e:
            self.logger.error(f"复制货号 {product_code} 文件失败: {e}")
            return {
                "success": False,
                "message": f"复制失败: {e}",
                "copied": copied_count,
                "main_image": main_image_file
            }

    def _is_valid_product_code(self, code: str) -> bool:
        """
        验证货号是否有效

        Args:
            code: 待验证的货号字符串

        Returns:
            bool: 是否为有效货号
        """
        # 基本验证：非空且长度合理
        if not code or len(code) < 2:
            return False

        # 可以根据实际业务规则添加更多验证
        # 例如：货号必须以字母开头，包含数字等
        # pattern = r'^[A-Z]\d+$'  # 示例：A开头后跟数字
        # return bool(re.match(pattern, code))

        return True

    def _copy_files_to_folder(self, target_folder: Path) -> Dict[str, Any]:
        """
        将配置文件中指定的文件复制到目标文件夹

        Args:
            target_folder: 目标文件夹路径

        Returns:
            Dict[str, Any]: 复制结果统计
        """
        copy_files = self.config.get("copy_files", [])
        copy_settings = self.config.get("copy_settings", {})

        if not copy_files:
            return {"success": True, "copied": 0, "failed": 0, "skipped": 0}

        overwrite = copy_settings.get("overwrite", False)
        continue_on_error = copy_settings.get("continue_on_error", True)

        copied_count = 0
        failed_count = 0
        skipped_count = 0

        for file_config in copy_files:
            try:
                source_path = Path(file_config["source"])

                # 检查源文件是否存在
                if not source_path.exists():
                    self.logger.warning(f"源文件不存在: {source_path}")
                    failed_count += 1
                    if not continue_on_error:
                        break
                    continue

                # 目标文件路径
                target_path = target_folder / source_path.name

                # 检查目标文件是否已存在
                if target_path.exists() and not overwrite:
                    skipped_count += 1
                    continue

                # 复制文件
                shutil.copy2(source_path, target_path)
                copied_count += 1

            except KeyError as e:
                self.logger.error(f"配置文件格式错误，缺少必要字段: {e}")
                failed_count += 1
                if not continue_on_error:
                    break
            except OSError as e:
                self.logger.error(f"文件复制失败 {source_path}: {e}")
                failed_count += 1
                if not continue_on_error:
                    break

        return {
            "success": failed_count == 0 or continue_on_error,
            "copied": copied_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }

    def create_product_folders(self, product_codes: Set[str]) -> List[Path]:
        """
        根据商品货号批量创建文件夹并复制配置文件

        Args:
            product_codes: 商品货号集合

        Returns:
            List[Path]: 创建的文件夹路径列表
        """
        created_folders = []
        product_list = sorted(product_codes)

        # 使用tqdm显示进度条
        for product_code in tqdm(product_list, desc="创建文件夹", unit="个", ncols=80):
            folder_path = self.result_dir / product_code

            try:
                folder_path.mkdir(exist_ok=True)
                created_folders.append(folder_path)

                # 复制配置文件中指定的文件
                copy_result = self._copy_files_to_folder(folder_path)
                if copy_result["copied"] > 0:
                    self.logger.debug(
                        f"为 {product_code} 复制了 {copy_result['copied']} 个文件"
                    )

            except OSError as e:
                self.logger.error(f"创建文件夹失败 {product_code}: {e}")

        self.logger.info(f"成功创建 {len(created_folders)} 个产品文件夹")
        return created_folders

    def get_file_info(self) -> Dict[str, Any]:
        """
        获取文件统计信息

        Returns:
            Dict[str, Any]: 包含文件统计信息的字典
        """
        try:
            # 获取所有图片文件
            image_files = self.get_all_image_files()
            if not image_files:
                self.logger.warning("未找到任何图片文件")
                return {
                    "total_images": 0,
                    "total_products": 0,
                    "source_directory": str(self.source_dir),
                    "result_directory": str(self.result_dir),
                    "supported_formats": list(self.supported_formats),
                    "product_codes": [],
                    "config_loaded": bool(self.config),
                    "copy_files": [],
                }

            # 提取商品货号
            product_codes = self.extract_product_codes()
            if not product_codes:
                self.logger.warning("未找到任何有效的商品货号")
                return {
                    "total_images": len(image_files),
                    "total_products": 0,
                    "source_directory": str(self.source_dir),
                    "result_directory": str(self.result_dir),
                    "supported_formats": list(self.supported_formats),
                    "product_codes": [],
                    "config_loaded": bool(self.config),
                    "copy_files": [],
                }

            # 安全地获取copy_files列表
            copy_files = []
            if self.config and isinstance(self.config, dict):
                copy_files_config = self.config.get("copy_files")
                if isinstance(copy_files_config, list):
                    copy_files = [f for f in copy_files_config if isinstance(f, dict) and f.get("source")]

            # 返回完整的统计信息
            return {
                "total_images": len(image_files),
                "total_products": len(product_codes),
                "source_directory": str(self.source_dir),
                "result_directory": str(self.result_dir),
                "supported_formats": list(self.supported_formats),
                "product_codes": sorted(list(product_codes)),
                "config_loaded": bool(self.config),
                "copy_files": copy_files,
            }

        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return {
                "total_images": 0,
                "total_products": 0,
                "source_directory": str(self.source_dir),
                "result_directory": str(self.result_dir),
                "supported_formats": list(self.supported_formats),
                "product_codes": [],
                "config_loaded": False,
                "copy_files": [],
                "error": str(e),
            }

    def process_all(self) -> Dict[str, Any]:
        """
        执行完整的文件处理流程

        Returns:
            Dict[str, Any]: 处理结果统计信息
        """
        try:
            # 1. 提取所有货号
            product_codes = self.extract_product_codes()

            if not product_codes:
                return {"success": False, "message": "未找到有效的商品货号"}

            # 2. 创建文件夹并复制文件
            created_folders = self.create_product_folders(product_codes)

            # 3. 返回处理结果
            result = {
                "success": True,
                "total_products": len(product_codes),
                "created_folders": len(created_folders),
                "product_codes": sorted(list(product_codes)),
                "folder_paths": [str(path) for path in created_folders],
                "config_loaded": bool(self.config),
            }

            self.logger.info(
                f"文件处理流程完成: 创建了 {len(created_folders)} 个文件夹"
            )
            return result

        except Exception as e:
            self.logger.error(f"文件处理流程失败: {e}")
            return {
                "success": False,
                "message": f"处理失败: {e}",
                "total_products": 0,
                "created_folders": 0,
                "product_codes": [],
                "folder_paths": [],
                "config_loaded": bool(self.config),
            }
