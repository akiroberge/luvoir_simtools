
'''jwstify_lensed_galaxies.py
This code takes the source-plane reconstruction of a lensed galaxy, convolves it to 
the normal diffraction limit of a telescope without lensing, then bins it to a more
normal pixel scale.  Now running with hacked PSFs for LUVOR, taken from HST and then resized.
jrigby, 7/2016, based on candelized_lensed_galaxies.py
'''
from astropy.io import fits
from astropy.convolution import convolve, convolve_fft
from astropy.stats import gaussian_fwhm_to_sigma   # a useful constant
from astropy.stats import mad_std
from scipy.misc import imresize
import numpy as np
from skimage.measure import block_reduce
import subprocess #  from comment by Adam on Python me dammit.
import os


def srcplane_to_luvoir(indir, in_images, filts, waves, in_pixscale, D_luvoir, outdir) :
    '''Take a source-plane reconstruction of a lensed galaxy, and predict what JWST would see.
    Inputs:
    indir :       directory to find the src plane reconstructed images.
    in_images:    list of input images, in indir
    filts:        list of LUVOIR filters to use.  Must be same shape as in_images
    waves:        list of wavelengths of those LUVOIR filters.  "
    in_pixscale:  the input pixel scale of the reconstructed src plane images, in arcsec/pixel
    out_pixscale: the output pixel scale , in arcsec/pix
    D_luvoir  :    How big is LUVOIR? in m.  Assumes diffraction limited
    outdir  :     what directory to write the output
    Outputs:      creates output images in outdir
    '''

    #psf_dir = "/Volumes/Aps_and_Docs/jrrigby1/Dropbox/SGAS-shared/s1110-paper2/PSF/"
    psf_dir = "./psfs/" 

    if len(in_images) != len(filts) :
        raise Exception("in_images and filters must be same shape.")
    np.set_printoptions(precision=3)

    if not os.path.exists(outdir):  # Make output directory if it doesn't already exist.
        os.makedirs(outdir)

    ref_PSF = "F390W_psf.fits"
    ref_wave = 0.390 # micron
    D_hst = 2.4003  # HST telescope diameter (m).
    print "D(m)  wave(um)  difflim(\") Pixel scales: [src plane input]  [output_desired]   [output_got].  All arcsec\pix"

    
    for ii, thisfile in enumerate(input_images) :#
        diff_lim = waves[ii] * 1E-6 / D_luvoir * 206265.  # Diffraction limit FWHM (")
        out_pixscale = diff_lim /2.0  # nyquist sampled
        print D_luvoir, waves[ii], diff_lim,
        data_in, header_in = fits.getdata(indir + thisfile, header=True)
        psf_file = psf_dir + ref_PSF
        #print "DEBUGGING, psf file is", psf_file
        psf_in =  fits.getdata(psf_file)
        scale_kate_psf = 0.03 / in_pixscale  # Kate's PSFs are 0.03"/pix.  Input src plane is finer
        scale_from_hst = (D_hst / D_luvoir) * waves[ii]/ref_wave  # scaling from HST psf
        scale_psf_by = scale_kate_psf * scale_from_hst
        #print "DEBUG, scaling PSF by", scale_psf_by, "made up of", scale_kate_psf, scale_from_hst
        psf_subsampled = imresize(psf_in, scale_psf_by)          
        #print "DEBUG, psf was resampled to ", psf_subsampled.shape, " from ", psf_in.shape
        data_out = convolve_fft(data_in, psf_subsampled)
        newname = outdir + filts[ii] + "_" + str(D_luvoir) + "m_conv.fits"    # output is convolved by PSF but not rebinned
        header_in['pix_scl'] = in_pixscale
        fits.writeto(newname, data_out, header_in, clobber=True)
        # rebin
        binby = int(out_pixscale / in_pixscale)  # this is the bin factor needed by rebinned
        # THIS IS A KLUDGE, because block_reduce can only handle integer downsampling factors.  Should do something more sophisticated.
        #print "Binning by", binby, ", but should be by", out_pixscale/in_pixscale
        rebinned = block_reduce(data_out, block_size=(binby,binby), func=np.sum)  # in skimage
        newname = outdir + filts[ii]  + "_" + str(D_luvoir) + "m_conv_rebin.fits"   # output is convolved by PSF and rebinned
        header_in['pix_scl'] = in_pixscale * binby
        fits.writeto(newname, rebinned, header_in, clobber=True)
        print in_pixscale, out_pixscale,  in_pixscale * binby

        # Add some noise.
        noise_center = 0.0
        noise_std =  0.0009 * (D_luvoir /  12.0)**(-0.5)
        #JT's imaging ETC: u-band: D=12m, t=1hr, m_AB=29.0 gives S/N=34
        #                  B-band: D=12m, t=1hr, m_AB=29.7 gives S/N=37.
        noisy = rebinned + np.random.normal(noise_center, noise_std, rebinned.shape)
        newname = outdir + filts[ii]  + "_" + str(D_luvoir) + "m_conv_rebin_noisy.fits"
        fits.writeto(newname, noisy, header_in, clobber=True)
        
    print "Wrote LUVOIR-ified images (convolved to LUVOIR PSF, binned to pixel scale", out_pixscale
    print "They are the _conv_rebin.fits images in "
    print "\t", outdir
    return(0)  # success

    
apertures = (2.4003, 4.0, 6.0, 8., 10., 12.)
for aperture in apertures:
    indir  = "/Volumes/Apps_and_Docs/jrrigby1/Dropbox/SGAS-shared/s1110-paper2/drizzled_source_images_23Feb2016/Ab/"
    outdir  = "/Volumes/Apps_and_Docs/jrrigby1/Dropbox/SGAS-shared/s1110-paper2/LUVOIRify/Ab/"
    input_images = ('sdssj1110p6459_F390W_0.03g0.8_drc_sci_core_Ab_s01_out.fits', "sdssj1110p6459_F606W_0.03g0.8_drc_sci_core_Ab_s01_out.fits", "sdssj1110p6459_F105W_0.03g0.5_drz_sci_core_Ab_s01_out.fits")
    filts = ('F390W', 'F606W', 'F105W') # Filters I want to map this to for LUVOIR.  May not be obvious mapping
    waves = np.array((0.390, 0.606, 1.05))
    in_pixscale = 0.1 * 0.03  #(arcsec/pixel)   The pixel scale of the input source plane reconstructions
    # From Keren: pixel scale = 0.1 of image plane pixel scale (0.03") = 0.003"/pix
    out_pixscale = 0.003  # just a guess
    srcplane_to_luvoir(indir, input_images, filts, waves, in_pixscale,  aperture, outdir)

for aperture in apertures:
    indir  = "/Volumes/Apps_and_Docs/jrrigby1/Dropbox/SGAS-shared/s1110-paper2/source_plane_model/"
    outdir  = "/Volumes/Apps_and_Docs/jrrigby1/Dropbox/SGAS-shared/s1110-paper2/LUVOIRify/Ab_model/"
    input_images = ('source_390_all.fits', 'source_606_all.fits')
    filts = ('F390W', 'F606W') # Filters I want to map this to for LUVOIR.  May not be obvious mapping
    waves = np.array((0.390, 0.606))
    in_pixscale = 0.1 * 0.03  #(arcsec/pixel)   The pixel scale of the input source plane reconstructions
    # From Keren: pixel scale = 0.1 of image plane pixel scale (0.03") = 0.003"/pix
    out_pixscale = 0.003  # just a guess
    srcplane_to_luvoir(indir, input_images, filts, waves, in_pixscale,  aperture, outdir)


    #
print "ALL DONE."
