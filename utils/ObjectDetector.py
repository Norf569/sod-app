from numpy import ndarray
from ultralytics import YOLO

class ObjectDetector():
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def compute(self, image: ndarray):
        results = self.model(image)[0].boxes
        return {'xywh': results.xywh.tolist(),
                'cls': results.cls.tolist(),
                'conf': results.conf.tolist()}
    
    def labels(self):
        return self.model.names