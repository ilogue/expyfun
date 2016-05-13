# -*- coding: utf-8 -*-

# Authors: Alexis Bosseler <bosseler@uw.com>
#  and others!!!!
#          simplified bsd-3 license

"""Script for infant basic preference testing using auditory stimuli"""

import numpy as np
from os import path as op
from expyfun import ExperimentController, get_keyboard_input
from expyfun.stimuli import read_wav
from expyfun._trigger_controllers import decimals_to_binary
from expyfun import assert_version
import expyfun.analyze as ea
from expyfun.visual import RawImage

fs= 24414
stim_dir = op.join(op.dirname(__file__), 'words')
sound_files = ['ko_ko_sa_250ms.wav']

#from expyfun import ExperimentController, get_keyboard_input#, set_log_level
#from expyfun.io import read_hdf5
#import expyfun.analyze as ea
#from expyfun.visual import RawImage

#     for ii, wav in enumerate(wavs):


 # define usable buttons / keys
    #live_keys = [x + 1 for x in range(num_freqs)]

print(__doc__)                        
from scipy.misc import imread

#from scipy.misc import imread

#assert_version('8511a4d')

sound_files = {j: op.join(stim_dir, k)
               for j, k in enumerate(sound_files)}
wavs = [np.ascontiguousarray(read_wav(v)) for _, v in sorted(sound_files.items())]
wav = sound_files[0]
# convert length of wave files into number of bits
n_bits = int(np.floor(np.log2(len(wavs)))) + 1
with ExperimentController('IDS', stim_db=75, stim_fs=fs, stim_rms=0.01,
                          check_rms=None, suppress_resamp=True, version='dev') as ec:
                              
               

            
    # stamp trigger line prior to stimulus onset
    #ec.clear_buffer()
    #ec.load_buffer(wav[0])
    #ec.identify_trial(ec_id=str(ii), ttl_id=decimals_to_binary([ii], [n_bits]))
    # our next start time is our last start time, plus
    # the stimulus duration
    #stim_len = 1./fs * len(wav[0][0])  # in seconds
    ec.start_stimulus()  # stamps stimulus onset
    ec.identify_trial(ec_id='one-tone trial')
    ec.listen_presses()
    ec.load_buffer(read_wav(wav)[0])
    ec.play()
    ec.wait_secs(3)
    ec.stop()
    
    #ec.flip()
    im = imread("/Users/bossler/Pictures/animals/Slide01.jpg")
    myImg = RawImage(ec, im)
    myImg.draw()

    #ec.write_data_line('listen / while / get_presses', events)
    #for (k,s,t) in events:
    #    print(k,s,t)
#    ec.flip()  # clears the screen
        
    
    ec.wait_secs(3)  # wait through tone duration to stop the playback
    #ec.stop()
    #ec.trial_ok()
    events = ec.get_presses(kind='both')
    ec.check_force_quit()  # make sure we're not trying to quit
    
    
