# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\settings_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(548, 601)
        self.gridLayout_6 = QtWidgets.QGridLayout(Dialog)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.groupBox_4 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_4.setTitle("")
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label_4 = QtWidgets.QLabel(self.groupBox_4)
        self.label_4.setObjectName("label_4")
        self.gridLayout_2.addWidget(self.label_4, 0, 0, 1, 1)
        self.comboBox_attachment = QtWidgets.QComboBox(self.groupBox_4)
        self.comboBox_attachment.setObjectName("comboBox_attachment")
        self.comboBox_attachment.addItem("")
        self.comboBox_attachment.addItem("")
        self.gridLayout_2.addWidget(self.comboBox_attachment, 0, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(self.groupBox_4)
        self.label_8.setObjectName("label_8")
        self.gridLayout_2.addWidget(self.label_8, 0, 2, 1, 1)
        self.comboBox_size = QtWidgets.QComboBox(self.groupBox_4)
        self.comboBox_size.setObjectName("comboBox_size")
        self.comboBox_size.addItem("")
        self.comboBox_size.addItem("")
        self.gridLayout_2.addWidget(self.comboBox_size, 0, 3, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.groupBox_4)
        self.label_7.setObjectName("label_7")
        self.gridLayout_2.addWidget(self.label_7, 1, 0, 1, 1)
        self.comboBox_position = QtWidgets.QComboBox(self.groupBox_4)
        self.comboBox_position.setObjectName("comboBox_position")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.comboBox_position.addItem("")
        self.gridLayout_2.addWidget(self.comboBox_position, 1, 1, 1, 1)
        self.label_9 = QtWidgets.QLabel(self.groupBox_4)
        self.label_9.setObjectName("label_9")
        self.gridLayout_2.addWidget(self.label_9, 1, 2, 1, 1)
        self.scaleBox = QtWidgets.QDoubleSpinBox(self.groupBox_4)
        self.scaleBox.setDecimals(1)
        self.scaleBox.setMinimum(0.1)
        self.scaleBox.setSingleStep(0.1)
        self.scaleBox.setProperty("value", 1.0)
        self.scaleBox.setObjectName("scaleBox")
        self.gridLayout_2.addWidget(self.scaleBox, 1, 3, 1, 1)
        self.gridLayout_6.addWidget(self.groupBox_4, 3, 0, 1, 12)
        self.RestoreButton = QtWidgets.QPushButton(Dialog)
        self.RestoreButton.setObjectName("RestoreButton")
        self.gridLayout_6.addWidget(self.RestoreButton, 8, 8, 1, 3)
        self.pushButton_videoTutorial = QtWidgets.QPushButton(Dialog)
        self.pushButton_videoTutorial.setObjectName("pushButton_videoTutorial")
        self.gridLayout_6.addWidget(self.pushButton_videoTutorial, 8, 0, 1, 8)
        self.groupBox_3 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_5 = QtWidgets.QLabel(self.groupBox_3)
        self.label_5.setToolTip("")
        self.label_5.setToolTipDuration(-1)
        self.label_5.setStatusTip("")
        self.label_5.setWhatsThis("")
        self.label_5.setObjectName("label_5")
        self.gridLayout_3.addWidget(self.label_5, 0, 0, 1, 1)
        self.Slider_main = QtWidgets.QSlider(self.groupBox_3)
        self.Slider_main.setToolTip("")
        self.Slider_main.setToolTipDuration(-1)
        self.Slider_main.setWhatsThis("")
        self.Slider_main.setMaximum(100)
        self.Slider_main.setPageStep(1)
        self.Slider_main.setProperty("value", 100)
        self.Slider_main.setSliderPosition(100)
        self.Slider_main.setTracking(True)
        self.Slider_main.setOrientation(QtCore.Qt.Horizontal)
        self.Slider_main.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.Slider_main.setTickInterval(5)
        self.Slider_main.setObjectName("Slider_main")
        self.gridLayout_3.addWidget(self.Slider_main, 0, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.groupBox_3)
        self.label_6.setObjectName("label_6")
        self.gridLayout_3.addWidget(self.label_6, 1, 0, 1, 1)
        self.Slider_review = QtWidgets.QSlider(self.groupBox_3)
        self.Slider_review.setMaximum(100)
        self.Slider_review.setPageStep(10)
        self.Slider_review.setProperty("value", 1)
        self.Slider_review.setSliderPosition(1)
        self.Slider_review.setOrientation(QtCore.Qt.Horizontal)
        self.Slider_review.setInvertedAppearance(False)
        self.Slider_review.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.Slider_review.setObjectName("Slider_review")
        self.gridLayout_3.addWidget(self.Slider_review, 1, 1, 1, 1)
        self.gridLayout_6.addWidget(self.groupBox_3, 2, 8, 1, 4)
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setWhatsThis("")
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.toolButton_gear = QtWidgets.QToolButton(self.groupBox)
        self.toolButton_gear.setObjectName("toolButton_gear")
        self.gridLayout_5.addWidget(self.toolButton_gear, 1, 2, 1, 1)
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setToolTipDuration(10000)
        self.label.setObjectName("label")
        self.gridLayout_5.addWidget(self.label, 0, 0, 1, 1)
        self.pushButton_randomize = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_randomize.setObjectName("pushButton_randomize")
        self.gridLayout_5.addWidget(self.pushButton_randomize, 2, 1, 1, 1)
        self.pushButton_imageFolder = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_imageFolder.setObjectName("pushButton_imageFolder")
        self.gridLayout_5.addWidget(self.pushButton_imageFolder, 2, 0, 1, 1)
        self.lineEdit_background = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit_background.setObjectName("lineEdit_background")
        self.gridLayout_5.addWidget(self.lineEdit_background, 0, 1, 1, 1)
        self.lineEdit_gear = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit_gear.setObjectName("lineEdit_gear")
        self.gridLayout_5.addWidget(self.lineEdit_gear, 1, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setToolTipDuration(10000)
        self.label_2.setObjectName("label_2")
        self.gridLayout_5.addWidget(self.label_2, 1, 0, 1, 1)
        self.toolButton_background = QtWidgets.QToolButton(self.groupBox)
        self.toolButton_background.setObjectName("toolButton_background")
        self.gridLayout_5.addWidget(self.toolButton_background, 0, 2, 1, 1)
        self.gridLayout_6.addWidget(self.groupBox, 1, 0, 1, 12)
        self.groupBox_5 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout.setObjectName("gridLayout")
        self.label_11 = QtWidgets.QLabel(self.groupBox_5)
        self.label_11.setObjectName("label_11")
        self.gridLayout.addWidget(self.label_11, 0, 0, 1, 1)
        self.lineEdit_color_main = QtWidgets.QLineEdit(self.groupBox_5)
        self.lineEdit_color_main.setObjectName("lineEdit_color_main")
        self.gridLayout.addWidget(self.lineEdit_color_main, 0, 1, 1, 1)
        self.toolButton_color_main = QtWidgets.QToolButton(self.groupBox_5)
        self.toolButton_color_main.setObjectName("toolButton_color_main")
        self.gridLayout.addWidget(self.toolButton_color_main, 0, 2, 1, 1)
        self.label_12 = QtWidgets.QLabel(self.groupBox_5)
        self.label_12.setObjectName("label_12")
        self.gridLayout.addWidget(self.label_12, 0, 3, 1, 1)
        self.lineEdit_color_top = QtWidgets.QLineEdit(self.groupBox_5)
        self.lineEdit_color_top.setObjectName("lineEdit_color_top")
        self.gridLayout.addWidget(self.lineEdit_color_top, 0, 4, 1, 1)
        self.toolButton_color_top = QtWidgets.QToolButton(self.groupBox_5)
        self.toolButton_color_top.setObjectName("toolButton_color_top")
        self.gridLayout.addWidget(self.toolButton_color_top, 0, 5, 1, 1)
        self.label_13 = QtWidgets.QLabel(self.groupBox_5)
        self.label_13.setObjectName("label_13")
        self.gridLayout.addWidget(self.label_13, 1, 3, 1, 1)
        self.lineEdit_color_bottom = QtWidgets.QLineEdit(self.groupBox_5)
        self.lineEdit_color_bottom.setObjectName("lineEdit_color_bottom")
        self.gridLayout.addWidget(self.lineEdit_color_bottom, 1, 4, 1, 1)
        self.toolButton_color_bottom = QtWidgets.QToolButton(self.groupBox_5)
        self.toolButton_color_bottom.setObjectName("toolButton_color_bottom")
        self.gridLayout.addWidget(self.toolButton_color_bottom, 1, 5, 1, 1)
        self.gridLayout_6.addWidget(self.groupBox_5, 4, 0, 1, 12)
        spacerItem = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout_6.addItem(spacerItem, 7, 0, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_2.setTitle("")
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.checkBox_reviewer = QtWidgets.QCheckBox(self.groupBox_2)
        self.checkBox_reviewer.setToolTipDuration(10000)
        self.checkBox_reviewer.setChecked(True)
        self.checkBox_reviewer.setObjectName("checkBox_reviewer")
        self.gridLayout_4.addWidget(self.checkBox_reviewer, 0, 0, 1, 1)
        self.checkBox_toolbar = QtWidgets.QCheckBox(self.groupBox_2)
        self.checkBox_toolbar.setToolTipDuration(10000)
        self.checkBox_toolbar.setChecked(True)
        self.checkBox_toolbar.setObjectName("checkBox_toolbar")
        self.gridLayout_4.addWidget(self.checkBox_toolbar, 1, 0, 1, 1)
        self.checkBox_topbottom = QtWidgets.QCheckBox(self.groupBox_2)
        self.checkBox_topbottom.setToolTipDuration(10000)
        self.checkBox_topbottom.setChecked(True)
        self.checkBox_topbottom.setObjectName("checkBox_topbottom")
        self.gridLayout_4.addWidget(self.checkBox_topbottom, 2, 0, 1, 1)
        self.gridLayout_6.addWidget(self.groupBox_2, 2, 0, 1, 8)
        self.OkButton = QtWidgets.QPushButton(Dialog)
        self.OkButton.setObjectName("OkButton")
        self.gridLayout_6.addWidget(self.OkButton, 8, 11, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout_6.addItem(spacerItem1, 5, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.toolButton_course = QtWidgets.QToolButton(Dialog)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("CustomBackground:AnKingSmall.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.toolButton_course.setIcon(icon)
        self.toolButton_course.setIconSize(QtCore.QSize(40, 40))
        self.toolButton_course.setObjectName("toolButton_course")
        self.horizontalLayout.addWidget(self.toolButton_course)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setMinimumSize(QtCore.QSize(400, 0))
        self.label_3.setWordWrap(True)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.gridLayout_6.addLayout(self.horizontalLayout, 6, 0, 1, 12)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.toolButton_website = QtWidgets.QToolButton(Dialog)
        self.toolButton_website.setMaximumSize(QtCore.QSize(31, 31))
        self.toolButton_website.setIcon(icon)
        self.toolButton_website.setIconSize(QtCore.QSize(31, 31))
        self.toolButton_website.setObjectName("toolButton_website")
        self.horizontalLayout_2.addWidget(self.toolButton_website)
        self.toolButton_youtube = QtWidgets.QToolButton(Dialog)
        self.toolButton_youtube.setMaximumSize(QtCore.QSize(31, 31))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("CustomBackground:YouTube.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.toolButton_youtube.setIcon(icon1)
        self.toolButton_youtube.setIconSize(QtCore.QSize(31, 31))
        self.toolButton_youtube.setObjectName("toolButton_youtube")
        self.horizontalLayout_2.addWidget(self.toolButton_youtube)
        self.toolButton_patreon = QtWidgets.QToolButton(Dialog)
        self.toolButton_patreon.setMaximumSize(QtCore.QSize(171, 26))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("CustomBackground:Patreon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.toolButton_patreon.setIcon(icon2)
        self.toolButton_patreon.setIconSize(QtCore.QSize(200, 31))
        self.toolButton_patreon.setObjectName("toolButton_patreon")
        self.horizontalLayout_2.addWidget(self.toolButton_patreon, 0, QtCore.Qt.AlignHCenter)
        self.toolButton_instagram = QtWidgets.QToolButton(Dialog)
        self.toolButton_instagram.setMaximumSize(QtCore.QSize(31, 31))
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("CustomBackground:Instagram.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.toolButton_instagram.setIcon(icon3)
        self.toolButton_instagram.setIconSize(QtCore.QSize(31, 31))
        self.toolButton_instagram.setObjectName("toolButton_instagram")
        self.horizontalLayout_2.addWidget(self.toolButton_instagram)
        self.toolButton_facebook = QtWidgets.QToolButton(Dialog)
        self.toolButton_facebook.setMaximumSize(QtCore.QSize(31, 31))
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("CustomBackground:Facebook.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.toolButton_facebook.setIcon(icon4)
        self.toolButton_facebook.setIconSize(QtCore.QSize(31, 31))
        self.toolButton_facebook.setObjectName("toolButton_facebook")
        self.horizontalLayout_2.addWidget(self.toolButton_facebook)
        self.gridLayout_6.addLayout(self.horizontalLayout_2, 0, 2, 1, 9)
        self.groupBox_5.raise_()
        self.groupBox_4.raise_()
        self.groupBox_3.raise_()
        self.groupBox_2.raise_()
        self.groupBox.raise_()
        self.pushButton_videoTutorial.raise_()
        self.RestoreButton.raise_()
        self.OkButton.raise_()

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Custom Background Settings"))
        self.label_4.setText(_translate("Dialog", "Attachment:"))
        self.comboBox_attachment.setItemText(0, _translate("Dialog", "fixed"))
        self.comboBox_attachment.setItemText(1, _translate("Dialog", "scroll"))
        self.label_8.setText(_translate("Dialog", "Size:"))
        self.comboBox_size.setItemText(0, _translate("Dialog", "cover"))
        self.comboBox_size.setItemText(1, _translate("Dialog", "contain"))
        self.label_7.setText(_translate("Dialog", "Position:"))
        self.comboBox_position.setCurrentText(_translate("Dialog", "left top"))
        self.comboBox_position.setItemText(0, _translate("Dialog", "left top"))
        self.comboBox_position.setItemText(1, _translate("Dialog", "center top"))
        self.comboBox_position.setItemText(2, _translate("Dialog", "right top"))
        self.comboBox_position.setItemText(3, _translate("Dialog", "right"))
        self.comboBox_position.setItemText(4, _translate("Dialog", "left"))
        self.comboBox_position.setItemText(5, _translate("Dialog", "center"))
        self.comboBox_position.setItemText(6, _translate("Dialog", "left bottom"))
        self.comboBox_position.setItemText(7, _translate("Dialog", "center bottom"))
        self.comboBox_position.setItemText(8, _translate("Dialog", "right bottom"))
        self.label_9.setText(_translate("Dialog", "Scale:"))
        self.RestoreButton.setText(_translate("Dialog", "Restore Default"))
        self.pushButton_videoTutorial.setText(_translate("Dialog", "Video Tutorial"))
        self.groupBox_3.setTitle(_translate("Dialog", "Background opacity"))
        self.label_5.setText(_translate("Dialog", "Main"))
        self.label_6.setText(_translate("Dialog", "Review"))
        self.toolButton_gear.setText(_translate("Dialog", "..."))
        self.label.setToolTip(_translate("Dialog", "<html><head/><body><p>Name of the background image file.</p><p>&quot;Random&quot; will shuffle through defaults</p></body></html>"))
        self.label.setText(_translate("Dialog", "Image name for background:"))
        self.pushButton_randomize.setText(_translate("Dialog", "Random Images"))
        self.pushButton_imageFolder.setText(_translate("Dialog", "Open Image Folders"))
        self.label_2.setToolTip(_translate("Dialog", "<html><head/><body><p>Name of the file to replace the gear icon. </p><p>Anki default is gears.svg</p><p>&quot;Random&quot; will shuffle through defaults</p></body></html>"))
        self.label_2.setText(_translate("Dialog", "Image name for gear icon:"))
        self.toolButton_background.setText(_translate("Dialog", "..."))
        self.groupBox_5.setTitle(_translate("Dialog", "Background color"))
        self.label_11.setText(_translate("Dialog", "Main:"))
        self.toolButton_color_main.setText(_translate("Dialog", "..."))
        self.label_12.setText(_translate("Dialog", "Top toolbar:"))
        self.toolButton_color_top.setText(_translate("Dialog", "..."))
        self.label_13.setText(_translate("Dialog", "Bottom toolbar:"))
        self.toolButton_color_bottom.setText(_translate("Dialog", "..."))
        self.checkBox_reviewer.setToolTip(_translate("Dialog", "<html><head/><body><p>Show the background image in the reviewer screen</p></body></html>"))
        self.checkBox_reviewer.setText(_translate("Dialog", "Show in reviewer"))
        self.checkBox_toolbar.setToolTip(_translate("Dialog", "<html><head/><body><p>Show the background image in the top and bottom toolbars in addition to the main screen</p></body></html>"))
        self.checkBox_toolbar.setText(_translate("Dialog", "Show in toolbar"))
        self.checkBox_topbottom.setToolTip(_translate("Dialog", "<html><head/><body><p>Set the background position of the toolbars to top and bottom (if the main background position is set to center, this will look cleaner for most images)<br/></p></body></html>"))
        self.checkBox_topbottom.setText(_translate("Dialog", "Toolbar top/bottom"))
        self.OkButton.setText(_translate("Dialog", "OK"))
        self.toolButton_course.setText(_translate("Dialog", "..."))
        self.label_3.setText(_translate("Dialog", "Interested in learning how to use Anki effectively? Check out the Anki Mastery Course, a comprehensive series of lessons and video tutorials on Anki designed by the AnKing team."))
        self.toolButton_website.setText(_translate("Dialog", "..."))
        self.toolButton_youtube.setText(_translate("Dialog", "..."))
        self.toolButton_patreon.setText(_translate("Dialog", "..."))
        self.toolButton_instagram.setText(_translate("Dialog", "..."))
        self.toolButton_facebook.setText(_translate("Dialog", "..."))
