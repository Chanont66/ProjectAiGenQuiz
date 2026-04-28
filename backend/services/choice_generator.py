import torch
import pytorch_lightning as pl
import spacy
import random
import os
import sys

# เพิ่ม path เพื่อให้สามารถเรียกใช้ utils ได้เมื่อรันไฟล์นี้โดยตรง
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Optional
from utils.nltk import get_wordnet_distractors

from .shared import QGModel, SEP_TOKEN, get_tokenizer, CHOICE_SOURCE_MAX_LEN, CHOICE_TARGET_MAX_LEN



class ChoiceGenerator:
    def __init__(self, checkpoint_path: str, **kwargs):
        self.tokenizer = get_tokenizer()
        # Pass tokenizer length to QGModel constructor if needed by Lightning
        self.model = QGModel.load_from_checkpoint(checkpoint_path, tokenizer_len=len(self.tokenizer))
        self.model.eval()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        self.nlp = spacy.load('en_core_web_sm')


    def _get_context_fallback(self, answer: str, context: str, count: int = 3) -> list[str]:
        doc = self.nlp(context)

        # ลอง NER ก่อน (entity ประเภทเดียวกัน)
        answer_ents = [ent for ent in doc.ents if answer.lower() in ent.text.lower()]
        answer_label = answer_ents[0].label_ if answer_ents else None

        candidates = []
        if answer_label:
            candidates = [
                ent.text for ent in doc.ents
                if ent.label_ == answer_label and ent.text.lower() != answer.lower()
            ]

        # fallback: คำ title-case จาก context
        if not candidates:
            candidates = [
                token.text for token in doc
                if token.is_alpha and len(token.text) > 3
                and token.text.istitle()
                and token.text.lower() != answer.lower()
            ]

        # fallback สุดท้าย: คำทั่วไปยาว > 4 ตัวอักษร
        if not candidates:
            candidates = [
                token.text for token in doc
                if token.is_alpha and len(token.text) > 4
                and not token.is_stop
                and token.text.lower() != answer.lower()
            ]

        # สุ่มและ deduplicate
        random.shuffle(candidates)
        seen = set()
        results = []
        for c in candidates:
            if c.lower() not in seen:
                seen.add(c.lower())
                results.append(c)
            if len(results) >= count:
                break

        return results[:count]

    def generate(self, correct: str, context: str, question: Optional[str] = None, count: int = 8) -> list[str]:
        # สร้าง input prompt
        if question:
            input_text = '{} {} {} {} {}'.format(correct, SEP_TOKEN, question, SEP_TOKEN, context)
        else:
            input_text = '{} {} {}'.format(correct, SEP_TOKEN, context)

        source_encoding = self.tokenizer(
            input_text,
            max_length=CHOICE_SOURCE_MAX_LEN,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            add_special_tokens=True,
            return_tensors='pt'
        )
        generated_ids = self.model.model.generate(
            input_ids=source_encoding['input_ids'].to(self.device),
            attention_mask=source_encoding['attention_mask'].to(self.device),
            num_beams=count,
            num_return_sequences=count,
            max_length=CHOICE_TARGET_MAX_LEN,
            repetition_penalty=2.5,
            length_penalty=1.0,
            early_stopping=True,
            use_cache=True
        )
        results = []
        seen = []
        for generated_id in generated_ids:
            decoded = self.tokenizer.decode(generated_id, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            parts = decoded.split(SEP_TOKEN)
            first_part = parts[0].strip()
            is_duplicate = any(first_part[:20] == s[:20] for s in seen)
            if first_part and not is_duplicate and first_part.lower() != correct.lower():
                results.append(first_part)
                seen.append(first_part)

        # T5 ได้ครบ จบ
        if len(results) >= 3:
            return results[:3]

        # ไม่ครบ ลองเติมด้วย WordNet
        needed = 3 - len(results)
        wn_results = get_wordnet_distractors(correct, count=needed)
        existing_lower = {r.lower() for r in results}
        for w in wn_results:
            if w.lower() not in existing_lower:
                results.append(w)
                existing_lower.add(w.lower())
            if len(results) >= 3:
                break

        # ถ้ายังไม่ครบอีก ก็สุ่มจาก context
        if len(results) < 3:
            needed = 3 - len(results)
            ctx_results = self._get_context_fallback(correct, context, count=needed)
            existing_lower = {r.lower() for r in results}
            for w in ctx_results:
                if w.lower() not in existing_lower:
                    results.append(w)
                    existing_lower.add(w.lower())
                if len(results) >= 3:
                    break

        return results[:3]


# if __name__ == '__main__':
#     cg = ChoiceGenerator(
#         checkpoint_path='model/model_gen_choice/model_choice.ckpt',
#     )

#     correct_answer = 'Oxygen'
#     question = 'What is the chemical element with the symbol O?'
#     context = "Oxygen is the chemical element with the symbol O and atomic number 8. It is a member of the chalcogen group in the periodic table, a highly reactive nonmetal, and an oxidizing agent that readily forms oxides with most elements as well as with other compounds. Oxygen is Earth's most abundant element, and after hydrogen and helium, it is the third-most abundant element in the universe. At standard temperature and pressure, two atoms of the element bind to form dioxygen, a colorless and odorless diatomic gas with the formula O2. Diatomic oxygen gas currently constitutes 20.95% of the Earth's atmosphere, though this has changed considerably over long periods of time. Oxygen makes up almost half of the Earth's crust in the form of oxides."

#     result = cg.generate(correct_answer, context, question=question)

#     print(f"Question: {question}")
#     print(f"Answer:   {correct_answer}")
#     print(f"Distractors: {result}")
#     print('--- test complete ---')