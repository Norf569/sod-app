	
import sys 
from PyQt6 import QtWidgets, QtGui
import design

from utils.tools import update_pixmap
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

        font = QtGui.QFont();
        font.setPointSize(12);
        self.setFont(font);

        self.detector = Detection(self)
        self.ocr = Ocr(self)
        self.similarity = Similarity(self)

        self.logger.info('app initialized')

        self.detector.setup_model()
        threading.Thread(target=self.ocr.setup_model).start()
        threading.Thread(target=self.similarity.setup_model).start()

    def resizeEvent(self, event):
        tab = self.tabWidget.currentIndex()
        if tab == 0:
            update_pixmap(self.sim_image_label, self.similarity.image)
            update_pixmap(self.sim_src_label, self.similarity.src_image)
        elif tab == 1:
            index = self.ocr.cidx
            if index != -1:
                update_pixmap(self.ocr_image_label, self.ocr.images[index])
        elif tab == 2:
            index = self.detector.cidx
            if index != -1:
                update_pixmap(self.det_image_label, self.detector.images[index])

        super().resizeEvent(event)

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


        
