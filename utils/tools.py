from PyQt6 import QtWidgets, QtCore, QtGui
from numpy import ndarray

def update_pixmap(label: QtWidgets.QLabel, image):
        if (type(image) != ndarray):
            return

        qt_image = QtGui.QImage(image,
                              image.shape[1],
                              image.shape[0],
                              image.strides[0],
                              QtGui.QImage.Format.Format_BGR888)
        pixmap = QtGui.QPixmap.fromImage(qt_image).scaled(
            label.width()-1,
            label.height()-1,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        ) 
        label.setPixmap(pixmap)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)