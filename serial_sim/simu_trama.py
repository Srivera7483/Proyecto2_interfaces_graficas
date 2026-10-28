import serial as rs, time as ti, random as RA

def Make_Data(nId):
    nEMA = nId # Identificador de la UMA
    nMP01 = RA.randint(5, 100) # Material Particulado 1.0 um
    nMP25 = RA.randint(5, 100) # Material Particulado 2.5 um
    nMP10 = RA.randint(5, 100) # Material Particulado 10 um
    nH103 = RA.randint(10, 10000) # Histograma MP 0.3 um
    nH105 = RA.randint(10, 10000) # Histograma MP 0.5 um
    nH101 = RA.randint(10, 10000) # Histograma MP 1.0 um
    nH125 = RA.randint(10, 10000) # Histograma MP 2.5 um
    nH150 = RA.randint(10, 10000) # Histograma MP 5.0 um
    nH110 = RA.randint(10, 10000) # Histograma MP 10 um
    nTE = RA.randint(5, 30) # Temperatura Celcius
    nHR = RA.randint(20, 70) # Humedad Relativa Aire

    sLine = str(nEMA) + ',' + str(nMP01) + ',' + str(nMP25) + ',' + str(nMP10) + ',' + \
            str(nH103) + ',' + str(nH105) + ',' + str(nH101) + ',' + \
            str(nH125) + ',' + str(nH150) + ',' + str(nH110) + ',' + \
            str(nTE) + ',' + str(nHR) + '\n'
    return sLine

# Configuración del puerto serial
MyCnx = rs.Serial('COM1') 
MyCnx.baudrate = 9600
nId = 1

while True:
    sAux = Make_Data(nId)
    print(sAux)
    # Se codifica a bytes mediante .encode() para PySerial
    MyCnx.write(sAux.encode()) 
    ti.sleep(0.1)
    nId += 1
    if nId == 6: 
        nId = 1
        