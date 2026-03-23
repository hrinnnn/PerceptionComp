import json

# 加载两个结果文件
with open('../test_result_summer/gemini_3_pro/Results-gemini-3-pro-preview.json', 'r', encoding='utf-8') as f:
    pro_data = json.load(f)

with open('../test_result_summer/gemini_3_flash/Results-gemini-3-flash-preview.json', 'r', encoding='utf-8') as f:
    flash_data = json.load(f)

# 任务1: 找出所有3-pro做错的题
pro_wrong = [item for item in pro_data if item.get('Correct') == False]

# 提取所需信息
task1_results = []
for item in pro_wrong:
    task1_results.append({
        'key': item.get('key'),
        'video_id': item.get('video_id'),
        'question': item.get('Question'),
        'options': item.get('Options'),
        'GT': item.get('GT'),
        'predicted_answer': item.get('Predicted Answer'),
        'thinking': item.get('Thinking'),
        'correct': item.get('Correct')
    })

# 任务2: 找出3-pro做错但3-flash做对的题
task2_results = []
for pro_item in pro_wrong:
    pro_key = pro_item.get('key')
    flash_item = next((item for item in flash_data if item.get('key') == pro_key), None)
    if flash_item and flash_item.get('Correct') == True:
        task2_results.append({
            'key': pro_item.get('key'),
            'video_id': pro_item.get('video_id'),
            'question': pro_item.get('Question'),
            'options': pro_item.get('Options'),
            'GT': pro_item.get('GT'),
            'gemini_3_pro_predicted_answer': pro_item.get('Predicted Answer'),
            'gemini_3_pro_thinking': pro_item.get('Thinking'),
            'gemini_3_pro_correct': pro_item.get('Correct'),
            'gemini_3_flash_predicted_answer': flash_item.get('Predicted Answer'),
            'gemini_3_flash_thinking': flash_item.get('Thinking'),
            'gemini_3_flash_correct': flash_item.get('Correct')
        })

# 保存为JSON文件
with open('task1_pro_wrong.json', 'w', encoding='utf-8') as f:
    json.dump(task1_results, f, ensure_ascii=False, indent=2)

with open('task2_pro_wrong_flash_correct.json', 'w', encoding='utf-8') as f:
    json.dump(task2_results, f, ensure_ascii=False, indent=2)

print(f"✅ 任务1完成: {len(task1_results)} 道题目已导出到 task1_pro_wrong.json")
print(f"✅ 任务2完成: {len(task2_results)} 道题目已导出到 task2_pro_wrong_flash_correct.json")

# 打印统计信息
print(f"\n统计信息:")
print(f"- Gemini-3-Pro 做错的题目总数: {len(pro_wrong)}")
print(f"- 其中 3-Pro 做错但 3-Flash 做对的题目数: {len(task2_results)}")
