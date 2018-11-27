import os, sys, argparse

from log import Log
from detector import Detector

def writeable_dir(prospective_dir):
    """
    Is a directory writeable?

    Based on http://stackoverflow.com/questions/2113427/determining-whether-a-directory-is-writeable.
    """
    if not os.path.isdir(prospective_dir):
        raise argparse.ArgumentTypeError("writeable_dir:{0} is not a valid path".format(prospective_dir))
    elif os.access(prospective_dir, os.W_OK):
        return prospective_dir
    else:
        raise argparse.ArgumentTypeError("writeable_dir:{0} is not a writeable dir".format(prospective_dir))

def wav_file(prospective_file):
    """
    Is a WAV file.
    """
    if not os.path.isfile(prospective_file):
        raise argparse.ArgumentTypeError("wav_file:{0} is not a valid path".format(prospective_file))
    elif os.access(prospective_file, os.R_OK) and os.path.splitext(prospective_file)[1].upper() == ".WAV":
        return prospective_file
    else:
        raise argparse.ArgumentTypeError("wav_file:{0} is not a readable WAV file".format(prospective_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model",
        help="PMDL file to use for hotword detection.")
    parser.add_argument("--log",
        help="Minimum level of log output.",
        choices={"DEBUG","INFO","WARNING","ERROR","CRITICAL"},
        default="INFO")
    parser.add_argument("--sensitivity", "-s",
        help="Sensitivity of the detector (between 0.0 and 1.0). Default is 0.5.",
        default=0.5,
        type=float)
    parser.add_argument("--before", "-b",
        help="Number of seconds to record before the hotword is detected. Default is 60.",
        default=60,
        type=int)
    parser.add_argument("--after", "-a",
        help="Number of seconds to record after the hotword is detected. Default is 60.",
        default=60,
        type=int)
    parser.add_argument("--gain", "-g",
        help="Factor to boost volume of input by. Default is 1.5.",
        default=1.5,
        type=float)
    parser.add_argument("--output", "-o",
        help="Output directory for audio recordings.",
        default=".",
        type=writeable_dir)
    parser.add_argument("--audio-beep",
        help="WAV file to play on commencement of recording",
        dest='audio_beep',
        default=None,
        type=wav_file)
    parser.add_argument("--continue", "-c",
        help="Continue recording on repeat of hotword.",
        dest='continue_recording',
        default=True,
        action='store_true')
    parser.add_argument("--delete-active",
        help="Delete active recording if button pressed during recording.",
        dest='delete_active_recording',
        action='store_false')
    parser.add_argument("--no-continue",
        help="Don't continue recording on repeat of hotword.",
        dest='continue_recording',
        action='store_false')
    args = parser.parse_args()

    Log.init(getattr(Log,args.log))
    Log.debug("__main__", "Logging set to %s " % args.log)

    if args.sensitivity < 0:
        sensitivity=0
    elif args.sensitivity > 1:
        sensitivity=1
    else:
        sensitivity=args.sensitivity

    Log.debug("__main__", "Sensitivity set to %f" % sensitivity)
    detector = Detector(decoder_model=args.model,
        sensitivity=sensitivity,
        audio_gain=args.gain,
        led_running_pin=24,
        led_listening_pin=15,
        led_recording_pin=18,
        continue_recording=args.continue_recording,
        output_dir=args.output,
        delete_active_recording=args.delete_active_recording,
        on_beep_audio_file=args.audio_beep)

    Log.debug("__main__", "Will record %d seconds before and %d seconds after hotword" % (args.before, args.after))
    detector.wait_on_button(button_pin=27,
        record_before=args.before,
        record_after=args.after,
        start_enabled=True)

    Log.info("__main__", "Goodbye, Cruel World!")
    sys.exit(0)