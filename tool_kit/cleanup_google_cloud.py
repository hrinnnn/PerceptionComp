import os
import json
import argparse
from datetime import datetime
import google.generativeai as genai


def cleanup_cloud_files(api_key, proxy=None):
    """清理Google云端存储的所有文件，并生成报告"""
    
    # 配置API
    genai.configure(api_key=api_key)
    
    # 设置代理（如果提供）
    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy: {proxy}")
    
    # 列出所有文件
    print("=" * 60)
    print("开始扫描云端文件...")
    print("=" * 60)
    
    files_to_delete = []
    total_size_mb = 0
    
    try:
        for file in genai.list_files():
            file_name = file.name
            file_size_mb = file.size_bytes / (1024 * 1024) if hasattr(file, 'size_bytes') else 0
            total_size_mb += file_size_mb
            files_to_delete.append({
                "name": file_name,
                "uri": file.uri,
                "size_mb": file_size_mb,
                "created_time": str(file.create_time) if hasattr(file, 'create_time') else "Unknown"
            })
            print(f"找到文件: {file_name}")
            print(f"  大小: {file_size_mb:.2f} MB")
            print(f"  URI: {file.uri}")
            print(f"  创建时间: {files_to_delete[-1]['created_time']}")
            print()
    
    except Exception as e:
        print(f"扫描文件时出错: {e}")
        return None
    
    if not files_to_delete:
        print("云端没有文件需要清理")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "no_files",
            "total_files": 0,
            "deleted_files": 0,
            "failed_deletions": 0,
            "total_size_cleaned_mb": 0,
            "deleted_list": [],
            "failed_list": []
        }
    
    # 确认删除
    print("=" * 60)
    print(f"找到 {len(files_to_delete)} 个文件，总大小约 {total_size_mb:.2f} MB")
    print("=" * 60)
    response = input("\n确认删除所有云端文件? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("已取消删除操作")
        return None
    
    # 删除文件
    print("\n开始删除文件...")
    print("=" * 60)
    
    deleted_list = []
    failed_list = []
    deleted_count = 0
    failed_count = 0
    
    for file_info in files_to_delete:
        try:
            genai.delete_file(file_info["name"])
            print(f"✓ 已删除: {file_info['name']} ({file_info['size_mb']:.2f} MB)")
            deleted_list.append(file_info)
            deleted_count += 1
        except Exception as e:
            print(f"✗ 删除失败: {file_info['name']}")
            print(f"  错误: {e}")
            file_info["error"] = str(e)
            failed_list.append(file_info)
            failed_count += 1
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": "cleanup_completed",
        "total_files": len(files_to_delete),
        "deleted_files": deleted_count,
        "failed_deletions": failed_count,
        "total_size_cleaned_mb": sum(f["size_mb"] for f in deleted_list),
        "deleted_list": deleted_list,
        "failed_list": failed_list
    }
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("清理报告摘要")
    print("=" * 60)
    print(f"总文件数: {report['total_files']}")
    print(f"成功删除: {report['deleted_files']}")
    print(f"删除失败: {report['failed_deletions']}")
    print(f"清理容量: {report['total_size_cleaned_mb']:.2f} MB")
    print("=" * 60)
    
    return report


def save_report(report, output_dir="./cleanup_reports"):
    """保存报告到JSON文件"""
    
    if report is None:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"cleanup_report_{timestamp}.json")
    
    # 保存JSON报告
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存到: {report_file}")
    
    # 生成文本报告
    text_report_file = os.path.join(output_dir, f"cleanup_report_{timestamp}.txt")
    with open(text_report_file, "w", encoding="utf-8") as f:
        f.write("Google Cloud Storage 清理报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成时间: {report['timestamp']}\n")
        f.write(f"状态: {report['status']}\n\n")
        f.write("清理统计:\n")
        f.write(f"  总文件数: {report['total_files']}\n")
        f.write(f"  成功删除: {report['deleted_files']}\n")
        f.write(f"  删除失败: {report['failed_deletions']}\n")
        f.write(f"  清理容量: {report['total_size_cleaned_mb']:.2f} MB\n\n")
        
        if report['deleted_list']:
            f.write("已删除的文件:\n")
            f.write("-" * 60 + "\n")
            for file_info in report['deleted_list']:
                f.write(f"  文件名: {file_info['name']}\n")
                f.write(f"  大小: {file_info['size_mb']:.2f} MB\n")
                f.write(f"  创建时间: {file_info['created_time']}\n")
                f.write(f"  URI: {file_info['uri']}\n\n")
        
        if report['failed_list']:
            f.write("删除失败的文件:\n")
            f.write("-" * 60 + "\n")
            for file_info in report['failed_list']:
                f.write(f"  文件名: {file_info['name']}\n")
                f.write(f"  大小: {file_info['size_mb']:.2f} MB\n")
                f.write(f"  错误: {file_info.get('error', '未知错误')}\n\n")
    
    print(f"文本报告已保存到: {text_report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理Google云端存储的文件")
    parser.add_argument(
        "--api_key",
        default=None,
        type=str,
        help="Google API key",
    )
    parser.add_argument(
        "--proxy",
        default="http://127.0.0.1:1082",
        type=str,
        help="Proxy URL",
    )
    parser.add_argument(
        "--output_dir",
        default="./cleanup_reports",
        type=str,
        help="Output directory for reports",
    )
    
    args = parser.parse_args()
    
    # 检查API key
    if not args.api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("错误: 未提供 API key")
            print("请通过 --api_key 参数传入或设置 GOOGLE_API_KEY 环境变量")
            exit(1)
    else:
        api_key = args.api_key
    
    # 执行清理
    report = cleanup_cloud_files(api_key, args.proxy)
    
    # 保存报告
    if report:
        save_report(report, args.output_dir)
