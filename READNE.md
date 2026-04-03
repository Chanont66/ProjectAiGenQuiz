# pip install torch transformers datasets sentencepiece protobuf

<!-- torch - deep learning framework ใช้สร้างและเทรน neural network, คำนวณ gradient อัตโนมัติ
transformers - โมเดลสำเร็จรูป เช่น GPT, BERT, T5 ครอบคลุมงานหลายอย่าง (NLP ด้วย)
datasets - ใช้โหลดและจัดการ dataset สำหรับเทรนโมเดล มี dataset สาธารณะให้ใช้หลายพันชุด ใช้ง่าย
sentencepiece - tokenization (แบ่งข้อความเป็น token) พัฒนาโดย Google ใช้งานโดยโมเดลหลายตัว รองรับหลายภาษา (ไทยด้วย)
protobuf - ต้องการสำหรับอ่าน SentencePiece model ของ mT5 -->

1. **torch** — Deep Learning Framework
   - ใช้สร้างและเทรน Neural Network
   - คำนวณ Gradient อัตโนมัติ (Autograd)
   - พัฒนาโดย Meta (Facebook AI Research)

2. **transformers** — โมเดลสำเร็จรูป
   - รวบรวมโมเดลยอดนิยม เช่น GPT, BERT, T5
   - ครอบคลุมงาน NLP หลากหลาย เช่น การแปลภาษา, การสรุปข้อความ, การตอบคำถาม
   - พัฒนาโดย Hugging Face

3. **datasets** — จัดการ Dataset
   - โหลดและจัดการ Dataset สำหรับเทรนโมเดล
   - มี Dataset สาธารณะให้ใช้งานหลายพันชุด
   - ใช้งานง่าย รองรับข้อมูลขนาดใหญ่
   - พัฒนาโดย Hugging Face

4. **sentencepiece** — Tokenization
   - แบ่งข้อความเป็น Token สำหรับป้อนเข้าโมเดล
   - รองรับหลายภาษา รวมถึงภาษาไทย
   - ใช้งานโดยโมเดลชั้นนำหลายตัว เช่น mT5, XLNet
   - พัฒนาโดย Google

5. **protobuf** — Protocol Buffers
   - ต้องการสำหรับอ่าน SentencePiece model ของ mT5
   - เป็น Dependency สนับสนุนการทำงานของ sentencepiece
   - พัฒนาโดย Google

### Comparison of Model Classes

| Class | งานที่ใช้ (Task) | สถาปัตยกรรม (Architecture) |
| :--- | :--- | :--- |
| `MT5ForConditionalGeneration` | Summarize, Translate, QA | Encoder-Decoder |
| `MT5EncoderModel` | Classification, Embedding | Encoder Only |
| `GPT2LMHeadModel` | Text generation ต่อต่อเนื่อง | Decoder Only |
| `BertForSequenceClassification` | จัดหมวดหมู่ | Encoder Only |


# seq2seq model
https://youtu.be/GiLQLqBnATs?si=64bKFLQ91qTTq-zH


# pip install accelerate
- เป็น library ช่วย train AI
- ทำให้ใช้ GPU/CPU ง่าย
- ต้องมีถ้าใช้ Trainer
 

# ตัวอย่างการใช้ transformers (prompt)
https://youtu.be/upYsw2XWr1Y?si=LgyDDhGzUr_8kI9X