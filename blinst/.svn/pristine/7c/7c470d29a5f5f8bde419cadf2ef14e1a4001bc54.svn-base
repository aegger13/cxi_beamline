# IPMcalc class from xpp's lusiipm.py file
# At time of copy, this is not imported anywhere

import numpy as np

class IPMcalc:
  """ Class to calculate the IPM signal """
  def __init__(self, eBeam=2, XrayE=8.265, Npoints=1024):
    # #=== IPM Calculations ==================================================
    material=1 # 0 for Be, 1 for Si3N4
    #GDET:FEE1:241:ENRC (green line in striptool)
    self.beam_energy=eBeam # mJ
    self.X_ray_energy=XrayE # keV
    self.N=Npoints # number of points, 2^N power
    self.capacitances=np.array([0.001, 0.0047, 0.024, 0.120, 0.620, 3.3, 10]) # nF
    #L=30. # in mm
    self.L=74. # in mm
    Zt=10. # in mm target distance
    self.diosq=10. #diode measurement in mm
    NA=6.022e23 # Arvogado
    Me=511.003 # electrom mass in keV
    Lambda=(12.398/self.X_ray_energy)*1e-4 # wavelength in microns
    k=2.*np.pi/Lambda # k-vector in wavenumbers
    self.int_0=self.beam_energy*1e-3/(self.X_ray_energy*1e3*1.602e-19)# # number of photons
    hn_0=12.398/(Lambda*1e4)
    r0_2=(2.818e-13)**2 # in cm^-2
    alpha=(12.398/(Lambda*1e4))/Me
    
    Tvx = Tvy = np.arange(-self.N/2,self.N/2,1)
    [tvx,tvy]=np.meshgrid(Tvx,Tvy) # create 2-D array
    self.xL=self.L/self.N # increment in x and y in mm
    self.xv=tvx*self.xL # create 2-D array in space, in mm
    self.yv=tvy*self.xL 
    theta=180-np.arctan(np.sqrt(self.xv * self.xv+self.yv * self.yv)/Zt)*180/np.pi
    phi=np.arctan(self.yv/(self.xv+1e-10))*180/np.pi
    sin_2_Lambda=np.sin((theta/2)/180*np.pi)/(Lambda*1e4)
    
    if (material == 0):
      density=1.848 # g/cc for Be
      t=288*1e-4 # cm for Be
      A=9.012 # g/mole for Be
      form_squared=(0.3542*sin_2_Lambda*sin_2_Lambda - 2.0714*sin_2_Lambda + 2.3439)**2 # Be
      isf=-1.3518*sin_2_Lambda*sin_2_Lambda + 3.7614*sin_2_Lambda + 1.4612 # Be
    elif (material == 1):
      density=3.44 # g/cc for Si3N4
      t=4*1e-4 # cm for Si3N4 (1e-4 --> micron)
      A=140.28 # g/mole for Si3N4
      form_squared=(3.9814*sin_2_Lambda*sin_2_Lambda - 10.715*sin_2_Lambda + 8.6966)**2 # Si3N4
      isf=-51.584*sin_2_Lambda*sin_2_Lambda + 94.948*sin_2_Lambda + 10.023 # Si3N4 8.265 keV
    else:
      print 'unknown material!'
      return
    coh_para=r0_2*(1-(np.sin(theta/180*np.pi)**2)*(np.cos(phi/180*np.pi)**2))
    coh_norm=0
    coh=coh_para*form_squared
    hn=hn_0/(1+alpha*(1-np.cos(theta/180*np.pi)))
    incoh_para=0.25*r0_2*(hn**2/hn_0**2)*(hn_0/hn+hn/hn_0-2+4*(1-(np.sin(theta/180*np.pi)**2)*(np.cos(phi/180*np.pi)**2)))
    incoh_norm=0.25*r0_2*(hn**2/hn_0**2)*(hn_0/hn+hn/hn_0-2)
    incoh=(incoh_para+incoh_norm)*isf
    total=coh*0+incoh # coherent should not be included    
    r=np.sqrt(self.xv**2+self.yv**2+Zt**2)
    self.int=self.int_0*(total*np.cos(np.pi-theta/180*np.pi)*(self.L/self.N)**2)/r**2*density*t*NA/A
    self.int_total=sum(sum(self.int))
    #set defaults before calculation
    self.average_diode = -1
    average_energy=self.average_diode/self.int_0*self.beam_energy*1e6 # nJ
    average_charge=average_energy/3.6 # nC        
    self.average_vol=np.divide((average_charge*1000),self.capacitances) # in mV

  def calcDio(self, dioX=999., dioY=999.):
    self.dio_x=-5.
    self.dio_y=7
    if (dioX == 999.):
      dioX=self.dio_x
      if (dioY == 999.):
        dioY=self.dio_y
        # define detector geometry
    self.diode_geo_ar=np.ones((self.N,self.N))
    for i in range(1,self.N):
      xval=i*self.xL-self.L/2.
      if (xval < dioX) or (xval > (dioX+self.diosq)):
        self.diode_geo_ar[i,:]=0
      else:
        for j in range(1,self.N):
          yval=j*self.xL-self.L/2.
          if (yval < dioY) or (yval > (dioY+self.diosq)):
            self.diode_geo_ar[i,j]=0

    self.int_diode_geo=self.int*self.diode_geo_ar
    int_diode_geo_total=sum(sum(self.int_diode_geo))
    return int_diode_geo_total

  def calcIPMset(self, calcWhat="d"):
    signal = [0., 0., 0., 0.]
    ndiode=4
    if (calcWhat == "v"):
      signal[0] = self.calcDio(-17., -5.)
      signal[1] = self.calcDio(7., -5.)
      ndiode=2
    elif (calcWhat == "h"):
      signal[2] = self.calcDio(-5., 7.)
      signal[3] = self.calcDio(-5., -17.)
      ndiode=2
    elif (calcWhat == "c"):
      signal[0] = self.calcDio(-17., 7.)
      signal[1] = self.calcDio(7., 7.)
      signal[2] = self.calcDio(7., -17.)
      signal[3] = self.calcDio(-17., -17.)
    elif (calcWhat == "c"):
      signal[0] = self.calcDio(-25., 15.)
      signal[1] = self.calcDio(15., 15.)
      signal[2] = self.calcDio(15., -25.)
      signal[3] = self.calcDio(-25., -25.)
    else:
      signal[0] = self.calcDio(-17., -5.)
      signal[1] = self.calcDio(7., -5.)
      signal[2] = self.calcDio(-5., 7.)
      signal[3] = self.calcDio(-5., -17.)

    self.average_diode=(signal[0]+signal[1]+signal[2]+signal[3])/ndiode
    average_energy=self.average_diode/self.int_0*self.beam_energy*1e6 # nJ
    average_charge=average_energy/3.6 # nC        
    self.average_vol=np.divide((average_charge*1000),self.capacitances) # in mV
    # ADC voltage is reduced by another factor 1/e
    average_vole=np.divide(self.average_vol,np.e) # in mV
    return self.average_vol

  def printInfo(self, printRes=True):
    print 'N = ',self.N
    print 'number of photons int_0 = ', self.int_0
    print 'int_total = %g' %self.int_total
    if (printRes):
      print 'average_diode = %g' %(self.average_diode)
      print 'average_vol (ADC) in mV =  ', self.average_vol

