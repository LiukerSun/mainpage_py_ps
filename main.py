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
        # 提取货号（文件名不含扩展名，去掉_1后缀）
        file_stem = image_file.stem
        if file_stem.endswith('_1'):
            product_code = file_stem[:-2]  # 去掉最后的"_1"
        else:
            product_code = file_stem
            
        logger.info(f"🖼️  处理商品: {product_code} (来源文件: {image_file.name})")

        # 获取商品价格
        price_text = price_manager.get_price(product_code)
        logger.debug(f"获取价格: {product_code} -> {price_text}")

        # 设置商品图片路径、文字内容和价格信息
        processor.update_source_data(
            {
                Config.SOURCE_DATA_KEY: str(image_file),
                Config.PRICE_TEXT_KEY: price_text,
                "file_name": image_file.stem,  # 添加文件名（不含扩展名）
            }
        )

        # 构建输出路径 - 保存到对应的result_data文件夹
        result_dir = Path(Config.RESULT_DIR) / product_code
        output_path = result_dir / f"{product_code}{Config.PROCESSED_SUFFIX}"

        # 确保输出目录存在
        result_dir.mkdir(parents=True, exist_ok=True)

        # 获取配置的背景颜色
        config = processor.config
        background_color = tuple(config.get("background_color", [255, 255, 255, 255]))

        # 创建合成图片
        success = processor.create_composite_image(
            str(output_path),
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


def process_single_product(
    processor: ImageProcessor, 
    file_manager: FileManager, 
    product_code: str, 
    price_manager: PriceManager, 
    logger: logging.Logger
) -> bool:
    """处理单个货号的所有相关图片
    
    Args:
        processor: 图片处理器实例
        file_manager: 文件管理器实例
        product_code: 商品货号
        price_manager: 价格管理器实例
        logger: 日志记录器
        
    Returns:
        bool: 处理是否成功
    """
    try:
        logger.info(f"🛍️  处理商品货号: {product_code}")
        
        # 检查是否有价格
        if not price_manager.has_price(product_code):
            logger.warning(f"  ⚠️  跳过商品 {product_code}：未找到价格信息")
            return False
        
        # 获取结果目录
        result_dir = Path(Config.RESULT_DIR) / product_code
        
        # 复制该货号的所有相关图片文件到结果文件夹
        copy_result = file_manager.copy_product_files_to_folder(product_code, result_dir)
        
        if not copy_result["success"]:
            logger.error(f"  ❌ 复制文件失败: {copy_result.get('message', '未知错误')}")
            return False
        
        logger.info(f"  📁 复制了 {copy_result['copied']} 个文件到 {result_dir}")
        
        # 获取主图片文件（_1结尾的）
        main_image_file = copy_result["main_image"]
        
        if not main_image_file:
            logger.warning(f"  ⚠️  未找到货号 {product_code} 的主图片文件（_1结尾）")
            return False
        
        logger.info(f"  🖼️  处理主图片: {main_image_file.name}")
        
        # 获取商品价格
        price_text = price_manager.get_price(product_code)
        logger.debug(f"获取价格: {product_code} -> {price_text}")

        # 设置商品图片路径、文字内容和价格信息
        processor.update_source_data(
            {
                Config.SOURCE_DATA_KEY: str(main_image_file),
                Config.PRICE_TEXT_KEY: price_text,
                "file_name": main_image_file.stem,  # 添加文件名（不含扩展名）
            }
        )

        # 构建修图输出路径
        processed_output_path = result_dir / f"{product_code}{Config.PROCESSED_SUFFIX}"

        # 获取配置的背景颜色
        config = processor.config
        background_color = tuple(config.get("background_color", [255, 255, 255, 255]))

        # 创建合成图片
        success = processor.create_composite_image(
            str(processed_output_path),
            background_color=background_color,
        )

        if success:
            logger.info(f"  ✅ 修图成功: {processed_output_path.name}")
            logger.info(f"  📷 原图保留: {main_image_file.name}")
            return True
        else:
            logger.error(f"  ❌ 修图失败: {product_code}")
            return False

    except OSError as e:
        logger.error(f"  ❌ 文件操作错误 {product_code}: {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ 处理货号 {product_code} 时发生未知错误: {e}")
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
    file_manager: FileManager, product_codes: List[str]
) -> None:
    """使用图层配置处理商品图片

    Args:
        file_manager: 文件管理器实例
        product_codes: 待处理的商品货号列表
    """
    logger = get_logger("main")

    try:
        # 初始化图片处理器
        processor = setup_processor()
        if not processor:
            logger.error("❌ 图片处理器初始化失败，程序退出")
            return
        
        # 初始化价格管理器
        price_manager = PriceManager(Config.DEFAULT_PRICE_PATH)
        if not price_manager:
            logger.error("❌ 价格管理器初始化失败，程序退出")
            return
        
        # 显示价格统计信息
        price_stats = price_manager.get_price_statistics()
        logger.info(f"💰 价格管理器统计:")
        logger.info(f"  商品数量: {price_stats['total_products']} 个")
        logger.info(f"  价格范围: {price_stats['price_range']}")
        if price_stats['total_products'] > 0:
            logger.info(f"  平均价格: ¥{price_stats['average_price']:.2f}")

        # 过滤掉没有价格的商品
        valid_product_codes = []
        skipped_product_codes = []
        for product_code in product_codes:
            if price_manager.has_price(product_code):
                valid_product_codes.append(product_code)
            else:
                skipped_product_codes.append(product_code)
                logger.warning(f"⚠️  跳过商品 {product_code}：未找到价格信息")

        if skipped_product_codes:
            logger.info(f"📋 跳过的商品（无价格）: {', '.join(skipped_product_codes)}")
        
        if not valid_product_codes:
            logger.error("❌ 没有找到任何有价格的商品，程序退出")
            return

        logger.info(f"🎨 开始处理 {len(valid_product_codes)} 个有价格的商品...")
        success_count = 0
        failed_count = 0

        # 按货号处理商品
        for product_code in valid_product_codes:
            if process_single_product(processor, file_manager, product_code, price_manager, logger):
                success_count += 1
            else:
                failed_count += 1
                logger.error(f"❌ 处理商品 {product_code} 失败")

        # 生成处理结果报告
        generate_processing_report(success_count, failed_count, logger)

    except FileNotFoundError as e:
        logger.error(f"❌ 图片处理器设置失败: {e}")
        return
    except Exception as e:
        logger.error(f"❌ 图片处理过程中发生未知错误: {e}")
        return


def main() -> None:
    """批量修图程序主函数"""
    logger = setup_logging()

    try:
        # 创建文件管理器实例
        file_manager = FileManager()

        # 获取文件信息
        info = file_manager.get_file_info()
        if not info or info.get('total_images', 0) == 0:
            logger.error("❌ 获取文件信息失败，程序退出")
            return

        # 显示发现的文件（只处理以_1结尾的主图片）
        logger.info(f"发现图片文件: {info['total_images']} 个")
        image_files = file_manager.get_main_image_files()  # 改为获取主图片文件
        if not image_files:
            logger.error("❌ 未找到任何主图片文件，程序退出")
            return

        logger.info(f"需要处理的主图片文件: {len(image_files)} 个")
        logger.info("文件列表:")
        for i, file_path in enumerate(image_files, 1):
            logger.info(f"  {i:2d}. {file_path.name}")

        # 执行完整的文件处理流程（创建文件夹结构）
        result = file_manager.process_all()

        if not result["success"]:
            error_msg = result.get("message", "未知错误")
            logger.error(f"❌ 文件夹创建失败: {error_msg}")
            return

        logger.info(f"文件夹创建完成:")
        logger.info(f"  货号数量: {result['total_products']} 个")
        logger.info(f"  创建文件夹: {result['created_folders']} 个")
        logger.info(f"  货号列表: {', '.join(result['product_codes'])}")

        # 开始图片处理
        logger.info("🎨 开始图片处理...")
        product_codes = list(result['product_codes'])
        process_images_with_layers(file_manager, product_codes)

    except FileNotFoundError as e:
        logger.error(f"❌ 文件错误: {e}")
        return
    except RuntimeError as e:
        logger.error(f"❌ 运行时错误: {e}")
        return
    except Exception as e:
        logger.error(f"❌ 程序运行发生未知错误: {e}")
        return


if __name__ == "__main__":
    main()
