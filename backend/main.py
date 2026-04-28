from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import re
import asyncio
import torch
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint

torch.serialization.add_safe_globals([ModelCheckpoint])

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
        checkpoint_path='../model/model_gen_choice/model_choice.ckpt',
        s2v_path='../model/s2v_old'
    )
except Exception as e:
    raise RuntimeError(f"Failed to load models: {e}")

class QuizRequest(BaseModel):
    text: str
    numQuiz: int = 1

def generate_one_quiz(text: str, sample_text: str):
    question = qg.generate('[MASK]', sample_text) 

    # เช็คว่าได้คำตอบไหม (เช็คจาก SEP_TOKEN ถ้ามี = มีคำตอบ)
    if SEP_TOKEN in question:
        parts = question.split(SEP_TOKEN)
        answer = parts[0].strip()
        question_text = parts[1].strip() if len(parts) > 1 else question
    else:
        answer = '[MASK]'
        question_text = question

    # ส่งคำตอบ, context, quiz ให้ model choice
    distractors = cg.generate(answer, text, question=question_text)

    # คำตอบ รวมกับ choice
    choices = [answer] + (distractors if distractors else [])
    choices_dict = {normalize(c): c for c in choices}
    filtered_choices = [c for norm_c, c in choices_dict.items() if norm_c != normalize(answer)]
    
    # เติมตัวเลือกให้ครบ 3 อีกที (กันว่าถ้า s2v ช่วยไม่ได้)
    words_in_text = [w for w in text.split() if len(w) > 3 and w.istitle()] 
    while len(filtered_choices) < 3:
        if words_in_text:
            fallback_word = random.choice(words_in_text) # สุ่มคำจากเนื้อหา
        else:
            # สุ่มคำสำเร็จรูป ถ้ามันได้ choice ไม่ครบจริงๆ
            fallback_word = random.choice(["None of the above", "Cannot be determined", "All of the above", "Not mentioned"])
        
        if normalize(fallback_word) != normalize(answer) and normalize(fallback_word) not in [normalize(c) for c in filtered_choices]:
            filtered_choices.append(fallback_word)
    
    final_choices = [answer] + filtered_choices[:3] # รวมคำตอบกับ choice
    random.shuffle(final_choices) # สุ่มสลับข้อ

    return {
        "question": question_text,
        "choices": final_choices,
        "answer": answer
    }

@app.post("/generate-quiz")
async def process_quiz(request: QuizRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # คลีน text ก่อน
    text = clean(request.text)
    num_quiz = request.numQuiz

    # หั่นเป็นประโยคย่อยๆ - ให้มันอ่านได้ ไม่เกิน token limit
    sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s) > 10]
    if not sentences:
        sentences = [text] 

    try:
        tasks = []
        n_sents = len(sentences)
        
        # วนทำตามจำนวนข้อ
        for i in range(num_quiz):
            start_idx = int((i * n_sents) / max(num_quiz, 1)) % max(n_sents, 1) # กันใช้เนื้อหาซ้ำจุดเดียวกัน
            
            # เลือก 3 ประโยค (ถ้าเนื้อหาน้อยกว่าก็เลือกเท่านั้น)
            window_size = min(3, n_sents) 
            chunk_sents = []
            
            for j in range(window_size):
                curr_idx = (start_idx + j) % max(n_sents, 1)
                if sentences[curr_idx] not in chunk_sents:
                    chunk_sents.append(sentences[curr_idx])
           
            sample_text = " ".join(chunk_sents) # รวมประโยคที่เลือก

            tasks.append(asyncio.to_thread(generate_one_quiz, text, sample_text))
        
        quiz_list = await asyncio.gather(*tasks)

        # กรอง quiz ที่ซ้ำกัน - กลายเป็นมีปัญหาได้ quiz ไม่ครบเพราะมันซ้ำ
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