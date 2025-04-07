from numpy import ndarray
from transformers.utils import logging
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

class TextRecognizer:
    def __init__(self, model_path):
        logging.set_verbosity_error()
        self._processor = TrOCRProcessor.from_pretrained(model_path)
        self._model = VisionEncoderDecoderModel.from_pretrained(model_path)

    def compute(self, img: ndarray):
        # img = np.array(img.convert('RGB'))

        pixel_values = self._processor(img, return_tensors="pt").pixel_values
        generated_ids = self._model.generate(pixel_values, max_length=128)
        generated_text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return generated_text