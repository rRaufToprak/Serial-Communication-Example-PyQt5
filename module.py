from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
import serial.tools.list_ports
from design import Ui_MainWindow

class SerialThread(QThread):
    data_received = pyqtSignal(str)

    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = True

    def run(self):
        try:
            # Seri portu belirtilen parametrelerle açmaya çalışır. Başarısız olursa bir istisna yakalar.
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException:
            # Eğer seri port açılamazsa, "Could not open serial port" mesajını sinyal olarak gönderir ve self.running bayrağını False yaparak iş parçacığını sonlandırır.
            self.data_received.emit("Could not open serial port")
            self.running = False
            return
      
        while self.running:
            #Seri porttan gelen veri olup olmadığını kontrol eder.
            if self.serial.in_waiting > 0:
                # Seri porttan bir satır veri okur ve UTF-8 olarak decode eder, ardından sağdaki boşlukları kaldırır.
                data = self.serial.readline().decode('utf-8').rstrip()
                # Alınan veriyi data_received sinyali aracılığıyla iletir.
                self.data_received.emit(data)

    def stop(self):
        #  İş parçacığının çalışmasını durdurur.
        self.running = False
        #  Eğer self.serial tanımlıysa (seri port açıksa) Seri portu kapatır.
        if self.serial:
            self.serial.close()

    #  Seri porta veri yazmak için kullanılır.
    def write_data(self, data):
        if self.serial:
            self.serial.write(data)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.populate_ports()

        self.serial_thread = None
        self.serial_connected = False
        self.ui.clearButton.clicked.connect(self.clear_coming_text)
        self.ui.connectButton.clicked.connect(self.connect_serial)
        self.ui.sendMsgButton.clicked.connect(self.send_string_data)
        
    def populate_ports(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.ui.portComboBox.addItem(port.device)

        if not ports:
            self.ui.portComboBox.addItem("No serial ports found")
            self.ui.portComboBox.setEnabled(False)

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def connect_serial(self):
        if self.serial_connected == False:
            # selected_port değişkenine, QComboBox'dan seçilen port atanır
            selected_port = self.ui.portComboBox.currentText()
            # Eğer QComboBox'da "No serial ports found" seçiliyse, bir hata mesajı gösterilir ve fonksiyon sonlanır. 
            # Bu, sistemde herhangi bir seri port bulunmadığını belirtir.
            if selected_port == "No serial ports found":
                QMessageBox.critical(self, "Error", "No serial ports available.")
                return
            # Eğer self.serial_thread zaten var ve çalışıyorsa (yani bir seri port bağlantısı açıksa), 
            # bu bağlantıyı durdurur (stop()) ve tamamen sonlanmasını bekler (wait()).
            if self.serial_thread:
                self.serial_thread.stop()
                self.serial_thread.wait()
            #selected_port ile yeni bir SerialThread nesnesi oluşturulur ve self.serial_thread değişkenine atanır.
            self.serial_thread = SerialThread(selected_port)
            self.ui.connectButton.setText("Disconnect")
            self.serial_connected = True
            #SerialThread içindeki data_received sinyali, update_text_edit metoduna bağlanır. 
            #Bu, seri porttan veri alındığında bu metodun çağrılmasını sağlar.
            self.serial_thread.data_received.connect(self.update_text_edit)
            # Yeni SerialThread iş parçacığı başlatılır (start()) ve seçilen seri porttan veri okumaya başlar.
            self.serial_thread.start()
        else:
            self.serial_connected = False
            self.serial_thread.disconnect()
            self.serial_thread.stop()
            self.ui.connectButton.setText("Connect")
            self.ui.rxTextEdit.append("Disconnected")
    # Bu metod, data_received sinyali tarafından çağrılır ve seri porttan alınan veriyi QTextEdit bileşenine ekler.
    def update_text_edit(self, data):
        # QTextEdit bileşenine (rxTextEdit) alınan veriyi ekler. Bu, verinin kullanıcı arayüzünde görünmesini sağlar.
        self.ui.rxTextEdit.append(data)

    def clear_coming_text(self):
        self.ui.rxTextEdit.clear()

    def send_string_data(self):
        string_data = self.ui.commandLineEdit.text().strip()
        try:
            if self.serial_thread:
                self.serial_thread.write_data(string_data.encode())
            
        except Exception as e:
            return f"Failed to send data: {str(e)}"

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()


