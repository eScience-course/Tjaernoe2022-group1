import numpy as np
import xarray as xr

def pnsd_integration(ds, size_thresh, var='dNdlogD', dvar = 'D'):
    '''
    - D is the mean diameter of the size bins
    - time is the time dimension
    - ds is the dataset containing the size distribution
    - pnsd is the variable in which the particle number size distribution is stored (dN/dlogDp)
    - size_thresh is the lower limit of the size bins to be integrated in nanometers
    '''
    Dp = ds[dvar].values
    logDp = np.log10(Dp)
    interval = np.array([logDp[i]-logDp[i-1] for i in range(1,np.size(Dp))])/2
    centers = logDp[:-1]+interval
    centers_bis = np.append(logDp[0]-interval[0], centers)
    centers_bis = np.append(centers_bis, logDp[-1]+interval[-1])
    bound_bin = 10**(centers_bis)#*10**(-9)
    dlogDp = np.array([np.log10(bound_bin[i+1])-np.log10(bound_bin[i]) for i in range(0, bound_bin.shape[0]-1)])
    pnsd_nolog = np.zeros(ds[var].values.shape)
    for i, Dp_i in enumerate(Dp):
        pnsd_nolog[:,i] = ds[var].sel(**{dvar : Dp_i}).values * dlogDp[i]
    ds[f'{var}_unlog'] = (['time', dvar], pnsd_nolog)
    ds['N'+str(np.round(size_thresh, 2))] = ds[f'{var}_unlog'].sel(**{dvar:slice(size_thresh, 1000)}).sum(**{'dim':dvar})


    
def compute_Nx_ebas_cleaned(ds, x=100, var_diam = 'D',v_dNdlog10D='particle_number_size_distribution'):

    v_log10D = 'log10D'
    ds[v_log10D] = np.log10(ds[var_diam])
    mid_points = (ds[v_log10D].values[0:-1] + ds[v_log10D].values[1:]) / 2
    bottom = ds[v_log10D].values[0] - (mid_points[0] - ds[v_log10D].values[0])
    top = ds[v_log10D].values[-1] + (mid_points[-1] - ds[v_log10D].values[-2])

    d_lims = np.concatenate([np.array([bottom]), mid_points, np.array([top])])
    # Somehow I thought it was a good idea to go to linear space and back to log later.....
    d_lims = 10**d_lims

    ds['bottom'] = xr.DataArray(d_lims[0:-1].transpose(), dims={var_diam: ds[var_diam]})
    ds['top'] = xr.DataArray(d_lims[1:].transpose(), dims={var_diam: ds[var_diam]})

    ds['diam_lims'] = ds[['bottom', 'top']].to_array(dim='limit')
    # compute dlogD:
    dlog10D = (np.log10(ds['diam_lims'].sel(limit='top')) - np.log10(ds['diam_lims'].sel(limit='bottom')))

    ds['dlog10D'] = xr.DataArray(dlog10D, dims={var_diam: ds[var_diam]})

    ds['log10D'] = np.log10(ds[var_diam])
    # compute number of particles in each bin:
    ds['dN'] = ds[v_dNdlog10D] * ds['dlog10D']

    arg_gt_x = int(ds[var_diam].where(ds['diam_lims'].sel(limit='bottom') > x).argmin().values)
    # get limits for grid box below
    # In log space...
    d_below = np.log10(ds['diam_lims'].isel(**{var_diam:(arg_gt_x - 1)}).sel(limit='bottom'))
    d_above = np.log10(ds['diam_lims'].isel(**{var_diam:(arg_gt_x - 1)}).sel(limit='top'))
    # fraction of gridbox above limit:
    frac_ab = (d_above - np.log10(x)) / (d_above - d_below)
    # Include the fraction of the bin box above limit:
    add = ds['dN'].isel(**{var_diam:(arg_gt_x - 1)}) * frac_ab

    Nx_orig = ds['dN'].isel(**{var_diam:slice(arg_gt_x,None)}).sum(var_diam) + add
    return Nx_orig