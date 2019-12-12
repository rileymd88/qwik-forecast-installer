import qrspy

host = 'localhost'
port = 4242
certPath = 'C:/ProgramData/Qlik/Sense/Repository/Exported Certificates/.Local Certificates/'
qrs = qrspy.ConnectQlik(server = host + ':' + str(port), 
                        certificate = (certPath + 'client.pem', certPath + 'client_key.pem'))
print(qrs)                        