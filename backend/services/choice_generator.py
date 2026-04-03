# backend/services/choice_generator.py

import torch
from transformers import T5ForConditionalGeneration, AutoTokenizer
import pytorch_lightning as pl
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
import spacy
from sense2vec import Sense2Vec

torch.serialization.add_safe_globals([ModelCheckpoint])

SEP_TOKEN = '<sep>'
MODEL_NAME = 't5-small'
SOURCE_MAX_TOKEN_LEN = 512
TARGET_MAX_TOKEN_LEN = 64

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.add_tokens(SEP_TOKEN)
tokenizer_len = len(tokenizer)


class QGModel(pl.LightningModule):
    def __init__(self):
        super().__init__()
        self.model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME, return_dict=True)
        self.model.resize_token_embeddings(tokenizer_len)

    def forward(self, input_ids, attention_mask, labels=None):
        output = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        return output.loss, output.logits

    def configure_optimizers(self):
        pass


class ChoiceGenerator:
    def __init__(self, checkpoint_path: str, s2v_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.tokenizer.add_tokens(SEP_TOKEN)
        self.model = QGModel.load_from_checkpoint(checkpoint_path)
        self.model.model.resize_token_embeddings(tokenizer_len)
        self.model.eval()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        self.s2v = Sense2Vec().from_disk(s2v_path)
        self.nlp = spacy.load('en_core_web_sm')

    def _get_s2v_distractors(self, answer: str, count: int = 3) -> list[str]:
        from collections import OrderedDict
        
        answer_normalized = answer.lower().replace(' ', '_')
        sense = self.s2v.get_best_sense(answer_normalized)
        
        if not sense:
            return []
        
        most_similar = self.s2v.most_similar(sense, n=count + 5)  # เผื่อกรองออก
        
        results = []
        for phrase in most_similar:
            text = phrase[0].split('|')[0].replace('_', ' ').lower()
            if text != answer.lower():
                results.append(text.capitalize())
            if len(results) >= count:
                break
        
        return list(OrderedDict.fromkeys(results))

    def generate(self, correct: str, context: str, count: int = 8) -> list[str]:
        source_encoding = self.tokenizer(
            '{} {} {}'.format(correct, SEP_TOKEN, context),
            max_length=SOURCE_MAX_TOKEN_LEN,
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
            max_length=TARGET_MAX_TOKEN_LEN,
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

        # ถ้า T5 ได้ไม่ครบ 3 → เติมด้วย sense2vec
        if len(results) < 3:
            s2v_results = self._get_s2v_distractors(correct, count=3 - len(results))
            results += s2v_results

        return results[:3]




# if __name__ == '__main__':
#     # ---------------------------- test ----------------------------
#     cg = ChoiceGenerator(
#         # checkpoint_path='model/model_gen_choice/model_choice.ckpt',
#         checkpoint_path='model/model_gen_choice/race-distractors.ckpt',
#         s2v_path='model/s2v_reddit/s2v_reddit_2015_md/s2v_old'
#     )
#     result = cg.generate('Oxygen', 'Oxygen is the chemical element with the symbol O and atomic number 8.')
#     print(result)

# pip install sense2vec spacy
# python -m spacy download en_core_web_sm