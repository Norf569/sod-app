
import cv2
import numpy as np
from mmocr.apis import TextDetInferencer

class TextDetector:
    def __init__(self, model_path):
        self._inferencer = TextDetInferencer(model=model_path)
    
    def compute(self, img: np.ndarray):
        output_imgs = []

        polygons = self._inferencer(img)['predictions'][0]['polygons']
        for polygon in polygons:
            max_x, max_y, min_x, min_y = map(round, [max(polygon[::2]), 
                                                    max(polygon[1::2]), 
                                                    min(polygon[::2]), 
                                                    min(polygon[1::2])])

            poly = np.array([[polygon[j], polygon[j+1]] for j in range(0, len(polygon), 2)], dtype=np.int32)

            cv2.polylines(img, [poly], True, (0, 0, 0))

            croped_img = img.copy()
            mask = np.zeros(croped_img.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [poly], (255))
            croped_img = cv2.bitwise_and(croped_img, croped_img, mask = mask)
            croped_img = croped_img[min_y:max_y, min_x:max_x]

            output_imgs.append(croped_img)

        return {'full': img, 'croped': output_imgs}