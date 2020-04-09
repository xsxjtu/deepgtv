from main_gpu_artificial import *
import os
import argparse
import numpy as np
from bm3d import bm3d_rgb, BM3DProfile
from experiment_funcs import get_experiment_noise, get_psnr, get_cropped_psnr
from PIL import Image
import matplotlib.pyplot as plt


def main(t, imagepath = 'C:\\Users\\HUYVU\\AppData\\Local\\Packages\\CanonicalGroupLimited.UbuntuonWindows_79rhkp1fndgsc\\LocalState\\rootfs\\home\\huyvu\\gauss\\'):
    # Experiment specifications
    #imagename = 'image_Lena512rgb.png'
    imagename = os.path.join(imagepath, 'ref'  , t + '_r.bmp')
    # Load noise-free image
    y = np.array(Image.open(imagename)) / 255

    # Possible noise types to be generated 'gw', 'g1', 'g2', 'g3', 'g4', 'g1w',
    # 'g2w', 'g3w', 'g4w'.
    noise_type = 'gw'
    noise_var = (15/255)**2  # Noise variance 25 std
    seed = 0  # seed for pseudorandom noise realization

    # Generate noise with given PSD
    noise, psd, kernel = get_experiment_noise(noise_type, noise_var, seed, y.shape)
    # N.B.: For the sake of simulating a more realistic acquisition scenario,
    # the generated noise is *not* circulant. Therefore there is a slight
    # discrepancy between PSD and the actual PSD computed from infinitely many
    # realizations of this noise with different seeds.

    # Generate noisy image corrupted by additive spatially correlated noise
    # with noise power spectrum PSD
    z = np.atleast_3d(y) + np.atleast_3d(noise)

    z_rang = np.minimum(np.maximum(z, 0), 1)
    noisyimagename=os.path.join(imagepath, 'noisy' , t + '_g.bmp')
    plt.imsave(noisyimagename, z_rang)
    z = np.array(Image.open(noisyimagename)) / 255
    # Call BM3D With the default settings.
    y_est = bm3d_rgb(z, psd)

    # To include refiltering:
    # y_est = bm3d_rgb(z, psd, 'refilter');

    # For other settings, use BM3DProfile.
    # profile = BM3DProfile(); # equivalent to profile = BM3DProfile('np');
    # profile.gamma = 6;  # redefine value of gamma parameter
    # y_est = bm3d_rgb(z, psd, profile);

    # Note: For white noise, you may instead of the PSD
    # also pass a standard deviation
    # y_est = bm3d_rgb(z, sqrt(noise_var));

    # If the different channels have varying PSDs, you can supply a MxNx3 PSD or a list of 3 STDs:
    # y_est = bm3d_rgb(z, np.concatenate((psd1, psd2, psd3), 2))
    # y_est = bm3d_rgb(z, [sigma1, sigma2, sigma3])

    psnr = get_psnr(y, y_est)
    print("PSNR:", psnr)

    # PSNR ignoring 16-pixel wide borders (as used in the paper), due to refiltering potentially leaving artifacts
    # on the pixels near the boundary of the image when noise is not circulant
    psnr_cropped = get_cropped_psnr(y, y_est, [16, 16])
    print("PSNR cropped:", psnr_cropped)

    # Ignore values outside range for display (or plt gives an error for multichannel input)
    y_est = np.minimum(np.maximum(y_est, 0), 1)
    z_rang = np.minimum(np.maximum(z, 0), 1)
    plt.imsave('t.bmp', y_est)
    y_est = np.array(Image.open('t.bmp')) / 255

    psnr = get_psnr(y, y_est)
    print("PSNR 2:", psnr)
    mse = ((y_est - y)**2).mean()*255
    print("MSE:", mse)
    #plt.imsave(imagepath+ 'noisy\\' + t + '_g.bmp', z_rang)

    # TEST CV2 PSNR
    try:
        from skimage.metrics import structural_similarity as compare_ssim
    except Exception:
        from skimage.measure import compare_ssim
    import cv2
    opath = 't.bmp'
    argref = imagename
    d = cv2.imread(opath, opt.rgb)
    tref = cv2.imread(argref, opt.rgb)
    (score, diff) = compare_ssim(tref, d, full=True, multichannel=True)
    psnr2 = cv2.PSNR(tref, d)
    print('#######################') 
    print('CV2 PSNR, SSIM: {:.2f}, {:.2f}'.format( psnr2, score))
    print('#######################') 
    print('')
    #plt.title("y, z, y_est")
    #plt.imshow(np.concatenate((y, np.squeeze(z_rang), y_est), axis=1))
    #plt.show()
    return psnr, mse

class RENOIR_Dataset2(Dataset):
    """
    Dataset loader
    """

    def __init__(self, img_dir, transform=None, subset=None):
        """
        Args:
            img_dir (string): Path to the csv file with annotations.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.img_dir = img_dir
        self.npath = os.path.join(img_dir, "noisy")
        self.rpath = os.path.join(img_dir, "ref")
        self.subset = subset
        self.nimg_name = sorted(os.listdir(self.npath))
        self.rimg_name = sorted(os.listdir(self.rpath))
        self.nimg_name = [
            i
            for i in self.nimg_name
            if i.split(".")[-1].lower() in ["jpeg", "jpg", "png", "bmp"]
        ]
        
        self.rimg_name = [
            i
            for i in self.rimg_name
            if i.split(".")[-1].lower() in ["jpeg", "jpg", "png", "bmp"]
        ]

        if self.subset:
            nimg_name = list()
            rimg_name = list()
            for i in range(len(self.nimg_name)):
                for j in self.subset:
                    if j in self.nimg_name[i]:
                        nimg_name.append(self.nimg_name[i])
                    # if j in self.rimg_name[i]:
                        rimg_name.append(self.rimg_name[i])
            self.nimg_name = sorted(nimg_name)
            self.rimg_name = sorted(rimg_name)
            

        self.transform = transform

    def __len__(self):
        return len(self.nimg_name)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        nimg_name = os.path.join(self.npath, self.nimg_name[idx])
        nimg = cv2.imread(nimg_name, opt.rgb)
        rimg_name = os.path.join(self.rpath, self.rimg_name[idx])
        rimg = cv2.imread(rimg_name, opt.rgb)

        
        sample = {'nimg': nimg, 'rimg': rimg, 'nn':self.nimg_name[idx], 'rn':self.rimg_name[idx]}

        if self.transform:
            sample = self.transform(sample)

        return sample

class ToTensor2(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample):
        nimg, rimg, nn, rn = sample['nimg'], sample['rimg'], sample['nn'], sample['rn']

        # swap color axis because
        # numpy image: H x W x C
        # torch image: C X H X W
        nimg = nimg.transpose((2, 0, 1))
        rimg = rimg.transpose((2, 0, 1))
        return {'nimg': torch.from_numpy(nimg),
                'rimg': torch.from_numpy(rimg), 'nn':nn, 'rn':rn}

class standardize2(object):
    """Convert opencv BGR to RGB order. Scale the image with a ratio"""

    def __init__(self, scale=None, w=None, normalize=None):
        """
        Args:
        scale (float): resize height and width of samples to scale*width and scale*height
        width (float): resize height and width of samples to width x width. Only works if "scale" is not specified
        """
        self.scale = scale
        self.w = w
        self.normalize = normalize

    def __call__(self, sample):
        nimg, rimg, nn, rn = sample['nimg'], sample['rimg'], sample['nn'], sample['rn']
        if self.scale:
            nimg = cv2.resize(nimg, (0, 0), fx=self.scale, fy=self.scale)
            rimg = cv2.resize(rimg, (0, 0), fx=self.scale, fy=self.scale)
        else:
            if self.w:
                nimg = cv2.resize(nimg, (self.w, self.w))
                rimg = cv2.resize(rimg, (self.w, self.w))
        if self.normalize:
            nimg = cv2.resize(nimg, (0, 0), fx=1, fy=1)
            rimg = cv2.resize(rimg, (0, 0), fx=1, fy=1)
        nimg = cv2.cvtColor(nimg, cv2.COLOR_BGR2RGB)
        rimg = cv2.cvtColor(rimg, cv2.COLOR_BGR2RGB)
        if self.normalize:
            nimg = nimg / 255
            rimg = rimg / 255
        return {'nimg': nimg,
                'rimg': rimg, 'nn':nn, 'rn':rn}
dtype=torch.FloatTensor
from torch.autograd import Variable

class gaussian_noise_(object):
    def __init__(self, stddev, mean):
        self.stddev = stddev
        self.mean = mean

    def __call__(self, sample):
        nimg, rimg = sample["rimg"].type(torch.FloatTensor), sample["rimg"]
        noise = self.stddev*Variable(torch.zeros(nimg.shape)).normal_()
        nimg = nimg + noise
        masks = (nimg>255).type(dtype)
        nimg = nimg - (nimg - 255)*masks
        masks = (nimg<0).type(dtype)
        nimg = nimg - (nimg)*masks
        return {"nimg": nimg, "rimg": rimg, 'rn':sample['rn']}

import shutil
import torchvision
def _main(imgw=324, trainp=None, gaussp=None):
    if not trainp:
        trainp = 'C:\\Users\\HUYVU\\AppData\\Local\\Packages\\CanonicalGroupLimited.UbuntuonWindows_79rhkp1fndgsc\\LocalState\\rootfs\\home\\huyvu\\train' 
    testset = ['10', '1', '2', '3', '4', '5', '6', '7','8','9']
    dataset = RENOIR_Dataset2(
        img_dir=trainp,
        transform=transforms.Compose([standardize2(w=imgw), ToTensor2(), gaussian_noise_(mean=0, stddev=25)]),
    )

    
    dataloader = DataLoader(
        dataset, batch_size=1, shuffle=False#, pin_memory=True
    )
    if not gaussp:
        gaussp = 'C:\\Users\\HUYVU\\AppData\\Local\\Packages\\CanonicalGroupLimited.UbuntuonWindows_79rhkp1fndgsc\\LocalState\\rootfs\\home\\huyvu\\gauss\\'
    noisyp = os.path.join(gaussp, 'noisy')
    refp = os.path.join(gaussp, 'ref')
    shutil.rmtree(gaussp, ignore_errors=True)
    shutil.rmtree(noisyp, ignore_errors=True)
    shutil.rmtree(refp, ignore_errors=True)
    os.makedirs(gaussp)
    os.makedirs(noisyp)
    os.makedirs(refp)

    for i, data in enumerate(dataloader, 0): 
        print(data['rn'])
        inputs = data['nimg'].float().type(dtype).squeeze(0)
        img = inputs.cpu().detach().numpy().astype(np.uint8)
        img = img.transpose(1, 2, 0)
        #plt.imsave('{0}{1}_g.bmp'.format(noisyp, testset[i]), img )
        inputs = data['rimg'].float().type(dtype).squeeze(0)
        img = inputs.cpu().detach().numpy().astype(np.uint8)
        img = img.transpose(1, 2, 0)
        plt.imsave(os.path.join(refp, '{0}_r.bmp'.format(testset[i])), img )
    
    bm3d_res = {'psnr':list(), 'mse':list()}
    for t in ['10', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        _psnr, _mse = main(t, imagepath=gaussp)
        bm3d_res['psnr'].append(_psnr)
        bm3d_res['mse'].append(_mse)
    print("MEAN BM3D PSNR, MSE:", np.mean(bm3d_res['psnr']), np.mean(bm3d_res['mse']))

    dataset = RENOIR_Dataset2(img_dir=gaussp,
                             transform = transforms.Compose([standardize2(),
                                                ToTensor2()])
                            )
    dataloader = DataLoader(dataset, batch_size=1,
                            shuffle=False, num_workers=1)
    # rm -r gauss_batch
    # mkdir gauss_batch
    # mkdir gauss_batch/noisy
    # mkdir gauss_batch/ref
    gaussp2 = gaussp + '_batch'
    noisyp = os.path.join(gaussp2, 'noisy')
    refp = os.path.join(gaussp2, 'ref')
    shutil.rmtree(gaussp2, ignore_errors=True)
    shutil.rmtree(noisyp, ignore_errors=True)
    shutil.rmtree(refp, ignore_errors=True)
    os.makedirs(gaussp2)
    os.makedirs(noisyp)
    os.makedirs(refp)

    shutil.rmtree(noisyp, ignore_errors=True)
    shutil.rmtree(refp, ignore_errors=True)
    os.makedirs(noisyp)
    os.makedirs(refp)
    stride=18
    for i_batch, s in enumerate(dataloader):
        print(i_batch, s['nimg'].size(),
              s['rimg'].size(), len(s['nimg']), s['nn'], s['rn'])
        T1 = s['nimg'].unfold(2, 36, stride).unfold(3, 36, stride).reshape(1, 3, -1, 36, 36).squeeze()
        T2 = s['rimg'].unfold(2, 36, stride).unfold(3, 36, stride).reshape(1, 3, -1, 36, 36).squeeze()
        nnn = s['nn'][0].split('.')[0]
        rn = s['rn'][0].split('.')[0]
        total = 0
        for i in range(T1.shape[1]):
            img = T1[:, i, :, :].cpu().detach().numpy().astype(np.uint8)
            img = img.transpose(1, 2, 0)
            plt.imsave('{0}\\{1}_{2}.png'.format(noisyp, nnn,i), img )
            total += 1
        for i in range(T2.shape[1]):
            img = T2[:, i, :, :].cpu().detach().numpy().astype(np.uint8)
            img = img.transpose(1, 2, 0)
            plt.imsave('{0}\\{1}_{2}.bmp'.format(refp, rn,i), img )
            
        print(total)
    print(T1.shape)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "-tp", "--train_path"
    )
    parser.add_argument(
        "-gp", "--gauss_path"
    )
    parser.add_argument(
        "-w", "--width", help="Resize image to a square image with given width"
    )
    parser.add_argument(
        "--channels", default=3
    )

    args = parser.parse_args()
    if args.width:
        imgw = int(args.width)
    else:
        imgw = None
    channels=int(args.channels)
    opt = OPT(train_path = args.train_path, batch_size = 50, admm_iter=4, prox_iter=3, delta=.1, channels=channels, eta=.3, u=25, lr=8e-6, momentum=0.9, u_max=65, u_min=55)
    opt._print()

    _main(imgw=imgw, trainp=args.train_path, gaussp=args.gauss_path)
