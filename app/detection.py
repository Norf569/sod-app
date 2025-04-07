import threading
from utils.ObjectDetector import ObjectDetector
from configs import config
import logging
from PyQt6 import QtWidgets
import design
import os
import cv2
from utils.tools import update_pixmap

class Detection:
    def __init__(self, app: design.Ui_MainWindow):
        self.logger = logging.getLogger(__name__)
        self.app = app 
        self.detector = None
        self.labels = None
        self.conf_threshold = 0.5
        self.files = []
        self.images = []
        self.cidx = -1
        self.cancel_flag = False

        self.setup_ui()

    def setup_ui(self):
        self.app.det_image_label.setText('')
        self.app.det_add_button.clicked.connect(self.getFiles)
        self.app.det_delete_button.clicked.connect(self.deleteFile)
        self.app.det_files_listWidget.clicked.connect(self.updateInfo)

        self.app.det_obj_button.clicked.connect(self.process_callback)
        self.app.det_cancel_button.clicked.connect(self.cancel)

        self.app.det_save_all_button.clicked.connect(self.save_callback)

    def getFiles(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, 
                                                          'Выбрать изображения', 
                                                          './', 
                                                          config.__IMGTYPES__)
        
        if (files == []):
            return
        
        self.files = files
        for file in self.files:
            self.images.append(cv2.imread(file))

        self.app.det_files_listWidget.clear()
        self.app.det_files_listWidget.addItems(
            [os.path.basename(file) for file in self.files]
        )
        self.app.det_files_listWidget.setCurrentRow(0)
        self.updateInfo()

    def deleteFile(self):
        index = self.app.det_files_listWidget.currentIndex().row()

        if index == -1:
            return 
        
        self.files.pop(index)
        self.images.pop(index)
        self.app.det_image_label.clear()
        self.app.det_files_listWidget.takeItem(index)

        self.updateInfo()

    def updateInfo(self):
        index = self.app.det_files_listWidget.currentIndex().row()
        self.cidx = index

        if (index == -1):
            return

        update_pixmap(self.app.det_image_label, self.images[index])

    def setup_model(self):
        self.logger.info('detection model initializing...')

        self.app.det_info_label.setText('Инициализация модели обнаружения объектов...\n')
        self.app.det_cancel_button.setVisible(False)
        self.app.det_progressBar.setVisible(False)
        self.app.stackedWidget_detection.setCurrentIndex(0)

        try:
            self.detector = ObjectDetector(config.__OBJDET_MODEL__)
            self.labels = self.detector.labels()
        except Exception as ex:
            self.logger.exception(ex)
            self.app.det_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Не удалось инициализировать модель обнаружения объектов! Попробуйте перезапустить приложение', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
        else:
            self.app.stackedWidget_detection.setCurrentIndex(1)
            self.logger.info('detection model initialized')

    def dispose_model(self):
        pass

    def process_callback(self):
        if self.files == []:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для обработки!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        threading.Thread(target=self.process).start()

    def process(self):
        if self.detector == None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Модель не инициализирована!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
    
        self.logger.info(f'detecion...')

        self.app.det_info_label.setText('Идёт обнаружение объектов...')

        progress = 0
        self.app.det_progressBar.setMaximum(len(self.files))
        self.app.det_progressBar.setValue(progress)

        self.app.det_cancel_button.setVisible(True)
        self.app.det_progressBar.setVisible(True)
        self.app.stackedWidget_detection.setCurrentIndex(0)

        try:
            for image in self.images:
                if (self.cancel_flag):
                    break

                bbox, cls, conf = self.detector.compute(image).values()
                for i in range(len(bbox)):
                    if (conf[i] >= self.conf_threshold):
                        x, y, w, h = list(map(round, bbox[i]))
                        cv2.rectangle(image, (x-w//2, y-h//2), (x+w//2, y+h//2), (255, 255, 255), 2)
                        cv2.putText(image, 
                                    f'{self.labels[round(cls[i])]} ({round(conf[i], 2)})', 
                                    (x-w//2, y-h//2), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                        
                progress += 1
                self.app.det_progressBar.setValue(progress)
        except Exception as ex:
            self.logger.exception(ex)
            self.app.det_info_label.setText('Ошибка во время обработки изображений!')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Ошибка во время обнаружения объектов! Попробуйте перезапустить приложение', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
        else:
            self.cancel_flag = False
            self.updateInfo()
            self.app.stackedWidget_detection.setCurrentIndex(1)
            self.logger.info(f'detection done')

    def cancel(self):
        self.cancel_flag = True
        # self.app.det_info_label.setText('Остановка...')

    def save_callback(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(None,
                                                          'Выбрать папку',
                                                          './')
        if path == '':
            return
        
        if self.files == []:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для сохранения!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return

        threading.Thread(target=lambda: self.save(path)).start()
    
    def save(self, path):
        self.logger.info('saving...')

        self.app.det_info_label.setText('Идёт сохранение...')
        self.app.det_cancel_button.setVisible(False)
        self.app.det_progressBar.setVisible(False)
        self.app.stackedWidget_detection.setCurrentIndex(0)

        try:
            for idx in range(len(self.images)):
                filename = os.path.basename(self.files[idx])
                cv2.imwrite(os.path.join(path, filename), self.images[idx])
        except Exception as ex:
            self.logger.exception(ex)
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 'Не удалось сохранить файлы!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
        else:
            self.logger.info('saving completed')

        self.app.stackedWidget_detection.setCurrentIndex(1)


        