#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
价格管理器模块
负责加载和管理商品价格信息
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .logger import get_logger


class PriceManager:
    """价格管理器，用于处理商品价格信息"""

    def __init__(self, price_file: str = "prices.yaml") -> None:
        """
        初始化价格管理器

        Args:
            price_file: 价格配置文件路径

        Raises:
            FileNotFoundError: 价格文件不存在时抛出警告但不中断程序
        """
        self.price_file = Path(price_file)
        self.logger = get_logger("price_manager")

        # 加载价格配置
        self.config = self._load_price_config()
        self.prices = self.config.get("prices", {})
        self.price_config = self.config.get("price_config", {})

        self.logger.info(f"价格管理器初始化完成，加载了 {len(self.prices)} 个商品价格")

    def _load_price_config(self) -> Dict[str, Any]:
        """
        加载价格配置文件

        Returns:
            Dict[str, Any]: 价格配置字典
        """
        try:
            if self.price_file.exists():
                with open(self.price_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"成功加载价格配置文件: {self.price_file}")
                return config or {}
            else:
                self.logger.warning(f"价格配置文件不存在: {self.price_file}")
                return self._get_default_config()
        except yaml.YAMLError as e:
            self.logger.error(f"价格配置文件格式错误 {self.price_file}: {e}")
            return self._get_default_config()
        except OSError as e:
            self.logger.error(f"读取价格配置文件失败 {self.price_file}: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            Dict[str, Any]: 默认价格配置
        """
        return {
            "price_config": {
                "default_format": "¥{price}",
                "default_price": "99.00",
                "display_settings": {
                    "show_currency": True,
                    "currency_symbol": "¥",
                    "decimal_places": 2,
                },
            },
            "prices": {},
        }

    def get_price(self, product_code: str) -> str:
        """
        获取指定商品的价格

        Args:
            product_code: 商品货号

        Returns:
            str: 格式化后的价格字符串
        """
        # 获取原始价格
        raw_price = self.prices.get(product_code)

        if raw_price is None:
            # 使用默认价格
            raw_price = self.price_config.get("default_price", "99.00")
            self.logger.warning(
                f"未找到商品 {product_code} 的价格，使用默认价格: {raw_price}"
            )

        # 格式化价格
        return self._format_price(raw_price)

    def _format_price(self, price: str) -> str:
        """
        格式化价格显示

        Args:
            price: 原始价格字符串

        Returns:
            str: 格式化后的价格字符串
        """
        try:
            # 获取格式配置
            price_format = self.price_config.get("default_format", "¥{price}")
            display_settings = self.price_config.get("display_settings", {})

            # 处理小数位数
            decimal_places = display_settings.get("decimal_places", 2)
            if decimal_places >= 0:
                try:
                    price_float = float(price)
                    price = f"{price_float:.{decimal_places}f}"
                except ValueError:
                    self.logger.warning(f"价格格式无法转换为数字: {price}")

            # 应用格式
            return price_format.format(price=price)

        except Exception as e:
            self.logger.error(f"价格格式化失败: {e}")
            return f"¥{price}"

    def has_price(self, product_code: str) -> bool:
        """
        检查是否有指定商品的价格

        Args:
            product_code: 商品货号

        Returns:
            bool: 是否存在价格信息
        """
        return product_code in self.prices

    def add_price(self, product_code: str, price: str) -> None:
        """
        添加或更新商品价格

        Args:
            product_code: 商品货号
            price: 价格
        """
        self.prices[product_code] = price
        self.logger.debug(f"添加/更新价格: {product_code} = {price}")

    def get_all_prices(self) -> Dict[str, str]:
        """
        获取所有价格信息

        Returns:
            Dict[str, str]: 所有商品价格字典
        """
        return self.prices.copy()

    def save_prices(self, output_file: Optional[str] = None) -> bool:
        """
        保存价格配置到文件

        Args:
            output_file: 输出文件路径，如果为None则保存到原文件

        Returns:
            bool: 保存是否成功
        """
        try:
            save_path = Path(output_file) if output_file else self.price_file

            # 构建完整配置
            full_config = {
                "price_config": self.price_config,
                "prices": self.prices,
            }

            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    full_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            self.logger.info(f"价格配置保存成功: {save_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存价格配置失败: {e}")
            return False

    def get_price_statistics(self) -> Dict[str, Any]:
        """
        获取价格统计信息

        Returns:
            Dict[str, Any]: 价格统计信息
        """
        if not self.prices:
            return {
                "total_products": 0,
                "price_range": "无数据",
                "average_price": 0.0,
                "has_default_config": bool(self.price_config),
            }

        try:
            # 转换价格为数值进行统计
            numeric_prices = []
            for price_str in self.prices.values():
                try:
                    numeric_prices.append(float(price_str))
                except ValueError:
                    continue

            if not numeric_prices:
                return {
                    "total_products": len(self.prices),
                    "price_range": "价格格式错误",
                    "average_price": 0.0,
                    "has_default_config": bool(self.price_config),
                }

            min_price = min(numeric_prices)
            max_price = max(numeric_prices)
            avg_price = sum(numeric_prices) / len(numeric_prices)

            return {
                "total_products": len(self.prices),
                "price_range": f"¥{min_price:.2f} - ¥{max_price:.2f}",
                "average_price": avg_price,
                "has_default_config": bool(self.price_config),
            }

        except Exception as e:
            self.logger.error(f"计算价格统计信息失败: {e}")
            return {
                "total_products": len(self.prices),
                "price_range": "统计失败",
                "average_price": 0.0,
                "has_default_config": bool(self.price_config),
            }
