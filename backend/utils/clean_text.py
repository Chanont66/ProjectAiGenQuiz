import re

def clean(text: str) -> str:
    text = re.sub(r'\((.*?)\)', '', text)  # ลบ (วงเล็บ)
    text = re.sub(r'\[(.*?)\]', '', text)  # ลบ [วงเล็บ]
    text = re.sub(' +', ' ', text)          # ลบ space ซ้ำ
    text = text.replace('–', '-')           # แก้ hyphen แปลก
    return text.strip()


import re
import string

def normalize(text: str) -> str:
    text = text.lower()
    text = ''.join(ch for ch in text if ch not in string.punctuation)
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    return ' '.join(text.split())

# # ใน process_quiz หลัง choices = [answer] + distractors
# choices = list({normalize(c): c for c in choices}.values())  # ลบซ้ำ
# choices = [c for c in choices if normalize(c) != normalize(answer)]  # ลบที่เหมือน answer
# choices = [answer] + choices[:3]  # เติม answer กลับ
# random.shuffle(choices)