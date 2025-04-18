
import cv2
import numpy as np
from mmocr.apis import TextDetInferencer
from sklearn.linear_model import LinearRegression

class TextDetector:
    def __init__(self, model_path):
        self._inferencer = TextDetInferencer(model=model_path)
        self._linear_model = LinearRegression()
    
    def compute(self, img: np.ndarray):
        output_imgs = []
        full_img = img.copy()

        prediction = self._inferencer(img)['predictions'][0]
        polygons = prediction['polygons']
        scores = prediction['scores']
        for i in range(len(polygons)):
            if (scores[i] < 0.5):
                continue

            polygon = polygons[i]
            max_x, max_y, min_x, min_y = map(round, [max(polygon[::2]), 
                                                    max(polygon[1::2]), 
                                                    min(polygon[::2]), 
                                                    min(polygon[1::2])])

            poly = np.array([[polygon[j], polygon[j+1]] for j in range(0, len(polygon), 2)], dtype=np.int32)

            cv2.polylines(full_img, [poly], True, (127, 127, 127), 1)

            croped_img = img.copy()[min_y:max_y, min_x:max_x]
            mask = np.zeros(img.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [poly], (255))
            mask = mask[min_y:max_y, min_x:max_x]
            croped_img = cv2.bitwise_and(croped_img, croped_img, mask = mask)

            nonzero = mask.nonzero()
            X = nonzero[1].reshape(-1, 1)
            y = nonzero[0].reshape(-1, 1)
            self._linear_model.fit(X, y)

            rad = np.arctan(self._linear_model.coef_)
            deg = float(rad * 180 / 3.14)
            (h, w) = croped_img.shape[:2]
            new_w, new_h = abs(np.sin(rad)*h) + abs(np.cos(rad)*w), abs(np.sin(rad)*w) + abs(np.cos(rad)*h)
            M = cv2.getRotationMatrix2D((w // 2, h // 2), deg, 1)
            M[0][2] += (new_w - w) / 2
            M[1][2] += (new_h - h) / 2
            croped_img = cv2.warpAffine(croped_img, M, (int(new_w), int(new_h)))

            nonzero = croped_img.nonzero() # занимает много времени
            max_x, max_y, min_x, min_y = map(round, [max(nonzero[1]), 
                                                    max(nonzero[0]), 
                                                    min(nonzero[1]), 
                                                    min(nonzero[0])])
            croped_img = croped_img[min_y:max_y, min_x:max_x]

            output_imgs.append(croped_img)
            
        return {'full': full_img, 'croped': output_imgs}