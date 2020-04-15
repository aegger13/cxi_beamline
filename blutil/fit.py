import minuit2
import numpy as np
from peakanalysis import PeakAnalysis
from scipy.special import erf
from pylab import *

sqrt2  = np.sqrt(2)
sqrtpi = np.sqrt(np.pi)
datax  = np.ones(1)
datay  = np.ones(1)
datae  = np.ones(1)

def oversample(v,fac):
  vo = linspace(min(v),max(v),v.shape[0]*fac)
  return vo

def gaussnorm(x,x0,sigma):
  return 1/sqrt2/sqrtpi/sigma*np.exp( -(x-x0)**2/2./sigma**2 )

def gauss(x,x0,sigma):
  return np.exp( -(x-x0)**2/2./sigma**2 )

def myexp(x,t0,tau):
  v=np.empty_like(x)
  f1=(x>t0)
  v[f1]=(1-np.exp(-(x[f1]-t0)/tau))
  f2=(x<=t0)
  v[f2] = 0
  return v

def conv_gauss_and_const(x,sig):
  return 0.5*(1-erf(-x/sqrt2/sig))

def conv_gauss_and_exp(x,sig,tau):
  return 0.5*exp(-(2*tau*x-sig**2)/2/tau**2)*(1-erf( (-tau*x+sig**2)/sqrt2/tau/sig))

def chi2gauss(a,x0,sigma,c):
  fit  = a*gauss(datax,x0,sigma)+c
  chi2 = (datay-fit)/datae
  return np.sum(chi2*chi2)
  
def fitgauss(x,y,e,a_init=None,x0_init=None,sigma_init=None,c_init=None):
  n_bkg = 3
  g = globals()
  g["datax"] = x; g["datay"] = y; g["datae"] = e
  try:
    (x0_guess,fwhm_guess,peak_guess) = PeakAnalysis(x,y,nb=n_bkg)
  except:
    x0_guess=fwhm_guess=peak_guess=None
  if (x0_init is None):    x0_init=x0_guess
  if (sigma_init is None): sigma_init=fwhm_guess/2.35
  if (c_init is None):     c_init = ( y[0:n_bkg].mean()+y[-1-n_bkg:-1].mean() ) /2.
  if (a_init is None):     a_init= (y-c_init).max()
  print x0_init,sigma_init,c_init,a_init
  m = minuit2.Minuit2(chi2gauss,a=a_init,x0=x0_init,sigma=sigma_init,c=c_init)
  m.printMode=1
  m.migrad()
  fit_par = m.values
  fit_err = m.errors
  fit = fit_par["a"]*gauss(x,fit_par["x0"],fit_par["sigma"])+fit_par["c"]
  return (fit_par,fit_err,x,fit)

class DaqFit(object):
  def __init__(self,daq_obj):
    self.daq=daq_obj

  def fitgauss(self,det=0,a_init=None,x0_init=None,sigma_init=None,c_init=None):
    if (type(det) == int):
      det = self.daq._Daq__y.keys()[det]
    x = np.array(self.daq._Daq__x)
    y = np.array(self.daq._Daq__y[det])
    e = np.array(self.daq._Daq__e[det])
    a = fitgauss(x,y,e,a_init=a_init,x0_init=x0_init,sigma_init=sigma_init,c_init=c_init)
    self.fitcurve = a[3]
    self.fit_par =  a[0]
    self.fit_err =  a[1]
    self.x = x
    self.y = y
    self.e = e
    self.drawfit()
    return a
  def drawfit(self,figName='DAQ fit'):
    fh_main = figure(1)
    fh = figure(2)
    clf()
    fh.canvas.set_window_title(figName)
    #subplot(1,2,1)
    lhd = errorbar(self.x,self.y,self.e,fmt='-ok')
    lhf = plot(self.x,self.fitcurve,'r')
    draw()
    legstr = ''
    elegstr = ''
    for i in self.fit_par.keys():
      legstr += i
      legstr = legstr + '=%e; '%(self.fit_par[i]) 
      elegstr += ('Err_' + i)
      elegstr = elegstr + '=%e; '%(self.fit_err[i]) 
    #legstr = 'teststring \nfor the fit'
    #print legstr
    #legend([lhd,lhf],['Data',legstr[:-1]],bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    title(legstr[:-2]+'\n'+elegstr[:-2])
    xlabel(fh_main.axes[0].get_xlabel())
    ylabel(fh_main.axes[0].get_ylabel())
    draw()  
