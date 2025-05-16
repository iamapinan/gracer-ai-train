import json
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from datasets import Dataset
import os

def load_dataset(file_path):
    """โหลดข้อมูลจากไฟล์ JSON หรือ CSV"""
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and 'data' in data:
                    return data['data']
                return data
        elif file_path.endswith('.csv'):
            print(f"กำลังโหลดไฟล์ CSV: {file_path}")
            df = pd.read_csv(file_path)
            print(f"คอลัมน์ที่มีในไฟล์ CSV: {df.columns.tolist()}")
            print(f"ตัวอย่างข้อมูล 5 แถวแรก:\n{df.head()}")
            
            # ตรวจสอบคอลัมน์ที่จำเป็น
            if 'text' not in df.columns:
                raise ValueError("ไม่พบคอลัมน์ 'text' ในไฟล์ CSV")
            
            # ทำความสะอาดข้อมูล
            df = df.fillna('')  # แทนที่ค่า NaN ด้วยสตริงว่าง
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # ตัดช่องว่างหน้า-หลัง
            
            # กรองข้อมูลที่ไม่สมบูรณ์
            df = df[df['text'].str.len() > 0]
            
            print(f"จำนวนข้อมูลหลังทำความสะอาด: {len(df)}")
            return df.to_dict('records')
        else:
            raise ValueError("รองรับเฉพาะไฟล์ .json และ .csv เท่านั้น")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return []

def prepare_dataset(data):
    """เตรียมข้อมูลสำหรับการฝึก"""
    texts = []
    print(f"จำนวนข้อมูลที่ได้รับ: {len(data)}")
    if len(data) > 0:
        print(f"ตัวอย่างข้อมูลแรก: {data[0]}")
        print(f"ประเภทของข้อมูลแรก: {type(data[0])}")
        print(f"คีย์ที่มีในข้อมูลแรก: {data[0].keys() if isinstance(data[0], dict) else 'ไม่ใช่ dictionary'}")
    
    for idx, item in enumerate(data):
        try:
            if isinstance(item, dict):
                # ใช้ข้อมูลจากคอลัมน์ text โดยตรง
                text = item.get('text', '').strip()
                
                print(f"\nกำลังประมวลผลข้อมูลที่ {idx + 1}:")
                print(f"text: {text[:100]}..." if text else "ไม่มี text")
                
                if text:
                    texts.append(text)
                    print("เพิ่มข้อความสำเร็จ")
                else:
                    print("ข้ามข้อมูลเนื่องจากไม่มี text")
            else:
                print(f"ข้ามข้อมูลที่ {idx + 1} เนื่องจากไม่ใช่ dictionary (เป็น {type(item)})")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการประมวลผลข้อมูลที่ {idx + 1}: {e}")
            continue
    
    print(f"\nสรุปผลการประมวลผล:")
    print(f"จำนวนข้อมูลทั้งหมด: {len(data)}")
    print(f"จำนวนข้อความที่เตรียมได้: {len(texts)}")
    
    if not texts:
        raise ValueError("ไม่พบข้อมูลที่สามารถใช้ในการฝึกได้")
    
    return Dataset.from_dict({"text": texts})

def main():
    # กำหนดค่าเริ่มต้น
    model_name = "gracer-ai"  # ชื่อโมเดลที่จะบันทึก
    dataset_path = "dltv_dataset/dltv_dataset_autotrain.csv"  # เปลี่ยนเป็นไฟล์ CSV
    base_model = "google/gemma-3-1b-it"
    
    # ใช้ CPU แทน MPS
    device = torch.device("cpu")
    print(f"ใช้ device: {device}")
    
    # โหลดข้อมูล
    print("กำลังโหลดข้อมูล...")
    data = load_dataset(dataset_path)
    print(f"จำนวนข้อมูลที่โหลดได้: {len(data)} รายการ")
    
    if not data:
        print("ไม่พบข้อมูล กรุณาตรวจสอบไฟล์ข้อมูล")
        return
    
    try:
        dataset = prepare_dataset(data)
        print(f"จำนวนข้อมูลที่เตรียมสำหรับการฝึก: {len(dataset)} รายการ")
    except ValueError as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return
    
    # โหลด tokenizer และโมเดล
    print("กำลังโหลด tokenizer และโมเดล...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    
    # ตั้งค่า tokenizer
    tokenizer.pad_token = tokenizer.eos_token
    
    # เตรียมข้อมูลสำหรับการฝึก
    def tokenize_function(examples):
        # Tokenize ข้อความ
        tokenized = tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=256,  # ลดความยาวลงเพื่อประหยัดหน่วยความจำ
            return_tensors="pt"
        )
        
        # สร้าง labels สำหรับ causal language modeling
        tokenized["labels"] = tokenized["input_ids"].clone()
        
        return tokenized
    
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    # ตั้งค่าการฝึก
    training_args = TrainingArguments(
        output_dir=f"./models/{model_name}",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,  # เพิ่มขึ้นเพื่อประหยัดหน่วยความจำ
        save_steps=1000,
        save_total_limit=2,
        logging_dir=f"./logs/{model_name}",
        logging_steps=100,
        learning_rate=2e-5,
        warmup_steps=100,
        fp16=False,
        bf16=False,
        use_cpu=True,  # ใช้ CPU แทน MPS
    )
    
    # โหลดโมเดลหลังจากตั้งค่า training arguments
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float32,
    ).to(device)
    
    # สร้าง trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )
    
    # เริ่มการฝึก
    print("เริ่มการฝึกโมเดล...")
    trainer.train()
    
    # บันทึกโมเดลและ tokenizer
    print("กำลังบันทึกโมเดล...")
    model.save_pretrained(f"./models/{model_name}")
    tokenizer.save_pretrained(f"./models/{model_name}")
    
    print(f"การฝึกเสร็จสิ้น! โมเดลถูกบันทึกที่ ./models/{model_name}")

if __name__ == "__main__":
    main() 