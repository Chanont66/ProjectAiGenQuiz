from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random
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

# โหลด model ครั้งเดียวตอนเริ่ม server
qg = QuestionGenerator('../model/model_gen_quiz/model_quiz.ckpt')
cg = ChoiceGenerator(
    # checkpoint_path='../model/model_gen_choice/model_choice.ckpt',
    checkpoint_path='../model/model_gen_choice/race-distractors.ckpt',
    s2v_path='../model/s2v_reddit/s2v_reddit_2015_md/s2v_old'
)

from pydantic import BaseModel

class QuizRequest(BaseModel):
    text: str
    numQuiz: int = 1

@app.post("/log")
async def process_quiz(request: QuizRequest):
    text = clean(request.text)
    num_quiz = request.numQuiz

    quiz_list = []
    for _ in range(num_quiz):
        # แยก answer ออกจาก question (format: "answer <sep> question")
        question = qg.generate('[MASK]', text)

        if SEP_TOKEN in question:
            parts = question.split(SEP_TOKEN)
            answer = parts[0].strip()
            question_text = parts[1].strip() if len(parts) > 1 else question
        else:
            answer = '[MASK]'
            question_text = question

        # สร้างตัวเลือก
        distractors = cg.generate(answer, text)

        # รวม correct + distractors แล้วสับไพ่
        choices = [answer] + distractors
        choices = list({normalize(c): c for c in choices}.values())  # ลบซ้ำ
        choices = [c for c in choices if normalize(c) != normalize(answer)]  # ลบที่เหมือน answer
        choices = [answer] + choices[:3]  # เติม answer กลับ
        random.shuffle(choices)

        quiz_list.append({
            "question": question_text,
            "choices": choices,
            "answer": answer
        })

    return {"quiz": quiz_list}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)