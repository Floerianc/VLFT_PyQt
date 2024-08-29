import sys 
import requests
import os
import re
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal
from ui import *

class uFile(QThread):
    '''
    A Class that acts as a userFile so basically the file the user wants to upload!
    '''
    def __init__(self) -> None:
        super().__init__()
        self.path: str
        self.name: str
        self.size: str
        self.readableSize: str
    
    def formatSize(self, size: int):
        '''
        I have no idea how this works but it works so idfc
        UPDATE 29.08.24: I understand how it works now
        '''
        for unit in ['', 'K', 'M', 'G', 'T']:
            if size < 1024:
                break
            size /= 1024
        return f'{size:.2f} {unit}B'

    def prepareFile(self):
        '''
        It splits the path with every / it finds.
        So for example if the path is:
        "C:/Windows/System32/file.exe"
        it would be split up into
        ['C:', 'Windows', 'System32', 'file.exe]
        the [-1] takes the last index of that list, 
        in this case it would be "file.exe".

        This name will later be used as the filename

        The size is the amount of bytes stored in that file
        and readableSize is basically a formatted size in Kb, Mb, Gb etc...
        '''
        self.name = self.path.split('/')[-1]
        self.size = os.path.getsize(self.path)
        self.readableSize = self.formatSize(self.size)


class WorkerThread(QThread):
    '''
    This Workerthread is supposed to control the upload and the progress bar,
    if it doesn't have its own thread everything will fucking crash.

    pyqtSignal sends a signal to another thread so we can update the
    progress bar with one thread and the progress label with another 
    thread, the main GUI thread.
    '''
    textChanged = pyqtSignal(str)

    def __init__(self, _path, name, size, readableSize):
        '''
        I hate this
        '''
        super().__init__()
        self.path = _path
        self.name = name
        self.size = size
        self.readableSize = readableSize
    
    def run(self):
        '''
        This sends a POST Request to the file.io server, I have no
        fucking idea why I have to use a Multipart request but whatever
        with every package that is being sent it calls the 
        self.displayProgress function as a callback.

        If the request is valid and returns a 200 as the status code we
        add the link to the file to the QListWidget. But we also change
        the UploadLabel text to "Finished Uploading" and reset the 
        progress bar to 0%
        '''
        with open(self.path, "rb") as f:
            mpe = MultipartEncoder({'field0': (self.name, f, "text/plain")})
            m = MultipartEncoderMonitor(mpe, self.displayProgress)
            r = requests.post(f'https://file.io/', data=m, headers={'Content-Type': m.content_type})
        
        if r.status_code == 200:
            ui.listWidget.addItem(f"{r.json()['link']} ({userFile.name})")
            ui.uploadLabel.setText("Finished Uploading!")
            ui.progressBarLabel.setGeometry(QtCore.QRect(0, 0, 0, 41))
        else:
            print("File couldn't be uploaded.")
    
    def displayProgress(self, monitor):
        '''
        This fucking sucks

        301 is the amount of pixels the progress bar needs in the width
        to fill the entire rectangular frame :D
        
        So the current length of the progress bar is the full length
        of the progress bar times the percentage of how much has been
        uploaded so far. However, if we update the progress bar AND the
        uploadLabel at the same time the program will crash.

        Therefore, we emit a signal to another thread which will handle
        the label to update with each package sent.
        '''
        maxLengthPx = 301 # Max size of progress bar
        currentLength = (maxLengthPx * monitor.bytes_read / userFile.size)
        ui.progressBarLabel.setGeometry(0, 0, round(currentLength), 41)
        self.textChanged.emit(f"{monitor.bytes_read / userFile.size * 100:.2f}% Completed")


class Application(Ui_MainWindow):
    def __init__(self, form) -> None:
        '''
        This initializes the program, it connects the buttons to specific
        functions etc...
        '''
        super().__init__()
        self.setupUi(form)

        self.fileButton.clicked.connect(self.browseFile)
        self.uploadButton.clicked.connect(self.uploadFile)
        self.listWidget.clicked.connect(self.copyLink)
        self.clearButton.clicked.connect(self.clearItems)
    
    def browseFile(self):
        filename = QFileDialog.getOpenFileName(None, "Open File", "", "All Files (*)")
        userFile.path = filename[0]
        userFile.prepareFile()
    
    def uploadFile(self):
        '''
        This uploadWorker is basically a thread which is supposed to 
        control the uploading section of this script. 
        '''
        try:
            self.uploadWorker = WorkerThread(userFile.path, userFile.name, userFile.size, userFile.readableSize)
            self.uploadWorker.textChanged.connect(self.updateProgressLabel)
            self.uploadWorker.start() 
        except:
            return
    
    def copyLink(self):
        item = self.listWidget.currentItem()
        itemText = item.text().strip()
        url = itemText.split(' ')
        os.system(f"echo {url[0]} | clip")
    
    def clearItems(self):
        self.listWidget.clear()
    
    def updateProgressLabel(self, text):
        self.uploadLabel.setText(text)


if __name__ == "__main__":
    '''
    All this initializes the window which we'll see.
    Basically how this works is that we have one thread for the 
    main GUI and one thread for the uploading
    '''
    userFile = uFile()

    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QMainWindow()
    ui = Application(Form)
    Form.show()
    app.exec()
