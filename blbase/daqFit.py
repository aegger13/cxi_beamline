import minuit2
import numpy as np
from blutil.peakanalysis import PeakAnalysis
from scipy.special import erf
from pylab import *
import scipy.optimize as opt
import inspect
from kulletools import nfigure

sqrt2  = np.sqrt(2)
sqrtpi = np.sqrt(np.pi)
datax  = np.ones(1)
datay  = np.ones(1)
datae  = np.ones(1)

def oversample(v,fac):
  vo = linspace(min(v),max(v),v.shape[0]*fac)
  return vo
def evalfunc(func,x,par):
  evstr = 'func(x,'
  for n in range(len(par)):
    evstr += 'par[%s],'%n
  evstr = evstr[:-1]
  evstr += ')'
  return eval(evstr)


#### FITTING FUNCTIONS #####

def gauss(x,Amp,x0,sig):
  return Amp*np.exp(-(x-x0)**2/sig)

def gaussgrad(x,Amp,x0,sig,grad,y0):
  return Amp*np.exp(-(x-x0)**2/2/sig**2) + grad*x + y0

def gaussgrad_findPars(x,y):
    CEN,FWHM,PEAK = PeakAnalysis(x,y,nb=3)
    return 1,CEN,FWHM/2.35,0,np.mean(y)

def step(x,Amp,x0,sig,y0):
  y = Amp*(erf((x-x0)/ np.sqrt(2) /sig) + 1)/2 + y0;
  return y

def step_findPars(x,y):
    CEN,FWHM,PEAK = PeakAnalysis(x,y,nb=3)
    return 1,CEN,FWHM/2.35,np.mean(y)

functions = [('gauss',gaussgrad,gaussgrad_findPars),('step',step,step_findPars)]




#def gaussnorm(x,x0,sigma):
  #return 1/sqrt2/sqrtpi/sigma*np.exp( -(x-x0)**2/2./sigma**2 )

#def gauss(x,x0,sigma):
  #return np.exp( -(x-x0)**2/2./sigma**2 )

#def myexp(x,t0,tau):
  #v=np.empty_like(x)
  #f1=(x>t0)
  #v[f1]=(1-np.exp(-(x[f1]-t0)/tau))
  #f2=(x<=t0)
  #v[f2] = 0
  #return v

#def conv_gauss_and_const(x,sig):
  #return 0.5*(1-erf(-x/sqrt2/sig))

#def conv_gauss_and_exp(x,sig,tau):
  #return 0.5*exp(-(2*tau*x-sig**2)/2/tau**2)*(1-erf( (-tau*x+sig**2)/sqrt2/tau/sig))

#def chi2gauss(a,x0,sigma,c):
  #fit  = a*gauss(datax,x0,sigma)+c
  #chi2 = (datay-fit)/datae
  #return np.sum(chi2*chi2)
  
#def fitgauss(x,y,e,a_init=None,x0_init=None,sigma_init=None,c_init=None):
  #n_bkg = 3
  #g = globals()
  #g["datax"] = x; g["datay"] = y; g["datae"] = e
  #try:
    #(x0_guess,fwhm_guess,peak_guess)= PeakAnalysis(x,y,nb=n_bkg)
  #except:
    #x0_guess=fwhm_guess=peak_guess=None
  #if (x0_init is None):    x0_init=x0_guess
  #if (sigma_init is None): sigma_init=fwhm_guess/2.35
  #if (c_init is None):     c_init = ( y[0:n_bkg].mean()+y[-1-n_bkg:-1].mean() ) /2.
  #if (a_init is None):     a_init= (y-c_init).max()
  #print x0_init,sigma_init,c_init,a_init
  #m = minuit2.Minuit2(chi2gauss,a=a_init,x0=x0_init,sigma=sigma_init,c=c_init)
  #m.printMode=1
  #m.migrad()
  #fit_par = m.values
  #fit_err = m.errors
  #fit = fit_par["a"]*gauss(x,fit_par["x0"],fit_par["sigma"])+fit_par["c"]
  #return (fit_par,fit_err,x,fit)

class Fit(object):
  def __init__(self,daq_obj,functions):
    self._daq = daq_obj
    self._functions = functions
    self._mask = []
    for function in functions:
      if len(function)==2:
        self.__dict__[function[0]] = funcFit(self._daq,function[1],self._mask,name=function[0])
      elif len(function)==3:
        self.__dict__[function[0]] = funcFit(self._daq,function[1],self._mask,name=function[0],p0func=function[2])




class funcFit(object):
  def __init__(self,daq_obj,func,mask,name='NoName',p0func=None):
    self.daq=daq_obj
    self.func = func
    self.p0func = p0func
    self.mask = mask
    self.name = name

  def __repr__(self):
    self.do_fit(None)
    popt = self.popt
    pcov = self.pcov
    names = inspect.getargspec(self.func)[0][1:]
    resstring =  '%s fit results\n' %self.name
    if popt is not inf:
      for name,n in zip(names,range(len(names))):
        resstring += '    ' + name + ' = %g'%popt[n] + ' '+'+-'+'%g'%np.sqrt(pcov[n,n]) + '\n'
    else: 
      for name,n in zip(names,range(len(names))):
        resstring += '    ' + name + ' = %g'%popt[n]+'\n'
    return resstring

  def getMaskFilter(self,x,mask=None):
    if mask==None:
      mask = self.mask
    if not mask:
      return
    filter = np.ones(np.shape(x))
    for m in mask:
      if m[0]=='inside':
        filter[np.min(m[1])<x<np.max(m[1])] = 0
      elif m[0]=='outside':
        filter[np.min(m[1])>x] = 0
        filter[np.max(m[1])<x] = 0
    return filter
        
  def do_fit(self,p0):
    x = np.array(self.daq._Daq__x).ravel()
    y = self.daq._Daq__y
    e = self.daq._Daq__e
    
    key = y.keys()[0]
    y = np.array(y[key]).ravel()
    e = np.array(e[key]).ravel()

    filter = self.getMaskFilter(x)
    filter = np.ones(np.shape(x),dtype=bool)
    
    x = x[filter]
    y = y[filter]
    e = e[filter]

    if self.p0func is not None:
      p0 = self.p0func(x,y)
    
    popt,pcov = self.curvefit(x,y,e,p0)
    self.popt = popt
    self.pcov = pcov
    self.plotfit()

  def plotfit(self):
    x = self.daq._Daq__x
    y = self.daq._Daq__y
    e = self.daq._Daq__e

    key = y.keys()[0]
    y = y[key]
    e = e[key]
    x = x.ravel()
    y = y.ravel()
    e = e.ravel()

    filter = self.getMaskFilter(x)
    filter = np.ones(np.shape(x),dtype=bool)

    xg = x[filter]
    yg = y[filter]
    eg = e[filter]
    xb = x[filter]
    yb = y[filter]
    eb = e[filter]

    xfit = oversample(x,10)
    
    yfit = evalfunc(self.func,xfit,self.popt)

    nfigure('DAQ fit')
    clf()
    #errorbar(xg,yg,yerr=eg,fmt='ko')
    #errorbar(xb,yb,yerr=eb,fmt='xr',color=(.8,.8,.8))
    plot(xg,yg,'k.')
    plot(xfit,yfit,'r')

  def curvefit(self,x=None,y=None,e=None,p0=None):
    x = x.ravel()
    y = y.ravel()
    e = e.ravel()
    #popt,pcov = opt.curve_fit(self.func,x,y,p0=p0,sigma=e)
    popt,pcov = opt.curve_fit(self.func,x,y,p0=p0)
    return popt,pcov

  #def fitgauss(self,det=0,a_init=None,x0_init=None,sigma_init=None,c_init=None):
    #if (type(det) == int):
      #det = self.daq._Daq__y.keys()[det]
    #x = np.array(self.daq._Daq__x)
    #y = np.array(self.daq._Daq__y[det])
    #e = np.array(self.daq._Daq__e[det])
    #a = fitgauss(x,y,e,a_init=a_init,x0_init=x0_init,sigma_init=sigma_init,c_init=c_init)
    #self.fitcurve = a[3]
    #self.fit_par =  a[0]
    #self.fit_err =  a[1]
    #self.x = x
    #self.y = y
    #self.e = e
    #self.drawfit()
    #return a
  #def drawfit(self,figName='DAQ fit'):
    #fh_main = figure(1)
    #fh = figure(2)
    #clf()
    #fh.canvas.set_window_title(figName)
    ##subplot(1,2,1)
    #lhd = errorbar(self.x,self.y,self.e,fmt='-ok')
    #lhf = plot(self.x,self.fitcurve,'r')
    #draw()
    #legstr = ''
    #elegstr = ''
    #for i in self.fit_par.keys():
      #legstr += i
      #legstr = legstr + '=%e; '%(self.fit_par[i]) 
      #elegstr += ('Err_' + i)
      #elegstr = elegstr + '=%e; '%(self.fit_err[i]) 
    ##legstr = 'teststring \nfor the fit'
    ##print legstr
    ##legend([lhd,lhf],['Data',legstr[:-1]],bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    #title(legstr[:-2]+'\n'+elegstr[:-2])
    #xlabel(fh_main.axes[0].get_xlabel())
    #ylabel(fh_main.axes[0].get_ylabel())
    #draw()




    
