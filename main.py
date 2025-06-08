#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @FileName:    main.py
# @Time:        2025/6/8 10:00
# @Author:      evansun
# @Project:     mainpage

from typing import List, Dict, Any
from pathlib import Path
import logging

from utils import FileManager, init_logging, get_logger, PriceManager
from utils.image_processor import ImageProcessor


class Config:
    """配置常量"""

    SOURCE_DATA_KEY = "product_image"
    PRICE_TEXT_KEY = "price_text"
    DEFAULT_CONFIG_PATH = "config.yaml"
    DEFAULT_PRICE_PATH = "prices.yaml"
    RESULT_DIR = "result_data"
    PROCESSED_SUFFIX = "_processed.png"


def setup_logging() -> logging.Logger:
    """设置日志系统"""
    init_logging()
    return get_logger("main")


def setup_processor(config_path: str = Config.DEFAULT_CONFIG_PATH) -> ImageProcessor:
    """设置图片处理器

    Args:
        config_path: 配置文件路径

    Returns:
        ImageProcessor: 配置好的图片处理器实例

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: 配置文件格式错误
    """
    try:
        processor = ImageProcessor(config_path)

        # 显示配置预览
        logger = get_logger("main")
        logger.info("📋 图层配置预览:")
        layers_info = processor.preview_layers()
        for layer_name, info in layers_info.items():
            logger.info(f"  {layer_name}: {info}")

        return processor

    except FileNotFoundError as e:
        raise FileNotFoundError(f"配置文件不存在: {config_path}") from e
    except Exception as e:
        raise RuntimeError(f"处理器初始化失败: {e}") from e


def process_single_image(
    processor: ImageProcessor, image_file: Path, price_manager: PriceManager, logger: logging.Logger
) -> bool:
    """处理单个图片文件
    
    Args:
        processor: 图片处理器实例
        image_file: 图片文件路径
        price_manager: 价格管理器实例
        logger: 日志记录器
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 提取货号（文件名不含扩展名）
        product_code = image_file.stem
        logger.info(f"🖼️  处理商品: {product_code}")

        # 获取商品价格
        price_text = price_manager.get_price(product_code)
        logger.debug(f"获取价格: {product_code} -> {price_text}")

        # 设置商品图片路径、文字内容和价格信息
        processor.update_source_data(
            {
                Config.SOURCE_DATA_KEY: str(image_file),
                Config.PRICE_TEXT_KEY: price_text,
            }
        )

        # 构建输出路径 - 保存到对应的result_data文件夹
        result_dir = Path(Config.RESULT_DIR) / product_code
        output_path = result_dir / f"{product_code}{Config.PROCESSED_SUFFIX}"

        # 确保输出目录存在
        result_dir.mkdir(parents=True, exist_ok=True)

        # 获取配置的画布和质量设置
        config = processor.config
        canvas_size = tuple(config.get("canvas_size", [1000, 1000]))
        background_color = tuple(config.get("background_color", [255, 255, 255, 255]))

        # 创建合成图片
        success = processor.create_composite_image(
            str(output_path),
            canvas_size=canvas_size,
            background_color=background_color,
        )

        if success:
            logger.info(f"  ✅ 成功: {output_path}")
            return True
        else:
            logger.error(f"  ❌ 失败: {product_code}")
            return False

    except OSError as e:
        logger.error(f"  ❌ 文件操作错误 {image_file.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ 处理 {image_file.name} 时发生未知错误: {e}")
        return False


def generate_processing_report(
    success_count: int, failed_count: int, logger: logging.Logger
) -> None:
    """生成处理结果报告

    Args:
        success_count: 成功处理的图片数量
        failed_count: 失败处理的图片数量
        logger: 日志记录器
    """
    logger.info(f"📊 图片处理完成:")
    logger.info(f"  ✅ 成功处理: {success_count} 个")
    logger.info(f"  ❌ 处理失败: {failed_count} 个")
    logger.info(f"  📁 输出目录: {Config.RESULT_DIR}/[货号]/")

    # 显示处理结果文件列表
    if success_count > 0:
        logger.info(f"📁 生成的文件:")
        result_base = Path(Config.RESULT_DIR)
        try:
            for product_dir in result_base.iterdir():
                if product_dir.is_dir():
                    logger.info(f"  📂 {product_dir.name}/")
                    for file in product_dir.iterdir():
                        if file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                            logger.info(f"    🖼️  {file.name}")
        except OSError as e:
            logger.warning(f"读取结果目录时出错: {e}")


def process_images_with_layers(
    file_manager: FileManager, image_files: List[Path]
) -> None:
    """使用图层配置处理商品图片

    Args:
        file_manager: 文件管理器实例
        image_files: 待处理的图片文件列表

    Raises:
        RuntimeError: 图片处理过程中发生严重错误
    """
    logger = get_logger("main")

    try:
        # 初始化图片处理器
        processor = setup_processor()
        
        # 初始化价格管理器
        price_manager = PriceManager(Config.DEFAULT_PRICE_PATH)
        
        # 显示价格统计信息
        price_stats = price_manager.get_price_statistics()
        logger.info(f"💰 价格管理器统计:")
        logger.info(f"  商品数量: {price_stats['total_products']} 个")
        logger.info(f"  价格范围: {price_stats['price_range']}")
        if price_stats['total_products'] > 0:
            logger.info(f"  平均价格: ¥{price_stats['average_price']:.2f}")

        success_count = 0
        failed_count = 0

        # 处理每个商品图片
        for image_file in image_files:
            if process_single_image(processor, image_file, price_manager, logger):
                success_count += 1
            else:
                failed_count += 1

        # 生成处理结果报告
        generate_processing_report(success_count, failed_count, logger)

    except (FileNotFoundError, RuntimeError) as e:
        logger.error(f"图片处理器设置失败: {e}")
        raise
    except Exception as e:
        logger.error(f"图片处理过程中发生未知错误: {e}")
        raise RuntimeError(f"图片处理失败: {e}") from e


def main() -> None:
    """批量修图程序主函数"""
    logger = setup_logging()

    try:
        # 创建文件管理器实例
        file_manager = FileManager()

        # 获取文件信息
        info = file_manager.get_file_info()

        # 显示发现的文件
        logger.info(f"发现图片文件: {info['total_images']} 个")
        image_files = file_manager.get_all_image_files()
        logger.info("文件列表:")
        for i, file_path in enumerate(image_files, 1):
            logger.info(f"  {i:2d}. {file_path.name}")

        if not image_files:
            logger.warning("未发现任何图片文件，程序退出")
            return

        # 执行完整的文件处理流程（创建文件夹结构）
        result = file_manager.process_all()

        if result["success"]:
            logger.info(f"文件夹创建完成:")
            logger.info(f"  货号数量: {result['total_products']} 个")
            logger.info(f"  创建文件夹: {result['created_folders']} 个")
            logger.info(f"  货号列表: {', '.join(result['product_codes'])}")

            # 开始图片处理
            logger.info("🎨 开始图片处理...")
            process_images_with_layers(file_manager, image_files)

        else:
            error_msg = result.get("message", "未知错误")
            logger.error(f"文件夹创建失败: {error_msg}")
            raise RuntimeError(f"文件夹创建失败: {error_msg}")

    except FileNotFoundError as e:
        logger.error(f"文件错误: {e}")
        raise
    except RuntimeError as e:
        logger.error(f"运行时错误: {e}")
        raise
    except Exception as e:
        logger.error(f"程序运行发生未知错误: {e}")
        raise RuntimeError(f"程序执行失败: {e}") from e


if __name__ == "__main__":
    main()
