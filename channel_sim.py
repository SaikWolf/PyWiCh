
#!/usr/bin/env python3

import os,sys
import pywich
import numpy as np


scn = pywich.scenarios
fad = pywich.fading
ant = pywich.antennas
chp = pywich.channel_performance
fqb = pywich.frequency_band

import argparse

def position_handle(value):
    return [float(item.strip()) for item in value.split(",")]
def position_sequence_handle(value):
    return [position_handle(item.strip()) for item in value.split(":")]

def parse_args():
    p = argparse.ArgumentParser()

    g = p.add_argument_group("PositionGrid")
    g.add_argument('--xmin',default=-100,type=float,help='Minimum X-position (Unit: m) (def: %(default)sm)')
    g.add_argument('--xmax',default= 100,type=float,help='Maximum X-position (Unit: m) (def: %(default)sm)')
    g.add_argument('--ymin',default=-100,type=float,help='Minimum Y-position (Unit: m) (def: %(default)sm)')
    g.add_argument('--ymax',default= 100,type=float,help='Maximum Y-position (Unit: m) (def: %(default)sm)')
    g.add_argument('--nelem',default=25,type=int,help='Number of grid elements (def: %(default)s)')
    g.add_argument('--los',choices=[0,1,2],default=2,type=int,help='Line of Sight Handler (def: %(default)s : {0: NLOS, 1: LOS, 2: Scenario})')

    b = p.add_argument_group("BaseStation")
    b.add_argument('--pbs',default=[0,0,20],type=position_handle,help='Position of the Base Station (Unit: m)(x,y,z) (def: %(default)r)')
    b.add_argument('--nbs',default=2,type=int,help='Number of Base Station antennas (def: %(default)s)')
    b.add_argument('--gbs',default=8,type=float,help='Gain of Base Station antennas (def: %(default)s)')
    b.add_argument('--bsdb',default=30,type=float,help='Base station transmit power in dBm (def: %(default)s)')
    b.add_argument('--bsnf',default=5,type=float,help='Base station noise figure (Unit: dB) (def: %(default)sdB)')

    m = p.add_argument_group("MobileStation")
    m.add_argument('--Nms',default=1,type=int,help='Number of Mobile Stations (def: %(default)s)')
    m.add_argument('--pms',action='append',default=None,type=position_sequence_handle,help='Position of the Mobile Station (Unit: m)(x0,y0,z0:x1,y1,z1:...)(per ms) (def: [[[10, 10, 2], [20, 10, 2]],])')
    m.add_argument('--tms',action='append',default=None,type=position_handle,help='Timing of the Mobile Station (Unit: s)(t0,t1,...)(per ms) (def: [[0, 0.01],])')
    m.add_argument('--nms',default=2,type=int,help='Number of Mobile Station antennas (def: %(default)s)')
    m.add_argument('--gms',default=8,type=float,help='Gain of Mobile Station antennas (def: %(default)s)')

    s = p.add_argument_group("Scenario")
    s.add_argument("--path",default='./data',type=str,help="Base path to save any results to (def: %(default)r)")
    s.add_argument("--name",default='test',type=str,help="Named folder within the base path to save to (def: %(default)r)")
    s.add_argument("--mode",choices=["ISP","UMA","UMI"],type=str,default='ISP',help="Scenario conditions (def: %(default)s)")
    s.add_argument("--fc",default=30,type=float,help="At what frequency should this scenario run? (Unit: GHz) (def: %(default)sGHz)")
    s.add_argument("--nprb",default=51,type=float,help="Number of resource blocks? (def: %(default)s)")
    s.add_argument("--scs",default=30,type=float,help="Subcarrier Spacing? (Unit: kHz) (def: %(default)skHz)")
    s.add_argument("--nf",default=-174,type=float,help="Assumed noise floor dBm/Hz (def: %(default)s)")
    # s.add_argument("--fc",default=30,type=float,help="At what frequency should this scenario run? (Unit: GHz) (def: %(default)sGHz)")

    args = p.parse_args()
    if args.pms is None:
        assert args.Nms == 1, "pms not (auto-)defined with >1 mobile stations"
        args.pms = ([[10, 10, 2], [20, 10, 2]],)
        if args.tms is None:
            args.tms = [[0,.01]]

    if args.Nms > 0:
        assert len(args.pms) == args.Nms, "number of ms paths does not match set number of ms units"
        assert len(args.tms) == args.Nms, "number of ms path timings does not match set number of ms units"
        for idx,(p,t) in enumerate(zip(args.pms,args.tms)):
            assert len(p) == len(t), f"ms index({idx}) has a positioning length ({len(p)}) and a timing length ({len(t)})"

    if len(args.name.split("_")) == 1:
        args.name += "_0000"
    return args

def setup_antennas(args):
    bs_antennas = args.nbs
    ms_antennas = args.nms
    bs_gain     = args.gbs
    ms_gain     = args.gms
    antenna_element_bs = ant.Antenna3gpp3D(bs_gain)
    antenna_element_ms = ant.AntennaIsotropic(ms_gain)
    antenna_array_bs = ant.AntennaArray3gpp(0.5,.5,1,bs_antennas,0,0,0,antenna_element_bs, 1,"antennaRx")
    antenna_array_ms = ant.AntennaArray3gpp(0.5,.5,1,ms_antennas,0,0,0,antenna_element_ms, 1,"antennaTx")
    #compute phase steering?
    return antenna_array_bs,antenna_array_ms

def setup_scenario(args):
    fcGHz = args.fc
    xmin = args.xmin
    xmax = args.xmax
    ymin = args.ymin
    ymax = args.ymax
    ngrid = args.nelem
    bs_pos = np.array(args.pbs)
    bs_dbm = args.bsdb
    force_los = args.los
    if (args.mode).lower() in ['isp']:
        scenario = scn.Scenario3GPPInDoor(fcGHz,xmin,xmax,ymin,ymax,ngrid,bs_pos,bs_dbm,True,force_los)
    elif (args.mode).lower() in ['umi']:
        scenario = scn.Scenario3GPPUmi(fcGHz,xmin,xmax,ymin,ymax,ngrid,bs_pos,bs_dbm,True,force_los)
    elif (args.mode).lower() in ['uma']:
        scenario = scn.Scenario3GPPUma(fcGHz,xmin,xmax,ymin,ymax,ngrid,bs_pos,bs_dbm,True,force_los)
    else:
        raise RuntimeError(f"Not sure what channel mode this is: {args.mode}")
    return scenario

def setup_freq_band(args):
    fcGHz = args.fc
    nprb = args.nprb
    spacing = args.scs
    noise_floor = args.nf
    bs_dbm = args.bsdb
    bs_nf = args.bsnf
    freq_band = fqb.FrequencyBand(fcGHz=fcGHz,number_prbs=nprb,bw_prb=spacing*12*1e3,noise_figure_db=bs_nf,thermal_noise_dbm_Hz=noise_floor)
    freq_band.compute_tx_psd(tx_power_dbm=bs_dbm)
    return freq_band

def setup_fading(scenario):
    return fad.Fading3gpp(scenario)

def setup_performance(args):
    performance = chp.ChannelPerformance()
    bs_ants, ms_ants = setup_antennas(args)
    scenario = setup_scenario(args)
    freq_band = setup_freq_band(args)
    fading = setup_fading(scenario)

    positions = np.empty(shape=(args.Nms,),dtype=object)
    timings = np.empty(shape=(args.Nms,),dtype=object)
    for idx,(pos,tmg) in enumerate(zip(args.pms,args.tms)):
        positions[idx] = np.array(pos)
        timings[idx] = np.array(tmg)

    simulation_path = os.path.join(args.path,args.name)

    constraints = [{
        'fading' : fading,
        'freq_band' : freq_band,
        'antennaTx' : bs_ants,
        'antennaRx' : ms_ants,
        'n_mspositions': positions,
        'n_times': timings,
        'force_los': args.los,
        'path': simulation_path,
        'mode': 2
    }]
    return performance,constraints,(bs_ants,ms_ants,scenario,freq_band,fading,positions,timings,simulation_path)

def main(args):
    print(args)

    target_dir = os.path.join(args.path,args.name)
    target_num = int(target_dir.split("_")[-1])

    valid_dir = not os.path.exists(target_dir)

    while not valid_dir:
        target_num += 1
        target_dir = '_'.join(target_dir.split("_")[:-1] + [f"{target_num:04d}"])
        valid_dir = not os.path.exists(target_dir)
    else:
        print("Simulation path:",target_dir)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir,exist_ok=False)

    performance,constraints,components = setup_performance(args)
    components[2].save(components[-1])
    components[0].save(components[-1])
    components[1].save(components[-1])
    components[3].save(components[-1])

    performance.compute_path(**(constraints[0]))



if __name__ == '__main__':
    main(parse_args())




