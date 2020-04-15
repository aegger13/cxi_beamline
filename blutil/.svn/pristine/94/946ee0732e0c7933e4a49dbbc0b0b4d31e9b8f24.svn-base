'''
Module for the basic manipulation of image information
'''
import logging
import numpy as np
import matplotlib.pyplot as plt

log  = logging.getLogger(__name__)


class Image(object):

    def __init__(self,array):
        self.raw     = array
        self.image   = np.copy(array)
        self._mask   = np.zeros(array.shape)
        
        #Attributes to keep track of saved ROI
        self._index = 1
        self._rois  = {}


    @property
    def intensity(self):
        """
        The sum of all the pixels in the image
        """
        return self.image.sum()

     
    @property
    def shape(self): #Convienence method
        """
        Return the dimensional sizes of the image
        """
        return np.shape(self.image)
        

    @property 
    def compressed(self):
        """
        Compress a colored image into a grayscale
        """
        if len(self.shape) > 2:
            return np.sum(self.image,axis=2)
        
        return self.raw


    @property
    def rois(self):
        """
        Return the saved ROI instances associated with image
        """
        return sorted(self._rois.keys())


    def add_roi(self,type='box',alias=None,**kwargs): 
        """
        Add an ROI to the image
        
        The ROI is added as a property of the image with the name given by the
        alias attribute. This is useful to save a certain region selection so
        that it can be accessed mutltiple times without redoing the mask
        calculation. In order to specify which shape ROI, include the type as
        either circle or box, then pass the pertinent shape attributes
        described in the associated functions keywords.
        
        Parameters
        ----------
            type : str, optional
                This is 'box' by default, for a circular region use 'circle'

            alias : str, optional
                The name associated with ROI. It is recommended to set this to
                a useful description, but an alias of ROI_(index) will be
                generated where index is incremented everytime the function is
                called wihtout an alias.
            
            kwargs : optional 
                Keyword arguments passed on to either the `.circular_roi` or
                `rectangular_roi` based on the chosen type.

        Returns
        -------
        img : Image
            An object of type Image containing only the ROI
            
        See Also
        --------
        `Image.rectangular_roi`, `Image.circular_roi`, `Image.add_roi`
        """
        types = {'box'    : self.rectangular_roi,
                 'circle' : self.circular_roi
                }
        
        if type not in types.keys(): 
            raise ValueError('Invalid type %s for ROI, choose either box or '\
                             'circle',type)
        
        if not alias: 
            alias = 'ROI_{:02d}'.format(self._index)    
            log.debug('No alias provided for ROI, using {:}'.format(alias))
            self._index += 1

        if alias in self.rois:
            print 'Overwriting ROI with the name {:}, as an ROI with this alias '\
                  'was already created'.format(alias)
        
        img = types[type](**kwargs)
        self._rois[alias] = img
        setattr(self,alias,img)
        
        return img


    def rectangular_roi(self,x=0.,y=0.,w=None,h=None):
        """
        Create a rectangular ROI 
        
        Parameters
        ----------
        x : float, optional
            Horizontal position for top-left corner of the ROI. By default, the
            most left pixel in the image.

        y : float, optional
            Vertical postion for top-left corner of the ROI. By default, the
            top most pixel in the image.
        
        w : float, optional
            Horizontal width for ROI. By default, the remaining width of the
            current image.

        h : float, optional
            Vertical height of the ROI. By default, the remaining height of the
            current image.

        Returns
        ------- 
        img : Image
            An object of type Image containing only the ROI
        
        See Also
        --------
        `Image.circular_roi`, `Image.add_roi`
        """
        if not w:
            w = np.shape(self.raw)[1]-x

        if not h:
            h = np.shape(self.raw)[0]-y
       
        img = self.image[y:y+h,x:x+w]
         
        return Image(img)

                             
    def circular_roi(self,outer=None,x=None,y=None,inner=0.,crop=True):
        """
        Create a circular ROI
        
        Parameters
        -----------
        x : float, optional
            Horizontal position for top-left corner of the ROI. By default, the
            horizontal center is used.

        y : float, optional
            Vertical postion for top-left corner of the ROI. By default, the
            vertical center is used.
        
        inner : float, optional
            The inner radius of the ROI. By default, no inner radius is used so
            a circle is returned
        
        outer : float, optional
            The outer radius of the ROI. By default, no outer radius is used. 
        
        crop  : bool , optional
            Choice to crop down the returned ROI to only show the area with
            circular region inside
        
        Returns
        -------
        img : Image
            An object of type Image containing only the ROI
        
        See Also
        --------
        `Image.circular_roi`, `Image.add_roi`
        """
        ly,lx = self.compressed.shape
        grid_y, grid_x = np.ogrid[0:ly,0:lx]
        
        #Use center of image if no position specified
        if x is None:
            x = lx/2
            log.debug('No position specified for x axis '\
                      'using center as location')

        if y is None:
            y = ly/2
            log.debug('No position specified for y axis '\
                      'using center as location')

        #Crop inner circle / does nothing if inner is unspecified
        inner_circle  = (grid_x-x)**2 + (grid_y-y)**2 < inner**2
        
        image = self.image
        #If an outer boundary was specifed apply
        if outer:
            outer_circle  = (grid_x-x)**2 + (grid_y-y)**2 > outer**2
            mask          = np.logical_or(inner_circle,outer_circle)

            if crop:
                y_min,y_max = np.clip([y-outer,y+outer],0,ly)
                x_min,x_max = np.clip([x-outer,x+outer],0,lx)
                
                print y_min,y_max,x_min,x_max,lx,ly

                image = image[y_min:y_max,x_min:x_max]
                mask = mask[y_min:y_max,x_min:x_max]
                
        else:
            mask  = inner_circle
        
        img = Image(image)
        #Apply the mask to the raw image
        #This must be done within the new 
        #object, so that the mask does not
        #affect the overall image.
        img.image[mask] = 0
        return img
   

    def update(self,img,ignore_size=False):
        """
        Update the raw array behind the `Image` object.

        This function is useful to update your image object if you are getting
        the array from a stream or at least an updating source. The main
        benefit of using this method is all of the image manipulation done
        previously on the image object will be preserved, just the image behind
        it will be updated.  
        
        Parameters
        ----------
            img : Image array
                The image array to be processed
            
            ignore_size : bool, optional
                By default, an Exception will be raised if you try and update
                the image and the new array is a different size than the
                previous. If you set to True, be prepared that saved ROIs will
                no longer make sense 
        
        Returns
        -------
            image : np.array
                The updated image with all of the previously configured
                image modfications.

        Raises
        ------
            ValueError
                This will be raised if the image has changed size and the
                ignore_size flag is not set 
        """
        array = self._to_np(img)
        
        if not ignore_size and img.shape != self.raw.shape:
            raise ValueError('New image is not the same size as the previous '\
                             'one.')
        self.raw = array

        return self.image
    

    def reset(self,propagate=True):
        """
        Reset all settings and masks applied to image.
        """
        self.image = np.copy(self.raw)


    def find_projection(self,axis='x'):
        """
        Return the projection along a specific axis
        
        Parameters
        ----------
        axis : The axis which to project onto either x, y, or r
        
        Returns
        -------
            np.array
                1-d array of projection
        
        TODO : Add radial / theta projection option
        """
        if axis == 'x':
           return self.compressed.sum(axis=0)
                             
        if axis == 'y':
            return self.compressed.sum(axis=1)


    def show(self):
        """
        Show the image using the `matplotlib` module
        """
        plt.imshow(self.image)
        plt.show()

    
    def _to_np(self,array):
        """
        Convert an arbitrary array to a numpy type
        """
        if not isinstance(array,np.ndarray):
            array = np.asarray(array)

        return array

