import threading
from utils.ObjectDetector import ObjectDetector
from configs import config
import logging
from PyQt6 import QtWidgets, QtCore
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
        self.worker = None

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
        if self.files != []:
            pressed = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Предупреждение', 'Несохранённые данные будут потеряны! Продолжить?', 
                                  QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No).exec()
            if pressed != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            
            
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(None, 
                                                          'Выбрать изображения', 
                                                          './', 
                                                          config.__IMGTYPES__)
        
        if (files == [] or not self.worker_isNone_msg()):
            return

        self.files = files

        self.worker = GetFilesWorker(self)
        self.worker.start()

        self.worker.getfiles_started.connect(lambda: self.event_started('Загрузка изображений...'))
        self.worker.getfiles_ended.connect(self.event_getfiles_ended)
        self.worker.finished.connect(self.event_worker_finished)

    def event_getfiles_ended(self):
        self.app.det_files_listWidget.clear()
        self.app.det_files_listWidget.addItems(
            [os.path.basename(file) for file in self.files]
        )
        self.app.det_files_listWidget.setCurrentRow(0)
        self.updateInfo()
        self.app.stackedWidget_detection.setCurrentIndex(1)

    def event_started(self, text):
        self.app.det_info_label.setText(text)
        self.app.det_cancel_button.setVisible(False)
        self.app.det_progressBar.setVisible(False)
        self.app.stackedWidget_detection.setCurrentIndex(0)

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

    def worker_isNone_msg(self):
        if self.worker != None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Происходит выполнение другой операции!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return False
        return True

    def setup_model(self):
        if not self.worker_isNone_msg():
            return
        
        self.worker = InitWorker(self)
        self.worker.start()

        event_init_ended = lambda: self.app.stackedWidget_detection.setCurrentIndex(1)

        self.worker.init_started.connect(self.event_init_started)
        self.worker.init_exept.connect(self.event_init_exept)
        self.worker.init_ended.connect(event_init_ended)
        self.worker.finished.connect(self.event_worker_finished)

    def event_init_started(self):
        self.app.det_info_label.setText('Инициализация модели обнаружения объектов...\n')
        self.app.det_cancel_button.setVisible(False)
        self.app.det_progressBar.setVisible(False)
        self.app.stackedWidget_detection.setCurrentIndex(0)

    def event_init_exept(self):
        self.app.det_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                'Не удалось инициализировать модель обнаружения объектов! Попробуйте перезапустить приложение', 
                                QtWidgets.QMessageBox.StandardButton.Close).exec()

    def dispose_model(self):
        pass

    def process_callback(self):
        if self.files == []:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для обработки!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        if not self.worker_isNone_msg():
            return

        self.worker = ProcessWorker(self)
        self.worker.start()

        event_detection_isNoen = lambda: QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                         'Модель не инициализирована!', 
                                         QtWidgets.QMessageBox.StandardButton.Close).exec()
        event_progress_bar_update =  lambda progress: self.app.det_progressBar.setValue(progress)

        self.worker.detector_isNone.connect(event_detection_isNoen)
        self.worker.detection_started.connect(self.evnet_detecion_started)
        self.worker.progress_bar_update.connect(event_progress_bar_update)
        self.worker.detection_exept.connect(self.event_detection_exept)
        self.worker.detection_ended.connect(self.event_detection_ended)
        self.worker.finished.connect(self.event_worker_finished)
        
    def evnet_detecion_started(self):
        self.app.det_progressBar.setMaximum(len(self.files))
        self.app.det_progressBar.setValue(0)

        self.event_started('Идёт обнаружение объектов...')

    def event_detection_exept(self):
        self.app.det_info_label.setText('Ошибка во время обработки изображений!')
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                'Ошибка во время обнаружения объектов! Попробуйте перезапустить приложение', 
                                QtWidgets.QMessageBox.StandardButton.Close).exec()
    
    def event_worker_finished(self):
        self.worker = None
        
    def event_detection_ended(self):
        self.cancel_flag = False
        self.updateInfo()
        self.app.stackedWidget_detection.setCurrentIndex(1)

    def cancel(self):
        self.cancel_flag = True
        self.app.det_info_label.setText('Остановка...')

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

        if not self.worker_isNone_msg():
            return
        
        self.worker = SaveWorker(self, path)
        self.worker.start()

        event_saving_exept = lambda: QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 'Не удалось сохранить файлы!', 
                                                           QtWidgets.QMessageBox.StandardButton.Close).exec()
        event_saving_ended = lambda: self.app.stackedWidget_detection.setCurrentIndex(1)

        self.worker.saving_started.connect(lambda: self.event_saving_started('Идёт сохранение...'))
        self.worker.saving_exept.connect(event_saving_exept)
        self.worker.saving_ended.connect(event_saving_ended)
        self.worker.finished.connect(self.event_worker_finished)


class InitWorker(QtCore.QThread):
    init_started = QtCore.pyqtSignal()
    init_exept = QtCore.pyqtSignal()
    init_ended = QtCore.pyqtSignal()

    def __init__(self, parent: Detection):
        super().__init__()

        self.parent_ = parent

    def run(self):
        self.parent_.logger.info('detection model initializing...')

        self.init_started.emit()

        try:
            self.parent_.detector = ObjectDetector(config.__OBJDET_MODEL__)
            self.parent_.labels = self.parent_.detector.labels()
        except Exception as ex:
            self.parent_.logger.exception(ex)
            self.init_exept.emit()
        else:
            self.init_ended.emit()
            self.parent_.logger.info('detection model initialized')

class ProcessWorker(QtCore.QThread):
    detector_isNone = QtCore.pyqtSignal()
    detection_started = QtCore.pyqtSignal()
    progress_bar_update = QtCore.pyqtSignal(int)
    detection_exept = QtCore.pyqtSignal()
    detection_ended = QtCore.pyqtSignal()

    def __init__(self, parent: Detection): 
        super().__init__()

        self.parent_ = parent

    def run(self):
        if self.parent_.detector == None:
            self.detector_isNone.emit()
            return
    
        self.parent_.logger.info(f'detecion...')

        self.detection_started.emit()
        progress = 0

        try:
            for image in self.parent_.images:
                if (self.parent_.cancel_flag):
                    break

                bbox, cls, conf = self.parent_.detector.compute(image).values()
                for i in range(len(bbox)):
                    if (conf[i] >= self.parent_.conf_threshold):
                        x, y, w, h = list(map(round, bbox[i]))
                        cv2.rectangle(image, (x-w//2, y-h//2), (x+w//2, y+h//2), (255, 255, 255), 2)
                        cv2.putText(image, 
                                    f'{self.parent_.labels[round(cls[i])]} ({round(conf[i], 2)})', 
                                    (x-w//2, y-h//2), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                        
                progress += 1
                self.progress_bar_update.emit(progress)
        except Exception as ex:
            self.parent_.logger.exception(ex)
            self.detection_exept.emit()
        else:
            self.detection_ended.emit()
            self.parent_.logger.info(f'detection done')

class SaveWorker(QtCore.QThread):
    saving_started = QtCore.pyqtSignal()
    saving_exept = QtCore.pyqtSignal()
    saving_ended = QtCore.pyqtSignal()

    def __init__(self, parent, path):
        super().__init__()

        self.parent_ = parent
        self.path = path

    def run(self):
        self.parent_.logger.info('saving...')
        self.saving_started.emit()

        try:
            for idx in range(len(self.parent_.images)):
                filename, extension = os.path.splitext(os.path.basename(self.parent_.files[idx]))
                cv2.imwrite(os.path.join(self.path, f'{filename}_objects{extension}'), self.parent_.images[idx])
        except Exception as ex:
            self.parent_.logger.exception(ex)
            self.saving_exept.emit()
        else:
            self.saving_ended.emit()
            self.parent_.logger.info('saving completed')

class GetFilesWorker(QtCore.QThread):
    getfiles_started = QtCore.pyqtSignal()
    getfiles_ended = QtCore.pyqtSignal()

    def __init__(self, parent: Detection):
        super().__init__()
        
        self.parent_ = parent

    def run(self):
        if len(self.parent_.files) > 100:
            self.getfiles_started.emit()

        for file in self.parent_.files:
            self.parent_.images.append(cv2.imread(file))

        self.getfiles_ended.emit()
        