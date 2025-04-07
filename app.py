	
import sys 
from PyQt6 import QtWidgets
import design

from app.detection import Detection
from app.ocr import Ocr 
from app.similarity import Similarity
import threading
import logging


class App(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.info('app initialization...')

        self.setupUi(self)

        self.detector = Detection(self)
        self.ocr = Ocr(self)
        self.similarity = Similarity(self)

        self.logger.info('app initialized')

        threading.Thread(target=self.detector.setup_model).start()
        threading.Thread(target=self.ocr.setup_model).start()
        threading.Thread(target=self.similarity.setup_model).start()

def main():
    logging.basicConfig(filename='log.log', level=logging.INFO,
                        filemode='w', format='%(asctime)s %(name)s %(levelname)s %(message)s')
    logging.info('logging started')

    try:
        app = QtWidgets.QApplication(sys.argv) 
        window = App() 
        window.show()  
        app.exec()  
    except Exception as ex:
        logging.exception(ex)

    logging.info('logging stopped')

if __name__ == '__main__':  
    main()


        
