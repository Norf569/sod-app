from utils.TextDetector import TextDetector
from utils.TextRecognizer import TextRecognizer
from configs import config
import logging
from PyQt6 import QtWidgets, QtCore
from utils.tools import update_pixmap
import design
import os
import cv2
import json

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
        self.cidx = -1
        self.texts = []
        self.cancel_flag = False
        self.worker = None

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

        self.app.ocr_button.clicked.connect(self.process_callback)
        self.app.ocr_cancel_button.clicked.connect(self.cancel)

        self.app.ocr_save_button.clicked.connect(self.save_callback)

    def getFiles(self):
        if self.files != []:
            pressed = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Предупреждение', 'Несохранённые данные будут потеряны! Продолжить?', 
                                  QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No).exec()
            if pressed != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, 
                                                          'Выбрать изображения', 
                                                          './', 
                                                          config.__IMGTYPES__)
        
        if (files == []):
            return
        
        self.files = files
        self.images = []
        self.texts = []

        self.worker = GetFilesWorker(self)
        self.worker.start()

        self.worker.getfiles_started.connect(self.event_started)
        self.worker.getfiles_ended.connect(self.event_getfiles_ended)
        self.worker.finished.connect(self.event_worker_finished)

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
        self.cidx = index

        if (index == -1):
            return

        update_pixmap(self.app.ocr_image_label, self.images[index])

        self.app.ocr_textBrowser.setText('\n'.join(self.texts[index]))

    def langEng(self):
        self.app.ocr_eng_button.setChecked(True)
        self.app.ocr_rus_button.setChecked(False)
        self.lang = 'eng'

    def langRus(self):
        self.app.ocr_eng_button.setChecked(False)
        self.app.ocr_rus_button.setChecked(True)
        self.lang = 'rus'

    def setup_model(self):
        if not self.worker_isNone_msg():
            return
        
        self.worker = InitWorker(self)
        self.worker.start()

        event_init_ended = lambda: self.app.stackedWidget_ocr.setCurrentIndex(1)

        self.worker.init_started.connect(self.event_started)
        self.worker.init_exept.connect(self.event_init_exept)
        self.worker.init_ended.connect(event_init_ended)
        self.worker.finished.connect(self.event_worker_finished)

    def dispose_model(self):
        pass

    def process_callback(self):
        if (self.files == []): 
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для обработки!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        if (self.detector == None or 
            self.recognizer_eng == None or
            self.recognizer_rus == None):
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 
                                  'Модели не инициализированы!', 
                                  buttons=QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
    
        if not self.worker_isNone_msg():
            return
        
        self.worker = ProcessWorker(self)
        self.worker.start()

        event_progress_bar_update =  lambda progress: self.app.ocr_progressBar.setValue(progress)

        self.worker.processing_started.connect(self.evnet_prcessing_started)
        self.worker.progress_bar_update.connect(event_progress_bar_update)
        self.worker.processing_exept.connect(self.event_processing_exept)
        self.worker.processing_ended.connect(self.evnet_prcessing_ended)
        self.worker.finished.connect(self.event_worker_finished)

    def cancel(self):
        self.cancel_flag = True
        self.app.ocr_info_label.setText('Остановка...')

    def save_callback(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(None,
                                                          'Выбрать папку',
                                                          './')
        if path == '':
            return
        
        if (self.files == []): 
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для сохранения!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        if not self.worker_isNone_msg():
            return
        
        self.worker = SaveWorker(self, path)
        self.worker.start()

        event_saving_exept = lambda: QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 'Не удалось сохранить файлы!', 
                                                           QtWidgets.QMessageBox.StandardButton.Close).exec()
        event_saving_ended = lambda: self.app.stackedWidget_ocr.setCurrentIndex(1)

        self.worker.saving_started.connect(self.event_started)
        self.worker.saving_exept.connect(event_saving_exept)
        self.worker.saving_ended.connect(event_saving_ended)
        self.worker.finished.connect(self.event_worker_finished)

    def worker_isNone_msg(self):
        if self.worker != None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Происходит выполнение другой операции!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return False
        return True

    def event_started(self, text, visible = False):
        self.app.ocr_info_label.setText(text)
        self.app.ocr_cancel_button.setVisible(visible)
        self.app.ocr_progressBar.setVisible(visible)
        self.app.stackedWidget_ocr.setCurrentIndex(0)

    def event_init_exept(self):
        self.app.ocr_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                'Не удалось инициализировать модели обнаружения и распзнования текста! Попробуйте перезапустить приложение', 
                                QtWidgets.QMessageBox.StandardButton.Close).exec()

    def event_worker_finished(self):
        self.worker = None

    def evnet_prcessing_started(self):
        self.app.ocr_progressBar.setMaximum(len(self.files))
        self.app.ocr_progressBar.setValue(0)

        self.event_started('Идёт обнаружение и распознавание текста...', True)

    def event_processing_exept(self):
        self.app.ocr_info_label.setText('Ошибка во время обработки изображений!')
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                'Ошибка во время обнаружения и распозновнаие текста! Попробуйте перезапустить приложение', 
                                QtWidgets.QMessageBox.StandardButton.Close).exec()

    def evnet_prcessing_ended(self):
        self.cancel_flag = False
        self.updateInfo()
        self.app.stackedWidget_ocr.setCurrentIndex(1)

    def event_getfiles_ended(self):
        self.app.ocr_files_listWidget.clear()
        self.app.ocr_files_listWidget.addItems(
            [os.path.basename(file) for file in self.files]
        )

        self.app.ocr_files_listWidget.setCurrentRow(0)
        self.updateInfo()
        self.app.stackedWidget_ocr.setCurrentIndex(1)


class InitWorker(QtCore.QThread):
    init_started = QtCore.pyqtSignal(str)
    init_exept = QtCore.pyqtSignal()
    init_ended = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()

        self.parent_ = parent

    def run(self):
        self.parent_.logger.info('text detection model initializing...')
        self.init_started.emit('Инициализация модели обнаружения текста...\n')

        try:
            self.parent_.detector = TextDetector(config.__TEXTDET_MODEL__)
        except Exception as ex:
            self.init_exept.emit()
            self.parent_.logger.exception(ex)
        else: 
            self.parent_.logger.info('text detection model initialized')

        self.parent_.logger.info('text recognition model initializing...')
        self.init_started.emit('Инициализация модели распознавания текста...\n')
        try:
            self.parent_.recognizer_eng = TextRecognizer(config.__OCR_MODEL_ENG__)
            self.parent_.recognizer_rus = TextRecognizer(config.__OCR_MODEL_RUS__)
        except Exception as ex:
            self.init_exept.emit()
            self.parent_.logger.exception(ex)
        else:
            self.init_ended.emit()
            self.parent_.logger.info('text recognition model initialized')

class ProcessWorker(QtCore.QThread):
    processing_started = QtCore.pyqtSignal()
    progress_bar_update = QtCore.pyqtSignal(int)
    processing_exept = QtCore.pyqtSignal()
    processing_ended = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()

        self.parent_ = parent

    def run(self):
        self.parent_.logger.info(f'text detection and recognition...')
        self.processing_started.emit()
        progress = 0

        try:
            self.parent_.texts = [''] * len(self.parent_.files) 
            for index in range(len(self.parent_.files)):
                if (self.parent_.cancel_flag):
                    break

                text = []
                full_image, croped_images = self.parent_.detector.compute(
                    self.parent_.images[index]).values()

                if len(croped_images) > 0:
                    for text_image in croped_images:
                        if (self.parent_.lang == 'rus'):
                            text.append(self.parent_.recognizer_rus.compute(text_image))
                        elif (self.parent_.lang == 'eng'):
                            text.append(self.parent_.recognizer_eng.compute(text_image))
                        else:
                            self.parent_.logger.error('invalid language')
                            break
                
                self.parent_.images[index] = full_image
                text.reverse()
                self.parent_.texts[index] = text

                progress += 1
                self.progress_bar_update.emit(progress)

        except Exception as ex:
            self.processing_exept.emit()
            self.parent_.logger.exception(ex)
        else:
            self.processing_ended.emit()
            self.parent_.logger.info(f'text detection and recognition done')

class SaveWorker(QtCore.QThread):
    saving_started = QtCore.pyqtSignal(str)
    saving_exept = QtCore.pyqtSignal()
    saving_ended = QtCore.pyqtSignal()

    def __init__(self, parent, path):
        super().__init__()

        self.parent_ = parent
        self.path = path

    def run(self):
        self.parent_.logger.info('saving...')
        self.saving_started.emit('Идёт сохранение...')

        try:
            dir = os.path.join(self.path, 'images')
            os.mkdir(dir)

            res_dict = {}
            for idx in range(len(self.parent_.files)):
                name = os.path.basename(self.parent_.files[idx])

                res_dict[name] = {}
                res_dict[name]['text'] = self.parent_.texts[idx]

                cv2.imwrite(os.path.join(dir, name), self.parent_.images[idx])

            with open(os.path.join(self.path, 'recognized_text.json'), 'w', encoding='utf-8') as file:
                json.dump(res_dict, file, indent=2)
        except Exception as ex:
            self.saving_exept.emit()
            self.parent_.logger.exception(ex)
        else:
            self.saving_ended.emit()
            self.parent_.logger.info('saving completed')

class GetFilesWorker(QtCore.QThread):
    getfiles_started = QtCore.pyqtSignal(str)
    getfiles_ended = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__()

        self.parent_ = parent

    def run(self):
        if len(self.parent_.files) > 100:
            self.getfiles_started.emit('Загрузка изображений...')

        for file in self.parent_.files:
            self.parent_.images.append(cv2.imread(file))
            self.parent_.texts.append([])
        
        self.getfiles_ended.emit()