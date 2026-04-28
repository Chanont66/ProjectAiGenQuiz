import pytorch_lightning as pl
from transformers import T5ForConditionalGeneration, AutoTokenizer
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
import torch

torch.serialization.add_safe_globals([ModelCheckpoint])

SEP_TOKEN = '<sep>'
MODEL_NAME = 't5-small'

# Choice Generator Constants
CHOICE_SOURCE_MAX_LEN = 512
CHOICE_TARGET_MAX_LEN = 64

# Question Generator Constants
QUESTION_SOURCE_MAX_LEN = 300
QUESTION_TARGET_MAX_LEN = 80

class QGModel(pl.LightningModule):
    def __init__(self, tokenizer_len: int):
        super().__init__()
        self.model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME, return_dict=True)
        self.model.resize_token_embeddings(tokenizer_len)

    def forward(self, input_ids, attention_mask, labels=None):
        output = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        return output.loss, output.logits

    def configure_optimizers(self):
        pass

def get_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.add_tokens(SEP_TOKEN)
    return tokenizer
