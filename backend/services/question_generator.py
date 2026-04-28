import torch
from transformers import T5ForConditionalGeneration, AutoTokenizer
import pytorch_lightning as pl

SEP_TOKEN = '<sep>'
MODEL_NAME = 't5-small'
SOURCE_MAX_TOKEN_LEN = 300
TARGET_MAX_TOKEN_LEN = 80

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.add_tokens(SEP_TOKEN)
tokenizer_len = len(tokenizer)


# ต้องนิยาม class เดิมที่ใช้ตอน train ไว้ด้วย เพื่อให้ load_from_checkpoint ทำงานได้
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


class QuestionGenerator:
    def __init__(self, checkpoint_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.tokenizer.add_tokens(SEP_TOKEN)
        
        self.model = QGModel.load_from_checkpoint(checkpoint_path)
        self.model.model.resize_token_embeddings(tokenizer_len) # เพิ่ม token ใหม่ต้อง resize
        self.model.eval()
        self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def generate(self, answer: str, context: str) -> str:
        source_encoding = self.tokenizer(
            '{} {} {}'.format(answer, SEP_TOKEN, context),
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
            num_beams=16,
            max_length=TARGET_MAX_TOKEN_LEN,
            repetition_penalty=2.5,
            length_penalty=1.0,
            early_stopping=True,
            use_cache=True
        )

        raw = self.tokenizer.decode(generated_ids[0], skip_special_tokens=False)

        # ตัดแค่ padding และ end token ออก เก็บ <sep> ไว้
        raw = raw.replace('</s>', '').replace('<pad>', '').strip()
        return raw




if __name__ == '__main__':
    qg = QuestionGenerator('model/model_gen_quiz/model_quiz.ckpt')
    sample_context = "Oxygen is the chemical element with the symbol O and atomic number 8. It is a member of the chalcogen group in the periodic table, a highly reactive nonmetal, and an oxidizing agent that readily forms oxides with most elements as well as with other compounds. Oxygen is Earth's most abundant element, and after hydrogen and helium, it is the third-most abundant element in the universe. At standard temperature and pressure, two atoms of the element bind to form dioxygen, a colorless and odorless diatomic gas with the formula O2. Diatomic oxygen gas currently constitutes 20.95% of the Earth's atmosphere, though this has changed considerably over long periods of time. Oxygen makes up almost half of the Earth's crust in the form of oxides."
    result = qg.generate('[MASK]', sample_context)
    
    print(f"Context: {sample_context}")
    print(f"Result: {result}")
    print('--- test complete ---')
