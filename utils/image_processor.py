#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import re
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import logging

from .logger import get_logger


class ImageProcessor:
    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config = self.load_config(config_path)
        self.logger = get_logger("image_processor")
        self.source_data = self.config.get("source_data", {})
        self.supported_formats = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def setup_logger(self) -> logging.Logger:
        """设置日志记录器（已弃用，使用统一日志系统）"""
        return get_logger("image_processor")

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            Dict[str, Any]: 配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: 配置文件格式错误
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config or {}
        except FileNotFoundError as e:
            error_msg = f"配置文件 {config_path} 不存在"
            if hasattr(self, "logger"):
                self.logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e
        except yaml.YAMLError as e:
            error_msg = f"配置文件解析错误: {e}"
            if hasattr(self, "logger"):
                self.logger.error(error_msg)
            raise yaml.YAMLError(error_msg) from e
        except OSError as e:
            error_msg = f"读取配置文件失败: {e}"
            if hasattr(self, "logger"):
                self.logger.error(error_msg)
            return {}

    def resolve_variables(self, text: str) -> str:
        """
        解析配置中的变量，如 ${product_image}

        Args:
            text: 待解析的文本字符串

        Returns:
            str: 解析后的文本
        """
        if not isinstance(text, str):
            return text

        def replace_var(match):
            var_name = match.group(1)
            return str(self.source_data.get(var_name, f"${{{var_name}}}"))

        return re.sub(r"\$\{([^}]+)\}", replace_var, text)

    def get_font(self, size: int = 32) -> ImageFont.FreeTypeFont:
        """
        获取字体对象

        Args:
            size: 字体大小

        Returns:
            ImageFont.FreeTypeFont: 字体对象
        """
        try:
            # 尝试不同的字体路径
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/arial.ttf",  # Arial
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)

            # 如果都不存在，使用默认字体
            self.logger.warning("未找到系统字体，使用默认字体")
            return ImageFont.load_default()

        except OSError as e:
            self.logger.warning(f"字体加载失败，使用默认字体: {e}")
            return ImageFont.load_default()

    def calculate_text_position(
        self,
        image_size: Tuple[int, int],
        text_size: Tuple[int, int],
        position: str,
        margin_x: int = 10,
        margin_y: int = 10,
    ) -> Tuple[int, int]:
        """
        计算文字位置

        Args:
            image_size: 图片尺寸 (宽, 高)
            text_size: 文字尺寸 (宽, 高)
            position: 位置字符串
            margin_x: X轴边距
            margin_y: Y轴边距

        Returns:
            Tuple[int, int]: 计算后的位置坐标 (x, y)
        """
        img_width, img_height = image_size
        text_width, text_height = text_size

        positions = {
            "top_left": (margin_x, margin_y),
            "top_center": ((img_width - text_width) // 2, margin_y),
            "top_right": (img_width - text_width - margin_x, margin_y),
            "center_left": (margin_x, (img_height - text_height) // 2),
            "center": ((img_width - text_width) // 2, (img_height - text_height) // 2),
            "center_right": (
                img_width - text_width - margin_x,
                (img_height - text_height) // 2,
            ),
            "bottom_left": (margin_x, img_height - text_height - margin_y),
            "bottom_center": (
                (img_width - text_width) // 2,
                img_height - text_height - margin_y,
            ),
            "bottom_right": (
                img_width - text_width - margin_x,
                img_height - text_height - margin_y,
            ),
        }

        return positions.get(position, positions["bottom_right"])

    def add_text_layer(
        self, base_image: Image.Image, layer_config: Dict[str, Any]
    ) -> Image.Image:
        """
        添加文字图层

        Args:
            base_image: 基础图片
            layer_config: 图层配置字典

        Returns:
            Image.Image: 添加文字后的图片
        """
        try:
            # 获取文字内容
            text = self.resolve_variables(layer_config.get("text", ""))
            if not text:
                self.logger.warning("文字内容为空，跳过文字图层")
                return base_image

            # 获取文字配置
            font_size = layer_config.get("font_size", 32)
            font_color = tuple(layer_config.get("font_color", [0, 0, 0, 255]))
            
            # 支持两种定位方式：绝对坐标或相对位置
            if "x" in layer_config and "y" in layer_config:
                # 使用绝对坐标
                use_absolute_position = True
                x = layer_config.get("x", 0)
                y = layer_config.get("y", 0)
            else:
                # 使用相对位置
                use_absolute_position = False
                position = layer_config.get("position", "bottom_right")
                margin_x = layer_config.get("margin_x", 10)
                margin_y = layer_config.get("margin_y", 10)

            # 创建绘制对象
            if base_image.mode != "RGBA":
                base_image = base_image.convert("RGBA")

            # 创建文字图层
            txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            font = self.get_font(font_size)

            # 计算文字尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 根据定位方式计算文字位置
            if use_absolute_position:
                # 使用绝对坐标（直接使用配置的x, y坐标）
                self.logger.debug(f"使用绝对坐标定位: ({x}, {y})")
            else:
                # 使用相对位置计算
                x, y = self.calculate_text_position(
                    base_image.size, (text_width, text_height), position, margin_x, margin_y
                )
                self.logger.debug(f"使用相对位置定位: {position} -> ({x}, {y})")

            # 绘制文字
            draw.text((x, y), text, font=font, fill=font_color)

            # 合成图层
            result = Image.alpha_composite(base_image, txt_layer)

            if use_absolute_position:
                self.logger.info(f"成功添加文字图层: '{text}' 在坐标 ({x}, {y})")
            else:
                self.logger.info(f"成功添加文字图层: '{text}' 在位置 {position}")
            return result

        except OSError as e:
            self.logger.error(f"文字图层文件操作失败: {e}")
            return base_image
        except Exception as e:
            self.logger.error(f"添加文字图层失败: {e}")
            return base_image

    def add_image_layer(
        self, base_image: Image.Image, layer_config: Dict[str, Any]
    ) -> Image.Image:
        """
        添加图片图层

        Args:
            base_image: 基础图片
            layer_config: 图层配置字典

        Returns:
            Image.Image: 添加图片层后的图片
        """
        try:
            # 获取图片路径
            source_path = self.resolve_variables(layer_config.get("source", ""))
            if not source_path or not os.path.exists(source_path):
                self.logger.warning(f"图片文件不存在: {source_path}")
                return base_image

            # 加载图片
            layer_image = Image.open(source_path)

            # 获取位置和尺寸配置
            x = layer_config.get("x", 0)
            y = layer_config.get("y", 0)
            width = layer_config.get("width")
            height = layer_config.get("height")

            # 调整图片尺寸
            if width and height:
                # 如果指定了宽度和高度，则缩放到指定尺寸
                layer_image = layer_image.resize(
                    (width, height), Image.Resampling.LANCZOS
                )
                self.logger.debug(f"调整图片尺寸到: {width}x{height}")
            elif width or height:
                # 如果只指定了一个维度，保持宽高比缩放
                original_width, original_height = layer_image.size
                if width:
                    ratio = width / original_width
                    new_height = int(original_height * ratio)
                    layer_image = layer_image.resize((width, new_height), Image.Resampling.LANCZOS)
                    self.logger.debug(f"按宽度 {width} 等比缩放，新尺寸: {width}x{new_height}")
                else:
                    ratio = height / original_height
                    new_width = int(original_width * ratio)
                    layer_image = layer_image.resize((new_width, height), Image.Resampling.LANCZOS)
                    self.logger.debug(f"按高度 {height} 等比缩放，新尺寸: {new_width}x{height}")
            else:
                self.logger.debug(f"保持原始尺寸: {layer_image.size}")

            # 确保基础图片是RGBA模式
            if base_image.mode != "RGBA":
                base_image = base_image.convert("RGBA")

            # 确保图层图片是RGBA模式
            if layer_image.mode != "RGBA":
                layer_image = layer_image.convert("RGBA")

            # 创建合成图层
            composite = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
            composite.paste(
                layer_image, (x, y), layer_image if layer_image.mode == "RGBA" else None
            )

            # 合成到基础图片
            result = Image.alpha_composite(base_image, composite)

            self.logger.info(f"成功添加图片图层: {source_path} 在位置 ({x}, {y})")
            return result

        except (OSError, Image.UnidentifiedImageError) as e:
            self.logger.error(f"图片图层文件操作失败: {e}")
            return base_image
        except Exception as e:
            self.logger.error(f"添加图片图层失败: {e}")
            return base_image

    def calculate_max_layer_size(self) -> Tuple[int, int]:
        """
        计算所有图层中的最大尺寸

        Returns:
            Tuple[int, int]: 最大宽度和高度
        """
        max_width = 0
        max_height = 0
        
        # 获取图层配置
        picture_layers = self.config.get("picture_layers", {})
        if not picture_layers:
            return (1000, 1000)  # 默认尺寸
            
        for layer_name, layer_config in picture_layers.items():
            # 获取图层位置和尺寸
            x = layer_config.get("x", 0)
            y = layer_config.get("y", 0)
            width = layer_config.get("width", 0)
            height = layer_config.get("height", 0)
            
            # 计算图层右下角坐标
            right = x + width
            bottom = y + height
            
            # 更新最大尺寸
            max_width = max(max_width, right)
            max_height = max(max_height, bottom)
            
        # 如果没有找到有效尺寸，返回默认值
        if max_width == 0 or max_height == 0:
            return (1000, 1000)
            
        return (max_width, max_height)

    def create_composite_image(
        self,
        output_path: str,
        canvas_size: Tuple[int, int] = (1000, 1000),
        background_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    ) -> bool:
        """
        根据配置创建合成图片

        Args:
            output_path: 输出文件路径
            canvas_size: 画布尺寸 (宽, 高)
            background_color: 背景颜色 RGBA

        Returns:
            bool: 创建是否成功
        """
        try:
            # 获取图层配置
            picture_layers = self.config.get("picture_layers", {})
            if not picture_layers:
                self.logger.error("未找到picture_layers配置")
                return False

            # 计算最大图层尺寸
            max_size = self.calculate_max_layer_size()
            self.logger.info(f"计算最大图层尺寸: {max_size}")

            # 创建基础画布
            base_image = Image.new("RGBA", max_size, background_color)

            # 按图层顺序处理
            layer_names = sorted(picture_layers.keys())

            for layer_name in layer_names:
                layer_config = picture_layers[layer_name]
                layer_type = layer_config.get("type", "image")

                self.logger.debug(f"处理图层: {layer_name} ({layer_type})")

                if layer_type == "text":
                    base_image = self.add_text_layer(base_image, layer_config)
                else:
                    base_image = self.add_image_layer(base_image, layer_config)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 保存图片
            if output_path.lower().endswith((".jpg", ".jpeg")):
                # JPEG不支持透明度，转换为RGB
                final_image = Image.new("RGB", base_image.size, (255, 255, 255))
                final_image.paste(
                    base_image,
                    mask=base_image.split()[-1] if base_image.mode == "RGBA" else None,
                )
                final_image.save(
                    output_path, "JPEG", quality=self.config.get("quality", 85)
                )
            else:
                base_image.save(output_path)

            self.logger.info(f"合成图片保存成功: {output_path}")
            return True

        except OSError as e:
            self.logger.error(f"文件操作失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"创建合成图片失败: {e}")
            return False

    def batch_create_images(
        self, image_configs: List[Dict[str, Any]], output_dir: str = "output"
    ) -> Dict[str, int]:
        """批量创建图片"""
        success_count = 0
        failed_count = 0

        for i, config in enumerate(image_configs):
            try:
                # 更新source_data
                if "source_data" in config:
                    self.source_data.update(config["source_data"])

                # 获取输出配置
                output_name = config.get("output_name", f"composite_{i+1}.png")
                output_path = os.path.join(output_dir, output_name)
                canvas_size = tuple(config.get("canvas_size", (1000, 1000)))
                background_color = tuple(
                    config.get("background_color", (255, 255, 255, 255))
                )

                # 创建图片
                if self.create_composite_image(
                    output_path, canvas_size, background_color
                ):
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                self.logger.error(f"处理第 {i+1} 个配置失败: {e}")
                failed_count += 1

        result = {
            "success": success_count,
            "failed": failed_count,
            "total": len(image_configs),
        }

        self.logger.info(f"批量处理完成: {result}")
        return result

    def update_source_data(self, new_data: Dict[str, Any]) -> None:
        """更新源数据变量"""
        self.source_data.update(new_data)
        self.logger.info(f"更新源数据: {new_data}")

    def preview_layers(self) -> Dict[str, Any]:
        """预览图层配置信息"""
        picture_layers = self.config.get("picture_layers", {})
        preview_info = {}

        for layer_name, layer_config in picture_layers.items():
            layer_type = layer_config.get("type", "image")
            if layer_type == "text":
                text = self.resolve_variables(layer_config.get("text", ""))
                preview_info[layer_name] = {
                    "type": "text",
                    "text": text,
                    "position": layer_config.get("position", "bottom_right"),
                    "font_size": layer_config.get("font_size", 32),
                }
            else:
                source = self.resolve_variables(layer_config.get("source", ""))
                preview_info[layer_name] = {
                    "type": "image",
                    "source": source,
                    "position": (layer_config.get("x", 0), layer_config.get("y", 0)),
                    "size": (layer_config.get("width"), layer_config.get("height")),
                }

        return preview_info

    def create_thumbnail_from_image(
        self,
        source_path: str,
        thumbnail_path: str,
        thumbnail_size: Tuple[int, int] = (400, 400),
        keep_aspect: bool = True,
    ) -> bool:
        """从已有图片创建缩略图"""
        try:
            if not os.path.exists(source_path):
                self.logger.error(f"源图片不存在: {source_path}")
                return False

            # 打开原图
            with Image.open(source_path) as image:
                # 转换为RGBA模式以支持透明度
                if image.mode != "RGBA":
                    image = image.convert("RGBA")

                # 创建缩略图
                if keep_aspect:
                    # 保持宽高比缩放
                    image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

                    # 如果需要，创建居中的缩略图
                    if image.size != thumbnail_size:
                        # 创建目标尺寸的透明背景
                        thumbnail = Image.new(
                            "RGBA", thumbnail_size, (255, 255, 255, 0)
                        )

                        # 计算居中位置
                        x = (thumbnail_size[0] - image.size[0]) // 2
                        y = (thumbnail_size[1] - image.size[1]) // 2

                        # 粘贴图片到中心
                        thumbnail.paste(
                            image, (x, y), image if image.mode == "RGBA" else None
                        )
                        image = thumbnail
                else:
                    # 直接缩放到目标尺寸
                    image = image.resize(thumbnail_size, Image.Resampling.LANCZOS)

                # 确保输出目录存在
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

                # 保存缩略图
                if thumbnail_path.lower().endswith((".jpg", ".jpeg")):
                    # JPEG不支持透明度，转换为RGB
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    rgb_image.paste(
                        image, mask=image.split()[-1] if image.mode == "RGBA" else None
                    )
                    rgb_image.save(
                        thumbnail_path, "JPEG", quality=self.config.get("quality", 85)
                    )
                else:
                    image.save(thumbnail_path)

                self.logger.info(f"缩略图创建成功: {thumbnail_path}")
                return True

        except Exception as e:
            self.logger.error(f"创建缩略图失败: {e}")
            return False
