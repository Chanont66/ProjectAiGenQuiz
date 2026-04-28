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
