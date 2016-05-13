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
import expyfun.analyze as ea
from scipy.misc import imread
from expyfun.visual import RawImage

def matchPressReleaseEvents(events):
    """Assumes events in chron. order"""
    lastPressByKey = {}
    durations = []
    for event in events:
        key, etime, pressOrRelease = event
        if pressOrRelease == 'press':
            assert not key in lastPressByKey, "two presses of same key"
            lastPressByKey[key] = etime
        elif pressOrRelease == 'release':
            if key in lastPressByKey:
                pressTime = lastPressByKey[key]
                del lastPressByKey[key]
            else:
                """No press found for this release. Count from beginning"""
                pressTime = 0
            durations.append((key, etime-pressTime))
    return durations

fs= 24414
#stim_dir = op.join(op.dirname(__file__), 'words')
#sound_files = ['ko_ko_sa_250ms.wav']

#sound_files = {j: op.join(stim_dir, k)
#               for j, k in enumerate(sound_files)}
#wavs = [np.ascontiguousarray(read_wav(v)) for _, v in sorted(sound_files.items())]
#wav = sound_files[0]
# convert length of wave files into number of bits
#n_bits = int(np.floor(np.log2(len(wavs)))) + 1
#stim_len = 1./fs * len(wav[0][0])  # in seconds
stimdir = 'stimuli'
imgs = [op.join(stimdir, i) for i in ['circle.png','star.png']]
rewardfpath = op.join(stimdir, 'like.png')
punishfpath = op.join(stimdir, 'fail.png')


with ExperimentController('testExp', participant='foo', session='001',
                          output_dir='.', version='dev') as ec:

    ec.screen_prompt('Ready?', max_wait=1)

    #ec.clear_buffer()
    #ec.load_buffer(tone)
    #dot.draw()
    #ec.identify_trial(ec_id='xyz', ttl_id=[0, 0])
    ec.listen_presses()

    ## stimulus phase
    for s in [0,1,0]:
        #ec.start_stimulus()
        RawImage(ec, imread(imgs[s])).draw()
        ec.flip()
        ec.wait_secs(.3)
        #ec.stop()
    ec.get_presses(kind='both') # Sends responses during stimuli to log.
    ec.listen_presses() # Clear response buffer at start of response phase.

    ## response phase
    ec.flip()
    ec.wait_secs(2)

    ## analyse responses
    events = ec.get_presses(kind='both')
    keydurs = matchPressReleaseEvents(events)
    print(keydurs)
    if not len(events):
        message = 'no keys pressed'
    else:
        message = ['{} {} after {} secs\n'
                   ''.format(k, r, round(t, 4)) for k, t, r in events]
        message = ''.join(message)
    ec.screen_prompt(message, 3)

    ## reward phase
    if False:
        RawImage(ec, imread(rewardfpath)).draw()
    else:
        RawImage(ec, imread(punishfpath)).draw()
    ec.flip()
    ec.wait_secs(2)


    #ec.trial_ok()
    #print('Presses:\n{}'.format(presses))
    ec.check_force_quit()  # make sure we're not trying to quit


        
    
    
    
    
