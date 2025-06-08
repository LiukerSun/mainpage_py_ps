#!/usr/bin/python
# coding:utf-8

# @FileName:    logger.py
# @Time:        2025/6/8 10:00
# @Author:      evansun
# @Project:     mainpage

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import yaml
from logging.handlers import RotatingFileHandler
import os

# ANSI颜色代码
class Colors:
    """终端颜色配置"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # 背景色
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 不同日志级别的颜色配置
    LEVEL_COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.BRIGHT_GREEN,
        'WARNING': Colors.BRIGHT_YELLOW,
        'ERROR': Colors.BRIGHT_RED,
        'CRITICAL': Colors.BG_RED + Colors.BRIGHT_WHITE
    }
    
    # 不同组件的颜色
    COMPONENT_COLORS = {
        'time': Colors.DIM + Colors.WHITE,
        'name': Colors.BRIGHT_BLUE,
        'level': Colors.BOLD,
        'message': Colors.WHITE,
        'filename': Colors.MAGENTA,
        'line': Colors.CYAN
    }
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and self._supports_color()
        
        # 带颜色的格式
        colored_format = (
            f"{self.COMPONENT_COLORS['time']}%(asctime)s{Colors.RESET} "
            f"│ {self.COMPONENT_COLORS['level']}%(levelname)-8s{Colors.RESET} "
            f"│ {self.COMPONENT_COLORS['name']}%(name)s{Colors.RESET} "
            f"│ {self.COMPONENT_COLORS['filename']}%(filename)s{Colors.RESET}:"
            f"{self.COMPONENT_COLORS['line']}%(lineno)d{Colors.RESET} "
            f"│ {self.COMPONENT_COLORS['message']}%(message)s{Colors.RESET}"
        )
        
        # 无颜色的格式（用于文件输出）
        plain_format = (
            "%(asctime)s │ %(levelname)-8s │ %(name)s │ "
            "%(filename)s:%(lineno)d │ %(message)s"
        )
        
        super().__init__(
            colored_format if self.use_colors else plain_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record):
        # 为不同级别的日志添加颜色
        if self.use_colors and record.levelname in self.LEVEL_COLORS:
            # 保存原始格式
            original_format = self._style._fmt
            
            # 获取级别颜色
            level_color = self.LEVEL_COLORS[record.levelname]
            
            # 更新格式字符串中的级别部分
            colored_format = original_format.replace(
                f"{self.COMPONENT_COLORS['level']}%(levelname)-8s{Colors.RESET}",
                f"{level_color}%(levelname)-8s{Colors.RESET}"
            )
            
            # 临时更新格式
            self._style._fmt = colored_format
            
            # 格式化记录
            formatted = super().format(record)
            
            # 恢复原始格式
            self._style._fmt = original_format
            
            return formatted
        
        return super().format(record)
    
    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        return (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() and
            os.environ.get('TERM') != 'dumb'
        )


class LoggerManager:
    """日志管理器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.loggers: Dict[str, logging.Logger] = {}
        
        # 日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置根日志器
        self._setup_root_logger()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载日志配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return config.get('logging', {})
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"⚠️ 加载日志配置失败: {e}，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认日志配置"""
        return {
            'enabled': True,
            'level': 'INFO',
            'console': {
                'enabled': True,
                'use_colors': True,
                'level': 'INFO'
            },
            'file': {
                'enabled': True,
                'level': 'DEBUG',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
    
    def _setup_root_logger(self):
        """设置根日志器"""
        if not self.config.get('enabled', True):
            logging.disable(logging.CRITICAL)
            return
        
        # 获取日志级别
        level = getattr(logging, self.config.get('level', 'INFO').upper())
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加控制台处理器
        if self.config.get('console', {}).get('enabled', True):
            self._add_console_handler(root_logger)
        
        # 添加文件处理器
        if self.config.get('file', {}).get('enabled', True):
            self._add_file_handler(root_logger)
    
    def _add_console_handler(self, logger: logging.Logger):
        """添加控制台处理器"""
        console_config = self.config.get('console', {})
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 设置级别
        level = getattr(logging, console_config.get('level', 'INFO').upper())
        console_handler.setLevel(level)
        
        # 设置格式器
        use_colors = console_config.get('use_colors', True)
        formatter = ColoredFormatter(use_colors=use_colors)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    def _add_file_handler(self, logger: logging.Logger):
        """添加文件处理器"""
        # 创建日志文件名
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"pythonps_{timestamp}.log"
        
        # 文件配置
        file_config = self.config.get('file', {})
        max_size = self._parse_size(file_config.get('max_size', '10MB'))
        backup_count = file_config.get('backup_count', 5)
        
        # 创建旋转文件处理器
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # 设置级别
        level = getattr(logging, file_config.get('level', 'DEBUG').upper())
        file_handler.setLevel(level)
        
        # 设置格式器（文件不使用颜色）
        formatter = ColoredFormatter(use_colors=False)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """解析文件大小字符串"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_system_info(self):
        """记录系统信息"""
        logger = self.get_logger('system')
        logger.info("=" * 60)
        logger.info("🚀 批量修图程序启动")
        logger.info("=" * 60)
        logger.info(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🐍 Python版本: {sys.version.split()[0]}")
        logger.info(f"📁 工作目录: {Path.cwd()}")
        logger.info(f"📄 日志目录: {self.log_dir.absolute()}")
        logger.info("=" * 60)
    
    def log_config_info(self, config: Dict[str, Any]):
        """记录配置信息"""
        logger = self.get_logger('config')
        logger.info("⚙️ 配置信息:")
        logger.info(f"   📊 日志级别: {self.config.get('level', 'INFO')}")
        logger.info(f"   🖥️  控制台输出: {'启用' if self.config.get('console', {}).get('enabled', True) else '禁用'}")
        logger.info(f"   💾 文件输出: {'启用' if self.config.get('file', {}).get('enabled', True) else '禁用'}")
        
        if config:
            copy_files_count = len(config.get('copy_files', []))
            logger.info(f"   📋 复制文件数: {copy_files_count}")
            logger.info(f"   🔄 覆盖模式: {'启用' if config.get('copy_settings', {}).get('overwrite', False) else '禁用'}")


# 全局日志管理器实例
_logger_manager: Optional[LoggerManager] = None

def get_logger_manager() -> LoggerManager:
    """获取全局日志管理器实例"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager

def get_logger(name: str = __name__) -> logging.Logger:
    """获取日志器的便捷函数"""
    return get_logger_manager().get_logger(name)

def init_logging(config_file: str = "config.yaml"):
    """初始化日志系统"""
    global _logger_manager
    _logger_manager = LoggerManager(config_file)
    _logger_manager.log_system_info()

# 便捷的日志函数
def debug(msg: str, logger_name: str = 'main'):
    """记录调试信息"""
    get_logger(logger_name).debug(msg)

def info(msg: str, logger_name: str = 'main'):
    """记录普通信息"""
    get_logger(logger_name).info(msg)

def warning(msg: str, logger_name: str = 'main'):
    """记录警告信息"""
    get_logger(logger_name).warning(msg)

def error(msg: str, logger_name: str = 'main'):
    """记录错误信息"""
    get_logger(logger_name).error(msg)

def critical(msg: str, logger_name: str = 'main'):
    """记录严重错误信息"""
    get_logger(logger_name).critical(msg) 