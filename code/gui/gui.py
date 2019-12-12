import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import qrspy
import os
import subprocess

root = tk.Tk()
root.geometry("500x800+300+300")

class App: 
    def __init__(self, root):
        
        #tk variables
        self.functionType = tk.IntVar()
        self.advanced = tk.IntVar()
        self.name_entry = tk.StringVar(value="PythonProphet")
        self.host_entry = tk.StringVar(value="localhost")
        self.port_entry = tk.StringVar(value="50066")
        self.certificate_entry = tk.StringVar(value="C:/ProgramData/Qlik/Sense/Repository/Exported Certificates/.Local Certificates/")
    
        # ui
        tk.Label(root, text="Qwik Forecast").grid(row=0, column=0)
        tk.Checkbutton(root, text='Advanced Settings', variable=self.advanced, command=self.checked).grid(row=1, column=0)
        self.install_button = tk.Button(root, text="Install Qwik Forecast", command=self.install)
        self.install_button.grid(row=2, column=0)  
    
    def checked(self):
        if self.advanced.get() == 1:
            self.name_label = tk.Label(root, text="Name")
            self.name_label.grid(row=3,column=0)
            self.name = tk.Entry(root, text="name", textvariable=self.name_entry, width=50)
            self.name.grid(row=4,column=0)
            self.host_label = tk.Label(root, text="Host")
            self.host_label.grid(row=5,column=0)
            self.host = tk.Entry(root, text="host", textvariable=self.host_entry, width=50)
            self.host.grid(row=6,column=0)
            self.port_label = tk.Label(root, text="Port")
            self.port_label.grid(row=7,column=0)
            self.port = tk.Entry(root, text="port", textvariable=self.port_entry, width=50)
            self.port.grid(row=8,column=0)
            self.certificates_label = tk.Label(root, text="Certificates Location")
            self.certificates_label.grid(row=9,column=0)
            self.certificates = tk.Entry(root, text="certificates", textvariable=self.certificate_entry, width=50)   
            self.certificates.grid(row=10,column=0)
            self.folder_button = tk.Button(root, text="...", command=self.get_folder)
            self.folder_button.grid(row=10,column=1)
            self.install_button.grid(row=11, column=0)                   
        else:
            self.name_label.destroy()
            self.name.destroy()
            self.host_label.destroy()
            self.host.destroy()
            self.port_label.destroy()
            self.port.destroy()
            self.certificates_label.destroy()
            self.certificates.destroy()
            self.folder_button.destroy()
            self.install_button.grid(row=2, column=0)
        return     
    
    def install(self):
        # set up console which reads out status
        console_row = 3
        if self.advanced == 1:
            console_row = 12
        if hasattr(self, 'console'):
            self.console.destroy()
        self.console = tk.Text(root)
        self.console.grid(row=console_row, column=0)

        # install as windows service
        try:
            self.console.insert("end", 'Installing analytic connection as a windows service...\n')    
            batch = "install.bat {0} {1}"
            install_directory = os.getcwd().split('gui')[0] + 'dist\__main__.exe' 
            subprocess.call(["..\\install.bat", self.name_entry.get(), install_directory], shell=False)           
            #os.system(batch.format(self.name_entry.get(), install_directory))
            self.console.insert("end", 'The analytic connection has now been installed as a windows service!\n')

        except Exception as e:
            print(e)
            self.console.insert("end", 'Looks like there was an error installing the analytic connection as a windows service!\n')  

        try:
            qrs = qrspy.ConnectQlik(server = self.host_entry.get() + ':' + str(4242), 
                        certificate = (self.certificate_entry.get() + 'client.pem', self.certificate_entry.get() + 'client_key.pem'))
            qrs.get_health()
        except Exception:    
            self.console.insert("end", 'It looks like we could not find your Qlik certificates! Please check the certificates folder location within the advanced settings!\n')
        
        # add analytic connection in qlik sense
        self.console.insert("end", 'Installing analytic connection in Qlik Sense...\n')    
        connections = qrs.get_analytic_connection()
        installed = False
        for connection in connections:
            if connection['name'] == self.name_entry.get():
                installed = True
                break
        if installed:
            self.console.insert("end", 'Analytic connection is already installed in Qlik Sense!\n')
        else:
            qrs.new_analytic_connection(self.name_entry.get(), self.host_entry.get(), self.port_entry.get())
            self.console.insert("end", 'Analytic connection successfully installed in Qlik Sense!\n')

    def get_folder(self):
        folder = filedialog.askdirectory(initialdir=self.certificate_entry.get(),title="Open Folder")
        if len(folder) >= 1:
            self.certificate_entry.set(folder)                  
if __name__=='__main__':
   App(root)
   tk.mainloop()