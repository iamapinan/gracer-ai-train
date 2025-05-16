import json
import pandas as pd
import re

def clean_text(text):
    # ลบตัวขึ้นบรรทัดใหม่และช่องว่างที่มากเกินไป
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def convert_to_autotrain():
    # อ่านไฟล์ JSON
    with open('dltv_dataset/dltv_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # สร้าง list สำหรับเก็บข้อมูลที่จะแปลงเป็น CSV
    rows = []
    
    # วนลูปข้อมูลแต่ละบทเรียน
    for lesson in data['data']:
        # ทำความสะอาดข้อความ
        content = clean_text(lesson['content'])
        
        # สร้าง instruction
        instruction = f"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction: สรุปเนื้อหาบทเรียน {lesson['lesson_name']} วิชา{lesson['subject']} ระดับชั้น{lesson['grade']}\n\n### Response: {content}"
        
        # เพิ่มข้อมูลลงใน list
        rows.append({
            'text': instruction
        })
    
    # สร้าง DataFrame
    df = pd.DataFrame(rows)
    
    # บันทึกเป็นไฟล์ CSV
    df.to_csv('dltv_dataset/dltv_dataset_autotrain.csv', index=False, encoding='utf-8')
    print(f"แปลงข้อมูลเสร็จสิ้น จำนวน {len(rows)} บทเรียน")

if __name__ == "__main__":
    convert_to_autotrain() 