import torch
import pytorch_lightning as pl
from .shared import QGModel, SEP_TOKEN, get_tokenizer, QUESTION_SOURCE_MAX_LEN, QUESTION_TARGET_MAX_LEN


class QuestionGenerator:
    def __init__(self, checkpoint_path: str):
        self.tokenizer = get_tokenizer()
        self.model = QGModel.load_from_checkpoint(checkpoint_path, tokenizer_len=len(self.tokenizer))
        self.model.eval()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)

    def generate(self, answer: str, context: str) -> str:
        source_encoding = self.tokenizer(
            '{} {} {}'.format(answer, SEP_TOKEN, context),
            max_length=QUESTION_SOURCE_MAX_LEN,
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
            max_length=QUESTION_TARGET_MAX_LEN,
            repetition_penalty=2.5,
            length_penalty=1.0,
            early_stopping=True,
            use_cache=True
        )

        raw = self.tokenizer.decode(generated_ids[0], skip_special_tokens=False)

        # ตัดแค่ padding และ end token ออก เก็บ <sep> ไว้
        raw = raw.replace('</s>', '').replace('<pad>', '').strip()
        return raw




# if __name__ == '__main__':
#     qg = QuestionGenerator('model/model_gen_quiz/model_quiz.ckpt')
#     sample_context = "Oxygen is the chemical element with the symbol O and atomic number 8. It is a member of the chalcogen group in the periodic table, a highly reactive nonmetal, and an oxidizing agent that readily forms oxides with most elements as well as with other compounds. Oxygen is Earth's most abundant element, and after hydrogen and helium, it is the third-most abundant element in the universe. At standard temperature and pressure, two atoms of the element bind to form dioxygen, a colorless and odorless diatomic gas with the formula O2. Diatomic oxygen gas currently constitutes 20.95% of the Earth's atmosphere, though this has changed considerably over long periods of time. Oxygen makes up almost half of the Earth's crust in the form of oxides."
#     result = qg.generate('[MASK]', sample_context)
    
#     print(f"Context: {sample_context}")
#     print(f"Result: {result}")
#     print('--- test complete ---')
