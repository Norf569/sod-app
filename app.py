	
import logging.handlers
import sys 
from PyQt6 import QtWidgets, QtGui
import design

from utils.tools import update_pixmap
from app.detection import Detection
from app.ocr import Ocr 
from app.similarity import Similarity
import logging


class App(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.info('app initialization...')

        self.setupUi(self)

        self.setWindowIcon(QtGui.QIcon('icon.png'))

        font = QtGui.QFont();
        font.setPointSize(12);
        self.setFont(font);

        self.detector = Detection(self)
        self.ocr = Ocr(self)
        self.similarity = Similarity(self)

        self.detector.setup_model()
        self.ocr.setup_model()
        self.similarity.setup_model()

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

    handler = logging.handlers.RotatingFileHandler(filename='app.log',
                                                            mode='a',
                                                            maxBytes=536870912, #500 mb
                                                            backupCount=1)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        handlers=[handler])
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


        
