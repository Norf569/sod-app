import threading
from utils.TextDetector import TextDetector
from utils.TextRecognizer import TextRecognizer
from configs import config
from PIL import Image
import logging
from PyQt6 import QtWidgets, QtGui, QtCore
import design
import os
import cv2
import json


'''

mem leak

проверка на уверенность

'''


class Ocr:
    def __init__(self, app: design.Ui_MainWindow):
        self.logger = logging.getLogger(__name__)
        self.app = app 
        self.recognizer_rus = None
        self.recognizer_eng = None
        self.detector = None
        self.lang = 'rus'
        self.conf_threshold = 0.5
        self.files = []
        self.images = []
        self.texts = []
        self.cancel_flag = False

        self.setup_ui()

    def setup_ui(self):
        self.app.ocr_add_button.clicked.connect(self.getFiles)
        self.app.ocr_delete_button.clicked.connect(self.deleteFile)
        self.app.ocr_files_listWidget.clicked.connect(self.updateInfo)

        self.app.ocr_rus_button.setCheckable(True)
        self.app.ocr_eng_button.setCheckable(True)
        self.app.ocr_rus_button.setChecked(True)
        self.app.ocr_rus_button.clicked.connect(self.langRus)
        self.app.ocr_eng_button.clicked.connect(self.langEng)

        ocr_callback = lambda: threading.Thread(target=self.process).start()
        self.app.ocr_button.clicked.connect(ocr_callback)
        self.app.ocr_cancel_button.clicked.connect(self.cancel)

        self.app.ocr_save_button.clicked.connect(self.save_callback)

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
            self.texts.append([])

        self.app.ocr_files_listWidget.clear()
        self.app.ocr_files_listWidget.addItems(
            [os.path.basename(file) for file in self.files]
        )
        self.app.ocr_files_listWidget.setCurrentRow(0)
        self.updateInfo()

    def deleteFile(self):
        index = self.app.ocr_files_listWidget.currentIndex().row()

        if index == -1:
            return 
        
        self.files.pop(index)
        self.images.pop(index)
        self.texts.pop(index)
        self.app.ocr_image_label.clear()
        self.app.ocr_textBrowser.clear()
        self.app.ocr_files_listWidget.takeItem(index)

        self.updateInfo()

    def updateInfo(self):
        index = self.app.ocr_files_listWidget.currentIndex().row()

        if (index == -1):
            return

        image = self.images[index]
        qt_image = QtGui.QImage(image,
                              image.shape[1],
                              image.shape[0],
                              image.strides[0],
                              QtGui.QImage.Format.Format_BGR888)
        pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
            self.app.ocr_image_label.width(),
            self.app.ocr_image_label.height(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        ) 
        self.app.ocr_image_label.setPixmap(pixmap)
        self.app.ocr_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.app.ocr_textBrowser.setText('\n'.join(self.texts[index]))

    def langEng(self):
        self.app.ocr_eng_button.setChecked(True)
        self.app.ocr_rus_button.setChecked(False)
        self.lang = 'eng'

    def langRus(self):
        self.app.ocr_eng_button.setChecked(False)
        self.app.ocr_rus_button.setChecked(True)
        self.lang = 'eng'

    def setup_model(self):
        self.logger.info('text detection model initializing...')

        
        self.app.ocr_info_label.setText('Инициализация модели обнаружения текста...\n')
        self.app.ocr_cancel_button.setVisible(False)
        self.app.ocr_progressBar.setVisible(False)
        self.app.stackedWidget_ocr.setCurrentIndex(0)

        try:
            self.detector = TextDetector(config.__TEXTDET_MODEL__)
        except Exception as ex:
            self.app.ocr_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
            self.logger.exception(ex)
        else: 
            self.logger.info('text detection model initialized')

        self.logger.info('text recognition model initializing...')
        self.app.ocr_info_label.setText('Инициализация модели распознавания текста...\n')
        try:
            self.recognizer_eng = TextRecognizer(config.__OCR_MODEL_ENG__)
            self.recognizer_rus = TextRecognizer(config.__OCR_MODEL_RUS__)
        except Exception as ex:
            self.app.ocr_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Не удалось инициализировать модели обнаружения и распзнования текста! Попробуйте перезапустить приложение', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            self.logger.exception(ex)
        else:
            self.app.stackedWidget_ocr.setCurrentIndex(1)
            self.logger.info('text recognition model initialized')

    def dispose_model(self):
        pass

    def process(self):
        if (self.detector == None or 
            self.recognizer_eng == None or
            self.recognizer_rus == None):
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 
                                  'Модели не инициализированы!', 
                                  buttons=QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
    
        self.logger.info(f'text detection and recognition...')

        self.app.ocr_info_label.setText('Идёт обнаружение и распознавание текста...')

        progress = 0
        self.app.ocr_progressBar.setMaximum(len(self.files))
        self.app.ocr_progressBar.setValue(progress)

        self.app.ocr_cancel_button.setVisible(True)
        self.app.ocr_progressBar.setVisible(True)
        self.app.stackedWidget_ocr.setCurrentIndex(0)

        try:
            self.texts = [''] * len(self.files) 
            for index in range(len(self.files)):
                if (self.cancel_flag):
                    break

                text = []
                full_image, croped_images = self.detector.compute(self.images[index]).values()

                if len(croped_images) > 0:
                    for text_image in croped_images:
                        if (self.lang == 'rus'):
                            text.append(self.recognizer_rus.compute(text_image))
                        elif (self.lang == 'eng'):
                            text.append(self.recognizer_eng.compute(text_image))
                        else:
                            self.logger.error('invalid language')
                            break
                
                self.images[index] = full_image
                text.reverse()
                self.texts[index] = text

                progress += 1
                self.app.ocr_progressBar.setValue(progress)

        except Exception as ex:
            self.logger.exception(ex)
            self.app.ocr_info_label.setText('Ошибка во время обработки изображений!')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Ошибка во время обнаружения и распозновнаие текста! Попробуйте перезапустить приложение', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
        else:
            self.cancel_flag = False
            self.app.stackedWidget_ocr.setCurrentIndex(1)
            self.logger.info(f'text detection and recognition done')

    def cancel(self):
        self.cancel_flag = True
        # self.app.ocr_info_label.setText('Остановка...')

    def save_callback(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(None,
                                                          'Выбрать папку',
                                                          './')
        if path == '':
            return
        
        if (len(self.files) == 0): 
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для сохранения!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        threading.Thread(target=lambda: self.save(path)).start()

    def save(self, path):
        self.logger.info('saving...')

        self.app.ocr_info_label.setText('Идёт сохранение...')
        self.app.ocr_cancel_button.setVisible(False)
        self.app.ocr_progressBar.setVisible(False)
        self.app.stackedWidget_ocr.setCurrentIndex(0)

        try:
            dir = os.path.join(path, 'images')
            os.mkdir(dir)

            res_dict = {}
            for idx in range(len(self.files)):
                name = os.path.basename(self.files[idx])

                res_dict[name] = {}
                res_dict[name]['text'] = self.texts[idx]

                cv2.imwrite(os.path.join(dir, name), self.images[idx])

            with open(os.path.join(path, 'recognized_text.json'), 'w', encoding='utf-8') as file:
                json.dump(res_dict, file, indent=2)
        except Exception as ex:
            self.logger.exception(ex)
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 'Не удалось сохранить файлы!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
        else:
            self.logger.info('saving completed')

        self.app.stackedWidget_ocr.setCurrentIndex(1)