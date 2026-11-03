"""One-command launcher for the user's existing IoT-23 archive and screening."""
import argparse
from pathlib import Path
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', default='/media/sf_Downloads/iot_23_datasets_full.tar.gz')
    parser.add_argument('--screen-output', default=str(Path.home()/'iot23_sang_loc_01'))
    parser.add_argument('--inventory', default=str(Path.home()/'iot23_work_01/KIEM_KE.csv'))
    parser.add_argument('--output', default=str(Path.home()/'iot23_da_loc_01'))
    args = parser.parse_args()
    try:
        from export_iot23_normal_syn import run
    except ImportError as error:
        parser.exit(1, 'Run with ~/ai_part2/.venv/bin/python; this tool needs NumPy. '+str(error)+'\n')
    output = Path(args.output).expanduser()
    print('Output:', output, flush=True)
    print('Two archive passes; CSV = original labelled flows, PCAP = selected packet records.', flush=True)
    print('Native Benign from every log; SYN flood only from the reviewed capture34 episode.', flush=True)
    try:
        run(args.archive, args.screen_output, args.inventory, output,
            resume=(output/'BAO_CAO_XUAT.json').is_file())
    except KeyboardInterrupt:
        parser.exit(130, '\nInterrupted. Run the same command to resume completed sources.\n')
    except (ValueError,OSError,EOFError,KeyError,UnicodeError,tarfile.TarError) as error:
        parser.exit(1, 'ERROR: '+str(error)+'\n')


if __name__ == '__main__':
    main()
