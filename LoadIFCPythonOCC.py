import sys
import os
import ifcopenshell
import ifcopenshell.geom
from OCC.Display.SimpleGui import init_display
from OCC.Core.Graphic3d import *
from OCC.Core.gp import gp_Vec, gp_Pnt
from OCC.Core.AIS import AIS_Shape
from OCC.Core.TopoDS import TopoDS_Iterator
from OCC.Core.TopAbs import TopAbs_ShapeEnum
from PyQt5.QtWidgets import (
    QTextEdit,
    QLabel,
    QApplication,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QGroupBox,
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QAction,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QMenuBar,
    QMenu,
    QTableWidgetItem,
    QTableWidget,
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QDir
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB, Quantity_NOC_BLACK
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QGroupBox, QDialog, QVBoxLayout, QCheckBox
from PyQt5.QtCore import Qt

from OCC.Display.backend import load_backend
load_backend("pyqt5")
import OCC.Display.qtDisplay as qtDisplay

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = "PyQt5 / pythonOCC / Ionut Bim Studio"
        self.left = 50
        self.top = 50
        self.width = 1800  # Increased width for more space for the display
        self.height = 1200
        self.grid_shapes = []
        self.initUI()
        self.log_text = QTextEdit()  # Inițializare QTextEdit pentru log

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setStyleSheet("""
            background-color: #1E1E1E;
            color: #D4D4D4;
            selection-background-color: #3E4455;
            selection-color: #D4D4D4;
        """)
        self.createMenuBar()
        self.createVerticalLayout()

        windowLayout = QHBoxLayout()
        windowLayout.addWidget(self.verticalGroupBox)
        windowLayout.addWidget(self.canvas)
        windowLayout.addWidget(self.rightVerticalGroupBox)

        windowLayout = QVBoxLayout()
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.verticalGroupBox)
        topLayout.addWidget(self.canvas)
        topLayout.addWidget(self.rightVerticalGroupBox)

        windowLayout.addLayout(topLayout)
        windowLayout.addWidget(self.bottomHorizontalGroupBox)

        centralWidget = QWidget()
        centralWidget.setLayout(windowLayout)
        self.setCentralWidget(centralWidget)

        # Setarea culorii pentru bara de titlu
        titleBar = self.findChild(QWidget, "qt_mac_large_toolbar")
        if titleBar:
            titleBar.setStyleSheet("background-color: #333333;")

        self.show()
        self.canvas.InitDriver()
        self.display = self.canvas._display

        self.shape_to_metadata_map = {}

    def createMenuBar(self):
        menubar = self.menuBar()

        fileMenu = menubar.addMenu('File')

        openAct = QAction('Open', self)
        openAct.setShortcut('Ctrl+O')
        openAct.triggered.connect(self.openFile)
        fileMenu.addAction(openAct)

        saveAct = QAction('Save', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAct)

        saveAsAct = QAction('Save As', self)
        saveAsAct.triggered.connect(self.saveFileAs)
        fileMenu.addAction(saveAsAct)

    def createVerticalLayout(self):
        self.verticalGroupBox = QGroupBox("Controls")
        self.verticalGroupBox.setFixedWidth(120)
        self.verticalGroupBox.setStyleSheet("background-color: #202020;")
        layout = QVBoxLayout()

        self.rightVerticalGroupBox = QGroupBox("Properties")
        self.rightVerticalGroupBox.setFixedWidth(300)
        self.rightVerticalGroupBox.setStyleSheet("""
            background-color: #1E1E1E;
            color: #D4D4D4;
            border: 1px solid #2E2E2E;
        """)
        rightLayout = QVBoxLayout()

        self.bottomPanel = QGroupBox("Bottom Panel")
        self.bottomPanel.setFixedHeight(200)
        self.bottomPanel.setStyleSheet(
            "background-color: #202020; border: none; padding: 5px;"
        )
        layout = QVBoxLayout()

        self.bottomPanel.setLayout(layout)

        erase_button = QPushButton("Unload ifc", self)
        erase_button.setStyleSheet(
            "background-color: #404040; color: orange; border: 1px solid #404040; padding: 5px;"
        )
        erase_button.clicked.connect(self.eraseIFC)
        layout.addWidget(erase_button)

        self.verticalGroupBox.setLayout(layout)
        self.rightVerticalGroupBox.setLayout(rightLayout)

        self.properties_table = QTableWidget()
        self.properties_table.setColumnCount(2)
        self.properties_table.setHorizontalHeaderLabels(["Name", "Value"])
        self.properties_table.horizontalHeader().setStretchLastSection(True)
        self.properties_table.setStyleSheet("""
            QTableWidget {
                background-color: #F0F0F0;
                color: #1E1E1E;
                border: 1px solid #2E2E2E;
            }
            QTableWidget QHeaderView {
                background-color: #F0F0F0;
                color: #1E1E1E;
                border: 1px solid #2E2E2E;
            }
            QTableWidget::item {
                padding: 5px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #3E4455;
            }
        """)
       
       
        self.bottomHorizontalGroupBox = QGroupBox("Bottom Panel")
        self.bottomHorizontalGroupBox.setFixedHeight(300)
        self.bottomHorizontalGroupBox.setStyleSheet("background-color: #202020;")
        bottomLayout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4;")
        bottomLayout.addWidget(self.log_text)

        self.bottomHorizontalGroupBox.setLayout(bottomLayout)


       
        rightLayout.addWidget(self.properties_table)

        self.canvas = qtDisplay.qtViewer3d(self)

    def get_attributes_and_properties_by_guid(self, ifc_file, guid):
        product = ifc_file.by_guid(guid)
        attributes = {attr: getattr(product, attr, None) for attr in dir(product) if not attr.startswith("_")}
        properties = {}
        if hasattr(product, "IsDefinedBy"):
            for rel in product.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    for prop in rel.RelatingPropertyDefinition.PropertySetDefinitions:
                        if hasattr(prop, "HasProperties"):
                            for p in prop.HasProperties:
                                properties[p.Name] = p.NominalValue.wrappedValue if hasattr(p.NominalValue, 'wrappedValue') else p.NominalValue
        attributes.update(properties)
        return attributes

    # Function to retrieve material properties of a product based on GlobalId
    def get_material_properties_by_guid(self, ifc_file, guid):
        product = ifc_file.by_guid(guid)
        material_properties = {}
        if hasattr(product, "HasAssociations"):
            for association in product.HasAssociations:
                if association.is_a("IfcRelAssociatesMaterial"):
                    material = association.RelatingMaterial
                    material_properties["Material"] = material.Name
        return material_properties

    def add_shape_to_map(self, shape, metadata):
        if shape.ShapeType() == TopAbs_ShapeEnum.TopAbs_COMPOUND:
            sub_shapes = TopoDS_Iterator(shape)
            while sub_shapes.More():
                sub_shape = sub_shapes.Value()
                self.shape_to_metadata_map[sub_shape] = metadata
                sub_shapes.Next()
        else:
            self.shape_to_metadata_map[shape] = metadata

    def displayIFC(self, fileName):
        self.ifc_file = ifcopenshell.open(fileName)
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_PYTHON_OPENCASCADE, True)

        for product in self.ifc_file.by_type("IfcProduct"):
            if product.Representation is not None:
                try:
                    shape = ifcopenshell.geom.create_shape(settings, inst=product)
                    r, g, b, a = shape.styles[0]
                    color = Quantity_Color(abs(r), abs(g), abs(b), Quantity_TOC_RGB)
                    self.display.DisplayShape(shape.geometry, color=color, transparency=0.15)
                    # Add GUID to our mapping
                    guid = product.GlobalId
                    self.add_shape_to_map(shape.geometry, guid)
                    print(f"Added {guid} to shape map")
                except RuntimeError:
                    print(f"Failed to process shape geometry for {product.GlobalId}")

        self.display.FitAll()
        self.register_select_callback()

    def on_select(self, selected_shapes, x, y):
        self.properties_table.setRowCount(0)
        for selected_shape in selected_shapes:
            if selected_shape.ShapeType() == TopAbs_ShapeEnum.TopAbs_COMPOUND:
                comp = selected_shape
                sub_shapes = TopoDS_Iterator(comp)
                while sub_shapes.More():
                    sub_shape = sub_shapes.Value()
                    guid = self.shape_to_metadata_map.get(sub_shape)
                    print(guid)
                    if guid:
                        metadata = self.get_attributes_and_properties_by_guid(self.ifc_file, guid)
                        material_properties = self.get_material_properties_by_guid(self.ifc_file, guid)
                        metadata.update(material_properties)
                        self.log_text.insertPlainText(f"Selected IFC Element: {metadata['Name']}")
                        self.log_text.insertPlainText(f"Properties: {metadata}")
                        self.update_metadata(metadata)
                    sub_shapes.Next()
            else:
                guid = self.shape_to_metadata_map.get(selected_shape)
                if guid:
                    metadata = self.get_attributes_and_properties_by_guid(self.ifc_file, guid)
                    material_properties = self.get_material_properties_by_guid(self.ifc_file, guid)
                    metadata.update(material_properties)
                    print(metadata)
                    self.log_text.appendPlainText(f"Selected IFC Element: {metadata['Name']}")
                    self.log_text.appendPlainText(f"Properties: {metadata}")
                    self.update_metadata(metadata)

    def register_select_callback(self):
        self.display.register_select_callback(self.on_select)

    def eraseIFC(self):
        self.display.EraseAll()

    def eventFilter(self, obj, event):
        if event.type() == Qt.MouseButtonPress:
            self.canvas.StartRotation(event.x(), event.y())
        elif event.type() == Qt.MouseMove:
            if event.buttons() == Qt.LeftButton:
                self.canvas.Rotation(event.x(), event.y())
        elif event.type() == Qt.KeyPress:
            if event.key() == Qt.Key_Left:
                self.display.View.Rotate(gp_Vec(-1, 0, 0))
            elif event.key() == Qt.Key_Right:
                self.display.View.Rotate(gp_Vec(1, 0, 0))
            elif event.key() == Qt.Key_Up:
                self.display.View.Rotate(gp_Vec(0, 1, 0))
            elif event.key() == Qt.Key_Down:
                self.display.View.Rotate(gp_Vec(0, -1, 0))
        return super().eventFilter(obj, event)

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def update_metadata(self, metadata):
        self.properties_table.setRowCount(len(metadata))
        for row, (key, value) in enumerate(metadata.items()):
            self.properties_table.setItem(row, 0, QTableWidgetItem(key))
            self.properties_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def clear_metadata(self):
        self.properties_table.setRowCount(0)

    def openFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open IFC File", QDir.homePath(), "IFC Files (*.ifc)", options=options)
        if fileName:
            self.displayIFC(fileName)
            print("this is my print", str(fileName))

    def saveFile(self):
        # Implement logic for saving the current state
        pass

    def saveFileAs(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save IFC File", QDir.homePath(), "IFC Files (*.ifc)", options=options)
        if fileName:
            # Implement logic for saving the current state as a new file
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()

    if os.getenv("APPVEYOR") is None:
        sys.exit(app.exec_())