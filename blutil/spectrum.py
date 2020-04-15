from blutil.plot import Plot2D
import struct
import numpy as np
import os


class SpectrumFile:
  def __init__(self,nspec=1000,onlyvis=False):
    self.plot=None
    self.doplot=True
    self.__nspec=nspec
    self.__ddark = np.zeros([3840])
    self.__specs = np.zeros([self.__nspec,3840])
    self.__minpix = 0
    self.__maxpix = 3839
    if (onlyvis):
      self.__minpix = 21
      self.__maxpix = 3830
    self.__havespecs = False

  def setdark(self, darkfile=None, av_start=0, n_av=1e6):
    """ no inpur filename -> dark spectrum = equal flat 0 (again)"""
    if (filename is None):
      self._ddark =  np.zeros([3840])
    else:
      darksum =  np.zeros([3840])
      ndark = 0
      fin.open(darkfile,"rb")
      while (fin):
        for i in range(0,3839):
          spec_val = struct.unpack('h',fin.read(2))[0]
          if av_start <= ndark < (av_start+n_av):
              darksum[i] = darksum[i] + specval
        ndark = ndark+1
      for i in range(0,3839):
        self._ddark[i] = darksum[i]/min(ndark-av_start)
      fin.close()
      
  def getspecs(self, infile=None, nspec=None):
    if (nspec is None):
      nspec=self.__nspec

      if (infile is None):
        return
    fin = open(infile,"rb")
    
    file_size = os.stat(infile)[6]
    nspec_max = file_size/(3840*2)
    print file_size, nspec_max

    this_spec = 0
    while True:
      try:
        for i in range(0,3839):
          this_pixel = struct.unpack('h',fin.read(2))[0]
          if (i>=self.__minpix):
            self.__specs[this_spec,i-self.__minpix] = this_pixel
        this_spec = this_spec+1
        print this_spec
        if (this_spec > nspec or this_spec >= nspec_max):
          break
      except EOFError:
        print 'file end'
    fin.close()
    self.__havespec = True

  def writeASCII(self, outfile="out.txt", infile=None, nspec=None):
    if (nspec is None):
      nspec=self._nspec
    if (not self.__havespecs):
      getspecs(infile, nspec)
    fout.open(outfile,"w")
    for ispec in range(0,nspec):
      for ipix in range(self.__minpix,self.__maxpix):
        fout.write("%h \t",self._specs[ispec,ipix])
      fout.write("\n")
    fout.close()

  def plot(self, beg_spec=0):
    plotid=self.__prepare_plot()
    self.plot=Plot2D(plotid)
    self.__y
    for ipix in range(0,self.__maxpix-self.__minpix):
      self.__y.append(self.specs[beg_spec,ipix])
    self.plot.setdata(self.__x,self.__y)

  def __prepare_plot(self):
    plotID=1
    self.__y=[]
    self.__x=[]
    for ipix in range(self.__minpix,self.__maxpix):
      self.__x.append(ipix)
    return plotID
