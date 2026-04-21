from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import re
import asyncio

from services.question_generator import QuestionGenerator
from services.choice_generator import ChoiceGenerator
from utils.clean_text import clean, normalize

SEP_TOKEN = '<sep>'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# โหลดโมเดลตอนเริ่ม Server
try:
    qg = QuestionGenerator('../model/model_gen_quiz/model_quiz.ckpt')
    cg = ChoiceGenerator(
        checkpoint_path='../model/model_gen_choice/race-distractors.ckpt',
        s2v_path='../model/s2v_reddit/s2v_reddit_2015_md/s2v_old'
    )
except Exception as e:
    raise RuntimeError(f"Failed to load models: {e}")

class QuizRequest(BaseModel):
    text: str
    numQuiz: int = 1

# ---------------------------------------------------------
# ฟังก์ชันแยกสำหรับสร้างข้อสอบ 1 ข้อ
# ---------------------------------------------------------
def generate_one_quiz(text: str, sample_text: str):
    # ใช้ sample_text (ประโยคเฉพาะข้อนั้นๆ) ไปสร้างคำถาม
    question = qg.generate('[MASK]', sample_text) 

    if SEP_TOKEN in question:
        parts = question.split(SEP_TOKEN)
        answer = parts[0].strip()
        question_text = parts[1].strip() if len(parts) > 1 else question
    else:
        answer = '[MASK]'
        question_text = question

    # สร้างตัวเลือกหลอกจาก text เต็ม (เพื่อให้ได้ตัวเลือกที่สมเหตุสมผลกับเนื้อเรื่อง)
    distractors = cg.generate(answer, text)

    choices = [answer] + (distractors if distractors else [])
    choices_dict = {normalize(c): c for c in choices}
    filtered_choices = [c for norm_c, c in choices_dict.items() if norm_c != normalize(answer)]
    
    # ระบบเติมตัวเลือกให้ครบ 4 ข้อเสมอ (Fallback)
    words_in_text = [w for w in text.split() if len(w) > 3 and w.istitle()] 
    
    while len(filtered_choices) < 3:
        if words_in_text:
            fallback_word = random.choice(words_in_text)
        else:
            fallback_word = random.choice(["None of the above", "Cannot be determined", "All of the above", "Not mentioned"])
        
        # เช็คว่าคำที่สุ่มมา ต้องไม่ซ้ำกับเฉลย และไม่ซ้ำกับตัวเลือกที่มีอยู่แล้ว
        if normalize(fallback_word) != normalize(answer) and normalize(fallback_word) not in [normalize(c) for c in filtered_choices]:
            filtered_choices.append(fallback_word)

    final_choices = [answer] + filtered_choices[:3]
    random.shuffle(final_choices)

    return {
        "question": question_text,
        "choices": final_choices,
        "answer": answer
    }

# ---------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------
@app.post("/generate-quiz")
async def process_quiz(request: QuizRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    text = clean(request.text)
    num_quiz = request.numQuiz

    # หั่นเป็นประโยคย่อยๆ
    sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s) > 10]
    if not sentences:
        sentences = [text] 

    try:
        # สับไพ่ประโยคก่อน 1 รอบ
        random.shuffle(sentences)

        tasks = []
        for i in range(num_quiz):
            # แจกประโยคให้ทีละข้อเรียงตามลำดับ วนลูปถ้าประโยคหมด
            sample_text = sentences[i % len(sentences)]
            
            # ทริค: ถ้าสั่งสร้างข้อสอบ "มากกว่า" ประโยคที่มี ให้เอาประโยคถัดไปมาต่อท้าย 
            # เพื่อหลอกโมเดลว่าเนื้อหาไม่เหมือนเดิม จะได้ไม่สร้างคำถามซ้ำ
            if i >= len(sentences):
                next_sentence = sentences[(i + 1) % len(sentences)]
                sample_text = sample_text + " " + next_sentence

            # โยนงานเข้า Background Thread ให้ทำพร้อมๆ กัน
            tasks.append(asyncio.to_thread(generate_one_quiz, text, sample_text))
        
        # รอจนกว่าทุกข้อจะสร้างเสร็จ
        quiz_list = await asyncio.gather(*tasks)

        # กรองคำถามซ้ำออก (เปรียบเทียบด้วย question text ที่ normalize แล้ว)
        seen_questions = set()
        unique_quiz = []
        for item in quiz_list:
            key = normalize(item["question"])
            if key not in seen_questions:
                seen_questions.add(key)
                unique_quiz.append(item)

        return {"quiz": unique_quiz}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)