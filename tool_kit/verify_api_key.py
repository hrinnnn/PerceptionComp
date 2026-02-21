#!/usr/bin/env python3
"""
Google API Key 验证脚本
验证 Google Gemini API 密钥是否有效

使用方法:
    python verify_api_key.py <api_key>
    或
    GOOGLE_API_KEY=<api_key> python verify_api_key.py
"""

import os
import sys
import argparse
import google.generativeai as genai
from google.api_core.exceptions import InvalidArgument, Unauthenticated


def verify_api_key(api_key: str, model_name: str = "gemini-3-flash-preview") -> bool:
    """
    验证 API key 是否有效
    
    Args:
        api_key: Google API 密钥
        model_name: 要测试的模型名称
        
    Returns:
        bool: True 表示密钥有效，False 表示无效
    """
    try:
        # 配置 API
        genai.configure(api_key=api_key)
        print(f"✓ API 密钥格式正确")
        
        # 初始化模型
        model = genai.GenerativeModel(model_name=model_name)
        print(f"✓ 模型 '{model_name}' 初始化成功")
        
        # 进行一个简单的 API 调用
        response = model.generate_content("Hello")
        print(f"✓ API 调用成功")
        print(f"✓ 模型响应: {response.text[:50]}...")
        
        return True
        
    except Unauthenticated as e:
        print(f"✗ 身份验证失败: API 密钥无效")
        print(f"  详情: {str(e)}")
        return False
        
    except InvalidArgument as e:
        print(f"✗ 参数错误: {str(e)}")
        return False
        
    except Exception as e:
        print(f"✗ 验证失败: {type(e).__name__}")
        print(f"  详情: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="验证 Google Gemini API 密钥是否有效",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python verify_api_key.py AlzaSyXxxx...
  GOOGLE_API_KEY=AlzaSyXxxx... python verify_api_key.py
  python verify_api_key.py --key AlzaSyXxxx... --model gemini-3-flash-preview
        """
    )
    
    parser.add_argument(
        "api_key",
        nargs="?",
        default=None,
        help="Google API 密钥 (或从 GOOGLE_API_KEY 环境变量读取)"
    )
    
    parser.add_argument(
        "--key",
        dest="api_key_arg",
        default=None,
        help="Google API 密钥 (命名参数)"
    )
    
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="要测试的模型名称 (默认: gemini-3-flash-preview)"
    )
    
    parser.add_argument(
        "--proxy",
        default="http://127.0.0.1:1082",
        type=str,
        help="Proxy URL",
    )
    
    args = parser.parse_args()
    
    # 获取 API 密钥
    api_key = args.api_key or args.api_key_arg or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未提供 API 密钥")
        print("\n使用方式:")
        print("  1. 命令行参数: python verify_api_key.py <api_key>")
        print("  2. 环境变量: GOOGLE_API_KEY=<api_key> python verify_api_key.py")
        print("  3. 命名参数: python verify_api_key.py --key <api_key>")
        sys.exit(1)
    
    print("=" * 60)
    print("Google Gemini API 密钥验证")
    print("=" * 60)
    print(f"\n验证中...")
    print(f"  模型: {args.model}")
    print(f"  密钥: {api_key[:10]}...{api_key[-5:]}\n")
    
    # 验证密钥
    success = verify_api_key(api_key, args.model)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 验证结果: API 密钥有效 ✓")
        print("=" * 60)
        return 0
    else:
        print("✗ 验证结果: API 密钥无效 ✗")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
