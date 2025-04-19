from transformers import ViTImageProcessor, ViTModel, logging
from numpy import ndarray
from torch.nn import CosineSimilarity

class ImageSimilarity:
    def __init__(self, model_path):
        logging.set_verbosity_error()
        self.processor = ViTImageProcessor.from_pretrained(model_path)
        self.model = ViTModel.from_pretrained(model_path)
        self.cos = CosineSimilarity(dim=0)
        self.source_features = None

    def src(self, source_img: ndarray):
        inputs = self.processor(source_img, return_tensors="pt")
        self.source_features = self.model(**inputs).last_hidden_state

    def compute(self, img: ndarray):
        if (self.source_features == None):
            return
        
        # img = Image.open(source_img).convert('RGB')
        # inputs = self.processor(source_img, return_tensors="pt")
        # source_features = self.model(**inputs).last_hidden_state

        # img = Image.open(path).convert('RGB')
        inputs = self.processor(img, return_tensors="pt")
        query_features = self.model(**inputs).last_hidden_state

        cos_sim = self.cos(self.source_features[0].reshape(-1), query_features[0].reshape(-1)).item()

        return cos_sim