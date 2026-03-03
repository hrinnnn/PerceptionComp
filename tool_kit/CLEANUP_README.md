# Google云端文件清理程序

## 概述
这个程序用于清理Google Generative AI API云端存储的文件，当API调用超出配额（exceeded quota）时使用。

## 功能
- 列出云端所有文件
- 显示文件大小和创建时间
- 安全确认后删除所有文件
- 生成详细的清理报告（JSON和文本格式）

## 使用方法

### 方式1：使用API Key参数
```bash
python tool_kit/cleanup_google_cloud.py --api_key "YOUR_API_KEY"
```

### 方式2：使用环境变量
```bash
export GOOGLE_API_KEY="YOUR_API_KEY"
python tool_kit/cleanup_google_cloud.py
```

### 方式3：带代理
```bash
python tool_kit/cleanup_google_cloud.py \
  --api_key "YOUR_API_KEY" \
  --proxy "http://127.0.0.1:1082"
```

### 方式4：指定报告输出目录
```bash
python tool_kit/cleanup_google_cloud.py \
  --api_key "YOUR_API_KEY" \
  --output_dir "/path/to/reports"
```

## 执行流程

1. **扫描阶段**: 列出所有云端文件
   - 显示文件名、大小、创建时间等信息
   - 计算总容量

2. **确认阶段**: 等待用户确认
   - 显示待删除文件总数和总大小
   - 要求用户输入 `yes` 确认删除

3. **删除阶段**: 逐个删除文件
   - 显示删除进度
   - 记录删除失败的文件

4. **报告生成**: 保存清理报告
   - JSON格式报告（完整数据）
   - 文本格式报告（易读）

## 报告内容

报告包含:
- 清理时间戳
- 总文件数、成功删除数、失败数
- 清理的总容量
- 已删除文件的详细列表
- 删除失败文件的详细列表（含错误信息）

## 报告位置
- 默认位置: `./cleanup_reports/`
- 文件名格式: `cleanup_report_YYYYMMDD_HHMMSS.json` 和 `.txt`

## 注意事项

1. **删除前确认**: 程序会要求明确确认才会删除文件
2. **不可恢复**: 删除操作不可逆，请谨慎操作
3. **代理设置**: 如需使用代理，确保代理地址正确
4. **API配额**: 清理文件后配额会重置，可以继续调用API

## 常见问题

### Q: 为什么API超出配额？
A: Google API有存储限制。可以定期运行此程序清理不需要的文件。

### Q: 能否恢复已删除的文件？
A: 不能。请确保确认删除操作前了解后果。

### Q: 删除失败怎么办？
A: 程序会保存失败列表到报告中。可以检查错误信息后手动处理。

## 与现有评估程序的配合使用

现有的 `gemini-3-flash-preview_evaluate.py` 程序包含了上传和缓存机制。定期运行清理程序可以：
- 防止云端文件堆积
- 避免超出容量配额
- 保持API正常使用
