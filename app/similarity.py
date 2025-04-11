import threading
from utils.ImageSimilarity import ImageSimilarity
from configs import config
import logging
from PyQt6 import QtWidgets, QtGui, QtCore
import design
import os
import cv2
import json
from utils.tools import update_pixmap

class Similarity:
    def __init__(self, app: design.Ui_MainWindow):
        self.logger = logging.getLogger(__name__)
        self.app = app 
        self.similarity = None
        self.threshold = 0
        self.src_file = None
        self.src_image = None
        self.files = []
        self.image = None
        self.sims_list = []
        self.slider_flag = False
        self.cancel_flag = False

        self.setup_ui()

    def setup_ui(self):
        self.app.sim_files_tableWidget.setHorizontalHeaderLabels(['Название', 'Процент схожести', 'index'])
        self.app.sim_files_tableWidget.setColumnHidden(2, True)

        self.app.sim_add_button.clicked.connect(self.getFiles)
        self.app.sim_delete_button.clicked.connect(self.deleteFile)
        self.app.sim_files_tableWidget.clicked.connect(self.updateInfo)
        self.app.sim_add_src_button.clicked.connect(self.getSrcFile)
        self.app.sim_delete_src_button.clicked.connect(self.deleteSrcFile)

        self.app.sim_button.clicked.connect(self.process_callback)

        self.app.sim_save_button.clicked.connect(self.save)
        self.app.sim_degree_slider.valueChanged.connect(self.thresholdUpdate)
        self.app.sim_degree_slider.sliderPressed.connect(self.pressedFlagRaise)
        self.app.sim_degree_slider.sliderReleased.connect(self.pressedFlagDown)

        self.app.sim_cancel_button.clicked.connect(self.cancel)

    def pressedFlagRaise(self):
        self.slider_flag = True

    def pressedFlagDown(self):
        self.slider_flag = False
        self.updateDegree()

    def getFiles(self):
        if self.sims_list != []:
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
        self.sims_list = []

        self.app.sim_degree_label.clear()
        self.app.sim_files_tableWidget.setRowCount(len(self.files))
        row = 0
        for file in self.files:
            self.app.sim_files_tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(os.path.basename(file)))
            self.app.sim_files_tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(row)))
            row += 1

        self.updateDegree()
        self.app.sim_files_tableWidget.setCurrentCell(0, 0)
        self.updateInfo()

    def getSrcFile(self):
        #данные добавляются, а не удаляются
        file, _ = QtWidgets.QFileDialog.getOpenFileName(None, 
                                                        'Выбрать изображение', 
                                                        './', 
                                                        config.__IMGTYPES__)
        
        if (file == ''):
            return
        
        self.src_file = file
        self.src_image = cv2.imread(file)
        self.sims_list = []

        self.app.sim_src_lineEdit.clear()
        self.app.sim_src_lineEdit.setText(os.path.basename(file))
        update_pixmap(self.app.sim_src_label, self.src_image)

        self.app.sim_degree_label.clear()
        self.updateDegree()

    def deleteFile(self):
        row_index = self.app.sim_files_tableWidget.currentRow()
        if row_index == -1:
            return 
        
        index = int(self.app.sim_files_tableWidget.item(row_index, 2).text())
        
        self.files.pop(index)
        self.image = None
        if (self.sims_list != []):
            self.sims_list.pop(index)
        self.app.sim_image_label.clear()
        self.app.sim_degree_label.clear()
        self.app.sim_files_tableWidget.removeRow(row_index)

        for row in range(self.app.sim_files_tableWidget.rowCount()):
            new_index = int(self.app.sim_files_tableWidget.item(row, 2).text())
            if (new_index > index):
                new_index -= 1
                self.app.sim_files_tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(new_index)))

        self.app.sim_files_tableWidget.setCurrentCell(
            row_index,
            0
        )
        self.updateInfo()

    def deleteSrcFile(self):
        self.src_file = None
        self.src_image = None
        self.sims_list = []
        self.app.sim_src_lineEdit.clear()
        self.app.sim_src_label.clear()
        self.app.sim_degree_label.clear()
        self.updateDegree()

    def updateInfo(self):
        index = self.app.sim_files_tableWidget.currentRow()
        if (index == -1 or self.app.sim_files_tableWidget.isRowHidden(index)):
            self.app.sim_files_tableWidget.clearSelection()
            return
        
        index = int(self.app.sim_files_tableWidget.item(index, 2).text())

        if (self.sims_list != []):
            self.app.sim_degree_label.setText(str(self.sims_list[index]))

        self.image = cv2.imread(self.files[index])
        update_pixmap(self.app.sim_image_label, self.image)

    def updateDegree(self):
        self.app.sim_files_tableWidget.setSortingEnabled(False)

        if (self.sims_list == []):
            for row in range(self.app.sim_files_tableWidget.rowCount()):
                self.app.sim_files_tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem('NaN'))
                self.app.sim_files_tableWidget.showRow(row)

            self.app.sim_files_tableWidget.setSortingEnabled(True)
        else:
            for row in range(self.app.sim_files_tableWidget.rowCount()):
                    item =  QtWidgets.QTableWidgetItem()
                    index = int(self.app.sim_files_tableWidget.item(row, 2).text())
                    item.setData(QtCore.Qt.ItemDataRole.DisplayRole, self.sims_list[index])
                    self.app.sim_files_tableWidget.setItem(row, 1, item)

            self.app.sim_files_tableWidget.setSortingEnabled(True)

            for row in range(self.app.sim_files_tableWidget.rowCount()):
                    item =  QtWidgets.QTableWidgetItem()
                    index = int(self.app.sim_files_tableWidget.item(row, 2).text())
                    if (type(self.sims_list[index]) != str and self.sims_list[index] < self.threshold):
                        self.app.sim_files_tableWidget.hideRow(row)
                    else:
                        self.app.sim_files_tableWidget.showRow(row)

    def thresholdUpdate(self):
        self.threshold = self.app.sim_degree_slider.value()
        self.app.sim_degree_lineEdit.setText(str(self.threshold))

        if (not self.slider_flag):
            self.updateDegree()

    def setup_model(self):
        self.logger.info('similarity model initializing...')

        self.app.sim_info_label.setText('Инициализация модели...\n')
        self.app.sim_cancel_button.setVisible(False)
        self.app.sim_progressBar.setVisible(False)
        self.app.stackedWidget_sim.setCurrentIndex(0)

        try:
            self.similarity = ImageSimilarity(config.__VIT_MODEL__)
        except Exception as ex:
            self.app.sim_info_label.setText('Не удалось инициализировать модель!\n'
                                            'Попробуйте перезапустить приложение')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Не удалось инициализировать модель для определения сходства! Попробуйте перезапустить приложение', 
                                  buttons=QtWidgets.QMessageBox.StandardButton.Close).exec()
            self.logger.exception(ex)
        else:
            self.app.stackedWidget_sim.setCurrentIndex(1)
            self.logger.info('similarity model initialized')

    def process_callback(self):
        if self.files == [] or self.src_file == None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Недостаточно данных для обработки!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return
        
        threading.Thread(target=self.process).start()

    def process(self):
        if self.similarity == None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 
                                  'Модель не инициализирована!', 
                                  buttons=QtWidgets.QMessageBox.StandardButton.Close).exec()
            return

        self.logger.info(f'processing...')

        self.app.sim_info_label.setText('Идёт вычисление степени сходства...')

        progress = 0
        self.app.sim_progressBar.setMaximum(len(self.files))
        self.app.sim_progressBar.setValue(progress)

        self.app.sim_cancel_button.setVisible(True)
        self.app.sim_progressBar.setVisible(True)
        self.app.stackedWidget_sim.setCurrentIndex(0)

        try:
            self.sims_list = ['NaN'] * len(self.files)

            for index in range(len(self.files)):
                if (self.cancel_flag):
                    break
                
                img = cv2.imread(self.files[index])
                sim = self.similarity.compute(self.src_image, img)
                self.sims_list[index] = round((sim + 1) / 2.0 * 100)

                progress += 1
                self.app.sim_progressBar.setValue(progress)
        except Exception as ex:
            self.app.sim_info_label.setText('Ошибка во время обработки изображений!')
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 
                                  'Ошибка во время определения сходства! Попробейте перезапустить приложение', 
                                  buttons=QtWidgets.QMessageBox.StandardButton.Close).exec()
            self.logger.exception(ex)
        else:
            self.cancel_flag = False
            self.logger.info(f'processing completed')

        self.updateInfo()
        self.updateDegree()
        self.app.stackedWidget_sim.setCurrentIndex(1)

    def cancel(self):
        self.cancel_flag = True
        # self.app.sim_info_label.setText('Остановка...')

    def save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(None,
                                                        'Выбрать файл',
                                                        './')
        if path == '':
            return 
        
        if self.sims_list == []:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Ошибка', 'Нет данных для сохранения!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            return

        self.logger.info('saving...')

        try:
            output_dict = {}
            output_dict['source_file'] = os.path.basename(self.src_file)
            output_dict['files'] = [{os.path.basename(self.files[i]): self.sims_list[i]} 
                                    for i in range(len(self.files)) if self.sims_list[i]>=self.threshold]

            with open(path, 'w', encoding='utf-8') as file:
                json.dump(output_dict, file, indent=2, ensure_ascii=False)
        except Exception as ex:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Critical, 'Ошибка', 'Не удалось сохранить файлы!', 
                                  QtWidgets.QMessageBox.StandardButton.Close).exec()
            self.logger.exception(ex)
        else:
            self.logger.info('json saved')