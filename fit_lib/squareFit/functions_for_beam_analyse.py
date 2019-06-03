from scipy.ndimage.interpolation import rotate
import h5py
import numpy as np
import matplotlib.pyplot as plt
import pdb
import numpy.fft as F

"""functions used for processing images of square beam
    """

def hdf5reader(filename,fps):
    """This is written function for read the HDF5 generated by the Fast camera
    [data,NOP,fps]=hdf5reader(filename,fps)
    
    input:
    filename=filename(also include path name if needed)
    fps=Frams per second. if you use the camera in ModeA(full range scan) and no triggering,
    you can input 'nan' and the code will guess it for you. 
    
    output:
        data=the stack of images
        NOP=number of pictures
        fps=frame per second
    """


    print('loading the HDF5 file...')
    f=h5py.File(filename, "r")

#unfortunately the t here is not the right t. 
    t = f['/entry/instrument/detector/NDAttributes/CAM.HDF.TIME_STAMP']
    NOP=len(t)

    data=f['/entry/instrument/detector/data']

#judge the fps for mode A(full scan size)
    if np.isnan(fps)==True:

    
        if data.shape[1]==120:
                fps = 713

        elif data.shape[1]==240:
                fps = 400

        elif  data.shape[1]==480:
                fps = 200

        else:
            print('Unable to determine FPS! range(N_R)\n\n')




        print('fps is estimated to be %d.'%fps)



    return data,NOP,fps


def fft_filter(Y,filtersize,nop):
    """fft bandpass filter for finding rotation angles
    Filter_Y=fft_filter(Y,filtersize,nop)
    
    input: 
        Y=the data you want to filtered
        filtersize=the size of the filter,smaller size gives smoother result. 
        NOP=number of points
    output:
        Filter_Y=the Filtered data
        """
    FftY=F.fft(Y)
    FftY[filtersize:(nop-filtersize+1)]=0
    Filter_Y=np.abs(F.ifft(FftY))
    return Filter_Y

#
def cross_point(slope1,inter1,slope2,inter2):
    """compute the cross point of two straight line
    
    [x,y]=cross_point(slope1,inter1,slope2,inter2)
    input: 
        informations of the two lines
    output:
        position of the cross point
    
    quite clear right?
        """
    m1=np.matrix([[1,-1],
        [slope2,-slope1]])
    m2=np.matrix([[inter1,inter2]])
    m2=np.transpose(m2)
    xy=(m1*m2)/(-slope1+slope2) 
    x=xy [0,0]
    y=xy [1,0]    
    return x,y    


     
def shift_subtraction_x(im,xshft):
    '''shift and subtract the image in x direction'''
    newimx = np.roll(im, xshft, axis=1)                #shift the image along x axis
    
#  compute the difference between origianl and shifted images, the left egde shows negetive values while 
#right edge shows positive values.   
    subimx=newimx-im                                   
    Sx=subimx.sum(axis=0)                               #sum over x axis
    return Sx     

def shift_subtraction_y(im,yshft): 
    '''shift and subtract the image in x direction'''  
    newimy = np.roll(im, yshft, axis=0)
    subimy=newimy-im
    Sy=np.transpose(subimy.sum(axis=1))
    return Sy


#compute the approximate params of the square beams                
def get_apx_params (im,graph):
    '''compute the approximate params of the square beams
    apxparams=get_apx_params (im,graph)
    
    
    
    input:
        im=the image...
        graph=plot the fitting if graph=1
    output:
        apxparams=[hmxin,centrex,centrey,height,width]
        (hmxin=half maximun intensity of the beam.
        ....)
    '''
    xshft=3                                           #set a thicker shift distance when the edge is blur
    yshft=3
    
    
    #the mean value of the whole image,which is slightly higher than the
    #background noise.

    meanim=np.mean(im);
    
    #take twice of the mean value as threshold.
    im[im<(2*meanim)]=0;                                                                                       
                                                                                                                                                                                                                                                                               
    Sx=shift_subtraction_x(im,3)
    Sy=shift_subtraction_y(im,3)
    
    sminindx = np.argmin(Sx)                            #find the positions of the edges
    smaxindx = np.argmax(Sx)
    sminindy = np.argmin(Sy)
    smaxindy = np.argmax(Sy)
    
    minindx=sminindx-xshft/2                            #shift the image back
    maxindx=smaxindx-xshft/2
    minindy=sminindy-yshft/2
    maxindy=smaxindy-yshft/2
    
    height=maxindy-minindy                              #compute the size the image 
    width=maxindx-minindx
    
    centrex=int((maxindx+minindx)/2)                  #compute the centre of the image (must be intergal)
    centrey=int((maxindy+minindy)/2)
    
    x_min_e=int(minindx+width/4)                      #find the 1/2 centre pf the square
    x_max_e=int(maxindx-width/4)
    y_min_e=int(minindy+height/4)
    y_max_e=int(maxindy-height/4)
    cut_im=im[y_min_e:y_max_e+1,x_min_e:x_max_e+1]
    

# compute the average intensity of the 1/2 centre of the image, then divide by 2 as the half maxima intensity.    
    hmxin=np.mean(cut_im)/2
    

        #plot the fitting result if graph==1
    if graph==1:
            plt.imshow(im,origin='lower')
            lines = plt.plot([x_min_e,x_max_e], [y_min_e,y_min_e],[x_max_e,x_max_e],[y_min_e,y_max_e],[x_min_e,x_max_e], [y_max_e,y_max_e],[x_min_e,x_min_e], [y_min_e,y_max_e])
            plt.setp(lines, color='r', linewidth=2.0)
            plt.show()
            
    apxparams=[hmxin,centrex,centrey,height,width]
    return apxparams

#######
def find_angles(im,angle_range,filtersize,hmxin,threspara):
    
    '''This function is used to determine the rotated angles of each side of the square.
     
    params=find_angles(im,angle_range,filtersize,hmxin,threspara)
    
    
    
    input:
        im=image
        angle_range=the range of rotation
        filtersize=the size of FFt band pass filter. (recomand 7)
        hmxin=half maximum of intensity
        threspara: normal is 1, means set the pixels with intensity lower than half maximum.
                    can set it to 1.1-1.5 if the edge of the image is blur(but sometimes
                    will make a hole inside the image.....)
    output:
        'params=[-angle_side1,-angle_side2,-angle_side3,-angle_side4]'
    
    '''
    #set the rotation angles(in degree)
    rotate_step=0.05
    
    rAngle=np.arange(-angle_range,angle_range+rotate_step,rotate_step)
    NoA=angle_range/rotate_step*2
    xshft=1
    yshft=1
    
    #set zero variables
    RSx_Max = np.zeros(rAngle.size)
    RSx_Min = np.zeros(rAngle.size)
    RSy_Max = np.zeros(rAngle.size)
    RSy_Min = np.zeros(rAngle.size)
    
    #t = time.time()

    for n in range(rAngle.size):
        #rotate the picture
        Rim=rotate(im,rAngle[n],reshape=False)
        
    #set the elements that lower than threshold to zero,threshold para normally take 1
    #but for images with blur edge,a higher threspara will works better.

        Rim[Rim<threspara*hmxin]=0
    
        #circshift the picture by certain pixels and then compute the subtract of
        #the obtained picture and the original one. Then the edge of the squre is
        #shown in the obtained picture.    
                    
        Rimx = np.roll(Rim,xshft, axis=1)
        subRimx=Rimx-Rim
        
        newRimy = np.roll(Rim,yshft, axis=0)
        subRimy=newRimy-Rim          
    
        #sum the subtracted picture over x and y respectively
        RSx=subRimx.sum(axis=0)
        RSy=np.transpose(subRimy.sum(axis=1))                  
                                            
        #the angle that gives us highest maxima or lowest minima is 
        #the angle that the side perpendicular to the axis.      
        RSx_Max[n] = np.amax(RSx)
        RSx_Min[n] = np.amin(RSx)
        RSy_Max[n] = np.amax(RSy)
        RSy_Min[n] = np.amin(RSy)    
                                                                                                                                                                
    #Use Fourier bandpass filter to remove the noise
    Filter_RSx_Max=fft_filter(RSx_Max,filtersize,NoA)
    Filter_RSx_Min=fft_filter(RSx_Min,filtersize,NoA)
    Filter_RSy_Max=fft_filter(RSy_Max,filtersize,NoA)
    Filter_RSy_Min=fft_filter(RSy_Min,filtersize,NoA)
    

 
    
    #find the angles that correspond tomin&max values
    angle_side1 = rAngle[np.argmax(Filter_RSx_Max)]
    angle_side2 = rAngle[np.argmax(Filter_RSy_Max)]
    angle_side3 = rAngle[np.argmax(Filter_RSx_Min)]
    angle_side4 = rAngle[np.argmax(Filter_RSy_Min)]                                                                                                                                                                                                                                               
    
    
    if angle_side1==0:
        angle_side1=0.0001
    
    if angle_side3==0:
        angle_side3=0.0001
    
    #print time.time() - t
    
    
    params=[-angle_side1,-angle_side2,-angle_side3,-angle_side4]
    return params
    
#compute the average rotation angles for N_R images
def average_angles(N_R,data,angle_range,filtersize,threspara):
    ''' compute the average angles of N_R images(normally 10)
        angles=average_angles(N_R,data,angle_range,filtersize,threspara):
    input:
        N_R=number of images to compute
        data=the stack of all images
        angle_range=the range of rotation
        filtersize=the size of FFt band pass filter. (recomand 7)
        hmxin=half maximum of intensity
        threspara: normal is 1, means set the pixels with intensity lower than half maximum.
                    can set it to 1.1-1.5 if the edge of the image is blur(but sometimes
                    will make a hole inside the image.....)
    output:
        angles=[angle_side1,...2,....3,....4]
    
    '''
    angles_a=np.zeros((4,N_R))
    for n in range(N_R):
      
        im =data[n,:,:]
        im=np.array(im,dtype=float)
#get the half maximum intensity of beam to remove back ground noise of the image.
#set the second parameter 1 to show the fitting result.(1/3 centre of the beam)
        apxparams=get_apx_params(im,0)
        hmxin=apxparams[0]
        s=im.shape

#shift the image for subtracion         
        im = np.roll(im,(int(s[0]/2)-apxparams[2]), axis=0)
        
        im = np.roll(im,(int(s[1]/2)-apxparams[1]),axis =1)
        
        angles_a[:,n]= find_angles(im,angle_range,filtersize,hmxin,threspara)
  

#compute the average angles for several images
    angles=np.sum(angles_a,axis=1)/N_R;
    return angles
    
    


def analy_square(im,angles,graph,threspara):
    '''the fucntion to fit square beam by edge detecting,compute the four vertex of a square beam by 
        given the angles of the four sides.
        
        
        
    params=analy_square(im,angles,graph,threspara)
    


        vertex3         vertex 2
            \   side 2   /     
             \_________ /
             /         |
     side 3 /          |  side 1
           /           |  
          /____________|
          |     side 4  \
     vertex 4        vertex 1


    Input:
    im = the image of the squre  
    angles= the angles of 4 sides.
    graph=To display graphical output please put a flag here (1) 
    threspara: normal is 1, means set the pixels with intensity lower than half maximum.
                    can set it to 1.1-1.5 if the edge of the image is blur(but sometimes
                    will make a hole inside the image.....)
    .
    Output:
    params=[centre_x centre_y width height inten]

    [centrey centrex]=the centre of the rectangle
    inten=the overall intensity of the square area
    
    
    
    '''
    #generate a blank params
    params=np.nan  
     
    xshft=1
    yshft=1
    
    #the number of points in two sides of the peaks that ???? dkhts
    nei_o=6                        
    nei_i=4


    s=im.shape
    
    #make sure the length and width of the image are even numbers(which should be
    #as long as you didn't cut the image into weired shape.)
    #otherwise cant find the accurate position of centre of picture and 
    #cause some delicate problems.~(>_<)~
    #but the 'delicate problems only influence the abosolute positions of the edge, 
    #wont influence the FFT and Allan deivation result.
    #So...you can delete it that one line of pixels....\('_`)/
    if s[0]&1==1:
        np.delete(im, 0, 0)
    if s[1]&1==1:
        np.delete(im, 0, 1)
    
    #calculte the shape of im again
    s=im.shape
    
    #make a copy of the image
    imc=im
    
    #get the approximate params (position,half maxmium intensity) of the square
    [hmxin,acentrex,acentrey,aheight,awidth]=get_apx_params(im,0)
    
    #shift the square to the centre of image by apx positions
    
    cen_im=np.roll(im,(int(s[0]/2)-acentrey),axis=0)
    cen_im=np.roll(cen_im,(int(s[1]/2)-acentrex),axis=1)
    
    #set the elements that lower than threshold to zero,threshold para normally take 1
    #but for images with blur edge,a higher threspara will works better.
    cen_im[cen_im<threspara*hmxin]=0
    

    
    
    #cut the image into smaller size(2width*2height)
    
      
    if aheight*3<s[0]:
        if awidth*3<s[1]:
           #####cut the centre of the picture.******notice!:in
           #####'round(s(1)/2)-round(aheight)+1', the '+1' is very
           #####important,which make sure the centre of the beam is in the
           #####centre of the cutted image.
            cut_cen_im=cen_im[(int(s[0]/2)-int(aheight)+1):(int(s[0]/2)+int(aheight)+1),(int(s[1]/2)-int(awidth)+1):(int(s[1]/2)+int(awidth)+1)]
        else :cut_cen_im=cen_im
    else:cut_cen_im=cen_im
    
    

    sc=cut_cen_im.shape
    
    #rotate image by the angle of sides
       
    cut_cen_im_1=rotate(cut_cen_im,angles[0],reshape=False)             #rotate the image, let the side1 perpendicular to x axis  
    Sx_side1=shift_subtraction_x(cut_cen_im_1,xshft)                  
    
    #find a more accurate position of side1
    apx_max_ind_1=np.argmax(Sx_side1)
    
    #check whether the pic is still in the range
    if apx_max_ind_1+nei_o>sc[1]:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    if apx_max_ind_1-nei_i<0:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params


#compute position for side1     
    nei_max_ind_1=apx_max_ind_1 + np.arange(-nei_i,nei_o+1,1)
    nei_max_1 = Sx_side1[(apx_max_ind_1-nei_i):(apx_max_ind_1+nei_o+1)]
    Sx_side1_max =sum(nei_max_1*nei_max_ind_1)/sum(nei_max_1)
    
    
    
    
    
    distance_side1=Sx_side1_max-xshft/2-int(sc[1]/2)     #Compute the distance between the original point (which is the centre of image)
                                                            #to side1,Since we have shifted our image, so remember to 'shift' them back!   
    
    slope1=-1/(np.tan(-angles[0]*np.pi/180))                           #compute the slope of side1 by its rotation angle
    intercept_side1=distance_side1/np.sin(-angles[0]*np.pi/180)       #compute the y intercept by the distance to original point and the slope
    
    
    
    #side2
    cut_cen_im_2=rotate(cut_cen_im,angles[1],reshape=False)
    Sy_side2=shift_subtraction_y(cut_cen_im_2,yshft)
    
    
        #find a more accurate position of side1
    apx_max_ind_2=np.argmax(Sy_side2)
    
    #check whether the pic is still in the range
    if apx_max_ind_2+nei_o>sc[0]:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    if apx_max_ind_2-nei_i<0:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params


    
    nei_max_ind_2=apx_max_ind_2 + np.arange(-nei_i,nei_o+1,1)
    nei_max_2 = Sy_side2[(apx_max_ind_2-nei_i):(apx_max_ind_2+nei_o+1)]
    Sy_side2_max =sum(nei_max_2*nei_max_ind_2)/sum(nei_max_2)
    
    
    distance_side2=Sy_side2_max-yshft/2-int(sc[0]/2)
    
    slope2=np.tan(-angles[1]*np.pi/180)
    intercept_side2=distance_side2/np.cos(-angles[1]*np.pi/180)
    
    #side3
    
    cut_cen_im_3=rotate(cut_cen_im,angles[2],reshape=False)
    Sx_side3=shift_subtraction_x(cut_cen_im_3,xshft)
    
    #find a more accurate position of side3
    apx_min_ind_3=np.argmin(Sx_side3)
    
    #check whether the pic is still in the range
    if apx_min_ind_3+nei_o>sc[1]:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    if apx_min_ind_3-nei_i<0:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    

    nei_min_ind_3=apx_min_ind_3 + np.arange(-nei_i,nei_o+1,1)
    nei_min_3 = Sx_side3[(apx_min_ind_3-nei_i):(apx_min_ind_3+nei_o+1)]
    Sx_side3_min =sum(nei_min_3*nei_min_ind_3)/sum(nei_min_3)
    

    
    distance_side3=Sx_side3_min-xshft/2-int(sc[1]/2)
    slope3=-1/(np.tan(-angles[2]*np.pi/180))
    intercept_side3=distance_side3/np.sin(-angles[2]*np.pi/180)
    
    
    
    
    
    
    cut_cen_im_4=rotate(cut_cen_im,angles[3],reshape=False)
    Sy_side4=shift_subtraction_y(cut_cen_im_4,yshft)
    
    
    #find a more accurate position of side3
    apx_min_ind_4=np.argmin(Sy_side4)
    
    #check whether the pic is still in the range
    if apx_min_ind_4+nei_o>sc[0]:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    if apx_min_ind_4-nei_i<0:
        print('image out of the picture!!!')
        params=[np.nan,np.nan]
        return params
    
    
    
    nei_min_ind_4=apx_min_ind_4 + np.arange(-nei_i,nei_o+1,1)
    nei_min_4 = Sy_side4[(apx_min_ind_4-nei_i):(apx_min_ind_4+nei_o+1)]
    Sy_side4_min =sum(nei_min_4*nei_min_ind_4)/sum(nei_min_4)
    

    distance_side4=Sy_side4_min-yshft/2-int(sc[0]/2)
    slope4=np.tan(-angles[3]*np.pi/180)
    intercept_side4=distance_side4/np.cos(-angles[3]*np.pi/180)
    
    
    #compute the cross points of the 4 sides,which are the vertexs of square
    [x1,y1]=cross_point(slope1,intercept_side1,slope4,intercept_side4)
    [x2,y2]=cross_point(slope1,intercept_side1,slope2,intercept_side2)
    [x3,y3]=cross_point(slope2,intercept_side2,slope3,intercept_side3)
    [x4,y4]=cross_point(slope3,intercept_side3,slope4,intercept_side4)
    
    #remember we haved shifted our square into the centre of the image, then we
    #need to 'shift' them back
    [x1,x2,x3,x4]=np.array([x1,x2,x3,x4])+acentrex
    [y1,y2,y3,y4]=np.array([y1,y2,y3,y4])+acentrey

    
    #the position of the centre of the square
    centre_x=(x1+x2+x3+x4)/4
    centre_y=(y1+y2+y3+y4)/4
    
    #compute other params
    width=(x1+x2-x3-x4)/2
    height=(y2+y3-y4-y1)/2
    inten=np.sum(cen_im)

    sc=imc.shape
    
    #plot the fitting result if graph=1
    if graph==1:  
        plt.figure()
        plt.imshow(imc,origin='lower')

        lines = plt.plot([x1,x2], [y1,y2],[x2,x3],[y2,y3],[x3,x4], [y3,y4],[x4,x1], [y4,y1])
        plt.setp(lines, color='r', linewidth=2.0)
        plt.show()
    
    params=[centre_x,centre_y,width,height,inten]
    return params
    
    
def fft_2D_squar_beam(im,phim0,sx,sy):

#set the constant 
    phase_const=2*np.pi

    s=im.shape

#compute the 2DFFT image and shift the 0-frequency to the centre
    fftim=F.fftshift(F.fft2(im))
#compute the phase of the image(only for the centre points
    phase=np.angle(fftim[(int(s[0]/2)-sy):(int(s[0]/2)+sy),(int(s[1]/2-sx)):(int(s[1]/2)+sx)])

#subtract the phase of current image  with the phase of the first image
    subph=phase-phim0; 

#convert the phase different all into the same period...well, dont know how to expalain...
#basically the phase will jump by 2*pi without these code.   
    for i in range(2*sy):
        for j in range(2*sx):
            if subph[i,j]>np.pi:
                subph[i,j]=subph[i,j]-2*np.pi
                
            else: 
                if subph[i,j]<-np.pi:
                    subph[i,j]=subph[i,j]+2*np.pi

#compute the average difference between neighour pixels in the image of phase defference, which correspond to the 
#position difference
    sumxph=subph.sum(axis=0)
    sumyph=np.transpose(subph.sum(axis=1))
    meanx=(np.sum(sumxph[0:sx])-np.sum(sumxph[sx:2*sx]))/(sx*sy*2)/sx
    meany=(np.sum(sumyph[0:sy])-np.sum(sumyph[sy:2*sy]))/(sx*sy*2)/sy

#convert the mean vlues into positions(in pixels0
    positionx=meanx*s[1]/phase_const
    positiony=meany*s[0]/phase_const


    position=[positionx,positiony]
    return position

def generate_sample_array(N_o_Ad,NOP):
    '''generate a suitable sample points for allandeviation.
    
    sample=generate_sample_array(N_o_Ad,NOP)
    
    input:
        N_O_Ad=the number of different intergration time you want.(but the generated
                array will has a slightly difference length, normally 1~4 more than your
                input number.
        NOP=  number of images
    
    output:
        sample: an array with numbers.
            eg: [1,2,3,4,5,7,9,11,13,15,....]

    '''
    ##################
    n=1
    f=1
    L=0
    p=10
    
    
    
    if NOP>15:
        parent=np.array([])
        
        #run the loop while the L is smaller than half of NOP
        while L<(int(NOP/2)-1):
            L=p*f+n    
        
            a=np.arange(n,L,f)
        
            #make sure the array is not out of boud
            if L>(int(NOP/2)-1):
                for x in np.arange(9,-1,-1):
                    if a[x]>(int(NOP/2)-1):
                        a=a[:x]               
            n=L
            f=f*2
            parent=np.append(parent,a)
        
            
        
            #get the length of the array, and compute the quotient between the length
            #%and the number of points that user wants.
        lp=parent.size
        
        
        quotinet=lp/N_o_Ad;
        
        if quotinet<1:
            quotinet=1;
        
        
        if N_o_Ad >20:
            s_ind1=np.arange(0,6,1)
            s_ind2=np.arange(6,lp-0.9,quotinet)
                
            s_ind=np.append(s_ind1,s_ind2)
            s_ind=s_ind.astype(int)
        
        
        else:
            s_ind=np.arange(0,lp-0.9,quotinet)
            s_ind=s_ind.astype(int)
        
        sample=parent[s_ind]
   
    #make sure not out of the pound
    else:
        sample=np.array([1,2])


    return sample